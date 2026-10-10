# SPDX-FileCopyrightText: 2026 Hasan Melih Akbulut
# SPDX-License-Identifier: Apache-2.0
"""Optional dependencies must be opt-in, intact, and visible in discovery."""
import hashlib
import importlib.util
import json
from pathlib import Path
import shutil
import subprocess
import sys

import pytest
import yaml

ROOT = Path(__file__).resolve().parents[2]
FLOW = ROOT/'hw/soc/flow'


@pytest.fixture
def modules(monkeypatch):
    monkeypatch.syspath_prepend(str(FLOW))
    import prepare_interfaces
    import interface_profile
    return prepare_interfaces, interface_profile


@pytest.fixture
def fake_sources(tmp_path, monkeypatch, modules):
    prepare, profile = modules
    soc = tmp_path/'soc'
    monkeypatch.setattr(prepare, 'SOC', soc)
    monkeypatch.setattr(prepare, "adapt_eth", lambda name, data: data)
    queried = []

    def git(command, **kwargs):
        name = Path(command[2]).name
        queried.append(name)
        return prepare.PINS[name]+'\n' if 'rev-parse' in command else ''

    monkeypatch.setattr(prepare.subprocess, 'check_output', git)
    paths = ['verilog-i2c/rtl/i2c_master.v']
    paths += ['verilog-ethernet/rtl/'+n+'.v' for n in
              ['eth_mac_1g_fifo','eth_mac_1g','axis_gmii_rx','axis_gmii_tx','lfsr']]
    paths += ['verilog-ethernet/lib/axis/rtl/'+n+'.v' for n in
              ['axis_async_fifo_adapter','axis_async_fifo','axis_adapter']]
    for name in paths:
        path = soc/'ext'/name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text('if (rst) begin\n        state_reg <= STATE_IDLE;\nend\n'
                        if path.name == 'axis_gmii_tx.v' else '// source '+name+'\n')
    return soc, queried, prepare, profile


def test_base_never_reads_or_requires_lgpl_checkout(fake_sources):
    soc, queried, prepare, profile = fake_sources
    bundle = prepare.prepare()
    assert set(queried) == {'verilog-i2c','verilog-ethernet'}
    assert not (soc/'ext/can').exists()
    assert not (soc/'ext/spacewire_reloaded').exists()
    assert 'CAN_WISHBONE_IF' not in bundle.read_text()
    assert profile.resolve('base', soc) == (bundle.resolve(), '')
    manifest = json.loads(bundle.with_suffix('.json').read_text())
    assert manifest['profile'] == 'base'
    assert set(manifest['pins']) == {'verilog-i2c','verilog-ethernet'}


@pytest.mark.parametrize('corruption', ['bundle', 'source', 'profile', 'pin', 'empty', 'lgpl', 'escape'])
def test_mismatched_or_modified_bundle_rejected(fake_sources, corruption):
    soc, _, prepare, profile = fake_sources
    bundle = prepare.prepare()
    path = bundle.with_suffix('.json')
    manifest = json.loads(path.read_text())
    if corruption == 'bundle':
        bundle.write_text(bundle.read_text()+'// changed\n')
    elif corruption == 'source':
        (soc/'ext/verilog-i2c/rtl/i2c_master.v').write_text('// changed\n')
    elif corruption == 'profile':
        manifest['profile'] = 'full'
    elif corruption == 'pin':
        manifest['pins']['verilog-i2c'] = '0'*40
    elif corruption == 'empty':
        manifest['inputs'] = {}
    elif corruption == 'lgpl':
        manifest['inputs']['ext/can/rtl/verilog/can_top.v'] = '0'*64
    else:
        manifest['inputs']['ext/verilog-i2c/../../../escape.v'] = '0'*64
    path.write_text(json.dumps(manifest))
    with pytest.raises((ValueError, OSError)):
        profile.resolve('base', soc)


def test_full_requires_explicit_selection_and_preserves_separate_base(fake_sources, monkeypatch):
    soc, queried, prepare, profile = fake_sources
    base = prepare.prepare()
    original = base.read_bytes()
    spw = soc/'ext/spacewire_reloaded/rtl/verilog'
    spw.mkdir(parents=True)
    for name in ['syncdff','spwram','spwrecvfront_generic','spwrecvfront_fast',
                 'spwrecv','spwxmit','spwxmit_fast','spwlink','spwstream']:
        (spw/(name+'.v')).write_text('// optional SpaceWire source\n')
    can = soc/'ext/can/rtl/verilog'
    can.mkdir(parents=True)
    (can/'can_top.v').write_text('// optional CAN source\n')
    # This fixture checks profile selection, not the immutable CAN decoder.
    # Actual decoder adaptation has separate pinned-source and pin tests.
    monkeypatch.setattr(prepare, 'bind_can', lambda name, data: data)
    bundle = prepare.prepare('full')
    assert base.read_bytes() == original and bundle != base
    assert profile.resolve('full', soc) == (bundle.resolve(), '-DSOC_LGPL_INTERFACES')
    assert 'CAN_WISHBONE_IF' in bundle.read_text()
    assert set(queried) == set(prepare.PINS)
    manifest_path = bundle.with_suffix('.json')
    manifest = json.loads(manifest_path.read_text())
    assert set(manifest['project_inputs']) == set(prepare.project_sources('full'))
    for bad in [{}, {**manifest['project_inputs'], '../escape': '0'*64},
                {**manifest['project_inputs'], 'regmap/can.yaml': '0'*64}]:
        manifest_path.write_text(json.dumps({**manifest, 'project_inputs': bad}))
        with pytest.raises(ValueError): profile.resolve('full', soc)
    manifest_path.write_text(json.dumps(manifest))
    with pytest.raises(ValueError):
        prepare.selected_pins('typo')


