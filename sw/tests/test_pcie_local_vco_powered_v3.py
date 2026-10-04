# SPDX-FileCopyrightText: 2026 Hasan Melih Akbulut
# SPDX-License-Identifier: Apache-2.0
"""Actual FIFO writer-exit/drain resource failures and unchanged analog recipe."""

import gzip
import hashlib
import inspect
import json
from pathlib import Path
import sys

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "scripts"))
import diagnose_pcie_local_vco_powered_v2 as prior
import diagnose_pcie_local_vco_powered_v3 as method


def test_measurement_and_native_deck_are_identical_to_frozen_v2():
    for name in (
        "deck",
        "wave_measure",
        "audit_native",
        "vector_contract",
        "physical_to_ideal",
        "circuit",
        "node_expression",
    ):
        assert inspect.getsource(getattr(method, name)) == inspect.getsource(
            getattr(prior, name)
        )
    assert method.STOP == prior.STOP == 12e-9
    assert method.STEP == prior.STEP == 1e-12
    assert method.BEGIN == prior.BEGIN == 6e-9
    assert method.INPUT_PINS == prior.INPUT_PINS
    assert method.METHOD_SHA == prior.METHOD_SHA
    assert method.OWN_LIMIT == 80 * 1024**2
    assert method.SHARED_RESERVE == 512 * 1024**2


def writer(path, count):
    path.write_text(
        "#!/usr/bin/python3\nimport random\n"
        f"data=random.Random(17).randbytes({count})\n"
        "with open('wave.fifo','wb',buffering=0) as f:f.write(data)\n"
    )
    path.chmod(0o700)


@pytest.mark.parametrize("fault", [None, "owned_drain", "shared_drain"])
def test_actual_writer_exits_before_final_chunk_budget_decision(
    tmp_path, monkeypatch, fault
):
    root = tmp_path / "case"
    root.mkdir()
    program = tmp_path / "writer"
    writer(program, 200_000)
    monkeypatch.setattr(method, "owned_size", lambda _: method.regular_size(root))
    monkeypatch.setattr(
        method,
        "shared_free",
        lambda: 1024**3 if fault != "shared_drain" else 512 * 1024**2 + 20_000,
    )
    monkeypatch.setattr(
        method, "OWN_LIMIT", 180_000 if fault == "owned_drain" else 400_000
    )
    monkeypatch.setattr(method, "RECEIPT_RESERVE", 32_768)
    row = dict(stream={}, resources=[])
    method.run_native(root, program, root, lambda: None, row)
    assert row["returncode"] == 0  # Actual producer completed normally.
    assert not (root / "wave.fifo").exists()
    assert row["post_drain_resources"]["owned_bytes"] == method.regular_size(root)
    assert row["post_drain_resources"]["owned_bytes"] <= method.OWN_LIMIT
    if fault is None:
        assert row["resource_stop"] is None and row["stream"]["complete"]
        raw = gzip.decompress((root / "wave.dat.gz").read_bytes())
        assert len(raw) == 200_000
        assert hashlib.sha256(raw).hexdigest() == row["stream"]["raw_sha256"]
    else:
        assert not row["stream"].get("complete")
        assert row["stream"].get("error")
        assert row["resource_stop"] == (
            "OWN_80MIB_FINAL_DRAIN_RESERVE"
            if fault == "owned_drain"
            else "SHARED_512MIB_FINAL_DRAIN_RESERVE"
        )
    (root / "control-result.json").write_text(
        json.dumps(
            dict(
                fault=fault,
                actual_native_writer_completed=True,
                row=row,
                method_sha256=hashlib.sha256(
                    Path(method.__file__).read_bytes()
                ).hexdigest(),
            ),
            indent=2,
        )
        + "\n"
    )


def test_actual_multiple_chunk_output_cannot_spend_receipt_reserve(
    tmp_path, monkeypatch
):
    import random

    source = tmp_path / "raw"
    source.write_bytes(random.Random(23).randbytes(3 * 1024**2))
    out = tmp_path / "out"
    out.mkdir()
    monkeypatch.setattr(method, "owned_size", lambda _: method.regular_size(out))
    monkeypatch.setattr(method, "shared_free", lambda: 1024**3)
    monkeypatch.setattr(method, "OWN_LIMIT", 2 * 1024**2)
    monkeypatch.setattr(method, "RECEIPT_RESERVE", 256 * 1024)
    record = {}
    method.stream_wave(source, out / "wave.gz", record, out)
    assert record["resource_stop"] == "OWN_80MIB_FINAL_DRAIN_RESERVE"
    assert not record.get("complete")
    assert 0 < method.regular_size(out) <= method.OWN_LIMIT - method.RECEIPT_RESERVE
    assert record["peak_owned_bytes"] == method.regular_size(out)
    (out / "control-result.json").write_text(
        json.dumps(
            dict(
                status="EXPECTED_PREWRITE_RESOURCE_REJECTION",
                stream=record,
                raw_input_sha256=hashlib.sha256(source.read_bytes()).hexdigest(),
                method_sha256=hashlib.sha256(
                    Path(method.__file__).read_bytes()
                ).hexdigest(),
            ),
            indent=2,
        )
        + "\n"
    )
