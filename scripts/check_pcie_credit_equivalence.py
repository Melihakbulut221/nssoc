# SPDX-FileCopyrightText: 2026 Hasan Melih Akbulut
# SPDX-License-Identifier: Apache-2.0
"""Prove credit accounting against the frozen pre-parallel whole-chip source."""

import argparse
import hashlib
import json
from pathlib import Path
import re
import subprocess

ROOT = Path(__file__).resolve().parents[1]
REFERENCE = ROOT / "sw/tests/fixtures/pcie_credit_tx/serial-credit.v"
REFERENCE_SHA = "7d01f9a423bdd4f141371c47465a8c718d1eb578373a00f6eb1590efaf1708d6"


def pin(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def run(candidate, out, yosys):
    if pin(REFERENCE) != REFERENCE_SHA:
        raise ValueError("Frozen credit reference changed")
    candidate, out, yosys = candidate.resolve(), out.resolve(), yosys.resolve()
    out.mkdir(parents=True, exist_ok=False)
    inputs = {str(p): pin(p) for p in (REFERENCE, candidate, Path(__file__), yosys)}
    for name, path in (("gold", REFERENCE), ("gate", candidate)):
        text = path.read_text()
        declaration = "module soc_pcie_credit_tx ("
        if text.count(declaration) != 1:
            raise ValueError("Unexpected credit module declaration")
        (out / (name + ".v")).write_text(text.replace(declaration, "module " + name + " ("))
    # clk2fflogic models explicit clock events and asynchronous resets. Do not
    # silently replace async resets with a synchronous-only proof assumption.
    recipe = "\n".join([
        "read_verilog -sv gold.v gate.v", "proc", "memory_map", "opt",
        "clk2fflogic", "opt", "equiv_make gold gate equiv",
        "hierarchy -top equiv", "equiv_simple", "equiv_induct -seq 4",
        "equiv_status -assert", "",
    ])
    (out / "proof.ys").write_text(recipe)
    with (out / "proof.log").open("w") as stream:
        result = subprocess.run([yosys, "-s", "proof.ys"], cwd=out,
                                stdout=stream, stderr=subprocess.STDOUT)
    text = (out / "proof.log").read_text()
    counts = re.findall(r"Of those cells (\d+) are proven and (\d+) are unproven", text)
    unchanged = all(pin(Path(p)) == value for p, value in inputs.items())
    passed = (result.returncode == 0 and len(counts) == 1
              and int(counts[0][0]) > 0 and int(counts[0][1]) == 0
              and "Equivalence successfully proven!" in text and unchanged)
    record = dict(status="PASS_SEQUENTIAL_EQUIVALENCE" if passed else "FAIL",
                  returncode=result.returncode, counts=counts, inputs=inputs,
                  inputs_unchanged=unchanged,
                  scope="RTL credit module equivalence, including explicit clock/reset events; not native timing, PHY or full-chip qualification")
    (out / "result.json").write_text(json.dumps(record, indent=2) + "\n")
    return record


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--candidate", type=Path, default=ROOT / "hw/soc/rtl/pcie/soc_pcie_credit_tx.v")
    p.add_argument("--yosys", type=Path, required=True)
    p.add_argument("--out", type=Path, required=True)
    a = p.parse_args()
    r = run(a.candidate, a.out, a.yosys)
    print(r["status"], r["counts"])
    return int(not r["status"].startswith("PASS"))


if __name__ == "__main__":
    raise SystemExit(main())
