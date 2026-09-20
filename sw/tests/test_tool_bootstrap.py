# SPDX-FileCopyrightText: 2026 Hasan Melih Akbulut
# SPDX-License-Identifier: Apache-2.0
"""Installer rollback/integrity and make resolution, with no network access."""
import hashlib
import importlib.util
import io
import os
from pathlib import Path
import shutil
import subprocess
import tarfile

import pytest

ROOT = Path(__file__).resolve().parents[2]
spec = importlib.util.spec_from_file_location("bootstrap_oss", ROOT / "scripts/bootstrap_oss.py")
bootstrap = importlib.util.module_from_spec(spec)
spec.loader.exec_module(bootstrap)


def archive_fixture(tmp_path, monkeypatch, *, omit=None, escape=False):
    archive = tmp_path / "fixture.tgz"
    with tarfile.open(archive, "w:gz") as bundle:
        entries = {"VERSION": bootstrap.VERSION.encode()}
        entries.update({"bin/" + name: b"#!/bin/sh\nexit 0\n" for name in bootstrap.BINARIES
                        if name != omit})
        if escape:
            entries["../../outside.txt"] = b"must not escape"
        for name, content in entries.items():
            entry = tarfile.TarInfo("oss-cad-suite/" + name)
            entry.mode = 0o755 if name.startswith("bin/") else 0o644
            entry.size = len(content)
            bundle.addfile(entry, io.BytesIO(content))
    monkeypatch.setattr(bootstrap, "ARCHIVE_SIZE", archive.stat().st_size)
    monkeypatch.setattr(bootstrap, "ARCHIVE_SHA256", hashlib.sha256(archive.read_bytes()).hexdigest())
    return archive


@pytest.fixture(autouse=True)
def forbid_network(monkeypatch):
    def forbidden(*args, **kwargs):
        raise AssertionError("test attempted network access")
    monkeypatch.setattr(bootstrap.urllib.request, "urlopen", forbidden)


def test_install_checked_archive_and_refuse_existing_target(tmp_path, monkeypatch):
    if not hasattr(tarfile, "data_filter"):
        pytest.skip("safe tar extraction requires Python 3.12 or its backport")
    archive = archive_fixture(tmp_path, monkeypatch)
    destination = tmp_path / "tools with spaces" / "oss-cad-suite"
    assert bootstrap.install(destination, archive) == destination
    assert (destination / "VERSION").read_text() == bootstrap.VERSION
    assert all(os.access(destination / "bin" / name, os.X_OK) for name in bootstrap.BINARIES)
    marker = destination / "keep-user-data"
    marker.write_text("preserved")
    with pytest.raises(FileExistsError, match="Refusing to replace"):
        bootstrap.install(destination, archive)
    assert marker.read_text() == "preserved"
    assert not list(destination.parent.glob(".oss-install-*"))
    assert not destination.with_name(destination.name + ".install-lock").exists()


@pytest.mark.parametrize("kind", ["size", "sha256"])
def test_archive_integrity_failure_leaves_no_install(tmp_path, monkeypatch, kind):
    archive = archive_fixture(tmp_path, monkeypatch)
    payload = bytearray(archive.read_bytes())
    if kind == "size": payload.append(0)
    else: payload[-1] ^= 1
    archive.write_bytes(payload)
    destination = tmp_path / "installed"
    with pytest.raises(ValueError, match="pinned release"):
        bootstrap.install(destination, archive)
    assert not destination.exists()
    assert not (tmp_path / "installed.install-lock").exists()
    assert not list(tmp_path.glob(".oss-install-*"))


@pytest.mark.parametrize("failure", ["missing_binary", "escape"])
def test_bad_extraction_rolls_back(tmp_path, monkeypatch, failure):
    if not hasattr(tarfile, "data_filter"):
        pytest.skip("safe tar extraction requires Python 3.12 or its backport")
    archive = archive_fixture(tmp_path, monkeypatch,
                              omit="yosys" if failure == "missing_binary" else None,
                              escape=failure == "escape")
    with pytest.raises((ValueError, tarfile.TarError)):
        bootstrap.install(tmp_path / "installed", archive)
    assert not (tmp_path / "installed").exists()
    assert not (tmp_path / "outside.txt").exists()
    assert not list(tmp_path.glob(".oss-install-*"))


def test_existing_lock_and_symlink_are_preserved(tmp_path, monkeypatch):
    archive = archive_fixture(tmp_path, monkeypatch)
    lock = tmp_path / "target.install-lock"
    lock.mkdir()
    with pytest.raises(FileExistsError):
        bootstrap.install(tmp_path / "target", archive)
    assert lock.is_dir()
    link = tmp_path / "symlink"
    link.symlink_to(tmp_path / "not-present")
    with pytest.raises(FileExistsError):
        bootstrap.install(link, archive)
    assert link.is_symlink()


@pytest.mark.parametrize("override", [None, "explicit"])
def test_make_resolves_one_checkout_from_any_working_directory(tmp_path, override):
    make = shutil.which("make")
    if not make: pytest.skip("make is not installed")
    env = dict(os.environ)
    env.pop("OSS_CAD_SUITE", None)
    selected = ROOT / "hw/soc/tools/oss-cad-suite" if override is None else tmp_path / "selected"
    if override: env["OSS_CAD_SUITE"] = str(selected)
    # A nonexistent explicit checkout must not fall back to installed PATH tools.
    result = subprocess.run([make, "-s", "-f", str(ROOT / "tools.mk"),
                             "--eval", "resolution:\n\t@echo $(YOSYS) $(SBY) $(VVP)",
                             "resolution"], cwd=tmp_path, env=env, check=True,
                            capture_output=True, text=True)
    assert result.stdout.strip().split() == [str(selected / "bin" / x) for x in ("yosys", "sby", "vvp")]
    default = subprocess.run([make, "-n", "-f", str(ROOT / "tools.mk")], cwd=tmp_path,
                             env=env, check=True, capture_output=True, text=True).stdout
    assert "checkout not found" in default
    assert "bootstrap_oss.py" not in default
