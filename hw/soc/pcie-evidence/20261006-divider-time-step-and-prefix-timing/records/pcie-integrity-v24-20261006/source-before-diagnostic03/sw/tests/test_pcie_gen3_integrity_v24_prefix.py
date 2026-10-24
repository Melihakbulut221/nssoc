# SPDX-FileCopyrightText: 2026 Hasan Melih Akbulut
# SPDX-License-Identifier: Apache-2.0
"""Actual finite matrix-alphabet relation against frozen V23 Verilog helpers."""
from pathlib import Path
import hashlib,runpy
import pytest
R=Path(__file__).resolve().parents[2];B=R/'hw/soc/rtl/pcie'
BASE=R/'hw/soc/rtl/pcie/soc_pcie_gen3_framer_rx_integrity_v23.v'
SIM=runpy.run_path(str(R/'sw/tests/test_pcie_gen3_integrity_v3_crc.py'))['simulate']
def original_functions():
 text=BASE.read_text();assert hashlib.sha256(text.encode()).hexdigest()=='505db8d1daa5c5263a16a3584175bc89a73d1b6e35f16e10b64f1f9f6483dde6'
 out=[]
 for name,width in [('control_transition',63),('control_compose',63),('control_apply',7)]:
  start=text.index(f' function automatic [{width}:0] {name};');end=text.index(' endfunction',start)+len(' endfunction');out.append(text[start:end])
 return '\n'.join(out)
