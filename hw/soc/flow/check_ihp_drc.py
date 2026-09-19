#!/usr/bin/env python3
# SPDX-FileCopyrightText: 2026 Hasan Melih Akbulut
# SPDX-License-Identifier: Apache-2.0
"""Run the locked upstream IHP main DRC rules and require zero report markers.

This is a separate verification measurement, not a replacement for the installed
PDK's checks. No cell, region or main rule is excluded. Recommended rules remain
off, matching the controlled comparison documented in docs/93.
"""
import argparse
from collections import Counter
import hashlib
import json
from pathlib import Path
import re
import shutil
import subprocess
import xml.etree.ElementTree as ET

from prepare_ihp_drc import LOCK, SOC, prepare


def digest(path):
    with Path(path).open("rb") as stream:
        return hashlib.file_digest(stream, "sha256").hexdigest()


def read_report(path, top):
    root = ET.parse(path).getroot()
    if root.tag != "report-database" or root.findtext("top-cell") != top:
        raise ValueError("DRC report has the wrong format or top cell")
    categories, cells, items = (root.find(key) for key in ("categories", "cells", "items"))
    if (categories is None or not categories.findall("category")
            or cells is None or items is None
            or top not in [cell.findtext("name") for cell in cells.findall("cell")]):
        raise ValueError("DRC report is missing categories, top cell or items")
    counts = Counter()
    for item in items:
        if item.tag != "item" or not item.findtext("category") or not item.findtext("cell"):
            raise ValueError("Malformed DRC marker")
        # Count waived/visited markers too. Neither flag can make this gate pass.
        counts[item.findtext("category")] += 1
    return {"markers": sum(counts.values()), "categories": dict(sorted(counts.items()))}


def record_result(output, top, returncode, expected_inputs):
    """A fresh report and a successful process are both required for PASS."""
    output = Path(output)
    result = {"status": "ERROR", "process_returncode": returncode}
    try:
        for path, expected in expected_inputs.items():
            if digest(path) != expected:
                raise ValueError("Input changed during DRC: " + str(path))
        report = output / "drc.lyrdb"
        result.update(read_report(report, top))
        result["report_sha256"] = digest(report)
        if returncode == 0:
            result["status"] = "PASS" if result["markers"] == 0 else "FAIL"
        else:
            result["error"] = "KLayout did not exit successfully"
    except (OSError, ValueError, ET.ParseError) as error:
        result["error"] = str(error)
    (output / "result.json").write_text(json.dumps(result, indent=2) + "\n")
    return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("gds", type=Path)
    parser.add_argument("--top", required=True)
    parser.add_argument("--tag", required=True, help="New output directory under hw/soc/out")
    parser.add_argument("--klayout", default="klayout")
    parser.add_argument("--threads", type=int, default=2)
    args = parser.parse_args()
    if not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9_-]*", args.tag) or args.threads < 1:
        parser.error("A safe run tag and a positive thread count are required")
    gds = args.gds.resolve(strict=True)
    if not gds.is_file() or not gds.stat().st_size:
        parser.error("A nonempty GDS file is required")
    executable = shutil.which(args.klayout)
    if executable is None:
        parser.error("KLayout executable not found")
    output = SOC / "out" / args.tag
    if output.exists():
        parser.error("Refusing to overwrite an existing run")
    lock = json.loads(LOCK.read_text())
    cache = SOC / "tools/ihp-drc-5e6d592"
    entrypoint = prepare(lock, cache)
    expected = {gds: digest(gds), LOCK: digest(LOCK)}
    expected.update({cache / row["path"]: row["sha256"] for row in lock["files"]})
    version = subprocess.run([executable, "-v"], capture_output=True, text=True)
    if version.returncode or not version.stdout.strip():
        parser.error("Cannot record the KLayout version")
    output.mkdir(parents=True, exist_ok=False)
    cmd = [executable, "-b", "-zz", "-r", str(entrypoint)]
    for value in ("input=" + str(gds), "topcell=" + args.top,
                  "report=" + str(output / "drc.lyrdb"), "run_mode=deep",
                  "no_recommended=True", "threads=" + str(args.threads)):
        cmd += ["-rd", value]
    (output / "inputs.json").write_text(json.dumps({
        "command": cmd, "klayout_version": version.stdout.strip(),
        "deck_commit": lock["commit"], "top": args.top,
        "scope": "Complete input GDS; unmodified upstream main rules, deep mode; optional recommended checks off",
        "input_sha256": {str(path): sha for path, sha in expected.items()},
    }, indent=2) + "\n")
    with (output / "run.log").open("w") as stream:
        try:
            returncode = subprocess.run(cmd, stdout=stream, stderr=subprocess.STDOUT).returncode
        except OSError as error:
            stream.write(str(error) + "\n")
            returncode = 127
    result = record_result(output, args.top, returncode, expected)
    print(json.dumps(result, indent=2))
    raise SystemExit({"PASS": 0, "FAIL": 1, "ERROR": 2}[result["status"]])


if __name__ == "__main__":
    main()
