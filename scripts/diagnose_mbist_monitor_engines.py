import os,json,subprocess,hashlib
from pathlib import Path
assert os.environ.get('GITHUB_ACTIONS')=='true'
out=Path('mbist-monitor-probe');out.mkdir()
original=Path('hw/soc/tb/mapped_mbist_boot_monitor_original.v')
fixed=Path('hw/soc/tb/mapped_mbist_boot_monitor.v')
assert hashlib.sha256(original.read_bytes()).hexdigest()=='c117d03640b2cc18be2390e050f8c7f85fdf14c694738355c6fbcc42f9650a0d'
expected=original.read_text().replace('output integer busy_cycles_o','output reg signed [31:0] busy_cycles_o').replace('output integer done_cycle_o','output reg signed [31:0] done_cycle_o')
unknown_expr="((busy_i !== 1'b0) && (busy_i !== 1'b1)) || ((done_i !== 1'b0) && (done_i !== 1'b1)) || ((failed_i !== 1'b0) && (failed_i !== 1'b1)) || ((eth_done_i[0] !== 1'b0) && (eth_done_i[0] !== 1'b1)) || ((eth_done_i[1] !== 1'b0) && (eth_done_i[1] !== 1'b1)) || ((eth_failed_i[0] !== 1'b0) && (eth_failed_i[0] !== 1'b1)) || ((eth_failed_i[1] !== 1'b0) && (eth_failed_i[1] !== 1'b1))"
expected=expected.replace("(^{busy_i,done_i,failed_i,eth_done_i,eth_failed_i}) === 1'bx",unknown_expr)
assert fixed.read_text()==expected
bench="`timescale 1ns/1ps\nmodule tb;\nreg clk=0; always #5 clk=~clk;\nreg rst=0,busy=0,done=0,failed=0;\nreg [1:0] edone=0,efailed=0;\nwire passed; wire [31:0] busy_count,done_cycle;\nmapped_mbist_boot_monitor dut(clk,rst,busy,done,failed,edone,efailed,passed,busy_count,done_cycle);\ninteger n;\ninitial begin\n for(n=0;n<210;n=n+1) begin\n  @(posedge clk);\n  rst<=n>=4;\n  busy<=n>=4 && n<164;\n  done<=n>=164;\n  edone<=n>=164 ? 2'b11 : 2'b00;\n  @(negedge clk); #1;\n  $display(\"TRACE n=%0d busy_count=%0d done_cycle=%0d passed=%b cycles=%0d seen=%b\",n,busy_count,done_cycle,passed,dut.cycles,dut.done_seen);\n end\n $finish;\nend\nendmodule\n"
engines=[('iverilog',[]),('cvc',[]),('cvc-interp',['+interp']),('cvc-ogate',['-Ogate']),('cvc-o',['-O'])]
def run(label,source,body,engine,flags):
 folder=out/label;folder.mkdir();v=folder/'tb.v';v.write_text(body);exe=folder/'sim'
 cmd=(['iverilog','-g2012','-s','tb','-o',str(exe)]if engine=='iverilog'else[str(Path('cvc-source/build64/cvc64').resolve()),'-sv',*flags,'-o',str(exe)])+[str(v),str(source)]
 if engine=='cvc-interp':
  idx=cmd.index('-o');del cmd[idx:idx+2]
  p=subprocess.run(cmd,stdout=subprocess.PIPE,stderr=subprocess.STDOUT,timeout=60)
  (folder/'compile.log').write_bytes(p.stdout)
 else:
  p=subprocess.run(cmd,stdout=subprocess.PIPE,stderr=subprocess.STDOUT,timeout=60)
  (folder/'compile.log').write_bytes(p.stdout);assert p.returncode==0,p.stdout[-2000:]
  assert exe.is_file()
  p=subprocess.run((['vvp','-n',str(exe)]if engine=='iverilog'else[str(exe)]),stdout=subprocess.PIPE,stderr=subprocess.STDOUT,timeout=60)
 (folder/'run.log').write_bytes(p.stdout)
 text=p.stdout.decode();lines=[l for l in text.splitlines()if l.startswith('TRACE ')]
 return dict(label=label,returncode=p.returncode,rows=len(lines),last=lines[-1]if lines else None,run_sha256=hashlib.sha256(p.stdout).hexdigest()),lines,text
