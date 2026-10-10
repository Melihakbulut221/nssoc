# SPDX-FileCopyrightText: 2026 Hasan Melih Akbulut
# SPDX-License-Identifier: Apache-2.0
"""Fail-closed native EVQ observer bindings and complete event capture."""
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
import run_cloud_npu_evq_trace as evq


def fixture(monkeypatch):
    def module(ins,outs,sequential=False):
        return dict(input=ins,output=outs,fields=ins+outs,sequential=sequential,body='input '+','.join(ins)+';output '+','.join(outs)+';')
    modules={'sg13g2_dfrbpq_1':module(['D','CLK','RESET_B'],['Q'],True),
        'sg13g2_nor2_1':module(['A','B'],['Y']),'sg13g2_xor2_1':module(['A','B'],['X']),
        'sg13g2_xnor2_1':module(['A','B'],['Y']),'mux4':module(['A0','A1','A2','A3','S0','S1'],['X']),
        'buf':module(['A'],['X'])}
    cells={}
    def add(n,t,ports):cells[n]=dict(type=t,ports=ports,source=json.dumps([t,ports],sort_keys=True));return n
    def ff(n,q,d='external_d',reset='rst'):return add(n,'sg13g2_dfrbpq_1',dict(Q=q,D=d,CLK='clk',RESET_B=reset))
    f=evq.EVQ
    for slot in range(4):
        for bit in range(16):ff(f'mem_{slot}_{bit}',f+f'mem[{slot}] [{bit}]',reset="1'h1")
        ff(f'par_{slot}',f+f'u_par.bits [{slot}]',reset="1'h1")
    ff('idx0',f+'rd_idx [0]');ff('idx1',f+'rd_idx [1]')
    leaves=[]
    for bit in range(16):
        net='head'+str(bit);leaves.append(net)
        add('mux'+str(bit),'mux4',{**{f'A{s}':f+f'mem[{s}] [{bit}]' for s in range(4)},'S0':f+'rd_idx [0]','S1':f+'rd_idx [1]','X':net})
    add('par_mux','mux4',{**{f'A{s}':f+f'u_par.bits [{s}]' for s in range(4)},'S0':f+'rd_idx [0]','S1':f+'rd_idx [1]','X':f+'head_par'})
    leaves.append(f+'head_par')
    while len(leaves)>1:
        a,b=leaves.pop(0),leaves.pop(0);n='parity'+str(len(leaves));out=n+'_out';add(n,'sg13g2_xor2_1',dict(A=a,B=b,X=out));leaves.append(out)
    ff('eligible','not_ok');add('pass','sg13g2_nor2_1',dict(A='not_ok',B=leaves[0],Y=f+'rd_pass'))
    ff('valid_a',f+'u_rdv_a.bits',f+'rd_pass');ff('valid_b',f+'rdv_b',f+'rd_pass')
    ff('old_state','old_state_q');ff('oh_a',r'\u_npu.u_node0.u_ohv_a.bits');ff('oh_b',r'\u_npu.u_node0.oh_valid_b')
    add('clk','buf',dict(A='clk_i',X='clk'));add('rst','buf',dict(A='rst_i',X='rst'))
    historical=dict(state_binding=dict(cells={'old_state':cells['old_state']}))
    monkeypatch.setattr(evq.previous,'bind',lambda *args:copy.deepcopy(historical))
    monkeypatch.setattr(evq,'native_modules',lambda model:modules)
    monkeypatch.setattr(evq,'native_cells',lambda netlist:cells)
    return cells,modules


def test_exact_read_valid_parity_and_memory_bit_identity(monkeypatch):
    cells,_=fixture(monkeypatch);b=evq.derive_binding('fixture','models','original')
    assert [r['bit'] for r in b['head_data']]==list(range(16))
    assert all(r['storage']==[(s,r['bit']) for s in range(4)] for r in b['head_data'])
    assert b['roots']['u_rdv_a.bits']==dict(instance='valid_a',port='Q')
    assert b['roots']['rdv_b']==dict(instance='valid_b',port='Q')
    assert set(b['closed_cone_cells'])<=set(b['cells'])
    assert {x['name'] for x in b['semantic_observations']}=={'rd_ok','not_rd_ok','rd_pass','head_bad','head_par'}|{f'selected_head_data[{i}]' for i in range(16)}
    assert b['signals'][-1]['expression']=='~(dut.pass.A)'
    assert any(x['conductor']=='external_d' for x in b['frontier'])
    assert all(cells[x['sink']]['ports'][x['port']]=="1'h1" for x in b['immediate_clock_reset_drivers'] if x.get('constant'))


