#!/usr/bin/env python3
# SPDX-FileCopyrightText: 2026 Hasan Melih Akbulut
# SPDX-License-Identifier: Apache-2.0
"""Run every locked main DRC table in two sequential KLayout processes.

Uses upstream's table selector without modifying rules. FEOL connectivity is
released before BEOL starts. Antenna, density and LVS remain separate gates.
This runner deliberately has no option to omit tables or recommended rules.
"""
import argparse
from collections import Counter
import hashlib
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


TABLES = {
    "feol_and_geometry": (
        "nwell", "pwellblock", "nbulay", "activ", "activfiller", "thickgateox",
        "gatpoly", "gatpolyfiller", "psd", "cont", "contbar", "npnsubstratetie",
        "schottkydiode", "latchup", "pin", "offgrid", "angle", "forbidden",
    ),
    "beol": (
        "metal1", "metaln", "metalnfiller", "via1", "vian", "topvia1",
        "topmetal1", "topmetal1filler", "topvia2", "topmetal2", "topmetal2filler",
        "passiv", "copperpillar", "pad", "solderbump", "sealring", "mim",
        "metalslits", "lbe",
    ),
}
# Measured against complete main on both clean and deliberately faulty controls.
# Hashes cover category names AND descriptions, not merely the marker count.
CATALOGS = {
    "feol_and_geometry": (443, "1d3c7e93e88ac3cb6142fd0dc54facf9c38504a17ea5084877cc174d7fff8928"),
    "beol": (117, "543a472ab90858c678973a7b430b80ebe774e245a5be0129eaf85dc98c4679f0"),
    "complete": (560, "5ff1a95814cf97d5766ad7878244a306238d4accd11d3f8e1f8bab3f0a520341"),
}


def catalog_identity(categories):
    serialized = json.dumps(categories, sort_keys=True, ensure_ascii=False,
                            separators=(",", ":")).encode()
    return len(categories), hashlib.sha256(serialized).hexdigest()


def partition_tables(entrypoint, locked_paths):
    """Require exact, disjoint coverage of the locked entrypoint's rule tables."""
    groups = {name: [] for name in TABLES}
    seen = set()
    pattern = r"^# %include (rule_decks/(feol|beol|pin|geometry|forbidden)/[^\n]+)$"
    for relative, kind in re.findall(pattern, entrypoint.read_text(), re.M):
        source = entrypoint.parent / relative
        if source not in locked_paths:
            raise ValueError("Rule table is not locked: " + relative)
        matches = re.findall(r"if TABLES\.include\?\('([^']+)'\)", source.read_text())
        if len(matches) != 1 or matches[0] in seen:
            raise ValueError("Missing or duplicate rule table selector: " + relative)
        table = matches[0]
        seen.add(table)
        groups["beol" if kind == "beol" else "feol_and_geometry"].append(table)
    if {name: tuple(tables) for name, tables in groups.items()} != TABLES:
        raise ValueError("Locked main table inventory differs from the validated partition")
    return groups


def category_references(categories):
    """KLayout quotes punctuation-bearing names but may leave identifiers bare."""
    references = {"'" + name + "'" for name in categories}
    references.update(name for name in categories
                      if re.fullmatch(r"[A-Za-z_][A-Za-z_0-9]*", name))
    return references


def read_categories(report):
    root = ET.parse(report).getroot()
    categories = {}
    for category in root.findall("categories/category"):
        name = category.findtext("name")
        if (not name or name in categories
                or category.findall("categories/category")):
            raise ValueError("Missing, duplicate or unexpected nested DRC category")
        categories[name] = category.findtext("description") or ""
    if not categories:
        raise ValueError("Missing DRC category inventory")
    cells = set()
    for cell in root.findall("cells/cell"):
        name, variant = cell.findtext("name"), cell.findtext("variant")
        if not name:
            raise ValueError("Missing DRC cell name")
        qualified = name + (":" + variant if variant else "")
        if qualified in cells:
            raise ValueError("Duplicate DRC cell identity")
        cells.add(qualified)
    category_refs = category_references(categories)
    for item in root.findall("items/item"):
        if (item.findtext("category") not in category_refs
                or item.findtext("cell") not in cells):
            raise ValueError("Marker references an unknown category or cell")
    return categories


def check_catalog(part, categories):
    if catalog_identity(categories) != CATALOGS[part]:
        raise ValueError("Incomplete or changed category inventory: " + part)


def combine(parts):
    """A single clean group cannot stand in for complete main coverage."""
    if set(parts) != set(TABLES):
        raise ValueError("Missing or unexpected DRC partition")
    categories = {}
    counts = Counter()
    error = False
    for name, part in parts.items():
        inventory = part["category_inventory"]
        check_catalog(name, inventory)
        if categories.keys() & inventory.keys():
            raise ValueError("Duplicate DRC categories across partitions")
        categories.update(inventory)
        result = part["result"]
        expected_status = ("ERROR" if result["process_returncode"] != 0
                           else "FAIL" if result["markers"] else "PASS")
        if result["status"] not in (expected_status, "ERROR"):
            raise ValueError("Inconsistent partition result")
        if (result["markers"] != sum(result["categories"].values())
                or result["category_count"] != len(inventory)
                or any(key not in category_references(inventory)
                       for key in result["categories"])
                or any(type(value) is not int or value < 1
                       for value in result["categories"].values())):
            raise ValueError("Inconsistent partition marker counts")
        error |= result["status"] == "ERROR"
        counts.update(result["categories"])
    check_catalog("complete", categories)
    return {"status": "ERROR" if error else "FAIL" if counts else "PASS",
            "markers": sum(counts.values()), "categories": dict(sorted(counts.items())),
            "category_count": len(categories)}


def verify_inputs(expected):
    for path, sha in expected.items():
        if digest(path) != sha:
            raise ValueError("Input changed during partitioned DRC: " + str(path))


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
                 SOC / "flow/check_ihp_drc.py", SOC / "flow/prepare_ihp_drc.py"):
        expected[path] = digest(path)
    groups = partition_tables(entrypoint, set(expected))
    version = subprocess.run([str(executable), "-v"], capture_output=True, text=True)
    if version.returncode or not version.stdout.strip():
        parser.error("Cannot record KLayout version")
    output.mkdir(parents=True, exist_ok=False)
    inputs = dict(top=args.top, deck_commit=lock["commit"], tables=groups,
                  klayout_version=version.stdout.strip(), mode="tiling", recommended=True,
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
                        "run_mode=tiling", "precheck_drc=False", "no_recommended=False",
                        "tables=" + " ".join(tables)]
            switches += ["no_" + group + "=True"
                         for group in ("feol", "beol", "offgrid", "angle", "pin", "forbidden")]
            for switch in switches:
                command += ["-rd", switch]
            (folder / "command.json").write_text(json.dumps(command, indent=2) + "\n")
            (output / "progress.json").write_text(json.dumps({"status": "RUNNING", "part": name}) + "\n")
            started = time.monotonic()
            with (folder / "run.log").open("w") as stream:
                try:
                    rc = subprocess.run(command, stdout=stream, stderr=subprocess.STDOUT,
                                        timeout=args.timeout_seconds).returncode
                except subprocess.TimeoutExpired:
                    stream.write("\nPartition timed out; no acceptance.\n")
                    rc = 124
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
