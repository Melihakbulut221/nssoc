# SPDX-FileCopyrightText: 2026 Hasan Melih Akbulut
# SPDX-License-Identifier: Apache-2.0
"""Bounded exact-source observation closure, never a substitute for native boot."""
import copy
import hashlib
import json
from pathlib import Path
import re
import shutil
import subprocess
import sys

import pytest

ROOT=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(ROOT/'scripts'))
import run_cloud_npu_frontier_trace as frontier


def fixture(monkeypatch):
    def mod(inputs,outputs,sequential=False):
        return dict(input=inputs,output=outputs,fields=sorted(inputs+outputs),sequential=sequential,
                    body='input '+','.join(inputs)+'; output '+','.join(outputs)+';')
    modules={'buf':mod(['A'],['X']),'nand':mod(['A','B'],['Y']),
             'sg13g2_dfrbpq_1':mod(['CLK','D','RESET_B'],['Q'],True)}
    def cell(typ,ports):return dict(type=typ,ports=ports,source=json.dumps([typ,ports],sort_keys=True))
    cells={'root':cell('nand',{'A':r'\u_npu.state0 ','B':'q1','Y':r'\u_npu.probe '}),
           'ff0':cell('sg13g2_dfrbpq_1',{'CLK':'clk','D':'d','RESET_B':'rst','Q':r'\u_npu.state0 '}),
           'ff1':cell('sg13g2_dfrbpq_1',{'CLK':'clk','D':'d','RESET_B':'rst','Q':'q1'}),
           'd_source':cell('buf',{'A':'next_i','X':'d'}),
           'clock_source':cell('buf',{'A':'clk_i','X':'clk'}),
           'reset_source':cell('buf',{'A':'rst_i','X':'rst'})}
    base=dict(signals=[],state_binding=dict(signals=[]),cells={})
    monkeypatch.setattr(frontier.previous,'bind',lambda *args:copy.deepcopy(base))
    monkeypatch.setattr(frontier,'native_modules',lambda model:modules)
    monkeypatch.setattr(frontier,'native_cells',lambda netlist:cells)
    return cells,modules,[r'\u_npu.probe']


def test_complete_semantic_closure_stops_at_actual_sequential_boundary(monkeypatch):
    cells,modules,roots=fixture(monkeypatch)
    row=frontier.derive_binding('fixture','model','original',roots)
    assert row['closed_cone_cells']==['ff0','ff1','root']
    assert row['sequential_boundary']==['ff0','ff1']
    assert set(row['cells'])==set(cells)
    assert len(row['immediate_boundary_drivers'])==6
    assert {x['conductor'] for x in row['frontier']}=={'clk_i','next_i','rst_i'}
    assert all(x['source'] is None for x in row['frontier'])
    assert {s['expression'] for s in row['signals']} >= {'dut.ff0.Q','dut.ff0.D','dut.ff0.CLK','dut.ff0.RESET_B','dut.d_source.A','dut.clock_source.A'}
    assert all(cells[r['source']['instance']]['ports'][r['source']['port']]==r['conductor'] for r in row['immediate_boundary_drivers'])


@pytest.mark.parametrize('defect',['missing_driver','duplicate_driver','changed_conductor','missing_port','loop','budget','scalar_budget','wrong_state_model','missing_data_driver'])
def test_no_implicit_alias_or_incomplete_graph_acceptance(monkeypatch,defect):
    cells,modules,roots=fixture(monkeypatch)
    if defect=='missing_driver':del cells['ff0']
    elif defect=='duplicate_driver':cells['duplicate']=copy.deepcopy(cells['ff0'])
    elif defect=='changed_conductor':cells['root']['ports']['A']=r'\u_npu.state0[0] '
    elif defect=='missing_port':del cells['root']['ports']['B']
    elif defect=='loop':cells['root']['ports']['A']=r'\u_npu.probe '
    elif defect=='budget':monkeypatch.setattr(frontier,'MAX_CELLS',2)
    elif defect=='scalar_budget':monkeypatch.setattr(frontier,'MAX_SIGNALS',2)
    elif defect=='wrong_state_model':modules['latch']=copy.deepcopy(modules['sg13g2_dfrbpq_1']);cells['ff0']['type']='latch'
    else:del cells['d_source']
    with pytest.raises(ValueError):frontier.derive_binding('fixture','model','original',roots)


