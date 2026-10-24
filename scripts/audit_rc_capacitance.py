#!/usr/bin/env python3
# SPDX-FileCopyrightText: 2026 Hasan Melih Akbulut
# SPDX-License-Identifier: Apache-2.0
"""Compare mapped capacitance pairs in flat C-only and distributed-RC exports.

Node maps must come from an independent topology proof. This audit checks their
consistency along resistors, but does not prove MOS topology, spatial attachment,
extractor accuracy or suitability for STA. A PASS is only matrix conservation.
"""
import argparse
from collections import defaultdict
import hashlib
import json
import math
from pathlib import Path
import re

SUFFIXES = {"": 1, "t": 1e12, "g": 1e9, "meg": 1e6, "k": 1e3,
            "m": 1e-3, "u": 1e-6, "n": 1e-9, "p": 1e-12, "f": 1e-15}
ABS_TOL = 1e-23
REL_TOL = 1e-5


def numeric(token):
    match = re.fullmatch(
        r"([+]?(?:\d+(?:\.\d*)?|\.\d+)(?:[eE][+-]?\d+)?)(meg|[tgkmunpf])?",
        token, re.I,
    )
    if not match:
        raise ValueError("Unsupported or negative passive value: " + token)
    value = float(match[1]) * SUFFIXES[(match[2] or "").lower()]
    if not math.isfinite(value) or value <= 0:
        raise ValueError("Nonpositive or nonfinite passive value")
    return value


def project(lines, node_map):
    """Project every capacitor; reject missing maps and inconsistent R edges."""
    mapping = {}
    if not isinstance(node_map, dict) or not node_map:
        raise ValueError("Nonempty independently derived node map required")
    for key, value in node_map.items():
        if not isinstance(key, str) or not isinstance(value, str) or not key or not value:
            raise ValueError("Node identities must be nonempty strings")
        key, value = key.upper(), value.upper()
        if key in mapping and mapping[key] != value:
            raise ValueError("Conflicting case-insensitive node identity")
        mapping[key] = value
    pairs, instances = defaultdict(list), set()
    capacitors = resistors = subcircuits = 0
    for line in lines:
        words = re.split(r"\s+\$|;", line.strip(), maxsplit=1)[0].split()
        if not words:
            continue
        name = words[0].upper()
        if not name or name.startswith(("*", "+")):
            continue
        if name == ".SUBCKT":
            subcircuits += 1
            if subcircuits > 1:
                raise ValueError("Flat single-subcircuit export required")
        if name in (".INCLUDE", ".INC", ".LIB"):
            raise ValueError("External circuit content is not audited")
        if name[0] not in "RC":
            continue
        if len(words) != 4 or name in instances:
            raise ValueError("Malformed or duplicate passive instance: " + name)
        instances.add(name)
        value = numeric(words[3])
        try:
            pair = tuple(sorted(mapping[n.upper()] for n in words[1:3]))
        except KeyError as error:
            raise ValueError("Unmapped passive endpoint: " + str(error)) from error
        if name[0] == "R":
            if pair[0] != pair[1]:
                raise ValueError("Resistor crosses independently mapped nets")
            resistors += 1
        else:
            if pair[0] == pair[1]:
                raise ValueError("Capacitor collapses to a self-pair")
            pairs[pair].append(value)
            capacitors += 1
    if not capacitors:
        raise ValueError("No capacitors audited")
    matrix = {pair: math.fsum(values) for pair, values in pairs.items()}
    if not all(math.isfinite(value) for value in matrix.values()):
        raise ValueError("Nonfinite aggregated capacitance")
    return matrix, dict(capacitors=capacitors, resistors=resistors,
                        pairs=len(matrix), total_f=math.fsum(matrix.values()))


def compare(reference, actual):
    missing = sorted(reference.keys() - actual.keys())
    extra = sorted(actual.keys() - reference.keys())
    mismatched = []
    for pair in sorted(reference.keys() & actual.keys()):
        difference = actual[pair] - reference[pair]
        if abs(difference) > ABS_TOL + REL_TOL * abs(reference[pair]):
            mismatched.append(dict(pair=pair, reference_f=reference[pair],
                                   rc_f=actual[pair], difference_f=difference))
    return dict(
        status="FAIL_RC_CAPACITANCE_CONSERVATION" if missing or extra or mismatched
        else "PASS_CAPACITANCE_MATRIX_ONLY",
        missing_pairs=len(missing), extra_pairs=len(extra),
        mismatched_pairs=len(mismatched), missing_sample=missing[:20],
        extra_sample=extra[:20], largest_mismatches=sorted(
            mismatched, key=lambda row: abs(row["difference_f"]), reverse=True)[:20],
        absolute_tolerance_f=ABS_TOL, relative_tolerance=REL_TOL,
        qualified_pex=False, timing_accepted=False, manufacturing_approval=False,
        scope="Pairwise capacitance conservation through supplied independent node maps. "
        "Excludes MOS topology proof, spatial RC attachment, model accuracy and STA qualification.",
    )


def digest(path):
    with path.open("rb") as stream:
        return hashlib.file_digest(stream, "sha256").hexdigest()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ("reference", "rc", "reference-map", "rc-map", "output"):
        parser.add_argument("--" + name, required=True, type=Path)
    args = parser.parse_args()
    paths = [args.reference, args.rc, args.reference_map, args.rc_map, Path(__file__)]
    if args.output.resolve() in [p.resolve() for p in paths] or args.output.exists():
        parser.error("Output must be a new path distinct from all inputs")
    result = dict(status="ERROR_NO_ACCEPTED_RESULT", qualified_pex=False,
                  timing_accepted=False, manufacturing_approval=False)
    try:
        pins = {str(p.resolve()): digest(p) for p in paths}
        result["input_sha256"] = pins
        with args.reference.open() as stream:
            reference, reference_stats = project(stream, json.loads(args.reference_map.read_text()))
        with args.rc.open() as stream:
            actual, actual_stats = project(stream, json.loads(args.rc_map.read_text()))
        result.update(compare(reference, actual), reference=reference_stats, rc=actual_stats)
        if any(digest(Path(p)) != sha for p, sha in pins.items()):
            raise ValueError("Input changed during audit")
    except (ValueError, OSError, OverflowError) as error:
        result.update(status="ERROR_NO_ACCEPTED_RESULT", error=str(error))
    args.output.write_text(json.dumps(result, indent=2) + "\n")
    print(result["status"])
    return 0 if result["status"] == "PASS_CAPACITANCE_MATRIX_ONLY" else 1


if __name__ == "__main__":
    raise SystemExit(main())
