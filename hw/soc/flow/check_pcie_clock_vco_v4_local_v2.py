#!/usr/bin/env python3
# SPDX-FileCopyrightText: 2026 Hasan Melih Akbulut
# SPDX-License-Identifier: Apache-2.0
"""Native DRC, deep/flat LVS and physical failures of the local-route four-PMOS VCO v4 macro."""

import argparse
import json
from pathlib import Path
import re

from check_ihp_drc import digest, record_result
from check_pcie_analog_bank import extracted_ports, quote, validate_lef
from check_pcie_rx_cell import execute
from make_pcie_clock_vco_v4_local_v2 import (
    CIRCUIT,
    CIRCUIT_SHA256,
    PORTS,
    TOP,
    physical_reference,
    use_direction,
)
from prepare_ihp_drc import validate_lock, verify

APP_SHA = "d6a349ec65be11456e96c4981d35f63ca34d3c85daf79a51e1ccb907bb5d7466"
REFERENCE_FAULTS = (
    "wrong_load",
    "tail_nx",
    "missing_tap",
    "ring_input",
    "mim_asymmetry",
    "pmos_width",
    "missing_well_tap",
    "follower_nx",
    "missing_follower",
    "sink_nx",
    "missing_control_pmos",
)
PHYSICAL_FAULTS = (
    "control_open",
    "clock_short",
    "power_short",
    "follower_open",
    "well_open",
    "limiter_emitter_short",
)


def fault_reference(text, fault):
    changes = {
        "follower_nx": (
            "QFPD2 AVDD BO_P CLKP BULK npn13G2 Nx=4",
            "QFPD2 AVDD BO_P CLKP BULK npn13G2 Nx=3",
        ),
        "missing_follower": (
            "QFND3 AVDD BO_N CLKN BULK npn13G2 Nx=4 we=0.07u le=0.9u m=1\n",
            "",
        ),
        "sink_nx": (
            "QFTND3 CLKN BREF AVSS BULK npn13G2 Nx=2",
            "QFTND3 CLKN BREF AVSS BULK npn13G2 Nx=1",
        ),
        "wrong_load": (
            "RRP0 AVDD P0 BULK rppd w=8u l=4.4u",
            "RRP0 AVDD P0 BULK rppd w=8u l=4.5u",
        ),
        "tail_nx": (
            "QT0 T0 REF AVSS BULK npn13G2 Nx=4",
            "QT0 T0 REF AVSS BULK npn13G2 Nx=3",
        ),
        "missing_tap": ("RTAP0 SUB BULK ptap1 A=4p P=8u\n", ""),
        "ring_input": ("QP1 P1 P0 T1", "QP1 P1 N0 T1"),
        "mim_asymmetry": (
            "CCP0 P0 AVSS cap_cmim w=12.2u",
            "CCP0 P0 AVSS cap_cmim w=12u",
        ),
        "pmos_width": (
            "MCTRL0 REF VCTRL AVDD NWELL sg13_hv_pmos w=8u",
            "MCTRL0 REF VCTRL AVDD NWELL sg13_hv_pmos w=7u",
        ),
        "missing_control_pmos": (
            "MCTRL3 REF VCTRL AVDD NWELL sg13_hv_pmos w=8u l=0.45u ng=1 m=1\n",
            "",
        ),
        "missing_well_tap": ("RNTAP AVDD NWELL ntap1 A=4p P=8u\n", ""),
    }
    if fault not in changes:
        raise ValueError("Unknown reference fault")
    old, new = changes[fault]
    if text.count(old) != 1:
        raise ValueError("Reference fault must bind exactly once")
    return text.replace(old, new)


