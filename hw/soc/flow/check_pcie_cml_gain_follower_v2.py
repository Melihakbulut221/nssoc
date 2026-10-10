#!/usr/bin/env python3
# SPDX-FileCopyrightText: 2026 Hasan Melih Akbulut
# SPDX-License-Identifier: Apache-2.0
"""Native CML gain/follower DRC/LVS and actual reference/geometry fault controls."""

import argparse
import json
from pathlib import Path
import sys, re

sys.path.insert(0, str(Path.cwd() / "hw/soc/flow"))

from check_ihp_drc import digest, record_result
from prepare_ihp_drc import validate_lock, verify
from check_pcie_rx_cell import execute
from check_pcie_analog_bank import extracted_ports

TOP = "nssoc_cml_gain_follower9_layout_v2"
PORTS = ["cp", "cn", "bp", "bn", "avdd", "avss", "sub"]

APP_SHA = "d6a349ec65be11456e96c4981d35f63ca34d3c85daf79a51e1ccb907bb5d7466"


def reference_fault(text, name):
    lines = text.splitlines(keepends=True)
    prefix = "QD0 " if name == "wrong_finger_count" else "QD1 "
    hits = [i for i, l in enumerate(lines) if l.startswith(prefix)]
    assert len(hits) == 1
    i = hits[0]
    if name == "wrong_finger_count":
        assert lines[i].count("Nx=2") == 1
        lines[i] = lines[i].replace("Nx=2", "Nx=1")
    elif name == "missing_hbt":
        lines[i] = ""
    else:
        raise ValueError(name)
    return "".join(lines)


def geometry_script(gds, target, fault):
    data = json.loads((gds.parent / "result.json").read_text())
    ports = {
        n: list(map(float, re.findall(r"-?\d+(?:\.\d+)?", v)))
        for n, v in data["ports"].items()
    }
    assert all(len(v) == 4 for v in ports.values())
    ys = {n: (v[1] + v[3]) / 2 for n, v in ports.items()}
    return f"""import pya
L=pya.Layout();L.read({str(gds)!r});top=L.cell({TOP!r});assert top is not None
fault={fault!r};ys={ys!r}
if fault=='offgrid':top.transform(pya.Trans(1,0))
elif fault=='q_open':
    li=L.layer(67,0);before=pya.Region(top.shapes(li));y=ys['bp'];cut=pya.Region(pya.DBox(5,y-1,6,y+1).to_itype(L.dbu));after=before-cut;assert before.area()!=after.area();top.shapes(li).clear();top.shapes(li).insert(after)
elif fault=='rail_short':
    top.shapes(L.layer(67,0)).insert(pya.DBox(2.5,min(ys['avdd'],ys['avss'])-.7,3,max(ys['avdd'],ys['avss'])+.7))
else:raise ValueError(fault)
L.write({str(target)!r})
"""


