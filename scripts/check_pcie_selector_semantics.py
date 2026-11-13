# SPDX-License-Identifier: Apache-2.0
"""Source-bound guards: raw/normalized/candidate HDL simulation and mutual SAT."""
import json,pathlib,re,subprocess,sys
from pcie_reference_x import normalize
out=pathlib.Path('out');out.mkdir(exist_ok=True)
rawdir,gatepath=map(pathlib.Path,sys.argv[1:]);records=[]
for kind,name,pattern,n,w,aw,phase_count in [
 ('lcrc','soc_pcie_lcrc_tx.v',r'wire\s*\[7:0\]\s*cursor_data_byte\s*=([^;]+);',8,32,4,16),
 ('dllp','soc_pcie_rx_credit.v',r'assign\s+out_data_o\s*=([^;]+);',6,8,6,4)]:
 raw=(rawdir/name).read_text();texts=[raw,normalize(name,raw),(gatepath/name).read_text()]
 expr=[]
 for text in texts:
  m=re.findall(pattern,text);assert len(m)==1;expr.append(m[0])
 if kind=='lcrc':
  ports='input [255:0] data,input [3:0] cursor_word,input [1:0] cursor_byte'
  declarations='localparam integer MAX_TLP_DWORDS=8; wire [31:0] words[0:7]; genvar k; generate for(k=0;k<8;k=k+1) begin assign words[k]=data[32*k +:32]; end endgenerate'
  args='data,idx,phase';control_decl='reg [1:0] phase;';set_phase='for(k=0;k<2;k=k+1) phase[k]=four((j>>(2*k))&3);'
 else:
  ports='input [47:0] data,input [5:0] output_index,input select_dllp,input [7:0] tlp_byte'
  declarations='wire [7:0] dllp[0:5]; genvar k; generate for(k=0;k<6;k=k+1) begin assign dllp[k]=data[8*k +:8]; end endgenerate'
  args='data,idx,sel,tlp_byte';control_decl='reg sel; reg [7:0] tlp_byte;';set_phase="sel=four(j); tlp_byte=(p==4 ? 8'hxx : p==5 ? 8'hzz : 8'ha5^p);"
 def module(label,e):return f'module {label}({ports},output [7:0] value);\n{declarations}\nassign value={e};\nendmodule\n'
 circuit=out/(kind+'-selector.v');circuit.write_text(module('original',expr[0])+module('gold',expr[1])+module('gate',expr[2]))
 results=[]
 for direction,pair in [('forward','gold gate'),('reverse','gate gold')]:
  for fault in [False,True]:
   path=out/(kind+'-fault.v') if fault else circuit
   if fault:path.write_text(module('gold',expr[1])+module('gate','~('+expr[2]+')'))
   ys=f'read_verilog -sv {path}; proc; memory_map; opt -keepdc; equiv_make {pair} equiv; hierarchy -top equiv; equiv_simple -undef; equiv_induct -undef -seq 4; equiv_status -assert;'
   x=subprocess.run(['yosys','-p',ys],capture_output=True,text=True,timeout=90);log=x.stdout+x.stderr
   (out/f'{kind}-{direction}-{fault}.log').write_text(log)
   accepted=x.returncode==0 and 'Equivalence successfully proven!' in log
   rejected=x.returncode!=0 and 'unproven $equiv cells' in log and 'ERROR: Found' in log
   results.append(dict(direction=direction,fault=fault,accepted=accepted,expected_rejection=rejected))
 count=8*(4**aw)*phase_count
 tb=f"""
module tb;
localparam integer N={n},W={w},AW={aw};
reg [N*W-1:0] data; reg [AW-1:0] idx; {control_decl}
wire [7:0] a,b,c;
original o({args},a); gold g({args},b); gate q({args},c);
integer p,i,j,k,t,checks;
function four;input integer n;begin case(n) 0:four=0;1:four=1;2:four=1'bx;3:four=1'bz;endcase end endfunction
initial begin
 checks=0;
 for(p=0;p<8;p=p+1) begin
  for(t=0;t<N;t=t+1) case(p)
   0:data[W*t +:W]=0;
   1:data[W*t +:W]=32'hffffffff;
   2:data[W*t +:W]=32'h12345678 ^ (t*32'h01020408);
   3:data[W*t +:W]=32'h89abcdef ^ (t*32'h08040201);
   4:data[W*t +:W]='hx;
   5:data[W*t +:W]='hz;
   6:data[W*t +:W]={{{{(W/4){{4'bx10z}}}}}};
   7:data[W*t +:W]={{{{(W/4){{4'bz01x}}}}}};
  endcase
  for(i=0;i<{4**aw};i=i+1) for(j=0;j<{phase_count};j=j+1) begin
   for(k=0;k<AW;k=k+1) idx[k]=four((i>>(2*k))&3);
   {set_phase}
   #1;
   if(a !== b || b !== c) $fatal(1,"selector mismatch p=%0d idx=%b raw=%b normalized=%b candidate=%b",p,idx,a,b,c);
   checks=checks+1;
  end
 end
 if(checks!={count}) $fatal(1,"missing cases");
 $display("RAW_NORMALIZED_CANDIDATE_PASS %0d",checks);$finish;
end
endmodule
"""
 tbpath=out/(kind+'-tb.v');tbpath.write_text(tb)
 subprocess.run(['iverilog','-g2012','-s','tb','-o',str(out/(kind+'.vvp')),str(circuit),str(tbpath)],check=True,timeout=90)
 sim=subprocess.run(['vvp',str(out/(kind+'.vvp'))],capture_output=True,text=True,timeout=90)
 (out/(kind+'-sim.log')).write_text(sim.stdout+sim.stderr)
 simulation_passed=sim.returncode==0 and f'RAW_NORMALIZED_CANDIDATE_PASS {count}' in sim.stdout
 # Inject a fault only in candidate; raw and normalized references remain intact.
 faultpath=out/(kind+'-sim-fault.v');faultpath.write_text(module('original',expr[0])+module('gold',expr[1])+module('gate','~('+expr[2]+')'))
 subprocess.run(['iverilog','-g2012','-s','tb','-o',str(out/(kind+'-fault.vvp')),str(faultpath),str(tbpath)],check=True,timeout=90)
 fault=subprocess.run(['vvp',str(out/(kind+'-fault.vvp'))],capture_output=True,text=True,timeout=90)
 (out/(kind+'-sim-fault.log')).write_text(fault.stdout+fault.stderr)
 fault_rejected=fault.returncode!=0 and 'selector mismatch' in fault.stdout
 formal_ok=all((x['expected_rejection'] and not x['accepted']) if x['fault'] else x['accepted'] for x in results)
 records.append(dict(kind=kind,passed=formal_ok and simulation_passed and fault_rejected,formal_controls=results,source_four_state_cases=count,simulation_passed=simulation_passed,simulation_fault_rejected=fault_rejected))
record=dict(passed=all(x['passed'] for x in records),checks=records,scope='Raw, explicit-out-of-range-X normalized reference, and candidate expressions. Exhaustive binary/X/Z indices and selector controls with eight data patterns; mutual undef SAT compares normalized reference and candidate. This is reference preparation evidence, not full-module acceptance.')
(out/'selector-controls.json').write_text(json.dumps(record,indent=2));print(json.dumps(record),flush=True)
assert record['passed'],'Reference normalization or selector checks failed'
