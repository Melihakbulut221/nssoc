#!/usr/bin/env python3
# SPDX-FileCopyrightText: 2026 Hasan Melih Akbulut
# SPDX-License-Identifier: Apache-2.0
"""Reject incomplete FasterCap 6.0.7 results even when the process exits zero.

This verifies execution and the requested numerical stopping criterion only.
It does not qualify the geometry, dielectric stack, ports or process model.
"""
import argparse
import hashlib
import json
import math
from pathlib import Path
import re


def check(text, returncode, tolerance):
    if returncode != 0:
        raise ValueError(f"Solver process failed: {returncode}")
    if not math.isfinite(tolerance) or not 0 < tolerance < 1:
        raise ValueError("Invalid requested tolerance")
    if not text.startswith("Running FasterCap version 6.0.7\n"):
        raise ValueError("Unsupported or missing solver version")
    fatal = re.findall(r"^.*(?:^\s*Error:|out of memory|execution stopped|aborted).*$",
                       text, re.M | re.I)
    if fatal:
        raise ValueError("Fatal solver diagnostic: " + fatal[-1].strip())
    declared = re.findall(r"^Auto calculation with max error: (\S+)$", text, re.M)
    if len(declared) != 1 or float(declared[0]) != tolerance:
        raise ValueError("Requested tolerance differs from solver configuration")
    warnings = list(re.finditer(r"^\s*Warning:[^\n]*", text, re.M | re.I))
    known = "Warning: dummy dielectric-dielectric interface found in the input file, skipping"
    interfaces, intermediate = [], []
    for warning in warnings:
        line = warning[0].strip()
        if line == known:
            interfaces.append(warning)
        elif re.fullmatch(
                r"Warning: capacitance matrix (?:has a non-negative off-diagonal "
                r"element at row \d+ col \d+|is not diagonally dominant due to row \d+)",
                line):
            intermediate.append(warning)
        else:
            raise ValueError("Unexpected solver warning")
    if interfaces:
        equal_interfaces = re.findall(
            r"Dielectric constants are: inperm ([0-9.]+)-j0\.000000, "
            r"outperm ([0-9.]+)-j0\.000000; differing less than 0\.100000%", text)
        if (len(equal_interfaces) != len(interfaces)
                or any(a != b for a, b in equal_interfaces)):
            raise ValueError("Skipped dielectric interface is not exactly equal-permittivity")
    ending = re.search(
        r"Total allocated memory: (\d+) kilobytes\s*\n"
        r"Total time: ([0-9.]+)s \([^\n]+\)\s*\Z", text)
    if not ending:
        raise ValueError("Missing final solver completion summary")
    matrices = list(re.finditer(r"^Capacitance matrix is:\s*\nDimension (\d+) x (\d+)\n",
                                text, re.M))
    if not matrices:
        raise ValueError("Missing capacitance matrix")
    last = matrices[-1]
    if any(not matrices[0].end() < w.start() < last.start() for w in intermediate):
        raise ValueError("Final matrix has an unresolved numerical warning")
    dimension = int(last[1])
    if dimension < 1 or dimension != int(last[2]):
        raise ValueError("Invalid capacitance matrix dimensions")
    lines = text[last.end():].splitlines()[:dimension]
    names, matrix = [], []
    for line in lines:
        fields = line.split()
        if len(fields) != dimension + 1:
            raise ValueError("Truncated capacitance matrix")
        names.append(fields[0])
        values = [float(x) * 1e-6 for x in fields[1:]]  # Solver prints microfarads.
        if not all(math.isfinite(x) for x in values):
            raise ValueError("Nonfinite capacitance matrix")
        matrix.append(values)
    if len(matrix) != dimension or len(set(names)) != dimension:
        raise ValueError("Incomplete matrix or duplicate conductor names")
    if any(matrix[i][i] <= 0 for i in range(dimension)):
        raise ValueError("Nonpositive capacitance diagonal")
    if (any(matrix[i][j] > 0 for i in range(dimension)
            for j in range(dimension) if i != j)
            or any(sum(row) < 0 for row in matrix)):
        raise ValueError("Final capacitance matrix has invalid signs or dominance")
    norms = list(re.finditer(
        r"^Weighted Frobenius norm of the difference between capacitance "
        r"\(auto option\): (\S+)$", text, re.M))
    if not norms or not last.end() < norms[-1].start() < ending.start():
        raise ValueError("Final matrix lacks its convergence result")
    error = float(norms[-1][1])
    if not math.isfinite(error) or not 0 <= error <= tolerance:
        raise ValueError("Requested numerical tolerance was not reached")
    if "Iteration number #" in text[norms[-1].end():]:
        raise ValueError("A later iteration lacks an accepted matrix")
    return dict(status="PASS_SOLVER_EXECUTION_AND_NUMERICAL_STOP_ONLY",
                tolerance=tolerance, last_relative_norm=error,
                conductors=names, matrix_F=matrix,
                equal_permittivity_warning_count=len(interfaces),
                earlier_iteration_warnings=[w[0].strip() for w in intermediate],
                allocated_memory_kib=int(ending[1]), elapsed_seconds=float(ending[2]),
                qualified_pex=False, manufacturing_approval=False)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("log", type=Path)
    parser.add_argument("--returncode", type=int, required=True)
    parser.add_argument("--tolerance", type=float, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    if args.output.exists():
        parser.error("Refusing to overwrite an existing audit")
    try:
        result = check(args.log.read_text(), args.returncode, args.tolerance)
    except (OSError, ValueError) as error:
        result = dict(status="ERROR_OR_INCOMPLETE_SOLVER_RESULT", reason=str(error),
                      qualified_pex=False, manufacturing_approval=False)
    result["input_sha256"] = {
        str(p.resolve()): hashlib.sha256(p.read_bytes()).hexdigest()
        for p in [args.log, Path(__file__)] if p.is_file()}
    args.output.write_text(json.dumps(result, indent=2) + "\n")
    print(result["status"])
    raise SystemExit(0 if result["status"].startswith("PASS_") else 2)


if __name__ == "__main__":
    main()
