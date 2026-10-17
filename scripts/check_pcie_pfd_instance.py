# SPDX-FileCopyrightText: 2026 Hasan Melih Akbulut
# SPDX-License-Identifier: Apache-2.0
"""Check the named PFD boundary, independently of extracted SPICE pin order."""

import argparse
import hashlib
import json
from pathlib import Path


MACRO = "nssoc_pfd255_wire_v1"
# Preserve the established negative-VCO-slope feedback polarity. These names
# belong to the loop, whereas the dictionary keys belong to the extracted PFD.
EXPECTED = {
    "sub": "sub", "vdd": "div_avdd", "ref": "fb", "fb": "ref",
    "reset": "reset", "vss": "avss", "up": "up", "down": "down",
    "wire_cref": "pfd_wire_cref",
}


def statements(text):
    result = []
    for line in text.splitlines():
        line = line.strip()
        if not line or line.startswith("*"):
            continue
        words = line.lower().split()
        if words[0] == "+":
            if not result:
                raise ValueError("Orphan SPICE continuation")
            result[-1].extend(words[1:])
        else:
            result.append(words)
    return result


def check(loop, model):
    headers = [s for s in statements(model) if s[:2] == [".subckt", MACRO]]
    calls = [s for s in statements(loop) if s[0] == "xdet"]
    if len(headers) != 1 or len(calls) != 1:
        raise ValueError("Expected exactly one PFD declaration and instance")
    ports, call = headers[0][2:], calls[0]
    if len(ports) != len(set(ports)) or set(ports) != set(EXPECTED):
        raise ValueError("Missing, duplicate or unexpected PFD port")
    if len(call) != len(ports) + 2 or call[-1] != MACRO:
        raise ValueError("PFD instance arity or model differs")
    actual = dict(zip(ports, call[1:-1], strict=True))
    if actual != EXPECTED:
        wrong = {p: {"actual": actual[p], "expected": n}
                 for p, n in EXPECTED.items() if actual[p] != n}
        raise ValueError("PFD named boundary mismatch: " + json.dumps(wrong, sort_keys=True))
    return {"status": "PASS_NAMED_PFD_INSTANCE_BOUNDARY", "ports": ports,
            "binding": actual, "serial_phy_complete": False}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--loop", type=Path, required=True)
    parser.add_argument("--model", type=Path, required=True)
    parser.add_argument("--out", type=Path, required=True)
    args = parser.parse_args()
    result = check(args.loop.read_text(), args.model.read_text())
    result["inputs"] = {
        str(p.resolve()): hashlib.sha256(p.read_bytes()).hexdigest()
        for p in (args.loop, args.model, Path(__file__))
    }
    args.out.write_text(json.dumps(result, indent=2) + "\n")
    print(result["status"])


if __name__ == "__main__":
    main()
