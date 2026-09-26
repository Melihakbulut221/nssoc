#!/usr/bin/env python3
# SPDX-FileCopyrightText: 2026 Hasan Melih Akbulut
# SPDX-License-Identifier: Apache-2.0
"""Derive the README's measured status from explicitly selected evidence.

No run-directory glob, inferred latest result, or historical failure deletion.
Update docs/status-sources.json deliberately when a newer result replaces one.
"""
import argparse
import hashlib
import json
from pathlib import Path
import re

ROOT = Path(__file__).resolve().parents[1]
START = "<!-- project-status:start -->"
END = "<!-- project-status:end -->"


def python_status(record):
    if record.get("status") == "PASS_FULL_PYTEST_NO_SKIPS":
        counts = {key: record[key] for key in ("collected", "passed", "failed", "skipped")}
        if (any(type(value) is not int or value < 0 for value in counts.values()) or
                counts["collected"] <= 0 or counts["passed"] != counts["collected"] or
                counts["failed"] or counts["skipped"] or
                not re.fullmatch(r"[0-9a-f]{40}", record["source_head"]) or
                record.get("final_source_status") != "CLEAN"):
            raise ValueError("Prepared pytest receipt does not support a complete passing inventory")
        return dict(head=record["source_head"], passed=counts["passed"],
                    skipped=0, failures=0)
    if record.get("status") != "PASS":
        raise ValueError("Python receipt has no accepted verdict")
    return dict(head=record["tested_head"], **record["pytest_counts"])


def core_physical_status(record):
    physical = record["physical"]
    if (record.get("status") != "PASS_PUBLISHED_EXACT_CORE_PHYSICAL_CHECKPOINT_ONLY" or
            physical.get("status") != "PASS_EXACT_NEW_CORE_PHYSICAL_CHECKS_NO_TIMING_OR_FOUNDRY_APPROVAL" or
            record.get("manufacturing_approval") is not False or
            record.get("final_sta_accepted") is not False or
            physical.get("manufacturing_approval") is not False or
            physical.get("timing_acceptance") is not False):
        raise ValueError("Core physical receipt must retain its non-signoff scope")
    candidate = physical["candidate_sha256"]
    if (not re.fullmatch(r"[0-9a-f]{64}", candidate) or
            physical["input_sha256"].get(physical["candidate_gds"]) != candidate or
            not any(name.endswith(".gds") and value == candidate
                    for name, value in record["members"].items())):
        raise ValueError("Core physical verdict lacks an exact archived GDS binding")
    checks = [(physical[name], count) for name, count in
              (("main", 560), ("density", 7), ("antenna", 31))]
    if len(physical["supplemental"]) != 1:
        raise ValueError("Core physical receipt lacks the accepted spacing supplement")
    checks.append((physical["supplemental"][0]["measurement"], 11))
    for check, count in checks:
        if (check.get("status") != "PASS" or check.get("markers") != 0 or
                check.get("category_count") != count or check.get("categories") or
                check.get("process_returncode", 0) != 0):
            raise ValueError("Incomplete or failing core physical measurement")
    lvs = physical["lvs"]
    if (lvs.get("status") != "PASS_WIDE_SPACING_REPAIRED_CORE_TRANSISTOR_LVS" or
            lvs.get("circuits") != 130 or lvs.get("primitives_each") != 5129488):
        raise ValueError("Core LVS inventory does not match the accepted candidate")
    return dict(candidate_sha256=candidate, main_categories=560, density_categories=7,
                antenna_categories=31, supplemental_categories=11, lvs_circuits=130,
                lvs_primitives_each=5129488, timing_accepted=False,
                manufacturing_approval=False, scope=record["scope"])


def native_status(record):
    runs = record["runs"]
    profiles = [run["profile"] for run in runs]
    if sorted(profiles) != ["base", "full"]:
        raise ValueError("Native acceptance needs exactly one base and one full run")
    if record["status"] != "PASS" or any(
            run["head"] != record["head"] or run["status"] != "PASS"
            or run["result"].get("passed") is not True
            or run["result"].get("sources_unchanged") is not True for run in runs):
        raise ValueError("Native profile verdict/source identity does not support aggregate PASS")
    return dict(status=record["status"], head=record["head"],
                scope=record["scope"], profiles=sorted(profiles))


def formal_status(record):
    rows = []
    for run in record["runs"]:
        result = run["result"]
        tasks = result["tasks"]
        if (not tasks or len(tasks) != record["expected_task_count"] or result.get("passed") is not True or
                result.get("sources_unchanged") is not True or any(
                    task["status"] != "PASS" or task["source_state"] != "clean"
                    for task in tasks.values())):
            raise ValueError("Formal inventory does not support aggregate PASS")
        rows.append(dict(head=result["head"], passed=len(tasks),
                         exclusions=len(result["exclusions"])))
    if not rows:
        raise ValueError("Formal evidence has no completed runs")
    return rows


