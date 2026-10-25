#!/usr/bin/env python3
# SPDX-FileCopyrightText: 2026 Hasan Melih Akbulut
# SPDX-License-Identifier: Apache-2.0
"""Install the pinned Linux x86-64 OSS CAD Suite without root or PATH mutation.

Requires Python >=3.12 for tarfile's data extraction filter. Existing targets
are never replaced. Both downloaded and supplied archives must match the
upstream release's size and SHA256 before extraction or execution.
"""

import argparse
import hashlib
import os
from pathlib import Path
import platform
import shutil
import sys
import tarfile
import tempfile
import urllib.request

ROOT = Path(__file__).resolve().parents[1]
RELEASE = "2026-08-04"
VERSION = "20260804"
URL = ("https://github.com/YosysHQ/oss-cad-suite-build/releases/download/"
       f"{RELEASE}/oss-cad-suite-linux-x64-{VERSION}.tgz")
ARCHIVE_SIZE = 737555999
ARCHIVE_SHA256 = "f9c8f52d7333341a1dcad3dc19b0ce229f1b30c5a30cdc8befcc6dd5c8ee2cbd"
BINARIES = ("sby", "eqy", "yosys", "iverilog", "vvp", "verilator")


def verify_archive(archive):
    if archive.stat().st_size != ARCHIVE_SIZE:
        raise ValueError("Archive size does not match pinned release")
    digest = hashlib.sha256()
    with archive.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    if digest.hexdigest() != ARCHIVE_SHA256:
        raise ValueError("Archive SHA256 does not match pinned release")


def install(destination, archive=None):
    destination = Path(destination).absolute()
    # lexists also protects a dangling symlink supplied as the target.
    if os.path.lexists(destination):
        raise FileExistsError(f"Refusing to replace existing target: {destination}")
    destination.parent.mkdir(parents=True, exist_ok=True)
    lock = destination.with_name(destination.name + ".install-lock")
    lock.mkdir()  # A concurrent installer must not share or remove this lock.
    try:
        with tempfile.TemporaryDirectory(prefix=".oss-install-", dir=destination.parent) as tmp:
            stage = Path(tmp)
            if archive is None:
                archive = stage / "release.tgz"
                if shutil.disk_usage(stage).free < ARCHIVE_SIZE + 64 * 1024**2:
                    raise OSError("Insufficient free space for the download")
                with urllib.request.urlopen(URL, timeout=60) as source, archive.open("xb") as target:
                    received = 0
                    while chunk := source.read(1024 * 1024):
                        received += len(chunk)
                        if received > ARCHIVE_SIZE:
                            raise ValueError("Download exceeds pinned archive size")
                        target.write(chunk)
            archive = Path(archive)
            verify_archive(archive)
            with tarfile.open(archive, "r:gz") as bundle:
                members = bundle.getmembers()
                if any(Path(m.name).parts[:1] != ("oss-cad-suite",) for m in members):
                    raise ValueError("Archive contains an unexpected top-level path")
                required = sum(m.size for m in members if m.isfile()) + 64 * 1024**2
                if shutil.disk_usage(stage).free < required:
                    raise OSError(f"Extraction needs at least {required} free bytes")
                bundle.extractall(stage, members=members, filter="data")
            tree = stage / "oss-cad-suite"
            if (tree / "VERSION").read_text().strip() != VERSION:
                raise ValueError("Extracted VERSION differs from pinned release")
            for name in BINARIES:
                if not os.access(tree / "bin" / name, os.X_OK):
                    raise ValueError(f"Missing executable in archive: {name}")
            if os.path.lexists(destination):
                raise FileExistsError(f"Target appeared during installation: {destination}")
            tree.rename(destination)
    finally:
        lock.rmdir()
    return destination


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--destination", type=Path, default=ROOT / "hw/soc/tools/oss-cad-suite")
    parser.add_argument("--archive", type=Path, help="Use an existing archive, still checksum verified")
    args = parser.parse_args()
    if sys.version_info < (3, 12):
        parser.error("Python 3.12 or newer is required for safe archive extraction")
    if platform.system() != "Linux" or platform.machine() not in ("x86_64", "AMD64"):
        parser.error("This pinned binary release supports Linux x86-64 only")
    try:
        target = install(args.destination, args.archive)
    except (OSError, ValueError, tarfile.TarError) as exc:
        parser.exit(1, f"OSS CAD Suite installation failed: {exc}\n")
    print(f"Installed OSS CAD Suite {RELEASE}: {target}")
    print(f"Verified SHA256: {ARCHIVE_SHA256}")


if __name__ == "__main__":
    main()
