#!/usr/bin/env python3
# SPDX-FileCopyrightText: 2026 Hasan Melih Akbulut
# SPDX-License-Identifier: Apache-2.0
"""Run one hash-bound native chip check on an independent worker.

No elapsed-time watchdog. Hosted worker limits still apply. Failure markers
are retained; this program does not accept density, LVS or timing by proxy.
"""
import argparse
import hashlib
import json
from pathlib import Path, PurePosixPath
import resource
import re
import subprocess
import sys
import tarfile
import time

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "hw/soc/flow"))
from check_ihp_drc import digest, record_result
from check_ihp_drc_partitioned import check_catalog, read_categories
from check_ihp_density_coverage import validate_density_coverage
from bootstrap_flow import verify as verify_tool
from fetch_evidence_assets import fetch, validate, verify

BASE_GROUPS = ("antenna", "feol_devices", "geometry_pin_forbidden", "geometry_grid",
          "geometry_angle", "beol", "supplemental_wide")
GROUPS = (*BASE_GROUPS, "density")


def validate_deck_dependencies(bundle, config):
    """Check native includes and runtime parameter files before costly extraction."""
    bundle = bundle.resolve()
    checked = set()
    def visit(path):
        path = path.resolve()
        if not path.is_relative_to(bundle) or not path.is_file():
            raise ValueError("Missing or escaping native dependency: " + str(path))
        if path in checked:
            return
        checked.add(path)
        source = path.read_text()
        for relative in re.findall(r"^# %include ([^\n]+)$", source, re.M):
            visit(path.parent / relative.strip())
        for relative in re.findall(r"File\.join\(script_dir, '([^']+\.json)'\)", source):
            dependency = (path.parent / relative).resolve()
            if not dependency.is_relative_to(bundle) or not dependency.is_file():
                raise ValueError("Missing or escaping native parameter file: " + str(dependency))
            values = json.loads(dependency.read_text())
            if not isinstance(values.get("drc_rules"), dict) or not values["drc_rules"]:
                raise ValueError("Missing native rule parameters")
            checked.add(dependency)
    for command in config["commands"].values():
        deck = command[command.index("-r") + 1]
        if not deck.startswith("@ROOT@/"):
            raise ValueError("Native deck must be inside the verified bundle")
        visit(bundle / deck[len("@ROOT@/"):])
    return len(checked)


def restore(archive, output):
    """Extract only regular, inventoried files, checking bytes before publication."""
    output.mkdir(exist_ok=False)
    with tarfile.open(archive) as tar:
        members = tar.getmembers()
        names = [m.name for m in members]
        if len(names) != len(set(names)):
            raise ValueError("Duplicate archive member")
        for member in members:
            name = PurePosixPath(member.name)
            if (not member.isfile() or name.is_absolute() or ".." in name.parts
                    or "\\" in member.name or str(name) != member.name):
                raise ValueError("Unsafe archive member")
        inventory = json.load(tar.extractfile("inventory.json"))
        if set(names) != set(inventory) | {"inventory.json"}:
            raise ValueError("Archive inventory does not cover every member")
        for member in members:
            if member.name == "inventory.json":
                continue
            row = inventory[member.name]
            if member.size != row["bytes"]:
                raise ValueError("Wrong member size")
            destination = output / member.name
            destination.parent.mkdir(parents=True, exist_ok=True)
            hasher = hashlib.sha256()
            with tar.extractfile(member) as source, destination.open("xb") as target:
                while chunk := source.read(1024 * 1024):
                    hasher.update(chunk)
                    target.write(chunk)
            if hasher.hexdigest() != row["sha256"]:
                raise ValueError("Wrong member hash")
    return inventory


def validate_config(config):
    if (set(config["commands"]) not in (set(BASE_GROUPS), set(GROUPS))
            or set(config["catalogs"]) != set(BASE_GROUPS)):
        raise ValueError("Missing or unexpected shard")
    if "density" in config["commands"]:
        command = config["commands"]["density"]
        options = [command[i + 1] for i, value in enumerate(command) if value == "-rd"]
        required = {"input=@GDS@", "topcell=nssoc_chip", "report=@REPORT@",
                    "threads=1", "run_mode=deep", "precheck_drc=False",
                    "no_recommended=False", "density_sanity=True"}
        if (len(command) != 4 + 2 * len(required)
                or command[4::2] != ["-rd"] * len(required)
                or len(options) != len(required) or set(options) != required
                or command[:4] != ["-b", "-zz", "-r",
                    "@ROOT@/hw/soc/tools/ihp-drc-5e6d592/ihp-sg13g2/libs.tech/klayout/tech/drc/rule_decks/density.drc"]):
            raise ValueError("Density requires the complete native deep-mode command")
    feol = {}
    for name in GROUPS[1:5]:
        cats = config["catalogs"][name]
        if feol.keys() & cats.keys():
            raise ValueError("Overlapping FEOL categories")
        feol.update(cats)
    check_catalog("feol_and_geometry", feol)
    check_catalog("beol", config["catalogs"]["beol"])
    for name, count in [("antenna", 31), ("supplemental_wide", 11)]:
        if len(config["catalogs"][name]) != count:
            raise ValueError("Incomplete auxiliary catalog")
    if config["top"] != "nssoc_chip" or config["gds"] != "input/chip.gds":
        raise ValueError("Unexpected chip identity")


