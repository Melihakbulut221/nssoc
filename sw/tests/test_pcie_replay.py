# SPDX-FileCopyrightText: 2026 Hasan Melih Akbulut
# SPDX-License-Identifier: Apache-2.0
"""Executable protocol faults must be detected by independent port scoreboards."""

from pathlib import Path
import ast
import xml.etree.ElementTree as ET
import os
import shutil
import subprocess
import sys

import pytest

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "scripts"))
from check_pcie_integrity import tool_environment  # noqa: E402
from cocotb_results import count_results  # noqa: E402


@pytest.mark.parametrize(
    "module,old,new,case",
    [
        (
            "soc_pcie_replay_tx",
            "new_slot<=advance(new_slot,1);",
            "new_slot<=advance(new_slot,2);",
            "full_queue",
        ),
        (
            "soc_pcie_replay_tx",
            "else next_store_sequence_plus_one<=next_store_sequence+12'd1;",
            "else next_store_sequence_plus_one<=next_store_sequence+12'd2;",
            "full_queue",
        ),
        (
            "soc_pcie_replay_tx",
            "else next_store_sequence_plus_one<=next_store_sequence+12'd1;",
            "else next_store_sequence_plus_one<={4'b0,next_store_sequence[7:0]+8'd1};",
            "modulo_wrap_4097",
        ),
        (
            "soc_pcie_dllp_rx",
            "trailer!=~crc[7:0] || rx_data_i!=~crc[15:8]",
            "1'b0",
            "corruption_reserved",
        ),
        (
            "soc_pcie_dllp_rx",
            "fc_header_o<={b1[5:0],b2[7:6]}",
            "fc_header_o<={b1[5:0],b2[6:5]}",
            "exhaustive_ack",
        ),
        (
            "soc_pcie_replay_tx",
            "ack_delta<=sent_count && ack_delta!=0",
            "ack_delta<=count && ack_delta!=0",
            "full_queue",
        ),
        ("soc_pcie_replay_tx", "count<=count-ack_delta", "count<=count", "full_queue"),
        (
            "soc_pcie_replay_tx",
            "assign tx_data_o=bytes[send_slot*MAX_BYTES+read_pos];",
            "assign tx_data_o=bytes[send_slot*MAX_BYTES+read_pos] ^ {7'b0,sending_replay};",
            "full_queue",
        ),
        (
            "soc_pcie_replay_tx",
            "!capturing && !timer_expiring && !replay_active",
            "!timer_expiring && !replay_active",
            "pending_ack",
        ),
        (
            "soc_pcie_replay_tx",
            "!capturing && !timer_expiring && !replay_active",
            "!capturing && !replay_active",
            "expiry_preempts",
        ),
        (
            "soc_pcie_replay_tx",
            "if(retries==MAX_REPLAYS)",
            "if(1'b0)",
            "timeout_duplicate",
        ),
        (
            "soc_pcie_replay_tx",
            "wire ack_allowed=ack_observed ? ack_was_allowed : current_ack_allowed;",
            "wire ack_allowed=current_ack_allowed;",
            "early_ack_is_classified",
        ),
        (
            "soc_pcie_reliable_packets",
            "wire choice=locked ? owner :",
            "wire choice=1'b0 ? owner :",
            "stalled_replay_first",
        ),
    ],
)
def test_real_port_scoreboard_rejects_protocol_mutation(
    tmp_path, module, old, new, case
):
    executable = shutil.which("iverilog")
    if not executable or not (Path(sys.executable).parent / "cocotb-config").is_file():
        pytest.skip("Actual Icarus and cocotb Python required")
    rtl = tmp_path / "rtl"
    rtl.mkdir()
    for source in (ROOT / "hw/soc/rtl/pcie").glob("*.v"):
        shutil.copyfile(source, rtl / source.name)
    path = rtl / (module + ".v")
    text = path.read_text()
    assert text.count(old) == 1
    path.write_text(text.replace(old, new))
    if module == "soc_pcie_dllp_rx":
        names = ["soc_pcie_crc16_byte", module]
    elif module == "soc_pcie_replay_tx":
        names = ["soc_pcie_crc32_byte", module]
    else:
        names = [
            "soc_pcie_crc16_byte",
            "soc_pcie_acknak_tx",
            "soc_pcie_packet_tx",
            "soc_pcie_crc32_byte",
            "soc_pcie_lcrc_rx",
            "soc_pcie_sequence_rx",
            "soc_pcie_lcrc_tx",
            "soc_pcie_packet_endpoint",
            "soc_pcie_tlp_stream",
            "soc_pcie_tlp_regs",
            "soc_pcie_link_packets",
            "soc_pcie_dllp_rx",
            "soc_pcie_replay_tx",
            module,
        ]
    env = tool_environment(Path(executable).parent)
    env["COCOTB_TEST_FILTER"] = case
    env["PYTHONDONTWRITEBYTECODE"] = "1"
    command = [
        "make",
        "-f",
        str(ROOT / "hw/soc/tb/cocotb" / ("Makefile." + module)),
        "VERILOG_SOURCES=" + " ".join(str(rtl / (n + ".v")) for n in names),
        "SIM_BUILD=" + str(tmp_path / "sim"),
        "COCOTB_RESULTS_FILE=" + str(tmp_path / "results.xml"),
    ]
    with (tmp_path / "mutation.log").open("w") as log:
        run = subprocess.run(
            command,
            cwd=tmp_path,
            env=env,
            stdout=log,
            stderr=subprocess.STDOUT,
            timeout=90,
        )
    assert run.returncode != 0
    bench = ROOT / "hw/soc/tb/cocotb" / ("test_" + module + ".py")
    total = sum(
        isinstance(n, ast.AsyncFunctionDef) and bool(n.decorator_list)
        for n in ast.parse(bench.read_text()).body
    )
    # Cocotb records nonselected cases as skipped. Exactly the requested case
    # must execute and fail, not a simulator/setup failure or another test.
    assert count_results([tmp_path / "results.xml"]) == (0, 1, total - 1)
    failed = [
        t
        for t in ET.parse(tmp_path / "results.xml").iter("testcase")
        if t.find("failure") is not None
    ]
    assert len(failed) == 1 and case in failed[0].attrib["name"]
    assert "AssertionError" in (tmp_path / "mutation.log").read_text()


def test_new_replay_is_separate_from_frozen_link():
    text = (ROOT / "hw/soc/rtl/pcie/soc_pcie_reliable_packets.v").read_text()
    assert "soc_pcie_link_packets #" in text
    assert "soc_pcie_credit_tx " not in text
    assert "input wire reserve_ready_i" in text
