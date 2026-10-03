#!/usr/bin/env python3
# SPDX-FileCopyrightText: 2026 Hasan Melih Akbulut
# SPDX-License-Identifier: Apache-2.0
"""Compare one immutable Vdd hierarchy in deep and flat native parent contexts.

This is a diagnostic of a single I/O master. It preserves strict native ports,
tap A/P, devices and geometry. A completed comparison may legitimately FAIL;
it never establishes whole-chip LVS, ESD qualification or production approval.
"""
import argparse
import hashlib
import json
import os
from pathlib import Path, PurePosixPath
import resource
import subprocess
import sys
import tarfile
import time

ROOT = Path(__file__).resolve().parents[1]
OUTPUT_ROOT = ROOT / "hw/soc/out"
sys.path.insert(0, str(ROOT / "hw/soc/flow"))
from bootstrap_flow import ARTIFACTS, verify as verify_runtime  # noqa: E402
from fetch_evidence_assets import fetch, verify as verify_asset  # noqa: E402
from prepare_ihp_drc import validate_lock  # noqa: E402
from audit_klayout_lvs import assess  # noqa: E402

TOP = "sg13g2_IOPadVdd"
GIB = 1024**3
ASSET = dict(
    name="timing-hold-review-and-io-global-repair-20260930.tar.gz",
    bytes=11653956,
    sha256="e99938d0051d66231e23e7a5bae003945ec6c8c7aff62b8cef4f1402b3838d4e",
    url="https://github.com/Melihakbulut221/nssoc/releases/download/"
        "evidence-20260927-chip-io/timing-hold-review-and-io-global-repair-20260930.tar.gz",
)
MEMBERS = {
    "io-review/vdd-subset/extracted/subset.gds": (
        "subset.gds", "6b9ba04d4766f2d8807f0c37208d7fe24a102eb53021b7a653e358ba502362a6"),
    "io-review/vdd-subset/extracted/receipt.json": (
        "subset-receipt.json", "35272d591da0ea3ad790335dd8fbd0c6c4bfb2268cc997e43e7e2adf939e57bc"),
    "io-review/subset-ab-1536m/subset-adapter_explicit_global/schematic.cir": (
        "schematic.cir", "2b9fc98f1b6279587cecf256b2d0269511ae905fac9c3095474e2ae75282aca8"),
}
LOCK = ROOT / "hw/soc/pnr/ihp-lvs.lock.json"
LOCK_SHA256 = "9a7989016329c26a75f6d2241913f891b8746ba977586146a788f4234b5a7532"
DECK = ROOT / "hw/soc/tools/ihp-lvs-5e6d592"
APP = ROOT / "hw/soc/tools/physical/librelane-3.0.5-x86_64.AppImage"
APP_SHA256 = ARTIFACTS["x86_64"][1]
AUDIT = ROOT / "hw/soc/flow/audit_klayout_lvs.py"
CONTROL = ROOT / "sw/tests/io_parent_lvs_native.py"
CONTROL_CASES = {"connected": True, "same_name_open": False, "missing_via": False,
                 "wrong_width": False, "wrong_length": False, "wrong_tap_perimeter": False,
                 "wrong_tap_area": False, "reversed_tap_terminals": False}
CONTROL_FILES = {"layout.gds", "hierarchy.l2n", "hierarchy.txt", "layout-netlist.txt",
                 "reference-netlist.txt"}


def sha(path):
    with Path(path).open("rb") as source:
        return hashlib.file_digest(source, "sha256").hexdigest()


def write_json(path, value):
    temporary = path.with_suffix(".json.tmp")
    with temporary.open("x") as stream:
        json.dump(value, stream, indent=2)
        stream.write("\n")
    os.replace(temporary, path)


