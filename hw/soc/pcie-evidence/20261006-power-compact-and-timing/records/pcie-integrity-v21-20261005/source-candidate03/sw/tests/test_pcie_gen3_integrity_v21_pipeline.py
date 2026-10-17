# SPDX-FileCopyrightText: 2026 Hasan Melih Akbulut
# SPDX-License-Identifier: Apache-2.0
"""Actual sequential descriptor snippets versus a separately expressed queue model.

This component relation permits arbitrary old state and literal X/Z payload;
whole-framer public traffic remains a separate test. No general cycle miter.
"""
from pathlib import Path
import runpy
import shutil
import subprocess
import pytest

ROOT=Path(__file__).resolve().parents[2]
GEN=ROOT/'scripts/generate_pcie_integrity_pipeline_v21.py'
DUT=ROOT/'hw/soc/rtl/pcie/soc_pcie_gen3_framer_rx_integrity_v21.v'
FIELDS=('data','keep','sop','eop','dllp','sequence')
WIDTHS=(128,16,16,16,16,48)
FAULTS=('no_fault_clear','invert_has_data','overwrite_full','metadata_shift','drop_simultaneous_capture','premature_end','block_empty_pop','skip_payload_copy','duplicate_output')


def test_exact_v17_inverse_and_single_writers():
 g=runpy.run_path(str(GEN));s=DUT.read_text()
 assert s==g['candidate']() and g['original'](s)==g['SOURCE'].read_text()
 for field in FIELDS:
  assert s.count('retire_'+field+'<=')==2
 assert s.count('retire_valid<=')==5
 assert s.count('retire_has_data<=')==5
 assert 'wire retire=enabled && active_o && committed!=0 && retire_room;' in s
 assert 'read_keep' not in g['RETIRE_CONTROL']


def component(fault=None):
 g=runpy.run_path(str(GEN));s=DUT.read_text()
 for k in ('DECLARATIONS','RETIRE_CONTROL','PAYLOAD_WRITER','NEW_RETIRE'):
  assert s.count(g[k])==1
 # These priority/body fragments are extracted verbatim from the whole DUT.
 clear='retire_valid<=0;retire_has_data<=0;'
 assert s.count(clear)==3
 outputreset='output_valid<=0;output_data<=0;output_keep<=0;output_sop<=0;output_eop<=0;output_dllp<=0;output_sequence<=0;'
 assert s.count(outputreset)==1
 normal='if(!output_valid || ready_i) output_valid<=0;'
 endtest='if(ending && read_ptr==write_ptr && !retire_valid && (!output_valid || ready_i)) begin'
 assert s.count(normal)==s.count(endtest)==1
 text='''module component;
 reg clk_i=0,rst_ni=1,flush_i,stream_start_i,stream_abort_i,active_o,fault_now,ready_i,ending;
 reg [6:0] committed,read_ptr,write_ptr;reg [2:0] read_count;
 reg [127:0] read_data;reg [15:0] read_keep,read_sop,read_eop,read_dllp;reg [47:0] read_sequence;
 reg output_valid;reg [127:0] output_data;reg [15:0] output_keep,output_sop,output_eop,output_dllp;reg [47:0] output_sequence;
 reg stream_end_o;
 wire enabled=rst_ni && !flush_i && !stream_start_i && !stream_abort_i;
'''+g['DECLARATIONS']+g['RETIRE_CONTROL']+g['PAYLOAD_WRITER']+'''
 always @(posedge clk_i or negedge rst_ni) begin
 if(!rst_ni) begin
 '''+clear+outputreset+'''read_ptr<=0;stream_end_o<=0;active_o<=0;
 end else begin
 stream_end_o<=0;
 if(flush_i || stream_start_i) begin
 '''+clear+'''output_valid<=0;read_ptr<=0;active_o<=stream_start_i && !flush_i;
 end else if((stream_abort_i && active_o) || fault_now) begin
 '''+clear+'''output_valid<=0;read_ptr<=0;active_o<=0;
 end else if(active_o) begin
 '''+normal+g['NEW_RETIRE']+endtest+'''
 stream_end_o<=1;active_o<=0;output_valid<=0;
 end
 end
 end
 end
'''
 if fault:
  edits={
   'no_fault_clear':('end else if((stream_abort_i && active_o) || fault_now) begin\n '+clear,'end else if((stream_abort_i && active_o) || fault_now) begin\n retire_has_data<=0;'),
   'invert_has_data':('if(read_keep!=0) retire_has_data<=1;','if(read_keep==0) retire_has_data<=1;'),
   'overwrite_full':('wire retire_room=!retire_valid || retire_pop;','wire retire_room=1;'),
   'metadata_shift':('output_sequence<=retire_sequence;','output_sequence<={retire_sequence[35:0],retire_sequence[47:36]};'),
   'drop_simultaneous_capture':('read_ptr<=read_ptr+read_count;retire_valid<=1;','read_ptr<=read_ptr+read_count;retire_valid<=!retire_pop;'),
   'premature_end':('&& !retire_valid &&','&&'),
   'block_empty_pop':('(!retire_has_data || !output_valid || ready_i)','(!output_valid || ready_i)'),
   'skip_payload_copy':('retire_data<=read_data;','retire_data<=retire_data;'),
   'duplicate_output':('if(!output_valid || ready_i) output_valid<=0;','if(1\'b0) output_valid<=0;'),
  }
  a,b=edits[fault];assert text.count(a)==1,(fault,a,text.count(a));text=text.replace(a,b)
 return text