def derive(root=ROOT):
    sources = json.loads((root / "docs/status-sources.json").read_text())
    records = {key: json.loads((root / path).read_text()) for key, path in sources.items()}
    corners = records["physical"]["corner_reports"]["results"]
    return dict(
        sources=sources,
        source_sha256={key: hashlib.sha256((root / path).read_bytes()).hexdigest()
                       for key, path in sources.items()},
        python=python_status(records["python"]),
        core_physical=core_physical_status(records["core_physical"]),
        peripheral_formal=dict(passed=sum(x["status"].split()[0] == "PASS"
                                          for x in records["peripheral_formal"]["tasks"]),
                               total=len(records["peripheral_formal"]["tasks"])),
        ram=dict(passed=sum(x["passed"] for x in records["ram"]["positive"]),
                 total=len(records["ram"]["positive"]),
                 negative_rejected=not records["ram"]["negative"]["passed"]),
        physical=dict(scope="corrected-loader/IRQ native global-route estimates; 5% derating",
                      setup_ns=min(x["setup_ns"] for x in corners.values()),
                      hold_ns=min(x["hold_ns"] for x in corners.values()),
                      max_fanout_violations=max(x["electrical"]["fanout"] for x in corners.values())),
        native_boot=native_status(records["native_boot"]),
        formal_sweep=formal_status(records["formal_sweep"]),
        native_replay=dict(status=records["native_replay"]["status"],
                           head=records["native_replay"]["head"],
                           **records["native_replay"]["acceptance"]),
    )


def table(status):
    p, f, ram, route, native = (status[k] for k in
                               ("python", "peripheral_formal", "ram", "physical", "native_boot"))
    replay = status["native_replay"]
    def evidence(name, text):
        return f'[{text}]({status["sources"][name]})'
    rows = [
        ("Silicon / product", "No silicon or radiation qualification; product gates open",
         "[Acceptance contract](docs/92-product-acceptance.md)"),
        ("Frozen pilot", "TTIHP26b submission; source tree frozen",
         "[Freeze contract](docs/34-pilot-freeze.md)"),
        ("Python regression", f'{p["passed"]} pass, {p["skipped"]} skip; commit `{p["head"][:7]}`',
         evidence("python", "Exact revision and command")),
        ("Peripheral checks", f'{f["passed"]}/{f["total"]} new formal tasks; {ram["passed"]}/{ram["total"]} native RAM profiles',
         evidence("peripheral_formal", "Formal scope") + "; " + evidence("ram", "RAM + negative control")),
        ("Mandatory formal sweep", "; ".join(
            f'{row["passed"]} PASS at `{row["head"][:7]}`, {row["exclusions"]} historical exclusions'
            for row in status["formal_sweep"]), evidence("formal_sweep", "Dated source-bound inventories")),
        ("Independent native boot", f'{native["status"]} base + full at `{native["head"][:7]}`; functional four-state simulation',
         evidence("native_boot", "Hosted result and retained prior failure")),
        ("Local native correction", f'{replay["status"]}: {replay["checks"]} checks, {replay["cycles"]:,} cycles; firmware `{replay["head"][:7]}`',
         evidence("native_replay", "Same hosted netlist, verified serial initialization")),
        ("32-SRAM core geometry", "Main DRC, density, antenna and transistor LVS PASS; timing/product open",
         evidence("core_physical", "Exact GDS and supplemental checks")),
        ("Historical timing estimate", f'Setup {route["setup_ns"]:.3f} ns, hold {route["hold_ns"]:.3f} ns; not final-core STA',
         evidence("physical", "Earlier route and electrical failures")),
    ]
    return "\n".join(["| Area | Measured status | Evidence |", "|---|---|---|"] +
                     ["| " + " | ".join(row) + " |" for row in rows])


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--write", action="store_true")
    args = parser.parse_args()
    status = derive()
    serialized = json.dumps(status, indent=2) + "\n"
    readme = ROOT / "README.md"
    text = readme.read_text()
    if text.count(START) != 1 or text.count(END) != 1:
        raise ValueError("README status markers are missing or duplicated")
    before, tail = text.split(START)
    _, after = tail.split(END)
    rendered = before + START + "\n" + table(status) + "\n" + END + after
    output = ROOT / "docs/project-status.json"
    if args.write:
        output.write_text(serialized)
        readme.write_text(rendered)
    elif not output.exists() or output.read_text() != serialized or rendered != text:
        raise SystemExit("Project status is stale; run python3 scripts/project_status.py --write")
    print("Project status matches selected evidence")


if __name__ == "__main__":
    main()
