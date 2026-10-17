#!/usr/bin/env python3
# SPDX-FileCopyrightText: 2026 Hasan Melih Akbulut
# SPDX-License-Identifier: Apache-2.0
"""Probe input-pad rail continuity through the native seven-metal stack.

No labels or virtual joins. Child-circuit IDs cannot establish cross-instance
connectivity. This audit excludes transistor/substrate LVS and RC qualification.
"""

import argparse
from datetime import datetime
import hashlib
import json
from pathlib import Path
import re
import resource
import time

GDS_SHA256 = "a5c79c3920154af5a523e3a1224402d6e863b9f7dd91c367ac6256d9045ad8ff"
LEF_SHA256 = "8b3dc3960960c08e07a1cde3dd9cd0484f5b12df07c4628726fff551bb775c0c"


def sha(p):
    with Path(p).open("rb") as f:
        return hashlib.file_digest(f, "sha256").hexdigest()


def net(n, region, point):
    value = n.probe_net(region, point)
    if value is None:
        raise ValueError("No physical conductor at probe")
    return (value.circuit().name, value.cluster_id)


def supply_errors(rails, top="nssoc_chip"):
    """Accept only four distinct, single, top-level physical supply nets."""
    errors = []
    if set(rails) != {"iovss", "iovdd", "vdd", "vss"}:
        errors.append("Missing or unexpected supply rail")
    if not all(n[0] == top for ids in rails.values() for n in ids):
        errors.append(
            "Unresolved child-circuit probes cannot prove cross-instance continuity"
        )
    for pin, ids in rails.items():
        if len(ids) != 1:
            errors.append(f"{pin} has {len(ids)} distinct probe identities")
    if len(set().union(*rails.values())) != sum(len(v) for v in rails.values()):
        errors.append("Different supply pins share a physical cluster")
    return errors


def controls(db):
    rows = []
    for connected in [True, False]:
        layout = db.Layout()
        layout.dbu = 0.001
        top = layout.create_cell("TOP")
        child = layout.create_cell("COLUMN")
        metals = [layout.layer(n, 0) for n in [8, 10, 30, 50, 67, 126, 134]]
        vias = [layout.layer(n, 0) for n in [19, 29, 49, 66, 125, 133]]
        for layer in metals:
            child.shapes(layer).insert(db.Box(0, 0, 20, 20))
        for layer in vias:
            child.shapes(layer).insert(db.Box(5, 5, 15, 15))
        for x in [0, 80]:
            top.insert(db.CellInstArray(child.cell_index(), db.Trans(x, 0)))
        if connected:
            top.shapes(metals[0]).insert(db.Box(0, 0, 100, 20))
        l = db.LayoutToNetlist(db.RecursiveShapeIterator(layout, top, []))
        m = [l.make_polygon_layer(i, "m" + str(j)) for j, i in enumerate(metals)]
        v = [l.make_polygon_layer(i, "v" + str(j)) for j, i in enumerate(vias)]
        for region in m + v:
            l.connect(region)
        for i, region in enumerate(v):
            l.connect(m[i], region)
            l.connect(region, m[i + 1])
        l.extract_netlist()
        nets = []
        for x in [10, 90]:
            n = l.probe_net(m[-1], db.Point(x, 10))
            assert n is not None
            nets.append(
                dict(
                    circuit=n.circuit().name,
                    cluster=n.cluster_id,
                    expanded_name=n.expanded_name(),
                )
            )
        equal = all(n["circuit"] == "TOP" for n in nets) and nets[0] == nets[1]
        assert equal == connected, (connected, nets)
        rows.append(dict(parent_bridge=connected, probe_nets=nets))
    return rows


