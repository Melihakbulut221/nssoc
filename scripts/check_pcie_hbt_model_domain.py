#!/usr/bin/env python3
# SPDX-FileCopyrightText: 2026 Hasan Melih Akbulut
# SPDX-License-Identifier: Apache-2.0
"""Reject unsupported literal npn13G2 multiplicities before native simulation.

This checks multiplicity applicability only, not SOA, PVT or circuit correctness.
Parameter expressions are rejected rather than evaluated without their scope.
"""
import argparse
from decimal import Decimal, InvalidOperation
import hashlib
import json
from pathlib import Path
import re


def inspect_source(text):
    statements = []
    for number, raw in enumerate(text.splitlines(), 1):
        line = raw.split("$", 1)[0].strip()
        if not line or line.startswith("*"):
            continue
        if line.startswith("+") and statements:
            statements[-1][1] += " " + line[1:]
        else:
            statements.append([number, line])
    devices = []
    for number, line in statements:
        fields = line.lower().split()
        if not fields[0].startswith("x") or "npn13g2" not in fields:
            continue
        model = fields.index("npn13g2")
        parameters = " ".join(fields[model + 1:])
        matches = re.findall(r"\bnx\s*=\s*([^\s]+)", parameters)
        value = (matches[0] if len(matches) == 1 else
                 "1" if not matches and not re.search(r"\bnx\b", parameters)
                 else "ambiguous")
        try:
            nx = Decimal(value)
            passed = (model == 5 and nx.is_finite() and nx == nx.to_integral_value()
                      and 1 <= nx <= 10)
        except InvalidOperation:
            passed = False
        devices.append(dict(line=number, instance=fields[0], nx=value,
                            passed=bool(passed)))
    return dict(passed=bool(devices) and all(d["passed"] for d in devices),
                devices=devices, declared_nx_range=[1, 10])


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("sources", nargs="+", type=Path)
    args = parser.parse_args()
    results = {}
    for path in args.sources:
        raw = path.read_bytes()
        results[str(path)] = dict(sha256=hashlib.sha256(raw).hexdigest(),
                                 **inspect_source(raw.decode()))
    print(json.dumps(results, indent=2))
    return 0 if all(r["passed"] for r in results.values()) else 1


if __name__ == "__main__":
    raise SystemExit(main())
