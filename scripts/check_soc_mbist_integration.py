#!/usr/bin/env python3
# SPDX-FileCopyrightText: 2026 Hasan Melih Akbulut
# SPDX-License-Identifier: Apache-2.0
"""Run actual soc_top/Ibex, raw SRAM MBIST and post-test ECC boot on native models."""

import argparse
import hashlib
import json
from pathlib import Path
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "hw/soc/flow"))
from gen_logic_boot_rom import generate


def run(command, output, timeout=180):
    with output.open("w") as stream:
        result = subprocess.run(
            list(map(str, command)),
            cwd=ROOT,
            stdout=stream,
            stderr=subprocess.STDOUT,
            timeout=timeout,
        )
    if result.returncode:
        raise RuntimeError(f"Command failed ({result.returncode}): {output}")


def passed_log(text):
    """A verdict cannot hide an error after $finish in the same time slot."""
    import re

    return (
        "PASS " in text
        and re.search(
            r"(?im)(?:%Fatal|%Error|\bFATAL:|\bERROR:|Assertion failed)", text
        )
        is None
    )


def pipeline_log_matches(text, core_req_reg, core_wb_stage, rf_synpre=1):
    """Require the elaborated DUT configuration, not just a requested CLI flag."""
    import re

    pipeline = re.findall(
        r"(?m)^PIPELINE core_req_reg=([01]) core_wb_stage=([01]) branch_target_alu=([01])$",
        text,
    )
    return (
        pipeline == [(str(core_req_reg), str(core_wb_stage), str(core_wb_stage))]
        and re.findall(r"(?m)^RF_SYNPRE=([01])$", text) == [str(rf_synpre)]
        and len(re.findall(r"(?m)^PIPELINE\b.*$", text)) == 1
        and len(re.findall(r"(?m)^RF_SYNPRE=.*$", text)) == 1
    )


