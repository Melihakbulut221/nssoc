# SPDX-FileCopyrightText: 2026 Hasan Melih Akbulut
# SPDX-License-Identifier: Apache-2.0
"""The interface flow must retain the upstream router and apply cleanup once."""
import importlib.util
from pathlib import Path
import shutil
import subprocess
import sys
from types import ModuleType, SimpleNamespace

import pytest

ROOT = Path(__file__).resolve().parents[2]


@pytest.fixture
def flow(tmp_path, monkeypatch):
    """Stub only LibreLane's class registry, not the script transformation."""
    script = tmp_path / "upstream.tcl"
    script.write_text("set before 1\nread_current_odb\n\nset after 2\n")

    class DetailedRouting:
        def get_script_path(self):
            return str(script)

    cts = type("PostCTS", (DetailedRouting,), {})
    grt = type("PostGRT", (DetailedRouting,), {})
    openroad = SimpleNamespace(ResizerTimingPostCTS=cts, ResizerTimingPostGRT=grt,
                               DetailedRouting=DetailedRouting)
    classic = type("Classic", (), {"Steps": [cts, grt, DetailedRouting], "gating_config_vars": {}})
    registry = SimpleNamespace(factory=SimpleNamespace(register=lambda: lambda cls: cls))
    for name, attrs in {
        "librelane": {"__path__": []},
        "librelane.flows": {"Flow": registry, "__path__": []},
        "librelane.flows.classic": {"Classic": classic},
        "librelane.steps": {"OpenROAD": openroad},
    }.items():
        module = ModuleType(name)
        module.__dict__.update(attrs)
        monkeypatch.setitem(sys.modules, name, module)
    spec = importlib.util.spec_from_file_location("tested_interface_flow", ROOT / "hw/soc/pnr/interface_flow.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    instance = module.CleanOrphanGuides()
    instance.step_dir = tmp_path
    return module, instance, script


def test_upstream_body_preserved_with_one_cleanup_after_database_read(flow):
    module, instance, script = flow
    original = script.read_text()
    output = Path(instance.get_script_path()).read_text()
    start = original.index("read_current_odb\n") + len("read_current_odb\n")
    added_and_tail = output[start:].splitlines(keepends=True)
    assert added_and_tail[0].startswith('source "')
    assert added_and_tail[1] == 'puts "REMOVED_ORPHAN_GUIDES [prune_orphan_guides [ord::get_db_block]]"\n'
    assert output[:start] + "".join(added_and_tail[2:]) == original
    assert sum(step is module.CleanOrphanGuides for step in module.Interfaces.Steps) == 1


@pytest.mark.parametrize("text", ["# no database load\n", "read_current_odb\nread_current_odb\n"])
def test_template_drift_fails_before_a_router_script_is_written(flow, text):
    _, instance, script = flow
    script.write_text(text)
    with pytest.raises(RuntimeError, match="Unsupported LibreLane routing script"):
        instance.get_script_path()
    assert not (Path(instance.step_dir) / "clean_orphan_guides_drt.tcl").exists()


def test_missing_cleanup_dependency_rejected(flow, tmp_path, monkeypatch):
    module, instance, _ = flow
    monkeypatch.setattr(module, "__file__", str(tmp_path / "missing/pnr/interface_flow.py"))
    with pytest.raises(RuntimeError, match="Missing guide cleanup script"):
        instance.get_script_path()


def test_literal_helper_path_is_not_tcl_substitution(flow, tmp_path, monkeypatch):
    tclsh = shutil.which("tclsh")
    if not tclsh:
        pytest.skip("tclsh is required to execute the generated flow script")
    module, instance, _ = flow
    # A literal path containing Tcl metacharacters must not execute commands
    # or expand variables. The fake helper exposes whether source succeeded.
    soc = tmp_path / 'space $missing[error unexpected]"\\literal'
    helper = soc / "flow/prune_orphan_guides.tcl"
    helper.parent.mkdir(parents=True)
    helper.write_text("proc prune_orphan_guides {block} {return 7}\n")
    monkeypatch.setattr(module, "__file__", str(soc / "pnr/interface_flow.py"))
    script = Path(instance.get_script_path()).read_text()
    script = 'proc read_current_odb {} {}\nnamespace eval ord {proc get_db_block {} {return block}}\n' + script
    script += 'puts "BODY_RETAINED $before $after"\n'
    result = subprocess.run([tclsh], input=script, capture_output=True, text=True)
    assert result.returncode == 0 and not result.stderr, result.stderr
    assert "REMOVED_ORPHAN_GUIDES 7" in result.stdout
    assert "BODY_RETAINED 1 2" in result.stdout


@pytest.mark.parametrize('step_name', ['BoundedPostCTS', 'BoundedPostGRT'])
@pytest.mark.parametrize('derate', ['5', '5.0'])
def test_native_resizer_rejects_truncation_before_database_load(flow, step_name, derate, tclsh):
    module, _, script = flow
    original = ('proc read_current_odb {} {puts DATABASE_READ}\n'
                'read_current_odb\nset setup_args {}\nlappend setup_args -setup\n'
                'puts "ARGS $setup_args"\n')
    script.write_text(original)
    step = getattr(module, step_name)()
    step.step_dir = script.parent
    output = Path(step.get_script_path())
    runner = script.parent / 'run_guarded.tcl'
    runner.write_text(f'set ::env(TIME_DERATING_CONSTRAINT) {derate}\n' + output.read_text())
    result = subprocess.run([tclsh, str(runner)], capture_output=True, text=True)
    if derate == '5':
        assert result.returncode != 0
        assert 'loses precision' in result.stderr
        assert 'DATABASE_READ' not in result.stdout
    else:
        assert result.returncode == 0, result.stderr
        assert 'early=0.95 late=1.05' in result.stdout
        assert 'DATABASE_READ' in result.stdout
        expected = 100
        assert f'ARGS -setup -max_iterations {expected}' in result.stdout
    assert script.read_text() == original


@pytest.mark.parametrize('selection,code', [('project', 74), ('override', 75),
                                          ('fallback', 73), ('missing-override', 127)])
def test_direct_layout_preparation_selects_python_before_any_synthesis(tmp_path, selection, code):
    import os
    # Run the actual shell entrypoint in an isolated project. The selected
    # interpreter records its arguments then deliberately stops preparation;
    # neither synthesis nor layout can run in this test.
    script = tmp_path / 'hw/soc/flow/implement_interfaces.sh'
    script.parent.mkdir(parents=True)
    shutil.copyfile(ROOT / 'hw/soc/flow/implement_interfaces.sh', script)
    project_python = tmp_path / '.venv/bin/python'
    fallback_python = tmp_path / 'bin/python3'
    override_python = tmp_path / 'explicit-python'
    for path, status in [(fallback_python, 73), (project_python, 74), (override_python, 75)]:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text('#!/bin/sh\nprintf "%s\\n" "$@" > "$NSSOC_TEST_PY_LOG"\nexit '+str(status)+'\n')
        path.chmod(0o755)
    env = {k: v for k, v in os.environ.items() if k not in ('PYTHON', 'INTERFACE_PYTHON')}
    log = tmp_path / 'interpreter.log'
    env.update(PATH=str(fallback_python.parent)+os.pathsep+env['PATH'],
               SOC_INTERFACE_PROFILE='full', NSSOC_TEST_PY_LOG=str(log))
    if selection == 'fallback': project_python.unlink()
    elif selection == 'override': env['INTERFACE_PYTHON'] = str(override_python)
    elif selection == 'missing-override': env['INTERFACE_PYTHON'] = str(tmp_path/'absent-python')
    result = subprocess.run(['bash', str(script), 'python-contract'], env=env,
                            capture_output=True, text=True)
    assert result.returncode == code, result.stdout + result.stderr
    assert not (tmp_path/'hw/soc/out/python-contract.inputs.json').exists()
    if selection == 'missing-override':
        assert not log.exists()
    else:
        assert log.read_text().splitlines() == [str(script.parent/'prepare_interfaces.py'),
                                               '--profile', 'full']


@pytest.fixture
def implementation_project(tmp_path):
    """Exercise the shell handoff with real ROM/profile generators.

    Only the expensive compiler/synthesizer/router are replaced; their
    argument and environment captures expose stale-profile handoffs.
    """
    import json
    project = tmp_path / 'project'
    flow = project / 'hw/soc/flow'
    flow.mkdir(parents=True)
    for pattern in ('hw/soc/flow/*', 'hw/soc/pnr/*.json', 'hw/soc/pnr/interface_flow.py',
                    'hw/soc/techmap/*', 'hw/soc/sta/*.sdc', 'hw/soc/rtl/soc_logic_boot_rom.v.in',
                    'sw/golden/*.py'):
        for source in ROOT.glob(pattern):
            if source.is_file():
                target = project / source.relative_to(ROOT)
                target.parent.mkdir(parents=True, exist_ok=True)
                shutil.copyfile(source, target)
    (flow/'prepare_interfaces.py').write_text('# preparation stub\n')
    (flow/'build_sw_soc.sh').write_text('set -eu\nmkdir -p "$1"\nprintf "loader" > "$1/test_soc.bin"\n')
    config = json.loads((project/'hw/soc/pnr/config-interfaces-logicrom.json').read_text())
    netlist = 'module soc_top();\n' + ''.join(
        f'{master} \\{name} ();\n' for master, data in config['MACROS'].items()
        for name in data['instances']) + 'endmodule\n'
    (flow/'mapped-fixture.v').write_text(netlist)
    (flow/'syn_soc_top.sh').write_text('''set -eu
flow=$(dirname "$0")
# Match the real synthesizer's output-directory replacement behavior.
rm -rf "$2"
mkdir -p "$2"
env | sort > "$2/environment.txt"
cp "$flow/mapped-fixture.v" "$2/soc_top.netlist.v"
python3 "$flow/gen_logic_boot_rom.py" --image "$SOC_BOOT_ROM_IMAGE" --output "$2/boot-rom"
case "${TEST_MUTATION:-}" in
 image) printf corrupt >> "$SOC_BOOT_ROM_IMAGE" ;;
 source) printf '# drift\n' >> "$flow/build_sw_soc.sh" ;;
 failed-synthesis) exit 79 ;;
esac
''')
    (flow/'pnr_soc_top.sh').write_text('set -eu\nenv | sort > "$NSSOC_PNR_CAPTURE"\nprintf "%s\\n" "$@" > "$NSSOC_PNR_CAPTURE.args"\n')
    return project


def run_implementation(project, *args, mutation=None, config=None):
    import os
    env = {key: value for key, value in os.environ.items()
           if key not in ('PYTHON', 'INTERFACE_PYTHON', 'PNR_CONFIG')}
    env.update(SOC_BOOT_ROM='legacy', SOC_WAKE_GNT='0', SOC_BOOT_ROM_IMAGE='/stale/image',
               SOC_MEM_HARDEN='0', NSSOC_PNR_CAPTURE=str(project/'pnr.env'))
    if mutation: env['TEST_MUTATION'] = mutation
    if config: env['PNR_CONFIG'] = str(config)
    return subprocess.run(['bash', str(project/'hw/soc/flow/implement_interfaces.sh'), 'trial', *args],
                          env=env, text=True, capture_output=True)


def test_current_boot_profile_reaches_router_with_identical_rom(implementation_project):
    import hashlib
    import json
    project = implementation_project
    result = run_implementation(project, '-T', 'OpenROAD.GlobalRouting')
    assert result.returncode == 0, result.stdout + result.stderr
    out = project/'hw/soc/out/trial'
    record = json.loads((out/'inputs.json').read_text())
    assert record['boot_image_sha256'] == hashlib.sha256(b'loader').hexdigest()
    assert record['configuration']['WAKE_GNT'] == 1
    assert record['configuration']['SOC_BOOT_ROM'] == 'logic'
    assert record['physical_config']['path'] == 'config-interfaces-logicrom.json'
    for capture in (out/'synthesis/environment.txt', project/'pnr.env'):
        env = dict(line.split('=', 1) for line in capture.read_text().splitlines() if '=' in line)
        assert env['SOC_BOOT_ROM'] == 'logic' and env['SOC_WAKE_GNT'] == '1'
        assert env['SOC_BOOT_ROM_IMAGE'] == str(out/'firmware/test_soc.bin')
        assert env['SOC_BOOT_ROM_DIR'] == str(out/'synthesis/boot-rom')
        assert env['SOC_MEM_HARDEN'] == '1'
    assert (out/'boot-rom-reference/soc_logic_boot_rom.v').read_bytes() == (out/'synthesis/boot-rom/soc_logic_boot_rom.v').read_bytes()
    assert (project/'pnr.env.args').read_text().splitlines()[-2:] == ['-T', 'OpenROAD.GlobalRouting']
    assert (out/'firmware.log').exists() and (out/'build.log').exists()
    # Retrying may not destroy the retained loader, logs or routed candidate.
    again = run_implementation(project)
    assert again.returncode == 2 and 'Refusing to overwrite' in again.stderr
    assert (out/'firmware/test_soc.bin').read_bytes() == b'loader'


@pytest.mark.parametrize('request_reg,writeback', [(0, 0), (1, 0), (0, 1), (1, 1)])
def test_core_pipeline_configuration_is_recorded_and_forwarded(
        implementation_project, monkeypatch, request_reg, writeback):
    import json
    monkeypatch.setenv('SOC_CORE_REQ_REG', str(request_reg))
    monkeypatch.setenv('SOC_CORE_WB_STAGE', str(writeback))
    project = implementation_project
    result = run_implementation(project, '--synthesis-only')
    assert result.returncode == 0, result.stdout + result.stderr
    out = project/'hw/soc/out/trial'
    config = json.loads((out/'inputs.json').read_text())['configuration']
    assert config['CORE_REQ_REG'] == request_reg
    assert config['CORE_WB_STAGE'] == writeback
    assert config['CORE_BRANCH_TARGET_ALU'] == writeback
    env = dict(line.split('=', 1) for line in
               (out/'synthesis/environment.txt').read_text().splitlines() if '=' in line)
    assert env['SOC_CORE_REQ_REG'] == str(request_reg)
    assert env['SOC_CORE_WB_STAGE'] == str(writeback)


def test_invalid_core_pipeline_is_rejected_before_work(implementation_project, monkeypatch):
    monkeypatch.setenv('SOC_CORE_WB_STAGE', '2')
    result = run_implementation(implementation_project)
    assert result.returncode == 2 and 'must be 0 or 1' in result.stderr
    assert not (implementation_project/'hw/soc/out/trial').exists()


@pytest.mark.parametrize('mutation', ['image', 'source', 'failed-synthesis'])
def test_implementation_rejects_drift_and_preserves_failure_logs(implementation_project, mutation):
    project = implementation_project
    result = run_implementation(project, mutation=mutation)
    assert result.returncode != 0
    assert not (project/'pnr.env').exists()
    out = project/'hw/soc/out/trial'
    assert (out/'build.log').exists() and (out/'inputs.json').exists()
    if mutation != 'failed-synthesis':
        assert 'changed during synthesis' in result.stderr


def test_old_sram_rom_floorplan_is_rejected_before_router(implementation_project):
    project = implementation_project
    result = run_implementation(project, config=project/'hw/soc/pnr/config-interfaces-synpre.json')
    assert result.returncode != 0 and 'ROM profile mismatch' in result.stderr
    assert not (project/'pnr.env').exists()


def test_synthesis_only_does_not_claim_or_start_layout(implementation_project):
    result = run_implementation(implementation_project, '--synthesis-only')
    assert result.returncode == 0, result.stdout + result.stderr
    assert 'no placement or signoff' in result.stdout
    assert not (implementation_project/'pnr.env').exists()