BENCH=r'''
 integer trial,k,clears,simultaneous,emptyheld,fullheld,ends,wraps,literals;
 reg ev,eh,ov,ea,ee,cap,pop,can_take,nonempty;
 reg [6:0] rp;
 reg [239:0] ep,op,new_payload;
 task check;
 begin
 // A queue owns at most one descriptor. Empty head consumes no public space.
 // Compute from old states before the edge; use no DUT availability wires.
 can_take=(!retire_valid) || (!retire_has_data) || (!output_valid) || ready_i;
 cap=(rst_ni && !flush_i && !stream_start_i && !stream_abort_i && active_o && committed!=0 && can_take);
 pop=(rst_ni && !flush_i && !stream_start_i && !stream_abort_i && active_o && retire_valid && ((!retire_has_data) || !output_valid || ready_i));
 ev=retire_valid;eh=retire_has_data;ov=output_valid;ea=active_o;ee=0;rp=read_ptr;
 ep={retire_data,retire_keep,retire_sop,retire_eop,retire_dllp,retire_sequence};
 op={output_data,output_keep,output_sop,output_eop,output_dllp,output_sequence};
 new_payload={read_data,read_keep,read_sop,read_eop,read_dllp,read_sequence};
 nonempty=0;if(read_keep!=0) nonempty=1;
 if(!rst_ni) begin ev=0;eh=0;ov=0;ea=0;rp=0;ep=0;op=0;end
 else begin
  if(cap) ep=new_payload;
  if(flush_i || stream_start_i) begin ev=0;eh=0;ov=0;ea=stream_start_i&&!flush_i;rp=0;clears=clears+1;end
  else if((stream_abort_i && active_o) || fault_now) begin ev=0;eh=0;ov=0;ea=0;rp=0;clears=clears+1;end
  else if(active_o) begin
   if(ready_i) ov=0;
   if(pop) begin ev=0;if(retire_has_data) begin ov=1;op={retire_data,retire_keep,retire_sop,retire_eop,retire_dllp,retire_sequence};end end
   if(cap) begin ev=1;eh=nonempty;rp=read_ptr+read_count;end
   if(ending && read_ptr==write_ptr && !retire_valid && (!output_valid || ready_i)) begin ee=1;ea=0;ov=0;end
   if(cap&&pop) simultaneous=simultaneous+1;
   if(pop&&!retire_has_data&&output_valid&&!ready_i) emptyheld=emptyheld+1;
   if(!cap&&retire_valid&&retire_has_data&&output_valid&&!ready_i) fullheld=fullheld+1;
   if(cap && rp<read_ptr) wraps=wraps+1;
   if(ee) ends=ends+1;
  end
 end
 #1;clk_i=1;#1;
 if({retire_valid,retire_has_data,output_valid,active_o,stream_end_o,read_ptr} !== {ev,eh,ov,ea,ee,rp}) $fatal(1,"PIPELINE_QUEUE_CONTROL trial=%0d",trial);
 if({retire_data,retire_keep,retire_sop,retire_eop,retire_dllp,retire_sequence} !== ep) $fatal(1,"PIPELINE_ATOMIC_CAPTURE trial=%0d",trial);
 if({output_data,output_keep,output_sop,output_eop,output_dllp,output_sequence} !== op) $fatal(1,"PIPELINE_OLD_PAYLOAD_TRANSFER trial=%0d",trial);
 clk_i=0;#1;
 end endtask
 task seed;
 begin
 clk_i=0;rst_ni=1;
 {flush_i,stream_start_i,stream_abort_i,active_o,fault_now,ready_i,retire_valid,retire_has_data,output_valid}=trial[8:0];
 committed=trial[9]?7'd4:0;read_count=(trial%4)+1;read_ptr=127;write_ptr=127;ending=trial[10];
 read_data=128'h123456789abcdef04211223344556677;read_keep=trial[11]?16'hffff:0;
 read_sop=16'h1248;read_eop=16'h8421;read_dllp=16'h4218;read_sequence=48'habcdef123456;
 retire_data=128'hf00df00d11223344fedcba9876543210;retire_keep=16'h55aa;retire_sop=16'h0842;retire_eop=16'h2480;retire_dllp=16'h8001;retire_sequence=48'h321654987abc;
 output_data=128'h88887777666655554444333322221111;output_keep=16'h1234;output_sop=16'h4321;output_eop=16'h8888;output_dllp=16'h3333;output_sequence=48'hdeadbeef0908;stream_end_o=0;
 end endtask
 initial begin
 clears=0;simultaneous=0;emptyheld=0;fullheld=0;ends=0;wraps=0;literals=0;
 for(trial=0;trial<4096;trial=trial+1) begin seed;check;end
 // Every literal field is independently copied on capture and old-head pop.
 for(k=0;k<12;k=k+1) begin
 trial=0;seed;active_o=1;ready_i=1;retire_valid=1;retire_has_data=1;output_valid=1;committed=4;read_keep=16'hffff;
 case(k)
 0:begin read_data[1]=1'bx;retire_data[2]=1'bx;end
 1:begin read_data[1]=1'bz;retire_data[2]=1'bz;end
 2:begin read_keep[1]=1'bx;retire_keep[2]=1'bx;end
 3:begin read_keep[1]=1'bz;retire_keep[2]=1'bz;end
 4:begin read_sop[1]=1'bx;retire_sop[2]=1'bx;end
 5:begin read_sop[1]=1'bz;retire_sop[2]=1'bz;end
 6:begin read_eop[1]=1'bx;retire_eop[2]=1'bx;end
 7:begin read_eop[1]=1'bz;retire_eop[2]=1'bz;end
 8:begin read_dllp[1]=1'bx;retire_dllp[2]=1'bx;end
 9:begin read_dllp[1]=1'bz;retire_dllp[2]=1'bz;end
 10:begin read_sequence[1]=1'bx;retire_sequence[2]=1'bx;end
 11:begin read_sequence[1]=1'bz;retire_sequence[2]=1'bz;end
 endcase
 check;literals=literals+1;
 end
 for(k=0;k<2;k=k+1) begin trial=0;seed;active_o=1;committed=4;read_keep=0;read_keep[0]=k?1'bz:1'bx;check;literals=literals+1;end
 // Reset also dominates an owned descriptor, output, and apparent capture.
 trial=511;seed;rst_ni=0;#1;check;
 if(clears==0||simultaneous==0||emptyheld==0||fullheld==0||ends==0||wraps==0||literals!=14) $fatal(1,"PIPELINE_COVERAGE");
 $display("PIPELINE_QUEUE_PASS cases=4096 literal=%0d simultaneous=%0d emptyheld=%0d fullheld=%0d ends=%0d wraps=%0d",literals,simultaneous,emptyheld,fullheld,ends,wraps);
 $finish;
 end
endmodule
'''