@pytest.mark.parametrize('fault',['rail_d','rail_type','missing_rail','duplicate_driver','parity_shape','parity_polarity','data_bit','data_slot','missing_head','loop','constant_reset','clock_driver','cell_budget','signal_budget'])
def test_binding_rejects_unwitnessed_or_wrong_equations(monkeypatch,fault):
    cells,mods=fixture(monkeypatch)
    if fault=='rail_d':cells['valid_a']['ports']['D']='not_ok'
    elif fault=='rail_type':cells['valid_a']['type']='buf'
    elif fault=='missing_rail':del cells['valid_b']
    elif fault=='duplicate_driver':cells['duplicate']=copy.deepcopy(cells['valid_a'])
    elif fault=='parity_shape':cells['pass']['ports']['B']='head0'
    elif fault=='parity_polarity':
        c=cells['parity0'];c['type']='sg13g2_xnor2_1';c['ports']['Y']=c['ports'].pop('X')
    elif fault=='data_bit':cells['mux0']['ports']['A0']=evq.EVQ+'mem[0] [1]'
    elif fault=='data_slot':cells['mux0']['ports']['A0']=evq.EVQ+'mem[1] [0]'
    elif fault=='missing_head':del cells['mem_0_0']
    elif fault=='loop':cells['mux0']['ports']['A0']='head0'
    elif fault=='constant_reset':cells['mem_0_0']['ports']['RESET_B']="1'h0"
    elif fault=='clock_driver':del cells['clk']
    elif fault=='cell_budget':monkeypatch.setattr(evq,'MAX_CELLS',2)
    else:monkeypatch.setattr(evq,'MAX_SIGNALS',2)
    with pytest.raises(ValueError):evq.derive_binding('fixture','models','original')


def test_read_only_instrumentation_and_exact_derived_bit(monkeypatch):
    fixture(monkeypatch);b=evq.derive_binding('fixture','models','original');base='module tb;reg clk;integer cycles;endmodule\n'
    observed=evq.instrument(base,b)
    assert re.sub(r'\n  // NSSOC_NPU_EVQ_BEGIN.*?  // NSSOC_NPU_EVQ_END\n','',observed,flags=re.S)==base
    assert 'force' not in observed and 'release' not in observed
    b['signals'][-1]['expression']='dut.pass.A'
    with pytest.raises(ValueError):evq.instrument(base,b)


@pytest.mark.parametrize('fault',['missing','expression','role','instance','derived_pin','duplicate_index'])
def test_unbound_observer_inputs_rejected(monkeypatch,fault):
    fixture(monkeypatch);b=evq.derive_binding('f','m','original')
    if fault=='missing':del b['cells'][b['signals'][0]['instance']]
    elif fault=='expression':b['signals'][0]['expression']='dut.other.Q'
    elif fault=='role':b['signals'][0]['role']='unsound'
    elif fault=='instance':b['signals'][-1]['instance']='oh_a'
    elif fault=='derived_pin':b['signals'][-1]['field']='B'
    else:b['signals'][-1]['index']=0
    with pytest.raises(ValueError):evq.instrument('module tb;endmodule',b)


def test_frozen_inputs_and_all_twenty_nine_ancestors():
    row=evq.lock();assert len(evq.PINS)==29
    for name,sha in evq.PINS.items():assert hashlib.sha256((ROOT/name).read_bytes()).hexdigest()==sha
    assert [(row['variants'][v]['cells'],row['variants'][v]['signals']) for v in ('original','candidate')]==[(209,1624),(210,1628)]
    assert row['prior']['run_id']==37158099088 and row['cycle_bound']==3000000


@pytest.mark.parametrize('fault',['prior','bounds','cycles','window','variant','producer'])
def test_lock_scope_failure(monkeypatch,tmp_path,fault):
    row=evq.lock()
    if fault=='prior':row['prior']['run_id']+=1
    elif fault=='bounds':row['bounds']['signals']+=1
    elif fault=='cycles':row['cycle_bound']=1600000
    elif fault=='window':row['window'][0]-=1
    elif fault=='variant':del row['variants']['candidate']
    else:row['producer']['source_commit']='wrong'
    p=tmp_path/evq.LOCK;p.parent.mkdir(parents=True);p.write_text(json.dumps(row));monkeypatch.setattr(evq,'ROOT',tmp_path)
    with pytest.raises(ValueError):evq.lock()


@pytest.mark.parametrize('fault',['hash','cells','signals','sequential'])
def test_binding_census_and_hash_fail_closed(monkeypatch,fault):
    fixture(monkeypatch);b=evq.derive_binding('f','m','original')
    expected=dict(binding_sha256=evq.digest(b),cells=len(b['cells']),signals=len(b['signals']),sequential_boundaries=len(b['sequential_boundary']))
    monkeypatch.setattr(evq,'lock',lambda:dict(variants={'original':expected}));assert evq.bind('f','m','original')==b
    if fault=='hash':expected['binding_sha256']='0'*64
    else:expected[{'cells':'cells','signals':'signals','sequential':'sequential_boundaries'}[fault]]+=1
    with pytest.raises(ValueError):evq.bind('f','m','original')


