import subprocess,json,os
from pathlib import Path
assert os.environ.get('GITHUB_ACTIONS')=='true'
out=Path('out/system-mbist-monitor');out.mkdir(parents=True)
cases={}
for case in range(7):
 tb="""`timescale 1ns/1ps
module tb;
reg clk=0;always #5 clk=!clk;
reg rst=0,busy=1,done=0,failed=0;wire passed;wire signed[31:0]bc,dc;
mapped_system_mbist_boot_monitor dut(clk,rst,busy,done,failed,passed,bc,dc);
integer n;
initial begin
 repeat(2) @(posedge clk);#1;rst=1;
 for(n=1;n<=50;n=n+1)begin
  @(posedge clk);#1;
  if(CASE==3)begin busy=0;done=1;end
  else if(n==38)begin busy=0;done=1;end
  if(n==40)case(CASE)
   1:failed=1;2:busy=1'bx;4:done=0;5:failed=1'bz;6:busy=1;
  endcase
 end
 @(posedge clk);#1;
 if(!passed || bc<=0 || dc<=bc)$fatal(1,"missing real handover");
 $display("SYSTEM_OBSERVER_PASS");$finish;
end
endmodule
""".replace('CASE',str(case))
 p=out/f'case{case}.v';p.write_text(tb);exe=out/f'case{case}.vvp'
 subprocess.run(['iverilog','-g2012','-s','tb','-o',str(exe),'hw/soc/tb/mapped_system_mbist_boot_monitor.v',str(p)],check=True)
 r=subprocess.run(['vvp',str(exe)],capture_output=True,text=True);log=r.stdout+r.stderr;(out/f'case{case}.log').write_text(log)
 if case==0:assert r.returncode==0 and 'SYSTEM_OBSERVER_PASS'in log
 else:assert r.returncode!=0 and 'MBIST_MONITOR'in log and 'SYSTEM_OBSERVER_PASS'not in log
 cases[str(case)]={'returncode':r.returncode,'expected_rejection':case!=0}
(out/'result.json').write_text(json.dumps(dict(passed=True,cases=cases,mapped_chip_boot_passed=False),indent=2))