def mutation_source(gds, output, generated, fault):
    lines = [
        "import pya",
        "l=pya.Layout()",
        "l.read(" + repr(str(gds)) + ")",
        "c=l.cell(" + repr(TOP) + ")",
    ]
    if fault == "offgrid":
        lines += ["c.shapes(l.layer(8,0)).insert(pya.DBox(2.002,2,2.102,2.1))"]
    elif fault == "follower_open":
        witnesses = [
            row
            for row in generated["routes"]
            if row.get("device") == "FPD2" and row.get("net") == "AVDD"
        ]
        if len(witnesses) != 1:
            raise ValueError("Exact added follower collector route is missing")
        witness = witnesses[0]
        coordinates = [
            float(value)
            for value in re.findall(r"-?\d+(?:\.\d+)?", witness["actual_pin_um"])
        ]
        if len(coordinates) != 4:
            raise ValueError("Unknown native pin rectangle")
        pin_x = (coordinates[0] + coordinates[2]) / 2
        x = round((pin_x + witness["escape_lane_um"]) / 2 / 0.005) * 0.005
        # Device route witnesses precede the final GDS origin translation.
        dx, dy = generated["origin_translation_um"]
        x += dx
        y = witness["escape_y_um"] + dy
        lines += [
            "region=pya.Region(c.shapes(l.layer(30,0)))",
            f"region-=pya.Region(pya.DBox({x - 0.1!r},{y - 0.3!r},{x + 0.1!r},{y + 0.3!r}).to_itype(l.dbu))",
            "c.shapes(l.layer(30,0)).clear()",
            "c.shapes(l.layer(30,0)).insert(region)",
        ]
    elif fault == "limiter_emitter_short":
        # Reproduce the actual first-locality short using real terminal
        # witnesses: bridge ring N0's emitter escape to limiter BN's emitter.
        found = []
        for name, net in (("N0", "T0"), ("BN", "BT")):
            matches = [
                r
                for r in generated["routes"]
                if r.get("device") == name and r.get("net") == net
            ]
            if len(matches) != 1 or matches[0]["source_layer"] != 2:
                raise ValueError("Exact ring/limiter emitter witnesses missing")
            found.append(matches[0])
        lower, upper = found
        box = [float(v) for v in re.findall(r"-?\d+(?:\.\d+)?", upper["actual_pin_um"])]
        if len(box) != 4 or lower["escape_y_um"] != upper["escape_y_um"]:
            raise ValueError("Emitter bridge requires actual aligned M3 routes")
        dx, dy = generated["origin_translation_um"]
        left = lower["escape_lane_um"] + dx
        right = (box[0] + box[2]) / 2 + dx
        y = lower["escape_y_um"] + dy
        if right - left < 1:
            raise ValueError("Emitter routes have no open physical gap")
        lines += [
            f"c.shapes(l.layer(30,0)).insert(pya.DBox({left - 0.2!r},{y - 0.2!r},{right + 0.2!r},{y + 0.2!r}))"
        ]
    elif fault == "well_open":
        dx, dy = generated["origin_translation_um"]
        records = {r["name"]: r for r in generated["instances"]}

        def box(value):
            result = [float(v) for v in re.findall(r"-?\d+(?:\.\d+)?", value)]
            if len(result) != 4:
                raise ValueError("Well fault requires actual native geometry")
            return result

        bridge = box(records["NTAP"]["body_connection_geometry_um"])
        lower = box(records["CTRL1"]["bbox_um"])
        upper = box(records["CTRL2"]["bbox_um"])
        if upper[1] - lower[3] < 4:
            raise ValueError("No native well-only gap for the isolation control")
        y = round((lower[3] + upper[1]) / 2 / 0.005) * 0.005 + dy
        x1, x2 = bridge[0] - 1 + dx, bridge[2] + 1 + dx
        lines += [
            "region=pya.Region(c.shapes(l.layer(31,0)))",
            f"region-=pya.Region(pya.DBox({x1!r},{y - 1!r},{x2!r},{y + 1!r}).to_itype(l.dbu))",
            "c.shapes(l.layer(31,0)).clear()",
            "c.shapes(l.layer(31,0)).insert(region)",
        ]
    elif fault == "control_open":
        b = generated["ports"]["VCTRL"]["rect_um"]
        y = (b[1] + b[3]) / 2
        # Cut a complete conductor section after the labelled outer pin, before
        # every real clock terminal; the label and original circuit remain.
        lines += [
            "region=pya.Region(c.shapes(l.layer(67,0)))",
            f"region-=pya.Region(pya.DBox(3,{y - 2!r},4,{y + 2!r}).to_itype(l.dbu))",
            "c.shapes(l.layer(67,0)).clear()",
            "c.shapes(l.layer(67,0)).insert(region)",
        ]
    elif fault in ("clock_short", "power_short"):
        names = ("CLKP", "CLKN") if fault == "clock_short" else ("AVDD", "AVSS")
        ys = [
            sum(generated["ports"][name]["rect_um"][k] for k in (1, 3)) / 2
            for name in names
        ]
        x = generated["bbox_um"][2] - 1 if fault == "clock_short" else 1
        lines += [
            f"c.shapes(l.layer(67,0)).insert(pya.DBox({x - 0.5!r},{min(ys)!r},{x + 0.5!r},{max(ys)!r}))"
        ]
    else:
        raise ValueError("Unknown physical fault")
    return "\n".join(lines + ["l.write(" + repr(str(output)) + ")", ""])


