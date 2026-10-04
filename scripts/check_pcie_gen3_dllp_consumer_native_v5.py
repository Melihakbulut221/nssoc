#!/usr/bin/env python3
# SPDX-FileCopyrightText: 2026 Hasan Melih Akbulut
# SPDX-License-Identifier: Apache-2.0
"""Additive pinned balance-XOR IHP mapping and frozen wide consumer port replay."""

import argparse
import ast
import json
import os
from pathlib import Path
import re
import resource
import shlex
import shutil
import signal
import subprocess
import time

from check_pcie_integrity import pin
from check_pcie_integrity_native import LIB_SHA, MODEL_SHA, quote
from cocotb_results import count_results

ROOT = Path(__file__).resolve().parents[1]
TOP = "soc_pcie_gen3_dllp_consumer_v5"
ABC_RECIPE = "strash; balance -x; &get -n; &nf; &put\n"

FROZEN_SOURCES = {
    "hw/soc/rtl/pcie/soc_pcie_gen3_dllp_consumer_v5.v": "734cce5b4b37b5d1f8ec4751deecdd3fda8934e32dbc1b7570b2ee2492cd72b4",
    "hw/soc/rtl/pcie/soc_pcie_gen3_rx_events_v5.v": "776d3748a2e18bf43d164688e042da3c8088c1aa0dc3b9fcfaa79133c5a47970",
    "scripts/check_pcie_gen3_dllp_consumer_v5.py": "9dae27c52b84cf7dda925c015cdb5eca9f602f61458ee78d03f672d3d062b5c7",
    "sw/tests/test_pcie_gen3_dllp_consumer_v5.py": "54c595cf319fa15f256776cefaeee0698078bd694e45c32f179fc8feb058bfb5",
    "sw/tests/test_pcie_gen3_dllp_consumer_lifecycle_v5.py": "90058e3a55b8265ba79983815c72b8e0dfe9ddf98bc2aeb8a119290c542a52ba",
    "hw/soc/tb/cocotb/test_soc_pcie_gen3_dllp_consumer_v5.py": "8c742770e115570767a78e5d1709c32705c6973558d90ec3ee834997cc57b401",
    "hw/soc/tb/cocotb/test_soc_pcie_gen3_rx_events_v5.py": "626bcf059b7dfe6623be26e10f159057835bb28a74de93ef5dd6da4f300f0684",
    "hw/soc/tb/cocotb/Makefile.soc_pcie_gen3_dllp_consumer_v5": "60bb2ce5ccf550564c0d7efa603a6330a2fceb335bc5869fb52586d054dab0eb",
    "hw/soc/tb/cocotb/Makefile.soc_pcie_gen3_rx_events_v5": "e1ce1467b6e5c1b3aa492bc44b07873be6117436c2d8c331689dac432ad6c963",
    "hw/soc/rtl/pcie/soc_pcie_gen3_ingress.v": "d34847efb81b7f6afc77d7165e0c5eb451656e10aaae73465355342d0f0505d2",
    "hw/soc/rtl/pcie/soc_pcie_gen3_data_descrambler.v": "081764c8fb0172cfe4f562a21afcf8e60dd631c4feb1f6e6a178e6379c2723d7",
    "hw/soc/rtl/pcie/soc_pcie_gen3_framer_rx_owned_v2.v": "a0e3dfe6f87d2ac538b44af34793e48813fb0c59692454b31ccff7bdf7ed288c",
    "hw/soc/rtl/pcie/soc_pcie_gen3_continuous_rx_owned_v2.v": "697bb3f119cb0b7b0f005de62be937054750eda7aaca330582678bd1f32559b7",
    "scripts/check_pcie_integrity.py": "b926f798ba26c02cbd8459350669adf770653ac89a962c106a0a55db916fcd5d",
    "scripts/cocotb_results.py": "f67fa5d00f0752557bfe9b30e998c64fe054746d948fd32f53365ba5e13012f2",
    "hw/soc/tb/cocotb/test_soc_pcie_gen3_continuous_rx_owned_v2.py": "f6ff16859c9f55572849989327663e0aaccc8ba4f702717edf2fccb58d611bcd",
    "scripts/check_pcie_gen3_dllp_consumer_compare_v5.py": "686f3e53f23b7f0201d97d594c1988a57181ec58b2c3d008bb49034c9ebd58d5",
    "sw/tests/test_pcie_gen3_dllp_consumer_compare_v5.py": "d405832698544a01c12d9e11332a2249790e558289eeffeaf22cc9ee32945c06",
    "hw/soc/tb/soc_pcie_gen3_dllp_consumer_compare_v5.v": "a993dba62f7a9eeaa6750d0b2ab7ace84d22d6d18a8e0547fee36ce0b7171097",
    "hw/soc/tb/cocotb/test_soc_pcie_gen3_dllp_consumer_compare_v5.py": "3722da8b7eb15b1f6d442d9a34b613588650aa6cba0d739263cbbc49f10924c4",
    "hw/soc/tb/cocotb/Makefile.soc_pcie_gen3_dllp_consumer_compare_v5": "400124d8d9e515ebe1eeb86d2622ec4f7e1559c10981e53cb8454982a4b1304e",
    "hw/soc/rtl/pcie/soc_pcie_gen3_dllp_consumer_v1.v": "e1a19382c2f446f0754b43818bdf497821ac3c34c7087caa1e9bcfb83e247483",
    "hw/soc/rtl/pcie/soc_pcie_gen3_dllp_consumer_v2.v": "eb4f3146ed1b8c142cf5784f44dc773353973edff94a7256c82d2b235bb5d224",
    "sw/tests/test_pcie_gen3_dllp_consumer_arithmetic_v5.py": "632c3db5074b3a492525594b18b33a99de541c2633804863f79d335d9f1b53b5",
    "hw/soc/rtl/pcie/soc_pcie_gen3_dllp_consumer_v3.v": "687fb805da42cc08a1b44ab373783cf26ec22d80be6c441489cd8d3a3573b7bd",
    "hw/soc/rtl/pcie/soc_pcie_gen3_dllp_consumer_v4.v": "84603647dd6b8023faccbdb8aba04996d4129147bdf3ad3e3aff94536ceafbd0",
    "scripts/check_pcie_gen3_dllp_consumer_forwarding_v5.py": "eab7e4ba92f3b17faf044b3c01e3b3aa8b301d77134d84968a516be5894d1809",
    "sw/tests/test_pcie_gen3_dllp_consumer_forwarding_v5.py": "d134d3371dd337919255fc05f1db812adac0f7c65e248669b4f396b6751c8f41",
    "hw/soc/tb/soc_pcie_gen3_dllp_consumer_forwarding_v5.v": "ed7a74a3da674ca47ec74b0588386acbc94207839bcb2ec2d3c5cd10c24dd7b5",
    "hw/soc/tb/cocotb/test_soc_pcie_gen3_dllp_consumer_forwarding_v5.py": "8bdf84c9a856764aee8f0786c823bd2236be90d1e26c560f0f4c21080c29b093",
    "hw/soc/tb/cocotb/Makefile.soc_pcie_gen3_dllp_consumer_forwarding_v5": "04ee7b5ac92f70f7babd6b124fc28eb872dabbaa516e965b2c1c4ada238700ba",
    "sw/tests/test_pcie_gen3_dllp_consumer_state_miter_v5.py": "2b24d237b4b85b97a1654421c666f5b5e1eec459d576fac63a4ba6c5647079fb"
}