def run(layout, out, app):
    root = Path.cwd()
    layout, out, app = layout.resolve(), out.resolve(), app.resolve()
    if out.exists() or not out.is_relative_to(root / "hw/soc/out"):
        raise ValueError("Use a fresh project output directory")
    if digest(app) != APP_SHA:
        raise ValueError("Native tool archive changed")
    generated = json.loads((layout / "result.json").read_text())
    pins = {Path(p): h for p, h in generated["inputs"].items()}
    pins.update({layout / name: h for name, h in generated["outputs"].items()})
    methods = [
        "make_pcie_cml_gain_follower_v2.py",
        "check_ihp_drc.py",
        "prepare_ihp_drc.py",
        "check_pcie_rx_cell.py",
        "audit_klayout_lvs.py",
        "check_pcie_analog_bank.py",
    ]
    pins.update(
        {
            p: digest(p)
            for p in [
                app,
                Path(__file__).resolve(),
                layout / "result.json",
                *[root / "hw/soc/flow" / n for n in methods],
            ]
        }
    )
    for typ in ("drc", "lvs"):
        path = root / f"hw/soc/pnr/ihp-{typ}.lock.json"
        lock = json.loads(path.read_text())
        validate_lock(lock)
        if lock["commit"] != "5e6d592e4002946a4616f798c357f0f3c06cf3b6":
            raise ValueError("Native deck revision changed")
        pins[path] = digest(path)
        for row in lock["files"]:
            path = root / f"hw/soc/tools/ihp-{typ}-5e6d592" / row["path"]
            verify(path.read_bytes(), row)
            pins[path] = row["sha256"]
    if any(digest(p) != h for p, h in pins.items()):
        raise ValueError("Layout source changed")
    out.mkdir()
    record = dict(
        status="RUNNING",
        inputs={str(p): h for p, h in pins.items()},
        steps={},
        serial_phy_complete=False,
        main_chip_integrated=False,
        qualified_pex=False,
    )

    def save():
        (out / "result.json").write_text(json.dumps(record, indent=2) + "\n")

    save()
    try:
        for name in (
            "drc",
            "lvs",
            "lvs_flat",
            "wrong_finger_count",
            "missing_hbt",
            "q_open",
            "rail_short",
            "offgrid",
        ):
            directory = out / name
            directory.mkdir()
            gds, schematic = layout / (TOP + ".gds"), layout / "schematic.cir"
            step = {}
            record["steps"][name] = step
            if name in ("wrong_finger_count", "missing_hbt"):
                target = directory / "fault.cir"
                target.write_text(reference_fault(schematic.read_text(), name))
                schematic = target
            if name in ("q_open", "rail_short", "offgrid"):
                target = directory / "fault.gds"
                script = directory / "fault.py"
                script.write_text(geometry_script(gds, target, name))
                step["mutation"] = execute(
                    [app, "python", script], directory, "mutation"
                )
                if step["mutation"]["returncode"] != 0 or digest(gds) == digest(target):
                    raise ValueError("Physical fault did not execute")
                gds = target
            drc = name in ("drc", "offgrid")
            typ = "drc" if drc else "lvs"
            suffix = "drc/ihp-sg13g2.drc" if drc else "lvs/sg13g2.lvs"
            entry = (
                root
                / f"hw/soc/tools/ihp-{typ}-5e6d592/ihp-sg13g2/libs.tech/klayout/tech"
                / suffix
            )
            options = [
                "input=" + str(gds),
                "topcell=" + TOP,
                "log=" + str(directory / "deck.log"),
                "run_mode=" + ("flat" if name == "lvs_flat" else "deep"),
            ]
            options += (
                [
                    "report=" + str(directory / "drc.lyrdb"),
                    "threads=2",
                    "no_recommended=False",
                    "precheck_drc=False",
                ]
                if drc
                else [
                    "schematic=" + str(schematic),
                    "report=" + str(directory / "result.lvsdb"),
                    "target_netlist=" + str(directory / "extracted.cir"),
                    "thr=2",
                    "no_simplify=true",
                    "top_lvl_pins=true",
                ]
            )
            command = [app, "klayout", "-b", "-zz", "-r", entry]
            for option in options:
                command += ["-rd", option]
            step["execution"] = execute(command, directory, "run")
            if step["execution"]["returncode"] != 0:
                raise ValueError("Native deck did not complete")
            if drc:
                result = record_result(directory, TOP, 0, pins)
                step["measurement"] = result
                expected = "PASS" if name == "drc" else "FAIL"
                if result["status"] != expected or result["category_count"] != 560:
                    raise ValueError("DRC verdict or rule coverage differs")
                if name == "offgrid" and not any(
                    "metal1_drw_Offgrid" in c for c in result["categories"]
                ):
                    raise ValueError("Offgrid fault rejected for wrong reason")
            else:
                step["audit_execution"] = execute(
                    [
                        app,
                        "python",
                        root / "hw/soc/flow/audit_klayout_lvs.py",
                        directory / "result.lvsdb",
                        "--top",
                        TOP,
                        "--deck-log",
                        directory / "deck.log",
                        "--output",
                        directory / "audit.json",
                    ],
                    directory,
                    "audit",
                )
                result = json.loads((directory / "audit.json").read_text())
                step["audit"] = result
                positive = name in ("lvs", "lvs_flat")
                if positive:
                    if (
                        result["status"] != "PASS within comparison scope"
                        or step["audit_execution"]["returncode"] != 0
                        or result["extraction_diagnostics"]
                        or result["circuit_status_counts"] != {"Match": 1}
                    ):
                        raise ValueError("Strict transistor comparison failed")
                    if len(result["circuits"]) != 1 or any(
                        result["circuits"][0][key] != 18
                        for key in (
                            "layout_devices_recursive",
                            "schematic_devices_recursive",
                        )
                    ):
                        raise ValueError("Physical device census differs")
                    if extracted_ports(
                        (directory / "extracted.cir").read_text(), TOP
                    ) != set(PORTS):
                        raise ValueError("Physical port census differs")
                elif (
                    result["status"] != "FAIL"
                    or step["audit_execution"]["returncode"] != 1
                    or "Deck explicitly reported a mismatch" not in result["reasons"]
                ):
                    raise ValueError("Native fault not rejected by actual comparison")
            step["status"] = (
                "PASS"
                if name in ("drc", "lvs", "lvs_flat")
                else "REJECTED_EXPECTED_FAULT"
            )
            save()
            print(name, step["status"], flush=True)
        if any(digest(p) != h for p, h in pins.items()):
            raise ValueError("Inputs changed during verification")
        record["status"] = "PASS_NATIVE_PDK_GAIN_FOLLOWER18_DRC_LVS_AND_FAULT_CONTROLS"
    except Exception as error:
        record.update(status="FAIL", error=repr(error))
        save()
        raise
    save()
    return record


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ("layout", "out", "app"):
        parser.add_argument("--" + name, type=Path, required=True)
    args = parser.parse_args()
    run(args.layout, args.out, args.app)


if __name__ == "__main__":
    main()