@pytest.mark.parametrize('selection,expected', [
    ('base', {'fetch-verilog-i2c','fetch-verilog-ethernet'}),
    ('full', {'fetch-verilog-i2c','fetch-verilog-ethernet','fetch-spacewire_reloaded','fetch-can'}),
    ('invalid', set()),
])
def test_make_fetches_only_explicitly_selected_dependencies(tmp_path, selection, expected):
    log = tmp_path/'commands.log'
    stub = tmp_path/'record-tool'
    stub.write_text('#!/usr/bin/env python3\nimport sys\nfrom pathlib import Path\np=Path('+repr(str(log))+')\nwith p.open("a") as f: f.write(" ".join(sys.argv[1:])+"\\n")\n')
    stub.chmod(0o755)
    result = subprocess.run(['make','--no-print-directory','soc-interfaces-prepare',
                             'SOC_INTERFACE_PROFILE='+selection,'MAKE='+str(stub),
                             'INTERFACE_PYTHON='+str(stub)], cwd=ROOT, capture_output=True, text=True)
    words = log.read_text().split() if log.exists() else []
    assert {w for w in words if w.startswith('fetch-')} == expected
    assert (result.returncode == 0) == (selection != 'invalid')


@pytest.mark.parametrize('full', [False, True])
def test_discovery_words_follow_elaborated_profile(tmp_path, full):
    iverilog, vvp = shutil.which('iverilog'), shutil.which('vvp')
    if not iverilog or not vvp:
        pytest.skip('Icarus is required for both discovery table profiles')
    spec = importlib.util.spec_from_file_location('profile_memmap', ROOT/'regmap/generate_memmap.py')
    gen = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(gen)
    data = gen.load()
    words = gen.apb_pnp_words(data)
    optional = {2*i+j for i, slot in enumerate(sorted(data['apb_slots'],key=lambda s:s['slot']))
                if slot['name'] in ('SPW','CAN') for j in [0,1]}
    bench = '''module tb;
reg [11:0] a; wire [31:0] d; wire ready,err;
soc_apb_pnp dut(.psel_i(1'b1),.penable_i(1'b1),.pwrite_i(1'b0),
.pwdata_i(32'd0),.paddr_i(a),.prdata_o(d),.pready_o(ready),.pslverr_o(err));
initial begin
'''
    for word, value in sorted(words.items()):
        if not full and word in optional:
            value = 0
        bench += f"a=12'h{4*word:03x}; #1; if(d!==32'h{value:08x} || !ready || err) $fatal(1,\"word {word}\");\n"
    bench += '$display("PROFILE_TABLE_PASS"); $finish; end\nendmodule\n'
    source = tmp_path/'tb.v'; source.write_text(bench)
    exe = tmp_path/'sim.vvp'
    args = [iverilog,'-g2005-sv','-s','tb','-I',str(ROOT/'hw/soc/rtl'),'-o',str(exe)]
    if full:
        args += ['-DSOC_LGPL_INTERFACES']
    subprocess.run(args+[str(ROOT/'hw/soc/rtl/soc_apb_pnp.v'),str(source)],check=True,capture_output=True,text=True)
    result = subprocess.run([vvp,str(exe)],check=True,capture_output=True,text=True)
    assert 'PROFILE_TABLE_PASS' in result.stdout


@pytest.mark.parametrize('profile,instances,accepted', [
    ('base', [], True), ('full', ['u_can', 'u_spw'], True),
    ('base', ['u_can', 'u_spw'], False), ('full', [], False),
    ('full', ['u_can'], False), ('base', ['u_spw'], False),
])
def test_physical_profile_rejects_mixed_netlist(tmp_path, modules, profile, instances, accepted):
    _, helper = modules
    netlist = tmp_path/'soc.v'
    netlist.write_text('module soc_top(input clk);\n// wire \\u_can.fake ;\n'
                       + ''.join('wire \\'+n+'.state ;\n' for n in instances)
                       + 'endmodule\n')
    if accepted:
        helper.check_netlist(netlist, profile)
    else:
        with pytest.raises(ValueError, match='does not match'):
            helper.check_netlist(netlist, profile)


def test_physical_profile_rejects_missing_top(tmp_path, modules):
    netlist = tmp_path/'wrong.v'; netlist.write_text('module other(); endmodule\n')
    with pytest.raises(ValueError, match='soc_top'):
        modules[1].check_netlist(netlist, 'base')


def test_workflow_full_dependencies_require_explicit_manual_selection():
    workflow = yaml.load((ROOT/'.github/workflows/checks.yml').read_text(), Loader=yaml.BaseLoader)
    inputs = workflow['on']['workflow_dispatch']['inputs']
    assert inputs['full_interfaces']['type'] == 'boolean'
    assert inputs['full_interfaces']['default'] == 'false'
    selection = workflow['env']['SOC_INTERFACE_PROFILE']
    assert "github.event_name == 'workflow_dispatch' && inputs.full_interfaces" in selection
    assert "&& 'full' || 'base'" in selection
    assert 'inputs.full_interfaces' in workflow['concurrency']['group']
    assert all('SOC_INTERFACE_PROFILE' not in job.get('env', {})
               for job in workflow['jobs'].values())
