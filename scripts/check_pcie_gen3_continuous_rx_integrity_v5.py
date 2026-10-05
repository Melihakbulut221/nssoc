#!/usr/bin/env python3
# SPDX-FileCopyrightText: 2026 Hasan Melih Akbulut
# SPDX-License-Identifier: Apache-2.0
"""Sustained wide CRC/quarantine RX; independent public-port functional controls."""

import argparse
import ast
import json
import os
import resource
import re
import shutil
import signal
from pathlib import Path
import subprocess
import sys

from check_pcie_integrity import pin, tool_environment
from check_pcie_integrity_native import LIB_SHA, MODEL_SHA, quote
from cocotb_results import count_results

ROOT = Path(__file__).resolve().parents[1]
COMMON = (
    "soc_pcie_gen3_ingress",
    "soc_pcie_gen3_data_descrambler",
    "soc_pcie_gen3_framer_rx_integrity_v5",
    "soc_pcie_gen3_continuous_rx_integrity_v5",
)


def interrupted(signum, _frame):
    raise InterruptedError(f"Parent signal {signum}")


def main():
    for sig in (signal.SIGTERM, signal.SIGINT):
        signal.signal(sig, interrupted)
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--top",
        choices=("soc_pcie_gen3_continuous_rx_integrity_v5",),
        default="soc_pcie_gen3_continuous_rx_integrity_v5",
    )
    parser.add_argument("--max-bytes", type=int, choices=(150, 4118), default=150)
    parser.add_argument(
        "--test", help="Exact named port case, for bounded actual HDL fault controls"
    )
    parser.add_argument("--out", type=Path, required=True)
    parser.add_argument("--iverilog-dir", type=Path)
    parser.add_argument("--rtl-dir", type=Path)
    parser.add_argument("--native", action="store_true")
    for name in ("yosys", "liberty", "models"):
        parser.add_argument("--" + name, type=Path)
    args = parser.parse_args()
    if args.native and (
        args.rtl_dir
        or any(
            getattr(args, n) is None
            for n in ("yosys", "liberty", "models", "iverilog_dir")
        )
    ):
        parser.error(
            "Native run requires explicit tools/libraries and forbids mutated RTL"
        )
    out = args.out.resolve()
    if out.exists():
        parser.error("Use a fresh output directory")
    rtl_dir = args.rtl_dir or ROOT / "hw/soc/rtl/pcie"
    rtl = [(rtl_dir / (name + ".v")).resolve() for name in COMMON]
    bench = ROOT / "hw/soc/tb/cocotb" / ("test_" + args.top + ".py")
    makefile = bench.with_name("Makefile." + args.top)
    files = [
        *rtl,
        bench,
        makefile,
        Path(__file__).resolve(),
        ROOT / "scripts/check_pcie_integrity.py",
        ROOT / "scripts/check_pcie_integrity_native.py",
        ROOT / "scripts/cocotb_results.py",
        ROOT / "scripts/generate_pcie_crc_candidates_v3.py",
    ]
    available = [
        n.name
        for n in ast.parse(bench.read_text()).body
        if isinstance(n, ast.AsyncFunctionDef) and n.decorator_list
    ]
    if args.test is not None and args.test not in available:
        parser.error("Unknown actual port case")
    expected = 1 if args.test else len(available)
    if expected == 0:
        parser.error("No actual port cases")
    if args.native:
        args.liberty, args.models = args.liberty.resolve(), args.models.resolve()
        if (
            pin(args.liberty)["sha256"] != LIB_SHA
            or pin(args.models)["sha256"] != MODEL_SHA
        ):
            parser.error("Require the exact unmodified c4 SG13G2 library/model bytes")
        version = subprocess.check_output(
            [str(args.iverilog_dir.resolve() / "iverilog"), "-V"],
            stderr=subprocess.STDOUT,
            text=True,
        )
        match = re.search(r"Icarus Verilog version (\d+)", version)
        if not match or int(match[1]) < 13:
            parser.error("Native cell delayed ports require Icarus >=13")
        files += [args.liberty, args.models]
    runtime = {}
    for tool in ("iverilog", "vvp", "yosys"):
        candidate = (
            args.yosys
            if tool == "yosys" and args.native
            else args.iverilog_dir / tool
            if args.iverilog_dir and tool != "yosys"
            else None
        )
        if candidate is None and tool != "yosys":
            candidate = Path(shutil.which(tool) or tool)
        if candidate is not None:
            candidate = candidate.resolve()
            runtime[str(candidate)] = pin(candidate)
    before = {str(p): pin(p) for p in files}
    out.mkdir(parents=True)
    record = dict(
        status="RUNNING",
        top=args.top,
        inputs=before,
        expected_tests=expected,
        mode="native" if args.native else "rtl",
        mapping_strategy="unconditional_parallel_crc_candidates_v3",
        commands=[],
        runtime=runtime,
        address_space_limit_bytes=2 * 1024**3,
        yosys_max_threads=1,
        max_encoded_bytes=args.max_bytes,
        exact_test_selection=args.test,
        theoretical_dwords_per_cycle=4,
        minimum_packet_ring_dwords=1 << (((args.max_bytes + 2) // 4 + 15).bit_length()),
        scope="Continuous raw32-bit/lane input, four ordered DWORD parser steps without a block-load bubble, and masked128-bit retirement. Whole-packet LCRC32/DLLPCRC16 and lookahead quarantine is preserved. EDB requires the inverted ordinary LCRC; CRC failure is distinct from framing failure. No ECRC/ACK/NAK/replay policy acceptance. Finite output stalls can overflow the bounded ring and halt the epoch. Fixed external Data Stream alignment/deskew only; no SKP/OS search, CDC, PMA, completePCS/LTSSM or physicalfrequency acceptance.",
    )

    def save():
        (out / "result.json").write_text(json.dumps(record, indent=2) + "\n")

    def child_limits():
        resource.setrlimit(resource.RLIMIT_AS, (2 * 1024**3, 2 * 1024**3))
        resource.setrlimit(resource.RLIMIT_CORE, (0, 0))

    def execute(command, log_name, environment=None):
        environment = dict(os.environ) if environment is None else environment.copy()
        # The Makefile asks the actual cocotb interpreter for its own sys.path.
        # Do not inject this CLI interpreter's standard library into another ABI.
        environment.pop("PYTHONPATH", None)
        environment.pop("PYTHONHOME", None)
        environment.pop("PYTHONEXECUTABLE", None)
        environment["PATH"] = os.pathsep.join(
            [
                str(ROOT / "hw/soc/tools/cocotb-venv/bin"),
                str(args.iverilog_dir.resolve()) if args.iverilog_dir else "/usr/bin",
                environment.get("PATH", ""),
            ]
        )
        environment["YOSYS_MAX_THREADS"] = "1"
        environment.pop("COCOTB_TEST_FILTER", None)
        environment.pop("COCOTB_TESTCASE", None)
        if args.test:
            environment["COCOTB_TEST_FILTER"] = "^.*\\." + re.escape(args.test) + "$"
        with (out / log_name).open("x") as log:
            process = subprocess.Popen(
                command,
                cwd=out,
                env=environment,
                stdout=log,
                stderr=subprocess.STDOUT,
                preexec_fn=child_limits,
                start_new_session=True,
            )
            try:
                process.wait()
            except BaseException:
                try:
                    os.killpg(process.pid, signal.SIGKILL)
                except ProcessLookupError:
                    pass
                finally:
                    process.wait()
                raise
            result = process
        record["commands"].append(
            dict(
                argv=command,
                returncode=result.returncode,
                log=log_name,
                log_pin=pin(out / log_name),
            )
        )
        save()
        if result.returncode:
            raise RuntimeError("Control failed: " + str(out / log_name))

    try:
        save()
        simulation_sources = rtl
        if args.native:
            script = (
                "read_liberty -lib "
                + quote(args.liberty)
                + "; read_verilog -sv "
                + " ".join(map(quote, rtl))
                + "; chparam -set MAX_ENCODED_BYTES "
                + str(args.max_bytes)
                + " "
                + args.top
                + "; hierarchy -check -top "
                + args.top
                + "; flatten -noscopeinfo; synth -top "
                + args.top
                + " -nofsm -noabc; "
                + "dfflibmap -liberty "
                + quote(args.liberty)
                + "; abc -liberty "
                + quote(args.liberty)
                + "; clean; check -assert; stat -liberty "
                + quote(args.liberty)
                + "; write_json "
                + quote(out / "mapped.json")
                + "; write_verilog -noattr -noexpr "
                + quote(out / "mapped.v")
            )
            (out / "map.ys").write_text(script + "\n")
            execute(
                [str(args.yosys.resolve()), "-Q", "-T", "-s", str(out / "map.ys")],
                "map.log",
            )
            cells = json.loads((out / "mapped.json").read_text())["modules"][args.top][
                "cells"
            ]
            if not cells or any(
                not c["type"].startswith("sg13g2_") for c in cells.values()
            ):
                raise ValueError("Unimplemented or non-IHP mapped cells")
            record["mapped_cells"] = len(cells)
            simulation_sources = [out / "mapped.v", args.models]
        execute(
            [
                "make",
                "-f",
                str(makefile),
                "--no-print-directory",
                "VERILOG_SOURCES=" + " ".join(map(str, simulation_sources)),
                "SIM_BUILD=" + str(out / "sim"),
                "COCOTB_RESULTS_FILE=" + str(out / "results.xml"),
                "PCIE_NATIVE=" + str(int(args.native)),
                "PCIE_WIDE_MAX_BYTES=" + str(args.max_bytes),
            ],
            "simulation.log",
            tool_environment(args.iverilog_dir),
        )
        counts = count_results([out / "results.xml"])
        record["tests"] = dict(zip(("passed", "failed", "skipped"), counts))
        expected_counts = (expected, 0, len(available) - 1 if args.test else 0)
        if counts != expected_counts:
            raise ValueError("Missing, failed or skipped port cases")
        if before != {str(p): pin(p) for p in files}:
            raise ValueError("Sources changed during verification")
        if runtime != {p: pin(Path(p)) for p in runtime}:
            raise ValueError("Runtime changed during verification")
        record["status"] = "PASS_PORT_ONLY_PCIE_GEN3_WIDE_CRC_QUARANTINE_RX"
    except BaseException as error:
        record.update(status="FAIL", error=repr(error))
    finally:
        record["outputs"] = {
            str(p.relative_to(out)): pin(p)
            for p in out.rglob("*")
            if p.is_file()
            and p.name != "result.json"
            and "sim" not in p.relative_to(out).parts
        }
        save()
    print(record["status"], record.get("tests", record.get("error")))
    return int(record["status"] != "PASS_PORT_ONLY_PCIE_GEN3_WIDE_CRC_QUARANTINE_RX")


if __name__ == "__main__":
    raise SystemExit(main())
