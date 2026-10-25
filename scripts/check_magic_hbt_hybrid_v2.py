#!/usr/bin/env python3
# SPDX-FileCopyrightText: 2026 Hasan Melih Akbulut
# SPDX-License-Identifier: Apache-2.0
"""Exact isolated 24-HBT device/wire bridge, not RF-qualified PEX.

The native LVS schematic retains every HBT and the finite physical ptap. Only
Metal1/Via1/Metal2 are copied into the wire-only GDS. Two explicit probes within
each real terminal pin establish the RC reference planes. This is not a model
of distributed intrinsic terminals, substrate spreading, or metal/device
coupling. Source mask geometry and native device parameters are never fitted.
"""

import argparse
import hashlib
import importlib.util
import json
import math
from pathlib import Path
import re
import sys

ROOT = Path(__file__).resolve().parents[1]
DEPENDENCIES = {
    "scripts/check_magic_coupled_cap_v2.py": "ab7aa8e59fe601772b4235fca7b63f708cab381245061dcb26f98d1f85209782",
    "hw/soc/flow/audit_klayout_lvs.py": "bcfc03cf993de873193fd55f80edb903ab9b3730198a1c374667671a67508568",
}
RUNTIME_PINS = ("47cec16ee2466f36c7ab277b006a7c50ed073ad79d5f9b805bd6643b02b976b9",
                "948bb9eb8b90a39ab96947983ade749e74ea871c5b63715b0a87d6e15653279c")


def require(value, message):
    if not value:
        raise ValueError(message)


def pin(path):
    path = Path(path)
    return {"bytes": path.stat().st_size, "sha256": hashlib.sha256(path.read_bytes()).hexdigest()}


def load(name, relative):
    path = ROOT / relative
    if DEPENDENCIES.get(relative):
        require(pin(path)["sha256"] == DEPENDENCIES[relative], "Frozen dependency changed")
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def lines(path):
    """SPICE continuations are syntax, not independent elements."""
    result = []
    for line in Path(path).read_text().splitlines():
        if not line.strip() or line.lstrip().startswith("*"):
            continue
        if line.startswith("+"):
            require(bool(result), "Orphan continuation")
            result[-1] += " " + line[1:].strip()
        else:
            result.append(line.strip())
    return result


def stable_ext(data):
    """Sort only the native hash-table cap records; retain every token/record."""
    rows = data.splitlines()
    return "\n".join([r for r in rows if not r.startswith("cap ")] + sorted(r for r in rows if r.startswith("cap "))) + "\n"


def devices(path):
    rows = [line.split() for line in lines(path)]
    require(len(rows) == 27 and rows[0][0].lower() == ".subckt" and rows[-1][0].lower() == ".ends", "Need exactly 25 extracted devices")
    expected = {f"{terminal}_N{nx}_T{orientation}" for nx in (1, 2, 4) for orientation in range(8) for terminal in "CBE"} | {"SUB"}
    require(len(rows[0][2:]) == 73 and set(rows[0][2:]) == expected, "Exact 73-port census changed")
    hbts, taps = {}, []
    bodies = set()
    for row in rows[1:-1]:
        if row[0].startswith("Q"):
            require(len(row) == 10 and row[5] == "npn13G2", "Wrong HBT model/arity")
            match = re.fullmatch(r"C_(N([124])_T([0-7]))", row[1])
            require(match is not None, "Unknown native collector")
            tag, nx = match[1], int(match[2])
            require(tag not in hbts and row[2:4] == ["B_" + tag, "E_" + tag], "Missing/merged/reordered native HBT terminal")
            require(dict(token.split("=") for token in row[6:]) == {"we": "70n", "le": "900n", "Nx": str(nx), "m": "1"}, "Native emitter dimensions/multiplicity changed")
            hbts[tag] = row
            bodies.add(row[4])
        else:
            require(row[0].startswith("R") and len(row) == 6 and row[3:] == ["ptap1", "A=4p", "P=8u"], "Missing/changed physical tap")
            taps.append(row)
    require(len(hbts) == 24 and len(taps) == 1 and len(bodies) == 1, "Exact HBT/tap/body census changed")
    body = next(iter(bodies))
    require(body not in expected and taps[0][1:3] == ["SUB", body], "Tap must connect external SUB to distinct native body")
    return {"ports": rows[0][2:], "rows": rows[1:-1], "body": body, "hbts": hbts, "tap": taps[0]}


