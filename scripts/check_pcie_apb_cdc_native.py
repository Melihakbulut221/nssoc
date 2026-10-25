#!/usr/bin/env python3
# SPDX-FileCopyrightText: 2026 Hasan Melih Akbulut
# SPDX-License-Identifier: Apache-2.0
"""Map the APB CDC bridge to pinned IHP cells and exercise its real ports."""

import argparse
import json
from pathlib import Path
import re
import resource
import subprocess

from check_pcie_integrity_native import LIB_SHA, MODEL_SHA, pin, quote

ROOT = Path(__file__).resolve().parents[1]


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ("out", "yosys", "iverilog-dir", "pdk"):
        parser.add_argument("--" + name, type=Path, required=True)
    args = parser.parse_args()
    out = args.out.resolve()
    std = args.pdk.resolve() / "libs.ref/sg13g2_stdcell"
    lib = std / "lib/sg13g2_stdcell_typ_1p20V_25C.lib"
    models = std / "verilog/sg13g2_stdcell.v"
    if pin(lib)["sha256"] != LIB_SHA or pin(models)["sha256"] != MODEL_SHA:
        parser.error("Exact c4 native standard-cell Liberty and models required")
    compiler = args.iverilog_dir.resolve() / "iverilog"
    simulator = compiler.with_name("vvp")
    version = subprocess.check_output(
        [str(compiler), "-V"], stderr=subprocess.STDOUT, text=True
    )
    match = re.search(r"Icarus Verilog version (\d+)", version)
    if not match or int(match[1]) < 13:
        parser.error("Actual IHP models require Icarus >=13")
    rtl = ROOT / "hw/soc/rtl/pcie/soc_pcie_apb_cdc.v"
    bench = ROOT / "hw/soc/tb/tb_pcie_apb_cdc.v"
    paths = [
        rtl,
        bench,
        lib,
        models,
        compiler,
        simulator,
        args.yosys.resolve(),
        Path(__file__),
        ROOT / "scripts/check_pcie_integrity_native.py",
    ]
    before = {str(p): pin(p) for p in paths}
    out.mkdir(parents=True, exist_ok=False)
    record = dict(
        status="RUNNING",
        inputs=before,
        commands=[],
        scope="Actual mapped IHP cells, three clock ratios, reset and stalled APB. Functional simulation only; no metastability, SDF, CDC physical constraints, placement or chip acceptance.",
    )

    def save():
        (out / "result.json").write_text(json.dumps(record, indent=2) + "\n")

    def limits():
        resource.setrlimit(resource.RLIMIT_AS, (2 * 1024**3,) * 2)

    def execute(command, name):
        with (out / name).open("x") as log:
            result = subprocess.run(
                list(map(str, command)),
                stdout=log,
                stderr=subprocess.STDOUT,
                cwd=out,
                preexec_fn=limits,
            )
        record["commands"].append(
            dict(argv=list(map(str, command)), returncode=result.returncode, log=name)
        )
        save()
        if result.returncode:
            raise ValueError(f"Native command failed: {name}")

    try:
        save()
        script = out / "map.ys"
        script.write_text(
            f"read_liberty -lib {quote(lib)}; read_verilog -sv {quote(rtl)}; "
            "hierarchy -check -top soc_pcie_apb_cdc; synth -top soc_pcie_apb_cdc -noabc; "
            f"dfflibmap -liberty {quote(lib)}; abc -liberty {quote(lib)}; "
            "hilomap -singleton -hicell sg13g2_tiehi L_HI -locell sg13g2_tielo L_LO; "
            f"clean; check -assert; stat -liberty {quote(lib)}; "
            f"write_json {quote(out / 'mapped.json')}; write_verilog -norename -noattr -noexpr {quote(out / 'mapped.v')};\n"
        )
        execute([args.yosys.resolve(), "-Q", "-T", "-s", script], "map.log")
        cells = json.loads((out / "mapped.json").read_text())["modules"][
            "soc_pcie_apb_cdc"
        ]["cells"]
        if not cells or any(
            not c["type"].startswith("sg13g2_") for c in cells.values()
        ):
            raise ValueError("Unmapped or missing physical cells")
        record["mapped_cells"] = len(cells)
        for sh, dh in [(2, 10), (11, 3), (5, 7)]:
            name = f"{sh}-{dh}"
            binary = out / (name + ".vvp")
            execute(
                [
                    compiler,
                    "-g2012",
                    "-s",
                    "tb_pcie_apb_cdc",
                    f"-Ptb_pcie_apb_cdc.SOURCE_HALF={sh}",
                    f"-Ptb_pcie_apb_cdc.DESTINATION_HALF={dh}",
                    "-o",
                    binary,
                    out / "mapped.v",
                    models,
                    bench,
                ],
                name + "-compile.log",
            )
            execute([simulator, binary], name + "-run.log")
            text = (out / (name + "-run.log")).read_text()
            expected = (
                f"PASS_PCIE_APB_CDC transfers=97 source_half={sh} destination_half={dh}"
            )
            if text.count(expected) != 1 or re.search(
                r"\b(?:ERROR|FATAL|WARNING):", text
            ):
                raise ValueError("Missing native verdict or simulation diagnostic")
        if before != {str(p): pin(p) for p in paths}:
            raise ValueError("Inputs changed during verification")
        record.update(
            status="PASS", clock_ratios=3, transfers_per_ratio=97, inputs_unchanged=True
        )
    except BaseException as error:
        record.update(status="FAIL", error=repr(error))
    finally:
        record["outputs"] = {
            p.name: pin(p)
            for p in out.iterdir()
            if p.is_file() and p.name != "result.json"
        }
        save()
    print(
        json.dumps(
            {
                k: v
                for k, v in record.items()
                if k not in ("inputs", "outputs", "commands")
            },
            indent=2,
        )
    )
    return record["status"] != "PASS"


if __name__ == "__main__":
    raise SystemExit(main())
