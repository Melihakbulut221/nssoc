#!/usr/bin/env python3
# SPDX-FileCopyrightText: 2026 Hasan Melih Akbulut
# SPDX-License-Identifier: Apache-2.0
"""Read real phase-detector LEF in OpenROAD; reject missing and obstructed macro pins."""

import argparse
import json
from pathlib import Path
import re

from check_ihp_drc import digest
from check_pcie_rx_cell import execute
from check_pcie_analog_bank import quote
from make_pcie_pfd102_v1 import TOP, PORTS, use_direction
from check_pcie_pfd102_v1 import APP_SHA


def coordinates(text):
    values = [float(v) for v in re.findall(r"-?\d+(?:\.\d+)?", text)]
    if len(values) != 4:
        raise ValueError("Invalid physical rectangle")
    return [round(v * 1000) for v in values]


def script(pdk, lef, generated):
    box = coordinates(generated["bbox_um"])
    if set(generated["ports"]) != set(PORTS):
        raise ValueError("Port census differs")
    lines = [
        "read_lef " + quote(pdk / "libs.ref/sg13g2_stdcell/lef/sg13g2_tech.lef"),
        "read_lef " + quote(lef),
        "set master [[ord::get_db] findMaster " + TOP + "]",
        'if {$master eq "NULL"} {error "PFD master missing"}',
        f'if {{[$master getWidth] != {box[2]} || [$master getHeight] != {box[3]}}} {{error "PFD outline changed"}}',
        'if {[llength [$master getMTerms]] != 8} {error "PFD terminal census changed"}',
    ]
    for name in PORTS:
        x1, y1, x2, y2 = coordinates(generated["ports"][name])
        use, direction = use_direction(name)
        lines += [
            "set term [$master findMTerm " + name + "]",
            'if {$term eq "NULL"} {error "PFD terminal missing"}',
            f'if {{[$term getIoType] ne "{direction}" || [$term getSigType] ne "{use}"}} {{error "PFD pin direction or use changed"}}',
            "set boxes {}; foreach pin [$term getMPins] {foreach b [$pin getGeometry] {lappend boxes [list [[$b getTechLayer] getName] [$b xMin] [$b yMin] [$b xMax] [$b yMax]]}}",
            'if {$boxes ne {{Metal5 %d %d %d %d}}} {error "PFD pin geometry changed"}'
            % (x1, y1, x2, y2),
            f'foreach b [$master getObstructions] {{if {{[[$b getTechLayer] getName] eq "Metal5" && [$b xMin] < {x2} && [$b xMax] > {x1} && [$b yMin] < {y2} && [$b yMax] > {y1}}} {{error "PFD pin is obstructed"}}}}',
        ]
    lines += [
        "set layers {}; foreach b [$master getObstructions] {lappend layers [[$b getTechLayer] getName]}",
        'if {[lsort -unique $layers] ne {Metal1 Metal2 Metal3 Metal4 Metal5 TopMetal1 TopMetal2}} {error "PFD obstruction layer census changed"}',
        "puts PASS_NATIVE_PFD_LEF",
    ]
    return "\n".join(lines) + "\n"


def run(layout, out, pdk, app):
    root = Path(__file__).resolve().parents[3]
    layout, out, pdk, app = [p.resolve() for p in (layout, out, pdk, app)]
    if (
        out.exists()
        or not out.is_relative_to(root / "hw/soc/out")
        or digest(app) != APP_SHA
    ):
        raise ValueError("Fresh project directory and pinned tool required")
    generated = json.loads((layout / "result.json").read_text())
    lef = layout / (TOP + ".lef")
    if digest(lef) != generated["outputs"][lef.name]:
        raise ValueError("LEF changed")
    inputs = [
        app,
        lef,
        layout / "result.json",
        pdk / "libs.ref/sg13g2_stdcell/lef/sg13g2_tech.lef",
        *[
            root / "hw/soc/flow" / n
            for n in (
                "check_pcie_pfd102_lef.py",
                "check_pcie_pfd102_v1.py",
                "make_pcie_pfd102_v1.py",
                "check_pcie_rx_cell.py",
                "check_ihp_drc.py",
                "check_pcie_analog_bank.py",
            )
        ],
    ]
    pins = {str(p): digest(p) for p in inputs}
    out.mkdir()
    record = dict(status="RUNNING", inputs=pins, steps={}, main_chip_integrated=False)
    for name in ["positive", "missing_pin", "blocked_pin"]:
        directory = out / name
        directory.mkdir()
        selected = lef
        if name != "positive":
            text = lef.read_text()
            if name == "missing_pin":
                text, count = re.subn(r"  PIN up\n.*?  END up\n", "", text, flags=re.S)
                if count != 1:
                    raise ValueError("Missing-pin fault did not bind")
            else:
                rect = [v / 1000 for v in coordinates(generated["ports"]["up"])]
                insertion = (
                    "  OBS\n    LAYER Metal5 ;\n      RECT "
                    + " ".join(str(v) for v in rect)
                    + " ;\n"
                )
                if text.count("  OBS\n") != 1:
                    raise ValueError("Obstruction fault did not bind")
                text = text.replace("  OBS\n", insertion)
            selected = directory / "fault.lef"
            selected.write_text(text)
        path = directory / "inspect.tcl"
        path.write_text(script(pdk, selected, generated))
        execution = execute([app, "openroad", "-exit", path], directory, "run")
        text = (directory / "run.log").read_text()
        if name == "positive":
            passed = (
                execution["returncode"] == 0
                and text.count("PASS_NATIVE_PFD_LEF") == 1
                and not re.search(r"^Error:|\[ERROR", text, re.M)
            )
        else:
            reason = (
                "PFD terminal census changed"
                if name == "missing_pin"
                else "PFD pin is obstructed"
            )
            passed = (
                execution["returncode"] != 0
                and "PASS_NATIVE_PFD_LEF" not in text
                and len(
                    re.findall(r"^Error: inspect\.tcl, \d+ " + reason + "$", text, re.M)
                )
                == 1
            )
        record["steps"][name] = dict(execution=execution, passed=passed)
        (out / "result.json").write_text(json.dumps(record, indent=2) + "\n")
        if not passed:
            raise ValueError("Native LEF control failed: " + name)
    if any(digest(Path(p)) != h for p, h in pins.items()):
        raise ValueError("Input changed")
    record["status"] = "PASS_NATIVE_LEF_AND_TWO_PHYSICAL_FAULTS"
    (out / "result.json").write_text(json.dumps(record, indent=2) + "\n")
    print(record["status"])


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ("layout", "out", "pdk", "app"):
        parser.add_argument("--" + name, type=Path, required=True)
    args = parser.parse_args()
    run(args.layout, args.out, args.pdk, args.app)


if __name__ == "__main__":
    main()
