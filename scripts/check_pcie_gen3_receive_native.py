#!/usr/bin/env python3
# SPDX-FileCopyrightText: 2026 Hasan Melih Akbulut
# SPDX-License-Identifier: Apache-2.0
"""Map default150 RX framing to pinned SG13G2 cells and replay frozen port tests."""

import argparse
import ast
import json
from pathlib import Path
import re
import runpy
import shutil
import subprocess
import sys

from check_pcie_gen3_framer import execute_command
from check_pcie_integrity import pin
from check_pcie_integrity_native import LIB_SHA, MODEL_SHA, quote
from cocotb_results import count_results

ROOT = Path(__file__).resolve().parents[1]
TOP = "soc_pcie_gen3_framer_rx"
FREE_FLOOR = 512 * 1024**2


def mapped_cell_count(document, liberty_text):
    """Require actual library cells, including rejection of fake prefixed cells."""
    known = set(re.findall(r"\bcell\s*\(\s*\"?([\w]+)\"?\s*\)", liberty_text))
    cells = document["modules"][TOP]["cells"]
    if not cells or any(
        not c["type"].startswith("sg13g2_") or c["type"] not in known
        for c in cells.values()
    ):
        raise ValueError("Empty mapping, unimplemented primitive or unknown IHP cell")
    return len(cells)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ("out", "yosys", "iverilog-dir", "liberty", "models"):
        parser.add_argument("--" + name, type=Path, required=True)
    parser.add_argument("--command-timeout-seconds", type=float)
    args = parser.parse_args()
    if args.command_timeout_seconds is not None and args.command_timeout_seconds <= 0:
        parser.error("Explicit watchdog must be positive")
    out = args.out.resolve()
    if out.exists():
        parser.error("Fresh output required; previous captures are preserved")
    lib, models = args.liberty.resolve(), args.models.resolve()
    if pin(lib)["sha256"] != LIB_SHA or pin(models)["sha256"] != MODEL_SHA:
        parser.error("Require exact unmodified SG13G2 c4 Liberty and cell model")
    tools = args.iverilog_dir.resolve()
    version = subprocess.check_output(
        [str(tools / "iverilog"), "-V"], stderr=subprocess.STDOUT, text=True
    )
    match = re.search(r"Icarus Verilog version (\d+)", version)
    if not match or int(match[1]) < 13:
        parser.error("Native delayed cell ports require Icarus >=13")
    rtl = ROOT / "hw/soc/rtl/pcie" / (TOP + ".v")
    driver = ROOT / "scripts/check_pcie_gen3_receive.py"
    bench = ROOT / "hw/soc/tb/cocotb" / ("test_" + TOP + ".py")
    sources = [
        rtl,
        driver,
        bench,
        bench.with_name("Makefile." + TOP),
        Path(__file__).resolve(),
        lib,
        models,
        ROOT / "scripts/check_pcie_gen3_framer.py",
        ROOT / "scripts/check_pcie_integrity.py",
        ROOT / "scripts/check_pcie_integrity_native.py",
        ROOT / "scripts/cocotb_results.py",
    ]
    expected = sum(
        isinstance(n, ast.AsyncFunctionDef) and bool(n.decorator_list)
        for n in ast.parse(bench.read_text()).body
    )
    if expected == 0:
        parser.error("No actual receive port tests")
    before = {str(p): pin(p) for p in sources}
    runtime = {
        str(p): pin(p)
        for p in (tools / "iverilog", tools / "vvp", args.yosys.resolve())
    }
    out.mkdir(parents=True)
    record = dict(
        status="RUNNING",
        top=TOP,
        max_encoded_bytes=150,
        inputs=before,
        runtime=runtime,
        iverilog_version=version.splitlines()[0],
        expected_tests=expected,
        address_space_limit_bytes=2 * 1024**3,
        stage_free_space_floor_bytes=FREE_FLOOR,
        free_space_checks=[],
        command_timeout_seconds=args.command_timeout_seconds,
        scope="Default150 mapped functional RX ports; no SDF, timing closure, PHY, LTSSM, maximum4118 native or main-chip adoption.",
    )

    def save():
        temporary = out / "result.tmp"
        temporary.write_text(json.dumps(record, indent=2) + "\n")
        temporary.replace(out / "result.json")

    def space_gate(stage):
        free = shutil.disk_usage(out).free
        record["free_space_checks"].append(dict(stage=stage, free_bytes=free))
        if free < FREE_FLOOR:
            raise RuntimeError("Native output filesystem has less than512MiB free")

    try:
        save()
        space_gate("before_mapping")
        recipe = (
            "read_liberty -lib "
            + quote(lib)
            + "; read_verilog -sv "
            + quote(rtl)
            + "; hierarchy -check -top "
            + TOP
            + "; flatten -noscopeinfo; synth -top "
            + TOP
            + " -noabc; dfflibmap -liberty "
            + quote(lib)
            + "; abc -liberty "
            + quote(lib)
            + "; clean; check -assert; stat -liberty "
            + quote(lib)
            + "; write_json "
            + quote(out / "mapped.json")
            + "; write_verilog -noattr -noexpr "
            + quote(out / "mapped.v")
        )
        (out / "map.ys").write_text(recipe + "\n")
        command = [str(args.yosys.resolve()), "-Q", "-T", "-s", str(out / "map.ys")]
        record["mapping_command"] = command
        record["mapping_returncode"] = execute_command(
            command, out / "map.log", None, args.command_timeout_seconds
        )
        if record["mapping_returncode"]:
            raise RuntimeError("Actual Yosys mapping failed")
        record["mapped_cells"] = mapped_cell_count(
            json.loads((out / "mapped.json").read_text()), lib.read_text()
        )
        space_gate("before_native_replay")
        argv = [
            str(driver),
            "--out",
            str(out / "ports"),
            "--iverilog-dir",
            str(tools),
            "--netlist",
            str(out / "mapped.v"),
            "--models",
            str(models),
        ]
        if args.command_timeout_seconds is not None:
            argv += ["--command-timeout-seconds", str(args.command_timeout_seconds)]
        record["port_driver_argv"] = argv
        save()
        # Execute the unchanged CLI in this process: its existing native child
        # group remains directly owned, including interrupt/watchdog cleanup.
        previous_argv = sys.argv
        try:
            sys.argv = argv
            try:
                runpy.run_path(str(driver), run_name="__main__")
            except SystemExit as exit_status:
                if exit_status.code not in (0, None):
                    raise RuntimeError(
                        "Frozen receive producer failed"
                    ) from exit_status
        finally:
            sys.argv = previous_argv
        ports = json.loads((out / "ports/result.json").read_text())
        counts = count_results([out / "ports/results.xml"])
        if ports["status"] != "PASS_PORT_ONLY_GEN3_RECEIVE_FRAMING" or counts != (
            expected,
            0,
            0,
        ):
            raise ValueError("Missing, failed or skipped mapped port cases")
        if before != {p: pin(p) for p in before} or runtime != {
            p: pin(p) for p in runtime
        }:
            raise ValueError("Source/model/runtime drift during native capture")
        record.update(
            status="PASS_MAPPED_DEFAULT150_GEN3_RECEIVE_FRAMING",
            tests=dict(zip(("passed", "failed", "skipped"), counts)),
            all_inputs_rechecked=True,
        )
    except BaseException as error:
        record.update(status="FAIL", error=repr(error))
        raise
    finally:
        record["outputs"] = {
            str(p.relative_to(out)): pin(p)
            for p in out.rglob("*")
            if p.is_file()
            and "sim" not in p.relative_to(out).parts
            and p not in (out / "result.json", out / "result.tmp")
        }
        save()
    print(record["status"], record["tests"])
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