def unpack_inputs(archive, destination):
    """Verify the complete published archive, then copy only three pinned files."""
    verify_asset(archive, ASSET)
    selected = {}
    with tarfile.open(archive) as source:
        members = source.getmembers()
        names = [item.name for item in members]
        if len(set(names)) != len(names) or len(names) > 1024:
            raise ValueError("Duplicate or excessive archive inventory")
        if sum(item.size for item in members) > 64 * 1024**2:
            raise ValueError("Archive expands beyond bounded input budget")
        for item in members:
            name = PurePosixPath(item.name)
            if (not item.isfile() or name.is_absolute() or ".." in name.parts
                    or "\\" in item.name or str(name) != item.name):
                raise ValueError("Unsafe archive member")
        inventory = json.load(source.extractfile("members.json"))
        if set(names) != set(inventory) | {"members.json"}:
            raise ValueError("Incomplete published member inventory")
        for item in members:
            if item.name == "members.json":
                continue
            row = inventory[item.name]
            if item.size != row["bytes"]:
                raise ValueError("Wrong inventoried member size")
            digest = hashlib.sha256()
            chunks = []
            with source.extractfile(item) as stream:
                while chunk := stream.read(1024**2):
                    digest.update(chunk)
                    if item.name in MEMBERS:
                        chunks.append(chunk)
            if digest.hexdigest() != row["sha256"]:
                raise ValueError("Wrong inventoried member hash")
            if item.name in MEMBERS:
                target, expected = MEMBERS[item.name]
                if digest.hexdigest() != expected:
                    raise ValueError("Wrong pinned Vdd input")
                selected[target] = b"".join(chunks)
    if set(selected) != {value[0] for value in MEMBERS.values()}:
        raise ValueError("Missing pinned Vdd inputs")
    proof = json.loads(selected["subset-receipt.json"])
    if (proof["status"] != "BYTE_PRESERVED_HIERARCHY_SUBSET" or proof["roots"] != [TOP]
            or proof["output"]["sha256"] != hashlib.sha256(selected["subset.gds"]).hexdigest()
            or proof["output"]["bytes"] != len(selected["subset.gds"])
            or proof["output"]["cell_count"] != 4 or len(proof["cells"]) != 4):
        raise ValueError("Invalid byte-preserved subset provenance")
    if not selected["schematic.cir"].startswith(b".GLOBAL sub!\n"):
        raise ValueError("Explicit substrate global missing")
    destination.mkdir(exist_ok=False)
    for name, data in selected.items():
        with (destination / name).open("xb") as stream:
            stream.write(data)
    return {str(destination / name): hashlib.sha256(data).hexdigest()
            for name, data in selected.items()}


def verify_deck(directory=DECK, lock_path=LOCK):
    if sha(lock_path) != LOCK_SHA256:
        raise ValueError("Changed native deck lock")
    lock = json.loads(lock_path.read_text())
    validate_lock(lock)
    if lock["commit"] != "5e6d592e4002946a4616f798c357f0f3c06cf3b6":
        raise ValueError("Unexpected native deck revision")
    pins = {str(lock_path): sha(lock_path)}
    for row in lock["files"]:
        path = directory / row["path"]
        if (not path.resolve().is_relative_to(directory.resolve())
                or path.stat().st_size != row["bytes"] or sha(path) != row["sha256"]):
            raise ValueError("Changed native deck dependency: " + row["path"])
        pins[str(path)] = row["sha256"]
    return directory / lock["entrypoint"], pins


def validate_controls(path):
    path = path.resolve()
    if not path.is_relative_to(OUTPUT_ROOT.resolve()):
        raise ValueError("Native control receipt must stay in this project's hw/soc/out")
    result = json.loads(path.read_text())
    if result.get("status") != "PASS_NATIVE_PARENT_CONTEXT_CONTROLS":
        raise ValueError("Native parent-context controls incomplete")
    if result.get("method_sha256", {}).get("sw/tests/io_parent_lvs_native.py") != sha(CONTROL):
        raise ValueError("Native controls source differs")
    if set(result.get("cases", {})) != set(CONTROL_CASES):
        raise ValueError("Missing or unexpected native control inventory")
    expected_outputs = {}
    for name, expected in CONTROL_CASES.items():
        case = result["cases"][name]
        if case.get("actual_match") is not expected or case.get("expected_match") is not expected:
            raise ValueError("Missing or wrong native control: " + name)
        if (case.get("device_counts") != {"NMOS4": 2, "TAP": 1}
                or case.get("extraction_diagnostics") != []
                or set(case.get("hierarchical_circuits", [])) != {"CHILD", "TOP"}
                or case.get("tap_terminal_order") != ["TIE", "WELL"]
                or case.get("tap_parameters") != {
                    "A": 0.75 if name == "wrong_tap_area" else 1.0,
                    "P": 5.0 if name == "wrong_tap_perimeter" else 4.0}):
            raise ValueError("Incomplete or inconsistent native device control: " + name)
        drains = 2 if name in ("same_name_open", "missing_via") else 1
        if (case.get("distinct_drain_nets_after_parent_extraction") != drains
                or len(case.get("drain_cluster_ids", [])) != 2
                or len(set(case["drain_cluster_ids"])) != drains):
            raise ValueError("Parent physical connectivity control inconsistent")
        if set(case.get("files", {})) != CONTROL_FILES:
            raise ValueError("Missing native control evidence files")
        for name_file, expected_sha in case["files"].items():
            output = (path.parent / name / name_file).resolve()
            if not output.is_relative_to(path.parent):
                raise ValueError("Native control evidence escapes its receipt directory")
            expected_outputs[str(output)] = expected_sha
    if not result.get("input_sha256") or not result.get("output_sha256"):
        raise ValueError("Native controls lack replayable source/output pins")
    if result["input_sha256"] != {str(CONTROL.resolve()): sha(CONTROL),
                                  str(APP.resolve()): APP_SHA256}:
        raise ValueError("Native controls must bind the exact method and pinned runtime")
    if result["output_sha256"] != expected_outputs:
        raise ValueError("Native output inventory differs from all control case files")
    check_pins(result["input_sha256"])
    check_pins(result["output_sha256"])
    return result


