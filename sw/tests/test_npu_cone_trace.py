# SPDX-FileCopyrightText: 2026 Hasan Melih Akbulut
# SPDX-License-Identifier: Apache-2.0
"""Exact next-state cone identity and lossless observed-transition boundaries."""
import hashlib
import importlib.util
from pathlib import Path
import re
import shutil
import sys

import pytest

ROOT=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(ROOT/'scripts'))
import run_cloud_npu_cone_trace as cone

spec=importlib.util.spec_from_file_location('scalar_fixture',ROOT/'sw/tests/test_npu_state_trace.py')
prior=importlib.util.module_from_spec(spec);spec.loader.exec_module(prior)


def source(variant):
    text=prior.source_fixture(variant)+'\n  assign input_d = 1\'h0;\n'
    roots=cone.native_cells('\n'.join(cone.ROOT_BODIES[variant]));wires=set()
    for bit,(name,cell) in zip((0,3),roots.items(),strict=True):
        out=cell['ports']['X' if variant=='original' else 'Y']
        state=cone.old.CELLS[variant][bit]
        pattern=r'  sg13g2_dfrbpq_1 '+state+r' \(\n.*?^  \);'
        match=re.search(pattern,text,re.M|re.S);assert match
        text=text.replace(match[0],match[0].replace('.D(input_d)',f'.D({out})'))
        for expr in cell['ports'].values():
            if re.fullmatch(r'_\d+_',expr):wires.add(expr)
    root_outputs={c['ports']['X' if variant=='original' else 'Y'] for c in roots.values()}
    text+='\n'.join('  wire '+wire+';' for wire in sorted(wires))+'\n'
    text+='\n'.join(cone.ROOT_BODIES[variant])+'\n'
    for i,wire in enumerate(sorted(wires-root_outputs)):
        text+=f"  sg13g2_buf_1 _{900000+i}_ (\n    .A(1'h0),\n    .X({wire})\n  );\n"
    return text


def binding(monkeypatch,variant='candidate',text=None):
    text=source(variant) if text is None else text
    monkeypatch.setitem(cone.q.EXPECTED_NETLISTS,variant,hashlib.sha256(text.encode()).hexdigest())
    return cone.bind(text,prior.model(),variant)


@pytest.mark.parametrize('variant',['original','candidate'])
def test_exact_roots_shared_driver_and_complete_scalar_bindings(monkeypatch,variant):
    row=binding(monkeypatch,variant)
    assert row['depth']==2 and row['state_binding']['model_sha256']==cone.old.MODEL_SHA
    assert [row['cells'][r]['source'] for r in row['roots']]==list(cone.ROOT_BODIES[variant])
    assert row['signals'][:44]==[dict(x,role='state_register') for x in row['state_binding']['signals']]
    assert len({x['expression'] for x in row['signals']})==len(row['signals'])
    if variant=='candidate':
        shared=row['shared_candidate_control'];assert shared['conductor']=='_047302_'
        assert shared['instance'] in row['cells']
        assert any(x['instance']==shared['instance'] and x['field']=='A' for x in row['signals'][44:])
    else:assert row['shared_candidate_control'] is None


@pytest.mark.parametrize('fault',['root_body','missing_root','duplicate_driver','missing_shared_producer','wrong_model','netlist_hash','cell_budget','scalar_budget'])
def test_changed_binding_rejected(monkeypatch,fault):
    text=source('candidate');model=prior.model()
    if fault=='root_body':text=text.replace('.B1(_047305_)','.B1(_047316_)',1)
    if fault=='missing_root':text=text.replace(cone.ROOT_BODIES['candidate'][0],'')
    if fault=='duplicate_driver':text+="  sg13g2_buf_1 _999999_ (\n    .A(1'h0),\n    .X(_047302_)\n  );\n"
    if fault=='missing_shared_producer':text=re.sub(r'  sg13g2_buf_1 _\d+_ \(\n    .A\(1\x27h0\),\n    .X\(_047302_\)\n  \);','',text)
    if fault=='wrong_model':model+='\n// changed'
    if fault=='cell_budget':monkeypatch.setattr(cone,'MAX_CELLS',1)
    if fault=='scalar_budget':monkeypatch.setattr(cone,'MAX_SIGNALS',44)
    monkeypatch.setitem(cone.q.EXPECTED_NETLISTS,'candidate',hashlib.sha256(text.encode()).hexdigest())
    if fault=='netlist_hash':text+='\n'
    with pytest.raises(ValueError):cone.bind(text,model,'candidate')


