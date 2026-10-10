# SPDX-FileCopyrightText: 2026 Hasan Melih Akbulut
# SPDX-License-Identifier: Apache-2.0
"""Reject unrelated archives and unsafe extraction before reading native data."""
import copy
import hashlib
import io
from pathlib import Path
import stat
import sys
import warnings
import zipfile

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[2]/"scripts"))
import verify_cloud_supply_artifacts as audit  # noqa: E402


def archive(items):
    stream = io.BytesIO()
    with warnings.catch_warnings():
        warnings.simplefilter("ignore", UserWarning)
        with zipfile.ZipFile(stream, "w") as target:
            for item in items:
                target.writestr(item, b"evidence")
    stream.seek(0)
    return zipfile.ZipFile(stream)


@pytest.mark.parametrize("names", [["../outside"], ["/outside"], ["a/../outside"],
                                  ["a\\outside"], ["a//b"], ["./a"], ["a/"],
                                  ["same", "same"]])
def test_reject_unsafe_or_duplicate_zip_members(names):
    with archive(names) as source, pytest.raises(ValueError, match="Unsafe or duplicate"):
        audit.members(source)


def test_reject_symlink_even_with_safe_name():
    link = zipfile.ZipInfo("checkpoint/manifest.json")
    link.create_system = 3
    link.external_attr = (stat.S_IFLNK | 0o777) << 16
    with archive([link]) as source, pytest.raises(ValueError, match="Unsafe or duplicate"):
        audit.members(source)


def index():
    names = ["supply-tiles-prepared", "supply-prepare-debug-attempt-1",
             "supply-tiled-final-attempt-1"]+[f"supply-tile-{i}-{'a'*64}" for i in range(64)]
    return {"artifacts": [dict(name=n, expired=False, size_in_bytes=1,
                               digest="sha256:"+"b"*64,
                               workflow_run=dict(id=17, head_sha="c"*40)) for n in names]}


def test_complete_index_requires_exact_external_identity():
    assert len(audit.check_index(index(), 17, "c"*40, "a"*64, 1)) == 67


@pytest.mark.parametrize("defect", ["missing", "duplicate", "extra", "run", "commit",
                                   "expired", "digest", "boolean_size", "name"])
def test_reject_incomplete_or_unrelated_artifact_catalog(defect):
    data = copy.deepcopy(index())
    rows = data["artifacts"]
    if defect == "missing":
        rows.pop()
    elif defect == "duplicate":
        rows[-1] = rows[-2]
    elif defect == "extra":
        rows.append(copy.deepcopy(rows[0]))
    elif defect == "run":
        rows[0]["workflow_run"]["id"] = 18
    elif defect == "commit":
        rows[0]["workflow_run"]["head_sha"] = "d"*40
    elif defect == "expired":
        rows[0]["expired"] = True
    elif defect == "digest":
        rows[0]["digest"] = "unverified"
    elif defect == "boolean_size":
        rows[0]["size_in_bytes"] = True
    else:
        rows[0]["name"] = "../supply-tiles-prepared"
    with pytest.raises(ValueError):
        audit.check_index(data, 17, "c"*40, "a"*64, 1)


def test_same_size_corrupt_archive_is_not_accepted(tmp_path):
    path = tmp_path/"artifact.zip"
    path.write_bytes(b"original")
    row = dict(size_in_bytes=8, digest="sha256:"+hashlib.sha256(b"original").hexdigest())
    audit.verify_archive(path, row)
    path.write_bytes(b"tampered")
    with pytest.raises(ValueError, match="digest mismatch"):
        audit.verify_archive(path, row)
    path.write_bytes(b"short")
    with pytest.raises(ValueError, match="size mismatch"):
        audit.verify_archive(path, row)
