#!/usr/bin/env python3
# SPDX-FileCopyrightText: 2026 Hasan Melih Akbulut
# SPDX-License-Identifier: Apache-2.0
"""Probe every conductor piece in a supply window using the original netlist.

The caller must supply the registered conductor layer from a physical extractor
with the correct native layer derivations. This helper does not extract a chip,
identify intended supply names or establish transistor/substrate LVS.
"""

import argparse
from datetime import datetime
import hashlib
import json
from pathlib import Path


def probe_window(db, extractor, conductor, window, dbu, top):
    """Do not replace a port containing separate islands with one centre probe."""
    if dbu <= 0 or not top:
        raise ValueError("Positive database unit and explicit top circuit required")
    clipped = (conductor & db.Region(window)).merged()
    samples = []
    for polygon in clipped.each():
        # Trapezoids are convex and hole-free, so their vertex mean is interior.
        # Query the ORIGINAL registered conductor, not the clipped region: a
        # connection outside this window must remain part of the measured net.
        for piece in polygon.decompose_trapezoids():
            vertices = list(piece.each_point())
            if piece.area() <= 0:
                raise ValueError("Degenerate conductor decomposition")
            point = db.DPoint(
                sum(p.x for p in vertices) * dbu / len(vertices),
                sum(p.y for p in vertices) * dbu / len(vertices),
            )
            if not piece.to_dtype(dbu).inside(point):
                raise ValueError("Probe witness is outside its conductor piece")
            net = extractor.probe_net(conductor, point)
            samples.append(
                dict(
                    point_um=[point.x, point.y],
                    circuit=None if net is None else net.circuit().name,
                    cluster=None if net is None else net.cluster_id,
                )
            )
    identities = {(s["circuit"], s["cluster"]) for s in samples}
    errors = []
    if not samples:
        errors.append("No conductor in required port window")
    if any(s["circuit"] != top for s in samples):
        errors.append(
            "Missing or child-local identity; cross-instance continuity unresolved"
        )
    if len(identities) != 1:
        errors.append("Port window resolves to multiple or zero physical identities")
    return dict(
        status="PASS_SINGLE_TOP_NET_WINDOW_ONLY"
        if not errors
        else "UNRESOLVED_OR_FAILED_WINDOW",
        samples=samples,
        identities=sorted(identities, key=str),
        errors=errors,
        full_chip_lvs_accepted=False,
        manufacturing_approval=False,
    )


def self_test(db):
    results = {}

    def flat(name, conductor, box, expected):
        l = db.LayoutToNetlist("TOP", 0.001)
        l.register(conductor, "metal")
        l.connect(conductor)
        l.extract_netlist()
        result = probe_window(db, l, conductor, box, 0.001, "TOP")
        assert (not result["errors"]) == expected, (name, result)
        results[name] = result
        return result

    ring = db.Region(db.Box(0, 0, 100, 100)) - db.Region(db.Box(20, 20, 80, 80))
    result = flat("hole_at_window_centre", ring, db.Box(0, 0, 100, 100), True)
    assert len(result["samples"]) >= 4
    assert all(
        not (0.020 < x < 0.080 and 0.020 < y < 0.080)
        for x, y in (s["point_um"] for s in result["samples"])
    )
    split = db.Region(db.Box(0, 0, 20, 20)) + db.Region(db.Box(80, 0, 100, 20))
    result = flat("disconnected_islands", split, db.Box(0, 0, 100, 20), False)
    assert len(result["identities"]) == 2
    # Connection exists above the queried window; local clipping loses it.
    bridge = (
        db.Region(db.Box(0, 0, 20, 60))
        + db.Region(db.Box(80, 0, 100, 60))
        + db.Region(db.Box(0, 40, 100, 60))
    )
    result = flat("connection_outside_window", bridge, db.Box(0, 0, 100, 20), True)
    assert len(result["samples"]) == 2 and len(result["identities"]) == 1
    flat(
        "empty_required_port",
        db.Region(db.Box(200, 200, 220, 220)),
        db.Box(0, 0, 20, 20),
        False,
    )
    flat(
        "one_dbu_wide_conductor",
        db.Region(db.Box(0, 0, 1, 10)),
        db.Box(0, 0, 1, 10),
        True,
    )
    # Identical floating child IDs must never masquerade as a parent connection.
    layout = db.Layout()
    layout.dbu = 0.001
    top = layout.create_cell("TOP")
    child = layout.create_cell("CHILD")
    li = layout.layer(8, 0)
    child.shapes(li).insert(db.Box(0, 0, 20, 20))
    for x in [0, 80]:
        top.insert(db.CellInstArray(child.cell_index(), db.Trans(x, 0)))
    l = db.LayoutToNetlist(db.RecursiveShapeIterator(layout, top, []))
    metal = l.make_polygon_layer(li, "metal")
    l.connect(metal)
    l.extract_netlist()
    result = probe_window(db, l, metal, db.Box(0, 0, 100, 20), 0.001, "TOP")
    assert result["errors"] and len(result["samples"]) == 2
    assert all(s["circuit"] == "CHILD" for s in result["samples"])
    results["floating_child_alias"] = result
    return results


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--self-test-output", required=True, type=Path)
    args = parser.parse_args()
    if args.self_test_output.exists():
        parser.error("Output must be new")
    import klayout.db as db

    result = dict(
        status="PASS_COMPONENT_PROBE_CONTROLS_ONLY",
        recorded=datetime.now().astimezone().isoformat(),
        controls=self_test(db),
        method_sha256=hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
        klayout_version=db.__version__,
        chip_connectivity_accepted=False,
        full_chip_lvs_accepted=False,
        manufacturing_approval=False,
    )
    args.self_test_output.parent.mkdir(parents=True, exist_ok=True)
    with args.self_test_output.open("x") as f:
        f.write(json.dumps(result, indent=2) + "\n")
    print(result["status"], len(result["controls"]))


if __name__ == "__main__":
    main()
