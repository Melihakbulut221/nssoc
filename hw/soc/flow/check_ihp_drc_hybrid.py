#!/usr/bin/env python3
# SPDX-FileCopyrightText: 2026 Hasan Melih Akbulut
# SPDX-License-Identifier: Apache-2.0
"""Run all locked main tables with deep FEOL and tiled BEOL geometry.

Upstream rules, category inventory and recommended checks are unchanged.
The BEOL-only upstream selector needs no global connectivity extraction.
Antenna, density and LVS remain separate gates. No table can be omitted.
"""
import argparse
import json
from pathlib import Path
import re
import resource
import shutil
import subprocess
import time
import xml.etree.ElementTree as ET

from check_ihp_drc import digest, record_result
from prepare_ihp_drc import LOCK, SOC, prepare


from bounded_process import bounded_run
from check_ihp_drc_partitioned import (
    partition_tables, verify_inputs, read_categories, check_catalog, combine,
)

MODES = {"feol_and_geometry": "deep", "beol": "tiling"}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("gds", type=Path)
    parser.add_argument("--top", required=True)
    parser.add_argument("--tag", required=True)
    parser.add_argument("--klayout", default="klayout")
    parser.add_argument("--threads", type=int, default=1)
    parser.add_argument("--timeout-seconds", type=int, default=21600,
                        help="Per-part process limit; a timeout is ERROR")
    args = parser.parse_args()
    if (not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9_-]*", args.tag)
            or args.threads < 1 or args.timeout_seconds < 1):
        parser.error("Safe tag and positive threads/timeout required")
    gds = args.gds.resolve(strict=True)
    if not gds.is_file() or not gds.stat().st_size:
        parser.error("A nonempty GDS is required")
    executable = shutil.which(args.klayout)
    if executable is None:
        parser.error("KLayout executable not found")
    executable = Path(executable).resolve(strict=True)
    output = SOC / "out" / args.tag
    if output.exists():
        parser.error("Refusing to overwrite an existing run")
    lock = json.loads(LOCK.read_text())
    cache = SOC / "tools/ihp-drc-5e6d592"
    entrypoint = prepare(lock, cache)
    expected = {cache / row["path"]: row["sha256"] for row in lock["files"]}
    for path in (gds, LOCK, Path(__file__).resolve(), executable,
                 SOC / "flow/check_ihp_drc.py", SOC / "flow/prepare_ihp_drc.py",
                 SOC / "flow/check_ihp_drc_partitioned.py",
                 SOC / "flow/bounded_process.py"):
        expected[path] = digest(path)
    groups = partition_tables(entrypoint, set(expected))
    version = subprocess.run([str(executable), "-v"], capture_output=True, text=True)
    if version.returncode or not version.stdout.strip():
        parser.error("Cannot record KLayout version")
    output.mkdir(parents=True, exist_ok=False)
    inputs = dict(top=args.top, deck_commit=lock["commit"], tables=groups,
                  klayout_version=version.stdout.strip(), modes=MODES, recommended=True,
                  input_sha256={str(p): sha for p, sha in expected.items()},
                  scope="All 37 main tables in two sequential processes; antenna, density, LVS and other layouts require separate acceptance")
    (output / "inputs.json").write_text(json.dumps(inputs, indent=2) + "\n")
    parts = {}
    result = {"status": "ERROR"}
    try:
        for name, tables in groups.items():
            verify_inputs(expected)
            folder = output / name
            folder.mkdir(exist_ok=False)
            command = [str(executable), "-b", "-zz", "-r", str(entrypoint)]
            switches = ["input=" + str(gds), "topcell=" + args.top,
                        "report=" + str(folder / "drc.lyrdb"), "threads=" + str(args.threads),
                        "run_mode=" + MODES[name], "precheck_drc=False", "no_recommended=False",
                        "tables=" + " ".join(tables)]
            switches += ["no_" + group + "=True"
                         for group in ("feol", "beol", "offgrid", "angle", "pin", "forbidden")]
            for switch in switches:
                command += ["-rd", switch]
            (folder / "command.json").write_text(json.dumps(command, indent=2) + "\n")
            (output / "progress.json").write_text(json.dumps({"status": "RUNNING", "part": name}) + "\n")
            started = time.monotonic()
            with (folder / "run.log").open("w") as stream:
                rc = bounded_run(command, stdout=stream,
                                 timeout=args.timeout_seconds).returncode
                if rc == 124:
                    stream.write("\nPartition timed out; no acceptance.\n")
            measurement = record_result(folder, args.top, rc, expected)
            # Missing/malformed reports, missing categories and tool failures
            # cannot pass even if their marker total happens to be zero.
            inventory = read_categories(folder / "drc.lyrdb")
            check_catalog(name, inventory)
            parts[name] = dict(result=measurement, category_inventory=inventory,
                               elapsed_seconds=time.monotonic() - started,
                               cumulative_child_peak_rss_kib=resource.getrusage(resource.RUSAGE_CHILDREN).ru_maxrss)
            (folder / "measurement.json").write_text(json.dumps(parts[name], indent=2) + "\n")
            print(name, measurement["status"], flush=True)
        verify_inputs(expected)
        # Detect report changes between parsing and aggregate publication.
        for name, part in parts.items():
            if digest(output / name / "drc.lyrdb") != part["result"]["report_sha256"]:
                raise ValueError("Partition report changed before aggregation: " + name)
        result = combine(parts)
    except (OSError, ValueError, KeyError, ET.ParseError) as error:
        result = {"status": "ERROR", "error": str(error)}
    result["parts"] = {name: part["result"] for name, part in parts.items()}
    result["scope"] = inputs["scope"]
    (output / "result.json").write_text(json.dumps(result, indent=2) + "\n")
    (output / "progress.json").write_text(json.dumps({"status": result["status"]}) + "\n")
    print(json.dumps(result, indent=2))
    raise SystemExit({"PASS": 0, "FAIL": 1, "ERROR": 2}[result["status"]])


if __name__ == "__main__":
    main()
