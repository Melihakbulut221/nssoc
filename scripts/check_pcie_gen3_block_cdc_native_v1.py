#!/usr/bin/env python3
# SPDX-FileCopyrightText: 2026 Hasan Melih Akbulut
# SPDX-License-Identifier: Apache-2.0
"""Map frozen complete-block CDC/FIFO to IHP cells and replay seven port cases."""

import argparse
import ast
from collections import Counter
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
import xml.etree.ElementTree as ET

from check_pcie_integrity import pin
from check_pcie_integrity_native import LIB_SHA, MODEL_SHA, quote
from cocotb_results import count_results

ROOT = Path(__file__).resolve().parents[1]
TOP = "soc_pcie_gen3_block_cdc_v1"
ABC_RECIPE = "strash; balance -x; &get -n; &nf; &put\n"
ENTRY_BYTES = 1024**3
FLOOR_BYTES = 528 * 1024**2
AS_BYTES = 2 * 1024**3
FROZEN = {
    "hw/soc/rtl/pcie/soc_pcie_gen3_block_cdc_v1.v": "9022c0f0479a52fdd928dcad574c11b0b4405412ca9f8f93f015793e7930d735",
    "hw/soc/ext/verilog-ethernet/lib/axis/rtl/axis_async_fifo.v": "339734a7984d7d540451c92f0831495837c451d170ba60dfbd59f851b28f4250",
    "scripts/check_pcie_gen3_block_cdc_v1.py": "f8201a9fdfc9da0135c79c79e85a01b2ef5c2560f59c9a1eaf8fc6d08a9aca43",
    "hw/soc/tb/cocotb/test_soc_pcie_gen3_block_cdc_v1.py": "232ddf45d651b7299f57afae0710ee1c81aad1b4ec5d37e03edffd2e60225c44",
    "hw/soc/tb/cocotb/Makefile.soc_pcie_gen3_block_cdc_v1": "8f561225f6224c3ebad1a7b020d749772ddf29aea02599715a032004c42ae036",
    "sw/tests/test_pcie_gen3_block_cdc_v1.py": "e6771923820e544cb7d5ec20f57485051ee0b0376261aa8bd069d20a8e693f3f",
    "sw/tests/test_pcie_gen3_block_cdc_v1_lifecycle.py": "578f1067917b04ad12c9fc9a6b96d327ff983015020b0500461dfbd7b81d2bff",
}
CASES = (
    "asynchronous_metadata_and_drift",
    "fast_reader_full_rate_and_many_wraps",
    "held_output_and_bounded_pressure",
    "exact_ram_prefetch_capacity_overflow_and_restart",
    "either_domain_reset_with_held_output",
    "stopped_clock_reset_and_restart",
    "alignment_loss_and_illegal_length_fail_closed",
)


def interrupted(signum, frame):
    raise KeyboardInterrupt("External process signal " + str(signum))


def check_sources():
    for name, digest in FROZEN.items():
        if pin(ROOT / name)["sha256"] != digest:
            raise RuntimeError("Frozen complete-block source changed: " + name)
    bench = ROOT / "hw/soc/tb/cocotb" / ("test_" + TOP + ".py")
    cases = tuple(
        n.name
        for n in ast.parse(bench.read_text()).body
        if isinstance(n, ast.AsyncFunctionDef) and n.decorator_list
    )
    if cases != CASES:
        raise RuntimeError("Frozen seven-case public oracle changed")


def child_limits():
    resource.setrlimit(resource.RLIMIT_AS, (AS_BYTES, AS_BYTES))
    resource.setrlimit(resource.RLIMIT_CORE, (0, 0))
    os.sched_setaffinity(0, {min(os.sched_getaffinity(0))})


def stop_group(child):
    # Failure/cancellation only. Always kill the whole group even when the
    # leader exits during TERM grace, and reap despite diagnostic I/O errors.
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
        finally:
            child.wait()


def execute(command, log_path, out, env, record, save):
    start = time.monotonic()
    minimum = shutil.disk_usage("/dev/shm").free
    child = None
    try:
        with log_path.open("x") as log:
            child = subprocess.Popen(
                command,
                cwd=out,
                env=env,
                stdout=log,
                stderr=subprocess.STDOUT,
                start_new_session=True,
                preexec_fn=child_limits,
            )
            record["active_group"] = child.pid
            save()
            while child.poll() is None:
                free = shutil.disk_usage("/dev/shm").free
                minimum = min(minimum, free)
                if free < FLOOR_BYTES:
                    raise RuntimeError("Shared528MiB storage floor")
                time.sleep(0.1)
            code = child.wait()
        record["commands"].append(
            dict(
                argv=command,
                returncode=code,
                elapsed_s=time.monotonic() - start,
                min_free_bytes=minimum,
                log=log_path.name,
            )
        )
        record["active_group"] = None
        save()
        if code:
            raise RuntimeError("Native phase failed: " + log_path.name)
    except BaseException:
        if child is not None:
            stop_group(child)
        raise


