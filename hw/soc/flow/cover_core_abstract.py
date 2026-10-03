#!/usr/bin/env python3
# SPDX-FileCopyrightText: 2026 Hasan Melih Akbulut
# SPDX-License-Identifier: Apache-2.0
"""Cover actual SG13G2 hard-core conductors in a compact routing abstract.

Run with a Python containing klayout.db. Both drawing and filler purposes are
read from the selected PDK layer map. Missing GDS purposes are empty, not an
excuse to omit purposes present in the map. Lower metals are blocked over the
whole die; upper-metal missing polygons get conservative bounding rectangles.
Pins and all metadata outside OBS remain unchanged. This is geometry coverage,
not electrical connectivity, routing clearance, density, DRC, LVS or timing.
"""
import argparse
import json
import re
import xml.etree.ElementTree as ET
from pathlib import Path

from compact_core_abstract import LOWER, UPPER, digest, inspect


def require(condition, message):
    if not condition:
        raise ValueError(message)


def layer_map(path):
    result = {}
    for prop in ET.parse(path).getroot().iter("properties"):
        name = prop.findtext("name", "")
        if name not in {f"{layer}.{purpose}" for layer in LOWER | UPPER
                        for purpose in ("drawing", "filler")}:
            continue
        require(name not in result, f"Repeated PDK layer {name}")
        result[name] = tuple(map(int, prop.findtext("source").split("/")[:2]))
    require(len(result) == 14, "Incomplete drawing/filler layer map")
    return result


def regions(db, text, dbu):
    pins = {name: db.Region() for name in UPPER}
    obs = {name: db.Region() for name in LOWER | UPPER}
    in_obs, in_pin, layer = False, False, None
    for line in text.splitlines():
        words = line.split()
        if not words:
            continue
        if words[0] == "PIN":
            in_pin, layer = True, None
        elif words == ["OBS"]:
            in_obs, layer = True, None
        elif words[0] == "END" and len(words) > 1:
            in_pin, layer = False, None
        elif words == ["END"] and in_obs:
            in_obs, layer = False, None
        elif words[0] == "LAYER":
            layer = words[1]
        elif words[0] == "RECT" and (in_obs or in_pin):
            require(len(words) == 6 and words[-1] == ";", "Unsupported RECT")
            values = list(map(float, words[1:5]))
            coords = [round(x / dbu) for x in values]
            require(all(abs(x / dbu - y) < 1e-5 for x, y in zip(values, coords)),
                    "LEF coordinate is off the selected GDS grid")
            if in_obs:
                require(layer in obs, "Unsupported OBS layer")
                obs[layer].insert(db.Box(*coords))
            elif layer in pins:
                pins[layer].insert(db.Box(*coords))
    return pins, obs


