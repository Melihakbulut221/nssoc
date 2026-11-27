# SPDX-FileCopyrightText: 2026 Hasan Melih Akbulut
# SPDX-License-Identifier: Apache-2.0
"""Actual SAT proofs reject corrupt reads even with initially undefined RAM."""
from pathlib import Path
import shutil
import subprocess
import sys

import pytest

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "scripts"))
from check_pcie_rx_read_cut import run, read_expression

SOURCE = ROOT / "hw/soc/rtl/pcie/soc_pcie_rx_credit.v"


@pytest.mark.parametrize("parameters", [{}, {"MAX_TLP_DWORDS": 3, "SLOTS_PER_CLASS": 1}])
def test_actual_read_cut(tmp_path, parameters):
    yosys = Path(shutil.which("yosys") or ROOT / "hw/soc/tools/oss-cad-suite/bin/yosys")
    assert run(SOURCE, tmp_path / "proof", yosys, parameters)["status"] == "PASS"


@pytest.mark.parametrize("old,new", [
    ("next_onehot[read_offset] & packets[bank*CAP+read_offset]",
     "next_onehot[read_offset] & packets[bank*CAP+(read_offset^1)]"),
    ("dllp[3'(output_index)]", "dllp[3'(output_index)^3'd1]"),
    ("restart ? packets[bank*CAP]", "restart ? packets[bank*CAP+1]"),
    ("handshake ? following : registered", "handshake ? following : ~registered"),
    ("registered<=commit_bank[bank] ? staging[0]", "registered<=commit_bank[bank] ? ~staging[0]"),
])
def test_actual_wrong_byte_is_rejected(tmp_path, old, new):
    text = SOURCE.read_text()
    assert text.count(old) == 1
    candidate = tmp_path / "wrong.v"
    candidate.write_text(text.replace(old, new))
    yosys = Path(shutil.which("yosys") or ROOT / "hw/soc/tools/oss-cad-suite/bin/yosys")
    result = run(candidate, tmp_path / "proof", yosys, {"MAX_TLP_DWORDS": 3, "SLOTS_PER_CLASS": 1})
    assert result["status"] == "FAIL"
    assert "SAT proof finished - model found: FAIL!" in (tmp_path / "proof/proof.log").read_text()


def test_changed_state_shape_is_rejected():
    with pytest.raises(ValueError, match="state shape"):
        read_expression(SOURCE.read_text().replace("CAP=MAX_TLP_DWORDS*4+6", "CAP=MAX_TLP_DWORDS*4+7"))


@pytest.mark.parametrize("old,new", [
    (None, None),
    ("packets[head_slot*CAP+output_index]", "packets[head_slot*CAP+(output_index^1)]"),
    ("dllp[output_index]", "dllp[output_index^1]"),
])
def test_frozen_flat_read_contract(tmp_path, old, new):
    fixture = ROOT / "sw/tests/fixtures/pcie_chip_timing/flat-rx.v"
    candidate = fixture
    if old is not None:
        text = fixture.read_text()
        assert text.count(old) == 1
        candidate = tmp_path / "flat-mutant.v"
        candidate.write_text(text.replace(old, new))
    yosys = Path(shutil.which("yosys") or ROOT / "hw/soc/tools/oss-cad-suite/bin/yosys")
    result = run(candidate, tmp_path / "proof", yosys, {"MAX_TLP_DWORDS": 3, "SLOTS_PER_CLASS": 1})
    assert result["status"] == ("PASS" if old is None else "FAIL")
    if old is not None:
        assert "SAT proof finished - model found: FAIL!" in (tmp_path / "proof/proof.log").read_text()


@pytest.mark.parametrize("fault", [None, "packet", "dllp"])
def test_live_pipeline_reads_queued_bytes(tmp_path, fault):
    """Check every valid cycle of the complete live receiver against its stored bytes."""
    source = SOURCE.read_text()
    reference = tmp_path / "reference.v"
    reference.write_text(source.replace("module soc_pcie_rx_credit #(",
                                        "module soc_pcie_rx_credit_ref #(", 1))
    mutations = {
        "packet": ("next_onehot[read_offset] & packets[bank*CAP+read_offset]",
                   "next_onehot[read_offset] & packets[bank*CAP+(read_offset^1)]"),
        "dllp": ("dllp[3'(output_index)]", "dllp[3'(output_index)^3'd1]"),
    }
    if fault:
        before, after = mutations[fault]
        assert source.count(before) == 1
        source = source.replace(before, after)
    candidate = tmp_path / "candidate.v"
    candidate.write_text(source)
    bench = (ROOT / "hw/soc/tb/tb_pcie_rx_credit_read_ahead.v").read_text()
    assert bench.count("    integer seed0;") == 1
    monitor = """
    integer checked_tlp=0,checked_dllp=0,checked_stall=0;
    reg [7:0] expected_byte;
    always @(negedge clk) if (c_valid) begin
        if (candidate.select_dllp) begin
            expected_byte=candidate.dllp[candidate.output_index];
            checked_dllp=checked_dllp+1;
        end else begin
            expected_byte=candidate.packets[candidate.head_slot*CAP+candidate.output_index];
            checked_tlp=checked_tlp+1;
        end
        if (!out_ready_i) checked_stall=checked_stall+1;
        if ((^expected_byte === 1'bx) || c_data !== expected_byte)
            $fatal(1,"LIVE_READ_MISMATCH");
    end
"""
    bench = bench.replace("    integer seed0;", monitor + "    integer seed0;")
    assert bench.count("        $finish;") == 1
    bench = bench.replace("        $finish;", """
        if (checked_tlp<1000 || checked_dllp<100 || checked_stall<100)
            $fatal(1,"LIVE_READ_COVERAGE");
        $display("LIVE_READ_COVERAGE_PASS %0d %0d %0d",checked_tlp,checked_dllp,checked_stall);
        $finish;
""")
    tb = tmp_path / "bench.v"
    tb.write_text(bench)
    image = tmp_path / "receiver.vvp"
    tools = ROOT / "hw/soc/tools/oss-cad-suite/bin"
    subprocess.run([shutil.which("iverilog") or tools / "iverilog", "-g2012",
                    "-s", "tb_pcie_rx_credit_read_ahead", "-o", image,
                    reference, candidate, tb], check=True)
    result = subprocess.run([shutil.which("vvp") or tools / "vvp", "-n", image,
                             "+seed=1", "+cycles=300000"], capture_output=True, text=True)
    if fault:
        assert result.returncode != 0 and "LIVE_READ_MISMATCH" in result.stdout, result.stdout
    else:
        assert result.returncode == 0 and "RESULT PASS" in result.stdout, result.stdout
        assert "LIVE_READ_COVERAGE_PASS" in result.stdout, result.stdout
