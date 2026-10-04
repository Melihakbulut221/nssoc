#!/usr/bin/env python3
# SPDX-FileCopyrightText: 2026 Hasan Melih Akbulut
# SPDX-License-Identifier: Apache-2.0
"""Private unreduced-cap precision experiment; never edits the source runtime.

The total capacitance and node storage remain native floats. Only local area
accumulation/scaling in the existing unreduced intrinsic branch uses double,
and native cap diagnostics/rnodes serialize
more digits. This changes no struct ABI, resistance rule, node alias or model.
A native conservation audit is required; applying this patch is not acceptance.
"""

import argparse
import hashlib
import json
from pathlib import Path

PINS = {
    "resis/ResSimple.c": "9a5d9b3a3eaad9d6a84b989d52a8b540419cd85fef4331bc53726bd965939855",
    "resis/ResPrint.c": "1d26d2db3c5e23899a573c62129a802fcf3c1670364e16c3e43816aed5465067",
    "resis/resis.h": "f70ea5aac67a40a5cfcb73bb9485ab114a26655fe3f7c8abd10456810b6a7df6",
}
EDITS = {
    "resis/ResSimple.c": (
        ("(void) ResDistributeCapacitance(ResNodeList, resisdata->rg_intrinsiccap);",
         "(void) ResDistributeIntrinsicCapacitancePrecise(ResNodeList, resisdata->rg_intrinsiccap);"),
        ('NSSOC_V2_INTRINSIC_DISTRIBUTION %s total=%g intrinsic=%g\\n',
         'NSSOC_V2_INTRINSIC_DISTRIBUTION %s total=%.17g intrinsic=%.17g\\n'),
    ),
    "resis/ResPrint.c": (
        ('rnode \\"%s\\" 0 %g %d %d %d\\n', 'rnode \\"%s\\" 0 %.17g %d %d %d\\n'),
    ),
}


def pin(path):
    path = Path(path)
    return {"bytes": path.stat().st_size, "sha256": hashlib.sha256(path.read_bytes()).hexdigest()}


def transform(relative, text):
    if relative not in EDITS:
        raise ValueError("Only the two exact native C files may change")
    if relative == "resis/ResSimple.c":
        start = text.index("void\nResDistributeCapacitance(nodelist, totalcap)")
        end = text.index("\n}\n", start) + 3
        original = text[start:end]
        if original.count("    float totalarea = 0, capperarea;") != 1:
            raise ValueError("Native area accumulation construct changed")
        precise = ("static " + original.replace("ResDistributeCapacitance", "ResDistributeIntrinsicCapacitancePrecise", 1)
                   .replace("    float totalarea = 0, capperarea;", "    double totalarea = 0, capperarea;"))
        text = text[:end] + "\n/* Private unreduced intrinsic-C precision path; legacy path unchanged. */\n" + precise + text[end:]
    for before, after in EDITS[relative]:
        if text.count(before) != 1:
            raise ValueError("Missing or repeated exact source construct")
        text = text.replace(before, after)
    return text


def patch(source, output):
    source, output = Path(source), Path(output)
    if output.exists():
        raise ValueError("Fresh private patch directory required")
    before = {}
    for relative, expected in PINS.items():
        before[relative] = pin(source / relative)
        if before[relative]["sha256"] != expected:
            raise ValueError("Frozen native source changed: " + relative)
    values = {relative: transform(relative, (source / relative).read_text()) for relative in EDITS}
    output.mkdir(parents=True)
    for relative, value in values.items():
        path = output / relative
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(value)
    if any(pin(source / n) != p for n, p in before.items()):
        raise ValueError("Source changed while preparing private patch")
    result = {
        "status": "PRIVATE_PATCH_PREPARED_NATIVE_ACCEPTANCE_PENDING",
        "source": before,
        "method": pin(__file__),
        "outputs": {n: pin(output / n) for n in values},
        "struct_header_unchanged": before["resis/resis.h"],
        "changed_files": sorted(values),
        "no_resistance_alias_geometry_or_model_rule_change": True,
        "native_acceptance": False,
    }
    (output / "patch.json").write_text(json.dumps(result, indent=2) + "\n")
    return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source", type=Path, required=True)
    parser.add_argument("--out", type=Path, required=True)
    args = parser.parse_args()
    print(patch(args.source, args.out)["status"])


if __name__ == "__main__":
    main()
