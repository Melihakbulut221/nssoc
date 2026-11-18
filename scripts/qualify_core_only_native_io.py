#!/usr/bin/env python3
"""Native IHP functional-pad regression with an explicit core stub; not signoff."""
import base64
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import re
import subprocess
import sys
ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / 'hw/soc/out/core-only-native-io'
REV = 'c4b8b4e5e7a05f375cca3815d51b3a37721fbf5c'
MODEL_SHA = '0195945188ec15560ad2cc9c000e3ff70255d65da717099b87b6b726a6e53429'
def digest(b): return hashlib.sha256(b).hexdigest()
def load(name, path):
    spec = importlib.util.spec_from_file_location(name, ROOT / path)
    module = importlib.util.module_from_spec(spec); spec.loader.exec_module(module)
    return module

def main():
    assert os.environ.get('GITHUB_ACTIONS') == 'true'
    OUT.mkdir(parents=True, exist_ok=False)
    result = dict(status='RUNNING', source_head=os.environ['GITHUB_SHA'], accepted=False,
                  actual_core_boot=False, transistor_pad_qualification=False,
                  physical_timing_complete=False, cases={})
    try:
        generator = load('native_chip_generator', 'scripts/generate_chip_io.py')
        host = load('native_chip_host', 'sw/golden/chip_status.py')
        paths = [Path(__file__), generator.CORE_CONTRACT,
                 ROOT/'scripts/generate_chip_io.py', ROOT/'sw/golden/chip_status.py',
                 ROOT/'hw/soc/rtl/chip/soc_status_serial.v']
        before = {str(p): digest(p.read_bytes()) for p in paths}
        contract = json.loads(generator.CORE_CONTRACT.read_text())
        shell, pads = generator.generate(contract)
        (OUT/'chip.v').write_text(shell)
        url = 'repos/IHP-GmbH/IHP-Open-PDK/contents/ihp-sg13g2/libs.ref/sg13g2_io/verilog/sg13g2_io.v?ref='+REV
        source = json.loads(subprocess.check_output(['gh','api',url]))
        model = base64.b64decode(source['content'])
        assert digest(model) == MODEL_SHA
        (OUT/'native_io.v').write_bytes(model)
        values = dict(busy=0, done=1, failed=1, fail_address=0x1234,
                      expected=0xfedcba9876543210, actual=0x0123456789abcdef,
                      phase=5, background=0xa6)
        ports = dict(mbist_busy_o=0, mbist_done_o=1, mbist_failed_o=1,
                     mbist_fail_addr_o=values['fail_address'], mbist_fail_expected_o=values['expected'],
                     mbist_fail_actual_o=values['actual'], mbist_fail_phase_o=5, mbist_fail_background_o=0xa6)
        expressions = dict(gpio_o="16'ha55a", gpio_oe_o="{16{strap_i[0]}}",
            qspi_io_o="4'ha", qspi_io_oe_o="{4{strap_i[1]}}",
            i2c_scl_oe_o="strap_i[2]", i2c_sda_oe_o="strap_i[3]")
        declarations=[]; assignments=[]
        for name,p in contract['core_ports'].items():
            width=p['width']; size='' if width==1 else f'[{width-1}:0] '
            declarations.append(f"{p['direction']} wire {size}{name}")
            if p['direction']=='output':
                expr=expressions.get(name, f"{width}'h{ports.get(name,0):x}")
                assignments.append(f'assign {name} = {expr};')
        (OUT/'core_stub.v').write_text('module soc_top('+','.join(declarations)+');\n'+'\n'.join(assignments)+'\nendmodule\n')
        bench=r"""
module tb;
reg clk=0,rst=0,tclk=0,req=0;
reg [3:0] strap=0;
reg ext_enable=1;
wire vdd=1'b1,vss=1'b0,ready,data;
wire pad_clk=clk,pad_rst=rst,pad_tclk=tclk,pad_req=req;
wire [3:0] pad_strap=strap;
tri [15:0] gpio;
tri [3:0] qspi;
tri1 scl,sda;
assign gpio=ext_enable?16'h5aa5:16'hzzzz;
assign qspi=ext_enable?4'h5:4'hz;
reg [191:0] frame;
integer i;
always #5 clk=~clk;
always #7 tclk=~tclk;
nssoc_chip dut(.VDD(vdd),.VSS(vss),.IOVDD(vdd),.IOVSS(vss),
 .pad_clk_i(pad_clk),.pad_rst_ni(pad_rst),.pad_strap_i(pad_strap),
 .pad_gpio(gpio),.pad_qspi_io(qspi),.pad_i2c_scl(scl),.pad_i2c_sda(sda),
 .pad_test_clk(pad_tclk),.pad_test_req(pad_req),.pad_test_ready(ready),.pad_test_data(data));
initial begin
 #2;
 if(dut.u_core.gpio_i!==16'h5aa5 || dut.u_core.qspi_io_i!==4'h5) $fatal(1,"Native pad input/release failed");
 if(scl!==1'b1 || sda!==1'b1) $fatal(1,"I2C release failed");
 ext_enable=0; strap=4'hf;
 #2;
 if(gpio!==16'ha55a || qspi!==4'ha) $fatal(1,"Native pad output enable failed");
 if(dut.u_core.gpio_i!==16'ha55a || dut.u_core.qspi_io_i!==4'ha) $fatal(1,"Native pad readback failed");
 if(scl!==1'b0 || sda!==1'b0) $fatal(1,"I2C low drive failed");
 strap=0;
 #2;
 if(gpio!==16'hzzzz || qspi!==4'hz || scl!==1'b1 || sda!==1'b1) $fatal(1,"Pad turn-around failed");
 ext_enable=1;
 repeat(6) @(negedge clk); rst=1;
 repeat(10) @(negedge tclk); req=1;
 wait(ready===1'b1);
 for(i=0;i<192;i=i+1) begin
  @(negedge tclk);
  if(data!==1'b0 && data!==1'b1) $fatal(1,"Unknown serial bit");
  frame[i]=data;
 end
 $display("FRAME %048h",frame);
 $display("NATIVE_PAD_FUNCTIONAL_PASS");
 $finish;
end
initial begin #20000; $fatal(1,"Mailbox timeout"); end
endmodule
"""
        (OUT/'tb.v').write_text(bench)
        text=model.decode()
        pattern=r'(\bmodule\s+sg13g2_IOPadInOut4mA\b.*?\bendmodule\b)'
        modules=list(re.finditer(pattern,text,re.S));assert len(modules)==1
        original=modules[0].group();anchor="assign pad = (c2p_en) ? c2p : 1'bz;"
        assert original.count(anchor)==1
        broken=text[:modules[0].start()]+original.replace(anchor,"assign pad = (!c2p_en) ? c2p : 1'bz;")+text[modules[0].end():]
        (OUT/'negative_enable_io.v').write_text(broken)
        for label,model_name in [('native','native_io.v'),('negative_enable','negative_enable_io.v')]:
            binary=OUT/(label+'.vvp')
            command=['iverilog','-g2012','-s','tb','-o',str(binary),str(OUT/'chip.v'),
                str(OUT/'core_stub.v'),str(OUT/model_name),str(ROOT/'hw/soc/rtl/chip/soc_status_serial.v'),str(OUT/'tb.v')]
            compile_result=subprocess.run(command,capture_output=True,text=True,timeout=60)
            (OUT/(label+'-compile.log')).write_text(compile_result.stdout+compile_result.stderr)
            assert compile_result.returncode==0, compile_result.stderr
            run=subprocess.run(['vvp',str(binary)],capture_output=True,text=True,timeout=60)
            (OUT/(label+'-run.log')).write_text(run.stdout+run.stderr)
            result['cases'][label]=dict(returncode=run.returncode, model_sha256=digest((OUT/model_name).read_bytes()))
            if label=='native':
                assert run.returncode==0 and 'NATIVE_PAD_FUNCTIONAL_PASS' in run.stdout,run.stdout+run.stderr
                frames=[line.split()[1] for line in run.stdout.splitlines() if line.startswith('FRAME ')]
                assert len(frames)==1 and host.decode(int(frames[0],16).to_bytes(24,'little'))==values
                result['decoded_frame']=values
            else:
                assert run.returncode!=0 and 'Native pad input/release failed' in run.stdout,run.stdout+run.stderr
        assert all(digest(Path(p).read_bytes())==h for p,h in before.items())
        result.update(status='PASS_NATIVE_FUNCTIONAL_PADS_WITH_CORE_STUB_NOT_SIGNOFF',
            sources_unchanged=True, protected_inputs=before, upstream_revision=REV, native_model_sha256=MODEL_SHA,
            scope='Generated core-only wiring and actual mailbox with native IHP functional pad Verilog. Core is an explicit stub. Models have zero timing arcs and do not validate supply behavior, transistor LVS, ESD, electrical loading, package or real core boot.')
    except BaseException as error:
        result.update(status='FAIL_OR_ERROR',error=repr(error));raise
    finally:
        result['outputs']={str(p.relative_to(OUT)):digest(p.read_bytes()) for p in OUT.rglob('*') if p.is_file() and p.name!='result.json'}
        (OUT/'result.json').write_text(json.dumps(result,indent=2)+'\n')
if __name__=='__main__': main()
