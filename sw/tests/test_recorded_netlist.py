# SPDX-FileCopyrightText: 2026 Hasan Melih Akbulut
# SPDX-License-Identifier: Apache-2.0
"""An available snapshot must not mask corrupt bytes or a changed live run."""
import gzip
import hashlib
import json

import pytest
from evidence import recorded_netlist


def sha(data):
    return hashlib.sha256(data).hexdigest()


@pytest.fixture
def snapshot(tmp_path):
    raw = b"module soc_top(input wire clk); endmodule\n"
    packed = gzip.compress(raw, mtime=0)
    (tmp_path / "snapshot.v.gz").write_bytes(packed)
    (tmp_path / "NOTICES.txt").write_bytes(b"Synthetic test fixture\n")
    record = {
        "archive": {"file": "snapshot.v.gz", "bytes": len(packed), "sha256": sha(packed)},
        "netlist": {"original_path": "live/soc_top.nl.v", "bytes": len(raw), "sha256": sha(raw)},
        "component_notices": {"file": "NOTICES.txt", "sha256": sha(b"Synthetic test fixture\n")},
    }
    meta = tmp_path / "snapshot.json"
    meta.write_text(json.dumps(record))
    output = tmp_path / "output"
    output.mkdir()
    return meta, output, record, raw


def test_absent_run_uses_actual_recorded_bytes(snapshot, tmp_path):
    meta, output, _, raw = snapshot
    assert recorded_netlist(meta, output, tmp_path).read_bytes() == raw


def test_changed_live_run_is_not_silently_replaced(snapshot, tmp_path):
    meta, output, _, raw = snapshot
    live = tmp_path / "live/soc_top.nl.v"
    live.parent.mkdir()
    live.write_bytes(raw)
    assert recorded_netlist(meta, output, tmp_path).read_bytes() == raw
    (output / "soc_top.nl.v").unlink()
    live.write_bytes(b"wrong live graph")
    with pytest.raises(AssertionError, match="Live run differs"):
        recorded_netlist(meta, output, tmp_path)
    assert not list(output.iterdir())


@pytest.mark.parametrize("field,value,reason", [
    ("archive.sha256", "0" * 64, "Archive digest"),
    ("archive.file", "../outside.gz", "Unsafe archive"),
    ("netlist.sha256", "0" * 64, "Netlist digest"),
    ("netlist.bytes", 10, "Decompressed size"),
    ("netlist.bytes", 100 * 1024 * 1024, "Invalid netlist size"),
    ("netlist.original_path", "../outside.v", "Unsafe live"),
    ("component_notices.sha256", "0" * 64, "Component notices"),
])
def test_invalid_evidence_cannot_become_a_netlist(snapshot, tmp_path, field, value, reason):
    meta, output, record, _ = snapshot
    section, key = field.split(".")
    record[section][key] = value
    meta.write_text(json.dumps(record))
    with pytest.raises(AssertionError, match=reason):
        recorded_netlist(meta, output, tmp_path)
    assert not list(output.iterdir())


def test_existing_output_is_never_overwritten(snapshot, tmp_path):
    meta, output, _, _ = snapshot
    target = output / "soc_top.nl.v"
    target.write_text("keep this file")
    with pytest.raises(FileExistsError):
        recorded_netlist(meta, output, tmp_path)
    assert target.read_text() == "keep this file"