def verify_tests(path):
    counts = dict(zip(("passed", "failed", "skipped"), count_results([path])))
    names = [n.attrib.get("name") for n in ET.parse(path).getroot().iter("testcase")]
    if counts != dict(passed=7, failed=0, skipped=0) or sorted(names) != sorted(CASES):
        raise RuntimeError("Require every exact frozen native case, without skips")
    return counts


def map_script(out, liberty):
    rtl = ROOT / "hw/soc/rtl/pcie" / (TOP + ".v")
    vendor = ROOT / "hw/soc/ext/verilog-ethernet/lib/axis/rtl/axis_async_fifo.v"
    return (
        "read_liberty -lib "
        + quote(liberty)
        + "; read_verilog -sv "
        + quote(rtl)
        + " "
        + quote(vendor)
        + "; hierarchy -check -top "
        + TOP
        + "; flatten -noscopeinfo; synth -top "
        + TOP
        + " -nofsm -noabc"
        + "; dfflibmap -liberty "
        + quote(liberty)
        + "; abc -script "
        + quote(out / "abc.script")
        + " -liberty "
        + quote(liberty)
        + "; clean; check -assert; stat -liberty "
        + quote(liberty)
        + "; write_json "
        + quote(out / "mapped.json")
        + "; write_verilog -noattr -noexpr "
        + quote(out / "mapped.v")
        + "\n"
    )


