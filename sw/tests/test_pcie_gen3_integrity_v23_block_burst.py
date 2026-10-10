# SPDX-FileCopyrightText: 2026 Hasan Melih Akbulut
# SPDX-License-Identifier: Apache-2.0
"""Real framer input bursts exercise the otherwise idle next-bank promotion."""

import ast
import hashlib
import json
from pathlib import Path
import re
import resource
import runpy
import shutil
import subprocess
import zlib

ROOT = Path(__file__).resolve().parents[2]
RTL = ROOT / "hw/soc/rtl/pcie"
BENCH = ROOT / "hw/soc/tb/cocotb/test_soc_pcie_gen3_continuous_rx_integrity_v23.py"


def pin(path):
    return {"bytes": path.stat().st_size, "sha256": hashlib.sha256(path.read_bytes()).hexdigest()}


def stimulus():
    # Reuse only the unchanged independent scalar encoder, never producer RTL.
    tree = ast.parse(BENCH.read_text())
    names = {"crc4", "tlp", "wire_tlp"}
    body = [n for n in tree.body if isinstance(n, ast.FunctionDef) and n.name in names]
    assert {n.name for n in body} == names
    namespace = {"zlib": zlib}
    exec(compile(ast.Module(body=body, type_ignores=[]), str(BENCH), "exec"), namespace)
    packets = [namespace["tlp"](0x123)]
    packets += [namespace["tlp"](0x200 + j, payload=(0, 4, 12, 32)[j % 4], four=bool(j & 1)) for j in range(24)]
    raw = bytes(60) + b"".join(namespace["wire_tlp"](p) for p in packets)
    raw += bytes((60 - len(raw)) % 64) + bytes.fromhex("1f809000")
    assert len(raw) % 64 == 0
    blocks = []
    for offset in range(0, len(raw), 64):
        b = raw[offset:offset + 64]
        blocks.append(sum(b[4 * word + lane] << (128 * lane + 8 * word) for lane in range(4) for word in range(16)))
    expected = [(byte, i == 0, i == len(p) - 1, int.from_bytes(p[:2], "big")) for p in packets for i, byte in enumerate(p)]
    return blocks, expected, len(packets)


