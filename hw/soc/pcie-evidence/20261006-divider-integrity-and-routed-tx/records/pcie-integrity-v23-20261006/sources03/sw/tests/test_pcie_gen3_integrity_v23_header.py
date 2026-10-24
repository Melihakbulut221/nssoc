# SPDX-FileCopyrightText: 2026 Hasan Melih Akbulut
# SPDX-License-Identifier: Apache-2.0
"""Actual adjacent relation and exact full-source inverse, not state equivalence."""
from pathlib import Path
import runpy
import pytest
ROOT=Path(__file__).resolve().parents[2]
RTL=ROOT/'hw/soc/rtl/pcie'
GEN=runpy.run_path(str(ROOT/'scripts/generate_pcie_integrity_header_v23.py'))
SIM=runpy.run_path(str(ROOT/'sw/tests/test_pcie_gen3_integrity_v3_crc.py'))['simulate']


def test_exact_generated_inverse_and_wrapper_bridge():
    new=(RTL/'soc_pcie_gen3_framer_rx_integrity_v23.v').read_text()
    assert new==GEN['candidate']()
    assert GEN['inverse'](new)==GEN['SOURCE'].read_text()
    for name in ('hw/soc/rtl/pcie/soc_pcie_gen3_continuous_rx_integrity_v22.v',
                 'hw/soc/tb/cocotb/Makefile.soc_pcie_gen3_continuous_rx_integrity_v22',
                 'scripts/check_pcie_gen3_continuous_rx_integrity_v22.py'):
        assert (ROOT/name.replace('_v22','_v23')).read_text().replace('_v23','_v22')==(ROOT/name).read_text()
    old=(ROOT/'hw/soc/tb/cocotb/test_soc_pcie_gen3_continuous_rx_integrity_v22.py').read_text()
    bench=(ROOT/'hw/soc/tb/cocotb/test_soc_pcie_gen3_continuous_rx_integrity_v23.py').read_text()
    assert bench.replace('_v23','_v22').replace('V23_','V22_').startswith(old)
    assert new[new.index(' // BEGIN V6 SHARED OLD VERDICT READS'):new.index(' // END V5 SLOT VERDICT CACHE')]==GEN['SOURCE'].read_text()[GEN['SOURCE'].read_text().index(' // BEGIN V6 SHARED OLD VERDICT READS'):GEN['SOURCE'].read_text().index(' // END V5 SLOT VERDICT CACHE')]


def functions():
    text=(RTL/'soc_pcie_gen3_framer_rx_integrity_v23.v').read_text()
    start=text.index(' function automatic [31:0] predecode_word;')
    end=text.index(' endfunction',start)+len(' endfunction')
    a=text.index(' function automatic [15:0] adjacent_header_relation;')
    b=text.index(' endfunction',a)+len(' endfunction')
    return text[start:end]+'\n'+text[a:b]


@pytest.mark.parametrize('fault',[None,'wrong_previous','current_tail','omit_format','equal_length','wrong_expected_bit'])
def test_actual_adjacent_relation_literal_and_binary(tmp_path,fault):
    body=functions()
    edits={
        'wrong_previous':('predecessor=decoded[(index-1)*32+19+:13];','predecessor=decoded[index*32+19+:13];'),
        'current_tail':('if(index==0) predecessor=previous_encoded;','if(index==0) predecessor=decoded[15*32+19+:13];'),
        'omit_format':('adjacent_header_relation[index]=decoded[index*32+18] ||','adjacent_header_relation[index]=1\'b0 ||'),
        'equal_length':('(predecessor!=decoded[index*32+5+:13]);','(predecessor==decoded[index*32+5+:13]);'),
        'wrong_expected_bit':('(predecessor!=decoded[index*32+5+:13]);','(predecessor!=decoded[index*32+4+:13]);'),
    }
    if fault:
        before,after=edits[fault];assert body.count(before)==1;body=body.replace(before,after)
    bench='''`timescale 1ns/1ps
module tb;
localparam MAX_ENCODED_BYTES=150;
'''+body+'''
reg [511:0] decoded;
reg [31:0] header;
reg [12:0] previous,expected_bytes,payload;
reg [15:0] got;
reg expected_bad;
integer i,j,length,fmt,count,position,n=0,literal=0,binary=0;
task check;
 begin
  // Original scalar header expression, with literal ternary four-state
  // semantics; selected relation must preserve unknown results, not mask them.
  payload=({header[17:16],header[31:24]}==0)?13'd4096:{1'b0,header[17:16],header[31:24],2'b00};
  expected_bytes=13'd18+(header[5]?13'd4:13'd0)+(header[6]?payload:13'd0)+(header[23]?13'd4:13'd0);
  expected_bad=header[7] || (previous!=expected_bytes);
  decoded={16{32'h13f055aa}};
  decoded[position*32+:32]=predecode_word(header);
  if(position>0) decoded[(position-1)*32+19+:13]=previous;
  got=adjacent_header_relation(decoded,previous);
  if(got[position]!==expected_bad)
   $fatal(1,"V23_ADJACENT_LITERAL case=%0d pos=%0d got=%b expected=%b",n,position,got[position],expected_bad);
  n=n+1;
 end
endtask
initial begin
 // Complete MAX150 encoded DWORD lengths5..38, all sixteen relevant
 // Fmt/TD flags and all1024 header payload lengths. Position cycles0..15.
 for(length=5;length<=38;length=length+1)
  for(fmt=0;fmt<16;fmt=fmt+1)
   for(count=0;count<1024;count=count+1) begin
    previous=length*4-2;header=0;
    header[7:5]=fmt[2:0];header[23]=fmt[3];
    header[17:16]=count[9:8];header[31:24]=count[7:0];
    position=n%16;
    check;
    // Independent integer arithmetic checks the predecode expression too.
    if(expected_bytes !== (18+(fmt&1?4:0)+(fmt&2?(count==0?4096:count*4):0)+(fmt&8?4:0)))
      $fatal(1,"V23_HEADER_INTEGER_REFERENCE");
    binary=binary+1;
   end
 // Explicit selected X and Z in every header and predecessor bit at every
 // lane; unselected words stay unrelated. No arbitrary-state DUT claim.
 for(position=0;position<16;position=position+1)
  for(i=0;i<45;i=i+1)
   for(j=0;j<2;j=j+1) begin
    header=32'h01000000;previous=18;
    if(i<32) begin
     if(j==0) header[i]=1'bx;else header[i]=1'bz;
    end else begin
     if(j==0) previous[i-32]=1'bx;else previous[i-32]=1'bz;
    end
    check;literal=literal+1;
   end
 if(binary!=557056 || literal!=1440) $fatal(1,"V23_ADJACENT_LITERAL_COVERAGE");
 $display("PASS_V23_ADJACENT_RELATION binary=%0d literalXZ=%0d",binary,literal);$finish;
end
endmodule
'''
    result,log=SIM(tmp_path,bench)
    if fault:
        assert result.returncode!=0 and 'V23_ADJACENT_LITERAL case=' in log
    else:
        assert result.returncode==0 and 'PASS_V23_ADJACENT_RELATION binary=557056 literalXZ=1440' in log
