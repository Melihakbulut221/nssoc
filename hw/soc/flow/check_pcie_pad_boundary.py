#!/usr/bin/env python3
# SPDX-FileCopyrightText: 2026 Hasan Melih Akbulut
# SPDX-License-Identifier: Apache-2.0
"""Strict native pad/ESD structure checks; no HBM, RF, PEX or chip acceptance."""

import argparse
import json
from pathlib import Path
import re

from check_ihp_drc import digest, record_result
from check_pcie_rx_cell import execute
from make_pcie_pad_boundary import TOP, PORTS, reference
from prepare_ihp_drc import validate_lock, verify

APP_SHA = "d6a349ec65be11456e96c4981d35f63ca34d3c85daf79a51e1ccb907bb5d7466"
REV = "5e6d592e4002946a4616f798c357f0f3c06cf3b6"


def fault_reference(text, fault):
    if text != reference():
        raise ValueError("Original four-device reference changed")
    changes = {
        "multiplicity": (
            "DPdd AVDD PADP AVSS diodevdd_2kv m=1",
            "DPdd AVDD PADP AVSS diodevdd_2kv m=2",
        ),
        "wrong_polarity": (
            "DPdd AVDD PADP AVSS diodevdd_2kv m=1",
            "DPdd AVDD PADP AVSS diodevss_2kv m=1",
        ),
        "wrong_rail": (
            "DPdd AVDD PADP AVSS diodevdd_2kv m=1",
            "DPdd AVSS PADP AVDD diodevdd_2kv m=1",
        ),
    }
    if fault not in changes:
        raise ValueError("Unknown reference fault")
    old, new = changes[fault]
    if text.count(old) != 1:
        raise ValueError("Ambiguous reference mutation")
    return text.replace(old, new)


def expected_terminals():
    return sorted(
        (
            model,
            tuple(
                sorted(
                    dict(
                        C="AVSS" if model == "diodevdd_2kv" else "AVDD",
                        B="AVDD" if model == "diodevdd_2kv" else "AVSS",
                        E=pad,
                    ).items()
                )
            ),
        )
        for model in ("diodevdd_2kv", "diodevss_2kv")
        for pad in ("PADP", "PADN")
    )


