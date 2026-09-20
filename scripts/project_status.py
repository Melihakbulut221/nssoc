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

ROOT = Path(__file__).resolve().parents[1]
START = "<!-- project-status:start -->"
END = "<!-- project-status:end -->"


def derive(root=ROOT):
    sources = json.loads((root / "docs/status-sources.json").read_text())
    records = {key: json.loads((root / path).read_text()) for key, path in sources.items()}
    corners = records["physical"]["corner_reports"]["results"]
    return dict(
        sources=sources,
        source_sha256={key: hashlib.sha256((root / path).read_bytes()).hexdigest()
                       for key, path in sources.items()},
        python=dict(head=records["python"]["tested_head"], **records["python"]["pytest_counts"]),
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
        native_boot=dict(status=records["native_boot"]["status"],
                         head=records["native_boot"]["head"],
                         scope=records["native_boot"]["scope"]),
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
        ("Independent native boot", f'{native["status"]} at `{native["head"][:7]}`; hosted correction replay pending',
         evidence("native_boot", "Hosted failure retained")),
        ("Local native correction", f'{replay["status"]}: {replay["checks"]} checks, {replay["cycles"]:,} cycles; firmware `{replay["head"][:7]}`',
         evidence("native_replay", "Same hosted netlist, verified serial initialization")),
        ("Physical closure", f'Setup {route["setup_ns"]:.3f} ns, hold {route["hold_ns"]:.3f} ns; electrical failures',
         evidence("physical", "Fixed-route estimate scope")),
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