@pytest.mark.parametrize('fault',[None,'wrong_initial_column','drop_bad_carry','drop_middle_exit','wrong_suffix'])
def test_actual_finite_matrix_alphabet(tmp_path,fault):
 text=(B/'soc_pcie_gen3_framer_rx_integrity_v24.v').read_text()
 candidate=text[text.index('function automatic [95:0] token_prefix_context;'):text.index(' function automatic [383:0] block_token_context;')]
 edits={
 'wrong_initial_column':('token_prefix_context[16+d]=t0[d*8+3];','token_prefix_context[16+d]=t0[d*8+2];'),
 'drop_bad_carry':('({8{c0[7]}}&8\'h80)|({8{c0[1]}}&c1);','8\'h00|({8{c0[1]}}&c1);'),
 'drop_middle_exit':('({8{c0[1]&c1[2]}}&context_bits[88+:8])','8\'h00'),
 'wrong_suffix':('token_prefix_context[80+d]=suffix2[d*8+2];','token_prefix_context[80+d]=t1[d*8+2];')}
 if fault:
  a,b=edits[fault];assert candidate.count(a)==1;candidate=candidate.replace(a,b)
 bench='''`timescale 1ns/1ps
module tb;
localparam TOKEN=2'd0,TLP=2'd1,LOOK=2'd2,DLLP=2'd3;
@ORIGINAL@
@CANDIDATE@
function automatic sym;
 input integer n;
 begin case(n) 0:sym=1'b0;1:sym=1'b1;2:sym=1'bx;default:sym=1'bz;endcase end
endfunction
function automatic [7:0] column;
 input [63:0] matrix;input integer s;
 integer d;
 begin for(d=0;d<8;d=d+1) column[d]=matrix[d*8+s];end
endfunction
reg [63:0] tokens[0:1023],matrices[0:16383];
reg [63:0] m,t,expected,p2,p3;
reg [7:0] carries[0:15],c,initials[0:15],mode,ref_mode,dut_mode;
reg [95:0] context_bits;
reg [1:0] state_value;
integer nt,nc,ni,nm,n,flags,carry_flags,k,found,i0,i1,i2,c0,c1,c2,st,w;
integer check_count,alphabet_vectors,full_matrix_checks;
reg [63:0] m0,m1,m2;
initial begin
 nt=0;nc=0;ni=0;nm=0;check_count=0;alphabet_vectors=0;full_matrix_checks=0;
 // Every literal0/1/X/Z token and carry classification reaches the actual
 // frozen indexed-onehot function; enumerate its full finite matrix alphabet.
 for(flags=0;flags<1024;flags=flags+1) begin
  t=control_transition(sym(flags%4),sym((flags/4)%4),sym((flags/16)%4),sym((flags/64)%4),sym((flags/256)%4),1'b0,1'b0);
  if(^t===1'bx) $fatal(1,"V24_UNEXPECTED_UNKNOWN_TOKEN_MATRIX");
  found=0;for(k=0;k<nt;k=k+1) if(tokens[k]===t) found=1;
  if(!found) begin tokens[nt]=t;nt=nt+1;end
  for(carry_flags=0;carry_flags<16;carry_flags=carry_flags+1) begin
   m=control_transition(sym(flags%4),sym((flags/4)%4),sym((flags/16)%4),sym((flags/64)%4),sym((flags/256)%4),sym(carry_flags%4),sym((carry_flags/4)%4));
   if(^m===1'bx) $fatal(1,"V24_UNEXPECTED_UNKNOWN_MATRIX");
   c=column(m,1);if((c&8'h79)!==0) $fatal(1,"V24_UNEXPECTED_CARRIED_DESTINATION");
   expected=t;for(k=0;k<8;k=k+1) expected[k*8+1]=c[k];
   if(expected!==m) $fatal(1,"V24_NONCARRY_COLUMN_DEPENDENCE");
   for(k=0;k<8;k=k+1) if(k!=1 && m[1*8+k]!==0) $fatal(1,"V24_NONCARRY_ENTERS_MODE1");
   found=0;for(k=0;k<nc;k=k+1) if(carries[k]===c) found=1;
   if(!found) begin carries[nc]=c;nc=nc+1;end
   found=0;for(k=0;k<nm;k=k+1) if(matrices[k]===m) found=1;
   if(!found) begin matrices[nm]=m;nm=nm+1;end
   alphabet_vectors=alphabet_vectors+1;
  end
 end
 for(n=0;n<16;n=n+1) begin
  state_value={sym(n/4),sym(n%4)};
  mode={4'b0,state_value==DLLP,state_value==LOOK,state_value==TLP,state_value==TOKEN};
  found=0;for(k=0;k<ni;k=k+1) if(initials[k]===mode) found=1;
  if(!found) begin initials[ni]=mode;ni=ni+1;end
 end
 if(alphabet_vectors!=16384 || nc!=4 || ni!=9 || nm!=nt*nc) $fatal(1,"V24_INCOMPLETE_ALPHABET");
 $display("V24_ALPHABET vectors=%0d token_matrices=%0d carry_columns=%0d initial_modes=%0d complete_matrices=%0d",alphabet_vectors,nt,nc,ni,nm);
 // Enumerate every ordered three-word token-matrix and independent carry
 // column. This is a superset of physically consistent remaining counters.
 for(i0=0;i0<nt;i0=i0+1) for(i1=0;i1<nt;i1=i1+1) for(i2=0;i2<nt;i2=i2+1) begin
  context_bits=token_prefix_context(tokens[i0],tokens[i1],tokens[i2]);
  for(c0=0;c0<nc;c0=c0+1) for(c1=0;c1<nc;c1=c1+1) for(c2=0;c2<nc;c2=c2+1) begin
   m0=tokens[i0];m1=tokens[i1];m2=tokens[i2];
   for(k=0;k<8;k=k+1) begin m0[k*8+1]=carries[c0][k];m1[k*8+1]=carries[c1][k];m2[k*8+1]=carries[c2][k];end
   p2=control_compose(m1,m0);p3=control_compose(m2,p2);full_matrix_checks=full_matrix_checks+1;
   for(st=0;st<ni;st=st+1) for(w=1;w<=3;w=w+1) begin
    case(w) 1:expected=m0;2:expected=p2;default:expected=p3;endcase
    ref_mode=control_apply(expected,initials[st]);
    dut_mode=context_prefix_modes(context_bits,initials[st],carries[c0],carries[c1],carries[c2],w);
    if(ref_mode!==dut_mode) $fatal(1,"V24_PREFIX_RELATION word=%0d tokens=%0d/%0d/%0d carries=%0d/%0d/%0d initial=%b expected=%b actual=%b",w,i0,i1,i2,c0,c1,c2,initials[st],ref_mode,dut_mode);
    check_count=check_count+1;
   end
  end
 end
 if(full_matrix_checks!=nt*nt*nt*nc*nc*nc || check_count!=full_matrix_checks*ni*3) $fatal(1,"V24_CENSUS");
 $display("V24_PREFIX_RELATION_PASS matrices=%0d comparisons=%0d",full_matrix_checks,check_count);$finish;
end
endmodule
'''.replace('@ORIGINAL@',original_functions()).replace('@CANDIDATE@',candidate)
 result,log=SIM(tmp_path,bench)
 if fault:assert result.returncode!=0 and 'V24_PREFIX_RELATION word=' in log,log
 else:assert result.returncode==0 and 'V24_PREFIX_RELATION_PASS' in log,log


def test_exact_generated_inverse_and_wrapper_bridge():
 GEN=runpy.run_path(str(R/'scripts/generate_pcie_integrity_prefix_v24.py'))
 new=(B/'soc_pcie_gen3_framer_rx_integrity_v24.v').read_text()
 assert new==GEN['candidate']() and GEN['inverse'](new)==GEN['SOURCE'].read_text()
 for name in ('hw/soc/rtl/pcie/soc_pcie_gen3_continuous_rx_integrity_v23.v',
              'hw/soc/tb/cocotb/Makefile.soc_pcie_gen3_continuous_rx_integrity_v23',
              'scripts/check_pcie_gen3_continuous_rx_integrity_v23.py'):
  assert (R/name.replace('_v23','_v24')).read_text().replace('_v24','_v23')==(R/name).read_text()
 old=(R/'hw/soc/tb/cocotb/test_soc_pcie_gen3_continuous_rx_integrity_v23.py').read_text()
 bench=(R/'hw/soc/tb/cocotb/test_soc_pcie_gen3_continuous_rx_integrity_v24.py').read_text()
 assert bench.replace('v24','v23').replace('V24','V23')==old


