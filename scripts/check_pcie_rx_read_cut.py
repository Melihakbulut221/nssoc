# SPDX-FileCopyrightText: 2026 Hasan Melih Akbulut
# SPDX-License-Identifier: Apache-2.0
"""Check RX memory reads with arbitrary initialized contents and addresses.

This supplements sequential equivalence: initially undefined memories must not
make an incorrect read expression vacuously pass. Only language-defined array
addresses are required. There is no output-valid or reachable-state assumption.
"""

import hashlib
import json
from pathlib import Path
import re
import subprocess

ROOT = Path(__file__).resolve().parents[1]
REFERENCE_SHA = "ea4977440f6e111cb87967385012835720cf2581d8b1c3d03608d55f097ffae8"


def pin(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def read_expression(text):
    # Fail closed on changes to the state shape that this cut represents.
    for declaration in (
        "CAP=MAX_TLP_DWORDS*4+6", "SLOTS=3*SLOTS_PER_CLASS",
        "CW=$clog2(CAP+2),SW=$clog2(SLOTS+1)",
        "reg [7:0] packets[0:SLOTS*CAP-1];", "reg [7:0] dllp[0:5];",
    ):
        if text.count(declaration) != 1:
            raise ValueError("RX read-cut state shape changed: " + declaration)
    if len(re.findall(r"\bassign\s+out_data_o\s*=", text)) != 1:
        raise ValueError("Unique RX data output assignment required")
    starts = [text.find(s) for s in (
        "    localparam integer READ_VALUES=", "    wire [7:0] bank_byte",
        "    assign out_data_o=",
    )]
    start = min(s for s in starts if s >= 0)
    end = text.index("    assign out_sop_o", start)
    return text[start:end]


def run(candidate, out, yosys, parameters=None):
    candidate, out, yosys = map(lambda p: Path(p).resolve(), (candidate, out, yosys))
    parameters = parameters or {}
    dwords = parameters.get("MAX_TLP_DWORDS", 8)
    per_class = parameters.get("SLOTS_PER_CLASS", 2)
    if type(dwords) is not int or type(per_class) is not int or dwords < 3 or per_class < 1:
        raise ValueError("Unsupported RX memory dimensions")
    cap, slots = dwords * 4 + 6, 3 * per_class
    reference = ROOT / "sw/tests/fixtures/pcie_chip_timing/flat-rx.v"
    if pin(reference) != REFERENCE_SHA:
        raise ValueError("Frozen RX reference changed")
    gold, gate = read_expression(reference.read_text()), read_expression(candidate.read_text())
    out.mkdir(parents=True, exist_ok=False)
    header = f"""module NAME(
 input [8*{slots*cap}-1:0] packet_bits,input [47:0] dllp_bits,
 input [$clog2({cap}+2)-1:0] output_index,
 input [$clog2({slots}+1)-1:0] head_slot,input select_dllp,
 output [7:0] out_data_o,output defined_read);
 localparam integer CAP={cap},SLOTS={slots},CW=$clog2(CAP+2),SW=$clog2(SLOTS+1);
 wire [7:0] packets[0:SLOTS*CAP-1]; wire [7:0] dllp[0:5];
 genvar cut_n;
 generate for(cut_n=0;cut_n<SLOTS*CAP;cut_n=cut_n+1)begin: cut_packet
 assign packets[cut_n]=packet_bits[8*cut_n+:8];end
 for(cut_n=0;cut_n<6;cut_n=cut_n+1)begin: cut_dllp
 assign dllp[cut_n]=dllp_bits[8*cut_n+:8];end endgenerate
 assign defined_read=select_dllp ? output_index<6 :
 head_slot<SLOTS && head_slot*CAP+output_index<SLOTS*CAP;
"""
    for name, body in (("gold", gold), ("gate", gate)):
        (out / (name + ".v")).write_text(header.replace("NAME", name) + body + "\nendmodule\n")
    recipe = """read_verilog -sv gold.v gate.v
proc
memory_map
opt
miter -equiv -ignore_gold_x -make_outputs -make_assert -flatten gold gate miter
hierarchy -top miter
opt_clean
sat -enable_undef -set-def-inputs -set gold_defined_read 1 -verify -prove-asserts -show-inputs -show-outputs
"""
    (out / "proof.ys").write_text(recipe)
    inputs = {str(p): pin(p) for p in (
        reference, candidate, yosys, Path(__file__),
        out / "gold.v", out / "gate.v", out / "proof.ys",
    )}
    with (out / "proof.log").open("w") as log:
        process = subprocess.run([yosys, "-s", "proof.ys"], cwd=out,
                                 stdout=log, stderr=subprocess.STDOUT)
    unchanged = all(pin(Path(p)) == digest for p, digest in inputs.items())
    passed = (process.returncode == 0 and unchanged
              and "SAT proof finished - no model found: SUCCESS!" in (out / "proof.log").read_text())
    result = dict(status="PASS" if passed else "FAIL", returncode=process.returncode,
                  parameters=parameters, inputs=inputs, inputs_unchanged=unchanged,
                  scope="Arbitrary defined memory bits, head slot and byte index; all language-defined array addresses including cross-bank reads. No out_valid mask or sequential/physical timing claim.")
    (out / "result.json").write_text(json.dumps(result, indent=2) + "\n")
    return result
