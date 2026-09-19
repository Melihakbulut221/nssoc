# SPDX-FileCopyrightText: 2026 Hasan Melih Akbulut
# SPDX-License-Identifier: Apache-2.0
"""A partial simulator run must not produce a green verification result."""

import importlib.util
import os
from pathlib import Path
import shutil
import subprocess
import sys

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