def records(tmp_path):
    log='NPU_EVQ_SUMMARY start=2 last=3 width=2 events=2 samples=2 sequence=5 final_cycle=4 armed=1\n'
    lines=['INIT seq=1 cycle=1 realtime_ns=10.001 all=x0',
           'EV seq=2 cycle=2 realtime_ns=15.000 signal=0 prior=0 value=x all=xx',
           'S seq=3 cycle=2 realtime_ns=20.001 all=xx',
           'EV seq=4 cycle=3 realtime_ns=25.000 signal=0 prior=x value=1 all=x1',
           'S seq=5 cycle=3 realtime_ns=30.001 all=x1']
    (tmp_path/'npu-evq-events.log').write_text('\n'.join(lines)+'\n');return log,lines


def test_static_unknown_is_not_first_new_transition(tmp_path):
    log,_=records(tmp_path);row=evq.parse(log,tmp_path,2,3,2)
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
    elif defect=='width':log=log.replace('width=2','width=2049')
    elif defect=='armed':log=log.replace('armed=1','armed=0')
    elif defect=='final_cycle':log=log.replace('final_cycle=4','final_cycle=3')
    (tmp_path/'npu-evq-events.log').write_text('\n'.join(lines)+'\n')
    with pytest.raises(ValueError):evq.parse(log,tmp_path,2,3,2,max_events=1 if defect=='limit' else 100000)


def test_monitor_supports_both_exact_widths_without_new_drives(tmp_path):
    compiler=shutil.which('iverilog');runtime=shutil.which('vvp')
    assert compiler and runtime,'Icarus is a required small observer control'
    for width in (1624,1628):
        directory=tmp_path/str(width);directory.mkdir()
        source=directory/'tiny.v';source.write_text('''`timescale 1ns/1ps
module tiny;reg clk=0;integer cycles=0;reg ['''+str(width-1)+''':0] observed=0;
always #5 clk=~clk;always @(posedge clk)cycles=cycles+1;
nssoc_npu_evq_event_trace #(.WIDTH('''+str(width)+'''),.START(2),.LAST(4)) observer(.clk_i(clk),.cycle_i({32'b0,cycles}),.signals_i(observed));
initial begin #15.002;observed['''+str(width-1)+''']=1'bx;#10;observed['''+str(width-1)+''']=1;#30;$finish;end
endmodule
''')
        cc=subprocess.run([compiler,'-g2005-sv','-s','tiny','-o',str(directory/'tiny.vvp'),str(source),str(ROOT/evq.MONITOR)],capture_output=True,text=True)
        assert cc.returncode==0,cc.stderr
        run=subprocess.run([runtime,'-i',str(directory/'tiny.vvp'),'+npu_evq_dir='+str(directory)],capture_output=True,text=True)
        assert run.returncode==0,run.stdout+run.stderr
        row=evq.parse(run.stdout,directory,2,4,width)
        assert row['first_new_unknown']['signal']==width-1 and row['events']==2


