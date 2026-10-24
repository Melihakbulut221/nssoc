#!/usr/bin/env python3
# SPDX-FileCopyrightText: 2026 Hasan Melih Akbulut
# SPDX-License-Identifier: Apache-2.0
"""Independently verify a complete zero-marker IHP density run.

The upstream deck emits most density categories only when they fail. Seven
empty slit categories alone therefore neither prove nor disprove coverage.
Require all 37 native execution records, completion, exact input hashes,
zero report items and the native global-density summary. This does not qualify
other DRC decks, LVS, parasitics, timing, a serial PHY or manufacturing.
"""
import argparse
import collections
import hashlib
import json
import math
from pathlib import Path
import re
import xml.etree.ElementTree as ET

DECK_COMMIT = "5e6d592e4002946a4616f798c357f0f3c06cf3b6"
LOCK_SHA256 = "d47860e82e76d81897ce51452aa1f7a7bb76643da38093911b5cdb55a4ebf73a"

RULES = (
    ["AFil.g", "AFil.g1", "AFil.g2", "AFil.g3", "GFil.g"]
    + [f"M{n}.{suffix}" for n in range(1, 6) for suffix in ("j", "k")]
    + [f"M{n}Fil.{suffix}" for n in range(1, 6) for suffix in ("h", "k")]
    + [f"TM{n}.{suffix}" for n in (1, 2) for suffix in ("c", "d")]
    + ["LBE.i"]
    + [f"Slt.i_{n}" for n in ("M1", "M2", "M3", "M4", "M5", "TM1", "TM2")]
)
SLIT_CATEGORIES = {name for name in RULES if name.startswith("Slt.i_")}
LIMITS = {
    "Activ": (35, 55), "GatPoly": (15, 100),
    **{f"Metal{n}": (35, 60) for n in range(1, 6)},
    "TopMetal1": (25, 70), "TopMetal2": (25, 70), "LBE": (0, 20),
}


def require(condition, message):
    if not condition:
        raise ValueError(message)


def digest(path):
    with Path(path).open("rb") as stream:
        return hashlib.file_digest(stream, "sha256").hexdigest()


def validate_report(log, report, top):
    executed = re.findall(r"Executing rule (\S+)\s*$", log, re.M)
    require(collections.Counter(executed) == collections.Counter(RULES),
            "Missing, repeated or unexpected native density rule execution")
    completion = re.findall(r"KLayout DRC run for density table completed in ([\d.]+) seconds", log)
    require(len(completion) == 1 and float(completion[0]) > 0,
            "Missing or duplicated native completion")
    require(not re.search(r"\b(?:ERROR|FATAL)\b|Traceback|segmentation fault", log, re.I),
            "Native diagnostic in otherwise successful log")
    tree = ET.fromstring(report)
    require(tree.findtext("top-cell") == top, "Wrong report top cell")
    items = tree.find("items")
    require(items is not None and len(items) == 0, "Missing item inventory or density markers")
    categories = [node.findtext("name") for node in tree.findall(".//category")]
    require(collections.Counter(categories) == collections.Counter(SLIT_CATEGORIES),
            "Unexpected or missing native zero-marker slit categories")
    densities = {}
    for name, value in re.findall(r"(\w+)\s+Density % =\s*([\d.]+)%", log):
        require(name not in densities, "Duplicate global-density summary")
        densities[name] = float(value)
    require(set(densities) == set(LIMITS), "Incomplete global-density summary")
    for name, value in densities.items():
        lower, upper = LIMITS[name]
        require(math.isfinite(value) and lower <= value <= upper,
                "Global density outside native limits: " + name)
    return dict(executed_rules=executed, executed_rule_count=len(executed),
                report_categories=categories, markers=0, global_density_percent=densities,
                native_elapsed_seconds=float(completion[0]))


def review(directory, expected_gds_sha256):
    directory = Path(directory).resolve()
    native = json.loads((directory / "result.json").read_text())
    inputs = json.loads((directory / "inputs.json").read_text())
    require(native["status"] == "PASS" and native["process_returncode"] == 0
            and native["markers"] == 0, "Native run did not pass")
    require(inputs["deck"] == "density" and inputs["mode"] == "deep"
            and inputs["density_sanity"] is True, "Wrong deck, mode or missing sanity checks")
    command = inputs["command"]
    require(command[1:4] == ["-b", "-zz", "-r"] and len(command[5:]) % 2 == 0,
            "Unexpected native command structure")
    options = {}
    for offset in range(5, len(command), 2):
        require(command[offset] == "-rd", "Unexpected native command argument")
        key, value = command[offset + 1].split("=", 1)
        require(key not in options, "Duplicate native option")
        options[key] = value
    require(set(options) == {"input", "topcell", "report", "threads", "run_mode",
                             "precheck_drc", "density_sanity"}, "Excluded or unknown native option")
    require(options["topcell"] == inputs["top"] and options["run_mode"] == "deep"
            and options["density_sanity"] == "True" and options["precheck_drc"] == "False",
            "Native options differ from recorded scope")
    require(Path(options["report"]).resolve() == directory / "drc.lyrdb",
            "Different native report path")
    pins = inputs["input_sha256"]
    require(options["input"] in pins and command[4] in pins, "Unpinned GDS or rule deck")
    require(re.fullmatch(r"[a-f0-9]{64}", expected_gds_sha256) is not None,
            "Expected GDS SHA-256 is required")
    require(pins[options["input"]] == expected_gds_sha256, "Different GDS identity")
    require(all(digest(name) == value for name, value in pins.items()), "Native input changed")
    lock = Path(__file__).resolve().parents[1] / "hw/soc/pnr/ihp-drc.lock.json"
    require(str(lock) in pins and pins[str(lock)] == LOCK_SHA256,
            "Missing or different native rule manifest")
    locked = json.loads(lock.read_text())
    require(locked["commit"] == inputs["deck_commit"] == DECK_COMMIT,
            "Different native rule version")
    relative = "ihp-sg13g2/libs.tech/klayout/tech/drc/rule_decks/density.drc"
    require(command[4].endswith("/" + relative), "Unexpected density entrypoint")
    deck_root = Path(command[4][:-len(relative)])
    for row in locked["files"]:
        require(pins.get(str(deck_root / row["path"])) == row["sha256"],
                "Missing or changed locked rule dependency: " + row["path"])

    for name, field in [("run.log", "log_sha256"), ("drc.lyrdb", "report_sha256")]:
        require(digest(directory / name) == native[field], "Native output hash mismatch")
    measured = validate_report((directory / "run.log").read_text(),
                               (directory / "drc.lyrdb").read_bytes(), inputs["top"])
    return dict(status="PASS_INDEPENDENT_DENSITY_37_EXECUTIONS_ZERO_MARKERS",
                gds_sha256=expected_gds_sha256, top=inputs["top"], measurements=measured,
                verified_native_inputs=len(pins), verified_locked_dependencies=len(locked["files"]),
                native_deck_commit=inputs["deck_commit"],
                records={str(directory / n): digest(directory / n)
                         for n in ["result.json", "inputs.json", "run.log", "drc.lyrdb"]},
                review_script_sha256=digest(__file__), scope=__doc__, manufacturing_approval=False)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--run-dir", type=Path, required=True)
    parser.add_argument("--expected-gds-sha256", required=True)
    parser.add_argument("--out", type=Path, required=True)
    args = parser.parse_args()
    result = review(args.run_dir, args.expected_gds_sha256)
    with args.out.open("x") as stream:
        stream.write(json.dumps(result, indent=2) + "\n")
    print(result["status"])


if __name__ == "__main__":
    main()
