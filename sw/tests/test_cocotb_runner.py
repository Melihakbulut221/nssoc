# SPDX-FileCopyrightText: 2026 Hasan Melih Akbulut
# SPDX-License-Identifier: Apache-2.0
"""A partial simulator run must not produce a green verification result."""

import importlib.util
import os
from pathlib import Path
import shutil
import signal
import subprocess
import sys
import time

import pytest

ROOT = Path(__file__).resolve().parents[2]
spec = importlib.util.spec_from_file_location("cocotb_results", ROOT / "scripts/cocotb_results.py")
results = importlib.util.module_from_spec(spec)
spec.loader.exec_module(results)


def test_counts_distinguish_failures_and_skips(tmp_path):
    xml = tmp_path / "results with spaces.xml"
    xml.write_text('<testsuites><testsuite><testcase/><testcase><failure/></testcase>'
                   '<testcase><error/></testcase><testcase><skipped/></testcase>'
                   '</testsuite></testsuites>')
    assert results.count_results([xml]) == (1, 2, 1)


@pytest.mark.parametrize("xml", ["<testsuites/>", "<unrelated/>", "broken XML"])
def test_invalid_results_are_rejected(tmp_path, xml):
    path = tmp_path / "results.xml"
    path.write_text(xml)
    with pytest.raises((ValueError, results.ET.ParseError)):
        results.count_results([path])


def test_running_suite_diagnostic_survives_interruption(tmp_path):
    scripts = tmp_path / 'scripts'
    scripts.mkdir()
    for name in ('run_cocotb.sh', 'cocotb_results.py'):
        shutil.copy(ROOT / 'scripts' / name, scripts / name)
    bench = tmp_path / 'hw/tb'
    bench.mkdir(parents=True)
    (bench / 'Makefile').write_text(
        'all:\n\t@echo live-native-diagnostic\n\t@sleep 60\n'
        'clean:\n\t@true\n')
    process = subprocess.Popen(
        ['bash', str(scripts / 'run_cocotb.sh')],
        env={**os.environ, 'PY': sys.executable},
        stdout=subprocess.PIPE, stderr=subprocess.PIPE, start_new_session=True,
    )
    log = tmp_path / 'hw/soc/out/cocotb/tb.log'
    try:
        deadline = time.monotonic() + 5
        while time.monotonic() < deadline:
            if log.exists() and 'live-native-diagnostic' in log.read_text():
                break
            time.sleep(.02)
        assert process.poll() is None
        assert log.exists() and 'live-native-diagnostic' in log.read_text()
    finally:
        os.killpg(process.pid, signal.SIGTERM)
        try:
            process.communicate(timeout=3)
        finally:
            # The isolated test owns this entire process group, including
            # make's sleeper, even if the shell has already terminated.
            try:
                os.killpg(process.pid, signal.SIGKILL)
            except ProcessLookupError:
                pass
            process.wait(timeout=3)
    assert 'live-native-diagnostic' in log.read_text()


@pytest.mark.parametrize("mode,passed,failed,skipped,clean", [
    ("success", 1, 0, 0, True),
    ("partial", 1, 0, 0, False),
    ("empty", 0, 0, 0, False),
    ("missing", 0, 0, 0, False),
    ("malformed", 0, 0, 0, False),
    ("failure", 0, 1, 0, False),
    ("skipped", 0, 0, 1, False),
    ("no_match", 0, 0, 0, False),
])
def test_runner_verdict(tmp_path, mode, passed, failed, skipped, clean):
    scripts = tmp_path / "scripts"
    scripts.mkdir()
    for name in ("run_cocotb.sh", "cocotb_results.py"):
        shutil.copy(ROOT / "scripts" / name, scripts / name)
    bench = tmp_path / "hw/tb"
    bench.mkdir(parents=True)
    # A real make execution produces a completed first variant followed by
    # a failing second variant. Its valid XML must not hide the exit code.
    xml = {
        "empty": "<testsuites/>",
        "malformed": "bad XML",
        "failure": "<testsuites><testcase><failure/></testcase></testsuites>",
        "skipped": "<testsuites><testcase><skipped/></testcase></testsuites>",
    }.get(mode, "<testsuites><testcase/></testsuites>")
    recipe = "\t@true\n" if mode == "missing" else f"\t@printf '%s' '{xml}' > results.xml\n"
    if mode == "partial":
        recipe += "\t@echo 'second variant failed to compile'\n\t@false\n"
    (bench / "Makefile").write_text("all:\n" + recipe + "clean:\n\t@rm -f results.xml\n")
    # A stale passing XML is deliberately present before the run.
    (bench / "results.xml").write_text("<testsuites><testcase/></testsuites>")
    proc = subprocess.run(
        ["bash", str(scripts / "run_cocotb.sh"), "absent" if mode == "no_match" else ""],
        env={**os.environ, "PY": sys.executable}, text=True, capture_output=True, timeout=20,
    )
    assert (proc.returncode == 0) == clean, proc.stdout + proc.stderr
    assert f"{passed} passed, {failed} failed," in proc.stdout
    assert f"{skipped} skipped" in proc.stdout
    if mode == "partial":
        assert "second variant failed to compile" in (tmp_path / "hw/soc/out/cocotb/tb.log").read_text()