def test_reconvergent_native_callback_and_live_snapshot_are_distinct(tmp_path):
    """A real buffer/XOR pulse reproduces the failed full-chip parser contract."""
    compiler=shutil.which('iverilog');runtime=shutil.which('vvp')
    assert compiler and runtime
    monitor="""nssoc_npu_evq_event_trace #(.WIDTH(4),.START(2),.LAST(4)) obs(
 .clk_i(clk),.cycle_i({32'b0,cycles}),.signals_i({y,b,a}));
"""
    source="""`timescale 1ns/1ps
module tiny;
reg clk=0;integer cycles=0;reg a=0;wire [1:0] b;wire y;
assign b[0]=a;buf(b[1],b[0]);xor(y,a,b[1]);
always #5 clk=~clk;always @(posedge clk)cycles=cycles+1;
always @(negedge clk) #0.002 $display("SIGNATURE cycle=%0d y=%b b=%b a=%b",cycles,y,b,a);
"""+monitor+"""initial begin #15.002;a=1;#10;a=0;#30;$finish;end
endmodule
"""
    outputs={}
    for name,text in [('observed',source),('baseline',source.replace(monitor,''))]:
        path=tmp_path/(name+'.v');path.write_text(text)
        cc=subprocess.run([compiler,'-g2005-sv','-s','tiny','-o',str(tmp_path/(name+'.vvp')),
            str(path),str(ROOT/evq.MONITOR)],capture_output=True,text=True)
        assert cc.returncode==0,cc.stderr
        rr=subprocess.run([runtime,'-i',str(tmp_path/(name+'.vvp')),
            '+npu_evq_dir='+str(tmp_path)],capture_output=True,text=True)
        assert rr.returncode==0,rr.stdout+rr.stderr
        outputs[name]=rr.stdout
    assert re.findall(r'^SIGNATURE.*$',outputs['observed'],re.M)==re.findall(
        r'^SIGNATURE.*$',outputs['baseline'],re.M)
    row=evq.parse(outputs['observed'],tmp_path,2,4,4)
    assert row['events']==10 and row['samples']==3
    assert len(row['live_snapshot_disagreements'])==2
    assert all(x['signal']==3 and x['callback_value']=='1' and x['live_value']=='0'
        for x in row['live_snapshot_disagreements'])
    assert not row['new_unknown_transitions']
    # A delayed live vector must not license a broken scalar chain or a lost
    # pulse. Corrupt actual native records, not a second implementation oracle.
    path=tmp_path/'npu-evq-events.log';raw=path.read_text()
    for original,replacement in [
        ('signal=3 prior=0 value=1','signal=3 prior=1 value=1'),
        ('signal=3 prior=1 value=0','signal=3 prior=0 value=1'),
        ('cycle=2 realtime_ns=20.001 all=0111','cycle=2 realtime_ns=20.001 all=1111'),
    ]:
        assert original in raw
        path.write_text(raw.replace(original,replacement,1))
        with pytest.raises(ValueError):evq.parse(outputs['observed'],tmp_path,2,4,4)
    path.write_text(raw)


def test_workflow_preserves_history_hidden_source_and_original_boot_scope():
    text=(ROOT/'.github/workflows/timing-npu-evq-trace.yml').read_text()
    assert 'fetch-depth: 0' in text and text.count('include-hidden-files: true')==2
    assert 'variant: [original, candidate]' in text and 'cancel-in-progress: false' in text
    assert 'timeout-minutes: 360' in text and 'GH_TOKEN: ${{ github.token }}' in text
    assert 'run_cloud_npu_evq_trace.py prepare' in text and 'run_cloud_npu_evq_trace.py run' in text
    code=(ROOT/'scripts/run_cloud_npu_evq_trace.py').read_text()
    assert "command.count('-DTIMEOUT_CYCLES=3000000')==1" in code
    assert "for key in ('GH_TOKEN','GITHUB_TOKEN','PYTHONPATH','PYTHONHOME'):env.pop(key,None)" in code


@pytest.mark.parametrize('fault',['inventory','frozen_source','own_source','captured_source'])
def test_complete_method_recheck_rejects_drift(tmp_path,monkeypatch,fault):
    source=tmp_path/'source';output=tmp_path/'output';source.mkdir();(output/'methods').mkdir(parents=True)
    for name in ('old.py','own.py'):
        (source/name).write_text(name);(output/'methods'/name).write_text(name)
    monkeypatch.setattr(evq,'ROOT',source);monkeypatch.setattr(evq,'PINS',{'old.py':hashlib.sha256(b'old.py').hexdigest()});monkeypatch.setattr(evq,'OWN',('own.py',))
    row={'methods':{n:evq.q.pin(source/n) for n in ('old.py','own.py')}};evq.verify_methods(output,row)
    if fault=='inventory':del row['methods']['old.py']
    elif fault=='frozen_source':(source/'old.py').write_text('changed')
    elif fault=='own_source':(source/'own.py').write_text('changed')
    else:(output/'methods/own.py').write_text('changed')
    with pytest.raises(ValueError):evq.verify_methods(output,row)


def test_z_transitions_are_not_hidden_by_binary_or_hex_conversion(tmp_path):
    log,lines=records(tmp_path);lines=[x.replace('x','z') for x in lines]
    (tmp_path/'npu-evq-events.log').write_text('\n'.join(lines)+'\n');r=evq.parse(log,tmp_path,2,3,2)
    assert r['initial_static_unknowns']==[dict(signal=1,value='z')]
    assert r['first_new_unknown']['value']=='z' and r['first_new_unknown']['signal']==0


def test_native_head_control_is_gated_in_real_cloud_prepare():
    text=(ROOT/'scripts/run_cloud_npu_evq_trace.py').read_text()
    assert "row['head_controls']=head_controls(" in text
    assert "'Mapped head/parity labels differ' in log" in text
    assert "log.count('EVQ_HEAD_NATIVE_PASS checks=1296')==1" in text
    assert text.count('verify_methods(output,row)')>=4
    assert 'previous.MAX_' not in text and 'previous.ROOT=' not in text
