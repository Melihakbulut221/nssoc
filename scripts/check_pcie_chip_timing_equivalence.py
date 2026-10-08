# SPDX-FileCopyrightText: 2026 Hasan Melih Akbulut
# SPDX-License-Identifier: Apache-2.0
"""Check bank reads, bounded MBIST and CDC reset isolation against frozen RTL.

No clock changes, input assumptions or valid-only output masking. Explicit
clock/reset events and undefined memory contents are modeled by Yosys.
"""

import argparse
import hashlib
import json
from pathlib import Path
import re
import subprocess

ROOT = Path(__file__).resolve().parents[1]
REFERENCES = {
    "cdc": ("raw-reset-cdc.v", "4215d7467b9026002e659633fe3c111eecf9f04a9dba90653e8f34572d7cad00",
            "soc_pcie_apb_cdc", "pcie/soc_pcie_apb_cdc.v"),
    "rx": ("flat-rx.v", "ea4977440f6e111cb87967385012835720cf2581d8b1c3d03608d55f097ffae8",
           "soc_pcie_rx_credit", "pcie/soc_pcie_rx_credit.v"),
    "mbist": ("wide-mbist.v", "4bdf54566b8244023ba167df01b539bd1c0b21c985987718329689b8c2f3bb81",
              "soc_sram_mbist", "dft/soc_sram_mbist.v"),
}


def pin(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def run(kind, candidate, out, yosys, parameters=None):
    filename, digest, module, default = REFERENCES[kind]
    reference = ROOT / "sw/tests/fixtures/pcie_chip_timing" / filename
    if pin(reference) != digest:
        raise ValueError("Frozen timing reference changed")
    candidate = (candidate or ROOT / "hw/soc/rtl" / default).resolve()
    out, yosys = out.resolve(), yosys.resolve()
    parameters = parameters or {}
    allowed = {"mbist": {"WIDTH", "DEPTH", "READ_LATENCY"},
               "rx": {"MAX_TLP_DWORDS", "SLOTS_PER_CLASS", "COMPLETER_ONLY"},
               "cdc": set()}[kind]
    if any(k not in allowed or type(v) is not int or v < 0 for k, v in parameters.items()):
        raise ValueError("Unsupported parameter")
    out.mkdir(parents=True, exist_ok=False)
    inputs = {str(p): pin(p) for p in (reference, candidate, yosys, Path(__file__))}
    for name, source in (("gold", reference), ("gate", candidate)):
        text = source.read_text()
        suffix = " (" if kind == "cdc" else " #("
        declaration = "module " + module + suffix
        if text.count(declaration) != 1:
            raise ValueError("Unexpected module declaration")
        (out / (name + ".v")).write_text(text.replace(declaration, "module " + name + suffix))
    recipe = ["read_verilog -sv -DSYNTHESIS gold.v gate.v"]
    for name in ("gold", "gate"):
        for key, value in parameters.items():
            recipe.append(f"chparam -set {key} {value} {name}")
    recipe += ["proc", "memory_map", "opt", "clk2fflogic", "opt",
               "equiv_make gold gate equiv", "hierarchy -top equiv",
               "equiv_simple -undef -short", "equiv_induct -undef -seq 4",
               "equiv_status -assert"]
    (out / "proof.ys").write_text("\n".join(recipe) + "\n")
    with (out / "proof.log").open("w") as log:
        process = subprocess.run([yosys, "-s", "proof.ys"], cwd=out,
                                 stdout=log, stderr=subprocess.STDOUT)
    text = (out / "proof.log").read_text()
    counts = re.findall(r"Of those cells (\d+) are proven and (\d+) are unproven", text)
    unchanged = all(pin(Path(p)) == digest for p, digest in inputs.items())
    passed = (process.returncode == 0 and len(counts) == 1 and int(counts[0][0]) > 0
              and int(counts[0][1]) == 0 and unchanged
              and "Equivalence successfully proven!" in text)
    result = dict(status="PASS" if passed else "FAIL", kind=kind,
                  parameters=parameters, returncode=process.returncode, counts=counts,
                  inputs=inputs, inputs_unchanged=unchanged,
                  scope="RTL sequential equivalence at the listed parameters; not native timing or serial PHY acceptance")
    (out / "result.json").write_text(json.dumps(result, indent=2) + "\n")
    return result


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--kind", choices=REFERENCES, required=True)
    p.add_argument("--candidate", type=Path)
    p.add_argument("--out", type=Path, required=True)
    p.add_argument("--yosys", type=Path, required=True)
    p.add_argument("--parameters", type=json.loads, default={})
    args = p.parse_args()
    result = run(args.kind, args.candidate, args.out, args.yosys, args.parameters)
    print(result["status"], result["counts"])
    return int(result["status"] != "PASS")


if __name__ == "__main__":
    raise SystemExit(main())