def validate_native(deck):
    files = [
        deck / n
        for n in [
            "layers_definitions.lvs",
            "general_derivations.lvs",
            "general_connections.lvs",
            "cap_derivations.lvs",
        ]
    ]
    layers, derived, connects, caps = [p.read_text() for p in files]
    for name, num in zip(
        ["metal1", "metal2", "metal3", "metal4", "metal5", "topmetal1", "topmetal2"],
        [8, 10, 30, 50, 67, 126, 134],
    ):
        for suffix, dt in [("drw", 0), ("filler", 22), ("slit", 24), ("res", 29)]:
            assert re.search(
                name
                + "_"
                + suffix
                + r"\s*= get_polygons\("
                + str(num)
                + ", "
                + str(dt)
                + r"\)",
                layers,
            )
        assert f"{name} = {name}_drw.join({name}_filler).not({name}_slit)" in layers
        assert re.search(
            name
            + r"_con\s*= "
            + name
            + r"\.not\("
            + name
            + r"_res\)"
            + (r"\.not\(ind_drw\)" if name.startswith("top") else ""),
            derived,
        )
    names = ["metal1", "metal2", "metal3", "metal4", "metal5", "topmetal1", "topmetal2"]
    for i, (name, num) in enumerate(
        zip(
            ["via1", "via2", "via3", "via4", "topvia1", "topvia2"],
            [19, 29, 49, 66, 125, 133],
        )
    ):
        assert re.search(
            name + r"_drw\s*= get_polygons\(" + str(num) + r", 0\)", layers
        )
        via = name + "_n_cap" if name == "topvia1" else name + "_drw"
        assert (
            f"connect({names[i]}_con, {via})" in connects
            and f"connect({via}, {names[i + 1]}_con)" in connects
        )
    assert (
        "topvia1_n_cap = topvia1_drw.not(mim_via)" in caps
        and "mim_via = vmim_drw.join(topvia1_drw).and(mim_drw)" in caps
    )
    assert re.search(r"mim_drw\s*= get_polygons\(36, 0\)", layers)
    return files


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--gds", type=Path)
    parser.add_argument("--lef", type=Path)
    parser.add_argument("--references", type=Path)
    parser.add_argument("--output", required=True, type=Path)
    parser.add_argument("--controls-only", action="store_true")
    args = parser.parse_args()
    if not args.controls_only and not all([args.gds, args.lef, args.references]):
        parser.error("GDS, LEF and native references are required")
    args.output.mkdir(parents=True, exist_ok=False)
    record = dict(
        status="PREPARING",
        method_sha256=sha(Path(__file__).resolve()),
        full_chip_lvs_accepted=False,
        timing_accepted=False,
        manufacturing_approval=False,
    )
    started = time.monotonic()

    def save():
        record.update(
            recorded=datetime.now().astimezone().isoformat(),
            elapsed_seconds=time.monotonic() - started,
        )
        (args.output / "result.json").write_text(json.dumps(record, indent=2) + "\n")

    save()
    try:
        memory = Path("/proc/meminfo").read_text()
        available = int(re.search(r"MemAvailable:\s+(\d+)", memory)[1]) * 1024
        cap = 1024**3 if args.controls_only else min(12 * 1024**3, available - 1024**3)
        record.update(memory_before=memory, address_space_limit_bytes=cap)
        save()
        if not args.controls_only and cap < 4 * 1024**3:
            raise RuntimeError(
                "Insufficient memory for recovery: require 4 GiB plus 1 GiB reserve"
            )
        resource.setrlimit(resource.RLIMIT_AS, (cap, cap))
        resource.setrlimit(resource.RLIMIT_CORE, (0, 0))
        import klayout.db as db

        record["hierarchical_controls"] = controls(db)
        record["hierarchical_controls_pass"] = True
        if args.controls_only:
            record["status"] = "PASS_HIERARCHICAL_CONTROLS_ONLY"
            save()
            return 0
        gds = args.gds.resolve()
        lef = args.lef.resolve()
        files = validate_native(args.references.resolve())
        pins = {str(p): sha(p) for p in [gds, lef, *files, Path(__file__).resolve()]}
        assert pins[str(gds)] == GDS_SHA256, "Unexpected GDS"
        assert pins[str(lef)] == LEF_SHA256, "Unexpected original IO LEF"
        record.update(status="DERIVING_METALS", input_sha256=pins)
        save()
        layout = db.Layout()
        opt = db.LoadLayoutOptions()
        mapping = db.LayerMap()
        i = 0
        for v in [8, 10, 30, 50, 67, 126, 134]:
            for dt in [0, 22, 24, 29]:
                mapping.map(f"{v}/{dt}", i)
                i += 1
        for v in [19, 29, 49, 66, 125, 133, 27, 36]:
            mapping.map(f"{v}/0", i)
            i += 1
        opt.set_layer_map(mapping, False)
        layout.read(str(gds), opt)
        assert layout.dbu == 0.001
        top = layout.cell("nssoc_chip")
        assert top is not None
        native = db.LayoutToNetlist(db.RecursiveShapeIterator(layout, top, []))
        native.threads = 1
        cache = {}

        def reg(v, dt=0):
            key = (v, dt)
            if key not in cache:
                cache[key] = native.make_polygon_layer(
                    layout.layer(v, dt), f"raw_{v}_{dt}"
                )
            return cache[key]

        metalnums = [8, 10, 30, 50, 67, 126, 134]
        vianums = [19, 29, 49, 66, 125, 133]
        conductors = []
        for v in metalnums:
            region = (reg(v) + reg(v, 22)) - reg(v, 24) - reg(v, 29)
            if v in [126, 134]:
                region -= reg(27)
            conductors.append(region.merged())
            print("METAL", v, conductors[-1].count(), flush=True)
        vias = [(reg(v) - reg(36) if v == 125 else reg(v)).merged() for v in vianums]
        for v, region in zip(metalnums, conductors):
            native.register(region, "metal" + str(v))
            native.connect(region)
        for index, (v, region) in enumerate(zip(vianums, vias)):
            native.register(region, "via" + str(v))
            native.connect(region)
            native.connect(conductors[index], region)
            native.connect(region, conductors[index + 1])
        record.update(status="EXTRACTING_FULL_METAL")
        save()
        print("EXTRACT_FULL_METAL", flush=True)
        native.extract_netlist()
        print("EXTRACTED", flush=True)
        regions = [conductors[-2], vias[-1], conductors[-1]]

        # Required pins are read from the original LEF, never from net names in GDS.
        text = (
            lef.read_text()
            .split("MACRO sg13g2_IOPadIn\n")[1]
            .split("END sg13g2_IOPadIn")[0]
        )
        ports = {}
        for pin in ["iovss", "iovdd", "vdd", "vss"]:
            body = re.search(r"  PIN " + pin + r"\n.*?  END " + pin, text, re.S)[0]
            layer = "TopMetal1" if pin in ["vdd", "vss"] else "TopMetal2"
            rects = re.findall(
                r"LAYER "
                + layer
                + r"\s*;\s*RECT ([0-9.]+) ([0-9.]+) ([0-9.]+) ([0-9.]+)\s*;",
                body,
            )
            assert rects, pin
            ports[pin] = [db.Box(*(round(float(v) * 1000) for v in z)) for z in rects]
        assert len(ports["iovss"]) == 3
        rows = []
        allnets = {k: set() for k in ports}
        for inst in top.each_inst():
            if inst.cell.name != "sg13g2_IOPadIn":
                continue
            for trans in inst.cell_inst.each_cplx_trans():
                row = dict(master=inst.cell.name, transform=str(trans), pins={})
                for pin, boxes in ports.items():
                    probes = []
                    for box in boxes:
                        actual = box.transformed(trans)
                        conductor = regions[0 if pin in ["vdd", "vss"] else 2]
                        assert (db.Region(actual) - conductor).is_empty()
                        point = actual.center()
                        nid = net(native, conductor, point)
                        allnets[pin].add(nid)
                        probes.append(
                            dict(
                                box_dbu=[
                                    actual.left,
                                    actual.bottom,
                                    actual.right,
                                    actual.top,
                                ],
                                physical_cluster=nid,
                            )
                        )
                    row["pins"][pin] = probes
                rows.append(row)
        assert len(rows) == 27, "Unexpected input pad count"
        errors = supply_errors(allnets)
        assert all(sha(Path(p)) == h for p, h in pins.items())
        result = dict(
            status="FAIL_PHYSICAL_SUPPLY_CONNECTION"
            if errors
            else "PASS_INPUT_PAD_METAL_CONTINUITY_ONLY",
            recorded=datetime.now().astimezone().isoformat(),
            input_sha256=pins,
            pad_count=len(rows),
            rails={k: sorted(v) for k, v in allnets.items()},
            errors=errors,
            pads=rows,
            scope="Hierarchical polygon-only extraction of all seven native conducting metal layers and six via layers across the filled chip, with TopVia1 under MIM markers excluded. Native drawing+fill minus slit/resistor/inductor cuts; no labels, virtual joins or abstract net connectivity. Only input-pad power ports are probed. This is a metal continuity/rail-isolation proof, not transistor LVS, DRC, RC/timing or manufacturing acceptance.",
            full_chip_lvs_accepted=False,
            manufacturing_approval=False,
        )
        record.update(result)
        save()
        print(record["status"], record["rails"], flush=True)
        return 1 if errors else 0
    except Exception as error:
        record.update(status="ERROR", error=repr(error))
        save()
        raise


if __name__ == "__main__":
    raise SystemExit(main())
