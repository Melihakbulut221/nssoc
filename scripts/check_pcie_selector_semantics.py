# SPDX-License-Identifier: Apache-2.0
"""Source-bound selector checks: mutual undef SAT + binary/X/Z simulation controls."""
import json,pathlib,re,subprocess,sys
out=pathlib.Path('out');out.mkdir(exist_ok=True)
def expression(p):
 s=pathlib.Path(p).read_text();m=re.findall(r'wire\s*\[7:0\]\s*cursor_data_byte\s*=([^;]+);',s)
 assert len(m)==1;return m[0]
expr=[expression(p) for p in sys.argv[1:]];assert len(expr)==2
prefix="""
module NAME(input [255:0] data, input [3:0] cursor_word, input [1:0] cursor_byte, output [7:0] value);
localparam integer MAX_TLP_DWORDS=8;
wire [31:0] words [0:7];
genvar k; generate for(k=0;k<8;k=k+1) begin assign words[k]=data[32*k +:32]; end endgenerate
assign value=EXPR;
endmodule
"""
def module(name,e):return prefix.replace('NAME',name).replace('EXPR',e)
(out/'selector.v').write_text(module('gold',expr[0])+module('gate',expr[1]))
results=[]
for direction,pair in [('forward','gold gate'),('reverse','gate gold')]:
 for fault in [False,True]:
  path=out/('selector-fault.v' if fault else 'selector.v')
  if fault:path.write_text(module('gold',expr[0])+module('gate','~('+expr[1]+')'))
  ys=f'read_verilog -sv {path}; proc; memory_map; opt -keepdc; equiv_make {pair} equiv; hierarchy -top equiv; equiv_simple -undef; equiv_induct -undef -seq 4; equiv_status -assert;'
  run=subprocess.run(['yosys','-p',ys],capture_output=True,text=True,timeout=90)
  log=run.stdout+run.stderr;(out/f'selector-{direction}-{fault}.log').write_text(log)
  accepted=run.returncode==0 and 'Equivalence successfully proven!' in log
  expected_rejection=(run.returncode!=0 and 'unproven $equiv cells' in log and 'ERROR: Found' in log)
  results.append(dict(direction=direction,fault=fault,accepted=accepted,expected_rejection=expected_rejection))
tb="""
module tb;
reg [255:0] data; reg [3:0] cursor_word; reg [1:0] cursor_byte;
wire [7:0] a,b;
gold g(data,cursor_word,cursor_byte,a); gate n(data,cursor_word,cursor_byte,b);
integer p,i,j,k,w,checks;
function four; input integer n; begin case(n) 0:four=0;1:four=1;2:four=1'bx;3:four=1'bz;endcase end endfunction
initial begin
 checks=0;
 for(p=0;p<8;p=p+1) begin
  for(w=0;w<8;w=w+1) begin
   case(p)
    0:data[32*w +:32]=32'h00000000;
    1:data[32*w +:32]=32'hffffffff;
    2:data[32*w +:32]=32'h12345678 ^ (w*32'h01020408);
    3:data[32*w +:32]=32'h89abcdef ^ (w*32'h08040201);
    4:data[32*w +:32]=32'hxxxxxxxx;
    5:data[32*w +:32]=32'hzzzzzzzz;
    6:data[32*w +:32]=32'hx5z3a7f0;
    7:data[32*w +:32]=32'h0f7a3z5x;
   endcase
  end
  for(i=0;i<256;i=i+1) for(j=0;j<16;j=j+1) begin
   for(k=0;k<4;k=k+1) cursor_word[k]=four((i>>(2*k)) & 3);
   for(k=0;k<2;k=k+1) cursor_byte[k]=four((j>>(2*k)) & 3);
   #1;
   if(a !== b) $fatal(1,"selector mismatch pattern=%0d word=%b byte=%b old=%b new=%b",p,cursor_word,cursor_byte,a,b);
   checks=checks+1;
  end
 end
 if(checks!=32768) $fatal(1,"missing cases");
 $display("SELECTOR_FOUR_STATE_CASES_PASS %0d",checks);$finish;
end
endmodule
"""
(out/'selector-tb.v').write_text(tb)
subprocess.run(['iverilog','-g2012','-s','tb','-o',str(out/'selector.vvp'),str(out/'selector.v'),str(out/'selector-tb.v')],check=True,timeout=90)
x=subprocess.run(['vvp',str(out/'selector.vvp')],capture_output=True,text=True,timeout=90)
(out/'selector-simulation.log').write_text(x.stdout+x.stderr);assert x.returncode==0 and 'SELECTOR_FOUR_STATE_CASES_PASS 32768' in x.stdout
# The simulator must also reject a known output fault, rather than merely exit zero.
subprocess.run(['iverilog','-g2012','-s','tb','-o',str(out/'selector-fault.vvp'),str(out/'selector-fault.v'),str(out/'selector-tb.v')],check=True,timeout=90)
bad=subprocess.run(['vvp',str(out/'selector-fault.vvp')],capture_output=True,text=True,timeout=90)
(out/'selector-simulation-fault.log').write_text(bad.stdout+bad.stderr);assert bad.returncode!=0 and 'selector mismatch' in bad.stdout
controls_ok=all((x['expected_rejection'] and not x['accepted']) if x['fault'] else x['accepted'] for x in results)
record=dict(passed=controls_ok,formal_controls=results,four_state_cases=32768,simulation_fault_rejected=True,scope='Actual old/new cursor_data_byte expressions at MAX_TLP_DWORDS=8. Mutual undef formal comparison covers arbitrary binary data/control; Icarus sweeps all binary/X/Z index combinations with eight representative data patterns. Not a full-module or all-parameter proof.')
(out/'selector-controls.json').write_text(json.dumps(record,indent=2));print(json.dumps(record),flush=True)

assert controls_ok, 'Mutual selector equivalence or explicit fault rejection remains unproven'
