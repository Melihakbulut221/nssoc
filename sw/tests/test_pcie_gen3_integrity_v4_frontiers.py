# SPDX-FileCopyrightText: 2026 Hasan Melih Akbulut
# SPDX-License-Identifier: Apache-2.0
"""Independent cross-product coverage of carried/new packet control frontiers."""

import runpy
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
RTL = ROOT / "hw/soc/rtl/pcie"
BASE = runpy.run_path(str(ROOT / "sw/tests/test_pcie_gen3_integrity_v3_crc.py"))


def frontier_bench():
    # The inherited bench compares all 28 parser outputs. Replace only its
    # stimulus schedule, so state/remaining/header/ending/slice are independent.
    bench = BASE["parser_miter"]().replace("_v3", "_v4").replace("_v2", "_v3")
    begin = bench.index("for(trial=0;trial<32768;")
    end = bench.index("#1;", begin)
    schedule = """for(trial=0;trial<8192;trial=trial+1) begin
f_lcrc=$random;f_dllp_crc=$random;f_current_block=0;
f_write_ptr=$random;f_commit_ptr=$random;f_packet_tag=$random;
f_packet_sequence=$random;f_expected_bytes=$random;
// 4 states x 8 boundary counts x 2 header states x 2 validity classes
// x 2 ending flags x 2 slice positions x 16 independent word patterns.
f_state=trial&3;
case((trial>>2)&7)
 0:f_remaining=0;1:f_remaining=1;2:f_remaining=2;3:f_remaining=3;
 4:f_remaining=4;5:f_remaining=5;6:f_remaining=7;7:f_remaining=2047;
endcase
f_header_first=(trial>>5)&1;f_header_bad=(trial>>6)&1;
f_ending=(trial>>7)&1;f_slice=((trial>>8)&1)?3:0;
for(j=0;j<4;j=j+1) words[j]=0;
case((trial>>9)&15)
 0:begin end
 1:words[0]=choices[1];
 2:words[1]=choices[1];
 3:words[2]=choices[1];
 4:words[3]=choices[1];
 5:begin words[0]=choices[2];words[1]=32'h01020304;words[2]=choices[1];end
 6:begin words[1]=choices[2];words[2]=32'h04030201;end
 7:begin words[2]=choices[2];words[3]=32'h05060708;end
 8:words[3]=choices[2];
 9:begin words[0]=choices[3];words[1]=choices[2];words[2]=32'h01020304;words[3]=choices[1];end
 10:words[1]=choices[3];
 11:words[0]=choices[6];
 12:words[0]=32'h02800060;
 13:words[0]=32'h00000080;
 14:words[3]=choices[4];
 15:begin words[1]=choices[3];words[2]=choices[2];words[3]=32'h01020304;end
endcase
// Compute carried first-header size independently as integer byte counts.
// Deliberately preserve a stale expected register when header_first is set.
if(f_header_first) begin
 k=(words[0][17:16]*256+words[0][31:24]);
 if(k==0) k=1024;
 f_packet_bytes=18+(words[0][5]?4:0)+(words[0][6]?4*k:0)+(words[0][23]?4:0);
end else f_packet_bytes=f_expected_bytes;
if(f_header_bad) f_packet_bytes=f_packet_bytes+1'b1;
for(j=0;j<4;j=j+1)
 for(b=0;b<4;b=b+1) f_current_block[b*128+j*8+:8]=words[j][b*8+:8];
"""
    bench = bench[:begin] + schedule + bench[end:]
    return bench.replace("PASS 32768", "PASS 8192 INDEPENDENT_FRONTIERS")


@pytest.mark.parametrize("fault", [None, "valid_header_rejected", "zero_wrap_ends"])
def test_actual_independent_parser_frontiers(tmp_path, fault):
    candidate = (RTL / "soc_pcie_gen3_framer_rx_integrity_v4.v").read_text()
    changes = {
        "valid_header_rejected": (
            "packet_bytes!=control_expected0",
            "packet_bytes==control_expected0",
        ),
        "zero_wrap_ends": (
            "remaining==(control_word+1)",
            "(remaining==0 || remaining==(control_word+1))",
        ),
    }
    if fault:
        old, new = changes[fault]
        assert old in candidate
        candidate = candidate.replace(old, new)
    path = tmp_path / "candidate.v"
    path.write_text(candidate)
    result, log = BASE["simulate"](
        tmp_path,
        frontier_bench(),
        [RTL / "soc_pcie_gen3_framer_rx_integrity_v3.v", path],
    )
    if fault:
        assert result.returncode != 0 and "PARSER_ARBITRARY_STATE_MISMATCH" in log
    else:
        assert result.returncode == 0 and "PASS 8192 INDEPENDENT_FRONTIERS" in log