def shard_coverage(group, config, output, returncode):
    """Density categories are conditional; require execution of all 37 rules."""
    if group == "density":
        return validate_density_coverage(output / "drc.lyrdb", output / "run.log",
                                         config["top"], returncode)
    inventory = read_categories(output / "drc.lyrdb")
    if inventory != config["catalogs"][group]:
        raise ValueError("Native category names/descriptions differ from reference")
    return dict(category_inventory=inventory)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--group", required=True, choices=GROUPS)
    parser.add_argument("--prepare-only", action="store_true")
    parser.add_argument("--archive", type=Path)
    parser.add_argument("--manifest", type=Path, default=ROOT /
                        "docs/evidence/chip-native-parallel-input-v2-assets-20260928.json")
    parser.add_argument("--output", type=Path, default=ROOT / "hw/soc/out/github-chip-checks")
    args = parser.parse_args()
    out = args.output.resolve() / args.group
    out.mkdir(parents=True, exist_ok=False)
    record = dict(status="PREPARING", group=args.group, manufacturing_approval=False)
    def save():
        (out / "result.json").write_text(json.dumps(record, indent=2) + "\n")
    save()
    try:
        manifest = args.manifest.resolve()
        rows = validate(json.loads(manifest.read_text()))
        if len(rows) != 1:
            raise ValueError("Exactly one immutable bundle required")
        row = rows[0]
        if args.archive:
            archive = args.archive.resolve()
            verify(archive, row)
        else:
            fetch(row, out)
            archive = out / row["name"]
        bundle = out / "bundle"
        inventory = restore(archive, bundle)
        config = json.loads((bundle / "config.json").read_text())
        validate_config(config)
        if args.group not in config["commands"]:
            raise ValueError("Selected shard is absent from this immutable bundle")
        dependencies = validate_deck_dependencies(bundle, config)
        gds = bundle / config["gds"]
        if digest(gds) != config["gds_sha256"]:
            raise ValueError("Wrong GDS identity")
        pins = {bundle / n: v["sha256"] for n, v in inventory.items()}
        app = ROOT / "hw/soc/tools/physical/librelane-3.0.5-x86_64.AppImage"
        verify_tool(app, "x86_64")
        for path in (app, Path(__file__).resolve(), manifest,
                     ROOT / "hw/soc/flow/check_ihp_drc.py",
                     ROOT / "hw/soc/flow/check_ihp_drc_partitioned.py"):
            pins[path] = digest(path)
        if args.group == "density":
            path = ROOT / "hw/soc/flow/check_ihp_density_coverage.py"
            pins[path] = digest(path)
        report = out / "drc.lyrdb"
        command = [str(app), "klayout"] + [
            x.replace("@ROOT@", str(bundle)).replace("@GDS@", str(gds))
            .replace("@REPORT@", str(report)) for x in config["commands"][args.group]]
        record.update(status="PREPARED", command=command, gds_sha256=digest(gds),
                      native_dependencies_checked=dependencies,
                      scope=config["scope"], known_density_markers=config.get("known_density_markers"),
                      input_sha256={str(p): v for p, v in pins.items()})
        save()
        if args.prepare_only:
            return
        def limits():
            resource.setrlimit(resource.RLIMIT_AS, (12 * 1024**3,) * 2)
            resource.setrlimit(resource.RLIMIT_FSIZE, (128 * 1024**2,) * 2)
            resource.setrlimit(resource.RLIMIT_CORE, (0, 0))
        record["status"] = "RUNNING"
        save()
        started = time.monotonic()
        with (out / "run.log").open("x") as log:
            with subprocess.Popen(command, stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                                  text=True, preexec_fn=limits) as child:
                for line in child.stdout:
                    log.write(line)
                    log.flush()
                    print(line, end="", flush=True)
                code = child.wait()
        # record_result writes result.json; preserve the full provenance below.
        deck = args.group if args.group in ("antenna", "density") else "main"
        measurement = record_result(out, config["top"], code, pins, deck=deck)
        record.update(status=measurement["status"], measurement=measurement,
                      elapsed_seconds=time.monotonic() - started)
        save()
        if measurement["status"] == "ERROR":
            raise ValueError("Native execution failed")
        coverage = shard_coverage(args.group, config, out, code)
        record["category_inventory"] = coverage["category_inventory"]
        if args.group == "density":
            if coverage["status"] != measurement["status"]:
                raise ValueError("Density coverage and measurement status disagree")
            record["density_coverage"] = coverage
        save()
    except Exception as exc:
        record.update(status="ERROR", error=repr(exc))
        save()
        raise


if __name__ == "__main__":
    main()