def test_escape_terminator_preserved_and_unknown_driver_not_aliased():
    drivers={r'\foo[0]':[dict(instance='a',port='Q')],r'\foo [0]':[dict(instance='b',port='Q')]}
    assert frontier.unique_driver(drivers,r'\foo[0] ')['instance']=='a'
    assert frontier.unique_driver(drivers,r'\foo [0]')['instance']=='b'
    with pytest.raises(ValueError):frontier.unique_driver(drivers,r'\foo  [0]')


def test_candidate_first_unknown_producer_is_exact(monkeypatch):
    cells,_,roots=fixture(monkeypatch)
    with pytest.raises(ValueError,match='driver'):frontier.derive_binding('fixture','model','candidate',roots)
    monkeypatch.setattr(frontier,'PRIOR',dict(candidate_frontier=[['root','Y',r'\u_npu.probe']]))
    row=frontier.derive_binding('fixture','model','candidate',roots)
    assert row['closed_cone_cells']==['ff0','ff1','root']


def test_instrumentation_reads_exact_fields_without_rewriting_baseline(monkeypatch):
    _,_,roots=fixture(monkeypatch);row=frontier.derive_binding('fixture','model','original',roots)
    baseline='module tb;reg clk;integer cycles;endmodule\n';text=frontier.instrument(baseline,row)
    assert re.sub(r'\n  // NSSOC_NPU_FRONTIER_BEGIN.*?  // NSSOC_NPU_FRONTIER_END\n','',text,flags=re.S)==baseline
    assert not re.search(r'\b(force|release|deposit)\b',text)
    row['signals'][0]['expression']='dut.bad); force dut.q=0;'
    with pytest.raises(ValueError):frontier.instrument(baseline,row)


@pytest.mark.parametrize('defect',['source','body','census','state_count'])
def test_fixed_binding_hash_rejects_different_observation(monkeypatch,defect):
    row=dict(cells={'a':{}},signals=[{}],sequential_boundary=list(range(38)))
    expected=dict(binding_sha256=frontier.digest(row),cells=1,signals=1)
    monkeypatch.setattr(frontier,'lock',lambda:dict(semantic_conductors=[],variants={'original':expected}))
    monkeypatch.setattr(frontier,'derive_binding',lambda *args:row)
    assert frontier.bind('source','model','original')==row
    if defect=='source':row['changed_source']='other'
    elif defect=='body':row['cells']['a']['model']='wrong'
    elif defect=='census':expected['cells']=2
    else:row['sequential_boundary'].pop();expected['binding_sha256']=frontier.digest(row)
    with pytest.raises(ValueError):frontier.bind('source','model','original')


def test_frozen_lock_and_all_twenty_four_ancestors_remain_exact():
    row=frontier.lock()
    assert len(row['semantic_conductors'])==52
    assert [(row['variants'][v]['cells'],row['variants'][v]['signals'],row['variants'][v]['closed_cells']) for v in ('original','candidate')]==[(116,728,70),(156,884,110)]
    assert row['cycle_bound']==3000000 and row['window']==[1569360,1569520]
    assert len(frontier.PINS)==24
    for name,sha in frontier.PINS.items():assert hashlib.sha256((ROOT/name).read_bytes()).hexdigest()==sha


@pytest.mark.parametrize('defect',['wrong_prior','duplicate_semantic','changed_bound','window','cycle_limit','unsafe_semantic','missing_variant'])
def test_lock_rejects_scope_changes(monkeypatch,tmp_path,defect):
    data=frontier.lock();path=tmp_path/frontier.LOCK;path.parent.mkdir(parents=True)
    if defect=='wrong_prior':data['prior']['run_id']+=1
    elif defect=='duplicate_semantic':data['semantic_conductors'][1]=data['semantic_conductors'][0]
    elif defect=='changed_bound':data['bounds']['cells']+=1
    elif defect=='window':data['window'][0]-=1
    elif defect=='cycle_limit':data['cycle_bound']=1600000
    elif defect=='unsafe_semantic':data['semantic_conductors'][0]='); force x=0;'
    else:del data['variants']['candidate']
    path.write_text(json.dumps(data));monkeypatch.setattr(frontier,'ROOT',tmp_path)
    with pytest.raises(ValueError):frontier.lock()


def records(tmp_path):
    log='NPU_FRONTIER_SUMMARY start=2 last=3 width=2 events=2 samples=2 sequence=5 final_cycle=4 armed=1\n'
    lines=['INIT seq=1 cycle=1 realtime_ns=10.001 all=x0',
           'EV seq=2 cycle=2 realtime_ns=15.000 signal=0 prior=0 value=x all=xx',
           'S seq=3 cycle=2 realtime_ns=20.001 all=xx',
           'EV seq=4 cycle=3 realtime_ns=25.000 signal=0 prior=x value=1 all=x1',
           'S seq=5 cycle=3 realtime_ns=30.001 all=x1']
    (tmp_path/'npu-frontier-events.log').write_text('\n'.join(lines)+'\n');return log,lines