def bench(blocks, expected, packets):
    inputs = {"clk_i": 1, "rst_ni": 1, "flush_i": 1, "stream_start_i": 1,
              "stream_abort_i": 1, "block_valid_i": 1, "headers_i": 8,
              "payload_i": 512, "block_error_i": 1, "ready_i": 1}
    outputs = {"block_ready_o": 1, "valid_o": 1, "data_o": 128, "keep_o": 16,
               "sop_o": 16, "eop_o": 16, "dllp_o": 16, "sequence_o": 48,
               "packet_good_o": 4, "packet_nullified_o": 4, "packet_crc_bad_o": 4,
               "packet_dllp_o": 4, "packet_sequence_o": 48, "framing_error_o": 1,
               "overflow_o": 1, "stream_end_o": 1, "active_o": 1, "halted_o": 1,
               "accepting_o": 1}
    def declaration(kind, name, width):
        return f"{kind} " + (f"[{width-1}:0] " if width > 1 else "") + name + ";"
    lines = ["`timescale 1ns/1ps", "module tb;"]
    lines += [declaration("reg", n, w) for n, w in inputs.items()]
    lines += [declaration("wire", p + n, w) for n, w in outputs.items() for p in ("", "gold_")]
    for version, name, prefix in ((22, "reference", "gold_"), (23, "candidate", "")):
        con = [f".{n}({n})" for n in inputs] + [f".{n}({prefix}{n})" for n in outputs]
        lines.append(f"soc_pcie_gen3_framer_rx_integrity_v{version} #(.MAX_ENCODED_BYTES(150),.RING_DWORDS(64)) {name}({','.join(con)});")
    lines += [f"reg [511:0] blocks[0:{len(blocks)-1}];",
              f"reg [7:0] bytes_expected[0:{len(expected)-1}];",
              f"reg sop_expected[0:{len(expected)-1}],eop_expected[0:{len(expected)-1}];",
              f"reg [11:0] seq_expected[0:{len(expected)-1}];"]
    lines += ["integer n,i,offset,accepted,cycle_no,good_count,end_count;",
              "integer promotions=0,changed_promotions=0,promote_and_accept=0,held_inputs=0,held_outputs=0;",
              "reg accepted_now,promotion_now;reg [15:0] expected_relation;",
              "reg held=0;reg [239:0] held_payload;"]
    gate = "{" + ",".join(outputs) + "}"
    gold = "{" + ",".join("gold_" + x for x in outputs) + "}"
    lines += [f"""
task cycle;
begin
 clk_i=0; #2;
 if(rst_ni && {gate} !== {gold}) $fatal(1,"V23_FRAMER_PUBLIC_MITER");
 accepted_now=rst_ni && block_valid_i && block_ready_o;
 promotion_now=rst_ni && reference.step && reference.slice==3 && reference.next_valid;
 expected_relation=candidate.next_header_relation;
 if(promotion_now) begin
   promotions=promotions+1;
   if(candidate.current_header_relation !== candidate.next_header_relation) changed_promotions=changed_promotions+1;
   if(accepted_now) promote_and_accept=promote_and_accept+1;
 end
 if(rst_ni && !stream_start_i) begin
   if(framing_error_o || overflow_o || halted_o) $fatal(1,"V23_FRAMER_UNEXPECTED_FAULT");
   if(block_valid_i && !block_ready_o) held_inputs=held_inputs+1;
   if(valid_o) begin
     if(held && held_payload !== {{data_o,keep_o,sop_o,eop_o,dllp_o,sequence_o}}) $fatal(1,"V23_FRAMER_STALLED_OUTPUT_CHANGED");
     held=!ready_i;held_payload={{data_o,keep_o,sop_o,eop_o,dllp_o,sequence_o}};
     if(!ready_i) held_outputs=held_outputs+1;
     if(!keep_o || ((sop_o|eop_o|dllp_o)&~keep_o)!=0) $fatal(1,"V23_FRAMER_METADATA_MASK");
     if(ready_i) for(i=0;i<16;i=i+1) if(keep_o[i]) begin
       if(offset>={len(expected)}) $fatal(1,"V23_FRAMER_EXTRA_BYTE");
       if(data_o[8*i+:8] !== bytes_expected[offset] || sop_o[i] !== sop_expected[offset] ||
          eop_o[i] !== eop_expected[offset] || dllp_o[i] !== 1'b0 ||
          sequence_o[(i/4)*12+:12] !== seq_expected[offset]) $fatal(1,"V23_FRAMER_BYTE_OR_METADATA_SCOREBOARD");
       offset=offset+1;
     end
   end else if(held) $fatal(1,"V23_FRAMER_STALLED_OUTPUT_VANISHED");
 end else held=0;
 clk_i=1; #2;
 if(promotion_now && candidate.current_header_relation !== expected_relation)
   $fatal(1,"V23_FRAMER_PROMOTION_RELATION");
 if(rst_ni) begin
   for(i=0;i<4;i=i+1) begin
     if(packet_good_o[i]) good_count=good_count+1;
     if(packet_nullified_o[i] || packet_crc_bad_o[i] || packet_dllp_o[i]) $fatal(1,"V23_FRAMER_UNEXPECTED_VERDICT");
   end
   if(stream_end_o) end_count=end_count+1;
 end
end
endtask
initial begin
"""]
    lines += [f"blocks[{i}]=512'h{b:0128x};" for i, b in enumerate(blocks)]
    lines += [f"bytes_expected[{i}]=8'h{b:02x};sop_expected[{i}]={int(s)};eop_expected[{i}]={int(e)};seq_expected[{i}]=12'h{q:03x};" for i, (b, s, e, q) in enumerate(expected)]
    lines.append(f"""
 clk_i=0;rst_ni=0;flush_i=0;stream_start_i=0;stream_abort_i=0;block_valid_i=0;
 headers_i=8'haa;payload_i=0;block_error_i=0;ready_i=1;offset=0;accepted=0;good_count=0;end_count=0;
 cycle;rst_ni=1;stream_start_i=1;cycle;stream_start_i=0;
 // Offer a block every cycle; advance only on actual ready/valid acceptance.
 // This naturally fills next-bank and holds a third block through backpressure.
 for(cycle_no=0;cycle_no<{len(blocks)*4+100};cycle_no=cycle_no+1) begin
   block_valid_i=(accepted<{len(blocks)});if(block_valid_i) payload_i=blocks[accepted];
   ready_i=!(cycle_no%31==10 || cycle_no%31==11 || cycle_no%31==12);
   cycle;if(accepted_now) accepted=accepted+1;
 end
 if(accepted!={len(blocks)} || offset!={len(expected)} || good_count!={packets} || end_count!=1 || active_o)
   $fatal(1,"V23_FRAMER_FINAL_SCOREBOARD accepted=%0d bytes=%0d good=%0d ends=%0d",accepted,offset,good_count,end_count);
 if(promotions<2 || changed_promotions<1 || promote_and_accept<1 || held_inputs<1 || held_outputs<1)
   $fatal(1,"V23_FRAMER_BURST_WITNESS promotions=%0d changed=%0d concurrent=%0d inputstall=%0d outputstall=%0d",promotions,changed_promotions,promote_and_accept,held_inputs,held_outputs);
 $display("PASS_V23_FRAMER_BURST blocks=%0d bytes=%0d packets=%0d promotions=%0d changed=%0d concurrent=%0d inputstall=%0d outputstall=%0d",accepted,offset,good_count,promotions,changed_promotions,promote_and_accept,held_inputs,held_outputs);
 $finish;
end
endmodule
""")
    return "\n".join(lines)


