#!/usr/bin/env python3
# SPDX-FileCopyrightText: 2026 Hasan Melih Akbulut
# SPDX-License-Identifier: Apache-2.0
"""Run and inventory the complete declared pilot/SoC regression formal sweep.

Use a fresh checkout after make soc-rtl-prepare. Existing task outputs are
rejected, so old statuses cannot become fresh evidence. Explicit historical
non-closing tasks remain exclusions in the report, never PASS verdicts.
"""
import argparse
import hashlib
import json
import os
from pathlib import Path
import re
import signal
import subprocess
import time

from formal_source_state import source_state

ROOT = Path(__file__).resolve().parents[1]
POLICY = ROOT / "hw/soc/formal/sweep-policy.json"


def tasks(config):
    text = config.read_text()
    section = re.search(r"(?ms)^\[tasks\]\s*\n(.*?)(?=^\[|\Z)", text)
    if not section:
        raise ValueError(f"No task declaration: {config}")
    return [line.split()[0] for line in section[1].splitlines()
            if line.strip() and not line.lstrip().startswith("#")]


def inventory(root):
    policy = json.loads((root / "hw/soc/formal/sweep-policy.json").read_text())
    expected, excluded = {}, {}
    for area in ("formal", "hw/soc/formal"):
        for config in sorted((root / area).glob("*.sby")):
            for task in tasks(config):
                path = f"{area}/{config.stem}_{task}"
                reason = None
                if area == "hw/soc/formal":
                    reason = policy["excluded_jobs"].get(config.name)
                    reason = reason or policy["excluded_tasks"].get(config.name + ":" + task)
                if reason: excluded[path] = reason
                else: expected[path] = {"config": str(config.relative_to(root)), "task": task}
    return expected, excluded


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def run(command, log, env, limit):
    start = time.monotonic()
    with log.open("x") as stream:
        child = subprocess.Popen(command, cwd=ROOT, env=env, stdout=stream,
                                 stderr=subprocess.STDOUT, start_new_session=True)
        try:
            code = child.wait(timeout=limit)
        except subprocess.TimeoutExpired:
            os.killpg(child.pid, signal.SIGTERM)
            try: child.wait(timeout=10)
            except subprocess.TimeoutExpired:
                os.killpg(child.pid, signal.SIGKILL)
                child.wait()
            code = 124
    return dict(command=command, returncode=code, elapsed_s=time.monotonic() - start)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, default=ROOT / "hw/soc/out/formal-sweep")
    parser.add_argument("--stage-timeout", type=int, default=1800)
    args = parser.parse_args()
    if args.stage_timeout <= 0: parser.error("stage timeout must be positive")
    expected, excluded = inventory(ROOT)
    existing = [str(p) for area in ("formal", "hw/soc/formal")
                for p in (ROOT / area).glob("*/config.sby")]
    if existing:
        parser.error("Use a fresh prepared checkout; existing formal task outputs: " + ", ".join(existing[:4]))
    if not (ROOT / "hw/soc/gen/ibex_register_file_ff.v").is_file():
        parser.error("Run make soc-rtl-prepare first")
    out = args.output.absolute()
    out.mkdir(parents=True, exist_ok=False)
    # Pin actual tracked inputs including headers, scripts and task policy.
    tracked = subprocess.check_output(["git", "ls-files", "-z"], cwd=ROOT).decode().split("\0")
    watched = [p for p in tracked if p and (p.startswith(("formal/", "hw/rtl/", "hw/soc/rtl/", "hw/soc/formal/", "scripts/")) or p == "tools.mk")]
    hashes = {p: digest(ROOT / p) for p in watched}
    hashes["hw/soc/gen/ibex_register_file_ff.v"] = digest(ROOT / "hw/soc/gen/ibex_register_file_ff.v")
    record = dict(head=subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=ROOT, text=True).strip(),
                  source_sha256=hashes, exclusions=excluded, stages=[], tasks={}, passed=False)
    result_path = out / "result.json"
    result_path.write_text(json.dumps(record, indent=2) + "\n")
    env = dict(os.environ)
    try:
        for area, target, name in (("formal", "everything", "pilot"), ("hw/soc/formal", "all", "soc")):
            stage = run(["make", "-C", area, target], out / (name + ".log"), env, args.stage_timeout)
            record["stages"].append(stage)
            result_path.write_text(json.dumps(record, indent=2) + "\n")
            if stage["returncode"]:
                raise RuntimeError(f"{name} sweep failed: exit {stage['returncode']}; see {out}")
    finally:
        for path, description in expected.items():
            work = ROOT / path
            fields = (work / "status").read_text().split() if (work / "status").exists() else []
            status = fields[0] if fields else "MISSING"
            state = source_state(work)
            record["tasks"][path] = dict(**description, status=status, source_state=state,
                                          log_sha256=digest(work / "logfile.txt") if (work / "logfile.txt").exists() else None)
        record["sources_unchanged"] = all((ROOT / p).is_file() and digest(ROOT / p) == value
                                           for p, value in hashes.items())
        record["passed"] = (len(record["stages"]) == 2 and
                            all(s["returncode"] == 0 for s in record["stages"]) and
                            record["sources_unchanged"] and bool(expected) and all(
            row["status"] == "PASS" and row["source_state"] == "clean" for row in record["tasks"].values())
                            )
        result_path.write_text(json.dumps(record, indent=2) + "\n")
    if not record["passed"]:
        raise RuntimeError(f"Formal task inventory is incomplete, stale or non-PASS; see {result_path}")
    print(f"PASS {len(expected)} fresh formal tasks; {len(excluded)} explicit historical non-closing tasks excluded")


if __name__ == "__main__":
    main()
