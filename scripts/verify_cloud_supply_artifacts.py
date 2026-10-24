#!/usr/bin/env python3
# SPDX-FileCopyrightText: 2026 Hasan Melih Akbulut
# SPDX-License-Identifier: Apache-2.0
"""Audit archived cloud tiles without expanding the gigabyte geometry bundle.

This verifies every geometry byte, checkpoint chain and deterministic union.
It does not repeat native extraction or establish transistor LVS or timing.
"""
import argparse
from datetime import datetime
import hashlib
import json
from pathlib import Path, PurePosixPath
import re
import shutil
import stat
import tempfile
import zipfile

import cloud_supply_tiles as tiled


def sha_stream(stream):
    return hashlib.file_digest(stream, "sha256").hexdigest()


def members(archive):
    result = {}
    for item in archive.infolist():
        path = PurePosixPath(item.filename)
        mode = item.external_attr >> 16
        if (not item.filename or path.is_absolute() or ".." in path.parts
                or "\\" in item.filename or str(path) != item.filename
                or item.is_dir() or stat.S_ISLNK(mode)
                or item.filename in result):
            raise ValueError("Unsafe or duplicate artifact member")
        result[item.filename] = item
    return result


def check_index(index, run_id, source_commit, bundle_sha256, attempt):
    if (type(run_id) is not int or run_id <= 0 or type(attempt) is not int or attempt <= 0
            or not re.fullmatch(r"[0-9a-f]{40}", source_commit)
            or not re.fullmatch(r"[0-9a-f]{64}", bundle_sha256)):
        raise ValueError("Explicit run, commit, bundle and attempt required")
    rows = index["artifacts"]
    expected = {"supply-tiles-prepared", f"supply-prepare-debug-attempt-{attempt}",
                f"supply-tiled-final-attempt-{attempt}"}
    expected.update(f"supply-tile-{i}-{bundle_sha256}" for i in range(64))
    if len(rows) != 67 or {r["name"] for r in rows} != expected:
        raise ValueError("Missing, duplicate or unexpected cloud artifacts")
    for row in rows:
        run = row["workflow_run"]
        if (row["expired"] or run["id"] != run_id or run["head_sha"] != source_commit
                or not re.fullmatch(r"sha256:[0-9a-f]{64}", row["digest"])
                or type(row["size_in_bytes"]) is not int or row["size_in_bytes"] <= 0):
            raise ValueError("Wrong artifact run/source/digest identity")
    return {r["name"]: r for r in rows}


def verify_archive(path, row):
    if path.stat().st_size != row["size_in_bytes"]:
        raise ValueError("Artifact archive size mismatch")
    with path.open("rb") as stream:
        if "sha256:" + sha_stream(stream) != row["digest"]:
            raise ValueError("Artifact archive digest mismatch")


