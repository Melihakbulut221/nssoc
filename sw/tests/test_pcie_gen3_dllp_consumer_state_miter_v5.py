# SPDX-FileCopyrightText: 2026 Hasan Melih Akbulut
# SPDX-License-Identifier: Apache-2.0
"""Actual finite arbitrary-prestate V4/V5 next-state comparison, not a proof."""
import hashlib
import json
from pathlib import Path
import re
import resource
import shutil
import subprocess

import pytest

ROOT = Path(__file__).resolve().parents[2]
OLD = ROOT / "hw/soc/rtl/pcie/soc_pcie_gen3_dllp_consumer_v4.v"
NEW = ROOT / "hw/soc/rtl/pcie/soc_pcie_gen3_dllp_consumer_v5.v"
FIELDS = dict(desc="nd", started="ns", done="nf", good="ng", nul="nn",
              bad="nb", dllp="nk", body_kind="nbodykind", size="nz",
              received="nr", seq="nseq", raw="nraw")
SCALARS = ("desc_ptr", "event_ptr", "epoch", "halted_o", "event_count", "event_owner",
           "event_sequence", "event_ack", "event_fc_data", "event_bytes", "event_kind",
           "event_raw", "event_phase", "event_class", "event_header")
NEXT = ("desc_next", "event_next", "protocol_error", "entry_error", "released",
        "desc_count", "desc_space", "body_space", "event_count_n", "event_owner_n",
        "event_sequence_n", "event_bytes_n", "event_kind_n", "event_raw_n", "event_ack_n",
        "event_phase_n", "event_class_n", "event_header_n", "event_fc_data_n")


def ports(text):
    header = text[text.index("(\n") + 2:text.index("\n);")]
    result = []
    for item in header.split(","):
        item = item.strip()
        match = re.fullmatch(r"(input|output)\s+(?:wire|reg)\s*(\[[^\]]+\])?\s*(\w+)", item)
        if match:
            direction, width, name = match.groups()
        else:
            assert re.fullmatch(r"\w+", item), item
            name = item
        result.append((direction, width or "", name))
    assert len(result) == 44
    return result


def bench():
    interface = ports(OLD.read_text())
    assert interface == ports(NEW.read_text())
    out = ["`timescale 1ns/1ps\nmodule test;\n"]
    for direction, width, name in interface:
        out.append((f"reg {width} {name};\n" if direction == "input" else
                    f"wire {width} old_{name},new_{name};\n"))
    for version, instance in ((4, "old"), (5, "new")):
        connections = ",".join(f".{name}({name if direction == 'input' else instance+'_'+name})"
                               for direction, width, name in interface)
        out.append(f"soc_pcie_gen3_dllp_consumer_v{version} {instance}_dut({connections});\n")
    out.append("""integer seed,trial,entry,lane,mode,target,other,observed;
function [127:0] random128;
 begin random128={$random(seed),$random(seed),$random(seed),$random(seed)};end
endfunction
initial begin
 seed=32'h47ab3901;clk_i=0;rst_ni=1;observed=0;
 for(trial=0;trial<2560;trial=trial+1) begin
  mode=trial%10;target=(trial*17)&63;other=(target+1)&63;
""")
    for direction, width, name in interface:
        if direction == "input" and name not in ("clk_i", "rst_ni"):
            out.append(f"  {name}=random128();\n")
    for field in SCALARS:
        out.append(f"  old.{field}=random128();new.{field}=old.{field};\n")
    out.append("  for(entry=0;entry<64;entry=entry+1) begin\n")
    for field in FIELDS:
        out.append(f"   old.{field}[entry]=random128();new.{field}[entry]=old.{field}[entry];\n")
    out.append("""  end
  if(mode!=0) begin
   flush_i=0;epoch_i=old.epoch;old.halted_o=0;new.halted_o=0;
   body_valid_i=1;tlp_ready_i=1;event_ready_i=0;descriptor_valid_i=0;
   body_keep_i=16'hffff;body_sop_i=0;body_eop_i=0;body_dllp_i=0;
   old.event_count=0;new.event_count=0;
   for(lane=0;lane<4;lane=lane+1) begin
    if(mode==1 || mode==5) entry=(target+lane)&63;
    else if(mode==3) entry=(lane&1)?other:target;
    else entry=target;
    body_owner_i[lane*6+:6]=entry;
    old.desc[entry]=0;old.started[entry]=1;old.done[entry]=0;old.body_kind[entry]=0;
    old.received[entry]=(trial/10)%2?8191:13'd8189;
   end
   if(mode==4) body_keep_i=16'h0f0f;
   if(mode==5) begin
    old.event_count=4;old.event_ptr=(target-4)&63;old.desc_ptr=target;event_ready_i=1;
    descriptor_valid_i=15;descriptor_good_i=15;descriptor_nullified_i=0;descriptor_crc_bad_i=0;descriptor_dllp_i=15;
    body_keep_i=16'h3333;body_sop_i=16'h1111;body_dllp_i=16'h3333;
    for(lane=0;lane<4;lane=lane+1) begin
     old.event_owner[lane*6+:6]=(target+lane)&63;
     descriptor_owner_i[lane*6+:6]=(target+lane)&63;
     descriptor_bytes_i[lane*13+:13]=6;
     old.desc[(target+lane)&63]=1;old.good[(target+lane)&63]=1;
    end
   end
   if(mode==6) begin old.event_count=(trial/10)%4+1;event_ready_i=0;body_valid_i=0;descriptor_valid_i=0;end
   if(mode==7) begin body_keep_i=16'hfff7;old.received[target]=8191;end
   if(mode==8) begin flush_i=(trial/10)%2;epoch_i=old.epoch+1;end
   if(mode==9) begin
    old.desc_ptr=target;descriptor_valid_i=15;descriptor_good_i=15;descriptor_nullified_i=0;descriptor_crc_bad_i=0;
    for(lane=0;lane<4;lane=lane+1) begin descriptor_owner_i[lane*6+:6]=target;descriptor_bytes_i[lane*13+:13]=lane?6:7;end
   end
""")
    # Recopy the complete changed prestate. Inputs are shared, clock stays low.
    for field in SCALARS:
        out.append(f"   new.{field}=old.{field};\n")
    out.append("   for(entry=0;entry<64;entry=entry+1) begin\n")
    for field in FIELDS:
        out.append(f"    new.{field}[entry]=old.{field}[entry];\n")
    out.append("   end\n  end\n  #1;\n  for(entry=0;entry<64;entry=entry+1) begin\n")
    for field in FIELDS.values():
        out.append(f'   if(old.{field}[entry] !== new.{field}[entry]) $fatal(1,"STATE_MITER_MISMATCH field={field} trial=%d mode=%d entry=%d",trial,mode,entry);\n')
    out.append("  end\n")
    for field in NEXT:
        out.append(f'  if(old.{field} !== new.{field}) $fatal(1,"STATE_MITER_MISMATCH scalar={field} trial=%d mode=%d",trial,mode);\n')
    for direction, width, name in interface:
        if direction == "output":
            out.append(f'  if(old_{name} !== new_{name}) $fatal(1,"STATE_MITER_MISMATCH port={name} trial=%d mode=%d",trial,mode);\n')
    out.append('  observed=observed+1;\n end\n $display("FINITE_STATE_MITER_PASS vectors=%d entries=64 fields=12 modes=10",observed);$finish;\nend\nendmodule\n')
    return "".join(out).replace("old.", "old_dut.").replace("new.", "new_dut.")


