# SPDX-FileCopyrightText: 2026 Hasan Melih Akbulut
# SPDX-License-Identifier: Apache-2.0
"""Actual HDL counterexamples at wide owned-DLLP public ports."""

import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import xml.etree.ElementTree as ET
import pytest

ROOT = Path(__file__).resolve().parents[2]
SRC = ROOT / "hw/soc/rtl/pcie/soc_pcie_gen3_dllp_consumer_v3.v"
DENSE = "sustained_two_dllps_per_cycle_and_sequence_wrap"
MIX = "mixed_fields_bad_null_and_independent_stalls"
HOLD = "exact_id_full_replace_and_held_generation"
FAULTS = (
    (
        "one_event",
        "for(j=0;j<4;j=j+1) begin\n       a=(event_next+j)&63;",
        "for(j=0;j<1;j=j+1) begin\n       a=(event_next+j)&63;",
        1,
        DENSE,
    ),
    (
        "ack_order",
        "event_ack_n[j*12+:12]={word_value[19:16],word_value[31:24]};",
        "event_ack_n[j*12+:12]={word_value[31:24],word_value[19:16]};",
        1,
        DENSE,
    ),
    (
        "fc_header",
        "{word_value[13:8],word_value[23:22]}",
        "{word_value[23:22],word_value[13:8]}",
        1,
        MIX,
    ),
    (
        "fc_data",
        "event_fc_data_n[j*12+:12]={word_value[19:16],word_value[31:24]};",
        "event_fc_data_n[j*12+:12]=0;",
        1,
        MIX,
    ),
    (
        "fc_phase",
        "kind[7:6]==1?0:kind[7:6]==3?1:2",
        "kind[7:6]==1?2:kind[7:6]==3?1:0",
        1,
        MIX,
    ),
    (
        "bad_crc_action",
        "if(nb[a]) event_kind_n[j*4+:4]=1;",
        "if(nb[a]) event_kind_n[j*4+:4]=3;",
        1,
        MIX,
    ),
    (
        "owner_generation_alias",
        "a=(event_next+j)&63;",
        "a=(event_next+j)&31;",
        1,
        DENSE,
    ),
    ("held_event_freed", "event_count!=0 && event_ready_i", "event_count!=0", 1, HOLD),
    (
        "held_body_id_reused",
        "!released[body_owner_i[c*6+:6]]) body_space=0;",
        "!released[body_owner_i[c*6+:6]]) body_space=1;",
        1,
        HOLD,
    ),
    ("tlp_owner_lost", "tlp_valid_o?body_owner_i:0", "0", 1, MIX),
    (
        "descriptor_order_unchecked",
        "id!=desc_next ||",
        "1'b0 ||",
        1,
        "malformed_ownership_fails_closed_then_epoch_restarts",
    ),
    (
        "epoch_never_restarts",
        "else if(flush_i || epoch_i!=epoch)",
        "else if(flush_i)",
        1,
        "epoch_invalidates_both_halves_and_held_events",
    ),
    ("body_not_awaited", "(!ng[a] || nf[a])", "1'b1", 1, MIX),
    (
        "unsupported_vc_accepted",
        "kind==8'h40 || kind==8'h50",
        "kind==8'h40 || kind==8'h41 || kind==8'h50",
        1,
        "body_before_descriptor_reserved_bits_and_unknown_vc",
    ),
)


def run(tmp, rtl=None, case=None, top=None, wrapper=None):
    tool = shutil.which("iverilog")
    assert tool and shutil.which("vvp"), "Actual Icarus required"
    out = tmp / "capture"
    cmd = [
        sys.executable,
        str(ROOT / "scripts/check_pcie_gen3_dllp_consumer_v3.py"),
        "--out",
        str(out),
        "--iverilog-dir",
        str(Path(tool).parent),
    ]
    if rtl:
        cmd += ["--rtl", str(rtl)]
    if case:
        cmd += ["--test", case]
    if top:
        cmd += ["--top", top]
    if wrapper:
        cmd += ["--wrapper-rtl", str(wrapper)]
    with (tmp / "launch.log").open("w") as f:
        result = subprocess.run(
            cmd,
            cwd=ROOT,
            stdout=f,
            stderr=subprocess.STDOUT,
            env={**os.environ, "PYTHONDONTWRITEBYTECODE": "1"},
        )
    r = json.loads((out / "result.json").read_text())
    rows = list(ET.parse(out / "results.xml").getroot().iter("testcase"))
    return result, r, [x for x in rows if x.find("skipped") is None], out


@pytest.mark.parametrize(
    "top", ["soc_pcie_gen3_dllp_consumer_v3", "soc_pcie_gen3_rx_events_v3"]
)
def test_actual_positive_ports(tmp_path, top):
    result, r, rows, _ = run(tmp_path, top=top)
    assert (
        result.returncode == 0 and r["status"] == "PASS_ACTUAL_WIDE_DLLP_CONSUMER_RTL"
    ), r
    assert len(rows) == (6 if top.endswith("consumer_v3") else 3)
    assert all(x.find("failure") is None for x in rows)


@pytest.mark.parametrize(
    "name,before,after,count,case", FAULTS, ids=[x[0] for x in FAULTS]
)
def test_actual_hdl_fault_rejected(tmp_path, name, before, after, count, case):
    text = SRC.read_text()
    assert text.count(before) == count
    rtl = tmp_path / "mutant.v"
    rtl.write_text(text.replace(before, after))
    result, r, rows, out = run(tmp_path, rtl, case)
    assert result.returncode != 0 and r["status"] == "FAIL"
    assert len(rows) == 1 and rows[0].find("failure") is not None
    assert "AssertionError" in (out / "simulation.log").read_text(), (
        "Compilation/runtime failure is not functional rejection"
    )


def test_actual_wrapper_abort_mask_fault_rejected(tmp_path):
    source = ROOT / "hw/soc/rtl/pcie/soc_pcie_gen3_rx_events_v3.v"
    before = ".flush_i(flush_i || stream_start_i || stream_abort_i)"
    text = source.read_text()
    assert text.count(before) == 1
    mutant = tmp_path / "wrapper.v"
    mutant.write_text(text.replace(before, ".flush_i(flush_i || stream_start_i)"))
    result, r, rows, out = run(
        tmp_path,
        case="held_event_abort_ready_same_edge_discards_old_epoch",
        top="soc_pcie_gen3_rx_events_v3",
        wrapper=mutant,
    )
    assert result.returncode != 0 and r["status"] == "FAIL"
    assert len(rows) == 1 and rows[0].find("failure") is not None
    assert (
        "Old DLLP event can handshake on explicit abort edge"
        in (out / "simulation.log").read_text()
    )
