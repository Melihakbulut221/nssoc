# SPDX-FileCopyrightText: 2026 Hasan Melih Akbulut
# SPDX-License-Identifier: Apache-2.0
"""Exercise the launcher boundary without depending on an installed suite."""

import os
from pathlib import Path
import subprocess
import sys

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "scripts"))
from cocotb_icarus_runtime import prepare_runtime, runtime_diagnostics


def executable(path, body):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("#!/bin/sh\n" + body)
    path.chmod(0o755)
    return path


def test_oss_loader_environment_and_argument_boundary(tmp_path):
    suite = tmp_path / "suite with ' quote"
    compiler = executable(suite / "bin/iverilog", 'printf "%s\\n" "$@"\n')
    wrapper = executable(suite / "bin/vvp", "exit 97\n")
    loader = executable(
        suite / "lib/ld-linux-x86-64.so.2",
        'test "${PYTHONHOME+set}" != set || exit 91\n'
        'test "${PYTHONEXECUTABLE+set}" != set || exit 92\n'
        'test "$PYGPI_PYTHON_BIN" = chosen-python || exit 93\n'
        'printf "%s\\n" "$@"\n',
    )
    binary = executable(suite / "libexec/vvp", "exit 98\n")
    originals = {p: p.read_bytes() for p in (compiler, wrapper, loader, binary)}
    selected, launchers, dependencies = prepare_runtime(suite / "bin", tmp_path / "runtime")
    args = ["-M", "path with spaces", "literal$(exit 99)", "'quoted'"]
    env = dict(os.environ, PYTHONHOME="wrong", PYTHONEXECUTABLE="wrong", PYGPI_PYTHON_BIN="chosen-python")
    output = subprocess.check_output([selected / "vvp", *args], env=env, text=True)
    assert output.splitlines() == [
        "--inhibit-cache", "--inhibit-rpath", "", "--library-path",
        str(suite / "lib"), str(binary), *args,
    ]
    assert subprocess.check_output([selected / "iverilog", *args], text=True).splitlines() == args
    assert len(launchers) == 2 and set(dependencies) == set(originals)
    assert all(p.read_bytes() == data for p, data in originals.items())
    with pytest.raises(FileExistsError):
        prepare_runtime(suite / "bin", selected)


def test_ordinary_icarus_and_incomplete_suite(tmp_path):
    bin_dir = tmp_path / "bin"
    executable(bin_dir / "iverilog", "exit 0\n")
    executable(bin_dir / "vvp", "exit 0\n")
    selected, launchers, dependencies = prepare_runtime(bin_dir, tmp_path / "runtime")
    assert selected == bin_dir and not launchers and len(dependencies) == 2
    assert not (tmp_path / "runtime").exists()
    executable(tmp_path / "libexec/vvp", "exit 0\n")
    with pytest.raises(ValueError, match="Incomplete"):
        prepare_runtime(bin_dir, tmp_path / "runtime")


@pytest.mark.parametrize("line", [
    "     -.--ns ERROR    gpi      Unexpected sys.executable value",
    "0.00ns CRITICAL cocotb Simulator failed",
    "ERROR: rtl.v:12 native failure",
    "WARNING: rtl.v:12 undefined input",
    "FATAL: rtl.v:12 assertion",
])
def test_native_diagnostics_fail_closed(line):
    assert runtime_diagnostics(line) == [line]


def test_normal_progress_is_not_an_error():
    assert runtime_diagnostics("0.00ns INFO cocotb Running tests\n2 tests passed") == []