def pin(path):
    return dict(bytes=path.stat().st_size, sha256=hashlib.sha256(path.read_bytes()).hexdigest())


def limits():
    resource.setrlimit(resource.RLIMIT_AS, (2*1024**3, 2*1024**3))
    resource.setrlimit(resource.RLIMIT_CORE, (0, 0))


def run(tmp, mutation=None):
    src = tmp / "test.v"
    src.write_text(bench())
    candidate = NEW
    if mutation:
        before, after = mutation
        source = NEW.read_text()
        assert source.count(before) == 1
        candidate = tmp / "mutant.v"
        candidate.write_text(source.replace(before, after))
    compiler, runtime = shutil.which("iverilog"), shutil.which("vvp")
    assert compiler and runtime
    commands = [[compiler, "-g2012", "-s", "test", "-o", str(tmp / "sim.vvp"), str(src), str(OLD), str(candidate)],
                [runtime, str(tmp / "sim.vvp")]]
    compile_result = subprocess.run(commands[0], capture_output=True, text=True, preexec_fn=limits)
    (tmp / "compile.log").write_text(compile_result.stdout+compile_result.stderr)
    assert compile_result.returncode == 0
    result = subprocess.run(commands[1], capture_output=True, text=True, preexec_fn=limits)
    (tmp / "simulation.log").write_text(result.stdout+result.stderr)
    record = dict(sources={str(p):pin(p) for p in (OLD, NEW, Path(__file__))},
                  runtime={str(Path(p).resolve()):pin(Path(p).resolve()) for p in (compiler, runtime)},
                  commands=commands, mutation=mutation, returncode=result.returncode,
                  outputs={p.name:pin(p) for p in tmp.iterdir() if p.is_file()},
                  scope="Finite identical arbitrary-prestate V4/V5 combinational comparison; all64 next-entry fields,19 next/control scalars and all public ports. Not all-state formal equivalence or native-cell/timing evidence.")
    (tmp / "result.json").write_text(json.dumps(record, indent=2)+"\n")
    return result


def test_actual_finite_all_entry_next_state_comparison(tmp_path):
    result = run(tmp_path)
    assert result.returncode == 0 and "FINITE_STATE_MITER_PASS vectors=       2560" in result.stdout


@pytest.mark.parametrize("before,after", [
    ("if(body_write[previous] &&", "if(1'b0 &&"),
    ("for(scatter_lane=0;scatter_lane<4;scatter_lane=scatter_lane+1)", "for(scatter_lane=3;scatter_lane>=0;scatter_lane=scatter_lane-1)"),
    ("}=incoming_context;", "}=incoming_context;local_entry_error=0;"),
    ("if(released[entry]) begin", "if(1'b0) begin"),
], ids=["forwarding_lost", "last_writer_lost", "sticky_error_lost", "release_lost"])
def test_actual_next_state_mutants_rejected(tmp_path, before, after):
    result = run(tmp_path, (before, after))
    assert result.returncode != 0 and "STATE_MITER_MISMATCH" in result.stdout
