#!/usr/bin/env python3
# SPDX-FileCopyrightText: 2026 Hasan Melih Akbulut
# SPDX-License-Identifier: Apache-2.0
"""Strict actual padded-bank connectivity/geometry tests, not a complete PHY or main chip."""

import argparse
from collections import Counter
import json
from pathlib import Path
import re
from check_ihp_drc import digest, record_result
from check_pcie_rx_cell import execute
from check_pcie_analog_bank import extracted_ports, quote, validate_lef
from make_pcie_analog_bank import use_direction, PORTS
from make_pcie_padded_bank import TOP, WIDTH, HEIGHT, reference, serial_net
from prepare_ihp_drc import validate_lock, verify

APP_SHA = "d6a349ec65be11456e96c4981d35f63ca34d3c85daf79a51e1ccb907bb5d7466"


def fault_reference(text, fault):
    changes = {
        "wrong_lane": (
            "Q2RX_P L2_RX_OUTN L2_RX_INP L2_RX_TAIL",
            "Q2RX_P L2_RX_OUTN L1_RX_INP L2_RX_TAIL",
        ),
        "missing_tap": ("R0TX_TAP0 SUB AVSS ptap1 A=4p P=8u\n", ""),
        "wrong_diode": (
            "D0TX_Pdd AVDD L0_TX_OUTP AVSS diodevdd_2kv m=1",
            "D0TX_Pdd AVDD L0_TX_OUTP AVSS diodevdd_2kv m=2",
        ),
    }
    if fault not in changes:
        raise ValueError("Unknown physical comparison fault")
    old, new = changes[fault]
    if text.count(old) != 1:
        raise ValueError("Fault must change one original device")
    return text.replace(old, new)


def mutation(gds, out, fault, generated):
    s = (
        "import pya\nl=pya.Layout()\nl.read("
        + repr(str(gds))
        + ")\nc=l.cell("
        + repr(TOP)
        + ")\n"
    )
    if fault == "physical_offgrid":
        s += "c.shapes(l.layer(8,0)).insert(pya.DBox(2.002,2,2.102,2.1))\n"
    elif fault == "physical_rail_short":
        s += "c.shapes(l.layer(10,0)).insert(pya.DBox(10,19,12,41))\n"
    elif fault == "physical_bulk_short":
        s += "c.shapes(l.layer(134,0)).insert(pya.DBox(530,61,546,63))\n"
    elif fault == "physical_serial_open":
        rows = [
            r
            for r in generated["vias"]
            if r["net"] == "L2_RX_INP"
            and r["bottom"] == "TopMetal1"
            and r["top"] == "TopMetal2"
        ]
        if len(rows) != 1:
            raise ValueError("Specific parent RX input via is not unique")
        x, y = rows[0]["center_um"]
        s += f"matches=[i for i in c.each_inst() if i.dbbox().center()==pya.DPoint({x!r},{y!r}) and not pya.Region(l.cell(i.cell_index).begin_shapes_rec(l.layer(133,0))).is_empty()]\nif len(matches)!=1:raise ValueError('Specific parent RX input via not unique in native geometry')\nmatches[0].delete()\n"
    else:
        raise ValueError("Unknown physical mutation")
    return s + "l.write(" + repr(str(out)) + ")\n"


