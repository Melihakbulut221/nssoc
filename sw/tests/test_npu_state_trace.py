# SPDX-FileCopyrightText: 2026 Hasan Melih Akbulut
# SPDX-License-Identifier: Apache-2.0
"""Source-bound native observation and fail-closed fixed-window controls."""
from pathlib import Path
import hashlib
import re
import shutil
import sys
import tarfile

import pytest

ROOT=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(ROOT/'scripts'))
import run_cloud_npu_state_trace as trace


def model():
    with tarfile.open(ROOT/'docs/evidence/alu-qualification-input-20261002.tar.xz') as archive:
        return archive.extractfile('models/sg13g2_stdcell.v').read().decode()


def source_fixture(variant='candidate'):
    lines=['  wire clk_i;','  wire rst_ni;','  wire input_d;']
    for name,width in trace.old.FIELDS:
        declaration=('\\'+name+' ') if '.' in name else name
        lines.append('  wire '+(f'[{width-1}:0] ' if width>1 else '')+declaration+';')
        if name=='u_npu.ev_state':continue
        for bit in range(width):
            if bit not in trace.old.UNDRIVEN_ALIASES.get(name,[]):
                lines.append('  assign '+declaration+(f'[{bit}]' if width>1 else '')+" = 1'h0;")
    for bit,name in enumerate(trace.CELLS[variant]):
        lines.append(f'  sg13g2_dfrbpq_1 {name} (\n    .Q(\\u_npu.ev_state [{bit}]),\n    .D(input_d),\n    .CLK(clk_i),\n    .RESET_B(rst_ni)\n  );')
    return '\n'.join(lines)


def binding_fixture(monkeypatch,variant='candidate',text=None):
    text=source_fixture(variant) if text is None else text
    monkeypatch.setitem(trace.q.EXPECTED_NETLISTS,variant,hashlib.sha256(text.encode()).hexdigest())
    return trace.bind(text,model(),variant)


@pytest.mark.parametrize('variant',['original','candidate'])
def test_native_model_and_state_q_identity_are_bound(monkeypatch,variant):
    binding=binding_fixture(monkeypatch,variant)
    assert len(binding['signals'])==44
    assert set(binding['cells'])==set(trace.CELLS[variant])
    assert binding['signals'][0]['field']=='D' and binding['signals'][1]['field']=='Q'
    assert binding['signals'][33]['state_bit']==3
    assert 'ihp_dff_r_err' in binding['native_dff_model']


@pytest.mark.parametrize('fault',['missing_cell','wrong_type','swapped_q','missing_reset','extra_pin','duplicate_cell','changed_model','unbound_netlist'])
def test_native_scalar_binding_rejects_inexact_sources(monkeypatch,fault):
    text=source_fixture();std=model()
    if fault=='missing_cell':text=text.replace(trace.CELLS['candidate'][0],'_9_')
    if fault=='wrong_type':text=text.replace('sg13g2_dfrbpq_1','sg13g2_dfrbpq_2',1)
    if fault=='swapped_q':text=text.replace('ev_state [0]','ev_state [9]').replace('ev_state [1]','ev_state [0]').replace('ev_state [9]','ev_state [1]')
    if fault=='missing_reset':text=text.replace('    .RESET_B(rst_ni)\n','')
    if fault=='extra_pin':text=text.replace('.D(input_d),','.D(input_d), .EXTRA(input_d),',1)
    if fault=='duplicate_cell':text+='\n'+text[text.index('  sg13g2_dfrbpq_1'):].split('  );',1)[0]+'  );'
    if fault=='changed_model':std=std.replace('wire int_fwire_IQ','wire changed_IQ',1)
    monkeypatch.setitem(trace.q.EXPECTED_NETLISTS,'candidate',hashlib.sha256(text.encode()).hexdigest())
    if fault=='unbound_netlist':text+='\n// changed'
    with pytest.raises(ValueError):trace.bind(text,std,'candidate')


def test_instrumentation_is_only_read_only_append(monkeypatch):
    b=binding_fixture(monkeypatch);source='module tb; reg clk;integer cycles; endmodule\n'
    new=trace.instrument(source,b)
    assert re.sub(r'\n  // NSSOC_NPU_STATE_TRACE_BEGIN.*?  // NSSOC_NPU_STATE_TRACE_END\n','',new,flags=re.S)==source
    assert '.START(1569360),.LAST(1569520)' in new
    assert not re.search(r'\b(force|release|deposit)\b',new)
    with pytest.raises(ValueError):trace.instrument(new,b)
    b['signals'][0]['expression']='dut.bad); force dut.q=0;'
    with pytest.raises(ValueError):trace.instrument(source,b)


def parser_fixture(tmp_path):
    rows=['EV seq=1 cycle=2 realtime_ns=1.000 signal=0 value=x all=000x',
          'EV seq=2 cycle=2 realtime_ns=1.000 signal=3 value=x all=x00x',
          'S seq=3 cycle=2 realtime_ns=1.001 all=x00x',
          'S seq=4 cycle=3 realtime_ns=2.001 all=0101']
    log='NPU_STATE_TRACE_SUMMARY start=2 last=3 width=4 events=2 samples=2 sequence=4 final_cycle=4\n'
    (tmp_path/'npu-state-events.log').write_text('\n'.join(rows)+'\n')
    return log,rows


