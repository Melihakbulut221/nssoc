# SPDX-FileCopyrightText: 2026 Hasan Melih Akbulut
# SPDX-License-Identifier: Apache-2.0
"""Original dynamic read versus literal balanced payload mux, including X masking."""

from pathlib import Path
import runpy

import pytest

ROOT = Path(__file__).resolve().parents[2]
RTL = ROOT / "hw/soc/rtl/pcie"
GEN = runpy.run_path(str(ROOT / "scripts/generate_pcie_integrity_retire_v20.py"))
SIM = runpy.run_path(str(ROOT / "sw/tests/test_pcie_gen3_integrity_v3_crc.py"))["simulate"]
FAULTS = {
    **{f"ignore_lane_{n}": ("if(read_eligible_root[r])", f"if(r!={n} && read_eligible_root[r])") for n in range(4)},
    "rotate_root_lane": ("read_eligible_root[read_lane]=", "read_eligible_root[(read_lane+1)%4]="),
    "ignore_control_count": ("   read_any=0;", "   read_any=|read_eligible_root;"),
    "unknown_verdict_passes": ("&& slot_verdict[read_slot])", "&& (slot_verdict[read_slot] !== 1'b0))"),
    "latch_read_any": ("   read_any=0;", "   // fault: missing default"),
    "lose_selected_eligibility": ("if(read_eligible_root[r]) read_any=1;", "if(read_eligible_root[r]) read_any=0;"),
}



def test_exact_generated_inverse_and_wrapper_bridge():
    text = (RTL / "soc_pcie_gen3_framer_rx_integrity_v20.v").read_text()
    assert text == GEN["candidate"]()
    assert GEN["original"](text) == GEN["SOURCE"].read_text()
    for name in [
        "hw/soc/rtl/pcie/soc_pcie_gen3_continuous_rx_integrity_v19.v",
        "hw/soc/tb/cocotb/Makefile.soc_pcie_gen3_continuous_rx_integrity_v19",
        "scripts/check_pcie_gen3_continuous_rx_integrity_v19.py",
    ]:
        assert (ROOT / name.replace("_v19", "_v20")).read_text().replace(
            "integrity_v20", "integrity_v19"
        ) == (ROOT / name).read_text()
    old = ROOT / "hw/soc/tb/cocotb/test_soc_pcie_gen3_continuous_rx_integrity_v19.py"
    new = ROOT / "hw/soc/tb/cocotb/test_soc_pcie_gen3_continuous_rx_integrity_v20.py"
    assert new.read_bytes().startswith(old.read_bytes())
    added = new.read_text()[len(old.read_text()):]
    assert added.startswith("\n\n# BEGIN V20 STALLED ZERO KEEP RETIRE CASE\n")
    assert added.count("@cocotb.test()") == 1
    assert text.count(" || !read_any);") == 1
    assert "read_keep==0" not in text


def literal_module(name, ring, body):
    width = ring.bit_length()
    ports = [f"input[{width-1}:0]read_ptr,committed", "output reg[2:0]read_count", "output wire empty"]
    declarations = [f"localparam RING_DWORDS={ring},PW={width};", "reg slot_verdict[0:RING_DWORDS-1];"]
    for field, bits in GEN["FIELDS"].items():
        ports.append(f"output reg[{4*bits-1}:0]read_{field}")
        declarations.append(f"reg[{bits-1}:0]slot_{field}[0:RING_DWORDS-1];")
    return "module " + name + "(" + ",".join(ports) + ");\n" + "\n".join(declarations) + body + "assign empty=" + ("!read_any" if name == "new_read" else "(read_keep==0)") + ";\nendmodule\n"


def exercise(tmp_path, ring, fault):
    source = (RTL / "soc_pcie_gen3_framer_rx_integrity_v20.v").read_text()
    body = GEN["balanced_read"]()
    assert source.count(body) == 1
    if fault:
        before, after = FAULTS[fault]
        assert body.count(before) == 1
        body = body.replace(before, after)
    width = ring.bit_length()
    aliases, gold_ports, gate_ports, seed_fields, gold_bits, gate_bits = [], [], [], [], ["gold_count", "gold_empty"], ["gate_count", "gate_empty"]
    for name, bits in GEN["FIELDS"].items():
        aliases.append(f"wire[{4*bits-1}:0]gold_{name},gate_{name};")
        gold_ports.append(f".read_{name}(gold_{name})")
        gate_ports.append(f".read_{name}(gate_{name})")
        seed_fields.append(f"gold.slot_{name}[k]=$random(seed);gate.slot_{name}[k]=gold.slot_{name}[k];")
        gold_bits.append("gold_" + name)
        gate_bits.append("gate_" + name)
    compare = "{" + ",".join(gold_bits) + "} !== {" + ",".join(gate_bits) + "}"
    bench = literal_module("old_read", ring, GEN["original_read"]()) + literal_module("new_read", ring, body)
    bench += f"module tb;localparam RING={ring},PW={width};reg[PW-1:0]ptr=0,committed=0;wire gold_empty,gate_empty;wire[2:0]gold_count,gate_count;\n"
    bench += "\n".join(aliases) + "\n"
    bench += "old_read gold(.read_ptr(ptr),.committed(committed),.read_count(gold_count),.empty(gold_empty)," + ",".join(gold_ports) + ");\n"
    bench += "new_read gate(.read_ptr(ptr),.committed(committed),.read_count(gate_count),.empty(gate_empty)," + ",".join(gate_ports) + ");\n"
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
def test_literal_balanced_read_all_metadata_and_unknown_masking(tmp_path, ring):
    exercise(tmp_path, ring, None)


