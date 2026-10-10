# SPDX-FileCopyrightText: 2026 Hasan Melih Akbulut
# SPDX-License-Identifier: Apache-2.0
"""Real HDL faults must fail a named public-port assertion, never compilation."""

import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import xml.etree.ElementTree as ET
import pytest

ROOT = Path(__file__).resolve().parents[2]
MODULES = (
    "soc_pcie_gen3_ingress_integrity_v11",
    "soc_pcie_gen3_data_descrambler",
    "soc_pcie_gen3_framer_rx_integrity_v21",
    "soc_pcie_gen3_continuous_rx_integrity_v21",
)
F = "soc_pcie_gen3_framer_rx_integrity_v21"
DENSE = "sustained_minimum_packets_exceed_every_buffer"
CRC_CASE = "tlp_crc_coverage_residue_nullification_and_successor"
DLLP_CASE = "crc_candidates_cover_every_dword_start_and_cross_slice_seed"
FAULTS = (
    ("selector_loses_stp", F, "crc_origin=j+1;", "crc_origin=0;", 1, CRC_CASE),
    (
        "sequence_byte_order",
        F,
        "crc_word[0][31:24],4'b0,crc_word[0][19:16]",
        "4'b0,crc_word[0][19:16],crc_word[0][31:24]",
        4,
        CRC_CASE,
    ),
    (
        "carry_word_order",
        F,
        "crc32_64(lcrc,{crc_word[1],crc_word[0]})",
        "crc32_64(lcrc,{crc_word[0],crc_word[1]})",
        1,
        CRC_CASE,
    ),
    (
        "stp_suffix_word_order",
        F,
        "crc32_112(32'hffffffff,{crc_word[3],crc_word[2],crc_word[1],crc_word[0][31:24],4'b0,crc_word[0][19:16]})",
        "crc32_112(32'hffffffff,{crc_word[3],crc_word[1],crc_word[2],crc_word[0][31:24],4'b0,crc_word[0][19:16]})",
        1,
        CRC_CASE,
    ),
    (
        "initial_dllp_loses_carry",
        F,
        "crc16_32(dllp_crc,crc_word[0])",
        "crc16_32(16'hffff,crc_word[0])",
        1,
        DLLP_CASE,
    ),
    (
        "dllp_preceding_seed_order",
        F,
        "crc16_48(16'hffff,{crc_word[1],crc_word[0][31:16]})",
        "crc16_48(16'hffff,{crc_word[0][31:16],crc_word[1]})",
        1,
        DLLP_CASE,
    ),
    (
        "look_drops_successor",
        F,
        "commit_n=position;state_n=TOKEN;",
        "commit_n=position;state_n=TOKEN;handled=1;",
        1,
        DENSE,
    ),
    (
        "edb_releases_bad",
        F,
        "verdict_value[j]=0;event_nullified[j]=",
        "verdict_value[j]=1;event_nullified[j]=",
        1,
        "edb_quarantine_and_eds_release_drain",
    ),
)


# Whole-product negatives complement isolated descriptor transition mutants.
FAULTS += (
    ("fault_descriptor_survives", F,
     "end else if((stream_abort_i && active_o) || fault_now) begin\n       retire_valid<=0;retire_has_data<=0;",
     "end else if((stream_abort_i && active_o) || fault_now) begin\n       retire_has_data<=0;", 1,
     "descriptor_parser_fault_cancels_queue_after_sampling_edge"),
    ("restart_descriptor_survives", F,
     "slice<=0;write_ptr<=0;read_ptr<=0;commit_ptr<=0;\n       retire_valid<=0;retire_has_data<=0;",
     "slice<=0;write_ptr<=0;read_ptr<=0;commit_ptr<=0;\n       retire_has_data<=0;", 1,
     "descriptor_epoch_controls_discard_owned_payload"),
    ("empty_descriptor_blocks", F,
     "(!retire_has_data || !output_valid || ready_i)",
     "(!output_valid || ready_i)", 1,
     "descriptor_empty_drain_under_held_output_and_eds"),
    ("full_descriptor_overwrite", F,
     "wire retire_room=!retire_valid || retire_pop;",
     "wire retire_room=1;", 1,
     "actual_full_ring_replacement_and_late_stall_overflow"),
)


def run(tmp_path, maximum=150, rtl=None, case=None):
    out = tmp_path / "capture"
    tool = shutil.which("iverilog")
    assert tool and shutil.which("vvp"), (
        "Actual Icarus required, never skip native RTL controls"
    )
    cmd = [
        sys.executable,
        str(ROOT / "scripts/check_pcie_gen3_continuous_rx_integrity_v21.py"),
        "--out",
        str(out),
        "--max-bytes",
        str(maximum),
        "--iverilog-dir",
        str(Path(tool).parent),
    ]
    if rtl:
        cmd += ["--rtl-dir", str(rtl)]
    if case:
        cmd += ["--test", case]
    with (tmp_path / "launch.log").open("w") as f:
        r = subprocess.run(
            cmd,
            cwd=ROOT,
            stdout=f,
            stderr=subprocess.STDOUT,
            env={**os.environ, "PYTHONDONTWRITEBYTECODE": "1"},
        )
    record = json.loads((out / "result.json").read_text())
    cases = list(ET.parse(out / "results.xml").getroot().iter("testcase"))
    assert len(cases) == 16 and not any(c.find("error") is not None for c in cases)
    selected = [c for c in cases if c.find("skipped") is None]
    assert [c.attrib["name"] for c in selected] == (
        [case] if case else [c.attrib["name"] for c in cases]
    )
    return r, record, selected, out


@pytest.mark.parametrize("maximum", [150, 4118])
def test_actual_wide_rx_full_positive_profiles(tmp_path, maximum):
    result, record, cases, _ = run(tmp_path, maximum)
    assert result.returncode == 0, record
    assert record["tests"] == {"passed": 16, "failed": 0, "skipped": 0}
    assert all(c.find("failure") is None for c in cases)


@pytest.mark.parametrize(
    "name,module,before,after,count,case", FAULTS, ids=[x[0] for x in FAULTS]
)
def test_actual_wide_rx_fault_rejected(
    tmp_path, name, module, before, after, count, case
):
    rtl = tmp_path / "rtl"
    rtl.mkdir()
    for m in MODULES:
        shutil.copyfile(ROOT / "hw/soc/rtl/pcie" / f"{m}.v", rtl / f"{m}.v")
    p = rtl / f"{module}.v"
    text = p.read_text()
    assert text.count(before) == count
    p.write_text(text.replace(before, after))
    result, record, cases, out = run(tmp_path, rtl=rtl, case=case)
    assert result.returncode != 0 and record["status"] == "FAIL"
    assert len(cases) == 1 and cases[0].find("failure") is not None
    assert "AssertionError" in (out / "simulation.log").read_text(), (
        "Compile/runtime errors cannot pass functional controls"
    )