def native_inspect(layout, pdk, report, out):
    import pya

    generated = json.loads((layout / "result.json").read_text())
    l = pya.Layout()
    l.read(str(layout / (TOP + ".gds")))
    top = l.cell(TOP)
    original = pya.Layout()
    original.read(str(pdk / "libs.ref/sg13g2_pr/gds/sg13g2_pr.gds"))
    expected = {
        (row["kind"], tuple(row["translation_um"]))
        for row in generated["instances"]
        if row["kind"].startswith("diode")
    }
    observed = []
    for inst in top.each_inst():
        c = l.cell(inst.cell_index)
        if not c.name.startswith(("diodevdd_2kv", "diodevss_2kv")):
            continue
        model = "diodevdd_2kv" if c.name.startswith("diodevdd_2kv") else "diodevss_2kv"
        t = inst.dtrans
        if t.angle != 0 or t.is_mirror():
            raise ValueError("ESD primitive rotated or mirrored unexpectedly")
        key = (model, (t.disp.x, t.disp.y))
        if key not in expected:
            raise ValueError("ESD primitive placement differs")
        native = original.cell(model)
        for info in set(l.layer_infos()) | set(original.layer_infos()):
            a = pya.Region(c.begin_shapes_rec(l.layer(info)))
            b = pya.Region(native.begin_shapes_rec(original.layer(info)))
            if not (a ^ b).is_empty():
                raise ValueError("Fixed ESD primitive geometry changed")
        observed.append(key)
    if len(observed) != 4 or set(observed) != expected:
        raise ValueError("Four exact ESD placements missing")
    layers = {"Metal5": 67, "TopMetal2": 134}
    geometry = {}
    for name in PORTS:
        row = generated["ports"][name]
        layer = layers[row["layer"]]
        drawing = pya.Region(top.begin_shapes_rec(l.layer(layer, 0)))
        pin = pya.Region()
        for coords in row["rectangles_um"]:
            pin.insert(pya.DBox(*coords).to_itype(l.dbu))
        if not (pin - drawing).is_empty():
            raise ValueError("Port is not on real conductor")
        labels = [
            s.dtext.string
            for s in top.each_shape(l.layer(layer, 25))
            if s.is_text() and s.dtext.string == name
        ]
        if len(labels) != len(row["rectangles_um"]):
            raise ValueError("Missing explicit physical port access labels")
        geometry[name] = row
    # LEF is deliberately fully blocked except its six actual conductor accesses.
    text = (layout / (TOP + ".lef")).read_text()
    obs = text.split("  OBS\n")
    if len(obs) != 2:
        raise ValueError("Exact LEF obstruction section required")
    sections = re.findall(r"    LAYER (\w+) ;\n((?:      RECT [^\n]+\n)+)", obs[1])
    metals = (
        "Metal1",
        "Metal2",
        "Metal3",
        "Metal4",
        "Metal5",
        "TopMetal1",
        "TopMetal2",
    )
    if tuple(m for m, _ in sections) != metals:
        raise ValueError("Exact seven LEF obstruction layers required")
    for metal, body in sections:
        actual = pya.Region()
        for row in body.splitlines():
            coords = [float(v) for v in row.split()[1:5]]
            actual.insert(pya.DBox(*coords).to_itype(l.dbu))
        expected = pya.Region(pya.DBox(0, 0, 220, 220).to_itype(l.dbu))
        for port in generated["ports"].values():
            if port["layer"] == metal:
                for box in port["rectangles_um"]:
                    expected -= pya.Region(pya.DBox(*box).to_itype(l.dbu))
        if not (actual ^ expected).is_empty():
            raise ValueError(
                "LEF obstruction coverage differs from exact outline minus actual ports"
            )
    db = pya.LayoutVsSchematic()
    db.read(str(report))
    c = db.netlist().circuit_by_name(TOP)
    terms = []
    for d in c.each_device():
        cls = d.device_class()
        if d.parameter("m") != 1:
            raise ValueError("ESD multiplicity changed")
        terms.append(
            (
                cls.name,
                tuple(
                    sorted(
                        (t.name, d.net_for_terminal(t.id()).name)
                        for t in cls.terminal_definitions()
                    )
                ),
            )
        )
    if sorted(terms) != expected_terminals():
        raise ValueError("Extracted native C/B/E to model VDD/PAD/VSS binding differs")
    if sorted(p.name() for p in c.each_pin()) != sorted(PORTS):
        raise ValueError("Extracted four-port contract differs")
    result = dict(
        status="PASS_FIXED_PRIMITIVES_TRANSFORMS_PHYSICAL_PORTS_AND_NAMED_ESD_TERMINALS",
        fixed_primitive_xor_zero=True,
        exact_seven_layer_obstruction_union=True,
        placements=observed,
        physical_ports=geometry,
        native_terminals=terms,
        raw_export_not_simulator_input=True,
    )
    out.write_text(json.dumps(result, indent=2) + "\n")


def mutation_script(gds, out, fault):
    prefix = (
        "import pya\nl=pya.Layout()\nl.read("
        + repr(str(gds))
        + ")\nc=l.cell("
        + repr(TOP)
        + ")\n"
    )
    if fault == "offgrid":
        body = "c.shapes(l.layer(8,0)).insert(pya.DBox(2.002,2.0,2.102,2.1))\n"
    elif fault == "pad_short":
        body = "c.shapes(l.layer(134,0)).insert(pya.DBox(48,208,152,212))\n"
    elif fault == "pad_open":
        body = "matches=[i for i in c.each_inst() if l.cell(i.cell_index).name.startswith('via_stack') and i.dbbox().center()==pya.DPoint(50.,140.) and not pya.Region(l.cell(i.cell_index).begin_shapes_rec(l.layer(133,0))).is_empty()]\nif len(matches)!=1:raise ValueError('Specific PADP TopVia2 not unique')\nfor i in matches:i.delete()\n"
    else:
        raise ValueError("Unknown physical fault")
    return prefix + body + "l.write(" + repr(str(out)) + ")\n"