def test_static_unknown_is_not_first_new_transition(tmp_path):
    log,_=records(tmp_path);row=frontier.parse(log,tmp_path,2,3,2)
    assert row['initial_static_unknowns']==[dict(signal=1,value='x')]
    assert row['first_new_unknown']['signal']==0 and row['first_new_unknown']['cycle']==2


@pytest.mark.parametrize('defect',['missing','duplicate','bad_sequence','prior','same_value','sample','time','missing_summary','double_summary','limit','width','armed','final_cycle'])
def test_complete_event_history_rejects_omission_or_fabrication(tmp_path,defect):
    log,lines=records(tmp_path)
    if defect=='missing':lines.pop(1)
    elif defect=='duplicate':lines.append(lines[-1])
    elif defect=='bad_sequence':lines[1]=lines[1].replace('seq=2','seq=3')
    elif defect=='prior':lines[1]=lines[1].replace('prior=0','prior=1')
    elif defect=='same_value':lines[1]=lines[1].replace('value=x all=xx','value=0 all=x0')
    elif defect=='sample':lines[2]=lines[2].replace('all=xx','all=x0')
    elif defect=='time':lines[1]=lines[1].replace('15.000','5.000')
    elif defect=='missing_summary':log=''
    elif defect=='double_summary':log+=log
    elif defect=='width':log=log.replace('width=2','width=1025')
    elif defect=='armed':log=log.replace('armed=1','armed=0')
    elif defect=='final_cycle':log=log.replace('final_cycle=4','final_cycle=3')
    (tmp_path/'npu-frontier-events.log').write_text('\n'.join(lines)+'\n')
    with pytest.raises(ValueError):frontier.parse(log,tmp_path,2,3,2,max_events=1 if defect=='limit' else 100000)


def test_monitor_supports_both_exact_widths_without_new_drives(tmp_path):
    compiler=shutil.which('iverilog');runtime=shutil.which('vvp')
    assert compiler and runtime,'Icarus is a required small observer control'
    for width in (728,884):
        directory=tmp_path/str(width);directory.mkdir()
        source=directory/'tiny.v';source.write_text('''`timescale 1ns/1ps
module tiny;reg clk=0;integer cycles=0;reg ['''+str(width-1)+''':0] observed=0;
always #5 clk=~clk;always @(posedge clk)cycles=cycles+1;
nssoc_npu_frontier_event_trace #(.WIDTH('''+str(width)+'''),.START(2),.LAST(4)) observer(.clk_i(clk),.cycle_i({32'b0,cycles}),.signals_i(observed));
initial begin #15.002;observed['''+str(width-1)+''']=1'bx;#10;observed['''+str(width-1)+''']=1;#30;$finish;end
endmodule
''')
        cc=subprocess.run([compiler,'-g2005-sv','-s','tiny','-o',str(directory/'tiny.vvp'),str(source),str(ROOT/frontier.MONITOR)],capture_output=True,text=True)
        assert cc.returncode==0,cc.stderr
        run=subprocess.run([runtime,'-i',str(directory/'tiny.vvp'),'+npu_frontier_dir='+str(directory)],capture_output=True,text=True)
        assert run.returncode==0,run.stdout+run.stderr
        row=frontier.parse(run.stdout,directory,2,4,width)
        assert row['first_new_unknown']['signal']==width-1 and row['events']==2


def test_workflow_preserves_history_hidden_source_and_original_boot_scope():
    text=(ROOT/'.github/workflows/timing-npu-frontier-trace.yml').read_text()
    assert 'fetch-depth: 0' in text and text.count('include-hidden-files: true')==2
    assert 'variant: [original, candidate]' in text and 'cancel-in-progress: false' in text
    assert 'timeout-minutes: 360' in text and 'GH_TOKEN: ${{ github.token }}' in text
    assert 'run_cloud_npu_frontier_trace.py prepare' in text and 'run_cloud_npu_frontier_trace.py run' in text
    code=(ROOT/'scripts/run_cloud_npu_frontier_trace.py').read_text()
    assert "command.count('-DTIMEOUT_CYCLES=3000000')==1" in code
    assert "for key in ('GH_TOKEN','GITHUB_TOKEN','PYTHONPATH','PYTHONHOME'):env.pop(key,None)" in code