def geometry(gds, fixture, report, deck_log, extracted, output):
    import klayout.db as db

    require(not output.exists(), "Output must be fresh")
    output.mkdir(parents=True)
    audit = load("native_lvs", "hw/soc/flow/audit_klayout_lvs.py")
    diagnostics = []
    verdict = audit.assess(audit.read_pairs(report, diagnostics), "nssoc_hbt_axis", deck_log.read_text(), diagnostics)
    require(verdict["status"] == "PASS within comparison scope", "Native complete LVS failed")
    native = devices(extracted)
    database = db.LayoutVsSchematic()
    database.read(str(report))
    circuit = database.netlist().circuit_by_name("nssoc_hbt_axis")
    require(circuit is not None and circuit.pin_count() == 73, "Native database port census changed")
    database_rows = []
    for device in circuit.each_device():
        kind = device.device_class()
        terminals = {t.name: device.net_for_terminal(t.id()).name for t in kind.terminal_definitions()}
        parameters = {p.name: device.parameter(p.id()) for p in kind.parameter_definitions()}
        if kind.name == "npn13G2":
            tag = terminals["C"][2:]
            require(tag in native["hbts"], "Database/export device mismatch")
            row = native["hbts"][tag]
            require([terminals[n] for n in ("C", "B", "E", "S")] == [n.removeprefix("\\") for n in row[1:5]], "Database/export terminal mismatch")
            require(parameters == {"we": .07, "le": .9, "Nx": float(tag[1]), "m": 1.0}, "Database/export parameter mismatch")
        else:
            require(kind.name == "ptap1" and terminals == {"TIE": "SUB", "WELL": native["body"].removeprefix("\\")}
                    and parameters == {"A": 4.0, "P": 8.0}, "Database/export tap mismatch")
        database_rows.append({"model": kind.name, "terminals": terminals, "parameters": parameters})
    require(len(database_rows) == 25, "Native database device census changed")
    record = json.loads(fixture.read_text())
    require(set(record["ports"]) == set(native["ports"]), "Fixture/native ports differ")
    layout = db.Layout()
    layout.read(str(gds))
    require(layout.dbu == .001, "Unexpected native grid")
    top = layout.cell("nssoc_hbt_axis")
    require(top is not None, "Wrong GDS top")
    wire = db.Layout()
    wire.dbu = layout.dbu
    wire_top = wire.create_cell("hbt_wires")
    regions = {}
    for layer in (8, 19, 10):
        region = db.Region(top.begin_shapes_rec(layout.layer(layer, 0))).merged()
        require(not region.is_empty(), "Missing actual metal/via layer")
        regions[layer] = region
        wire_top.shapes(wire.layer(layer, 0)).insert(region)
        require((region ^ db.Region(wire_top.begin_shapes_rec(wire.layer(layer, 0)))).is_empty(), "Copied wire geometry differs")
    extractor = db.LayoutToNetlist("WIRE", layout.dbu)
    for layer, region in regions.items():
        extractor.register(region, "gds_" + str(layer))
        extractor.connect(region)
    extractor.connect(regions[8], regions[19])
    extractor.connect(regions[19], regions[10])
    extractor.extract_netlist()
    mapping = {}
    for name in native["ports"]:
        port = record["ports"][name]
        layer = port["layer"]
        require(layer in (8, 10), "Wrong terminal metal")
        box = db.DBox(*port["box"]).to_itype(layout.dbu)
        # Verify the actual GDS top pin rectangle, not merely supplied JSON.
        actual = db.Region(top.shapes(layout.layer(layer, 2)))
        require((db.Region(box) - actual).is_empty(), "Missing source pin rectangle")
        texts = [s.text for s in top.each_shape(layout.layer(layer, 25)) if s.is_text() and s.text.string == name]
        require(len(texts) == 1 and box.contains(texts[0].trans.disp), "Missing/moved source pin label")
        center = box.center()
        points = ([[box.left + 50, center.y], [box.right - 50, center.y]] if box.width() > box.height()
                  else [[center.x, box.bottom + 50], [center.x, box.top - 50]])
        nets = [extractor.probe_net(regions[layer], db.Point(*xy)) for xy in points]
        require(points[0] != points[1] and all(net is not None for net in nets), "Missing or coincident wire anchor")
        require(nets[0].cluster_id == nets[1].cluster_id, "Open physical terminal conductor")
        mapping[name] = {"layer": layer, "anchors_dbu": points, "cluster": nets[0].cluster_id}
    require(len({row["cluster"] for row in mapping.values()}) == 73, "Shorted native terminal conductors")
    require(sum(1 for _ in extractor.netlist().circuit_by_name("WIRE").each_net()) == 73, "Unmapped metal/via component")
    wire.write(str(output / "wires.gds"))
    extractor.write(str(output / "wires.l2n"))
    result = {"status": "PASS_NATIVE_DEVICE_AND_WIRE_GEOMETRY_BINDING_ONLY", "mapping": mapping,
              "native_devices": native, "database_devices": database_rows, "lvs": verdict, "method": pin(__file__),
              "inputs": {str(p): pin(p) for p in (gds, fixture, report, deck_log, extracted)},
              "outputs": {p.name: pin(p) for p in output.iterdir() if p.is_file()},
              "qualified_pex": False}
    (output / "geometry.json").write_text(json.dumps(result, indent=2) + "\n")
    return result