@pytest.mark.parametrize("binding", ["complete", "missing_driver", "missing_workflow"])
def test_native_suite_needs_a_live_external_driver_binding(tmp_path, binding):
    scripts = tmp_path / "scripts"
    scripts.mkdir()
    for name in ("run_cocotb.sh", "cocotb_results.py"):
        shutil.copy(ROOT / "scripts" / name, scripts / name)
    bench = tmp_path / "hw/soc/tb/cocotb"
    bench.mkdir(parents=True)
    (bench / "test_soc_mem_parity.py").write_text("# Native fixture module\n")
    (bench / "Makefile").write_text(
        "all:\n\t@printf '%s' '<testsuites><testcase/></testsuites>' > results.xml\n"
        "clean:\n\t@rm -f results.xml\n")
    workflow = tmp_path / ".github/workflows/checks.yml"
    workflow.parent.mkdir(parents=True)
    if binding != "missing_workflow":
        workflow.write_text("      - name: Native SRAM parity\n"
                            "        run: bash scripts/check_soc_memory_parity.sh\n")
    if binding != "missing_driver":
        (scripts / "check_soc_memory_parity.sh").write_text("#!/bin/sh\nexit 0\n")
    result = subprocess.run(["bash", str(scripts / "run_cocotb.sh"), "cocotb"],
                            env={**os.environ, "PY": sys.executable},
                            capture_output=True, text=True, timeout=20)
    assert (result.returncode == 0) == (binding == "complete"), result.stdout
    if binding == "complete":
        assert "separately run by check_soc_memory_parity.sh" in result.stdout
        assert "1 skipped" in result.stdout
    else:
        assert "UNREACHED cocotb test modules" in result.stdout


@pytest.mark.parametrize("mode", ["success", "partial", "missing", "skipped", "short"])
def test_prepared_pcie_ethernet_driver_is_counted_fail_closed(tmp_path, mode):
    scripts = tmp_path / "scripts"
    scripts.mkdir()
    for name in ("run_cocotb.sh", "cocotb_results.py"):
        shutil.copy(ROOT / "scripts" / name, scripts / name)
    bench = tmp_path / "hw/soc/tb/cocotb"
    bench.mkdir(parents=True)
    (bench / "Makefile.soc_pcie_ethernet").write_text(
        "$(error Prepared driver required)\n"
    )
    compiler = tmp_path / "bin"
    compiler.mkdir()
    (compiler / "iverilog").write_text("#!/bin/sh\nexit 0\n")
    (compiler / "iverilog").chmod(0o755)
    xml = "<testsuites><testcase/><testcase/></testsuites>"
    if mode == "skipped":
        xml = "<testsuites><testcase/><testcase><skipped/></testcase></testsuites>"
    elif mode == "short":
        xml = "<testsuites><testcase/></testsuites>"
    (scripts / "check_pcie_ethernet_soc.py").write_text(
        "from pathlib import Path\nimport argparse\n"
        "p=argparse.ArgumentParser();p.add_argument('--out',type=Path);"
        "p.add_argument('--iverilog-dir',type=Path);"
        "p.add_argument('--async-pcie',action='store_true');a=p.parse_args()\n"
        "assert a.async_pcie and (a.iverilog_dir/'iverilog').is_file()\n"
        "assert not a.out.exists();a.out.mkdir()\n"
        + ("" if mode == "missing" else f"(a.out/'results.xml').write_text({xml!r})\n")
        + f"raise SystemExit({1 if mode == 'partial' else 0})\n"
    )
    env = {**os.environ, "PY": sys.executable,
           "PATH": str(compiler) + os.pathsep + os.environ["PATH"]}
    # A second invocation must allocate a fresh capture instead of reusing XML.
    for _ in range(2):
        result = subprocess.run(
            ["bash", scripts / "run_cocotb.sh", "soc_pcie_ethernet"],
            env=env, capture_output=True, text=True, timeout=20,
        )
        assert (result.returncode == 0) == (mode == "success"), result.stdout + result.stderr
    captures = list((tmp_path / "hw/soc/out/cocotb").glob("pcie-ethernet.*/capture"))
    assert len(captures) == 2
