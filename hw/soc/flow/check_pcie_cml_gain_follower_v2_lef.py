#!/usr/bin/env python3
# SPDX-FileCopyrightText: 2026 Hasan Melih Akbulut
# SPDX-License-Identifier: Apache-2.0
"""Verify the CML gain/follower LEF with native OpenROAD and three physical faults."""

import argparse
import hashlib
import json
import re
from pathlib import Path
import sys

sys.path.insert(0, str(Path.cwd() / "hw/soc/flow"))
from check_pcie_rx_cell import execute
from check_pcie_analog_bank import quote


def pin(p):
    return hashlib.sha256(p.read_bytes()).hexdigest()


def run(source, out, P, APP):
    source, out, P, APP = [p.resolve() for p in (source, out, P, APP)]
    assert (
        pin(APP) == "d6a349ec65be11456e96c4981d35f63ca34d3c85daf79a51e1ccb907bb5d7466"
    )
    r = json.loads((source / "result.json").read_text())
    r["ports"] = {
        n: dict(
            rect=[round(float(x) * 1000) for x in re.findall(r"-?\d+(?:\.\d+)?", v)],
            layer="Metal5",
            direction="INOUT"
            if n in ["avdd", "avss", "sub"]
            else "OUTPUT"
            if n in ["bp", "bn"]
            else "INPUT",
            use="POWER"
            if n == "avdd"
            else "GROUND"
            if n in ["avss", "sub"]
            else "SIGNAL",
        )
        for n, v in r["ports"].items()
    }
    assert set(r["ports"]) == {"cp", "cn", "bp", "bn", "avdd", "avss", "sub"}
    TOP = "nssoc_cml_gain_follower9_layout_v2"
    lef = source / (TOP + ".lef")
    assert pin(lef) == r["outputs"][lef.name]
    out.mkdir()

    def script(selected):
        lines = [
            "read_lef " + quote(P / "libs.ref/sg13g2_stdcell/lef/sg13g2_tech.lef"),
            "read_lef " + quote(selected),
            "set master [[ord::get_db] findMaster " + TOP + "]",
            'if {$master eq "NULL"} {error "Missing master"}',
            'if {[$master getWidth] != 366000 || [$master getHeight] != 119630} {error "Outline changed"}',
            'if {[llength [$master getMTerms]] != 7} {error "Pin census changed"}',
        ]
        for name, p in r["ports"].items():
            x0, y0, x1, y1 = p["rect"]
            layer = p["layer"]
            lines += [
                "set term [$master findMTerm " + name + "]",
                'if {$term eq "NULL"} {error "Missing pin"}',
                f'if {{[$term getIoType] ne "{p["direction"]}" || [$term getSigType] ne "{p["use"]}"}} {{error "Pin type changed"}}',
                "set boxes {}; foreach pin [$term getMPins] {foreach b [$pin getGeometry] {lappend boxes [list [[$b getTechLayer] getName] [$b xMin] [$b yMin] [$b xMax] [$b yMax]]}}",
                'if {$boxes ne {{%s %d %d %d %d}}} {error "Pin geometry changed"}'
                % (layer, x0, y0, x1, y1),
                f'foreach b [$master getObstructions] {{if {{[[$b getTechLayer] getName] eq "{layer}" && [$b xMin] < {x1} && [$b xMax] > {x0} && [$b yMin] < {y1} && [$b yMax] > {y0}}} {{error "Pin obstructed"}}}}',
            ]
        lines += [
            "set layers {}; foreach b [$master getObstructions] {lappend layers [[$b getTechLayer] getName]}",
            'if {[lsort -unique $layers] ne {Metal1 Metal2 Metal3 Metal4 Metal5 TopMetal1 TopMetal2}} {error "Obstruction layers changed"}',
            "puts PASS_NATIVE_FOLLOWER_LEF",
        ]
        return "\n".join(lines) + "\n"

    inputs = {
        str(p): pin(p)
        for p in [
            Path(__file__),
            lef,
            source / "result.json",
            APP,
            P / "libs.ref/sg13g2_stdcell/lef/sg13g2_tech.lef",
        ]
    }
    record = dict(status="RUNNING", inputs=inputs, steps={}, main_chip_integrated=False)
    text = lef.read_text()
    missing, n = re.subn(r"  PIN cp\n.*?  END cp\n", "", text, flags=re.S)
    assert n == 1
    faults = {
        "positive": text,
        "missing_pin": missing,
        "blocked_pin": text.replace(
            "  OBS\n",
            "  OBS\n    LAYER Metal5 ;\n      RECT "
            + " ".join(f"{x / 1000:.3f}" for x in r["ports"]["bp"]["rect"])
            + " ;\n",
        ),
        "wrong_outline": text.replace(
            "SIZE 366.000 BY 119.630", "SIZE 366.001 BY 119.630"
        ),
    }
    assert all(
        content != text for name, content in faults.items() if name != "positive"
    )
    for name, content in faults.items():
        directory = out / name
        directory.mkdir()
        selected = lef
        if name != "positive":
            selected = directory / "fault.lef"
            selected.write_text(content)
        tcl = directory / "inspect.tcl"
        tcl.write_text(script(selected))
        execution = execute([APP, "openroad", "-exit", tcl], directory, "run")
        log = (directory / "run.log").read_text()
        if name == "positive":
            passed = (
                execution["returncode"] == 0
                and log.count("PASS_NATIVE_FOLLOWER_LEF") == 1
                and not re.search(r"^Error:|\[ERROR", log, re.M)
            )
        else:
            expected = {
                "missing_pin": "Pin census changed",
                "blocked_pin": "Pin obstructed",
                "wrong_outline": "Outline changed",
            }[name]
            passed = (
                execution["returncode"] != 0
                and "PASS_NATIVE_FOLLOWER_LEF" not in log
                and len(
                    re.findall(
                        r"^Error: inspect\.tcl, \d+ " + expected + "$", log, re.M
                    )
                )
                == 1
            )
        record["steps"][name] = dict(passed=passed, execution=execution)
        (out / "result.json").write_text(json.dumps(record, indent=2) + "\n")
        assert passed, name
    assert all(pin(Path(p)) == h for p, h in inputs.items())
    record["status"] = "PASS_NATIVE_LEF_SEVEN_PINS_AND_THREE_FAULTS"
    (out / "result.json").write_text(json.dumps(record, indent=2) + "\n")
    print(record["status"])


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ["layout", "out", "pdk", "app"]:
        parser.add_argument("--" + name, type=Path, required=True)
    args = parser.parse_args()
    run(args.layout, args.out, args.pdk, args.app)


if __name__ == "__main__":
    main()
