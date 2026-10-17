#!/usr/bin/env python3
# SPDX-FileCopyrightText: 2026 Hasan Melih Akbulut
# SPDX-License-Identifier: Apache-2.0
"""Exercise actual hierarchical GDS abstraction using positive and fault fixtures.

Run with the LibreLane AppImage's Python (klayout.db), passing a fresh directory.
This checks the abstraction method, not the product's physical correctness.
"""
import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "hw/soc/flow"))
from compact_core_abstract import digest  # noqa: E402
from cover_core_abstract import cover, regions  # noqa: E402


def run(output):
    import klayout.db as db

    output.mkdir(exist_ok=False, parents=True)
    layers = ["Metal1", "Metal2", "Metal3", "Metal4", "Metal5",
              "TopMetal1", "TopMetal2"]
    cases = ["prefill", "filled", "wrong_top", "unsupported_map",
             "missing_map", "missing_pin_metal", "lower_outside", "off_grid"]
    results = []
    for case in cases:
        path = output / case
        path.mkdir()
        layout = db.Layout()
        layout.dbu = 0.001
        top = layout.create_cell("wrong" if case == "wrong_top" else "core")
        child = layout.create_cell("child")
        top.insert(db.CellInstArray(child.cell_index(), db.Trans()))
        props = []
        for index, name in enumerate(layers, 1):
            for purpose, datatype in (("drawing", 0), ("filler", 22)):
                if case == "missing_map" and name == "Metal1" and datatype == 22:
                    continue
                props.append(f"<properties><name>{name}.{purpose}</name>"
                             f"<source>{index}/{datatype}@1</source></properties>")
            if case != "missing_pin_metal" or name != "TopMetal1":
                top.shapes(layout.layer(index, 0)).insert(db.Box(1000, 1000, 2000, 2000))
            if name.startswith("Top"):
                child.shapes(layout.layer(index, 0)).insert(db.Box(3000, 3000, 4000, 4000))
                if case == "filled":
                    child.shapes(layout.layer(index, 22)).insert(db.Box(5000, 5000, 6000, 6000))
        if case == "lower_outside":
            child.shapes(layout.layer(1, 22)).insert(db.Box(-1000, 0, 0, 1000))
        lyp = "<layer-properties>" + "".join(props) + "</layer-properties>"
        # Real LYP sources use 'layer/datatype@view'. A malformed source must fail.
        lyp = lyp.replace("@1", "")
        if case == "unsupported_map":
            lyp = lyp.replace("1/0", "invalid/0", 1)
        (path / "layers.lyp").write_text(lyp)
        lef = "MACRO core\n  SIZE 20 BY 20 ;\n"
        for name in layers[-2:]:
            lef += (f"  PIN {name}\n    PORT\n      LAYER {name} ;\n"
                    f"      RECT 1 1 2 2 ;\n    END\n  END {name}\n")
        lef += "  OBS\n" + "".join(
            f"    LAYER {name} ;\n    RECT 1 1 2 2 ;\n" for name in layers)
        lef += "  END\nEND core\n"
        if case == "off_grid":
            lef = lef.replace("RECT 1 1", "RECT 1.0005 1", 1)
        (path / "source.lef").write_text(lef)
        layout.write(str(path / "core.gds"))
        try:
            receipt = cover(path / "source.lef", path / "core.gds",
                            path / "layers.lyp", path / "output.lef")
            if case not in ("prefill", "filled"):
                raise AssertionError(f"Fault accepted: {case}")
            pins, obs = regions(db, (path / "output.lef").read_text(), 0.001)
            for name in layers[-2:]:
                expected = db.Region(db.Box(3000, 3000, 4000, 4000))
                if case == "filled":
                    expected.insert(db.Box(5000, 5000, 6000, 6000))
                    assert receipt["layers"][name]["filler_polygons"] == 1
                assert (expected - obs[name]).is_empty()
                assert pins[name].area() == 1000000
            for name in layers[:5]:
                assert obs[name].bbox() == db.Box(0, 0, 20000, 20000)
            result = dict(case=case, status="PASS", receipt=receipt)
        except ValueError as error:
            if case in ("prefill", "filled"):
                raise
            assert not (path / "output.lef").exists()
            result = dict(case=case, status="EXPECTED_REJECTION", error=str(error))
        results.append(result)
    receipt = dict(status="PASS_TWO_HIERARCHICAL_GDS_AND_SIX_FAULT_CONTROLS",
                   results=results, manufacturing_approval=False,
                   source_sha256={str(p.relative_to(ROOT)): digest(p) for p in
                                  [Path(__file__), ROOT / "hw/soc/flow/cover_core_abstract.py",
                                   ROOT / "hw/soc/flow/compact_core_abstract.py"]})
    (output / "result.json").write_text(json.dumps(receipt, indent=2) + "\n")
    print(receipt["status"])


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("output", type=Path)
    run(parser.parse_args().output)