def simulate(tmp_path,fault=None):
 p=tmp_path/'literal.v';p.write_text(component(fault)+BENCH)
 assert shutil.which('iverilog') and shutil.which('vvp')
 with (tmp_path/'compile.log').open('w') as log:
  r=subprocess.run(['iverilog','-g2012','-s','component','-o',str(tmp_path/'literal.vvp'),str(p)],stdout=log,stderr=subprocess.STDOUT)
 assert r.returncode==0,(tmp_path/'compile.log').read_text()
 with (tmp_path/'simulation.log').open('w') as log:r=subprocess.run(['vvp',str(tmp_path/'literal.vvp')],stdout=log,stderr=subprocess.STDOUT)
 return r,(tmp_path/'simulation.log').read_text()


def test_actual_sequential_descriptor_queue_literal(tmp_path):
 r,s=simulate(tmp_path);assert r.returncode==0 and 'PIPELINE_QUEUE_PASS cases=4096 literal=14' in s,s


@pytest.mark.parametrize('fault',FAULTS)
def test_actual_descriptor_faults_rejected(tmp_path,fault):
 r,s=simulate(tmp_path,fault);assert r.returncode!=0 and any(x in s for x in ('PIPELINE_QUEUE_CONTROL','PIPELINE_ATOMIC_CAPTURE','PIPELINE_OLD_PAYLOAD_TRANSFER')),s