def test_scalar_parser_distinguishes_bits_at_same_time_in_observed_order(tmp_path):
    log,_=parser_fixture(tmp_path);r=trace.parse(log,tmp_path,2,3,4)
    assert [(e['signal'],e['value'],e['sequence']) for e in r['unknown_scalar_events']]==[(0,'x',1),(3,'x',2)]


@pytest.mark.parametrize('fault',['summary_missing','summary_duplicate','incomplete_window','missing_record','duplicate_cycle','outside_window','wrong_index','wrong_snapshot','hex_loss','sequence_gap','time_backwards','event_bound'])
def test_scalar_parser_rejects_incomplete_or_lossy_observation(tmp_path,fault):
    log,rows=parser_fixture(tmp_path)
    if fault=='summary_missing':log=''
    if fault=='summary_duplicate':log+=log
    if fault=='incomplete_window':log=log.replace('final_cycle=4','final_cycle=3')
    if fault=='missing_record':rows.pop()
    if fault=='duplicate_cycle':rows[-1]=rows[-1].replace('cycle=3','cycle=2')
    if fault=='outside_window':rows[0]=rows[0].replace('cycle=2','cycle=1')
    if fault=='wrong_index':rows[0]=rows[0].replace('signal=0','signal=4')
    if fault=='wrong_snapshot':rows[0]=rows[0].replace('all=000x','all=0000')
    if fault=='hex_loss':rows[0]=rows[0].replace('all=000x','all=X')
    if fault=='sequence_gap':rows[1]=rows[1].replace('seq=2','seq=4')
    if fault=='time_backwards':rows[1]=rows[1].replace('1.000','0.999')
    (tmp_path/'npu-state-events.log').write_text('\n'.join(rows)+'\n')
    with pytest.raises(ValueError):trace.parse(log,tmp_path,2,3,4,max_events=1 if fault=='event_bound' else trace.MAX_EVENTS)


def test_actual_tiny_scalar_monitor_window_event_order_and_unknown_bits(tmp_path):
    iverilog=shutil.which('iverilog');vvp=shutil.which('vvp');assert iverilog and vvp
    source=tmp_path/'tiny.v'
    source.write_text('''`timescale 1ns/1ps
module tiny;
reg clk=0;integer cycles=0;reg [3:0] data=0;
always #5 clk=~clk;always @(posedge clk) cycles=cycles+1;
nssoc_npu_state_event_trace #(.WIDTH(4),.START(2),.LAST(5)) observer(
.clk_i(clk),.cycle_i({32'b0,cycles}),.signals_i(data));
initial begin #2;data=15;#18;data[0]=1'bx;#0.001;data[3]=1'bx;#1;data=5;#60;$finish;end
endmodule
''')
    c=trace.q.alu.execute([iverilog,'-g2005-sv','-s','tiny','-o',tmp_path/'sim.vvp',source,ROOT/trace.MONITOR],tmp_path,'compile')
    assert c['returncode']==0
    r=trace.q.alu.execute([vvp,'-i',tmp_path/'sim.vvp','+npu_trace_dir='+str(tmp_path)],tmp_path,'run')
    assert r['returncode']==0
    parsed=trace.parse((tmp_path/'run.log').read_text(),tmp_path,2,5,4)
    assert [x['signal'] for x in parsed['unknown_scalar_events']]==[0,3]
    assert parsed['unknown_scalar_events'][0]['realtime_ns']=='20.000'
    assert parsed['unknown_scalar_events'][1]['realtime_ns']=='20.001'
    assert parsed['samples']==4


def test_native_event_bound_cannot_silently_drop_observations(tmp_path):
    iverilog=shutil.which('iverilog');vvp=shutil.which('vvp');assert iverilog and vvp
    source=tmp_path/'tiny.v'
    source.write_text('''`timescale 1ns/1ps
module tiny;reg clk=0;integer cycles=0;reg data=0;
always #5 clk=~clk;always @(posedge clk)cycles=cycles+1;
nssoc_npu_state_event_trace #(.WIDTH(1),.START(2),.LAST(5),.MAX_EVENTS(1)) observer(
.clk_i(clk),.cycle_i({32'b0,cycles}),.signals_i(data));
initial begin #20;data=1;#1;data=0;#60;$finish;end
endmodule
''')
    c=trace.q.alu.execute([iverilog,'-g2005-sv','-s','tiny','-o',tmp_path/'sim.vvp',source,ROOT/trace.MONITOR],tmp_path,'compile')
    assert c['returncode']==0
    r=trace.q.alu.execute([vvp,'-i',tmp_path/'sim.vvp','+npu_trace_dir='+str(tmp_path)],tmp_path,'run')
    assert r['returncode']!=0 and 'Native scalar event bound exhausted' in (tmp_path/'run.log').read_text()
    with pytest.raises(ValueError):trace.parse((tmp_path/'run.log').read_text(),tmp_path,2,5,1,max_events=1)


def test_dependencies_and_old_producer_are_byte_frozen():
    for name,pin in trace.PINS.items():assert trace.q.common.sha(ROOT/name)==pin
    assert trace.q.CYCLES==3000000 and trace.PRIOR['candidate_boot_failed'] is True


def test_full_chip_stays_cloud_only(tmp_path,monkeypatch):
    monkeypatch.delenv('GITHUB_ACTIONS',raising=False)
    with pytest.raises(ValueError,match='cloud-only'):trace.prepare(tmp_path/'out',tmp_path/'work','candidate')
    with pytest.raises(ValueError,match='cloud-only'):trace.run(tmp_path/'out')