result=dict(source_head=os.environ['GITHUB_SHA'],original_sha256=hashlib.sha256(original.read_bytes()).hexdigest(),fixed_sha256=hashlib.sha256(fixed.read_bytes()).hexdigest(),accepted=False,cases=[],controls=[])
try:
 reference=None
 for variant,source in [('original',original),('fixed',fixed)]:
  for engine,flags in engines:
   row,lines,text=run(variant+'-'+engine,source,bench,engine,flags)
   if reference is None:
    assert len(lines)==210 and row['returncode']==0
    reference=lines
    last=dict(t.split('=')for t in lines[-1].split()[1:])
    assert int(last['busy_count'])==128 and int(last['done_cycle'])==161 and last['passed']=='1'
   row['identical_to_original_iverilog']=lines==reference
   row['mismatch_count']=sum(a!=b for a,b in zip(reference,lines))+abs(len(reference)-len(lines))
   result['cases'].append(row)
 # Independent acceptance-rejection controls; original assertion messages retained.
 controls=[
  ('failed',"failed<=n>=64;","MBIST_MONITOR native SRAM test failure"),
  ('unknown',"failed<=n>=64 ? 1'bx : 1'b0;","MBIST_MONITOR unknown mapped status"),
  ('dropped',"done<=n>=164 && n<190;","MBIST_MONITOR completion dropped without external reset"),
  ('no_busy',"busy<=0;","MBIST_MONITOR neither busy nor complete")]
 for name,mutation,message in controls:
  body=bench.replace('  @(negedge clk); #1;','  '+mutation+'\n  @(negedge clk); #1;')
  assert body!=bench
  for engine,flags in engines[:2]:
   row,lines,text=run('control-'+name+'-'+engine,fixed,body,engine,flags)
   row['detected']=message in text;result['controls'].append(row)
 # Exhaust every four-state input of the seven-bit unknown predicate.
 predicate_bench=r"""
`timescale 1ns/1ps
module tb;
reg busy_i,done_i,failed_i;reg [1:0] eth_done_i,eth_failed_i;reg [6:0] bits;
wire unknown_status=EXPRESSION;
integer n,k,u;
initial begin
 for(n=0;n<16384;n=n+1) begin
  u=n;
  for(k=0;k<7;k=k+1) begin
   case(u%4) 0:bits[k]=1'b0;1:bits[k]=1'b1;2:bits[k]=1'bx;3:bits[k]=1'bz;endcase
   u=u/4;
  end
  {busy_i,done_i,failed_i,eth_done_i,eth_failed_i}=bits;
  #1;$display("TRACE n=%0d unknown=%b",n,unknown_status);
 end
 $finish;
end
endmodule
""".replace('EXPRESSION',unknown_expr)
 oracle=['TRACE n='+str(n)+' unknown='+str(int(any(((n>>(2*k))&3)>=2 for k in range(7))))for n in range(16384)]
 result['unknown_truth_table']=[]
 for engine,flags in engines:
  row,lines,text=run('unknown-truth-'+engine,fixed,predicate_bench,engine,flags)
  row['mismatch_count']=sum(a!=b for a,b in zip(oracle,lines))+abs(len(oracle)-len(lines))
  result['unknown_truth_table'].append(row)
 assert all(r['mismatch_count']==0 and r['rows']==16384 for r in result['unknown_truth_table'])
 assert all(c['identical_to_original_iverilog'] and c['returncode']==0 for c in result['cases']if c['label'].startswith('fixed-'))
 assert any(not c['identical_to_original_iverilog']for c in result['cases']if c['label'].startswith('original-cvc'))
 assert len(result['controls'])==8 and all(c['detected']for c in result['controls'])
 result['status']='PASS_SIGNED32_AND_BITWISE_UNKNOWN_MONITOR_CONTROLS'
finally:
 result['outputs']={str(p.relative_to(out)):hashlib.sha256(p.read_bytes()).hexdigest()for p in out.rglob('*')if p.is_file()and p.suffix in ('.log','.v')}
 (out/'result.json').write_text(json.dumps(result,indent=2))