def lef_script(pdk, lef, generated):
    def q(value):
        s = str(value)
        if any(c in s for c in "{}\n\r"):
            raise ValueError("Unsafe Tcl path")
        return "{" + s + "}"

    lines = [
        "read_lef " + q(pdk / "libs.ref/sg13g2_stdcell/lef/sg13g2_tech.lef"),
        "read_lef " + q(lef),
        "set master [[ord::get_db] findMaster " + TOP + "]",
        'if {$master eq "NULL"} {error "Pad master missing"}',
        'if {[$master getWidth]!=220000 || [$master getHeight]!=220000} {error "Pad outline changed"}',
        'if {[llength [$master getMTerms]]!=4} {error "Pad terminal census changed"}',
    ]
    for name in PORTS:
        row = generated["ports"][name]
        use = "POWER" if name == "AVDD" else "GROUND" if name == "AVSS" else "SIGNAL"
        boxes = " ".join(
            "{" + row["layer"] + " " + " ".join(str(round(v * 1000)) for v in b) + "}"
            for b in row["rectangles_um"]
        )
        lines += [
            "set t [$master findMTerm " + name + "]",
            'if {$t eq "NULL" || [$t getIoType] ne "INOUT" || [$t getSigType] ne "'
            + use
            + '"} {error "Pad terminal type changed"}',
            "set boxes {}; foreach p [$t getMPins] {foreach b [$p getGeometry] {lappend boxes [list [[$b getTechLayer] getName] [$b xMin] [$b yMin] [$b xMax] [$b yMax]]}}",
            "if {[lsort $boxes] ne [lsort {"
            + boxes
            + '}]} {error "Pad terminal geometry changed"}',
        ]
    lines += [
        "set layers {}; foreach b [$master getObstructions] {lappend layers [[$b getTechLayer] getName]}",
        'if {[lsort -unique $layers] ne {Metal1 Metal2 Metal3 Metal4 Metal5 TopMetal1 TopMetal2}} {error "Pad obstruction layers changed"}',
        "puts PASS_NATIVE_PAD_LEF_FOUR_NETS_SIX_ACCESSES_NO_RF_APPROVAL",
    ]
    return "\n".join(lines) + "\n"


