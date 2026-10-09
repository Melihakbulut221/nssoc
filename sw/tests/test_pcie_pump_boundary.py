# SPDX-FileCopyrightText: 2026 Hasan Melih Akbulut
# SPDX-License-Identifier: Apache-2.0
"""Corrupted native-observation controls for the streaming pump reader."""
import gzip
import hashlib
import importlib.util
import json
from pathlib import Path

import numpy as np
import pytest

SPEC = importlib.util.spec_from_file_location(
    "pump_boundary", Path(__file__).resolve().parents[2] / "scripts/compare_pcie_pump_boundary.py"
)
reader = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(reader)


def fixture(directory, fault=""):
    # Cross the reader's block boundary; corrupt an unselected column too.
    values = np.zeros((1026, 3), dtype="<f8")
    values[:, 0] = np.arange(1026) * 1e-12
    values[:, 1] = np.arange(1026)
    if fault == "nonfinite":
        values[1024, 2] = np.nan
    if fault == "time":
        values[1024, 0] = values[1023, 0]
    names = ["time", "v(up)", "v(other)"]
    table = [[str(i), name, "time" if i == 0 else "voltage"] for i, name in enumerate(names)]
    header = "Title: test\nFlags: real\nNo. Variables: 3\nNo. Points: 0\nVariables:\n"
    header += "".join("\t".join(row) + "\n" for row in table) + "Binary:\n"
    payload = values.tobytes()
    raw = header.encode() + payload + (b"wrong" if fault == "trailer" else b"1026")
    if fault == "truncated":
        raw = raw[:-90]
    (directory / "wave.raw.gz").write_bytes(gzip.compress(raw))
    result = {"columns": names, "raw_table": table, "rows": 1026, "raw_bytes": len(raw), "raw_sha256": hashlib.sha256(raw).hexdigest(), "payload_sha256": hashlib.sha256(payload).hexdigest(), "outputs": {"wave.raw.gz": reader.pin(directory / "wave.raw.gz")}, "status": "TEST_FIXTURE"}
    if fault == "digest":
        result["raw_sha256"] = "0" * 64
    if fault == "payload_digest":
        result["payload_sha256"] = "0" * 64
    if fault == "table":
        result["raw_table"][2][1] = "v(wrong)"
    if fault == "columns":
        result["columns"][2] = "v(wrong)"
    if fault == "bytes":
        result["raw_bytes"] += 1
    if fault == "compressed_digest":
        result["outputs"]["wave.raw.gz"]["sha256"] = "0" * 64
    (directory / "result.json").write_text(json.dumps(result))
    return values


def test_streaming_multiblock_selection(tmp_path):
    original = fixture(tmp_path)
    selected, provenance = reader.read_trace(tmp_path, ["time", "v(up)"])
    np.testing.assert_array_equal(selected, original[:, :2])
    assert provenance["rows"] == 1026
    assert provenance["width"] == 3


@pytest.mark.parametrize("fault,match", [
    ("nonfinite", "nonfinite raw"), ("time", "time order"),
    ("trailer", "row-count trailer"), ("truncated", "truncated payload"),
    ("digest", "raw digest"), ("payload_digest", "payload digest"),
    ("table", "header table"), ("columns", "table names"),
    ("bytes", "raw byte count"), ("compressed_digest", "output digest"),
])
def test_corrupted_raw_rejected(tmp_path, fault, match):
    fixture(tmp_path, fault)
    with pytest.raises(ValueError, match=match):
        reader.read_trace(tmp_path, ["time", "v(up)"])


def test_missing_required_observation_rejected(tmp_path):
    fixture(tmp_path)
    with pytest.raises(ValueError, match="missing observation"):
        reader.read_trace(tmp_path, ["time", "v(down)"])