def run_burst(directory, fault=None):
    directory.mkdir(exist_ok=True)
    assert fault in (None, "header_promote_stale")
    sources = []
    for v in (22, 23):
        original = RTL / f"soc_pcie_gen3_framer_rx_integrity_v{v}.v"
        text = original.read_text()
        if v == 23 and fault:
            module = runpy.run_path(str(ROOT / "sw/tests/test_pcie_gen3_integrity_v23_miter.py"))
            old, new = module["HEADER_FAULTS"][fault]
            assert text.count(old) == 1
            text = text.replace(old, new)
        out = directory / original.name
        out.write_text(text)
        sources.append(out)
    blocks, expected, packets = stimulus()
    top = directory / "tb.v"
    top.write_text(bench(blocks, expected, packets))
    image = directory / "sim.vvp"
    command = [shutil.which("iverilog") or "/usr/bin/iverilog", "-g2012", "-s", "tb", "-o", str(image), str(top), *map(str, sources)]
    def limits():
        resource.setrlimit(resource.RLIMIT_AS, (2 * 1024**3, 2 * 1024**3))
        resource.setrlimit(resource.RLIMIT_CORE, (0, 0))
    with (directory / "compile.log").open("x") as log:
        result = subprocess.run(command, stdout=log, stderr=subprocess.STDOUT, preexec_fn=limits)
    assert result.returncode == 0
    with (directory / "simulation.log").open("x") as log:
        result = subprocess.run([shutil.which("vvp") or "/usr/bin/vvp", str(image)], stdout=log, stderr=subprocess.STDOUT, preexec_fn=limits)
    text = (directory / "simulation.log").read_text()
    receipt = {"fault": fault, "returncode": result.returncode, "blocks": len(blocks), "bytes": len(expected), "packets": packets,
               "inputs": {str(p): pin(p) for p in [BENCH, Path(__file__), *sources, top]},
               "outputs": {p.name: pin(p) for p in [image, directory / "compile.log", directory / "simulation.log"]}}
    (directory / "result.json").write_text(json.dumps(receipt, indent=2) + "\n")
    if fault:
        assert result.returncode != 0 and "V23_FRAMER_PROMOTION_RELATION" in text
    else:
        assert result.returncode == 0 and "PASS_V23_FRAMER_BURST" in text
        assert re.search(r"promotions=[1-9]\d* changed=[1-9]\d* concurrent=[1-9]\d* inputstall=[1-9]\d* outputstall=[1-9]\d*", text)


def test_actual_block_burst_scoreboard_and_promotion(tmp_path):
    run_burst(tmp_path / "burst")
