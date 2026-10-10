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
    "soc_pcie_gen3_ingress",
    "soc_pcie_gen3_data_descrambler",
    "soc_pcie_gen3_framer_rx_owned_v2",
    "soc_pcie_gen3_continuous_rx_owned_v2",
)
F = "soc_pcie_gen3_framer_rx_owned_v2"
DENSE = "sustained_minimum_packets_exceed_every_buffer"
FAULTS = (
    ("three_steps", F, "for(j=0;j<4;j=j+1)", "for(j=0;j<3;j=j+1)", 1, DENSE),
    (
        "lost_same_edge_block_activation",
        F,
        "if(!current_valid || (last_slice && !next_valid))",
        "if(!current_valid)",
        1,
        DENSE,
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
    (
        "zero_body_lost",
        F,
        "TLP:begin\n             lcrc_n=crc32_32(lcrc_n,word);\n             write_data[j*32+:32]=word;write_keep[j*4+:4]=4'b1111;",
        "TLP:begin\n             lcrc_n=crc32_32(lcrc_n,word);\n             write_data[j*32+:32]=word;write_keep[j*4+:4]=(word==0)?4'b0000:4'b1111;",
        1,
        "maximum_zero_packets_cross_blocks_and_verdict_wrap",
    ),
    (
        "one_completion_event",
        F,
        "event_good[j]=(dllp_crc_n==16'h556f);",
        "event_good[0]=(dllp_crc_n==16'h556f);",
        1,
        DENSE,
    ),
    (
        "denied_full_replace",
        F,
        "+released_dwords",
        "+0",
        1,
        "actual_full_ring_replacement_and_late_stall_overflow",
    ),
    (
        "held_output_register_corruption",
        F,
        "if(!output_valid || ready_i) output_valid<=0;",
        "if(output_valid && !ready_i) output_data<=output_data^128'b1; if(!output_valid || ready_i) output_valid<=0;",
        1,
        "bounded_stalls_preserve_all_wide_metadata",
    ),
    (
        "verdict_wrap_alias",
        F,
        "tag_n=position;",
        "tag_n={1'b0,position[AW-1:0]};",
        2,
        "verdict_tag_reuse_cannot_nullify_an_older_live_tail",
    ),
    (
        "eds_loses_pending_packet",
        F,
        "if(ending_n) begin current_valid<=0;next_valid<=0;end",
        "if(ending_n) begin current_valid<=0;next_valid<=0;active_o<=0;end",
        1,
        "edb_quarantine_and_eds_release_drain",
    ),
    (
        "bad_block_header_ignored",
        F,
        "(headers_i!=8'haa || block_error_i)",
        "block_error_i",
        1,
        "malformed_tokens_and_headers_never_release_quarantine",
    ),
    (
        "bad_stp_crc_ignored",
        F,
        "crc==word[23:20]",
        "1'b1",
        1,
        "malformed_tokens_and_headers_never_release_quarantine",
    ),
    (
        "wrong_raw_lane",
        "soc_pcie_gen3_ingress",
        "word_i[lane*32+:32]",
        "word_i[((lane+1)%4)*32+:32]",
        1,
        DENSE,
    ),
    (
        "wrong_lfsr_advance",
        "soc_pcie_gen3_data_descrambler",
        "mask(128,bit_number)",
        "mask(127,bit_number)",
        1,
        DENSE,
    ),
    (
        "restart_without_reseed",
        "soc_pcie_gen3_continuous_rx_owned_v2",
        "transport_flush || stream_start_i",
        "transport_flush",
        1,
        "start_without_abort_reseeds_and_discards_prior_epoch",
    ),
)


CRC_CASE = "tlp_crc_coverage_residue_nullification_and_successor"
DLLP_CASE = "primary_trace_crc_vectors_and_adjacent_bad_dllps"
FAULTS += (
    ("lcrc_initial_zero", F, "crc32_16(32'hffffffff,", "crc32_16(32'b0,", 1, CRC_CASE),
    (
        "sequence_byte_order",
        F,
        "crc32_16(32'hffffffff,{word[31:24],4'b0,word[19:16]})",
        "crc32_16(32'hffffffff,{4'b0,word[19:16],word[31:24]})",
        1,
        CRC_CASE,
    ),
    (
        "lcrc_misses_last_word",
        F,
        "lcrc_n=crc32_32(lcrc_n,word);",
        "if(remaining_n!=1) lcrc_n=crc32_32(lcrc_n,word);",
        1,
        CRC_CASE,
    ),
    ("ordinary_lcrc_not_checked", F, "(lcrc_n==32'hdebb20e3)", "1'b1", 2, CRC_CASE),
    ("edb_ignores_inverted_lcrc", F, "(lcrc_n==32'b0)", "1'b1", 1, CRC_CASE),
    (
        "wrong_dllp_residue_reproduces_first_failure",
        F,
        "16'h556f",
        "16'h555f",
        3,
        DLLP_CASE,
    ),
    ("dllp_seed_zero", F, "crc16_16(16'hffff,", "crc16_16(16'b0,", 1, DLLP_CASE),
    (
        "dllp_body_order",
        F,
        "crc16_16(16'hffff,word[31:16])",
        "crc16_16(16'hffff,{word[23:16],word[31:24]})",
        1,
        DLLP_CASE,
    ),
    (
        "crc_failure_is_good",
        F,
        "event_crc_bad[j]=(lcrc_n!=32'hdebb20e3)",
        "event_good[j]=(lcrc_n!=32'hdebb20e3)",
        1,
        CRC_CASE,
    ),
    ("event_type_lost", F, "event_dllp[j]=1", "event_dllp[j]=0", 1, DLLP_CASE),
)


OWNED_CASE = "ownership_long_generation_sequence_wrap"
FAULTS += (
    (
        "owner_body_ignored",
        F,
        "(owner_body_taken[ot] || body_taken_now[ot])",
        "1'b1",
        1,
        "held_body_prevents_owner_slot_reuse",
    ),
    (
        "owner_descriptor_ignored",
        F,
        "(owner_desc_taken[ot] || desc_taken_now[ot])",
        "1'b1",
        1,
        "bad_descriptors_fill_owner_slots_fail_closed",
    ),
    (
        "bad_descriptor_missing",
        F,
        "owner_done[verdict_owners[oi*OW+:OW] & (OWNER_SLOTS-1)]<=1;",
        "owner_done[verdict_owners[oi*OW+:OW] & (OWNER_SLOTS-1)]<=event_good[oi];",
        1,
        OWNED_CASE,
    ),
    (
        "null_descriptor_missing",
        F,
        "owner_null[verdict_owners[oi*OW+:OW] & (OWNER_SLOTS-1)]<=event_nullified[oi];",
        "owner_null[verdict_owners[oi*OW+:OW] & (OWNER_SLOTS-1)]<=0;",
        1,
        OWNED_CASE,
    ),
    (
        "wrong_body_owner",
        F,
        "read_owner[r*OW+:OW]=slot_owner[read_address];",
        "read_owner[r*OW+:OW]=0;",
        1,
        OWNED_CASE,
    ),
    (
        "descriptor_generation_lost",
        F,
        "descriptor_read_owner[od*OW+:OW]=owner_identity[oa];",
        "descriptor_read_owner[od*OW+:OW]=owner_identity[oa] & (OWNER_SLOTS-1);",
        1,
        OWNED_CASE,
    ),
    (
        "held_descriptor_overwrite",
        F,
        "if(descriptor_count==0 || descriptor_ready_i)",
        "if(1'b1)",
        1,
        "descriptors_hold_while_body_drains",
    ),
    (
        "held_body_frees_ring",
        F,
        "wire body_pop=enabled && active_o && output_valid && ready_i;",
        "wire body_pop=enabled && active_o && output_valid;",
        1,
        "body_holds_after_descriptors_retired",
    ),
    (
        "wrong_descriptor_length",
        F,
        "descriptor_read_bytes[od*13+:13]=owner_bytes[oa];",
        "descriptor_read_bytes[od*13+:13]=owner_bytes[oa]+1'b1;",
        1,
        OWNED_CASE,
    ),
    (
        "descriptor_pointer_stuck",
        F,
        "if(descriptor_pop) descriptor_ptr<=descriptor_read_ptr;",
        "if(descriptor_pop) descriptor_ptr<=descriptor_ptr;",
        1,
        OWNED_CASE,
    ),
    (
        "owner_capacity_ignored",
        F,
        "owner_full_now=1;",
        "owner_full_now=0;",
        2,
        "bad_descriptors_fill_owner_slots_fail_closed",
    ),
    (
        "same_edge_owner_free_denied",
        F,
        " && !release_now[allocate_n & (OWNER_SLOTS-1)]",
        "",
        2,
        "same_edge_descriptor_release_allows_full_owner_replace",
    ),
)


def run(tmp_path, maximum=150, rtl=None, case=None):
    out = tmp_path / "capture"
    tool = shutil.which("iverilog")
    assert tool and shutil.which("vvp"), (
        "Actual Icarus required, never skip native RTL controls"
    )
    cmd = [
        sys.executable,
        str(ROOT / "scripts/check_pcie_gen3_continuous_rx_owned_v2.py"),
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
    assert len(cases) == 20 and not any(c.find("error") is not None for c in cases)
    selected = [c for c in cases if c.find("skipped") is None]
    assert [c.attrib["name"] for c in selected] == (
        [case] if case else [c.attrib["name"] for c in cases]
    )
    return r, record, selected, out


@pytest.mark.parametrize("maximum", [150, 4118])
def test_actual_wide_rx_full_positive_profiles(tmp_path, maximum):
    result, record, cases, _ = run(tmp_path, maximum)
    assert result.returncode == 0, record
    assert record["tests"] == {"passed": 20, "failed": 0, "skipped": 0}
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
    result, record, cases, out = run(
        tmp_path,
        maximum=4118 if name == "owner_body_ignored" else 150,
        rtl=rtl,
        case=case,
    )
    assert result.returncode != 0 and record["status"] == "FAIL"
    assert len(cases) == 1 and cases[0].find("failure") is not None
    assert "AssertionError" in (out / "simulation.log").read_text(), (
        "Compile/runtime errors cannot pass functional controls"
    )