def lef_script(pdk, lef, generated):
    box = generated["bbox_um"]
    lines = [
        "read_lef " + quote(pdk / "libs.ref/sg13g2_stdcell/lef/sg13g2_tech.lef"),
        "read_lef " + quote(lef),
        "set master [[ord::get_db] findMaster " + TOP + "]",
        'if {$master eq "NULL"} {error "VCO master missing"}',
        f'if {{[$master getWidth] != {round(box[2] * 1000)} || [$master getHeight] != {round(box[3] * 1000)}}} {{error "VCO outline changed"}}',
        'if {[llength [$master getMTerms]] != 6} {error "Analog terminal census changed"}',
    ]
    if set(generated["ports"]) != set(PORTS):
        raise ValueError("VCO LEF pin census differs")
    for name in PORTS:
        use, direction = use_direction(name)
        coords = " ".join(
            str(round(v * 1000)) for v in generated["ports"][name]["rect_um"]
        )
        lines += [
            "set term [$master findMTerm " + name + "]",
            'if {$term eq "NULL"} {error "VCO terminal missing"}',
            'if {[$term getIoType] ne "'
            + direction
            + '" || [$term getSigType] ne "'
            + use
            + '"} {error "VCO terminal type differs"}',
            "set boxes {}; foreach pin [$term getMPins] {foreach box [$pin getGeometry] {lappend boxes [list [[$box getTechLayer] getName] [$box xMin] [$box yMin] [$box xMax] [$box yMax]]}}",
            "if {$boxes ne {{Metal5 "
            + coords
            + '}}} {error "VCO terminal geometry differs"}',
        ]
    lines += [
        "set obs {}; foreach box [$master getObstructions] {lappend obs [[$box getTechLayer] getName]}",
        'if {[lsort -unique $obs] ne {Metal1 Metal2 Metal3 Metal4 Metal5 TopMetal1 TopMetal2}} {error "VCO blockage layer census changed"}',
        "foreach term [$master getMTerms] {foreach pin [$term getMPins] {foreach pb [$pin getGeometry] {foreach ob [$master getObstructions] {",
        'if {[[$pb getTechLayer] getName] eq [[$ob getTechLayer] getName] && [$pb xMin] < [$ob xMax] && [$ob xMin] < [$pb xMax] && [$pb yMin] < [$ob yMax] && [$ob yMin] < [$pb yMax]} {error "VCO pin obstruction overlap"}',
        "}}}}",
        "puts PASS_NATIVE_ANALOG_BANK_LEF_ONLY",
    ]
    return "\n".join(lines) + "\n"