def main():
    signal.signal(signal.SIGTERM, interrupted)
    signal.signal(signal.SIGINT, interrupted)
    p = argparse.ArgumentParser(description=__doc__)
    for name in ("out", "tools", "liberty", "models"):
        p.add_argument("--" + name, type=Path, required=True)
    a = p.parse_args()
    out, tools, liberty, models = (
        getattr(a, k).resolve() for k in ("out", "tools", "liberty", "models")
    )
    if out.exists():
        p.error("Fresh output directory required")
    check_sources()
    if pin(liberty)["sha256"] != LIB_SHA or pin(models)["sha256"] != MODEL_SHA:
        p.error("Require pinned c4 SG13 library and native cell models")
    entry = shutil.disk_usage("/dev/shm").free
    if entry < ENTRY_BYTES:
        p.error("Native entry requires1GiB free")
    oss = tools.parent
    runtime_files = [tools / n for n in ("yosys", "yosys-abc", "iverilog", "vvp")]
    runtime_files += [
        oss / "libexec" / n
        for n in ("yosys", "yosys-abc", "iverilog", "ivl", "ivlpp", "vvp")
    ]
    runtime_files += [oss / "lib/ld-linux-x86-64.so.2"]
    runtime_files += list((oss / "lib/ivl").glob("*.tgt"))
    runtime_files += list((oss / "lib/ivl").glob("*.vpi"))
    interpreter = ROOT / "hw/soc/tools/cocotb-venv/bin/python3"
    runtime_files += [interpreter.resolve()]
    runtime = {str(f): pin(f) for f in runtime_files}
    files = [ROOT / f for f in FROZEN]
    files += [
        Path(__file__).resolve(),
        ROOT / "scripts/check_pcie_integrity.py",
        ROOT / "scripts/check_pcie_integrity_native.py",
        ROOT / "scripts/cocotb_results.py",
        ROOT / "sw/tests/test_pcie_gen3_block_cdc_native_v1.py",
        liberty,
        models,
    ]
    before = {str(f): pin(f) for f in files}
    out.mkdir(parents=True)
    launchers = out / "runtime"
    launchers.mkdir()
    compiler = launchers / "iverilog"
    compiler.write_text(
        "#!/bin/sh\nexec " + shlex.quote(str(tools / "iverilog")) + ' "$@"\n'
    )
    loader = [
        str(oss / "lib/ld-linux-x86-64.so.2"),
        "--inhibit-cache",
        "--inhibit-rpath",
        "",
        "--library-path",
        str(oss / "lib"),
        str(oss / "libexec/vvp"),
    ]
    vvp = launchers / "vvp"
    vvp.write_text(
        "#!/bin/sh\nexec env -u PYTHONHOME -u PYTHONEXECUTABLE "
        + " ".join(shlex.quote(x) for x in loader)
        + ' "$@"\n'
    )
    for f in (compiler, vvp):
        f.chmod(0o755)
        before[str(f)] = pin(f)
    env = dict(os.environ)
    for key in (
        "PYTHONPATH",
        "PYTHONHOME",
        "PYTHONEXECUTABLE",
        "COCOTB_TEST_FILTER",
        "COCOTB_TESTCASE",
    ):
        env.pop(key, None)
    env.update(
        YOSYS_MAX_THREADS="1",
        OMP_NUM_THREADS="1",
        OPENBLAS_NUM_THREADS="1",
        PYTHONDONTWRITEBYTECODE="1",
    )
    env["PATH"] = os.pathsep.join(
        [str(interpreter.parent), str(launchers), env.get("PATH", "")]
    )
    record = dict(
        status="RUNNING",
        inputs=before,
        runtime=runtime,
        top=TOP,
        depth=32,
        ram_entries=32,
        prefetch_entries=2,
        expected_cases=list(CASES),
        commands=[],
        native_cells=True,
        entry_free_bytes=entry,
        mapping_recipe=ABC_RECIPE.strip(),
        resource_contract=dict(
            address_space=AS_BYTES,
            one_cpu=True,
            core_bytes=0,
            entry_shm_bytes=ENTRY_BYTES,
            continuous_shm_bytes=FLOOR_BYTES,
            elapsed_watchdog=False,
        ),
        scope="Finite gate-level digital functionality, default DEPTH32. No SDF, physical Gray-bus/reset constraints, metastability/MTBF, routed CDC qualification, SKP rate compensation, deskew or complete PCIe claim.",
    )

    def save():
        temp = out / "result.tmp"
        temp.write_text(json.dumps(record, indent=2) + "\n")
        temp.replace(out / "result.json")

    try:
        save()
        execute(
            [str(tools / "iverilog"), "-V"],
            out / "iverilog-version.txt",
            out,
            env,
            record,
            save,
        )
        version = (out / "iverilog-version.txt").read_text()
        match = re.search(r"Icarus Verilog version (\d+)", version)
        if not match or int(match[1]) < 13:
            raise RuntimeError("Native delayed cell ports require Icarus13 or later")
        (out / "abc.script").write_text(ABC_RECIPE)
        (out / "map.ys").write_text(map_script(out, liberty))
        execute(
            [str(tools / "yosys"), "-Q", "-T", "-s", str(out / "map.ys")],
            out / "map.log",
            out,
            env,
            record,
            save,
        )
        cells = json.loads((out / "mapped.json").read_text())["modules"][TOP]["cells"]
        if not cells or any(
            not c["type"].startswith("sg13g2_") for c in cells.values()
        ):
            raise RuntimeError("Unimplemented/non-IHP cells remain")
        record["mapped_cells"] = len(cells)
        record["cell_types"] = dict(
            sorted(Counter(c["type"] for c in cells.values()).items())
        )
        generated = {
            str(out / n): pin(out / n)
            for n in ("map.ys", "abc.script", "mapped.v", "mapped.json")
        }
        record["mapped_inputs"] = generated
        save()
        make = ROOT / "hw/soc/tb/cocotb" / ("Makefile." + TOP)
        command = [
            "make",
            "-f",
            str(make),
            "VERILOG_SOURCES=" + str(out / "mapped.v") + " " + str(models),
            "SIM_BUILD=" + str(out / "sim"),
            "COCOTB_RESULTS_FILE=" + str(out / "results.xml"),
            "DEPTH=32",
            "COMPILE_ARGS=-g2012 -gspecify -f " + str(out / "sim/cmds.f"),
        ]
        execute(command, out / "simulation.log", out, env, record, save)
        record["tests"] = verify_tests(out / "results.xml")
        if "Unexpected sys.executable" in (out / "simulation.log").read_text():
            raise RuntimeError("Embedded interpreter mismatch")
        for path, value in {**before, **runtime, **generated}.items():
            if pin(Path(path)) != value:
                raise RuntimeError("Native input drift: " + path)
        record["status"] = "PASS_NATIVE_IHP_COMPLETE_BLOCK_CDC_FINITE"
    except BaseException as error:
        record.update(status="FAIL", error=repr(error))
        raise
    finally:
        record["outputs"] = {
            str(f.relative_to(out)): pin(f)
            for f in out.rglob("*")
            if f.is_file() and f.name not in ("result.json", "result.tmp")
        }
        save()


if __name__ == "__main__":
    main()
