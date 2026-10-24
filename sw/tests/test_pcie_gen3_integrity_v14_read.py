# SPDX-FileCopyrightText: 2026 Hasan Melih Akbulut
# SPDX-License-Identifier: Apache-2.0
"""Original dynamic read versus literal parallel select, including X masking."""

from pathlib import Path
import runpy

import pytest

ROOT = Path(__file__).resolve().parents[2]
RTL = ROOT / "hw/soc/rtl/pcie"
GEN = runpy.run_path(str(ROOT / "scripts/generate_pcie_integrity_read_v14.py"))
SIM = runpy.run_path(str(ROOT / "sw/tests/test_pcie_gen3_integrity_v3_crc.py"))["simulate"]
FAULTS = {
    "wrong_address": ("read_address=(read_ptr+r)&", "read_address=(read_ptr+r+1)&"),
    "missing_slot": ("read_address==read_slot &&", "read_address==read_slot && read_slot!=7 &&"),
    "ignore_verdict": ("&& slot_verdict[read_slot])", "&& 1'b1)"),
    "ignore_keep": ("slot_keep[read_slot]!=0", "1'b1"),
    "wrong_sequence_slot": ("|slot_sequence[read_slot]", "|slot_sequence[(read_slot+1)%RING_DWORDS]"),
    "lost_lane_offset": ("read_address=(read_ptr+r)&", "read_address=read_ptr&"),
    "unknown_verdict_passes": ("&& slot_verdict[read_slot])", "&& (slot_verdict[read_slot] !== 1'b0))"),
}


def test_exact_generated_inverse_and_wrapper_bridge():
    text = (RTL / "soc_pcie_gen3_framer_rx_integrity_v14.v").read_text()
    assert text == GEN["candidate"]()
    assert text.count(GEN["parallel_read"]()) == 1
    restored = text.replace(GEN["parallel_read"](), GEN["original_read"]())
    assert restored.replace("integrity_v14", "integrity_v11") == GEN["SOURCE"].read_text()
    for name in [
        "hw/soc/rtl/pcie/soc_pcie_gen3_continuous_rx_integrity_v11.v",
        "hw/soc/tb/cocotb/test_soc_pcie_gen3_continuous_rx_integrity_v11.py",
        "hw/soc/tb/cocotb/Makefile.soc_pcie_gen3_continuous_rx_integrity_v11",
    ]:
        assert (ROOT / name.replace("_v11", "_v14")).read_text().replace("integrity_v14", "integrity_v11") == (ROOT / name).read_text()


def literal_module(name, ring, body):
    width = ring.bit_length()
    ports = [f"input[{width-1}:0]read_ptr,committed", "output reg[2:0]read_count"]
    declarations = [f"localparam RING_DWORDS={ring},PW={width};", "reg slot_verdict[0:RING_DWORDS-1];"]
    for field, bits in GEN["FIELDS"].items():
        ports.append(f"output reg[{4*bits-1}:0]read_{field}")
        declarations.append(f"reg[{bits-1}:0]slot_{field}[0:RING_DWORDS-1];")
    return "module " + name + "(" + ",".join(ports) + ");\n" + "\n".join(declarations) + body + "endmodule\n"


