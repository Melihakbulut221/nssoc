# SPDX-FileCopyrightText: 2026 Hasan Melih Akbulut
# SPDX-License-Identifier: Apache-2.0
"""Prove the late-byte LCRC predicate rewrite without packet-state assumptions."""

import argparse
import hashlib
import json
from pathlib import Path
import re
import subprocess

ROOT = Path(__file__).resolve().parents[1]
REFERENCE = ROOT / "sw/tests/fixtures/pcie_chip_timing/lcrc-before-residue.v"
REFERENCE_SHA = "7d68e35487f00fee5e0e389cb6e09c2e543cab01c2d303ae6156404719f0571a"
CRC = ROOT / "hw/soc/rtl/pcie/soc_pcie_crc32_byte.v"
CRC_SHA = "b3e856cb329d35a634171f6c57b4e0205b94d140e8e8c50ca6334826dbb70129"


def pin(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def normalized(text):
    return re.sub(r"\s+", "", re.sub(r"/\*.*?\*/|//[^\n]*", "", text, flags=re.S))


def predicate(text, reference):
    matches = list(re.finditer(r"\bwire\s+crc_residue_ok\s*=(.*?);", text, re.S))
    if len(matches) != 1:
        raise ValueError("Exactly one residue predicate declaration required")
    match = matches[0]
    restored = text[:match.start()] + text[match.end():]
    if len(re.findall(r"\bcrc_residue_ok\b", restored)) != 1:
        raise ValueError("Exactly one residue predicate use required")
    restored = re.sub(r"\bcrc_residue_ok\b", "crc_next==32'hdebb20e3", restored)
    if normalized(restored) != normalized(reference):
        raise ValueError("Packet state, handshake, storage or CRC update changed")
    return match[1]


def run(candidate, out, yosys):
    candidate, out, yosys = (Path(p).resolve() for p in (candidate, out, yosys))
    if pin(REFERENCE) != REFERENCE_SHA or pin(CRC) != CRC_SHA:
        raise ValueError("Frozen LCRC reference or CRC primitive changed")
    expression = predicate(candidate.read_text(), REFERENCE.read_text())
    out.mkdir(parents=True, exist_ok=False)
    header = "module NAME(input [31:0] crc,input [7:0] rx_data_i,input rx_sop_i,output good);\n"
    gold = """wire [31:0] next_crc;
soc_pcie_crc32_byte update_crc(.state_i(rx_sop_i ? 32'hffffffff : crc),
 .data_i(rx_data_i),.state_o(next_crc));
assign good=next_crc==32'hdebb20e3;
endmodule
"""
    (out / "gold.v").write_text(header.replace("NAME", "gold") + gold)
    (out / "gate.v").write_text(header.replace("NAME", "gate") + "assign good=" + expression + ";\nendmodule\n")
    (out / "proof.ys").write_text(f"""read_verilog -sv {CRC} gold.v gate.v
proc
flatten
opt
miter -equiv -make_outputs -make_assert -flatten gold gate miter
hierarchy -top miter
opt_clean
sat -verify -prove-asserts -set-def-inputs -show-inputs -show-outputs
""")
    inputs = {str(p): pin(p) for p in (
        candidate, REFERENCE, CRC, yosys, Path(__file__),
        out / "gold.v", out / "gate.v", out / "proof.ys",
    )}
    with (out / "proof.log").open("w") as log:
        process = subprocess.run([yosys, "-s", "proof.ys"], cwd=out,
                                 stdout=log, stderr=subprocess.STDOUT)
    unchanged = all(pin(p) == digest for p, digest in inputs.items())
    passed = (unchanged and process.returncode == 0
              and "SAT proof finished - no model found: SUCCESS!" in (out / "proof.log").read_text())
    result = dict(status="PASS" if passed else "FAIL", returncode=process.returncode,
                  inputs=inputs, inputs_unchanged=unchanged,
                  unchanged_controller_and_storage=True,
                  scope="All 41 defined CRC-state, data-byte and SOP input bits; no packet-valid, reachable-state, latency or timing assumption. Only the EOP predicate differs from the frozen controller.")
    (out / "result.json").write_text(json.dumps(result, indent=2) + "\n")
    return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--candidate", type=Path, default=ROOT / "hw/soc/rtl/pcie/soc_pcie_lcrc_rx.v")
    parser.add_argument("--out", type=Path, required=True)
    parser.add_argument("--yosys", type=Path, required=True)
    args = parser.parse_args()
    result = run(args.candidate, args.out, args.yosys)
    print(result["status"])
    return int(result["status"] != "PASS")


if __name__ == "__main__":
    raise SystemExit(main())