def wire_tcl(mapping, gds, output):
    require(len(mapping) == 73, "Incomplete wire mapping")
    result = ['puts "NSSOC_LOADED_NATIVE_LIBRARIES [info loaded]"', f"cd {{{output}}}", "drc off",
              f"gds read {{{gds}}}", "load hbt_wires", "select top cell"]
    for index, (name, row) in enumerate(mapping.items()):
        require(re.fullmatch(r"(?:[CBE]_N[124]_T[0-7]|SUB)", name), "Unsafe/wrong terminal name")
        for endpoint, (label, xy) in enumerate(zip((name, "D_" + name), row["anchors_dbu"])):
            x, y = [v * .001 for v in xy]
            result += [f"box values {x}um {y}um {x}um {y}um", f"label {label} center metal{ {8: 1, 10: 2}[row['layer']]}",
                       f"port {label} make {2 * index + endpoint + 1}", f"port {label} class inout", f"port {label} use signal"]
    result += ["save hbt_wires", "extract style ngspice()", "extract all", "ext2sim labels on", "ext2sim",
               "extresist threshold 0", "extresist tolerance 0.000001", "extresist simplify off", "extresist all",
               "ext2spice lvs", "ext2spice global off", "ext2spice cthresh 0", "ext2spice rthresh 0",
               "ext2spice extresist on", "ext2spice -o wires.spice", "quit -noprompt"]
    return "\n".join(result) + "\n"


