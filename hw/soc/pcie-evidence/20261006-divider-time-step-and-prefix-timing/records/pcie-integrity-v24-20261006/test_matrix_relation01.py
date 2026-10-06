# SPDX-FileCopyrightText: 2026 Hasan Melih Akbulut
# SPDX-License-Identifier: Apache-2.0
"""Actual finite matrix-alphabet relation against frozen V23 Verilog helpers."""
from pathlib import Path
import hashlib,runpy
import pytest
B=Path(__file__).resolve().parent;R=B.parents[3]
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
 candidate=(B/'prefix_candidate01.vh').read_text()
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
