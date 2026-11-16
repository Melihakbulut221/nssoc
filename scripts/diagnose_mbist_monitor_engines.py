import os,json,subprocess,hashlib
from pathlib import Path
assert os.environ.get('GITHUB_ACTIONS')=='true'
out=Path('mbist-monitor-probe');out.mkdir()
monitor=Path('hw/soc/tb/mapped_mbist_boot_monitor.v')
bench=r"""`timescale 1ns/1ps
module tb;
reg clk=0; always #5 clk=~clk;
reg rst=0,busy=0,done=0,failed=0;
reg [1:0] edone=0,efailed=0;
wire passed; wire [31:0] busy_count,done_cycle;
mapped_mbist_boot_monitor dut(clk,rst,busy,done,failed,edone,efailed,passed,busy_count,done_cycle);
integer n;
initial begin
 for(n=0;n<210;n=n+1) begin
  @(posedge clk);
  rst<=n>=4;
  busy<=n>=4 && n<164;
  done<=n>=164;
  edone<=n>=164 ? 2'b11 : 2'b00;
  @(negedge clk); #1;
  $display("TRACE n=%0d busy_count=%0d done_cycle=%0d passed=%b cycles=%0d seen=%b",n,busy_count,done_cycle,passed,dut.cycles,dut.done_seen);
 end
 $finish;
end
endmodule
"""
(out/'tb.v').write_text(bench)
rows=[];result=dict(source_head=os.environ['GITHUB_SHA'],monitor_sha256=hashlib.sha256(monitor.read_bytes()).hexdigest(),accepted=False,cases=rows)
try:
 ref=None
 for name,flags in [('iverilog',[]),('cvc',[]),('cvc-interp',['+interp']),('cvc-ogate',['-Ogate']),('cvc-o',['-O'])]:
  exe=out/(name+'.sim')
  cmd=(['iverilog','-g2012','-s','tb','-o',str(exe)] if name=='iverilog' else [str(Path('cvc-source/build64/cvc64').resolve()),'-sv',*flags,'-o',str(exe)])
  cmd += [str(out/'tb.v'),str(monitor)]
  p=subprocess.run(cmd,stdout=subprocess.PIPE,stderr=subprocess.STDOUT)
  (out/(name+'-compile.log')).write_bytes(p.stdout);assert p.returncode==0,p.stdout[-2000:]
  p=subprocess.run((['vvp','-n',str(exe)] if name=='iverilog' else [str(exe)]),stdout=subprocess.PIPE,stderr=subprocess.STDOUT,timeout=60)
  (out/(name+'-run.log')).write_bytes(p.stdout)
  lines=[l for l in p.stdout.decode().splitlines() if l.startswith('TRACE ')]
  assert p.returncode==0 and len(lines)==210
  if ref is None:
   ref=lines
   last=dict(t.split('=')for t in lines[-1].split()[1:])
   assert int(last['busy_count'])==128 and int(last['done_cycle'])==161 and last['passed']=='1',last
  diff=[dict(index=i,reference=a,candidate=b)for i,(a,b)in enumerate(zip(ref,lines))if a!=b]
  rows.append(dict(name=name,returncode=p.returncode,rows=len(lines),mismatches=len(diff),examples=diff[:4],last=lines[-1]))
 result['status']='PASS_IDENTICAL_MONITOR_TRACES' if all(x['mismatches']==0 for x in rows) else 'FAIL_MONITOR_ENGINE_DISAGREEMENT'
 assert result['status']=='PASS_IDENTICAL_MONITOR_TRACES'
finally:
 (out/'result.json').write_text(json.dumps(result,indent=2))
