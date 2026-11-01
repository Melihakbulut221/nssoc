#!/usr/bin/env python3
# SPDX-FileCopyrightText: 2026 Hasan Melih Akbulut
# SPDX-License-Identifier: Apache-2.0
"""Fetch an immutable IHP verification deck without changing the installed PDK.

The lock includes every runtime rule, process constants and upstream licence.
Existing modified files are rejected, never silently replaced. This prepares
rules; it does not run DRC or assert that a layout or PDK migration passes.
"""
import argparse
import hashlib
import json
import re
import urllib.request
from pathlib import Path, PurePosixPath

SOC = Path(__file__).resolve().parents[1]
LOCK = SOC / "pnr/ihp-drc.lock.json"


def validate_lock(lock):
    if lock["repository"] != "https://github.com/IHP-GmbH/IHP-Open-PDK":
        raise ValueError("Unexpected upstream repository")
    if not re.fullmatch(r"[0-9a-f]{40}", lock["commit"]):
        raise ValueError("An immutable commit is required")
    seen = set()
    for row in lock["files"]:
        path = PurePosixPath(row["path"])
        if (path.is_absolute() or ".." in path.parts or "\\" in row["path"]
                or str(path) != row["path"] or row["path"] in seen):
            raise ValueError("Unsafe or duplicate locked path")
        if not re.fullmatch(r"[0-9a-f]{64}", row["sha256"]):
            raise ValueError("Invalid SHA-256")
        if not isinstance(row["bytes"], int) or row["bytes"] <= 0:
            raise ValueError("Invalid locked size")
        seen.add(row["path"])
    if lock["entrypoint"] not in seen or "LICENSE" not in seen:
        raise ValueError("Missing entrypoint or upstream licence")


def verify(data, row):
    if len(data) != row["bytes"] or hashlib.sha256(data).hexdigest() != row["sha256"]:
        raise ValueError("Content does not match lock: " + row["path"])


def fetch(url):
    with urllib.request.urlopen(url, timeout=60) as response:
        return response.read()


def prepare(lock, output, fetch_bytes=fetch):
    validate_lock(lock)
    output = Path(output).resolve()
    # Verify the entire existing cache before downloading or writing anything.
    missing = []
    for row in lock["files"]:
        path = output / row["path"]
        if not path.resolve().is_relative_to(output):
            raise ValueError("Locked path escapes output through a symlink")
        if path.exists():
            verify(path.read_bytes(), row)
        else:
            missing.append(row)
    for row in missing:
        url = ("https://raw.githubusercontent.com/IHP-GmbH/IHP-Open-PDK/"
               + lock["commit"] + "/" + row["path"])
        data = fetch_bytes(url)
        verify(data, row)
        path = output / row["path"]
        path.parent.mkdir(parents=True, exist_ok=True)
        # Exclusive creation protects a concurrent writer's output.
        with path.open("xb") as stream:
            stream.write(data)
    return output / lock["entrypoint"]


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path,
                        default=SOC / "tools/ihp-drc-5e6d592")
    args = parser.parse_args()
    if not args.output.resolve().is_relative_to((SOC / "tools").resolve()):
        parser.error("Output must stay inside this project's hw/soc/tools")
    lock = json.loads(LOCK.read_text())
    entrypoint = prepare(lock, args.output)
    print(f"Verified {len(lock['files'])} files at {lock['commit']}")
    print(entrypoint)


if __name__ == "__main__":
    main()
