# SPDX-FileCopyrightText: 2026 Hasan Melih Akbulut
# SPDX-License-Identifier: Apache-2.0
"""Launch OSS CAD Suite Icarus with the selected cocotb Python environment."""

from pathlib import Path
import shlex


def prepare_runtime(bin_dir, destination):
    """Return tool directory, generated launchers and actual native dependencies.

    OSS CAD Suite's vvp wrapper overwrites PYTHONHOME/PYTHONEXECUTABLE with
    its bundled Python. Preserve its loader/library path but let cocotb select
    the interpreter. Never modify the installed suite. Ordinary Icarus needs
    no adapter; an incomplete OSS installation fails instead of falling back.
    """
    bin_dir = Path(bin_dir).resolve()
    destination = Path(destination).resolve()
    compiler, wrapper = bin_dir / "iverilog", bin_dir / "vvp"
    for path in (compiler, wrapper):
        if not path.is_file():
            raise FileNotFoundError(path)
    suite = bin_dir.parent
    binary = suite / "libexec/vvp"
    loader = suite / "lib/ld-linux-x86-64.so.2"
    dependencies = [compiler, wrapper]
    if not binary.exists() and not loader.exists():
        return bin_dir, [], dependencies
    if not binary.is_file() or not loader.is_file():
        raise ValueError("Incomplete OSS CAD Suite native Icarus runtime")
    destination.mkdir()
    commands = {
        "iverilog": [str(compiler)],
        "vvp": [
            "env", "-u", "PYTHONHOME", "-u", "PYTHONEXECUTABLE",
            str(loader), "--inhibit-cache", "--inhibit-rpath", "",
            "--library-path", str(suite / "lib"), str(binary),
        ],
    }
    launchers = []
    for name, argv in commands.items():
        path = destination / name
        path.write_text("#!/bin/sh\nexec " + shlex.join(argv) + ' "$@"\n')
        path.chmod(0o755)
        launchers.append(path)
    return destination, launchers, [*dependencies, loader, binary]


def runtime_diagnostics(text):
    """Retain fatal native and cocotb diagnostics, including pre-time startup."""
    import re

    return [
        line for line in text.splitlines()
        if re.search(r"(?:WARNING|ERROR|FATAL):|\b(?:ERROR|CRITICAL)\s+\S", line)
        or "Unexpected sys.executable" in line
    ]
