#!/usr/bin/env python3
# SPDX-FileCopyrightText: 2026 Hasan Melih Akbulut
# SPDX-License-Identifier: Apache-2.0
"""Conservatively compact lower-metal LEF obstructions, retaining upper metal.

Pin and via definitions remain byte-identical. Lower-metal obstacles become
their enclosing rectangle; TopMetal1/2 obstacles remain byte-identical. This
does not change GDS or certify routing, electrical connectivity or signoff.
"""
import argparse
import hashlib
import json
import math
from pathlib import Path

LOWER = frozenset(f"Metal{i}" for i in range(1, 6))
UPPER = frozenset(("TopMetal1", "TopMetal2"))


def digest(path):
    with Path(path).open("rb") as stream:
        return hashlib.file_digest(stream, "sha256").hexdigest()


def inspect(path):
    bounds, counts, hashes = {}, {}, {}
    in_obs, layer, sections = False, None, 0
    outside = hashlib.sha256()
    with Path(path).open() as stream:
        for line in stream:
            words = line.split()
            if words == ["OBS"]:
                if in_obs or sections:
                    raise ValueError("Expected exactly one macro OBS section")
                in_obs, sections = True, sections + 1
                continue
            if not in_obs:
                outside.update(line.encode())
                continue
            if words == ["END"]:
                in_obs, layer = False, None
                continue
            if not words:
                continue
            if len(words) == 3 and words[0] == "LAYER" and words[2] == ";":
                layer = words[1]
                if layer not in LOWER | UPPER or layer in counts:
                    raise ValueError("Unsupported or repeated obstruction layer")
                counts[layer], hashes[layer] = 0, hashlib.sha256()
                hashes[layer].update(line.encode())
                continue
            if (layer is None or len(words) != 6 or words[0] != "RECT"
                    or words[-1] != ";"):
                raise ValueError("Unsupported obstruction syntax")
            box = list(map(float, words[1:5]))
            if (not all(math.isfinite(x) for x in box)
                    or box[2] <= box[0] or box[3] <= box[1]):
                raise ValueError("Invalid obstruction rectangle")
            old = bounds.get(layer, box)
            bounds[layer] = [min(old[0], box[0]), min(old[1], box[1]),
                             max(old[2], box[2]), max(old[3], box[3])]
            counts[layer] += 1
            hashes[layer].update(line.encode())
    if in_obs or sections != 1 or set(counts) != LOWER | UPPER or not all(counts.values()):
        raise ValueError("Incomplete routing-layer obstruction inventory")
    return dict(bounds=bounds, counts=counts, outside_sha256=outside.hexdigest(),
                layer_sha256={k: h.hexdigest() for k, h in hashes.items()})


def verify(source, candidate):
    before, after = inspect(source), inspect(candidate)
    if before["outside_sha256"] != after["outside_sha256"]:
        raise ValueError("Pin, via or macro metadata changed")
    for layer in UPPER:
        if before["layer_sha256"][layer] != after["layer_sha256"][layer]:
            raise ValueError("Upper-metal obstacles changed")
    for layer in LOWER:
        a, b = before["bounds"][layer], after["bounds"][layer]
        if after["counts"][layer] != 1 or any(
                (b[i] > a[i] if i < 2 else b[i] < a[i]) for i in range(4)):
            raise ValueError("Lower-metal envelope does not cover the source")
    return before, after


def compact(source, output):
    source, output = Path(source), Path(output)
    initial_hash = digest(source)
    data = inspect(source)
    in_obs, layer = False, None
    with source.open() as stream, output.open("x") as target:
        for line in stream:
            words = line.split()
            if words == ["OBS"]:
                in_obs = True
            elif in_obs and words == ["END"]:
                in_obs, layer = False, None
            elif in_obs and words and words[0] == "LAYER":
                layer = words[1]
                target.write(line)
                if layer in LOWER:
                    # Native export uses decimal micron coordinates. Nine digits
                    # after the point preserve its nanometre-grid envelopes.
                    target.write("    RECT " + " ".join(
                        f"{x:.9f}" for x in data["bounds"][layer]) + " ;\n")
                continue
            elif in_obs and layer in LOWER and words and words[0] == "RECT":
                continue
            target.write(line)
    before, after = verify(source, output)
    if digest(source) != initial_hash:
        raise ValueError("Source changed during compaction")
    return dict(status="PASS_CONSERVATIVE_LEF_OBSTRUCTION_COMPACTION_ONLY",
                source_sha256=initial_hash, output_sha256=digest(output),
                source=before, output=after, physical_connectivity_accepted=False,
                timing_accepted=False, manufacturing_approval=False)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("source", type=Path)
    parser.add_argument("output", type=Path)
    parser.add_argument("--receipt", type=Path, required=True)
    args = parser.parse_args()
    if args.output.exists() or args.receipt.exists():
        parser.error("Choose new output and receipt paths")
    result = compact(args.source, args.output)
    args.receipt.write_text(json.dumps(result, indent=2) + "\n")
    print(result["status"])


if __name__ == "__main__":
    main()