def inspect_native(layout, dbpath, out):
    import pya

    rec = json.loads((layout / "result.json").read_text())
    l = pya.Layout()
    l.read(str(layout / (TOP + ".gds")))
    top = l.cell(TOP)
    inputs = rec["input_sha256"]
    source_paths = {}
    for label, name in [
        ("bank", "nssoc_pcie_analog_bank4.gds"),
        ("pad", "nssoc_pcie_pad_boundary.gds"),
    ]:
        paths = [Path(p) for p in inputs if Path(p).name == name]
        # Historical wrong/fault GDS names differ; exactly one verified positive per type.
        if len(paths) != 1:
            raise ValueError("Ambiguous positive primitive source")
        source_paths[label] = paths[0]
        native = pya.Layout()
        native.read(str(paths[0]))
        before = native.top_cell()
        after = l.cell("padded_" + label)
        for info in set(l.layer_infos()) | set(native.layer_infos()):
            if info.datatype in (2, 25):
                continue
            a = pya.Region(before.begin_shapes_rec(native.layer(info)))
            b = pya.Region(after.begin_shapes_rec(l.layer(info)))
            if not (a ^ b).is_empty():
                raise ValueError(
                    "Conductive/device geometry of preserved source changed"
                )
    found = []
    for inst in top.each_inst():
        c = l.cell(inst.cell_index)
        if c.name in ("padded_bank", "padded_pad"):
            found.append((c.name, str(inst.dtrans)))
    expected = [("padded_bank", str(pya.DTrans(300.0, 60.0)))] + [
        (
            "padded_pad",
            str(
                pya.DTrans(3, False, 0.0, i * 360.0 + 280.0)
                if kind == "TX"
                else pya.DTrans(1, False, 860.0, i * 360.0 + 200.0)
            ),
        )
        for i in range(4)
        for kind in ("TX", "RX")
    ]
    if Counter(found) != Counter(expected):
        raise ValueError("Nine actual parent placements differ")
    layers = {
        "Metal1": 8,
        "Metal2": 10,
        "Metal3": 30,
        "Metal4": 50,
        "Metal5": 67,
        "TopMetal1": 126,
        "TopMetal2": 134,
    }
    for n, row in rec["ports"].items():
        b = pya.DBox(*row["rect_um"])
        shape = pya.Region(b.to_itype(l.dbu))
        drawing = pya.Region(top.begin_shapes_rec(l.layer(layers[row["layer"]], 0)))
        if not (shape - drawing).is_empty():
            raise ValueError("Parent access lacks real conductive geometry")
        labels = [
            s.dtext.string
            for s in top.each_shape(l.layer(layers[row["layer"]], 25))
            if s.is_text() and s.dtext.string == n and b.contains(s.dtext.trans.disp)
        ]
        if labels != [n]:
            raise ValueError("Parent access name/geometry changed")
    text = (layout / (TOP + ".lef")).read_text()
    obs = text.split("  OBS\n")
    if len(obs) != 2:
        raise ValueError("Unique LEF OBS required")
    sections = re.findall(r"    LAYER (\w+) ;\n((?:      RECT [^\n]+\n)+)", obs[1])
    if [m for m, _ in sections] != list(layers):
        raise ValueError("Exact seven blockage layers required")
    for metal, body in sections:
        actual = pya.Region()
        for line in body.splitlines():
            actual.insert(
                pya.DBox(*[float(x) for x in line.split()[1:5]]).to_itype(l.dbu)
            )
        expected_region = pya.Region(pya.DBox(0, 0, WIDTH, HEIGHT).to_itype(l.dbu))
        for row in rec["ports"].values():
            if row["layer"] == metal:
                expected_region -= pya.Region(pya.DBox(*row["rect_um"]).to_itype(l.dbu))
        if not (actual ^ expected_region).is_empty():
            raise ValueError("Exact obstruction union changed")
    db = pya.LayoutVsSchematic()
    db.read(str(dbpath))
    c = db.netlist().circuit_by_name(TOP)
    counts = Counter()
    esd = []
    tap = []
    for d in c.each_device():
        cls = d.device_class()
        counts[cls.name] += 1
        nets = {
            t.name: d.net_for_terminal(t.id()).name for t in cls.terminal_definitions()
        }
        if cls.name == "npn13G2" and nets["S"] != "AVSS":
            raise ValueError("Physical HBT bulk not on actual substrate return")
        if cls.name == "rsil" and nets["rsil_sub"] != "AVSS":
            raise ValueError("Physical resistor substrate differs")
        if cls.name == "ptap1":
            tap.append(
                dict(
                    terminals=nets,
                    area_um2=d.parameter("A"),
                    perimeter_um=d.parameter("P"),
                )
            )
            if (
                nets != {"TIE": "SUB", "WELL": "AVSS"}
                or d.parameter("A") != 256.0
                or d.parameter("P") != 512.0
            ):
                raise ValueError("Literal tap geometry or separate SUB access changed")
        if cls.name.startswith("diodev"):
            expected = {
                "C": "AVSS" if cls.name == "diodevdd_2kv" else "AVDD",
                "B": "AVDD" if cls.name == "diodevdd_2kv" else "AVSS",
            }
            if any(nets[k] != v for k, v in expected.items()) or d.parameter("m") != 1:
                raise ValueError("Native ESD rail/polarity differs")
            esd.append((cls.name, nets["E"]))
    if counts != {
        "npn13G2": 32,
        "rsil": 24,
        "ptap1": 1,
        "diodevdd_2kv": 16,
        "diodevss_2kv": 16,
    }:
        raise ValueError("Native device inventory differs")
    expected_esd = [
        (model, serial_net(i, k, p))
        for model in ("diodevdd_2kv", "diodevss_2kv")
        for i in range(4)
        for k in ("TX", "RX")
        for p in ("P", "N")
    ]
    if Counter(esd) != Counter(expected_esd) or {p.name() for p in c.each_pin()} != set(
        PORTS
    ):
        raise ValueError("All sixteen real serial-pad connections not proved")
    out.write_text(
        json.dumps(
            dict(
                status="PASS_NINE_SOURCE_IDENTICAL_INSTANCES_47_ACCESS_PORTS_16_REAL_SERIAL_PAD_CONNECTIONS_AND_ACTUAL_SUBSTRATE_RETURN",
                source_paths={k: str(v) for k, v in source_paths.items()},
                placements=found,
                device_counts=dict(counts),
                named_esd_connections=esd,
                actual_literal_tap=tap,
                exact_seven_layer_obstruction_union=True,
                main_chip_integrated=False,
                qualified_pex=False,
                esd_qualified=False,
            ),
            indent=2,
        )
        + "\n"
    )


