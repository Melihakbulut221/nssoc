# SPDX-FileCopyrightText: 2026 Hasan Melih Akbulut
# SPDX-License-Identifier: Apache-2.0
"""Seven literal field writes plus exact inverse; invalid state is not equated."""

from pathlib import Path
import runpy
import pytest

ROOT = Path(__file__).resolve().parents[2]
RTL = ROOT / "hw/soc/rtl/pcie"
GEN = runpy.run_path(str(ROOT / "scripts/generate_pcie_integrity_slots_v19.py"))
SIM = runpy.run_path(str(ROOT / "sw/tests/test_pcie_gen3_integrity_v3_crc.py"))[
    "simulate"
]
FIELDS = {
    "data": 32,
    "keep": 4,
    "sop": 4,
    "eop": 4,
    "dllp": 4,
    "sequence": 12,
    "tag": 7,
}


def test_exact_generated_inverse_and_wrapper_bridge():
    new = (RTL / "soc_pcie_gen3_framer_rx_integrity_v19.v").read_text()
    assert new == GEN["candidate"]()
    old = new.replace("integrity_v19", "integrity_v17")
    assert old.count(GEN["writer"]()) == 1
    old = old.replace(GEN["writer"](), "")
    assert old.count(GEN["MARKER"]) == 1
    old = old.replace(GEN["MARKER"], GEN["original_writes"]())
    assert old == GEN["SOURCE"].read_text()
    for name in [
        "hw/soc/rtl/pcie/soc_pcie_gen3_continuous_rx_integrity_v17.v",
        "hw/soc/tb/cocotb/Makefile.soc_pcie_gen3_continuous_rx_integrity_v17",
        "scripts/check_pcie_gen3_continuous_rx_integrity_v17.py",
    ]:
        assert (ROOT / name.replace("_v17", "_v19")).read_text().replace(
            "_v19", "_v17"
        ) == (ROOT / name).read_text()
    baseline = (
        ROOT / "hw/soc/tb/cocotb/test_soc_pcie_gen3_continuous_rx_integrity_v17.py"
    ).read_text()
    candidate = (
        ROOT / "hw/soc/tb/cocotb/test_soc_pcie_gen3_continuous_rx_integrity_v19.py"
    ).read_text()
    assert candidate.startswith(baseline)
    assert candidate[len(baseline) :].startswith(
        "\n\n# BEGIN V19 FAULT EPOCH QUARANTINE CASE\n"
    )
    # The verdict array and generated cache writer remain fault qualified.
    assert "if(step && !fault_now) slot_verdict[cache_slot]<=next_value;" in new
    assert (
        "if(verdict_enable[w]) verdict[verdict_tags[w*PW+:PW]]<=verdict_value[w];"
        in new
    )
    for field in FIELDS:
        assert (
            new.count(f"slot_{field}[(write_ptr+slot_content_lane)&(RING_DWORDS-1)]<=")
            == 1
        )
        assert f"slot_{field}[(write_ptr+w)&(RING_DWORDS-1)]<=" not in new


@pytest.mark.parametrize(
    "fault", [None, *["lose_" + f for f in FIELDS], "rotate_data", "ignore_step"]
)
def test_actual_literal_seven_field_writer(tmp_path, fault):
    body = GEN["writer"]()
    if fault and fault.startswith("lose_"):
        field = fault.removeprefix("lose_")
        lines = [line for line in body.splitlines(True) if f"slot_{field}[(" in line]
        assert len(lines) == 1
        body = body.replace(lines[0], "")
    elif fault == "rotate_data":
        before = "write_data[slot_content_lane*32+:32]"
        assert body.count(before) == 1
        body = body.replace(before, "write_data[((slot_content_lane+1)%4)*32+:32]")
    elif fault == "ignore_step":
        assert body.count("if(step)") == 1
        body = body.replace("if(step)", "if(1'b1)")
    declarations, initial, expected, checks = [], [], [], []
    for field, width in FIELDS.items():
        value = "write_tags" if field == "tag" else "write_" + field
        declarations += [
            f"reg[{width - 1}:0] slot_{field}[0:63],expected_{field}[0:63];reg[{4 * width - 1}:0] {value};"
        ]
        initial += [
            f"for(i=0;i<64;i=i+1) begin slot_{field}[i]=$random(seed);expected_{field}[i]=slot_{field}[i];end",
            f"for(i=0;i<4;i=i+1) {value}[i*{width}+:{width}]=$random(seed);",
        ]
        expected += [f"expected_{field}[(write_ptr+j)&63]={value}[j*{width}+:{width}];"]
        checks += [
            f'if(slot_{field}[i]!==expected_{field}[i])$fatal(1,"V19_LITERAL_FIELD {field} trial=%0d slot=%0d",n,i);'
        ]
    bench = (
        """`timescale 1ns/1ps
module tb;
localparam RING_DWORDS=64,PW=7;
reg clk_i=0,step=0;reg[PW-1:0]write_ptr=0;
"""
        + "\n".join(declarations)
        + body
        + """
integer n,i,j,seed=19371337,known_updates=0,unknown_holds=0,wraps=0;
initial begin
for(n=0;n<4096;n=n+1) begin
 clk_i=0;step=0;
"""
        + "\n".join(initial)
        + """
 write_ptr=n%128;
 case((n>>7)&3) 0:step=0;1:step=1;2:step=1'bx;3:step=1'bz;endcase
 #1;
 if(step===1'b1) begin
  known_updates=known_updates+1;if((write_ptr&63)>60)wraps=wraps+1;
  for(j=0;j<4;j=j+1) begin
"""
        + "\n".join(expected)
        + """
  end
 end else if(step!==1'b0) unknown_holds=unknown_holds+1;
 clk_i=1;#1;
 for(i=0;i<64;i=i+1) begin
"""
        + "\n".join(checks)
        + """
 end
end
if(known_updates!=1024||unknown_holds!=2048||wraps!=48)$fatal(1,"V19_LITERAL_COVERAGE");
$display("PASS_V19_LITERAL_SEVEN_FIELDS cases4096 updates1024 unknownholds2048 wraps48");$finish;
end endmodule
"""
    )
    result, log = SIM(tmp_path, bench)
    if fault:
        assert result.returncode != 0 and "V19_LITERAL_FIELD" in log
    else:
        assert result.returncode == 0 and "PASS_V19_LITERAL_SEVEN_FIELDS" in log