@pytest.mark.parametrize('fault',[None,'premature_eds','wrong_word_offset'])
def test_actual_block_context_pack_and_eds(tmp_path,fault):
 text=(B/'soc_pcie_gen3_framer_rx_integrity_v24.v').read_text()
 body=text[text.index('function automatic [95:0] token_prefix_context;'):text.index(' reg [383:0] current_token_context,next_token_context;')]
 if fault:
  edits={
   'premature_eds':("control_transition(word0[0],word0[1],word0[2],1'b0,word0[4],1'b0,1'b0)","control_transition(word0[0],word0[1],word0[2],word0[3],word0[4],1'b0,1'b0)"),
   'wrong_word_offset':('word1=decoded[(beat*4+1)*32+:32];','word1=decoded[(beat*4+0)*32+:32];')}
  before,after=edits[fault];assert body.count(before)==1;body=body.replace(before,after)
 bench='''`timescale 1ns/1ps
module tb;
@ORIGINAL@
@BODY@
reg [511:0] decoded;
reg [383:0] actual,expected;
reg [63:0] transition[0:2],prefix,suffix;
reg [31:0] w;
integer position,flags,bitno,symbol,j,beat,wordno,source,destination,n=0;
task check;
 begin
  expected=0;
  for(beat=0;beat<4;beat=beat+1) begin
   for(wordno=0;wordno<3;wordno=wordno+1) begin
    w=decoded[(beat*4+wordno)*32+:32];
    transition[wordno]=control_transition(w[0],w[1],w[2],1'b0,w[4],1'b0,1'b0);
   end
   for(wordno=0;wordno<3;wordno=wordno+1) begin
    if(wordno==0) prefix=transition[0];
    else prefix=control_compose(transition[wordno],prefix);
    for(source=0;source<3;source=source+1)
     for(destination=0;destination<8;destination=destination+1)
      expected[beat*96+wordno*24+source*8+destination]=prefix[destination*8+(source==0?0:source+1)];
   end
   suffix=control_compose(transition[2],transition[1]);
   for(destination=0;destination<8;destination=destination+1) begin
    expected[beat*96+72+destination]=transition[1][destination*8+2];
    expected[beat*96+80+destination]=suffix[destination*8+2];
    expected[beat*96+88+destination]=transition[2][destination*8+2];
   end
  end
  actual=block_token_context(decoded);
  if(actual!==expected) $fatal(1,"V24_BLOCK_CONTEXT_PACK case=%0d position=%0d",n,position);
  n=n+1;
 end
endtask
task unrelated;
 begin
  for(j=0;j<16;j=j+1) decoded[j*32+:32]=32'h5a001a00|((j*7+3)%32);
 end
endtask
initial begin
 // Zero raw DWORD decodes to IDL. Every retained prefix column and suffix
 // therefore maps to TOKEN; exact twelve-byte filler cannot be allzero.
 decoded={16{32'h4}};actual=block_token_context(decoded);
 if(actual!=={4{96'h010101010101010101010101}}) $fatal(1,"V24_ZERO_PREDECODE_FILLER");
 for(position=0;position<16;position=position+1) begin
  for(flags=0;flags<32;flags=flags+1) begin
   unrelated;decoded[position*32+:5]=flags;check;
  end
  for(bitno=0;bitno<5;bitno=bitno+1) for(symbol=0;symbol<2;symbol=symbol+1) begin
   unrelated;decoded[position*32+:5]=5'b10011;
   if(symbol==0) decoded[position*32+bitno]=1'bx;else decoded[position*32+bitno]=1'bz;
   check;
  end
 end
 if(n!=672) $fatal(1,"V24_BLOCK_PACK_CENSUS");
 $display("PASS_V24_BLOCK_CONTEXT_PACK vectors=%0d positions=16 binary=512 XZ=160 filler=exact",n);$finish;
end
endmodule
'''.replace('@ORIGINAL@',original_functions()).replace('@BODY@',body)
 result,log=SIM(tmp_path,bench)
 if fault:assert result.returncode!=0 and 'V24_BLOCK_CONTEXT_PACK case=' in log,log
 else:assert result.returncode==0 and 'PASS_V24_BLOCK_CONTEXT_PACK vectors=672' in log,log