def validate_native_devices(text):
    """Census/geometry guard complements strict native topology comparison."""
    from collections import Counter
    from decimal import Decimal

    def value(token):
        scales = {"n": "1e-9", "u": "1e-6", "p": "1e-12"}
        return (
            Decimal(token[:-1]) * Decimal(scales[token[-1]])
            if token[-1] in scales
            else Decimal(token)
        )

    records = []
    for line in text.splitlines():
        if line.startswith("+"):
            records[-1] += " " + line[1:]
        elif line.strip() and not line.startswith("*"):
            records.append(line)
    rows = [line.split() for line in records if not line.startswith(".")]
    if len(rows) != 62:
        raise ValueError("Exact sixty-two unsimplified native devices required")
    geometry = Counter()
    for row in rows:
        if row[0].startswith(("Q", "M")):
            model_index = 5
        elif row[0].startswith("R") and row[3] == "rppd":
            model_index = 4
        else:
            model_index = 3
        # Extracted rppd has the explicit body terminal before its model.
        if row[0].startswith("R") and "rppd" in row:
            model_index = row.index("rppd")
        model = row[model_index]
        parameters = {
            k: value(v) for k, v in (item.split("=") for item in row[model_index + 1 :])
        }
        if len(parameters) != len(row[model_index + 1 :]):
            raise ValueError("Duplicate native device parameter")
        geometry[(model, tuple(sorted(parameters.items())))] += 1
    expected = Counter()
    root = Path(__file__).resolve().parents[3]
    reference = physical_reference((root / CIRCUIT).read_text())
    for line in reference.splitlines():
        if not line or line[0] in "*.":
            continue
        row = line.split()
        index = 5 if row[0].startswith(("Q", "M")) else (4 if "rppd" in row else 3)
        model = row[index]
        ps = {k: value(v) for k, v in (item.split("=") for item in row[index + 1 :])}
        if model == "rppd":
            ps["ps"] = Decimal(0)
        elif model == "cap_cmim":
            ps["A"] = ps["w"] * ps["l"]
            ps["P"] = 2 * (ps["w"] + ps["l"])
        elif model == "sg13_hv_pmos":
            if ps["ng"] != 1 or ps["m"] != 1:
                raise ValueError("Literal independent PMOS geometry differs")
            ps = {
                "W": ps["w"],
                "L": ps["l"],
                "AS": ps["w"] * Decimal("0.34e-6"),
                "AD": ps["w"] * Decimal("0.34e-6"),
                "PS": 2 * (ps["w"] + Decimal("0.34e-6")),
                "PD": 2 * (ps["w"] + Decimal("0.34e-6")),
                "rfmode": Decimal(0),
            }
        expected[(model, tuple(sorted(ps.items())))] += 1
    if geometry != expected:
        raise ValueError(
            "Native geometry/model/multiplicity differs from literal four-PMOS circuit and finite contacts"
        )
    for row in rows:
        if "ptap1" in row or "ntap1" in row:
            port = "SUB" if "ptap1" in row else "AVDD"
            if row[1] != port or row[2] in PORTS:
                raise ValueError("Finite native body/well contact topology differs")