def lef_script(pdk, path, record):
    lines = [
        "read_lef " + quote(pdk / "libs.ref/sg13g2_stdcell/lef/sg13g2_tech.lef"),
        "read_lef " + quote(path),
        "set m [[ord::get_db] findMaster " + TOP + "]",
        'if {$m eq "NULL"} {error "Analog master missing"}',
        f'if {{[$m getWidth]!={round(WIDTH * 1000)} || [$m getHeight]!={round(HEIGHT * 1000)}}} {{error "Analog outline changed"}}',
        'if {[llength [$m getMTerms]]!=47} {error "Analog terminal census changed"}',
    ]
    for n, row in record["ports"].items():
        use, direction = use_direction(n)
        coords = " ".join(str(round(v * 1000)) for v in row["rect_um"])
        lines += [
            "set t [$m findMTerm " + n + "]",
            'if {$t eq "NULL" || [$t getIoType] ne "'
            + direction
            + '" || [$t getSigType] ne "'
            + use
            + '"} {error "Analog terminal contract changed"}',
            "set boxes {}; foreach p [$t getMPins] {foreach b [$p getGeometry] {lappend boxes [list [[$b getTechLayer] getName] [$b xMin] [$b yMin] [$b xMax] [$b yMax]]}}",
            "if {$boxes ne {{"
            + row["layer"]
            + " "
            + coords
            + '}}} {error "Analog physical access changed"}',
        ]
    return "\n".join(lines + ["puts PASS_NATIVE_ANALOG_BANK_LEF_ONLY", ""])


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    for n in ("layout", "pdk", "out"):
        ap.add_argument("--" + n, type=Path, required=True)
    ap.add_argument("--native-inspect", type=Path)
    a = ap.parse_args()
    root = Path(__file__).resolve().parents[3]
    layout = a.layout.resolve()
    out = a.out.resolve()
    pdk = a.pdk.resolve()
    if a.native_inspect:
        return inspect_native(layout, a.native_inspect, out)
    if out.exists() or not (
        out.is_relative_to(root / "hw/soc/out")
        or out.is_relative_to(Path("/dev/shm"))
        and out.name.startswith("nssoc-padded-")
    ):
        ap.error("Fresh output required")
    rec = json.loads((layout / "result.json").read_text())
    pins = {Path(p): h for p, h in rec["input_sha256"].items()}
    app = root / "hw/soc/tools/physical/librelane-3.0.5-x86_64.AppImage"
    if digest(app) != APP_SHA:
        raise ValueError("Native runtime differs")
    for n, h in rec["output_sha256"].items():
        pins[layout / n] = h
    for p in [
        Path(__file__).resolve(),
        app,
        layout / "result.json",
        pdk / "libs.ref/sg13g2_stdcell/lef/sg13g2_tech.lef",
        *[
            root / "hw/soc/flow" / n
            for n in (
                "make_pcie_padded_bank.py",
                "check_pcie_rx_cell.py",
                "check_pcie_analog_bank.py",
                "check_ihp_drc.py",
                "prepare_ihp_drc.py",
                "audit_klayout_lvs.py",
            )
        ],
    ]:
        pins[p] = digest(p)
    for typ in ("drc", "lvs"):
        p = root / f"hw/soc/pnr/ihp-{typ}.lock.json"
        lock = json.loads(p.read_text())
        validate_lock(lock)
        if lock["commit"] != "5e6d592e4002946a4616f798c357f0f3c06cf3b6":
            raise ValueError("Unchanged strict deck required")
        pins[p] = digest(p)
        for row in lock["files"]:
            p = root / f"hw/soc/tools/ihp-{typ}-5e6d592" / row["path"]
            verify(p.read_bytes(), row)
            pins[p] = row["sha256"]
    bankrefs = [
        p
        for p in pins
        if p.name == "schematic.cir" and p.parent.name == "nssoc-bank-02"
    ]
    if len(bankrefs) != 1 or (layout / "schematic.cir").read_text() != reference(
        bankrefs[0].read_text()
    ):
        raise ValueError("Literal parent reference not reproduced")
    if any(digest(p) != h for p, h in pins.items()):
        raise ValueError("Input identity changed")
    out.mkdir(parents=True)
    result = dict(
        status="RUNNING",
        inputs={str(p): h for p, h in pins.items()},
        steps=[],
        main_chip_integrated=False,
        phy_complete=False,
        qualified_pex=False,
        esd_qualified=False,
    )

    def save():
        (out / "result.json").write_text(json.dumps(result, indent=2) + "\n")

    try:
        for name in (
            "drc",
            "physical_offgrid",
            "lvs",
            "wrong_lane",
            "missing_tap",
            "wrong_diode",
            "physical_serial_open",
            "physical_bulk_short",
            "physical_rail_short",
        ):
            d = out / name
            d.mkdir()
            step = dict(name=name)
            result["steps"].append(step)
            save()
            gds = layout / (TOP + ".gds")
            net = layout / "schematic.cir"
            if name.startswith("physical_"):
                wrong = d / "wrong.gds"
                script = d / "mutate.py"
                script.write_text(mutation(gds, wrong, name, rec))
                step["mutation_execution"] = execute(
                    [app, "python", script], d, "mutation"
                )
                if step["mutation_execution"]["returncode"] != 0 or digest(
                    wrong
                ) == digest(gds):
                    raise ValueError("Native physical negative failed to bind")
                gds = wrong
            elif name not in ("drc", "lvs"):
                wrong = d / "wrong.cir"
                wrong.write_text(fault_reference(net.read_text(), name))
                net = wrong
            drc = name in ("drc", "physical_offgrid")
            entry = root / (
                "hw/soc/tools/ihp-drc-5e6d592/ihp-sg13g2/libs.tech/klayout/tech/drc/ihp-sg13g2.drc"
                if drc
                else "hw/soc/tools/ihp-lvs-5e6d592/ihp-sg13g2/libs.tech/klayout/tech/lvs/sg13g2.lvs"
            )
            opts = dict(
                input=gds,
                topcell=TOP,
                log=d / "deck.log",
                run_mode="deep" if drc else "flat",
            )
            opts.update(
                dict(
                    report=d / "drc.lyrdb",
                    threads=2,
                    no_recommended="False",
                    precheck_drc="False",
                )
                if drc
                else dict(
                    schematic=net,
                    report=d / "result.lvsdb",
                    target_netlist=d / "extracted.cir",
                    thr=2,
                )
            )
            cmd = [app, "klayout", "-b", "-zz", "-r", entry]
            for k, v in opts.items():
                cmd += ["-rd", f"{k}={v}"]
            step["execution"] = execute(cmd, d, "run")
            if step["execution"]["returncode"] != 0:
                raise ValueError("Native deck did not complete")
            if drc:
                m = record_result(d, TOP, 0, pins)
                step["measurement"] = m
                step["status"] = m["status"]
                if (
                    m.get("category_count") != 560
                    or "KLayout DRC run for tables 'main' completed"
                    not in (d / "run.log").read_text()
                ):
                    raise ValueError("Main deck incomplete")
                if name == "drc" and m["status"] != "PASS":
                    raise ValueError("Actual padded bank DRC failed")
                if name != "drc" and (
                    m["status"] != "FAIL"
                    or m["categories"].get("metal1_drw_Offgrid", 0) < 1
                ):
                    raise ValueError("Native offgrid control not rejected")
            else:
                step["audit_execution"] = execute(
                    [
                        app,
                        "python",
                        root / "hw/soc/flow/audit_klayout_lvs.py",
                        d / "result.lvsdb",
                        "--top",
                        TOP,
                        "--deck-log",
                        d / "deck.log",
                        "--output",
                        d / "audit.json",
                    ],
                    d,
                    "audit",
                )
                audit = json.loads((d / "audit.json").read_text())
                step["audit"] = audit
                step["status"] = audit["status"]
                if name == "lvs":
                    expected = [
                        dict(
                            layout=TOP,
                            schematic=TOP.upper(),
                            status="Match",
                            layout_devices_recursive=89,
                            schematic_devices_recursive=89,
                        )
                    ]
                    if (
                        step["audit_execution"]["returncode"] != 0
                        or audit["status"] != "PASS within comparison scope"
                        or audit["circuits"] != expected
                        or extracted_ports((d / "extracted.cir").read_text(), TOP)
                        != set(PORTS)
                    ):
                        raise ValueError("Strict89-device/47-port parent LVS failed")
                elif (
                    step["audit_execution"]["returncode"] != 1
                    or audit["status"] != "FAIL"
                    or audit["circuit_status_counts"].get("NoMatch", 0) < 1
                ):
                    raise ValueError("Specific native LVS negative not rejected")
            save()
            print(name, step["status"], flush=True)
        result["geometry_execution"] = execute(
            [
                app,
                "python",
                Path(__file__).resolve(),
                "--layout",
                layout,
                "--pdk",
                pdk,
                "--out",
                out / "native-geometry.json",
                "--native-inspect",
                out / "lvs/result.lvsdb",
            ],
            out,
            "native-geometry",
        )
        if result["geometry_execution"]["returncode"] != 0:
            raise ValueError(
                "Native source geometry or actual terminal topology failed"
            )
        result["native_geometry"] = json.loads(
            (out / "native-geometry.json").read_text()
        )
        for negative in (False, True):
            d = out / ("lef_missing_pin" if negative else "lef")
            d.mkdir()
            lef = layout / (TOP + ".lef")
            if negative:
                text, n = re.subn(
                    r"  PIN L0_RX_VCM\n.*?  END L0_RX_VCM\n",
                    "",
                    lef.read_text(),
                    flags=re.S,
                )
                if n != 1:
                    raise ValueError("Missing physical port mutation did not bind")
                lef = d / "wrong.lef"
                lef.write_text(text)
            script = d / "inspect.tcl"
            script.write_text(lef_script(pdk, lef, rec))
            execution = execute([app, "openroad", "-exit", script], d, "native")
            validate_lef(
                execution["returncode"], (d / "native.log").read_text(), negative
            )
            result["steps"].append(
                dict(
                    name=d.name,
                    status="EXPECTED_REJECTION" if negative else "PASS",
                    execution=execution,
                )
            )
            save()
        if any(digest(p) != h for p, h in pins.items()):
            raise ValueError("Inputs changed during verification")
        result["status"] = (
            "PASS_PADDED_BANK4_NATIVE_MAIN_DRC_STRICT_LVS_47_PORTS_8_NEGATIVES_NOT_FULL_PHY_OR_CHIP"
        )
        result["outputs"] = {
            str(p.relative_to(out)): digest(p)
            for p in sorted(out.rglob("*"))
            if p.is_file() and p != out / "result.json"
        }
        save()
    except BaseException as exc:
        result.update(status="FAILED_OR_INCOMPLETE", error=repr(exc))
        save()
        raise


if __name__ == "__main__":
    main()
