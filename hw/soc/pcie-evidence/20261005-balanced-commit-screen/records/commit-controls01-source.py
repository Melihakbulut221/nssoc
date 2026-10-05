# SPDX-FileCopyrightText: 2026 Hasan Melih Akbulut
# SPDX-License-Identifier: Apache-2.0
"""Actual complete-parser equivalence for the balanced commit selection."""

from pathlib import Path
import runpy

import pytest

ROOT = Path(__file__).resolve().parents[2]
RTL = ROOT / "hw/soc/rtl/pcie"
GEN = runpy.run_path(str(ROOT / "scripts/generate_pcie_integrity_commit_v18.py"))
REFERENCE = runpy.run_path(str(ROOT / "sw/tests/test_pcie_gen3_integrity_v3_crc.py"))
FAULTS = {
    "lower_priority": ("commit_lower=commit_write[1]?", "commit_lower=!commit_write[1]?"),
    "upper_priority": ("commit_upper=commit_write[3]?", "commit_upper=!commit_write[3]?"),
    "lose_upper": ("if(|commit_write[3:2])", "if(1'b0)"),
    "lose_fallback": ("else commit_n=commit_ptr;", "else commit_n=0;"),
    "look_offset": ("commit_value[j*PW+:PW]=position;", "commit_value[j*PW+:PW]=position+1'b1;"),
    "literal_z_to_x": ("commit_n=commit_upper;", "commit_n=commit_upper|{PW{1'b0}};"),
}


def test_exact_generated_inverse_and_wrapper_bridge():
    text = (RTL / "soc_pcie_gen3_framer_rx_integrity_v18.v").read_text()
    assert text == GEN["candidate"]()
    assert GEN["restore"](text) == GEN["SOURCE"].read_text()
    # No read-tree/event-sensitivity change is hidden in this candidate.
    read = runpy.run_path(str(ROOT / "scripts/generate_pcie_integrity_read_v17.py"))
    assert text.count(read["balanced_read"]()) == 1
    for name in [
        "hw/soc/rtl/pcie/soc_pcie_gen3_continuous_rx_integrity_v17.v",
        "hw/soc/tb/cocotb/test_soc_pcie_gen3_continuous_rx_integrity_v17.py",
        "hw/soc/tb/cocotb/Makefile.soc_pcie_gen3_continuous_rx_integrity_v17",
        "scripts/check_pcie_gen3_continuous_rx_integrity_v17.py",
    ]:
        assert (ROOT / name.replace("_v17", "_v18")).read_text().replace(
            "_v18", "_v17"
        ) == (ROOT / name).read_text()


def parser_miter():
    source = REFERENCE["parser_miter"]().replace(
        "soc_pcie_gen3_framer_rx_integrity_v2",
        "soc_pcie_gen3_framer_rx_integrity_v17",
    ).replace(
        "soc_pcie_gen3_framer_rx_integrity_v3",
        "soc_pcie_gen3_framer_rx_integrity_v18",
    )
    # Feed each unchanged parser its real predecode companion. Both actual
    # module bodies run; this is not a Python copy of the new reduction.
    source = source.replace(
        "initial begin",
        "wire [511:0] f_current_predecode=gold.predecode_block(f_current_block);\n"
        "initial begin\nforce gold.current_predecode=f_current_predecode;\n"
        "force gate.current_predecode=f_current_predecode;",
        1,
    )
    source = source.replace(
        "#1;",
        """// Actual selected and unselected payloads retain X and Z. Unknown
// branch predicates exercise procedural not-true masking in both parsers.
if(trial%31==1) f_commit_ptr[trial%7]=1'bx;
if(trial%31==2) f_commit_ptr[trial%7]=1'bz;
if(trial%37==1) f_write_ptr[trial%7]=1'bx;
if(trial%37==2) f_write_ptr[trial%7]=1'bz;
if(trial%41==1) f_ending=1'bx;
if(trial%41==2) f_ending=1'bz;
if(trial%43==1) f_state=2'bxz;
if(trial%47==1) f_header_first=1'bx;
if(trial%47==2) f_header_bad=1'bz;
if(trial%53==1) f_remaining[trial%11]=1'bx;
if(trial%59==1) f_current_block[trial%512]=1'bz;
#1;""",
        1,
    )
    return source


@pytest.mark.parametrize("fault", [None, *FAULTS])
def test_actual_complete_parser_arbitrary_state_and_four_state(tmp_path, fault):
    candidate = (RTL / "soc_pcie_gen3_framer_rx_integrity_v18.v").read_text()
    if fault:
        before, after = FAULTS[fault]
        assert candidate.count(before) == 1
        candidate = candidate.replace(before, after)
    target = tmp_path / "candidate.v"
    target.write_text(candidate)
    result, log = REFERENCE["simulate"](
        tmp_path,
        parser_miter(),
        [RTL / "soc_pcie_gen3_framer_rx_integrity_v17.v", target],
    )
    if fault:
        assert result.returncode != 0 and "PARSER_ARBITRARY_STATE_MISMATCH" in log
    else:
        assert result.returncode == 0 and "PASS 32768 ACTUAL_FULL_PARSER_CASES" in log
