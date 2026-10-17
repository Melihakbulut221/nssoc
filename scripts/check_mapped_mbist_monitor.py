#!/usr/bin/env python3
# SPDX-FileCopyrightText: 2026 Hasan Melih Akbulut
# SPDX-License-Identifier: Apache-2.0
"""Execute the actual mapped-boot observer against good and corrupt signals."""
import argparse,hashlib,json,subprocess
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
BENCH=r'''`timescale 1ns/1ps
module tb;
reg clk=0, rst=0, busy=1, done=0, failed=0;
reg [1:0] eth_done=0, eth_failed=0;
wire passed; wire [31:0] busy_cycles,done_cycle;
integer fault=0;
always #5 clk=~clk;
mapped_mbist_boot_monitor dut(.clk_i(clk),.rst_ni(rst),.busy_i(busy),.done_i(done),.failed_i(failed),.eth_done_i(eth_done),.eth_failed_i(eth_failed),.passed_o(passed),.busy_cycles_o(busy_cycles),.done_cycle_o(done_cycle));
initial begin
 if (!$value$plusargs("fault=%d",fault)) fault=0;
 repeat(4) @(posedge clk); #1; rst=1;
 if(fault==1)busy=0;
 if(fault==7)begin busy=0;done=1;eth_done=3;end
 repeat(40) @(posedge clk); #1;
 if(fault==2)busy=1'bx;
 if(fault==3)failed=1;
 repeat(5) @(posedge clk); #1;
 if(fault!=8)begin busy=0;done=1;eth_done=3;end
 if(fault==4)eth_done=1;
 if(fault==5)busy=1;
 repeat(5) @(posedge clk); #1;
 if(fault==6)begin done=0;busy=1;end
 if(fault==9)eth_failed=2;
 repeat(5) @(posedge clk); #1;
 if(passed!==1 || busy_cycles==0 || done_cycle<=busy_cycles)$fatal(1,"MBIST_MONITOR final incomplete");
 $display("MBIST_MONITOR_CONTROL PASS");$finish;
end
endmodule
'''
def main():
    p=argparse.ArgumentParser();p.add_argument('--iverilog',type=Path,required=True);p.add_argument('--output',type=Path,required=True);args=p.parse_args();out=args.output;out.mkdir(parents=True,exist_ok=False)
    source=ROOT/'hw/soc/tb/mapped_mbist_boot_monitor.v';sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest();before=sha(source)
    (out/'tb.v').write_text(BENCH)
    result=dict(passed=False,source_sha256=before,cases=[],scope='Actual observer logic controls, not SRAM cell or MBIST algorithm fault coverage')
    try:
        cmd=[str(args.iverilog),'-g2005-sv','-s','tb','-o',str(out/'run.vvp'),str(out/'tb.v'),str(source)]
        with(out/'compile.log').open('w')as f:subprocess.run(cmd,stdout=f,stderr=subprocess.STDOUT,check=True)
        names=['success','never_busy','unknown','system_failure','missing_ethernet_done','busy_at_done','done_drop','false_done','never_done','ethernet_failure']
        for fault,name in enumerate(names):
            log=out/(name+'.log')
            with log.open('w')as f:run=subprocess.run([str(args.iverilog.with_name('vvp')),str(out/'run.vvp'),'+fault='+str(fault)],stdout=f,stderr=subprocess.STDOUT,timeout=10)
            text=log.read_text();good=run.returncode==0 and 'MBIST_MONITOR_CONTROL PASS'in text and 'FATAL:'not in text
            if fault==0:assert good,text
            else:assert run.returncode!=0 and 'MBIST_MONITOR'in text and 'MBIST_MONITOR_CONTROL PASS'not in text,text
            result['cases'].append(dict(name=name,returncode=run.returncode,expected_pass=fault==0,expected_fault_rejected=fault!=0,log_sha256=sha(log)))
        assert sha(source)==before;result.update(passed=True,source_unchanged=True)
    finally:(out/'result.json').write_text(json.dumps(result,indent=2)+'\n')
if __name__=='__main__':main()
