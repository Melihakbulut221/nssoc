#!/usr/bin/env python3
# SPDX-FileCopyrightText: 2026 Hasan Melih Akbulut
# SPDX-License-Identifier: Apache-2.0
"""Run the regression using the project cocotb interpreter and selected Icarus."""
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile

from cocotb_icarus_runtime import prepare_runtime


def main():
    root = Path(__file__).resolve().parents[1]
    if sys.argv[1:2] == ["--pytest"]:
        runner = [sys.executable, "-m", "pytest", *sys.argv[2:]]
    else:
        runner = [str(root / "scripts/run_cocotb.sh"), *sys.argv[1:]]
    env = os.environ.copy()
    hardware_bin = root / "hw/.venv/bin"
    suite = Path(env.get("OSS_CAD_SUITE") or root / "hw/soc/tools/oss-cad-suite")
    search_path = os.pathsep.join((env["PATH"], str(suite.resolve() / "bin")))
    compiler = shutil.which("iverilog", path=search_path)
    env["PATH"] = search_path
    with tempfile.TemporaryDirectory(prefix="nssoc-cocotb-") as tmp:
        if compiler and (hardware_bin / "cocotb-config").is_file():
            runtime, _, _ = prepare_runtime(Path(compiler).parent, Path(tmp) / "bin")
            env["PATH"] = os.pathsep.join((str(hardware_bin), str(runtime), env["PATH"]))
        return subprocess.run(runner, cwd=root, env=env).returncode


if __name__ == "__main__":
    sys.exit(main())
