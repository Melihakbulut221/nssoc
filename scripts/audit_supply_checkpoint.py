#!/usr/bin/env python3
# SPDX-FileCopyrightText: 2026 Hasan Melih Akbulut
# SPDX-License-Identifier: Apache-2.0
"""Audit every declared IO supply window against a pinned physical checkpoint.

A passing result covers the supplied, independently verified window inventory.
It is not full-chip transistor/substrate LVS, RC or manufacturing acceptance.
"""

import argparse
from collections import Counter
import json
from pathlib import Path

from check_chip_supply_connectivity import sha, supply_errors
from plan_chip_supply_probes import LAYERS, SUPPLIES
from probe_supply_components import probe_window
from supply_checkpoint import load


def validate_plan(plan, manifest):
    if plan["status"] != "PASS_IO_PORT_WINDOW_COVERAGE_ONLY":
        raise ValueError("Unverified window inventory")
    gds = {h for p, h in plan["input_sha256"].items() if Path(p).suffix == ".gds"}
    checkpoint_gds = {
        h for p, h in manifest["input_sha256"].items() if Path(p).suffix == ".gds"
    }
    if len(gds) != 1 or not gds <= checkpoint_gds:
        raise ValueError("Window plan and checkpoint must bind the same GDS")
    if manifest["dbu"] != 0.001 or not manifest.get("floating_subcircuits_retained"):
        raise ValueError(
            "Nanometre database units and floating hierarchy retention required"
        )
    windows = plan["windows"]
    if not windows or len(windows) != plan["port_windows"]:
        raise ValueError("Incomplete window inventory")
    instances = {}
    for w in windows:
        if w["pin"] not in SUPPLIES or LAYERS.get(w["layer"]) != w["gds_layer"]:
            raise ValueError("Unknown supply or layer mapping")
        b = w["box_nm"]
        if (
            len(b) != 4
            or any(type(x) is not int for x in b)
            or b[0] >= b[2]
            or b[1] >= b[3]
        ):
            raise ValueError("Invalid window rectangle")
        if w["instance"] in instances and instances[w["instance"]] != w["master"]:
            raise ValueError("Instance master changed within inventory")
        instances[w["instance"]] = w["master"]
    if (
        len(instances) != plan["io_instances"]
        or Counter(instances.values()) != plan["io_masters"]
        or Counter(w["pin"] for w in windows) != plan["windows_by_rail"]
        or Counter(w["layer"] for w in windows) != plan["windows_by_layer"]
        or set(plan["windows_by_rail"]) != set(SUPPLIES)
    ):
        raise ValueError("Window inventory coverage counters disagree")


def audit(db, extractor, manifest, plan):
    validate_plan(plan, manifest)
    rows = []
    rails = {pin: set() for pin in SUPPLIES}
    bad_windows = []
    for index, w in enumerate(plan["windows"]):
        layer = extractor.layer_by_name("metal" + str(w["gds_layer"]))
        if layer is None:
            raise ValueError("Checkpoint missing native conductor layer " + w["layer"])
        result = probe_window(
            db, extractor, layer, db.Box(*w["box_nm"]), 0.001, manifest["top"]
        )
        rails[w["pin"]].update(tuple(x) for x in result["identities"])
        if result["errors"]:
            bad_windows.append(index)
        rows.append(dict(window=w, measurement=result))
    errors = supply_errors(rails, top=manifest["top"])
    if bad_windows:
        errors.append(f"{len(bad_windows)} supply windows unresolved or failed")
    return dict(
        status="PASS_ALL_DECLARED_IO_SUPPLY_WINDOWS_ONLY"
        if not errors
        else "FAIL_OR_UNRESOLVED_IO_SUPPLY_WINDOWS",
        io_instances=plan["io_instances"],
        checked_windows=len(rows),
        rails={k: sorted(v, key=str) for k, v in rails.items()},
        errors=errors,
        bad_window_indices=bad_windows,
        windows=rows,
        full_chip_lvs_accepted=False,
        manufacturing_approval=False,
    )


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--checkpoint", required=True, type=Path)
    parser.add_argument("--manifest-sha256", required=True)
    parser.add_argument("--plan", required=True, type=Path)
    parser.add_argument("--plan-sha256", required=True)
    parser.add_argument("--output", required=True, type=Path)
    args = parser.parse_args()
    if args.output.exists():
        parser.error("Output must be new")
    args.output.parent.mkdir(parents=True, exist_ok=True)
    record = dict(
        status="PREPARING", full_chip_lvs_accepted=False, manufacturing_approval=False
    )

    def write():
        args.output.write_text(json.dumps(record, indent=2) + "\n")

    write()
    try:
        if sha(args.plan) != args.plan_sha256:
            raise ValueError("Plan hash mismatch")
        import klayout.db as db

        extractor, manifest = load(db, args.checkpoint, args.manifest_sha256)
        plan = json.loads(args.plan.read_text())
        record.update(audit(db, extractor, manifest, plan))
        if (
            sha(args.plan) != args.plan_sha256
            or sha(args.checkpoint / "manifest.json") != args.manifest_sha256
        ):
            raise ValueError("Input changed during audit")
        record.update(
            plan_sha256=args.plan_sha256,
            checkpoint_manifest_sha256=args.manifest_sha256,
            database_sha256=manifest["database_sha256"],
            scope=__doc__,
            method_sha256=sha(Path(__file__)),
        )
        write()
        return 1 if record["errors"] else 0
    except Exception as error:
        record.update(status="ERROR", error=repr(error))
        write()
        raise


if __name__ == "__main__":
    raise SystemExit(main())