def test_escaped_scalar_and_bit_select_are_distinct_conductors():
    scalar=r"\foo[0] "
    bit_select=r"\foo [0]"
    assert cone.net_key(scalar)!=cone.net_key(bit_select)
    drivers={cone.net_key(scalar):'scalar_driver',cone.net_key(bit_select):'bus_driver'}
    assert len(drivers)==2 and drivers[cone.net_key(bit_select)]=='bus_driver'
    assert cone.net_key(' _047302_ ')==cone.net_key('_047302_')


def test_sequential_boundary_is_observed_without_traversal(monkeypatch):
    text=source('candidate')
    text=text.replace("sg13g2_buf_1 _900000_ (\n    .A(1'h0),\n    .X(_026978_)",
                      "sg13g2_dfrbpq_1 _900000_ (\n    .D(input_d),\n    .CLK(clk_i),\n    .RESET_B(rst_ni),\n    .Q(_026978_)")
    row=binding(monkeypatch,text=text)
    assert row['cells']['_900000_']['sequential'] is True
    assert {x['field'] for x in row['signals'][44:] if x['instance']=='_900000_'}>=set(cone.old.FIELDS)
    assert any(x['reason']=='sequential_boundary' and x['sink']=='_900000_' for x in row['frontier'])


def test_instrumentation_preserves_all_baseline_statements(monkeypatch):
    row=binding(monkeypatch);text='module tb;reg clk;integer cycles;endmodule\n';new=cone.instrument(text,row)
    assert re.sub(r'\n  // NSSOC_NPU_CONE_BEGIN.*?  // NSSOC_NPU_CONE_END\n','',new,flags=re.S)==text
    assert not re.search(r'\b(force|release|deposit)\b',new)
    with pytest.raises(ValueError):cone.instrument(new,row)
    row['signals'][-1]['expression']='dut.bad); force dut.q=0;'
    with pytest.raises(ValueError):cone.instrument(text,row)


def rows(tmp_path):
    raw=['INIT seq=1 cycle=1 realtime_ns=10.001 all=0x',
         'EV seq=2 cycle=2 realtime_ns=20.000 signal=1 prior=0 value=x all=xx',
         'S seq=3 cycle=2 realtime_ns=20.001 all=xx',
         'EV seq=4 cycle=3 realtime_ns=25.000 signal=0 prior=x value=0 all=x0',
         'S seq=5 cycle=3 realtime_ns=30.001 all=x0']
    summary='NPU_CONE_SUMMARY start=2 last=3 width=2 events=2 samples=2 sequence=5 final_cycle=4 armed=1\n'
    (tmp_path/'npu-cone-events.log').write_text('\n'.join(raw)+'\n')
    return raw,summary


def test_static_x_is_separate_from_new_transition(tmp_path):
    _,log=rows(tmp_path);row=cone.parse(log,tmp_path,2,3,2)
    assert row['initial_static_unknowns']==[dict(signal=0,value='x')]
    assert row['first_new_unknown']==dict(sequence=2,cycle=2,realtime_ns='20.000',signal=1,prior='0',value='x')
    assert len(row['new_unknown_transitions'])==1