def require_resources(meminfo=Path("/proc/meminfo")):
    values = dict(line.split(":", 1) for line in meminfo.read_text().splitlines())
    available = int(values["MemAvailable"].split()[0]) * 1024
    if available < 5 * GIB:
        raise ValueError("Native Vdd requires 5 GiB available RAM; use isolated cloud worker")
    return available


def command(app, deck, inputs, case, mode):
    if mode not in ("deep", "flat"):
        raise ValueError("Unsupported comparison mode")
    args = [str(app), "klayout", "-b", "-zz", "-r", str(deck)]
    for name, value in dict(input=inputs / "subset.gds", schematic=inputs / "schematic.cir",
                            topcell=TOP, report=case / "lvs.lvsdb.gz", log=case / "deck.log",
                            target_netlist=case / "extracted.cir", run_mode=mode, thr=1,
                            disable_tap_extraction="false",
                            ignore_top_ports_mismatch="false").items():
        args.extend(["-rd", f"{name}={value}"])
    return args


def check_pins(pins):
    for path, expected in pins.items():
        if sha(path) != expected:
            raise ValueError("Source changed during comparison: " + path)


def execute(args, log):
    def limits():
        resource.setrlimit(resource.RLIMIT_AS, (4 * GIB,) * 2)
        resource.setrlimit(resource.RLIMIT_CORE, (0, 0))
    start = time.monotonic()
    with log.open("x") as stream:
        completed = subprocess.run(args, stdout=stream, stderr=subprocess.STDOUT,
                                   preexec_fn=limits, check=False)
    return dict(command=args, returncode=completed.returncode,
                elapsed_seconds=time.monotonic() - start, address_space_limit_bytes=4 * GIB,
                elapsed_watchdog=False)


def verdict(case, native, audit_process):
    expected = [case / name for name in ("lvs.lvsdb.gz", "deck.log", "extracted.cir", "audit.json")]
    if native["returncode"] != 0 or any(not path.is_file() or path.stat().st_size == 0 for path in expected):
        raise ValueError("Native comparison did not complete with all required outputs")
    audit = json.loads((case / "audit.json").read_text())
    valid = ((audit.get("status") == "PASS within comparison scope" and
              audit_process["returncode"] == 0 and not audit.get("reasons")) or
             (audit.get("status") == "FAIL" and audit_process["returncode"] == 1 and
              bool(audit.get("reasons"))))
    if not valid or audit.get("top") != TOP or not audit.get("circuits"):
        raise ValueError("Inconsistent or incomplete strict native audit")
    replay = assess(audit["circuits"], TOP, (case / "deck.log").read_text(),
                    audit.get("extraction_diagnostics", []))
    if any(audit.get(key) != value for key, value in replay.items()):
        raise ValueError("Audit assessment cannot be independently replayed")
    for name in ("lvs.lvsdb.gz", "deck.log"):
        path = case / name
        row = audit.get("inputs", {}).get(str(path), {})
        if row != {"bytes": path.stat().st_size, "sha256": sha(path)}:
            raise ValueError("Audit does not bind exact native outputs")
    return audit


