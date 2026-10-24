#!/usr/bin/env python3
# SPDX-FileCopyrightText: 2026 Hasan Melih Akbulut
# SPDX-License-Identifier: Apache-2.0
"""Read all reported path groups in each delimited OpenSTA timing phase.

This summarizes reported paths, not unconstrained paths or timing signoff.
report_checks orders results within each path group; its first slack is not
necessarily the worst slack across the design.
"""

import argparse
import json
import math
import re
from pathlib import Path


def parse_phases(text, marker_prefix="PHASE"):
    if marker_prefix not in ("PHASE", "CORNER"):
        raise ValueError("Unsupported marker prefix")
    markers = list(re.finditer(r"^" + marker_prefix + r"_(\w+)[ \t]*$", text, re.M))
    if not markers:
        raise ValueError("No timing phase markers")
    phases = {}
    for index, marker in enumerate(markers):
        name = marker[1]
        if name in phases:
            raise ValueError(f"Duplicate phase: {name}")
        end = markers[index + 1].start() if index + 1 < len(markers) else len(text)
        body = text[marker.end():end]
        starts = list(re.finditer(r"^Startpoint:", body, re.M))
        paths = []
        for i, start in enumerate(starts):
            stop = starts[i + 1].start() if i + 1 < len(starts) else len(body)
            block = body[start.start():stop]
            fields = {}
            for key in ("Startpoint", "Endpoint", "Path Group", "Path Type", "Corner"):
                matches = re.findall(r"^" + key + r":[ \t]*(.+)$", block, re.M)
                if len(matches) != 1:
                    raise ValueError(f"Missing or duplicate {key} in {name}")
                fields[key] = matches[0].strip()
            slacks = re.findall(r"^[ \t]*(\S+)[ \t]+slack \((MET|VIOLATED)\)[ \t]*$", block, re.M)
            if len(slacks) != 1:
                raise ValueError(f"Missing or duplicate path slack in {name}")
            value = float(slacks[0][0])
            if not math.isfinite(value):
                raise ValueError(f"Nonfinite slack in {name}")
            if fields["Path Type"] not in ("min", "max"):
                raise ValueError(f"Unsupported path type in {name}")
            paths.append(dict(group=fields["Path Group"], corner=fields["Corner"],
                              path_type=fields["Path Type"], startpoint=fields["Startpoint"],
                              endpoint=fields["Endpoint"], slack_ns=value))
        if not paths:
            raise ValueError(f"No complete reported paths in {name}")
        if len({(p["corner"], p["path_type"]) for p in paths}) != 1:
            raise ValueError(f"Mixed corner/path types in {name}")
        groups = {}
        for path in paths:
            groups.setdefault(path["group"], []).append(path["slack_ns"])
        phases[name] = dict(worst_slack_ns=min(p["slack_ns"] for p in paths),
                            path_count=len(paths), groups={g: dict(worst_slack_ns=min(v),
                            path_count=len(v)) for g, v in groups.items()}, paths=paths)
    return phases


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("log", type=Path)
    parser.add_argument("--out", type=Path, required=True)
    parser.add_argument("--marker-prefix", choices=("PHASE", "CORNER"), default="PHASE")
    args = parser.parse_args()
    result = dict(status="COMPLETE_REPORTED_GROUP_SLACK_SUMMARY", phases=parse_phases(args.log.read_text(), args.marker_prefix),
                  timing_accepted=False, scope="All reported groups only; no unconstrained-path or signoff claim.")
    args.out.write_text(json.dumps(result, indent=2) + "\n")


if __name__ == "__main__":
    main()