def main():
    from check_soc_lint import physical_regfile, sources

    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--pdk", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    suite = ROOT / "hw/soc/tools/oss-cad-suite/bin"
    parser.add_argument("--iverilog", type=Path, default=suite / "iverilog")
    parser.add_argument("--vvp", type=Path, default=suite / "vvp")
    parser.add_argument(
        "--simulator", choices=("iverilog", "verilator"), default="iverilog"
    )
    parser.add_argument("--profile", choices=("base", "full"), default="base")
    parser.add_argument("--eth-mbist", action="store_true", help="Include both physical Ethernet FIFO MBISTs")
    parser.add_argument("--core-req-reg", type=int, choices=(0, 1), default=0)
    parser.add_argument("--core-wb-stage", type=int, choices=(0, 1), default=0)
    parser.add_argument("--rf-synpre", type=int, choices=(0, 1), default=1,
                        help="Match the physical SYNPRE=1 profile; 0 is a separate control")
    args = parser.parse_args()
    out = args.output.resolve()
    if not out.is_relative_to(ROOT / "hw/soc/out"):
        parser.error("Output must be inside hw/soc/out")
    out.mkdir(parents=True, exist_ok=False)
    version = subprocess.check_output(
        [str(args.iverilog), "-V"], stderr=subprocess.DEVNULL, text=True
    )
    import re

    match = re.search(r"Icarus Verilog version (\d+)", version)
    if not match or int(match[1]) < 13:
        parser.error("Native models require Icarus >=13")
    (out / "iverilog-version.log").write_text(version)
    files, define, _ = sources(args.profile)
    soc = ROOT / "hw/soc"
    regfile_source = soc / "rtl/ibex_regfile_secded.v"
    if args.rf_synpre:
        regfile_copy = out / "ibex_regfile_secded.v"
        regfile_copy.write_text(physical_regfile(regfile_source.read_text()))
        if files.count(regfile_source) != 1:
            raise ValueError("Expected exactly one SECDED register file")
        files = [regfile_copy if p == regfile_source else p for p in files]
    asm = soc / "tb/sw/mbist_boot.S"
    gcc = soc / "tools/rvgcc/bin/riscv-none-elf-gcc"
    objcopy = gcc.with_name("riscv-none-elf-objcopy")
    run(
        [
            gcc,
            "-march=rv32i",
            "-mabi=ilp32",
            "-nostdlib",
            "-nostartfiles",
            "-Wl,-Ttext=0xc0000080",
            "-Wl,--entry=_start",
            asm,
            "-o",
            out / "boot.elf",
        ],
        out / "gcc.log",
    )
    run(
        [objcopy, "-O", "binary", out / "boot.elf", out / "boot.bin"],
        out / "objcopy.log",
    )
    generate(out / "boot.bin", out / "rom")
    files = [soc / "rtl/soc_mem_sram.v" if p.name == "soc_mem.v" else p for p in files]
    files += sorted((soc / "rtl/dft").glob("*.v"))
    files += [out / "rom/soc_logic_boot_rom.v", soc / "tb/tb_soc_mbist_integration.v"]
    models = args.pdk.resolve() / "libs.ref/sg13g2_sram/verilog"
    files += [
        models / name
        for name in (
            "RM_IHPSG13_1P_core_behavioral_bm_bist.v",
            "RM_IHPSG13_1P_2048x64_c2_bm_bist.v",
        )
    ]
    if args.eth_mbist:
        files += [models / name for name in (
            "RM_IHPSG13_2P_256x16_c2_bm_bist.v",
            "RM_IHPSG13_2P_core_behavioral_bm_bist_ideal.v",
            "RM_IHPSG13_2P_core_behavioral_ideal.v")]
    sha = lambda p: hashlib.sha256(p.read_bytes()).hexdigest()
    tracked = files + [
        regfile_source,
        asm,
        Path(__file__).resolve(),
        gcc,
        objcopy,
        ROOT / "scripts/check_soc_lint.py",
        ROOT / "hw/soc/flow/gen_logic_boot_rom.py",
        ROOT / "hw/soc/rtl/soc_logic_boot_rom.v.in",
        ROOT / "sw/golden/secded.py",
        ROOT / "hw/soc/flow/ibex_sources.sh",
        ROOT / "hw/soc/flow/interface_profile.py",
        ROOT / "hw/soc/rtl/soc_memmap.vh",
        args.iverilog,
        args.vvp,
    ]
    pins = {str(p): sha(p) for p in tracked}
    result = dict(
        passed=False,
        scope="Actual soc_top RAM MBIST and Ibex ECC boot; functional native models, no layout claim",
        profile=args.profile,
        eth_mbist=args.eth_mbist,
        core_req_reg=args.core_req_reg,
        core_wb_stage=args.core_wb_stage,
        rf_synpre=args.rf_synpre,
        simulator=args.simulator,
        input_sha256=pins,
        cases=[],
    )
    try:
        command = [
            str(args.iverilog),
            "-g2012",
            "-DFUNCTIONAL",
            "-DSG13G2_ICG_BEHAVIOURAL",
            "-DSOC_SRAM_MBIST",
            "-DSOC_LOGIC_BOOT_ROM",
            "-I" + str(soc / "rtl"),
            "-I" + str(ROOT / "hw/rtl"),
            "-s",
            "tb_soc_mbist_integration",
            "-o",
            str(out / "run.vvp"),
            f"-Ptb_soc_mbist_integration.CORE_REQ_REG={args.core_req_reg}",
            f"-Ptb_soc_mbist_integration.CORE_WB_STAGE={args.core_wb_stage}",
        ]
        if args.eth_mbist:
            command.append("-DSOC_ETH_MBIST")
        if define:
            command.append(define)
        executable = [args.vvp, out / "run.vvp"]
        if args.simulator == "verilator":
            verilator = suite / "verilator"
            defines = [x for x in command if x.startswith(("-D", "-I"))]
            command = [
                str(verilator),
                "--binary",
                "--timing",
                "-Wno-fatal",
                "-j",
                "2",
                "--top-module",
                "tb_soc_mbist_integration",
                "--Mdir",
                str(out / "obj_dir"),
                f"-GCORE_REQ_REG={args.core_req_reg}",
                f"-GCORE_WB_STAGE={args.core_wb_stage}",
                *defines,
            ]
            executable = [out / "obj_dir/Vtb_soc_mbist_integration"]
            pins[str(verilator)] = sha(verilator)
        result["compile_command"] = list(map(str, command + files))
        run(command + files, out / "compile.log", timeout=600)
        cases = [
            ("success", []),
            ("por-restart", ["+restart=1"]),
            ("illegal-state", ["+illegal=1"]),
        ] + [(f"fault-bank-{bank}", [f"+fault_bank={bank}"]) for bank in range(4)]
        if args.eth_mbist:
            cases += [("eth-fault-tx", ["+ethfault=0"]), ("eth-fault-rx", ["+ethfault=1"]),
                      ("eth-missing-clock", ["+ethstall=1"])]
        for name, plus in cases:
            log = out / (name + ".log")
            run([*executable, *plus], log, timeout=1800)
            if not passed_log(log.read_text()):
                raise RuntimeError("Missing pass or error in test log: " + name)
            if not pipeline_log_matches(log.read_text(), args.core_req_reg, args.core_wb_stage,
                                        args.rf_synpre):
                raise RuntimeError("Elaborated pipeline configuration mismatch: " + name)
            result["cases"].append(dict(name=name, passed=True, log_sha256=sha(log)))
        result["sources_unchanged"] = all(sha(Path(p)) == h for p, h in pins.items())
        result["passed"] = result["sources_unchanged"] and len(result["cases"]) == len(cases)
    finally:
        (out / "result.json").write_text(json.dumps(result, indent=2) + "\n")
    return 0 if result["passed"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