def cover(source, gds, lyp, output):
    import klayout.db as db

    source, gds, lyp, output = map(Path, (source, gds, lyp, output))
    require(not output.exists(), "Choose a fresh output")
    inputs = {str(p.resolve()): digest(p) for p in (source, gds, lyp)}
    before = inspect(source)
    require(all(before["counts"][name] == 1 for name in LOWER),
            "Run compact_core_abstract.py first")
    text = source.read_text()
    macros = re.findall(r"^MACRO\s+(\S+)\s*$", text, re.M)
    sizes = re.findall(r"^\s*SIZE ([0-9.]+) BY ([0-9.]+) ;\s*$", text, re.M)
    require(len(macros) == len(sizes) == 1, "Expected one sized hard macro")
    width, height = map(float, sizes[0])
    require(width > 0 and height > 0, "Invalid die dimensions")
    layout = db.Layout()
    layout.read(str(gds))
    require(len(layout.top_cells()) == 1, "Expected one GDS top cell")
    top, dbu = layout.top_cell(), layout.dbu
    require(top.name == macros[0], "GDS/LEF macro identities disagree")
    mapping = layer_map(lyp)
    die = db.Box(0, 0, round(width / dbu), round(height / dbu))
    require(abs(width / dbu - die.right) < 1e-5
            and abs(height / dbu - die.top) < 1e-5, "Off-grid die")
    # Hierarchical bboxes avoid flattening millions of SRAM polygons.
    for name in LOWER:
        for purpose in ("drawing", "filler"):
            li = layout.find_layer(*mapping[f"{name}.{purpose}"])
            box = top.bbox(li) if li is not None else db.Box()
            require(box.empty() or (box & die) == box,
                    f"{name}.{purpose} extends outside macro die")
    pins, obs = regions(db, text, dbu)
    additions, stats, metal = {}, {}, {}
    for name in sorted(UPPER):
        purposes = {}
        for purpose in ("drawing", "filler"):
            li = layout.find_layer(*mapping[f"{name}.{purpose}"])
            purposes[purpose] = (db.Region(top.begin_shapes_rec(li))
                                 if li is not None else db.Region())
        metal[name] = (purposes["drawing"] + purposes["filler"]).merged()
        require((pins[name] - metal[name]).is_empty(),
                f"{name} pin has no backing in selected GDS")
        missing = metal[name] - (pins[name] + obs[name])
        additions[name] = [polygon.bbox() for polygon in missing.each()]
        stats[name] = dict(drawing_polygons=purposes["drawing"].count(),
                           filler_polygons=purposes["filler"].count(),
                           missing_before_um2=missing.area() * dbu ** 2,
                           added_rectangles=len(additions[name]))
    lines, in_obs, layer = [], False, None

    def finish_layer():
        for box in additions.get(layer, []):
            lines.append("    RECT " + " ".join(f"{v * dbu:.9f}" for v in
                         (box.left, box.bottom, box.right, box.top)) + " ;\n")

    for line in text.splitlines(keepends=True):
        words = line.split()
        if words == ["OBS"]:
            in_obs = True
        elif in_obs and words and words[0] == "LAYER":
            finish_layer()
            layer = words[1]
        elif in_obs and words == ["END"]:
            finish_layer()
            in_obs, layer = False, None
        elif in_obs and layer in LOWER and words and words[0] == "RECT":
            box = before["bounds"][layer]
            envelope = (min(0, box[0]), min(0, box[1]),
                        max(width, box[2]), max(height, box[3]))
            line = "    RECT " + " ".join(f"{x:.9f}" for x in envelope) + " ;\n"
        lines.append(line)
    result_text = "".join(lines)
    outpins, outobs = regions(db, result_text, dbu)
    for name in LOWER | UPPER:
        require((obs[name] - outobs[name]).is_empty(), "Original obstruction lost")
    for name in UPPER:
        require((pins[name] ^ outpins[name]).is_empty(), "Pin geometry changed")
        require((metal[name] - (outpins[name] + outobs[name])).is_empty(),
                "Selected GDS conductors remain uncovered")
        stats[name]["missing_after_um2"] = 0.0
    require(all(digest(p) == h for p, h in inputs.items()), "Input changed")
    with output.open("x") as stream:
        stream.write(result_text)
    require(inspect(output)["outside_sha256"] == before["outside_sha256"],
            "Pin, via or macro metadata changed")
    return dict(status="PASS_SELECTED_GDS_CONDUCTOR_COVERAGE_ONLY",
                input_sha256=inputs, output_sha256=digest(output), layers=stats,
                lower_metal_full_die_envelope_verified=True,
                layer_map={k: list(v) for k, v in mapping.items()},
                physical_connectivity_accepted=False, timing_accepted=False,
                manufacturing_approval=False)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ("source", "gds", "lyp", "output"):
        parser.add_argument(name, type=Path)
    parser.add_argument("--receipt", type=Path, required=True)
    args = parser.parse_args()
    require(not args.receipt.exists(), "Choose a fresh receipt")
    result = cover(args.source, args.gds, args.lyp, args.output)
    args.receipt.write_text(json.dumps(result, indent=2) + "\n")
    print(result["status"])


if __name__ == "__main__":
    main()
