# SPDX-License-Identifier: Apache-2.0
"""Exercise the actual workflow shell with failing tool stubs, without CAD."""
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
import yaml

ROOT = Path(__file__).resolve().parents[2]
FLOW = ROOT / ".github/workflows/cloud-evidence-summary.yml"
FAKE = r'''
import json, os, pathlib, sys
if sys.argv[1] == "-c":
    os.execv(sys.executable, [sys.executable, *sys.argv[1:]])
args = sys.argv[1:]
if args[0].endswith("check_soc_lint.py"):
    label = "lint-" + args[args.index("--profile") + 1]
    out = pathlib.Path(args[args.index("--output") + 1])
    status = "PASS_WITH_RECORDED_WARNINGS"
else:
    label = "joint-async" if "--async-pcie" in args else "joint-sync"
    out = pathlib.Path(args[args.index("--out") + 1])
    status = "PASS"
with open("attempts", "a") as f:
    f.write(label + "\n")
out.mkdir(parents=True, exist_ok=True)
mode = os.environ.get("FAULT_MODE", "")
target = os.environ.get("FAULT_TARGET", "")
if label != target or mode != "missing":
    data = {"status": "FAIL" if label == target and mode == "status" else status}
    (out / "result.json").write_text("{" if label == target and mode == "json" else json.dumps(data))
sys.exit(7 if label in os.environ.get("FAIL_LABELS", "").split(",") else 0)
'''

class FailurePropagation(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        jobs = yaml.safe_load(FLOW.read_text())["jobs"]
        cls.soc = next(s["run"] for s in jobs["pcie-soc"]["steps"]
                       if s.get("name", "").startswith("Base and full lint,"))
        cls.lint = next(s["run"] for s in jobs["pcie-unit"]["steps"]
                        if s.get("name") == "Lint the PCIe packet subsystem")

    def run_soc(self, failures=(), mode="", target=""):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            tools = root / "bin"
            tools.mkdir()
            stub = tools / "python3"
            stub.write_text("#!" + sys.executable + "\n" + FAKE)
            stub.chmod(0o755)
            env = dict(os.environ, PATH=str(tools) + os.pathsep + os.environ["PATH"],
                       OSS_CAD_SUITE=str(tools), GITHUB_WORKSPACE=tmp,
                       FAIL_LABELS=",".join(failures), FAULT_MODE=mode, FAULT_TARGET=target)
            p = subprocess.run(["bash", "-e", "-o", "pipefail", "-c", self.soc],
                               cwd=tmp, env=env, text=True, capture_output=True)
            attempts = (root / "attempts").read_text().splitlines()
            self.assertEqual(attempts, ["lint-base", "lint-full", "joint-async", "joint-sync"],
                             p.stdout + p.stderr)
            self.assertEqual(p.returncode == 0, not failures and not mode, p.stdout + p.stderr)
            for label in attempts:
                self.assertTrue((root / "out" / (label + ".log")).is_file())

    def test_all_exit_code_combinations(self):
        labels = ["lint-base", "lint-full", "joint-async", "joint-sync"]
        for mask in range(16):
            with self.subTest(mask=mask):
                self.run_soc([name for bit, name in enumerate(labels) if mask & (1 << bit)])

    def test_missing_malformed_and_failed_reports(self):
        for mode in ["missing", "json", "status"]:
            for target in ["lint-base", "lint-full", "joint-async", "joint-sync"]:
                with self.subTest(mode=mode, target=target):
                    self.run_soc(mode=mode, target=target)

    def test_lint_exit_is_not_hidden_by_output_filter(self):
        for code in [0, 1, 2]:
            for text in ["", "%Error: deliberately injected", "%Warning-OTHER: diagnostic"]:
                with self.subTest(code=code, text=text), tempfile.TemporaryDirectory() as tmp:
                    root = Path(tmp)
                    (root / "out").mkdir()
                    tool = root / "verilator"
                    tool.write_text("#!/bin/bash\nprintf '%s' \"$LINT_TEXT\"\nexit \"$LINT_CODE\"\n")
                    tool.chmod(0o755)
                    env = dict(os.environ, PATH=tmp + os.pathsep + os.environ["PATH"],
                               LINT_TEXT=text, LINT_CODE=str(code))
                    p = subprocess.run(["bash", "-e", "-o", "pipefail", "-c", self.lint],
                                       cwd=tmp, env=env, text=True, capture_output=True)
                    self.assertEqual(p.returncode, code, p.stdout + p.stderr)
                    self.assertEqual((root / "out/lint.txt").read_text(), text)

if __name__ == "__main__":
    unittest.main(verbosity=2)
