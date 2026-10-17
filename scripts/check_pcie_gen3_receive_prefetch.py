#!/usr/bin/env python3
# SPDX-FileCopyrightText: 2026 Hasan Melih Akbulut
# SPDX-License-Identifier: Apache-2.0
"""Replay the frozen RX oracle on a literal prefetch port wrapper; optionally map SG13G2."""

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
from check_pcie_gen3_receive_native import mapped_cell_count
from check_pcie_integrity import pin
from check_pcie_integrity_native import LIB_SHA, MODEL_SHA, quote
from cocotb_results import count_results

ROOT = Path(__file__).resolve().parents[1]
TOP = "soc_pcie_gen3_framer_rx"
PREFETCH = TOP + "_prefetch"
WRAPPER = """// SPDX-FileCopyrightText: 2026 Hasan Melih Akbulut
// SPDX-License-Identifier: CERN-OHL-W-2.0
// Literal verification adapter: no storage, logic, timing or policy changes.
module soc_pcie_gen3_framer_rx #(parameter integer MAX_ENCODED_BYTES=150)(
 input wire clk_i,rst_ni,flush_i,stream_start_i,stream_abort_i,
 input wire block_valid_i,output wire block_ready_o,
 input wire [7:0] headers_i,input wire [511:0] payload_i,input wire block_error_i,
 output wire valid_o,input wire ready_i,output wire [7:0] data_o,
 output wire sop_o,eop_o,dllp_o,packet_good_o,packet_nullified_o,
 output wire [11:0] sequence_o,
 output wire framing_error_o,stream_end_o,active_o,halted_o
);
 soc_pcie_gen3_framer_rx_prefetch #(.MAX_ENCODED_BYTES(MAX_ENCODED_BYTES)) dut(
 .clk_i(clk_i),.rst_ni(rst_ni),.flush_i(flush_i),
 .stream_start_i(stream_start_i),.stream_abort_i(stream_abort_i),
 .block_valid_i(block_valid_i),.block_ready_o(block_ready_o),
 .headers_i(headers_i),.payload_i(payload_i),.block_error_i(block_error_i),
 .valid_o(valid_o),.ready_i(ready_i),.data_o(data_o),.sop_o(sop_o),.eop_o(eop_o),
 .dllp_o(dllp_o),.packet_good_o(packet_good_o),.packet_nullified_o(packet_nullified_o),
 .sequence_o(sequence_o),.framing_error_o(framing_error_o),.stream_end_o(stream_end_o),
 .active_o(active_o),.halted_o(halted_o));
endmodule
"""


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--out", required=True, type=Path)
    parser.add_argument("--iverilog-dir", type=Path)
    parser.add_argument(
        "--rtl", type=Path, help="Source-bound prefetch candidate or fault-control override"
    )
    parser.add_argument("--native", action="store_true")
    parser.add_argument("--max-encoded-bytes", default=150, type=int)
    parser.add_argument("--command-timeout-seconds", type=float)
    for name in ("yosys", "liberty", "models"):
        parser.add_argument("--" + name, type=Path)
    args = parser.parse_args()
    if not 18 <= args.max_encoded_bytes <= 4118 or (
        args.native and args.max_encoded_bytes != 150
    ):
        parser.error("Capacity18..4118; native default150 only")
    if args.native and (
        any(
            getattr(args, n) is None
            for n in ("yosys", "liberty", "models", "iverilog_dir")
        )
    ):
        parser.error("Native requires explicit tools/library/models")
    if args.command_timeout_seconds is not None and args.command_timeout_seconds <= 0:
        parser.error("Explicit watchdog must be positive")
    out = args.out.resolve()
    if out.exists():
        parser.error("Fresh output required")
    tools = (
        args.iverilog_dir or Path(shutil.which("iverilog") or "iverilog").parent
    ).resolve()
    rtl = (args.rtl or ROOT / "hw/soc/rtl/pcie" / (PREFETCH + ".v")).resolve()
    rtl_text = rtl.read_text()
    if re.findall(r"^module\s+(\w+)", rtl_text, re.M) != [PREFETCH]:
        parser.error(
            "Require exactly the prefetch module; legacy verification wrapper is fixed"
        )
    driver = ROOT / "scripts/check_pcie_gen3_receive.py"
    bench = ROOT / "hw/soc/tb/cocotb" / ("test_" + TOP + ".py")
    files = [
        rtl,
        driver,
        bench,
        bench.with_name("Makefile." + TOP),
        Path(__file__).resolve(),
        ROOT / "scripts/check_pcie_gen3_receive_native.py",
        ROOT / "scripts/check_pcie_gen3_framer.py",
        ROOT / "scripts/check_pcie_integrity.py",
        ROOT / "scripts/check_pcie_integrity_native.py",
        ROOT / "scripts/cocotb_results.py",
    ]
    runtime = {str(tools / name): pin(tools / name) for name in ("iverilog", "vvp")}
    if args.native:
        args.liberty, args.models, args.yosys = (
            args.liberty.resolve(),
            args.models.resolve(),
            args.yosys.resolve(),
        )
        if (
            pin(args.liberty)["sha256"] != LIB_SHA
            or pin(args.models)["sha256"] != MODEL_SHA
        ):
            parser.error("Exact unmodified SG13G2 c4 Liberty and cell model required")
        version = subprocess.check_output(
            [str(tools / "iverilog"), "-V"], stderr=subprocess.STDOUT, text=True
        )
        match = re.search(r"Icarus Verilog version (\d+)", version)
        if not match or int(match[1]) < 13:
            parser.error("Native delayed ports require Icarus >=13")
        files += [args.liberty, args.models]
        runtime[str(args.yosys)] = pin(args.yosys)
    before = {str(p): pin(p) for p in files}
    expected = sum(
        isinstance(n, ast.AsyncFunctionDef) and bool(n.decorator_list)
        for n in ast.parse(bench.read_text()).body
    )
    if expected == 0:
        parser.error("No frozen port test cases")
    out.mkdir(parents=True)
    record = dict(
        status="RUNNING",
        mode="native" if args.native else "rtl",
        top=PREFETCH,
        verification_top=TOP,
        max_encoded_bytes=args.max_encoded_bytes,
        inputs=before,
        runtime=runtime,
        expected_tests=expected,
        scope="Registered next-byte address, lane-local shift and bounded positions, frozen v1 port oracle through literal adapter. No PHY/LTSSM, main-chip, SDF or timing-closure claim; native default150 only.",
    )

    def save():
        temporary = out / "result.tmp"
        temporary.write_text(json.dumps(record, indent=2) + "\n")
        temporary.replace(out / "result.json")

    def native_space(stage):
        free = shutil.disk_usage(out).free
        record.setdefault("native_stage_free_space", []).append(
            dict(stage=stage, bytes=free)
        )
        if free < 512 * 1024**2:
            raise RuntimeError("Native512MiB filesystem reserve unavailable")

    try:
        save()
        combined = out / "verification.v"
        (out / "wrapper.v").write_text(WRAPPER)
        combined.write_text(rtl_text + "\n" + WRAPPER)
        record["wrapper"] = pin(out / "wrapper.v")
        record["combined_source"] = pin(combined)
        argv = [
            str(driver),
            "--out",
            str(out / "ports"),
            "--iverilog-dir",
            str(tools),
            "--max-encoded-bytes",
            str(args.max_encoded_bytes),
        ]
        if args.native:
            native_space("mapping")
            recipe = (
                "read_liberty -lib "
                + quote(args.liberty)
                + "; read_verilog -sv "
                + quote(combined)
                + "; hierarchy -check -top "
                + TOP
                + "; flatten -noscopeinfo; synth -top "
                + TOP
                + " -noabc; dfflibmap -liberty "
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
            (out / "map.ys").write_text(recipe + "\n")
            record["mapping_returncode"] = execute_command(
                [str(args.yosys), "-Q", "-T", "-s", str(out / "map.ys")],
                out / "map.log",
                None,
                args.command_timeout_seconds,
            )
            if record["mapping_returncode"]:
                raise RuntimeError("Actual prefetch native mapping failed")
            record["mapped_cells"] = mapped_cell_count(
                json.loads((out / "mapped.json").read_text()), args.liberty.read_text()
            )
            native_space("replay")
            argv += ["--netlist", str(out / "mapped.v"), "--models", str(args.models)]
        else:
            argv += ["--rtl", str(combined)]
        if args.command_timeout_seconds is not None:
            argv += ["--command-timeout-seconds", str(args.command_timeout_seconds)]
        record["frozen_driver_argv"] = argv
        save()
        previous = sys.argv
        try:
            sys.argv = argv
            try:
                runpy.run_path(str(driver), run_name="__main__")
            except SystemExit as result:
                if result.code not in (0, None):
                    raise RuntimeError("Frozen v1 port driver failed") from result
        finally:
            sys.argv = previous
        ports = json.loads((out / "ports/result.json").read_text())
        counts = count_results([out / "ports/results.xml"])
        if (
            counts != (expected, 0, 0)
            or ports["status"] != "PASS_PORT_ONLY_GEN3_RECEIVE_FRAMING"
        ):
            raise ValueError("Missing/failed/skipped frozen port cases")
        if before != {p: pin(p) for p in before} or runtime != {
            p: pin(p) for p in runtime
        }:
            raise ValueError("Source/model/runtime drift")
        if record["combined_source"] != pin(combined) or record["wrapper"] != pin(
            out / "wrapper.v"
        ):
            raise ValueError("Verification adapter changed")
        record.update(
            status="PASS_GEN3_RECEIVE_PREFETCH_PORTS",
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
