#!/usr/bin/env python3
# SPDX-FileCopyrightText: 2026 Hasan Melih Akbulut
# SPDX-License-Identifier: Apache-2.0
"""Adapt native IHP I/O CDL syntax for the pinned KLayout LVS reader.

Remove an empty .PARAM declaration, map X-prefixed ptap1/ntap1 pseudo-devices
to R-prefixed native CustomTap devices, and map the res_rppd model spelling
to the reader's rppd name. Nodes and parameter values are unchanged. This is
an LVS dialect conversion, not a SPICE simulation model or an LVS pass.
"""
import argparse
import json
import re
from pathlib import Path

from transistor_schematic import digest, read_cdl


def normalize(text):
    lines, changes = text.splitlines(keepends=True), []
    for index, original in enumerate(lines):
        words = original.split()
        candidate, reason = original, None
        if re.fullmatch(r"\s*\.PARAM\s*", original, re.I):
            candidate, reason = "", "empty_parameter_declaration"
        elif words and words[0].startswith("X") and any("=" in x for x in words):
            if (len(words) != 10 or words[3] != "/"
                    or words[4] not in ("ptap1", "ntap1")
                    or not words[0].startswith("XR")
                    or len({x.split("=")[0].lower() for x in words[5:]}) != 5
                    or {x.split("=")[0].lower() for x in words[5:]}
                    != {"r", "a", "perim", "w", "l"}
                    or any(not re.fullmatch(r"[A-Za-z]+=\d+(?:\.\d*)?(?:[eE][-+]?\d+)?[fpnumkKMG]?", x)
                           for x in words[5:])):
                raise ValueError("Unsupported parameterized CDL call: " + original)
            candidate = original.replace(words[0], words[0][1:], 1)
            reason = "native_tap_device_prefix"
        elif "$[res_rppd]" in original and not original.lstrip().startswith("*"):
            if (len(words) < 7 or not words[0].startswith("R")
                    or not re.fullmatch(r"\$SUB=[^\s=]+", words[4])
                    or words[5] != "$[res_rppd]"):
                raise ValueError("Unsupported resistor alias context: " + original)
            candidate = original.replace("$[res_rppd]", "$[rppd]")
            reason = "native_rppd_model_spelling"
        if candidate != original:
            changes.append(dict(line=index + 1, before=original, after=candidate, reason=reason))
            lines[index] = candidate
    # Reverse every substitution at its original line slot, including deletions.
    restored = lines.copy()
    for change in changes:
        restored[change["line"] - 1] = change["before"]
    if "".join(restored) != text:
        raise ValueError("Conversion is not exactly reversible")
    return "".join(lines), changes


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("source", type=Path)
    parser.add_argument("output", type=Path)
    parser.add_argument("--receipt", type=Path, required=True)
    args = parser.parse_args()
    if args.output.exists() or args.receipt.exists():
        parser.error("Choose fresh output and receipt paths")
    source_hash = digest(args.source)
    output, changes = normalize(args.source.read_text())
    if digest(args.source) != source_hash:
        raise ValueError("Source changed")
    with args.output.open("x") as stream:
        stream.write(output)
    definitions, _ = read_cdl([args.output])
    receipt = dict(status="DIALECT_CONVERSION_REQUIRES_NATIVE_READER_AND_LVS",
                   source_sha256=source_hash, output_sha256=digest(args.output),
                   changes=changes, subcircuits=len(definitions),
                   native_reader_verified=False, lvs_accepted=False,
                   manufacturing_approval=False)
    args.receipt.write_text(json.dumps(receipt, indent=2) + "\n")
    print(receipt["status"])


if __name__ == "__main__":
    main()
