# SPDX-FileCopyrightText: 2026 Hasan Melih Akbulut
# SPDX-License-Identifier: Apache-2.0
"""Native port-suite controls for sequence acceptance and actual wire serialization."""

import hashlib
import json
from pathlib import Path
import shutil
import subprocess
import sys
import zlib

import pytest

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "scripts"))
import check_pcie_packet as driver  # noqa: E402


def runtime():
    if (
        not shutil.which("iverilog")
        or not shutil.which("vvp")
        or not (Path(sys.executable).parent / "cocotb-config").is_file()
    ):
        pytest.skip("Native Icarus and this interpreter cocotb are required")


@pytest.mark.parametrize(
    "fault,file,old,new",
    [
        (
            "duplicate_forward",
            "soc_pcie_sequence_rx.v",
            "decided<=1;forward_packet<=expected;",
            "decided<=1;forward_packet<=expected || duplicate;",
        ),
        (
            "bad_tx_seed",
            "soc_pcie_lcrc_tx.v",
            "length<=count+1'b1;state<=PREFIX0;crc<=32'hffffffff;",
            "length<=count+1'b1;state<=PREFIX0;crc<=32'hfffffffe;",
        ),
        (
            "advance_while_stalled",
            "soc_pcie_lcrc_tx.v",
            "if (tx_valid_o && tx_ready_i) begin",
            "if (tx_valid_o) begin",
        ),
        (
            "drop_pending_ack",
            "soc_pcie_sequence_rx.v",
            "if (ack_valid_o && ack_ready_i) ack_valid_o<=0;",
            "if (ack_valid_o) ack_valid_o<=0;",
        ),
    ],
)
def test_actual_endpoint_port_suite_rejects_mutations(tmp_path, fault, file, old, new):
    runtime()
    rtl = tmp_path / "rtl"
    rtl.mkdir()
    for name in driver.SOURCES:
        shutil.copyfile(ROOT / name, rtl / Path(name).name)
    path = rtl / file
    text = path.read_text()
    assert text.count(old) == 1
    path.write_text(text.replace(old, new))
    out = tmp_path / fault
    run = subprocess.run(
        [
            sys.executable,
            str(ROOT / "scripts/check_pcie_packet.py"),
            "--out",
            str(out),
            "--rtl-dir",
            str(rtl),
        ],
        capture_output=True,
        text=True,
        timeout=180,
    )
    result = json.loads((out / "result.json").read_text())
    assert run.returncode and result["returncode"]
    assert result["tests"]["failed"] > 0 and result["tests"]["skipped"] == 0
    assert sum(result["tests"].values()) == 6
    assert (
        result["xml"]["sha256"]
        == hashlib.sha256((out / "results.xml").read_bytes()).hexdigest()
    )


def test_actual_standalone_tx_capacity_and_bad_framing_controls(tmp_path):
    runtime()
    out = tmp_path / "tx"
    subprocess.run(
        [
            sys.executable,
            str(ROOT / "scripts/check_pcie_packet.py"),
            "--unit-tx",
            "--out",
            str(out),
        ],
        check=True,
        capture_output=True,
        text=True,
        timeout=60,
    )
    d = json.loads((out / "result.json").read_text())
    assert d["top"] == "soc_pcie_lcrc_tx" and d["tests"] == {
        "passed": 2,
        "failed": 0,
        "skipped": 0,
    }
    assert d["inputs_rechecked"] is True


def test_mapped_endpoint_cannot_mix_rtl_inputs(tmp_path):
    out = tmp_path / "out"
    run = subprocess.run(
        [
            sys.executable,
            str(ROOT / "scripts/check_pcie_packet.py"),
            "--out",
            str(out),
            "--netlist",
            "mapped.v",
            "--models",
            "model.v",
            "--rtl-dir",
            "rtl",
        ],
        capture_output=True,
        text=True,
    )
    assert run.returncode == 2 and "never mixes RTL" in run.stderr and not out.exists()


@pytest.mark.parametrize(
    "prefix_tlp,wire_crc",
    [
        ("0abc400000010138970f8234503078563412", "ad7c660b"),
        ("0000000000010138970f82345000", "ad595ccd"),
    ],
)
def test_literal_historical_lcrc_wire_vectors(prefix_tlp, wire_crc):
    assert zlib.crc32(bytes.fromhex(prefix_tlp)).to_bytes(4, "little").hex() == wire_crc
