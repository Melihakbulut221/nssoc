# SPDX-FileCopyrightText: 2026 Hasan Melih Akbulut
# SPDX-License-Identifier: Apache-2.0
"""Reject malformed or changed cloud input bundles before executing tools."""
import hashlib
import io
import json
from pathlib import Path
import sys
import tarfile

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "scripts"))
import run_chip_native_shard as runner


def archive(tmp_path, defect=None):
    payload = b"native-layout"
    name = "input/chip.gds"
    if defect == "traversal": name = "../chip.gds"
    if defect == "absolute": name = "/chip.gds"
    row = dict(bytes=len(payload), sha256=hashlib.sha256(payload).hexdigest())
    if defect == "hash": row["sha256"] = "0" * 64
    if defect == "size": row["bytes"] += 1
    inv = json.dumps({name: row}).encode()
    path = tmp_path / "bundle.tar"
    with tarfile.open(path, "w") as tar:
        entries = [("inventory.json", inv), (name, payload)]
        if defect == "duplicate": entries.append((name, payload))
        if defect == "unlisted": entries.append(("unlisted", b"x"))
        for n, data in entries:
            info = tarfile.TarInfo(n)
            info.size = len(data)
            if defect == "symlink" and n == name:
                info.type = tarfile.SYMTYPE
                info.linkname = "/tmp/foreign"
                info.size = 0
            tar.addfile(info, io.BytesIO(data))
    return path


def test_verified_bundle_roundtrip(tmp_path):
    inv = runner.restore(archive(tmp_path), tmp_path / "restored")
    assert (tmp_path / "restored/input/chip.gds").read_bytes() == b"native-layout"
    assert set(inv) == {"input/chip.gds"}


@pytest.mark.parametrize("defect", ["traversal", "absolute", "hash", "size", "duplicate", "unlisted", "symlink"])
def test_rejects_unsafe_or_changed_members(tmp_path, defect):
    with pytest.raises(ValueError):
        runner.restore(archive(tmp_path, defect), tmp_path / "restored")


def test_does_not_overwrite_existing_restoration(tmp_path):
    out = tmp_path / "restored"
    out.mkdir()
    with pytest.raises(FileExistsError): runner.restore(archive(tmp_path), out)


def test_rejects_missing_shards():
    with pytest.raises(ValueError, match="shard"):
        runner.validate_config(dict(commands={}, catalogs={}))