@pytest.mark.parametrize("fault", list(FAULTS))
def test_actual_select_and_mask_faults_are_detected(tmp_path, fault):
    exercise(tmp_path, 64, fault)


def fourstate(tmp_path, fault=False):
    """Actual literal selected X/Z and unknown conditions, all public read bits."""
    body = GEN["balanced_read"]()
    if fault:
        before = "read_payload_root[r];"
        assert body.count(before) == 1
        body = body.replace(before, "(60'b0 | read_payload_root[r]);")
    bench = literal_module("old_read", 16, GEN["original_read"]()) + literal_module("new_read", 16, body)
    declarations = []
    connections = {name: [] for name in ("gold", "gate")}
    vectors = {name: [name + "_count", name + "_empty"] for name in connections}
    for field, width in GEN["FIELDS"].items():
        declarations.append(f"wire[{4*width-1}:0]gold_{field},gate_{field};")
        for name in connections:
            connections[name].append(f".read_{field}({name}_{field})")
            vectors[name].append(name + "_" + field)
    bench += "module tb;reg[4:0]ptr=15,committed=4;wire gold_empty,gate_empty;wire[2:0]gold_count,gate_count;integer k,n=0;\n"
    bench += "\n".join(declarations) + "\n"
    for name, module in [("gold", "old_read"), ("gate", "new_read")]:
        bench += f"{module} {name}(.read_ptr(ptr),.committed(committed),.read_count({name}_count),.empty({name}_empty)," + ",".join(connections[name]) + ");\n"
    compare = "{" + ",".join(vectors["gold"]) + "} !== {" + ",".join(vectors["gate"]) + "}"
    bench += "task check;begin #1;if(" + compare + ")$fatal(1,\"BALANCED_4STATE_MISMATCH case=%0d\",n);n=n+1;end endtask\n"
    bench += "task seed;begin ptr=15;committed=4;for(k=0;k<16;k=k+1)begin\n"
    for field, width in GEN["FIELDS"].items():
        bench += f"gold.slot_{field}[k]={width}'h" + ("f" if field == "keep" else "1") + f";gate.slot_{field}[k]=gold.slot_{field}[k];\n"
    bench += "gold.slot_verdict[k]=1;gate.slot_verdict[k]=1;end end endtask\ninitial begin\nseed;check;\n"
    cases = 1
    # Four lane positions across ring wrap, every field with literal X and Z.
    # Keep retains a known 1 bit, so selected X/Z is eligible and observable.
    for lane in range(4):
        slot = (15 + lane) & 15
        for field, width in GEN["FIELDS"].items():
            for symbol in ("x", "z"):
                value = "1" + symbol * (width - 1) if field == "keep" else symbol * width
                bench += f"seed;gold.slot_{field}[{slot}]={width}'b{value};gate.slot_{field}[{slot}]=gold.slot_{field}[{slot}];check;\n"
                cases += 1
    for symbol in ("x", "z"):
        for target in ("ptr", "committed", "keep", "verdict"):
            bench += "seed;"
            if target in ("ptr", "committed"):
                bench += f"{target}[0]=1'b{symbol};"
            elif target == "keep":
                bench += f"gold.slot_keep[15]=4'b{symbol*4};gate.slot_keep[15]=gold.slot_keep[15];"
            else:
                bench += f"gold.slot_verdict[15]=1'b{symbol};gate.slot_verdict[15]=gold.slot_verdict[15];"
            bench += "check;\n"
            cases += 1
    # Entirely unselected slots may contain high impedance in every field.
    for symbol in ("x", "z"):
        bench += "seed;"
        for field, width in GEN["FIELDS"].items():
            bench += f"gold.slot_{field}[8]={width}'b{symbol*width};gate.slot_{field}[8]=gold.slot_{field}[8];"
        bench += f"gold.slot_verdict[8]=1'b{symbol};gate.slot_verdict[8]=gold.slot_verdict[8];check;\n"
        cases += 1
    bench += f'if(n!={cases})$fatal(1,"BALANCED_4STATE_COVERAGE");$display("PASS_BALANCED_4STATE cases=%0d",n);$finish;end endmodule\n'
    result, log = SIM(tmp_path, bench)
    if fault:
        assert result.returncode != 0 and "BALANCED_4STATE_MISMATCH" in log
    else:
        assert result.returncode == 0 and f"PASS_BALANCED_4STATE cases={cases}" in log


