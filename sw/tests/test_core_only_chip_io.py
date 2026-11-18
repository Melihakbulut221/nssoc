# SPDX-FileCopyrightText: 2026 Hasan Melih Akbulut
# SPDX-License-Identifier: Apache-2.0
"""Core-only shell and wire-format tests, not actual-chip or pad-cell qualification."""
import importlib.util
import json
from pathlib import Path
import shutil
import subprocess
import pytest

ROOT = Path(__file__).resolve().parents[2]
def module(name, path):
    spec = importlib.util.spec_from_file_location(name, ROOT / path)
    obj = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(obj)
    return obj
generator = module("core_chip_generator", "scripts/generate_chip_io.py")
host = module("core_chip_host", "sw/golden/chip_status.py")
VALUES = dict(busy=0, done=1, failed=1, fail_address=0x1234,
              expected=0xfedcba9876543210, actual=0x0123456789abcdef,
              phase=5, background=0xa6)

def contract():
    return json.loads(generator.CORE_CONTRACT.read_text())

def test_core_contract_and_complete_pad_consumption():
    c = contract()
    before = json.dumps(c, sort_keys=True)
    text, pads = generator.generate(c)
    assert before == json.dumps(c, sort_keys=True)
    assert not any(n.startswith(("eth_", "pcie_")) for n in c["core_ports"])
    assert "eth_" not in text and "pcie_" not in text
    assert "32'h4d420002, 5'b0" in text
    assert len({p["instance"] for p in pads}) == len(pads)
    assert sum(bool(p.get("supply")) for p in pads) == 4
    for name in c["core_ports"]:
        assert text.count(f".{name}({name})") == 1
    for name in ("spw_di_i", "spw_do_o", "can_rx_i", "can_tx_o",
                 "i2c_scl_i", "i2c_scl_oe_o", "spi_sck_o"):
        assert name in c["core_ports"]

@pytest.mark.parametrize("mutation", ["network_port", "wrong_magic", "wrong_reserve", "missing_status"])
def test_invalid_core_contract_rejected(mutation):
    c = contract()
    if mutation == "network_port":
        c["core_ports"]["eth_irq_o"] = dict(direction="output", width=1)
    elif mutation == "wrong_magic":
        c["status_format"]["magic"] = "4d420001"
    elif mutation == "wrong_reserve":
        c["status_format"]["reserved_bits"] = 1
    else:
        c["status_lsb_first"].pop()
    with pytest.raises(ValueError):
        generator.generate(c)

def test_core_decoder_and_reserved_bits():
    frame = 0x4d420002 << 160
    for name, value in VALUES.items():
        lsb, width = host.CORE_FIELDS[name]
        assert 0 <= value < 1 << width
        frame |= value << lsb
    decoded = host.decode(frame.to_bytes(24, "little"))
    assert decoded == VALUES and "eth_done" not in decoded
    for bit in range(155, 160):
        with pytest.raises(ValueError):
            host.decode((frame | (1 << bit)).to_bytes(24, "little"))
    for bad in ((frame ^ (1 << 191)).to_bytes(24, "little"), bytes(23), bytes(25)):
        with pytest.raises(ValueError):
            host.decode(bad)

def test_generated_core_shell_serial_frame(tmp_path):
    """Actual mailbox and generated wiring; core and I/O cells are explicit stubs."""
    compiler, runtime = shutil.which("iverilog"), shutil.which("vvp")
    assert compiler and runtime, "Real Icarus execution required"
    c = contract()
    text, _ = generator.generate(c)
    shell = tmp_path / "chip.v"; shell.write_text(text)
    declarations = []
    assignments = []
    value_ports = {"mbist_" + name + "_o": value for name, value in
                   (("busy", 0), ("done", 1), ("failed", 1),
                    ("fail_addr", VALUES["fail_address"]), ("fail_expected", VALUES["expected"]),
                    ("fail_actual", VALUES["actual"]), ("fail_phase", 5), ("fail_background", 0xa6))}
    for name, p in c["core_ports"].items():
        width = p["width"]
        size = "" if width == 1 else f"[{width-1}:0] "
        declarations.append(f'{p["direction"]} wire {size}{name}')
        if p["direction"] == "output":
            assignments.append(f"assign {name} = {width}'h{value_ports.get(name, 0):x};")
    stubs = "module soc_top(" + ",".join(declarations) + ");\n" + "\n".join(assignments) + "\nendmodule\n"
    power = "inout wire iovdd, iovss, vdd, vss"
    stubs += f"module sg13g2_IOPadIn(inout wire pad,{power},output wire p2c); assign p2c=pad; endmodule\n"
    stubs += f"module sg13g2_IOPadOut4mA(inout wire pad,{power},input wire c2p); assign pad=c2p; endmodule\n"
    stubs += f"module sg13g2_IOPadInOut4mA(inout wire pad,{power},output wire p2c,input wire c2p,c2p_en); assign p2c=pad; assign pad=c2p_en?c2p:1'bz; endmodule\n"
    for suffix in ("Vdd", "Vss", "IOVdd", "IOVss"):
        stubs += f"module sg13g2_IOPad{suffix}({power}); endmodule\n"
    stub_path = tmp_path / "stubs.v"; stub_path.write_text(stubs)
    bench = tmp_path / "tb.v"
    bench.write_text("""
module tb;
reg clk=0, rst=0, tclk=0, req=0;
wire vdd=1'b1, vss=1'b0, ready, data;
wire pad_clk=clk, pad_rst=rst, pad_tclk=tclk, pad_req=req;
reg [191:0] frame;
integer i;
always #5 clk=~clk;
always #7 tclk=~tclk;
nssoc_chip dut(.VDD(vdd),.VSS(vss),.IOVDD(vdd),.IOVSS(vss),
 .pad_clk_i(pad_clk),.pad_rst_ni(pad_rst),
 .pad_test_clk(pad_tclk),.pad_test_req(pad_req),
 .pad_test_ready(ready),.pad_test_data(data));
initial begin
 repeat(6) @(negedge clk);
 rst=1;
 repeat(10) @(negedge tclk);
 req=1;
 wait(ready===1'b1);
 for(i=0;i<192;i=i+1) begin
  @(negedge tclk);
  if(data!==1'b0 && data!==1'b1) $fatal(1,"Unknown serial bit");
  frame[i]=data;
 end
 $display("FRAME %048h",frame);
 $finish;
end
initial begin #20000; $fatal(1,"Mailbox timeout"); end
endmodule
""")
    binary = tmp_path / "run.vvp"
    built = subprocess.run([compiler, "-g2012", "-s", "tb", "-o", str(binary),
                            str(shell), str(stub_path), str(ROOT / "hw/soc/rtl/chip/soc_status_serial.v"),
                            str(bench)], capture_output=True, text=True, timeout=30)
    assert built.returncode == 0, built.stdout + built.stderr
    result = subprocess.run([runtime, str(binary)], capture_output=True, text=True, timeout=30)
    assert result.returncode == 0, result.stdout + result.stderr
    frames = [line.split()[1] for line in result.stdout.splitlines() if line.startswith("FRAME ")]
    assert len(frames) == 1
    assert host.decode(int(frames[0], 16).to_bytes(24, "little")) == VALUES