def interrupted(signum, frame):
    raise KeyboardInterrupt("External process signal " + str(signum))


def main():
    signal.signal(signal.SIGTERM, interrupted)
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--out", type=Path, required=True)
    p.add_argument("--rtl", type=Path)
    p.add_argument("--wrapper-rtl", type=Path)
    p.add_argument("--top", choices=(TOP, "soc_pcie_gen3_rx_events_v5"), default=TOP)
    p.add_argument("--test")
    p.add_argument("--iverilog-dir", type=Path, required=True)
    for name in ("yosys", "liberty", "models"):
        p.add_argument("--" + name, type=Path, required=True)
    a = p.parse_args()
    if a.rtl or a.wrapper_rtl:
        p.error("Native mapping requires unchanged frozen RTL")
    if shutil.disk_usage("/dev/shm").free < 1024**3:
        p.error("Native entry requires1GiB free")
    if pin(a.liberty)["sha256"] != LIB_SHA or pin(a.models)["sha256"] != MODEL_SHA:
        p.error("Require exact unchanged c4 SG13 timing/model files")
    out = a.out.resolve()
    if out.exists():
        p.error("Fresh output directory required")
    if a.wrapper_rtl and a.top == TOP:
        p.error("Wrapper mutation requires wrapper top")
    rtl = (a.rtl or ROOT / "hw/soc/rtl/pcie" / (TOP + ".v")).resolve()
    bench = ROOT / "hw/soc/tb/cocotb" / ("test_" + a.top + ".py")
    make = bench.with_name("Makefile." + a.top)
    cases = [
        n.name
        for n in ast.parse(bench.read_text()).body
        if isinstance(n, ast.AsyncFunctionDef) and n.decorator_list
    ]
    if a.test and a.test not in cases:
        p.error("Unknown actual port test")
    rtls = [rtl]
    if a.top != TOP:
        rtls += [
            ROOT / "hw/soc/rtl/pcie" / (n + ".v")
            for n in (
                "soc_pcie_gen3_ingress",
                "soc_pcie_gen3_data_descrambler",
                "soc_pcie_gen3_framer_rx_owned_v2",
                "soc_pcie_gen3_continuous_rx_owned_v2",
            )
        ]
    if a.top != TOP:
        rtls.append(
            (
                a.wrapper_rtl or ROOT / "hw/soc/rtl/pcie/soc_pcie_gen3_rx_events_v5.v"
            ).resolve()
        )
    files = [
        *rtls,
        bench,
        make,
        Path(__file__),
        ROOT / "scripts/check_pcie_integrity.py",
        ROOT / "scripts/cocotb_results.py",
    ]
    if a.top != TOP:
        files += [
            ROOT / "hw/soc/tb/cocotb" / name
            for name in (
                "test_soc_pcie_gen3_dllp_consumer_v5.py",
                "test_soc_pcie_gen3_continuous_rx_owned_v2.py",
            )
        ]
    files += [
        a.liberty.resolve(),
        a.models.resolve(),
        ROOT / "scripts/check_pcie_integrity_native.py",
    ]
    for name, digest in FROZEN_SOURCES.items():
        f = ROOT / name
        if pin(f)["sha256"] != digest:
            p.error("Frozen positive-source contract changed: " + name)
        files.append(f)
    version = subprocess.check_output(
        [str(a.iverilog_dir.resolve() / "iverilog"), "-V"],
        stderr=subprocess.STDOUT,
        text=True,
    )
    match = re.search(r"Icarus Verilog version (\d+)", version)
    if not match or int(match[1]) < 13:
        p.error("Native delayed cell ports require Icarus13 or later")
    before = {str(f.resolve()): pin(f) for f in files}
    tools = {
        str((a.iverilog_dir / n).resolve()): pin((a.iverilog_dir / n).resolve())
        for n in ("iverilog", "vvp")
    }
    tools[str(a.yosys.resolve())] = pin(a.yosys.resolve())
    out.mkdir(parents=True)
    (out / "iverilog-version.txt").write_text(version)
    selected_tools = a.iverilog_dir.resolve()
    oss = selected_tools.parent
    # OSS's vvp shell wrapper unconditionally points embedded Python at its
    # separate tabbypy tree. Launch the same pinned native binary/loader with
    # the actual cocotb interpreter environment instead; no runtime edits.
    if (oss / "libexec/vvp").is_file() and (oss / "lib/ld-linux-x86-64.so.2").is_file():
        selected_tools = out / "runtime"
        selected_tools.mkdir()
        compiler = selected_tools / "iverilog"
        compiler.write_text(
            "#!/bin/sh\nexec "
            + shlex.quote(str((a.iverilog_dir / "iverilog").resolve()))
            + ' "$@"\n'
        )
        compiler.chmod(0o755)
        before[str(compiler)] = pin(compiler)
        loader, binary = oss / "lib/ld-linux-x86-64.so.2", oss / "libexec/vvp"
        for f in (loader, binary):
            tools[str(f)] = pin(f)
        launcher = selected_tools / "vvp"
        command = [
            str(loader),
            "--inhibit-cache",
            "--inhibit-rpath",
            "",
            "--library-path",
            str(oss / "lib"),
            str(binary),
        ]
        launcher.write_text(
            "#!/bin/sh\nexec env -u PYTHONHOME -u PYTHONEXECUTABLE "
            + " ".join(shlex.quote(x) for x in command)
            + ' "$@"\n'
        )
        launcher.chmod(0o755)
        before[str(launcher)] = pin(launcher)
    r = dict(
        status="RUNNING",
        inputs=before,
        runtime=tools,
        exact_test=a.test,
        expected_tests=1 if a.test else len(cases),
        native_cells=True,
        mapping_recipe=ABC_RECIPE.strip(),
        resource_contract="Independent1GiB entry,528MiB continuous scratch floor,2GiBAS/core0,oneCPU,noelapsedwatchdog",
        scope="Owned integrity boundary; no independent CRC verification, replay/credit policy, physical timing or full PCIe claim.",
    )

    def save():
        tmp = out / "result.tmp"
        tmp.write_text(json.dumps(r, indent=2) + "\n")
        tmp.replace(out / "result.json")

    def limits():
        resource.setrlimit(resource.RLIMIT_AS, (2 * 1024**3, 2 * 1024**3))
        resource.setrlimit(resource.RLIMIT_CORE, (0, 0))

    env = dict(os.environ)
    for key in (
        "PYTHONPATH",
        "PYTHONHOME",
        "PYTHONEXECUTABLE",
        "COCOTB_TEST_FILTER",
        "COCOTB_TESTCASE",
    ):
        env.pop(key, None)
    env["YOSYS_MAX_THREADS"] = "1"
    env["PATH"] = os.pathsep.join(
        [
            str(ROOT / "hw/soc/tools/cocotb-venv/bin"),
            str(selected_tools),
            env.get("PATH", ""),
        ]
    )
    if a.test:
        env["COCOTB_TEST_FILTER"] = "^.*\\." + re.escape(a.test) + "$"
    command = [
        "make",
        "-f",
        str(make),
        "VERILOG_SOURCES=" + " ".join(map(str, rtls)),
        "SIM_BUILD=" + str(out / "sim"),
        "COCOTB_RESULTS_FILE=" + str(out / "results.xml"),
    ]
    r["argv"] = command
    save()
    r["commands"] = []

    def execute(command, log_name):
        start = time.monotonic()
        minimum = shutil.disk_usage("/dev/shm").free
        with (out / log_name).open("x") as log:
            child = subprocess.Popen(
                command,
                cwd=out,
                env=env,
                stdout=log,
                stderr=subprocess.STDOUT,
                start_new_session=True,
                preexec_fn=limits,
            )
            try:
                r["active_group"] = child.pid
                save()
                while child.poll() is None:
                    free = shutil.disk_usage("/dev/shm").free
                    minimum = min(minimum, free)
                    if free < 528 * 1024**2:
                        raise RuntimeError("Shared528MiB storage floor")
                    time.sleep(0.2)
            except BaseException:
                try:
                    try:
                        os.killpg(child.pid, signal.SIGTERM)
                    except ProcessLookupError:
                        pass
                    time.sleep(5)
                finally:
                    try:
                        os.killpg(child.pid, signal.SIGKILL)
                    except ProcessLookupError:
                        pass
                    child.wait()
                raise
        code = child.wait()
        r["commands"].append(
            dict(
                argv=command,
                returncode=code,
                elapsed_s=time.monotonic() - start,
                min_free_bytes=minimum,
            )
        )
        r["active_group"] = None
        save()
        if code:
            raise RuntimeError("Native phase failed: " + log_name)

    try:
        (out / "abc.script").write_text(ABC_RECIPE)
        mapping = (
            "read_liberty -lib "
            + quote(a.liberty.resolve())
            + "; read_verilog -sv "
            + " ".join(map(quote, rtls))
            + "; hierarchy -check -top "
            + a.top
            + "; flatten -noscopeinfo; synth -top "
            + a.top
            + " -nofsm -noabc; dfflibmap -liberty "
            + quote(a.liberty.resolve())
            + "; abc -script "
            + quote(out / "abc.script")
            + " -liberty "
            + quote(a.liberty.resolve())
            + "; clean; check -assert; stat -liberty "
            + quote(a.liberty.resolve())
            + "; write_json "
            + quote(out / "mapped.json")
            + "; write_verilog -noattr -noexpr "
            + quote(out / "mapped.v")
        )
        (out / "map.ys").write_text(mapping + "\n")
        execute(
            [str(a.yosys.resolve()), "-Q", "-T", "-s", str(out / "map.ys")], "map.log"
        )
        cells = json.loads((out / "mapped.json").read_text())["modules"][a.top]["cells"]
        if not cells or any(
            not c["type"].startswith("sg13g2_") for c in cells.values()
        ):
            raise RuntimeError("Unimplemented or non-IHP cells")
        r["mapped_cells"] = len(cells)
        generated = {
            str(out / n): pin(out / n)
            for n in ("mapped.v", "mapped.json", "map.ys", "abc.script")
        }
        r["mapped_inputs"] = generated
        command = [
            "make",
            "-f",
            str(make),
            "VERILOG_SOURCES=" + str(out / "mapped.v") + " " + str(a.models.resolve()),
            "SIM_BUILD=" + str(out / "sim"),
            "COCOTB_RESULTS_FILE=" + str(out / "results.xml"),
            "COMPILE_ARGS=-g2012 -gspecify -f " + str(out / "sim/cmds.f"),
        ]
        execute(command, "simulation.log")
        if any(pin(Path(n)) != v for n, v in generated.items()):
            raise RuntimeError("Mapped replay input drift")
        counts = dict(
            zip(("passed", "failed", "skipped"), count_results([out / "results.xml"]))
        )
        r["tests"] = counts
        if "Unexpected sys.executable" in (out / "simulation.log").read_text():
            raise RuntimeError("Embedded Python identity mismatch")
        if counts["failed"] or counts["passed"] != r["expected_tests"]:
            raise RuntimeError("Wrong actual test disposition/count")
        if any(pin(Path(f)) != v for f, v in before.items()):
            raise RuntimeError("Source changed during simulation")
        if any(pin(Path(f)) != v for f, v in tools.items()):
            raise RuntimeError("Simulator runtime changed")
        r["status"] = "PASS_NATIVE_IHP_WIDE_DLLP_CONSUMER"
    except BaseException as error:
        r.update(status="FAIL", error=repr(error))
        raise
    finally:
        r["outputs"] = {
            str(f.relative_to(out)): pin(f)
            for f in out.rglob("*")
            if f.is_file() and f.name not in ("result.json", "result.tmp")
        }
        save()


if __name__ == "__main__":
    main()