def test_literal_selected_x_z_fields_and_unknown_conditions(tmp_path):
    fourstate(tmp_path)


def test_actual_payload_or_z_conversion_fault_is_detected(tmp_path):
    fourstate(tmp_path, fault=True)


EVENTS = ["read_address"] + ["slot_" + name + "[read_slot]" for name in GEN["FIELDS"]] + ["slot_verdict[read_slot]"]


def isolated_sensitivity(tmp_path, fault=None):
    """Change each leaf input alone, including hidden-to-visible transitions."""
    body = GEN["balanced_read"]()
    assert (RTL / "soc_pcie_gen3_framer_rx_integrity_v20.v").read_text().count(body) == 1
    header = "always @(" + " or ".join(EVENTS) + ")"
    assert body.count(header) == 1
    if fault == "wrong_data_event_slot":
        body = body.replace(header, header.replace("slot_data[read_slot]", "slot_data[(read_slot+1)%RING_DWORDS]"))
    elif fault is not None:
        assert fault in EVENTS
        body = body.replace(header, "always @(" + " or ".join(term for term in EVENTS if term != fault) + ")")
    aliases = []
    connections = {name: [] for name in ("gold", "gate")}
    vectors = {name: [name + "_count", name + "_empty"] for name in connections}
    for field, width in GEN["FIELDS"].items():
        aliases.append(f"wire[{4*width-1}:0]gold_{field},gate_{field};")
        for name in connections:
            connections[name].append(f".read_{field}({name}_{field})")
            vectors[name].append(name + "_" + field)
    bench = literal_module("old_read", 16, GEN["original_read"]()) + literal_module("new_read", 16, body)
    bench += "module tb;reg[4:0]ptr=0,committed=4;wire gold_empty,gate_empty;wire[2:0]gold_count,gate_count;integer k,n=0;\n"
    bench += "\n".join(aliases) + "\n"
    for name, module in [("gold", "old_read"), ("gate", "new_read")]:
        bench += f"{module} {name}(.read_ptr(ptr),.committed(committed),.read_count({name}_count),.empty({name}_empty)," + ",".join(connections[name]) + ");\n"
    compare = "{" + ",".join(vectors["gold"]) + "} !== {" + ",".join(vectors["gate"]) + "}"
    bench += "task check;begin #1;if(" + compare + ")$fatal(1,\"ISOLATED_SENSITIVITY_MISMATCH case=%0d\",n);n=n+1;end endtask\n"
    bench += "initial begin\nfor(k=0;k<16;k=k+1)begin\n"
    for field in GEN["FIELDS"]:
        bench += f"gold.slot_{field}[k]=" + ("15" if field == "keep" else "k+1") + f";gate.slot_{field}[k]=gold.slot_{field}[k];\n"
    bench += "gold.slot_verdict[k]=1;gate.slot_verdict[k]=1;end\ncheck;\n"
    cases = 1
    for field, width in GEN["FIELDS"].items():
        values = [f"{width}'h2"] + [f"{width}'b" + ("1" + symbol * (width - 1) if field == "keep" else symbol * width) for symbol in ("x", "z")]
        for value in values:
            bench += f"gold.slot_{field}[0]={value};gate.slot_{field}[0]=gold.slot_{field}[0];check;\n"
            cases += 1
    steps = [
        "gold.slot_verdict[0]=0;gate.slot_verdict[0]=0;",
        "gold.slot_data[0]=32'hdeadbeef;gate.slot_data[0]=32'hdeadbeef;",
        "gold.slot_verdict[0]=1;gate.slot_verdict[0]=1;",
        "gold.slot_keep[0]=0;gate.slot_keep[0]=0;",
        "gold.slot_sequence[0]=12'habc;gate.slot_sequence[0]=12'habc;",
        "gold.slot_keep[0]=15;gate.slot_keep[0]=15;",
        "ptr=4;", "ptr=5'bxxxxx;", "ptr=0;", "committed=0;",
        "gold.slot_data[0]=32'hcababcde;gate.slot_data[0]=32'hcababcde;",
        "committed=4;",
    ]
    for change in steps:
        bench += change + "check;\n"
        cases += 1
    assert cases == 31
    bench += f'if(n!={cases})$fatal(1,"SENSITIVITY_COVERAGE");$display("PASS_ISOLATED_SENSITIVITY cases=%0d",n);$finish;end endmodule\n'
    result, log = SIM(tmp_path, bench)
    if fault is None:
        assert result.returncode == 0 and "PASS_ISOLATED_SENSITIVITY cases=31" in log
    else:
        assert result.returncode != 0 and "ISOLATED_SENSITIVITY_MISMATCH" in log


