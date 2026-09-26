#!/usr/bin/env python3
# SPDX-FileCopyrightText: 2026 Hasan Melih Akbulut
# SPDX-License-Identifier: Apache-2.0
"""Verify the raw MBIST port on three native IHP functional macro models.

This is digital model/port verification, not transistor or chip-integrated MBIST.
The output directory must be new. Missing models/tools are errors, never skips.
"""

import argparse
import hashlib
import json
from pathlib import Path
import shutil
import subprocess

ROOT = Path(__file__).resolve().parents[1]
SHAPES = [(512, 16), (1024, 32), (2048, 64)]


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--pdk", type=Path, required=True, help="SG13G2 PDK root")
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    args.output.mkdir(parents=True, exist_ok=False)
    record = {
        "status": "RUNNING",
        "physical_signoff": False,
        "chip_integration": False,
        "cases": [],
        "inputs": {},
    }
    result_file = args.output / "result.json"

    def save():
        result_file.write_text(json.dumps(record, indent=2) + "\n")

    try:
        compiler, runtime = shutil.which("iverilog"), shutil.which("vvp")
        if not compiler or not runtime:
            raise RuntimeError("Icarus Verilog compiler and runtime are required")
        record["tool_sha256"] = {
            Path(p).name: sha(Path(p)) for p in (compiler, runtime)
        }
        source_paths = [
            Path(__file__).resolve(),
            ROOT / "hw/soc/rtl/dft/soc_sram_mbist.v",
            ROOT / "hw/soc/rtl/dft/soc_sram_test_port.v",
            ROOT / "hw/soc/tb/tb_soc_sram_test_port.v",
        ]
        models = args.pdk / "libs.ref/sg13g2_sram/verilog"
        common = models / "RM_IHPSG13_1P_core_behavioral_bm_bist.v"
        macro_paths = [
            models / f"RM_IHPSG13_1P_{depth}x{width}_c2_bm_bist.v"
            for depth, width in SHAPES
        ]
        inputs = source_paths + [common] + macro_paths
        original_hashes = {p: sha(p) for p in inputs}
        record["inputs"] = {
            str(p.relative_to(ROOT))
            if p.is_relative_to(ROOT)
            else "PDK/verilog/" + p.name: digest
            for p, digest in original_hashes.items()
        }
        save()
        for (depth, width), macro_path in zip(SHAPES, macro_paths):
            binary = args.output / f"{depth}x{width}.vvp"
            cmd = [
                compiler,
                "-g2012",
                "-DFUNCTIONAL",
                "-DMBIST_NATIVE",
                f"-DMBIST_MACRO={macro_path.stem}",
                "-s",
                "tb_soc_sram_test_port",
                f"-Ptb_soc_sram_test_port.WIDTH={width}",
                f"-Ptb_soc_sram_test_port.DEPTH={depth}",
                "-o",
                str(binary),
                *map(str, source_paths[1:]),
                str(common),
                str(macro_path),
            ]
            compiled = subprocess.run(cmd, capture_output=True, text=True, timeout=60)
            (args.output / f"{depth}x{width}-compile.log").write_text(
                compiled.stdout + compiled.stderr
            )
            if compiled.returncode:
                raise RuntimeError(f"native {depth}x{width} compile failed")
            for mode, fault in [(0, 0), (1, 0), (2, 0), (3, 0), (0, 1)]:
                case = f"{depth}x{width}-mode{mode}-fault{fault}"
                run = subprocess.run(
                    [runtime, str(binary), f"+mode={mode}", f"+fault={fault}"],
                    capture_output=True,
                    text=True,
                    timeout=60,
                )
                (args.output / f"{case}.log").write_text(run.stdout + run.stderr)
                passed = run.returncode == 0 and "PASS test-port " in run.stdout
                record["cases"].append(
                    {
                        "case": case,
                        "passed": passed,
                        "read_corruption_detected": bool(fault),
                        "returncode": run.returncode,
                    }
                )
                save()
                if not passed:
                    raise RuntimeError(f"native {case} failed")
        if any(sha(p) != h for p, h in original_hashes.items()):
            raise RuntimeError("an input changed during verification")
        record["status"] = "PASS_15_NATIVE_FUNCTIONAL_MODEL_PORT_CASES"
        save()
        print(record["status"])
    except BaseException as exc:
        record.update(status="ERROR", error=str(exc))
        save()
        raise


if __name__ == "__main__":
    main()
