#!/usr/bin/env python3
# SPDX-FileCopyrightText: 2026 Hasan Melih Akbulut
# SPDX-License-Identifier: Apache-2.0
"""Run the recovered x4 SDS deskew composition with exact raw-port controls."""

import argparse
import ast
import gzip
import hashlib
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
from cocotb_results import count_results

ROOT = Path(__file__).resolve().parents[1]
TOP = "soc_pcie_gen3_recovered_events_v2"


def interrupted(signum, frame):
    raise KeyboardInterrupt("External process signal " + str(signum))


def main():
    signal.signal(signal.SIGTERM, interrupted)
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--out", type=Path, required=True)
    p.add_argument("--rtl", type=Path)
    p.add_argument("--depth", type=int, default=32)
    p.add_argument("--test")
    p.add_argument("--iverilog-dir", type=Path, required=True)
    a = p.parse_args()
    out = a.out.resolve()
    if out.exists():
        p.error("Fresh output directory required")
    rtl = (a.rtl or ROOT / "hw/soc/rtl/pcie" / (TOP + ".v")).resolve()
    bench = ROOT / "hw/soc/tb/cocotb" / ("test_" + TOP + ".py")
    make = bench.with_name("Makefile." + TOP)
    cases = [
        n.name
        for n in ast.parse(bench.read_text()).body
        if isinstance(n, ast.AsyncFunctionDef) and n.decorator_list
    ]
    if a.test and a.test not in cases:
        p.error("Unknown actual port test")
    vendor = ROOT / "hw/soc/ext/verilog-ethernet/lib/axis/rtl/axis_async_fifo.v"
    if pin(vendor)["sha256"] != "339734a7984d7d540451c92f0831495837c451d170ba60dfbd59f851b28f4250":
        p.error("Pinned existing Ethernet vendor FIFO changed")
    rtls = [rtl, ROOT / "hw/soc/rtl/pcie/soc_pcie_gen3_recovered_x4_v4.v", ROOT / "hw/soc/rtl/pcie/soc_pcie_gen3_framer_rx_owned_v3.v", ROOT / "hw/soc/rtl/pcie/soc_pcie_gen3_recovered_owned_rx_v1.v", ROOT / "hw/soc/rtl/pcie/soc_pcie_gen3_dllp_consumer_v6.v", ROOT / "hw/soc/rtl/pcie/soc_pcie_gen3_lane_align_v3.v", ROOT / "hw/soc/rtl/pcie/soc_pcie_gen3_block_cdc_v1.v", ROOT / "hw/soc/rtl/pcie/soc_pcie_gen3_sds_deskew_v2.v", ROOT / "hw/soc/rtl/pcie/soc_pcie_gen3_record_descrambler_v1.v", vendor]
    files = [*rtls, ROOT / "hw/soc/tb/cocotb/test_soc_pcie_gen3_recovered_x4_v3.py", ROOT / "hw/soc/tb/cocotb/test_soc_pcie_gen3_continuous_rx_integrity_v4.py", ROOT / "hw/soc/tb/cocotb/test_soc_pcie_gen3_dllp_consumer_v6.py", bench, make, Path(__file__), ROOT / "scripts/check_pcie_integrity.py", ROOT / "scripts/cocotb_results.py"]
    before = {str(f.resolve()): pin(f) for f in files}
    tools = {
        str((a.iverilog_dir / n).resolve()): pin((a.iverilog_dir / n).resolve())
        for n in ("iverilog", "vvp")
    }
    if shutil.disk_usage("/dev/shm").free < 1024**3:
        p.error("Shared1GiB entry floor")
    out.mkdir(parents=True)
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
        allowed_cpu_affinity=sorted(os.sched_getaffinity(0)),
        inputs=before,
        runtime=tools,
        exact_test=a.test,
        expected_tests=1 if a.test else len(cases),
        native_cells=False,
        scope="Four raw recovered lanes through local SDS lock, CDC and bounded common-clock DATA ordinal deskew. OS-aware DATA descrambling, lossless SKP sideband/state/parity diagnostics; parser-context EDS/strict normal SKP cohorts, CRC-qualified owned packets and ordered DLLP events; no full LTSSM, physical CDC qualification or complete PCIe claim.",
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
        "DEPTH=" + str(a.depth),
    ]
    r["depth"] = a.depth
    r["ram_entries"] = a.depth
    r["prefetch_entries"] = 2
    r["argv"] = command
    save()
    child = None
    try:
        with (out / "simulation.log").open("x") as log:
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
                while child.poll() is None:
                    if shutil.disk_usage("/dev/shm").free < 528 * 1024**2:
                        raise RuntimeError("Shared528MiB storage floor")
                    time.sleep(0.1)
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
        r["returncode"] = child.wait()
        if child.returncode:
            raise RuntimeError("Actual RTL simulation failed")
        counts = dict(
            zip(("passed", "failed", "skipped"), count_results([out / "results.xml"]))
        )
        r["tests"] = counts
        if "Unexpected sys.executable" in (out / "simulation.log").read_text():
            raise RuntimeError("Embedded Python identity mismatch")
        expected_skipped = len(cases) - 1 if a.test else 0
        if counts != dict(passed=r["expected_tests"], failed=0, skipped=expected_skipped):
            raise RuntimeError("Wrong actual test disposition/count")
        executed = [x.attrib.get("name") for x in ET.parse(out / "results.xml").getroot().iter("testcase") if x.find("skipped") is None]
        if sorted(executed) != sorted([a.test] if a.test else cases):
            raise RuntimeError("Wrong actual selected test identity")
        if any(pin(Path(f)) != v for f, v in before.items()):
            raise RuntimeError("Source changed during simulation")
        if any(pin(Path(f)) != v for f, v in tools.items()):
            raise RuntimeError("Simulator runtime changed")
        r["status"] = "PASS_ACTUAL_RECOVERED_X4_RTL"
    except BaseException as error:
        r.update(status="FAIL", error=repr(error))
        raise
    finally:
        capture_error = None
        # The child has been reaped above. Retain its exact compiled program
        # losslessly without keeping multiple uncompressed copies in shared RAM.
        vvp = out / "sim/sim.vvp"
        if vvp.is_file():
            try:
                raw_pin = pin(vvp)
                compressed = vvp.with_suffix(".vvp.gz")
                with vvp.open("rb") as src, gzip.open(compressed, "xb", compresslevel=1) as dst:
                    shutil.copyfileobj(src, dst, 1024**2)
                size = 0
                digest = hashlib.sha256()
                with gzip.open(compressed, "rb") as src:
                    while chunk := src.read(1024**2):
                        size += len(chunk)
                        digest.update(chunk)
                if {"bytes": size, "sha256": digest.hexdigest()} != raw_pin or pin(vvp) != raw_pin:
                    raise RuntimeError("Compiled program gzip readback changed bytes")
                r["compiled_program"] = {"raw": raw_pin, "gzip": pin(compressed), "full_readback": True}
                vvp.unlink()
            except BaseException as error:
                capture_error = error
                r.update(status="FAIL", capture_error=repr(error))
        r["outputs"] = {
            str(f.relative_to(out)): pin(f)
            for f in out.rglob("*")
            if f.is_file() and f.name not in ("result.json", "result.tmp")
        }
        save()
        if capture_error is not None:
            raise capture_error


if __name__ == "__main__":
    main()