def test_isolated_leaf_events_and_inactive_to_active_transitions(tmp_path):
    isolated_sensitivity(tmp_path)


def test_exhaustive_local_fourstate_retire_predicate_and_masks(tmp_path):
    """All local keep/verdict patterns and all five-bit count/address patterns."""
    body = GEN["balanced_read"]()
    bench = literal_module("old_read", 16, GEN["original_read"]())
    bench += literal_module("new_read", 16, body)
    fields = list(GEN["FIELDS"].items())
    ports = {name: [] for name in ("gold", "gate")}
    vectors = {name: [name + "_count", name + "_empty"] for name in ports}
    bench += "module tb;reg[4:0]ptr=15,committed=4;wire gold_empty,gate_empty;wire[2:0]gold_count,gate_count;integer k,v,lane,i,n=0,selected;\n"
    for field, width in fields:
        bench += f"wire[{4*width-1}:0]gold_{field},gate_{field};\n"
        for name in ports:
            ports[name].append(f".read_{field}({name}_{field})")
            vectors[name].append(name + "_" + field)
    for name, module in [("gold", "old_read"), ("gate", "new_read")]:
        bench += f"{module} {name}(.read_ptr(ptr),.committed(committed),.read_count({name}_count),.empty({name}_empty)," + ",".join(ports[name]) + ");\n"
    compare = "{" + ",".join(vectors["gold"]) + "} !== {" + ",".join(vectors["gate"]) + "}"
    bench += """function[4:0] quad5;input integer value;integer bitno;begin
for(bitno=0;bitno<5;bitno=bitno+1)begin
case((value>>(2*bitno))&3)0:quad5[bitno]=0;1:quad5[bitno]=1;2:quad5[bitno]=1'bx;3:quad5[bitno]=1'bz;endcase
end end endfunction
"""
    bench += "task check;begin #1;if(" + compare + ")$fatal(1,\"V20_4STATE_RETIRE_MISMATCH case=%0d\",n);if(gold_empty!==1'b0&&gold_empty!==1'b1)$fatal(1,\"V20_GOLD_EMPTY_UNKNOWN\");n=n+1;end endtask\n"
    bench += "task seed;begin ptr=15;committed=4;for(i=0;i<16;i=i+1)begin\n"
    for field, width in fields:
        value = "0" if field == "keep" else "i+1"
        bench += f"gold.slot_{field}[i]={value};gate.slot_{field}[i]=gold.slot_{field}[i];\n"
    bench += "gold.slot_verdict[i]=1;gate.slot_verdict[i]=1;end end endtask\ninitial begin\n"
    bench += """// Every four-state keep nibble and verdict value, one selected lane.
for(lane=0;lane<4;lane=lane+1)begin
 for(k=0;k<256;k=k+1)begin
  for(v=0;v<4;v=v+1)begin
   seed;selected=(15+lane)&15;
   gold.slot_keep[selected]=quad5(k);gate.slot_keep[selected]=gold.slot_keep[selected];
   gold.slot_verdict[selected]=quad5(v);gate.slot_verdict[selected]=gold.slot_verdict[selected];check;
  end
 end
end
if(n!=4096)$fatal(1,"V20_KEEP_VERDICT_COVERAGE");
// All 4^5 count words, preserving procedural unknown comparison masking.
for(lane=0;lane<4;lane=lane+1)begin
 for(k=0;k<1024;k=k+1)begin
  seed;selected=(15+lane)&15;
  gold.slot_keep[selected]=4'b1zzx;gate.slot_keep[selected]=gold.slot_keep[selected];
  committed=quad5(k);check;
 end
end
if(n!=8192)$fatal(1,"V20_COUNT_COVERAGE");
// All 4^5 pointer words, including unknown lower bits and wrap/epoch bit.
for(k=0;k<1024;k=k+1)begin
 seed;for(i=0;i<16;i=i+1)begin gold.slot_keep[i]=4'b1xz0;gate.slot_keep[i]=gold.slot_keep[i];end
 ptr=quad5(k);check;
end
if(n!=9216)$fatal(1,"V20_POINTER_COVERAGE");
$display("PASS_V20_EXHAUSTIVE_LOCAL_FOURSTATE cases9216 keep_verdict4096 count4096 pointer1024");$finish;end endmodule
"""
    result, log = SIM(tmp_path, bench)
    assert result.returncode == 0 and "PASS_V20_EXHAUSTIVE_LOCAL_FOURSTATE cases9216" in log