def exercise(tmp_path, ring, fault):
    source = (RTL / "soc_pcie_gen3_framer_rx_integrity_v14.v").read_text()
    body = GEN["parallel_read"]()
    assert source.count(body) == 1
    if fault:
        before, after = FAULTS[fault]
        assert body.count(before) == 1
        body = body.replace(before, after)
    width = ring.bit_length()
    aliases, gold_ports, gate_ports, seed_fields, gold_bits, gate_bits = [], [], [], [], ["gold_count"], ["gate_count"]
    for name, bits in GEN["FIELDS"].items():
        aliases.append(f"wire[{4*bits-1}:0]gold_{name},gate_{name};")
        gold_ports.append(f".read_{name}(gold_{name})")
        gate_ports.append(f".read_{name}(gate_{name})")
        seed_fields.append(f"gold.slot_{name}[k]=$random(seed);gate.slot_{name}[k]=gold.slot_{name}[k];")
        gold_bits.append("gold_" + name)
        gate_bits.append("gate_" + name)
    compare = "{" + ",".join(gold_bits) + "} !== {" + ",".join(gate_bits) + "}"
    bench = literal_module("old_read", ring, GEN["original_read"]()) + literal_module("new_read", ring, body)
    bench += f"module tb;localparam RING={ring},PW={width};reg[PW-1:0]ptr=0,committed=0;wire[2:0]gold_count,gate_count;\n"
    bench += "\n".join(aliases) + "\n"
    bench += "old_read gold(.read_ptr(ptr),.committed(committed),.read_count(gold_count)," + ",".join(gold_ports) + ");\n"
    bench += "new_read gate(.read_ptr(ptr),.committed(committed),.read_count(gate_count)," + ",".join(gate_ports) + ");\n"
    bench += """integer n,k,seed=1471337,unknown_cases=0,wraps=0,zero_count=0,partial_count=0,full_count=0;
initial begin
for(n=0;n<4096;n=n+1) begin
 for(k=0;k<RING;k=k+1) begin
""" + "\n".join(seed_fields) + """
   gold.slot_verdict[k]=$random(seed);gate.slot_verdict[k]=gold.slot_verdict[k];
 end
 ptr=n;committed=(n%8<5)?n%8:$random(seed);
 if((ptr&(RING-1))>RING-4)wraps=wraps+1;
 if(committed==0)zero_count=zero_count+1;
 else if(committed<4)partial_count=partial_count+1;
 else full_count=full_count+1;
 // Keep and verdict may be unknown even in a selected slot. Procedural if
 // must keep the reference's not-true masking. Unknown selected payloads
 // remain unknown when the slot is eligible; unrelated unknowns never leak.
 if(n%17==3) begin
   k=ptr&(RING-1);gold.slot_verdict[k]=1'bx;gate.slot_verdict[k]=1'bx;
   gold.slot_keep[k]=4'hf;gate.slot_keep[k]=4'hf;committed=4;unknown_cases=unknown_cases+1;
 end
 if(n%29==7) begin
   k=ptr&(RING-1);gold.slot_keep[k]=4'bxxxx;gate.slot_keep[k]=4'bxxxx;
   gold.slot_verdict[k]=1;gate.slot_verdict[k]=1;committed=4;unknown_cases=unknown_cases+1;
 end
 if(n%41==11) begin
   k=ptr&(RING-1);gold.slot_data[k]=32'bx;gate.slot_data[k]=32'bx;
   gold.slot_keep[k]=4'hf;gate.slot_keep[k]=4'hf;gold.slot_verdict[k]=1;gate.slot_verdict[k]=1;
   committed=4;unknown_cases=unknown_cases+1;
 end
 if(n%53==9) begin ptr[0]=1'bx;unknown_cases=unknown_cases+1;end
 if(n%71==13) begin committed[1]=1'bx;unknown_cases=unknown_cases+1;end
 #1;
 if(COMPARE)$fatal(1,"PARALLEL_READ_MISMATCH sample=%0d",n);
end
if(unknown_cases<500||wraps<50||zero_count<400||partial_count<1000||full_count<1000)$fatal(1,"PARALLEL_READ_COVERAGE");
$display("PASS_LITERAL_PARALLEL_READ4096 ring=%0d unknown=%0d wraps=%0d partial=%0d",RING,unknown_cases,wraps,partial_count);$finish;
end endmodule
""".replace("COMPARE", compare)
    result, log = SIM(tmp_path, bench)
    if fault:
        assert result.returncode != 0 and "PARALLEL_READ_MISMATCH" in log
    else:
        assert result.returncode == 0 and "PASS_LITERAL_PARALLEL_READ4096" in log


@pytest.mark.parametrize("ring", [16, 64, 128])
def test_literal_parallel_read_all_metadata_and_unknown_masking(tmp_path, ring):
    exercise(tmp_path, ring, None)


@pytest.mark.parametrize("fault", list(FAULTS))
def test_actual_select_and_mask_faults_are_detected(tmp_path, fault):
    exercise(tmp_path, 64, fault)