def bridge(geometry_path, native_dir, baseline_dir, output):
    require(not output.exists(), "Output must be fresh")
    record = json.loads(geometry_path.read_text())
    require(record["method"] == pin(__file__), "Geometry method pin changed")
    for name, expected in record["inputs"].items():
        require(pin(name) == expected, "Geometry input changed")
    for name, expected in record["outputs"].items():
        require(pin(geometry_path.parent / name) == expected, "Geometry output changed")
    mapping, native = record["mapping"], record["native_devices"]
    require(len(mapping) == 73 and set(mapping) == set(native["ports"]), "Incomplete bridge")
    for folder, runtime_sha in zip((native_dir, baseline_dir), RUNTIME_PINS):
        require((folder / "native.tcl").read_text() == wire_tcl(mapping, geometry_path.parent / "wires.gds", folder), "Native command/deck changed")
        run = json.loads((folder / "run.json").read_text())
        require(run["runtime"]["sha256"] == runtime_sha and run["execution"]["returncode"] == 0
                and run["execution"]["memory_limit_bytes"] == 2147483648, "Wrong/failed native runtime")
        require(run["producer"] == pin(__file__) and run["geometry"] == pin(geometry_path)
                and run["gds"] == pin(geometry_path.parent / "wires.gds"), "Native source/geometry closure failed")
        require(set(run["outputs"]) == {"wires.spice", "hbt_wires.res.ext", "hbt_wires.nodes", "hbt_wires.sim",
                                       "hbt_wires.ext", "hbt_wires.mag", "native.log", "native.tcl"}, "Native output closure failed")
        for name, expected_pin in run["outputs"].items():
            require(pin(folder / name) == expected_pin, "Native output pin changed")
        command = run["execution"]["command"]
        require(len(command) == 9 and command[:1] == ["/usr/bin/env"] and command[1].startswith("CAD_ROOT=")
                and command[2] == "/usr/bin/tclsh8.6" and command[4:7] == ["-dnull", "-noconsole", "-rcfile"]
                and command[-1] == str(folder / "native.tcl"), "Unexpected native launch")
        runtime = Path(command[1].removeprefix("CAD_ROOT="))
        require(command[3] == str(runtime / "magic/tcl/magic.tcl") and pin(runtime / "magic/tcl/tclmagic.so")["sha256"] == runtime_sha,
                "Native launcher/library binding failed")
        require(f"NSSOC_LOADED_NATIVE_LIBRARIES {{{runtime}/magic/tcl/tclmagic.so Tclmagic}}" in (folder / "native.log").read_text(),
                "Native loaded-library witness missing")
        technology = Path(command[7]).parent
        require(set(run["technology"]) == {p.name for p in technology.iterdir() if p.is_file()}, "Technology inventory changed")
        for name, expected_pin in run["technology"].items():
            require(pin(technology / name) == expected_pin, "Technology input changed")
    output.mkdir(parents=True)
    normalized = []
    stable = []
    for index, folder in enumerate((native_dir, baseline_dir)):
        path = output / f"normalized-{index}.spice"
        path.write_text("\n".join(lines(folder / "wires.spice")) + "\n")
        normalized.append(path)
        path = output / f"stable-cap-order-{index}.ext"
        path.write_text(stable_ext((folder / "hbt_wires.ext").read_text()))
        stable.append(path)
    auditor = load("frozen_coupled", "scripts/check_magic_coupled_cap_v2.py")
    rc = auditor.audit(stable[0], native_dir / "hbt_wires.res.ext", normalized[0], native_dir / "native.log", stable[1], normalized[1])
    wire_rows = [line.split() for line in lines(normalized[0])]
    expected = set(native["ports"]) | {"D_" + name for name in native["ports"]}
    require(set(wire_rows[0][2:]) == expected and len(wire_rows[0][2:]) == 146, "Wire port census changed")
    resistors = [row for row in wire_rows[1:-1] if row[0].startswith("R")]
    require(len(resistors) == 73 and {frozenset(row[1:3]) for row in resistors} == {frozenset((name, "D_" + name)) for name in mapping}, "Wire resistance graph does not contract one-to-one")
    require(all(math.isfinite(float(row[3])) and float(row[3]) > 0 for row in resistors), "Invalid native wire resistance")
    # Preserve native model/parameter tokens verbatim. The output is an extracted
    # schematic, not a claimed simulator-ready foundry-model adapter.
    merged = ["* Native extracted device schematic plus separately audited metal/via RC.", ".subckt hbt_hybrid " + " ".join(native["ports"])]
    reconstructed = []
    for row in native["rows"]:
        limit = 5 if row[0].startswith("Q") else 3
        copy = list(row)
        for index in range(1, limit):
            if copy[index] in mapping:
                copy[index] = "D_" + copy[index]
        merged.append(" ".join(copy))
        reconstructed.append([token[2:] if index in range(1, limit) and token.startswith("D_") else token for index, token in enumerate(copy)])
    require(reconstructed == native["rows"], "Device graph/parameter preservation failed")
    for row in wire_rows[1:-1]:
        require(len(row) == 4 and row[0][0] in "RC", "Unexpected wire element")
        copy = [row[0][0] + "WIRE_" + row[0][1:], *row[1:]]
        copy[1:3] = [native["body"] if node == "sub" else node for node in copy[1:3]]
        merged.append(" ".join(copy))
    merged.append(".ends hbt_hybrid")
    (output / "hybrid.cir").write_text("\n".join(merged) + "\n")
    (output / "rc-audit.json").write_text(json.dumps(rc, indent=2) + "\n")
    result = {"status": "PASS_ISOLATED_24_HBT_73_PORT_DEVICE_WIRE_BRIDGE_ONLY", "hbts": 24, "tap_devices": 1,
              "ports": 73, "wire_endpoints": 146, "wire_resistors": 73, "matrix_dimension": 73,
              "native_body": native["body"], "finite_tap_preserved": True, "exact_device_graph_contraction": True,
              "geometry": pin(geometry_path), "method": pin(__file__), "inputs": {str(p): pin(p) for folder in (native_dir, baseline_dir) for p in folder.iterdir() if p.is_file()},
              "outputs": {p.name: pin(p) for p in output.iterdir() if p.is_file()}, "qualified_pex": False,
              "limitations": ["Wire-only Metal1/Via1/Metal2 technology RC at explicit terminal reference planes.",
                              "No intrinsic-terminal spreading, device/wire coupling, substrate spreading, RF or full-bank qualification.",
                              "Native LVS Q/R device syntax retained; no claim of simulator-ready foundry model translation."]}
    (output / "result.json").write_text(json.dumps(result, indent=2) + "\n")
    return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest="mode", required=True)
    geo = sub.add_parser("geometry")
    for name in ("gds", "fixture", "report", "deck-log", "extracted", "output"):
        geo.add_argument("--" + name, type=Path, required=True)
    tcl = sub.add_parser("tcl")
    tcl.add_argument("geometry", type=Path)
    tcl.add_argument("output", type=Path)
    audit = sub.add_parser("audit")
    for name in ("geometry", "native-dir", "baseline-dir", "output"):
        audit.add_argument("--" + name, type=Path, required=True)
    args = parser.parse_args()
    if args.mode == "geometry":
        result = geometry(args.gds, args.fixture, args.report, args.deck_log, args.extracted, args.output)
    elif args.mode == "tcl":
        value = json.loads(args.geometry.read_text())
        require(not args.output.exists(), "Output directory must be new")
        args.output.mkdir(parents=True)
        (args.output / "native.tcl").write_text(wire_tcl(value["mapping"], args.geometry.parent / "wires.gds", args.output))
        result = {"status": "TCL_WRITTEN_NATIVE_RUN_REQUIRED"}
    else:
        result = bridge(args.geometry, args.native_dir, args.baseline_dir, args.output)
    print(result["status"])


if __name__ == "__main__":
    try:
        main()
    except (ValueError, OSError) as error:
        print(str(error), file=sys.stderr)
        raise SystemExit(2)