def validate_lvs(step, text, positive):
    audit = step["audit"]
    if positive:
        if (
            audit["status"] != "PASS within comparison scope"
            or step["audit_execution"]["returncode"] != 0
            or extracted_ports(text, TOP) != set(PORTS)
            or len(audit["circuits"]) != 1
            or audit["circuits"][0]["layout_devices_recursive"] != 62
            or audit["circuits"][0]["schematic_devices_recursive"] != 62
        ):
            raise ValueError("Positive VCO LVS/port/device census did not pass")
        validate_native_devices(text)
    elif audit["status"] != "FAIL" or step["audit_execution"]["returncode"] != 1:
        raise ValueError("Native VCO negative was accepted")
    elif step["name"] == "control_open":
        if (
            extracted_ports(text, TOP) != set(PORTS) - {"VCTRL"}
            or len(audit["circuits"]) != 1
            or audit["circuits"][0]["layout_devices_recursive"] != 62
            or audit["circuits"][0]["schematic_devices_recursive"] != 62
        ):
            raise ValueError(
                "Control open must remove exactly VCTRL with all native devices retained"
            )
        validate_native_devices(text)
    elif audit["circuit_status_counts"].get("NoMatch", 0) < 1:
        raise ValueError("Native VCO fault failed for an unrelated reason")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ("layout", "pdk", "out"):
        parser.add_argument("--" + name, type=Path, required=True)
    args = parser.parse_args()
    root = Path(__file__).resolve().parents[3]
    out, layout, pdk = args.out.resolve(), args.layout.resolve(), args.pdk.resolve()
    if out.exists() or not (
        out.is_relative_to(root / "hw/soc/out")
        or out.is_relative_to(Path("/dev/shm"))
        and out.name.startswith("nssoc-vco-")
    ):
        parser.error("Fresh project or /dev/shm/nssoc-vco- directory required")
    generated = json.loads((layout / "result.json").read_text())
    app = root / "hw/soc/tools/physical/librelane-3.0.5-x86_64.AppImage"
    if digest(app) != APP_SHA or digest(root / CIRCUIT) != CIRCUIT_SHA256:
        raise ValueError("VCO circuit or native runtime changed")
    gds, schematic = layout / (TOP + ".gds"), layout / "schematic.cir"
    if schematic.read_text() != physical_reference((root / CIRCUIT).read_text()):
        raise ValueError("Physical reference differs from frozen VCO")
    pins = {Path(k): v for k, v in generated["input_sha256"].items()}
    for name, expected in generated["output_sha256"].items():
        if digest(layout / name) != expected:
            raise ValueError("Generated physical view changed")
        pins[layout / name] = expected
    methods = [
        "check_pcie_clock_vco_v4_local_v2.py",
        "make_pcie_clock_vco_v4_local_v2.py",
        "check_pcie_rx_cell.py",
        "check_pcie_analog_bank.py",
        "make_pcie_analog_bank.py",
        "make_pcie_rx_cell.py",
        "make_pcie_rx_cell_v2.py",
        "check_ihp_drc.py",
        "prepare_ihp_drc.py",
        "audit_klayout_lvs.py",
    ]
    for path in [
        app,
        layout / "result.json",
        pdk / "libs.ref/sg13g2_stdcell/lef/sg13g2_tech.lef",
        *(root / "hw/soc/flow" / name for name in methods),
    ]:
        pins[path] = digest(path)
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
    if any(not p.is_file() or digest(p) != h for p, h in pins.items()):
        raise ValueError("Physical source changed before validation")
    out.mkdir(parents=True)
    record = dict(
        status="RUNNING",
        inputs={str(p): h for p, h in pins.items()},
        steps=[],
        phy_complete=False,
        qualified_pex=False,
        manufacturing_approval=False,
        scope="Compact four-PMOS voltage-controlled VCO v4 physical connectivity and main-rule screen only; no post-layout oscillation/PLL/fanout acceptance.",
    )

    def save():
        (out / "result.json").write_text(json.dumps(record, indent=2) + "\n")

    try:
        save()
        for name in (
            "drc",
            "offgrid",
            "lvs",
            "lvs_flat",
            *REFERENCE_FAULTS,
            *PHYSICAL_FAULTS,
        ):
            directory = out / name
            directory.mkdir()
            step = dict(name=name)
            record["steps"].append(step)
            save()
            physical, reference = gds, schematic
            if name == "offgrid" or name in PHYSICAL_FAULTS:
                physical = directory / "wrong.gds"
                script = directory / "mutate.py"
                script.write_text(mutation_source(gds, physical, generated, name))
                step["mutation_execution"] = execute(
                    [app, "python", script], directory, "mutation"
                )
                if step["mutation_execution"]["returncode"] != 0 or digest(
                    physical
                ) == digest(gds):
                    raise ValueError("Physical fault did not bind")
            if name in REFERENCE_FAULTS:
                reference = directory / "wrong.cir"
                reference.write_text(fault_reference(schematic.read_text(), name))
            drc = name in ("drc", "offgrid")
            entry = root / (
                "hw/soc/tools/ihp-drc-5e6d592/ihp-sg13g2/libs.tech/klayout/tech/drc/ihp-sg13g2.drc"
                if drc
                else "hw/soc/tools/ihp-lvs-5e6d592/ihp-sg13g2/libs.tech/klayout/tech/lvs/sg13g2.lvs"
            )
            options = [
                "input=" + str(physical),
                "topcell=" + TOP,
                "log=" + str(directory / "deck.log"),
                "run_mode=flat" if name == "lvs_flat" else "run_mode=deep",
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
                    "schematic=" + str(reference),
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
                measurement = record_result(directory, TOP, 0, pins)
                step["measurement"], step["status"] = measurement, measurement["status"]
                if (
                    measurement["category_count"] != 560
                    or "KLayout DRC run for tables 'main' completed"
                    not in (directory / "run.log").read_text()
                ):
                    raise ValueError("Native main rule census incomplete")
                if name == "drc" and measurement["status"] != "PASS":
                    raise ValueError("VCO main DRC failed")
                if name == "offgrid" and (
                    measurement["status"] != "FAIL"
                    or measurement["categories"].get("metal1_drw_Offgrid", 0) < 1
                ):
                    raise ValueError("Physical DRC fault was accepted")
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
                step["audit"] = json.loads((directory / "audit.json").read_text())
                step["status"] = step["audit"]["status"]
                validate_lvs(
                    step,
                    (directory / "extracted.cir").read_text(),
                    name in ("lvs", "lvs_flat"),
                )
            save()
            print(name, step["status"], flush=True)
        for negative in (None, "missing_pin", "blocked_pin"):
            directory = out / ("lef_" + negative if negative else "lef")
            directory.mkdir()
            view = layout / (TOP + ".lef")
            if negative == "missing_pin":
                text, count = re.subn(
                    r"  PIN VCTRL\n.*?  END VCTRL\n", "", view.read_text(), flags=re.S
                )
                if count != 1:
                    raise ValueError("LEF fault did not bind")
                view = directory / "wrong.lef"
                view.write_text(text)
            if negative == "blocked_pin":
                pin = generated["ports"]["CLKP"]["rect_um"]
                obstruction = (
                    "      RECT " + " ".join(f"{value:.3f}" for value in pin) + " ;\n"
                )
                text = view.read_text()
                if text.count("  OBS\n") != 1:
                    raise ValueError("LEF obstruction insertion did not bind")
                text = text.replace(
                    "  OBS\n", "  OBS\n    LAYER Metal5 ;\n" + obstruction, 1
                )
                view = directory / "wrong.lef"
                view.write_text(text)
            script = directory / "inspect.tcl"
            script.write_text(lef_script(pdk, view, generated))
            execution = execute([app, "openroad", "-exit", script], directory, "native")
            log = (directory / "native.log").read_text()
            if negative == "blocked_pin":
                if (
                    execution["returncode"] == 0
                    or "PASS_NATIVE_ANALOG_BANK_LEF_ONLY" in log
                    or len(
                        re.findall(
                            r"^Error: inspect\.tcl, \d+ VCO pin obstruction overlap$",
                            log,
                            re.M,
                        )
                    )
                    != 1
                ):
                    raise ValueError(
                        "Blocked clock-pin LEF negative failed incorrectly"
                    )
            else:
                validate_lef(execution["returncode"], log, bool(negative))
            record["steps"].append(
                dict(
                    name=directory.name,
                    execution=execution,
                    status="EXPECTED_REJECTION" if negative else "PASS",
                )
            )
            save()
        if any(digest(p) != h for p, h in pins.items()):
            raise ValueError("Physical inputs changed during native validation")
        record["status"] = (
            "PASS_VCO_MAIN_DRC_STRICT_DEEP_FLAT_LVS_LEF_AND_TWENTY_NEGATIVE_CONTROLS_ONLY"
        )
        record["outputs"] = {
            str(p.relative_to(out)): digest(p)
            for p in sorted(out.rglob("*"))
            if p.is_file() and p != out / "result.json"
        }
        save()
    except BaseException as error:
        record.update(status="FAILED_OR_INCOMPLETE", error=repr(error))
        save()
        raise


if __name__ == "__main__":
    main()