def run(output, archive=None, controls=None, prepare_only=False):
    output = output.resolve()
    if not output.is_relative_to(OUTPUT_ROOT.resolve()):
        raise ValueError("Output must remain in this project's hw/soc/out")
    output.mkdir(parents=True, exist_ok=False)
    record = dict(schema=1, status="PREPARING", top=TOP, cases={}, input_sha256={},
                  source_sha=os.environ.get("GITHUB_SHA"), run_id=os.environ.get("GITHUB_RUN_ID"),
                  scope="Strict isolated Vdd parent-context diagnostic; no whole-chip acceptance",
                  cell_lvs_accepted=False, full_chip_lvs_accepted=False, manufacturing_approval=False)
    result_path = output / "result.json"
    write_json(result_path, record)
    try:
        if archive is None:
            cache = output / "asset"
            cache.mkdir()
            fetch(ASSET, cache)
            archive = cache / ASSET["name"]
        archive = archive.resolve()
        record["asset"] = ASSET
        record["input_sha256"] = unpack_inputs(archive, output / "inputs")
        record["input_sha256"][str(archive)] = ASSET["sha256"]
        methods = [Path(__file__).resolve(), AUDIT, CONTROL, ROOT / "scripts/bootstrap_flow.py",
                   ROOT / "scripts/fetch_evidence_assets.py", ROOT / "hw/soc/flow/prepare_ihp_drc.py"]
        record["input_sha256"].update({str(path): sha(path) for path in methods})
        if prepare_only:
            check_pins(record["input_sha256"])
            record["status"] = "PREPARED_NO_NATIVE_COMPARISON"
            write_json(result_path, record)
            return record
        if controls is None:
            raise ValueError("Native positive and negative control receipt is required")
        record["controls"] = validate_controls(controls)
        record["input_sha256"][str(controls.resolve())] = sha(controls)
        record["input_sha256"].update(record["controls"]["input_sha256"])
        record["input_sha256"].update(record["controls"]["output_sha256"])
        deck, pins = verify_deck()
        record["input_sha256"].update(pins)
        verify_runtime(APP, "x86_64")
        record["input_sha256"][str(APP)] = sha(APP)
        for mode in ("deep", "flat"):
            check_pins(record["input_sha256"])
            available = require_resources()
            case = output / mode
            case.mkdir()
            detail = dict(status="RUNNING", launch_mem_available_bytes=available)
            record["cases"][mode] = detail
            record["status"] = "RUNNING_" + mode.upper()
            write_json(result_path, record)
            detail["native"] = execute(command(APP, deck, output / "inputs", case, mode), case / "run.log")
            write_json(result_path, record)
            audit_args = [str(APP), "python", str(AUDIT), str(case / "lvs.lvsdb.gz"),
                          "--top", TOP, "--deck-log", str(case / "deck.log"),
                          "--output", str(case / "audit.json")]
            detail["audit_process"] = execute(audit_args, case / "audit.log")
            detail["audit"] = verdict(case, detail["native"], detail["audit_process"])
            detail["status"] = detail["audit"]["status"]
            detail["output_sha256"] = {str(path): sha(path) for path in case.iterdir() if path.is_file()}
            check_pins(record["input_sha256"])
            write_json(result_path, record)
        record["cell_lvs_accepted"] = record["cases"]["flat"]["status"] == "PASS within comparison scope"
        record["status"] = ("PASS_VDD_PARENT_CONTEXT_ONLY" if record["cell_lvs_accepted"]
                            else "FAIL_VDD_PARENT_CONTEXT_LVS")
        write_json(result_path, record)
        return record
    except Exception as error:
        record.update(status="ERROR_OR_INCOMPLETE_NATIVE_COMPARISON", error=repr(error))
        write_json(result_path, record)
        raise


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--archive", type=Path, help="Existing exact published input asset")
    parser.add_argument("--controls", type=Path, help="Completed independent native fixture receipt")
    parser.add_argument("--prepare-only", action="store_true")
    args = parser.parse_args()
    try:
        result = run(args.output, args.archive, args.controls, args.prepare_only)
    except (OSError, ValueError, KeyError, tarfile.TarError) as error:
        parser.exit(2, str(error) + "\n")
    print(result["status"])
    return 1 if result["status"].startswith("FAIL") else 0


if __name__ == "__main__":
    raise SystemExit(main())