def validate_open(audit, code, extracted):
    """An isolated bondpad disappears as a top port: require that exact strict failure."""
    headers = re.findall(r"^\.SUBCKT\s+" + TOP + r"\s+(.*)$", extracted, re.M | re.I)
    expected = [
        dict(
            layout=TOP,
            schematic=TOP.upper(),
            status="Match",
            layout_devices_recursive=4,
            schematic_devices_recursive=4,
        )
    ]
    if (
        code != 1
        or audit["status"] != "FAIL"
        or audit["circuits"] != expected
        or audit["extraction_diagnostics"]
        or audit["reasons"]
        != [
            "Missing explicit successful deck verdict",
            "Deck explicitly reported a mismatch",
        ]
        or len(headers) != 1
        or set(headers[0].split()) != {"AVDD", "AVSS", "PADN"}
    ):
        raise ValueError(
            "Physical open did not produce exact missing-only-PADP strict rejection"
        )


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
        return native_inspect(layout, pdk, a.native_inspect, out)
    if out.exists() or not (
        out.is_relative_to(root / "hw/soc/out")
        or out.is_relative_to(Path("/dev/shm"))
        and out.name.startswith("nssoc-pad-")
    ):
        ap.error("Fresh project or /dev/shm/nssoc-pad- output required")
    generated = json.loads((layout / "result.json").read_text())
    app = root / "hw/soc/tools/physical/librelane-3.0.5-x86_64.AppImage"
    if digest(app) != APP_SHA:
        raise ValueError("Unrecognized exact native runtime")
    pins = {Path(p): h for p, h in generated["input_sha256"].items()}
    for name, h in generated["output_sha256"].items():
        if digest(layout / name) != h:
            raise ValueError("Generated physical view changed")
        pins[layout / name] = h
    for p in [
        Path(__file__).resolve(),
        app,
        layout / "result.json",
        pdk / "libs.ref/sg13g2_stdcell/lef/sg13g2_tech.lef",
        *[
            root / "hw/soc/flow" / name
            for name in [
                "make_pcie_pad_boundary.py",
                "check_pcie_rx_cell.py",
                "check_ihp_drc.py",
                "audit_klayout_lvs.py",
                "prepare_ihp_drc.py",
            ]
        ],
    ]:
        pins[p] = digest(p)
    for typ in ("drc", "lvs"):
        p = root / f"hw/soc/pnr/ihp-{typ}.lock.json"
        lock = json.loads(p.read_text())
        validate_lock(lock)
        if lock["commit"] != REV:
            raise ValueError("Native deck revision differs")
        pins[p] = digest(p)
        for row in lock["files"]:
            p = root / f"hw/soc/tools/ihp-{typ}-5e6d592" / row["path"]
            verify(p.read_bytes(), row)
            pins[p] = row["sha256"]
    if any(digest(p) != h for p, h in pins.items()):
        raise ValueError("Input changed before native checks")
    if (layout / "schematic.cir").read_text() != reference():
        raise ValueError("Unchanged literal reference required")
    out.mkdir(parents=True)
    record = dict(
        status="RUNNING",
        inputs={str(p): h for p, h in pins.items()},
        steps=[],
        main_chip_integrated=False,
        esd_qualified=False,
        qualified_pex=False,
    )

    def save():
        (out / "result.json").write_text(json.dumps(record, indent=2) + "\n")

    try:
        for name in (
            "drc",
            "offgrid",
            "lvs",
            "multiplicity",
            "wrong_polarity",
            "wrong_rail",
            "pad_short",
            "pad_open",
        ):
            d = out / name
            d.mkdir()
            step = dict(name=name)
            record["steps"].append(step)
            save()
            gds = layout / (TOP + ".gds")
            net = layout / "schematic.cir"
            if name in ("offgrid", "pad_short", "pad_open"):
                gds = d / "wrong.gds"
                script = d / "mutate.py"
                script.write_text(mutation_script(layout / (TOP + ".gds"), gds, name))
                step["mutation"] = execute([app, "python", script], d, "mutation")
                if step["mutation"]["returncode"] != 0 or digest(gds) == digest(
                    layout / (TOP + ".gds")
                ):
                    raise ValueError("Specific physical mutation failed")
            elif name not in ("drc", "lvs"):
                net = d / "wrong.cir"
                net.write_text(
                    fault_reference(
                        net.read_text()
                        if net.exists()
                        else (layout / "schematic.cir").read_text(),
                        name,
                    )
                )
            if name in ("drc", "offgrid"):
                entry = (
                    root
                    / "hw/soc/tools/ihp-drc-5e6d592/ihp-sg13g2/libs.tech/klayout/tech/drc/ihp-sg13g2.drc"
                )
                opts = dict(
                    input=gds,
                    topcell=TOP,
                    report=d / "drc.lyrdb",
                    log=d / "deck.log",
                    threads=2,
                    run_mode="deep",
                    no_recommended="False",
                    precheck_drc="False",
                )
            else:
                entry = (
                    root
                    / "hw/soc/tools/ihp-lvs-5e6d592/ihp-sg13g2/libs.tech/klayout/tech/lvs/sg13g2.lvs"
                )
                opts = dict(
                    input=gds,
                    schematic=net,
                    topcell=TOP,
                    report=d / "result.lvsdb",
                    log=d / "deck.log",
                    target_netlist=d / "extracted.cir",
                    run_mode="flat",
                    thr=2,
                )
            cmd = [app, "klayout", "-b", "-zz", "-r", entry]
            for k, v in opts.items():
                cmd += ["-rd", f"{k}={v}"]
            step["execution"] = execute(cmd, d, "run")
            if step["execution"]["returncode"] != 0:
                raise ValueError("Native deck failed to complete")
            if name in ("drc", "offgrid"):
                step["measurement"] = record_result(d, TOP, 0, pins)
                m = step["measurement"]
                step["status"] = m["status"]
                if (
                    m.get("category_count") != 560
                    or "KLayout DRC run for tables 'main' completed"
                    not in (d / "run.log").read_text()
                ):
                    raise ValueError("Incomplete native main DRC")
                if name == "drc" and m["status"] != "PASS":
                    raise ValueError("Pad main DRC failed")
                if name == "offgrid" and (
                    m["status"] != "FAIL"
                    or m["categories"].get("metal1_drw_Offgrid", 0) <= 0
                ):
                    raise ValueError("Specific physical offgrid fault not rejected")
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
                    if (
                        step["audit_execution"]["returncode"] != 0
                        or audit["status"] != "PASS within comparison scope"
                        or audit["circuits"]
                        != [
                            dict(
                                layout=TOP,
                                schematic=TOP.upper(),
                                status="Match",
                                layout_devices_recursive=4,
                                schematic_devices_recursive=4,
                            )
                        ]
                    ):
                        raise ValueError("Strict four-device pad LVS did not pass")
                elif name == "pad_open":
                    validate_open(
                        audit,
                        step["audit_execution"]["returncode"],
                        (d / "extracted.cir").read_text(),
                    )
                elif (
                    step["audit_execution"]["returncode"] != 1
                    or audit["status"] != "FAIL"
                    or audit["circuit_status_counts"].get("NoMatch", 0) < 1
                ):
                    raise ValueError("Specific native LVS negative not rejected")
            save()
            print(name, step["status"], flush=True)
        inspect = execute(
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
        if inspect["returncode"] != 0:
            raise ValueError("Native source geometry or named terminal checks failed")
        record["native_geometry_execution"] = inspect
        record["native_geometry"] = json.loads(
            (out / "native-geometry.json").read_text()
        )
        for negative in (False, True):
            d = out / ("lef_missing_pin" if negative else "lef")
            d.mkdir()
            lef = layout / (TOP + ".lef")
            if negative:
                s, n = re.subn(
                    r"  PIN PADP\n.*?  END PADP\n", "", lef.read_text(), flags=re.S
                )
                if n != 1:
                    raise ValueError("Specific missing LEF port mutation failed")
                lef = d / "wrong.lef"
                lef.write_text(s)
            script = d / "inspect.tcl"
            script.write_text(lef_script(pdk, lef, generated))
            rec = execute([app, "openroad", "-exit", script], d, "native")
            text = (d / "native.log").read_text()
            banner = "PASS_NATIVE_PAD_LEF_FOUR_NETS_SIX_ACCESSES_NO_RF_APPROVAL"
            if negative:
                if (
                    rec["returncode"] == 0
                    or banner in text
                    or len(
                        re.findall(
                            r"^Error: inspect\.tcl, \d+ Pad terminal census changed$",
                            text,
                            re.M,
                        )
                    )
                    != 1
                ):
                    raise ValueError("Wrong native LEF negative outcome")
            elif (
                rec["returncode"] != 0
                or text.count(banner) != 1
                or re.search(r"^Error:|\[ERROR", text, re.M)
            ):
                raise ValueError("Native pad LEF failed")
            record["steps"].append(
                dict(
                    name=d.name,
                    execution=rec,
                    status="EXPECTED_REJECTION" if negative else "PASS",
                )
            )
            save()
        if any(digest(p) != h for p, h in pins.items()):
            raise ValueError("Native input changed during checks")
        record["status"] = (
            "PASS_PAD_BOUNDARY_MAIN_DRC_STRICT_LVS_AND_SEVEN_NEGATIVES_NO_ESD_RF_APPROVAL"
        )
        record["output_sha256"] = {
            str(p.relative_to(out)): digest(p)
            for p in sorted(out.rglob("*"))
            if p.is_file() and p != out / "result.json"
        }
        save()
    except BaseException as exc:
        record.update(status="FAILED_OR_INCOMPLETE", error=repr(exc))
        save()
        raise


if __name__ == "__main__":
    main()
