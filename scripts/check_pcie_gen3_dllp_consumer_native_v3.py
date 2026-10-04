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
TOP = "soc_pcie_gen3_dllp_consumer_v3"
ABC_RECIPE = "strash; balance -x; &get -n; &nf; &put\n"

FROZEN_SOURCES = {
    "hw/soc/rtl/pcie/soc_pcie_gen3_dllp_consumer_v3.v": "687fb805da42cc08a1b44ab373783cf26ec22d80be6c441489cd8d3a3573b7bd",
    "hw/soc/rtl/pcie/soc_pcie_gen3_rx_events_v3.v": "1a0c57ec3499843325d1903070a0c92e4dd409ab400c9f54f324975cbfc25580",
    "scripts/check_pcie_gen3_dllp_consumer_v3.py": "4978b91b2392d05325288fcfaa4dad6ab83be832b30df289547d0d3e21a96f0d",
    "sw/tests/test_pcie_gen3_dllp_consumer_v3.py": "f9db99b4e86d14823f797e3eeea03c69617c02d4f42b56e359e2c547d0391532",
    "sw/tests/test_pcie_gen3_dllp_consumer_lifecycle_v3.py": "6fc4671fa38f9e21645c0d5db196af63a22e80b040c40d6d3956df9620567fc4",
    "hw/soc/tb/cocotb/test_soc_pcie_gen3_dllp_consumer_v3.py": "8c742770e115570767a78e5d1709c32705c6973558d90ec3ee834997cc57b401",
    "hw/soc/tb/cocotb/test_soc_pcie_gen3_rx_events_v3.py": "f8f3c0884652c17a4547d05db284ac3a42d0bea50614557464e4d29177908467",
    "hw/soc/tb/cocotb/Makefile.soc_pcie_gen3_dllp_consumer_v3": "81427becfb9f35f0aeea364878d24a008a218d2bc1a9cdd6c2216acda6f3be4e",
    "hw/soc/tb/cocotb/Makefile.soc_pcie_gen3_rx_events_v3": "9e8a8221da73df82ab0044ca7fe3b8a89716bf7acd2b725d5c80ec2bf4ee2498",
    "hw/soc/rtl/pcie/soc_pcie_gen3_ingress.v": "d34847efb81b7f6afc77d7165e0c5eb451656e10aaae73465355342d0f0505d2",
    "hw/soc/rtl/pcie/soc_pcie_gen3_data_descrambler.v": "081764c8fb0172cfe4f562a21afcf8e60dd631c4feb1f6e6a178e6379c2723d7",
    "hw/soc/rtl/pcie/soc_pcie_gen3_framer_rx_owned_v2.v": "a0e3dfe6f87d2ac538b44af34793e48813fb0c59692454b31ccff7bdf7ed288c",
    "hw/soc/rtl/pcie/soc_pcie_gen3_continuous_rx_owned_v2.v": "697bb3f119cb0b7b0f005de62be937054750eda7aaca330582678bd1f32559b7",
    "scripts/check_pcie_integrity.py": "b926f798ba26c02cbd8459350669adf770653ac89a962c106a0a55db916fcd5d",
    "scripts/cocotb_results.py": "f67fa5d00f0752557bfe9b30e998c64fe054746d948fd32f53365ba5e13012f2",
    "hw/soc/tb/cocotb/test_soc_pcie_gen3_continuous_rx_owned_v2.py": "f6ff16859c9f55572849989327663e0aaccc8ba4f702717edf2fccb58d611bcd",
    "scripts/check_pcie_gen3_dllp_consumer_compare_v3.py": "e56e0c82d1272729de7fb7955049a6f54860db5ee67ae868cbbadcc81f1c26f3",
    "sw/tests/test_pcie_gen3_dllp_consumer_compare_v3.py": "71c31c4b220a709b09c7534e151a23988a119e70f0739d96cbeb1d7e7b0ca9df",
    "hw/soc/tb/soc_pcie_gen3_dllp_consumer_compare_v3.v": "7ee4d18a280331740a8dfbbdd190275dd81b6ad82a11ad1f0cb832d373db2cd5",
    "hw/soc/tb/cocotb/test_soc_pcie_gen3_dllp_consumer_compare_v3.py": "3722da8b7eb15b1f6d442d9a34b613588650aa6cba0d739263cbbc49f10924c4",
    "hw/soc/tb/cocotb/Makefile.soc_pcie_gen3_dllp_consumer_compare_v3": "528c7fa07e829f008a05b0a2e7d0b05f58231bfb67bd95d019b4a7a71ce4a819",
    "hw/soc/rtl/pcie/soc_pcie_gen3_dllp_consumer_v1.v": "e1a19382c2f446f0754b43818bdf497821ac3c34c7087caa1e9bcfb83e247483",
    "hw/soc/rtl/pcie/soc_pcie_gen3_dllp_consumer_v2.v": "eb4f3146ed1b8c142cf5784f44dc773353973edff94a7256c82d2b235bb5d224",
    "sw/tests/test_pcie_gen3_dllp_consumer_arithmetic_v3.py": "7587db1970d4b4bf610c3d59c9fcc3c6aed3d52bd5b0e94e8c13a5253b547420"
}


def interrupted(signum, frame):
    raise KeyboardInterrupt("External process signal " + str(signum))


def main():
    signal.signal(signal.SIGTERM, interrupted)
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--out", type=Path, required=True)
    p.add_argument("--rtl", type=Path)
    p.add_argument("--wrapper-rtl", type=Path)
    p.add_argument("--top", choices=(TOP, "soc_pcie_gen3_rx_events_v3"), default=TOP)
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
                a.wrapper_rtl or ROOT / "hw/soc/rtl/pcie/soc_pcie_gen3_rx_events_v3.v"
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
                "test_soc_pcie_gen3_dllp_consumer_v3.py",
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