@pytest.mark.parametrize('fault',['missing_init','second_init','missing_event','unchanged_event','wrong_prior','wrong_sample','wrong_snapshot','wrong_index','time_backwards','duplicate_cycle','unarmed','missing_summary','duplicate_summary','incomplete_window','event_bound'])
def test_incomplete_or_inconsistent_event_history_rejected(tmp_path,fault):
    raw,log=rows(tmp_path)
    if fault=='missing_init':raw[0]=raw[0].replace('INIT','S')
    if fault=='second_init':raw[2]=raw[2].replace('S seq','INIT seq')
    if fault=='missing_event':raw.pop(1)
    if fault=='unchanged_event':raw[1]=raw[1].replace('value=x','value=0').replace('all=xx','all=0x')
    if fault=='wrong_prior':raw[1]=raw[1].replace('prior=0','prior=1')
    if fault=='wrong_sample':raw[2]=raw[2].replace('all=xx','all=00')
    if fault=='wrong_snapshot':raw[1]=raw[1].replace('all=xx','all=0x')
    if fault=='wrong_index':raw[1]=raw[1].replace('signal=1','signal=2')
    if fault=='time_backwards':raw[1]=raw[1].replace('20.000','1.000')
    if fault=='duplicate_cycle':raw[4]=raw[4].replace('cycle=3','cycle=2')
    if fault=='unarmed':log=log.replace('armed=1','armed=0')
    if fault=='missing_summary':log=''
    if fault=='duplicate_summary':log+=log
    if fault=='incomplete_window':log=log.replace('final_cycle=4','final_cycle=3')
    (tmp_path/'npu-cone-events.log').write_text('\n'.join(raw)+'\n')
    with pytest.raises(ValueError):cone.parse(log,tmp_path,2,3,2,max_events=1 if fault=='event_bound' else cone.MAX_EVENTS)


def test_real_monitor_coalesced_callback_static_unknown_and_native_event_limit(tmp_path):
    iv=shutil.which('iverilog');vvp=shutil.which('vvp');assert iv and vvp
    source=tmp_path/'tiny.v';source.write_text('''`timescale 1ns/1ps
module tiny;reg clk=0;integer cycles=0;reg [1:0] data=2'bx0;
always #5 clk=~clk;always @(posedge clk)cycles=cycles+1;
nssoc_npu_cone_event_trace #(.WIDTH(2),.START(2),.LAST(4),.MAX_EVENTS(2)) observer(
.clk_i(clk),.cycle_i({32'b0,cycles}),.signals_i(data));
initial begin #20;data[0]=1;data[0]=0;#1;data[0]=1'bx;#39;$finish;end
endmodule
''')
    compile_row=cone.tiny_execute([iv,'-g2005-sv','-s','tiny','-o',tmp_path/'a.vvp',source,ROOT/cone.MONITOR],tmp_path,'compile')
    assert compile_row['returncode']==0
    run=cone.tiny_execute([vvp,'-i',tmp_path/'a.vvp','+npu_cone_dir='+str(tmp_path)],tmp_path,'run');assert run['returncode']==0
    row=cone.parse((tmp_path/'run.log').read_text(),tmp_path,2,4,2)
    assert row['events']==1 and row['initial_static_unknowns']==[dict(signal=1,value='x')]
    assert row['first_new_unknown']['signal']==0 and row['first_new_unknown']['realtime_ns']=='21.000'
    source.write_text(source.read_text().replace("#1;data[0]=1'bx;", "#1;data[0]=1'bx;#1;data[0]=0;#1;data[0]=1;"))
    assert cone.tiny_execute([iv,'-g2005-sv','-s','tiny','-o',tmp_path/'b.vvp',source,ROOT/cone.MONITOR],tmp_path,'bounded-compile')['returncode']==0
    failed=cone.tiny_execute([vvp,'-i',tmp_path/'b.vvp','+npu_cone_dir='+str(tmp_path)],tmp_path,'bounded-run')
    assert failed['returncode']!=0 and 'Cone event bound exhausted' in (tmp_path/'bounded-run.log').read_text()
    with pytest.raises(ValueError):cone.parse((tmp_path/'bounded-run.log').read_text(),tmp_path,2,4,2)


def test_sources_cloud_boundary_and_no_qualification_relaxation(monkeypatch,tmp_path):
    for path,sha in cone.PINS.items():assert cone.q.common.sha(ROOT/path)==sha
    assert cone.q.CYCLES==3000000 and (cone.START,cone.LAST)==(1569360,1569520)
    assert cone.PRIOR['first_candidate_data_unknown']<cone.PRIOR['first_candidate_q_unknown']
    monkeypatch.delenv('GITHUB_ACTIONS',raising=False)
    with pytest.raises(ValueError,match='cloud-only'):cone.prepare(tmp_path/'out',tmp_path/'work','candidate')
    with pytest.raises(ValueError,match='cloud-only'):cone.run(tmp_path/'out')
