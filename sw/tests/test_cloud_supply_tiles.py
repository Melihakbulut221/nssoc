# SPDX-FileCopyrightText: 2026 Hasan Melih Akbulut
# SPDX-License-Identifier: Apache-2.0
"""Coverage, immutable publication and negative contracts without native tools."""
import copy
import importlib.util
import json
from pathlib import Path
import sys

import pytest

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT/"scripts"))
import cloud_supply_tiles as tiled  # noqa: E402


def test_grid_covers_all_faces_and_corners():
    grid = tiled.tile_grid([0, 0, 800, 800], 8, 8)
    assert len(grid["tiles"]) == 64
    assert len(grid["seams"]) == 112+98
    assert {tuple(s["tiles"]) for s in grid["seams"]} == {
        (a, b) for a in range(64) for b in range(a+1, 64)
        if abs(a%8-b%8) <= 1 and abs(a//8-b//8) <= 1}
    assert sum((t["core"][2]-t["core"][0])*(t["core"][3]-t["core"][1])
               for t in grid["tiles"]) == 800*800
    tiled.validate_grid(grid)


@pytest.mark.parametrize("field", ["missing_tile", "duplicate_tile", "missing_diagonal", "core_gap", "halo"])
def test_reject_incomplete_partition(field):
    grid = tiled.tile_grid([-7, 8, 794, 813], 8, 8)
    if field == "missing_tile":
        grid["tiles"].pop()
    elif field == "duplicate_tile":
        grid["tiles"][1] = grid["tiles"][0]
    elif field == "missing_diagonal":
        grid["seams"] = [s for s in grid["seams"] if s["tiles"] != [0, 9]]
    elif field == "core_gap":
        grid["tiles"][0]["core"][2] -= 1
    else:
        grid["halo_dbu"] = 1
    with pytest.raises(ValueError):
        tiled.validate_grid(grid)


def test_window_spanning_four_tiles_is_not_dropped_or_clipped_to_centre():
    grid = tiled.tile_grid([0, 0, 200, 200], 2, 2)
    plan = {"windows": [{"box_nm": [90, 90, 110, 110], "gds_layer": 8}]}
    pieces = [q for i in range(4) for q in tiled.queries(grid, i, plan) if q["kind"] == "window"]
    assert len(pieces) == 4
    assert sum((q["box_dbu"][2]-q["box_dbu"][0])*(q["box_dbu"][3]-q["box_dbu"][1])
               for q in pieces) == 400
    for i in range(4):
        seams = [q for q in tiled.queries(grid, i, plan) if q["kind"] == "seam"]
        assert len(seams) == 3*13
        assert set(q["layer"] for q in seams) == set(tiled.LAYERS)


def test_atomic_publication_refuses_overwrite(tmp_path):
    path = tmp_path/"receipt.json"
    tiled.write_new(path, {"status": "ORIGINAL"})
    with pytest.raises(FileExistsError):
        tiled.write_new(path, {"status": "REPLACED"})
    assert json.loads(path.read_text()) == {"status": "ORIGINAL"}
    assert list(tmp_path.iterdir()) == [path]


def test_failed_serialization_does_not_publish_partial_json(tmp_path):
    with pytest.raises(TypeError):
        tiled.write_new(tmp_path/"receipt.json", {"not_json": object()})
    assert list(tmp_path.iterdir()) == []


@pytest.mark.parametrize("args", [([0, 0, 2, 2], 2, 2), ([0, 0, 100, 100], 0, 2),
                                ([0, 0, 100, 100], 17, 2), ([0, 0, 0, 100], 2, 2)])
def test_reject_invalid_grid(args):
    with pytest.raises(ValueError):
        tiled.tile_grid(*args)


def test_disconnected_same_cluster_numbers_in_different_tiles_are_not_joined():
    grid = tiled.tile_grid([0, 0, 200, 100], 2, 1)
    windows = [{"pin": pin, "gds_layer": 8, "box_nm": [x, y, x+10, y+10]}
               for y, pin in enumerate(tiled.SUPPLIES) for x in (0, 190)]
    plan = {"windows": windows, "io_instances": 2}
    manifest = dict(grid=grid, methods={}, plan_sha256="plan")
    results = []
    for tile in grid["tiles"]:
        rows = []
        for q in tiled.queries(grid, tile["id"], plan):
            samples = []
            if q["kind"] == "window":
                samples = [dict(circuit="TOP", cluster=q["index"]//2, point_um=[0, 0])]
            rows.append(dict(query=q, geometry_sha256="empty" if not samples else "piece", samples=samples))
        results.append(dict(status="VERIFIED_TILE_MEASUREMENTS_ONLY", tile_id=tile["id"],
                            bundle_sha256="bundle", plan_sha256="plan", methods={}, measurements=rows))
    result = tiled.combine(manifest, "bundle", plan, results)
    assert len(result["errors"]) == 4
    assert all(len(identities) == 2 for identities in result["rails"].values())
    broken = copy.deepcopy(results)
    broken[0]["measurements"].pop()
    with pytest.raises(ValueError, match="coverage"):
        tiled.combine(manifest, "bundle", plan, broken)


def test_production_pins_match_immutable_queue_contract():
    # These are identity constants, not mutable local queue reads.
    assert tiled.GDS_SHA256 == "a5c79c3920154af5a523e3a1224402d6e863b9f7dd91c367ac6256d9045ad8ff"
    assert tiled.PLAN_SHA256 == "340047aaf8cdc30d00d4af3489759187d1a78366846f2030238d62d32136a109"
    assert len(tiled.LAYERS) == 13
    assert importlib.util.find_spec("cloud_supply_tiles") is not None
