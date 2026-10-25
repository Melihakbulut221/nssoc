# SPDX-FileCopyrightText: 2026 Hasan Melih Akbulut
# SPDX-License-Identifier: Apache-2.0
"""Exhaust actual old/new source fragments over every count/keep combination."""
import hashlib
import json
from pathlib import Path
import shutil
import subprocess

import pytest

ROOT=Path(__file__).resolve().parents[2]
OLD=ROOT/'hw/soc/rtl/pcie/soc_pcie_gen3_dllp_consumer_v2.v'
NEW=ROOT/'hw/soc/rtl/pcie/soc_pcie_gen3_dllp_consumer_v4.v'


def block(text, old):
    start=text.index('           for(byte_lane=0;' if old else '           case(local_nr)')
    return text[start:text.index('           if(le!=0) begin',start)]


def module(name,body,shared=''):
    return f'''module {name}(input wire [12:0] count,input wire [3:0] lk,
input wire [31:0] lw,initial_raw,input wire initial_error,
output reg [12:0] local_nr,output reg [31:0] local_nraw,output reg local_entry_error);
wire [127:0] body_data_i={{4{{lw}}}};wire [15:0] body_keep_i={{4{{lk}}}};
{shared}
integer byte_lane,destination,lane;
reg [2:0] byte_count,byte_prefix;
reg [13:0] count_sum;
always @* begin
 local_nr=count;local_nraw=initial_raw;local_entry_error=initial_error;
 byte_count=0;byte_prefix=0;count_sum=0;lane=0;
{body}
end
endmodule
'''


BENCH='''module test;
reg [12:0] count;reg [3:0] keep;reg [31:0] word_value,initial_raw;reg initial_error;
wire [12:0] old_count,new_count;wire [31:0] old_raw,new_raw;wire old_error,new_error;
old_word a(count,keep,word_value,initial_raw,initial_error,old_count,old_raw,old_error);
new_word b(count,keep,word_value,initial_raw,initial_error,new_count,new_raw,new_error);
integer i,k,s,vectors;
initial begin
 vectors=0;
 for(s=0;s<2;s=s+1) for(i=0;i<8192;i=i+1) for(k=0;k<16;k=k+1) begin
  count=i;keep=k;word_value=s?32'h10ff80a7:32'h67452301;
  initial_raw=s?32'h76543210:32'hfedcba98;initial_error=s;
  #1;
  if({new_count,new_raw,new_error} !== {old_count,old_raw,old_error})
   $fatal(1,"SOURCE_WORD_MISMATCH count=%d keep=%d seed=%d",i,k,s);
  vectors=vectors+1;
 end
 $display("SOURCE_WORD_EXHAUSTIVE_PASS vectors=%d",vectors);$finish;
end
endmodule
'''


def pin(path):
    return {'bytes':path.stat().st_size,'sha256':hashlib.sha256(path.read_bytes()).hexdigest()}


def run(tmp,mutation=None):
    old,new=OLD.read_text(),NEW.read_text()
    old_block,new_block=block(old,True),block(new,False)
    shared=new[new.index(' // Shared input compaction:'):new.index(' // Each physical owner entry')]
    if mutation:
        before,after=mutation
        assert (new_block+shared).count(before)==1
        new_block=new_block.replace(before,after);shared=shared.replace(before,after)
    src=tmp/'test.v';src.write_text(module('old_word',old_block)+module('new_word',new_block,shared)+BENCH)
    compiler=shutil.which('iverilog');runtime=shutil.which('vvp')
    assert compiler and runtime
    binary=tmp/'sim.vvp'
    command=[compiler,'-g2012','-s','test','-o',str(binary),str(src)]
    compiled=subprocess.run(command,capture_output=True,text=True)
    (tmp/'compile.log').write_text(compiled.stdout+compiled.stderr)
    assert compiled.returncode==0
    simulated=subprocess.run([runtime,str(binary)],capture_output=True,text=True)
    (tmp/'simulation.log').write_text(simulated.stdout+simulated.stderr)
    r={'sources':{str(p):pin(p) for p in (OLD,NEW,Path(__file__))},'runtime':{str(Path(p).resolve()):pin(Path(p).resolve()) for p in (compiler,runtime)},'mutation':mutation,'returncode':simulated.returncode,'outputs':{p.name:pin(p) for p in tmp.iterdir() if p.is_file()},'scope':'Actual literal source fragment arithmetic only; no full module formal proof/native cells/timing.'}
    (tmp/'result.json').write_text(json.dumps(r,indent=2)+'\n')
    return simulated


def test_actual_all_count_mask_and_sticky_error_source_fragments(tmp_path):
    p=run(tmp_path)
    assert p.returncode==0 and 'SOURCE_WORD_EXHAUSTIVE_PASS vectors=     262144' in p.stdout


@pytest.mark.parametrize('before,after',[
    ('if(count_sum[13]) local_entry_error=1;',"if(1'b0) local_entry_error=1;"),
    ("13'd8191: begin","13'd8188: begin"),
    ("+{2'b0,input_keep[3]}","+3'b0"),
],ids=['overflow_lost','prefix_modulo_lost','fourth_byte_lost'])
def test_actual_non_equivalent_arithmetic_rejected(tmp_path,before,after):
    p=run(tmp_path,(before,after))
    assert p.returncode!=0 and 'SOURCE_WORD_MISMATCH' in p.stdout