def audit(index, directory, run_id, source_commit, bundle_sha256, attempt=1):
    rows = check_index(index, run_id, source_commit, bundle_sha256, attempt)
    directory = Path(directory)
    inventory = {}
    for name, row in rows.items():
        path = directory/(name+".zip")
        verify_archive(path, row)
        with zipfile.ZipFile(path) as archive:
            inventory[name] = {key: dict(bytes=item.file_size, crc32=item.CRC)
                               for key, item in members(archive).items()}
    # Only small metadata and one native checkpoint at a time reach disk.
    with tempfile.TemporaryDirectory(prefix="supply-audit-", dir=directory.parent) as scratch:
        scratch = Path(scratch)
        bundle_dir = scratch/"bundle"
        bundle_dir.mkdir()
        geometry_bytes = 0
        with zipfile.ZipFile(directory/"supply-tiles-prepared.zip") as archive:
            for name in ("bundle.json", "plan.json"):
                (bundle_dir/name).write_bytes(archive.read(name))
            bundle, plan = tiled.validate_bundle(bundle_dir, bundle_sha256)
            if not bundle["production"] or len(bundle["grid"]["tiles"]) != 64:
                raise ValueError("Complete production bundle required")
            expected = {"bundle.json", "plan.json"}
            for tile in bundle["tile_files"].values():
                name = tile["file"]
                prepared = name.removesuffix(".gds")+".prepared.json"
                expected.update((name, prepared))
                info = archive.getinfo(name)
                with archive.open(name) as stream:
                    digest = sha_stream(stream)
                if info.file_size != tile["bytes"] or digest != tile["sha256"]:
                    raise ValueError("Prepared geometry hash/size mismatch")
                if json.loads(archive.read(prepared)) != tile:
                    raise ValueError("Prepared tile receipt differs from bundle")
                if set(tile["geometry"]) != set(tiled.LAYERS):
                    raise ValueError("Incomplete tile layer geometry inventory")
                geometry_bytes += info.file_size
            if set(members(archive)) != expected:
                raise ValueError("Unexpected or missing prepared bundle member")
        results = []
        result_hashes = {}
        for tile_id in range(64):
            name = f"supply-tile-{tile_id}-{bundle_sha256}"
            tile_dir = scratch/"tile"
            tile_dir.mkdir()
            with zipfile.ZipFile(directory/(name+".zip")) as archive:
                contents = members(archive)
                required = {"checkpoint/connectivity.l2n.gz", "checkpoint/prepared.json",
                            "checkpoint/manifest.json", "measurement.json", "extract.log",
                            "measure.log", "verify.log", f"job-attempt-{attempt}.json"}
                if set(contents) != required:
                    raise ValueError("Incomplete or unexpected fresh-run tile inventory")
                for member in contents:
                    destination = tile_dir/member
                    destination.parent.mkdir(parents=True, exist_ok=True)
                    with archive.open(member) as source, destination.open("xb") as target:
                        shutil.copyfileobj(source, target, length=1024*1024)
            result = json.loads((tile_dir/"measurement.json").read_text())
            if result["tile_id"] != tile_id:
                raise ValueError("Tile artifact contains another tile")
            job = json.loads((tile_dir/f"job-attempt-{attempt}.json").read_text())
            if (job["run_id"] != str(run_id) or job["attempt"] != str(attempt)
                    or job["commit"] != source_commit or job["tile"] != tile_id
                    or job["bundle_sha256"] != bundle_sha256):
                raise ValueError("Wrong tile producer job identity")
            tiled.validate_result_chain(tile_dir, result, bundle, bundle_sha256)
            result_hashes[name] = tiled.sha(tile_dir/"measurement.json")
            results.append(result)
            shutil.rmtree(tile_dir)
        expected = tiled.combine(bundle, bundle_sha256, plan, results)
        with zipfile.ZipFile(directory/f"supply-tiled-final-attempt-{attempt}.zip") as archive:
            cloud = json.loads(archive.read("final.json"))
            if "PASS_ALL_DECLARED_IO_SUPPLY_WINDOWS_TILED_ONLY" not in archive.read("aggregate.log").decode():
                raise ValueError("Native aggregate log has no success marker")
        for key, value in expected.items():
            # JSON arrays canonically represent Python tuples in union results.
            if cloud[key] != json.loads(json.dumps(value)):
                raise ValueError("Independent recombination differs: "+key)
        if (cloud["bundle_sha256"] != bundle_sha256 or cloud["methods"] != bundle["methods"]
                or cloud["plan_sha256"] != bundle["plan_sha256"]
                or cloud["source_gds_sha256"] != bundle["source_gds_sha256"]
                or cloud["production"] is not True):
            raise ValueError("Aggregate provenance differs")
        bindings = cloud["result_sha256"]
        if (len(bindings) != 64
                or any(PurePosixPath(p).name != "measurement.json" for p in bindings)
                or {PurePosixPath(p).parent.name: h for p, h in bindings.items()} != result_hashes):
            raise ValueError("Aggregate measurement digest inventory differs")
        if expected["errors"] or expected["bad_window_indices"]:
            raise ValueError("Production supply audit did not pass")
    return dict(status="PASS_ARCHIVES_GEOMETRY_CHECKPOINT_CHAINS_AND_RECOMBINATION_ONLY",
                recorded=datetime.now().astimezone().isoformat(), run_id=run_id,
                source_commit=source_commit, bundle_sha256=bundle_sha256,
                source_gds_sha256=bundle["source_gds_sha256"], plan_sha256=bundle["plan_sha256"],
                artifacts_verified=len(rows), geometry_bytes_streamed=geometry_bytes,
                geometry_files=64, native_checkpoint_chains=64,
                checked_windows=expected["checked_windows"], io_instances=expected["io_instances"],
                seams=expected["seams"], seam_witnesses=expected["seam_witnesses"],
                rails=expected["rails"], errors=[], independently_recombined=True,
                archive_inventory=inventory, measurement_sha256=result_hashes,
                native_extraction_repeated_locally=False,
                scope="Every archived geometry byte and checkpoint chain verified; same native measurements independently recombined. Declared IO-window metal connectivity only.",
                full_chip_lvs_accepted=False, timing_accepted=False, manufacturing_approval=False)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--index", type=Path, required=True)
    parser.add_argument("--directory", type=Path, required=True)
    parser.add_argument("--run-id", type=int, required=True)
    parser.add_argument("--source-commit", required=True)
    parser.add_argument("--bundle-sha256", required=True)
    parser.add_argument("--attempt", type=int, default=1)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    if args.output.exists():
        parser.error("Output must be fresh")
    result = audit(json.loads(args.index.read_text()), args.directory, args.run_id,
                   args.source_commit, args.bundle_sha256, args.attempt)
    tiled.write_new(args.output, result)
    print(result["status"])


if __name__ == "__main__":
    main()
