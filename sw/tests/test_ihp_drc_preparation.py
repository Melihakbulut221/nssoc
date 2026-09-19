# SPDX-FileCopyrightText: 2026 Hasan Melih Akbulut
# SPDX-License-Identifier: Apache-2.0
"""A verification-deck update must not trust changed or unpinned input bytes."""
import copy
import hashlib
import importlib.util
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
spec = importlib.util.spec_from_file_location(
    "prepare_ihp_drc", ROOT / "hw/soc/flow/prepare_ihp_drc.py")
deck = importlib.util.module_from_spec(spec)
spec.loader.exec_module(deck)


@pytest.fixture
def inputs():
    data = {"rules/main.drc": b"upstream rules\n", "LICENSE": b"upstream license\n"}
    lock = {
        "repository": "https://github.com/IHP-GmbH/IHP-Open-PDK",
        "commit": "a" * 40,
        "entrypoint": "rules/main.drc",
        "files": [{"path": path, "bytes": len(value),
                   "sha256": hashlib.sha256(value).hexdigest()}
                  for path, value in data.items()],
    }
    return lock, data


def test_verified_download_and_offline_cache_reuse(tmp_path, inputs):
    lock, data = inputs
    calls = []

    def fetch(url):
        prefix = "https://raw.githubusercontent.com/IHP-GmbH/IHP-Open-PDK/" + "a" * 40 + "/"
        assert url.startswith(prefix)
        calls.append(url)
        return data[url[len(prefix):]]

    result = deck.prepare(lock, tmp_path, fetch)
    assert result.read_bytes() == data[lock["entrypoint"]]
    assert len(calls) == 2
    deck.prepare(lock, tmp_path, lambda url: pytest.fail("Cache should need no network"))


def test_changed_cache_rejected_before_any_download(tmp_path, inputs):
    lock, data = inputs
    (tmp_path / "LICENSE").write_bytes(b"changed license")
    with pytest.raises(ValueError, match="does not match lock"):
        deck.prepare(lock, tmp_path, lambda url: pytest.fail("Preflight must finish first"))
    assert not (tmp_path / "rules").exists()
    assert (tmp_path / "LICENSE").read_bytes() == b"changed license"


def test_corrupted_download_is_not_written(tmp_path, inputs):
    lock, _ = inputs
    with pytest.raises(ValueError, match="does not match lock"):
        deck.prepare(lock, tmp_path, lambda url: b"wrong bytes")
    assert not list(tmp_path.iterdir())


@pytest.mark.parametrize("bad_path", ["../escape", "/absolute", "rules/../escape", "rules\\escape"])
def test_locked_paths_cannot_escape_output(bad_path, inputs):
    lock, _ = inputs
    lock = copy.deepcopy(lock)
    lock["files"][0]["path"] = bad_path
    with pytest.raises(ValueError, match="Unsafe"):
        deck.validate_lock(lock)


def test_existing_symlink_cannot_redirect_write(tmp_path, inputs):
    lock, _ = inputs
    output = tmp_path / "cache"
    output.mkdir()
    outside = tmp_path / "outside"
    outside.mkdir()
    (output / "rules").symlink_to(outside, target_is_directory=True)
    with pytest.raises(ValueError, match="symlink"):
        deck.prepare(lock, output, lambda url: pytest.fail("Must reject before network"))
    assert not list(outside.iterdir())


def test_floating_revision_and_missing_license_are_rejected(inputs):
    lock, _ = inputs
    wrong = copy.deepcopy(lock)
    wrong["commit"] = "main"
    with pytest.raises(ValueError, match="immutable"):
        deck.validate_lock(wrong)
    wrong = copy.deepcopy(lock)
    wrong["files"] = wrong["files"][:1]
    with pytest.raises(ValueError, match="licence"):
        deck.validate_lock(wrong)
