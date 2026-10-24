# SPDX-FileCopyrightText: 2026 Hasan Melih Akbulut
# SPDX-License-Identifier: Apache-2.0
"""Actual RTL-port DATA ordinal and lossless SKP scoreboards, not internal state."""
import hashlib
import json
from pathlib import Path
import random
import shutil
import subprocess

import pytest

ROOT = Path(__file__).resolve().parents[2]
RTL = ROOT / "hw/soc/rtl/pcie/soc_pcie_gen3_sds_deskew_v1.v"
EIEOS = (int.from_bytes(bytes([0, 255] * 8), "little") << 2) | 1
SDS = (int.from_bytes(bytes([0xE1] + [0x55] * 15), "little") << 2) | 1


def record(block, code=2, skp=0, eieos=0, realign=0):
    return block | (code << 194) | (skp << 197) | (eieos << 198) | (realign << 199)


def fixture(case):
    rng = random.Random(602144)
    payloads = [[rng.getrandbits(128) for _ in range(4)] for _ in range(76)]
    # Payload bits can alias EIEOS/SDS characters without changing DATA headers.
    payloads[4][0] = EIEOS >> 2
    payloads[5][3] = SDS >> 2
    queues = []
    for lane in range(4):
        q = [(0, record(EIEOS, eieos=1, realign=1)),
             (0, record((int.from_bytes(bytes([0x66] * 16), "little") << 2) | 1)),
             (lane * 7, record(SDS))]
        for i, data in enumerate(payloads):
            if i:
                for code in ((i + lane) % 5, (i // 5 + lane) % 5):
                    trailer = bytes([0xAA, 0xE1, (i * 19 + lane) & 255])
                    skp = (int.from_bytes(bytes([0xAA] * (4 + 4 * code) + [0xE1]) + trailer, "little") << 2) | 1
                    q.append((0, record(skp, code, skp=1)))
            q.append((0, record((data[lane] << 2) | 2)))
        queues.append(q)
    injection = 0
    expect_fault = case not in {"cohort_stalls_and_all_skp_lengths", "last_allowed_skew_cycle", "long_training_before_sds"}
    if case in {"last_allowed_skew_cycle", "one_cycle_after_skew_limit"}:
        _, r = queues[3][3]
        queues[3][3] = (66 if case == "last_allowed_skew_cycle" else 67, r)
    elif case == "long_training_before_sds":
        for lane in range(4):
            _, r = queues[lane][2]
            queues[lane][2] = (200 + lane * 7, r)
    elif case == "missing_sds":
        queues[3] = queues[3][:2]
    elif case == "sds_without_eieos":
        queues[2] = queues[2][2:]
    elif case == "skp_before_first_data":
        queues[1][3] = queues[1][4]
    elif case == "duplicate_sds":
        queues[0].insert(3, (0, record(SDS)))
    elif case == "malformed_sds":
        queues[0][2] = (0, record(SDS ^ (1 << 82)))
    elif case == "sds_high_padding":
        queues[0][2] = (0, record(SDS | (1 << 188)))
    elif case == "data_before_sds":
        queues[0][2] = queues[0][3]
    elif case == "eieos_during_data":
        queues[2][7] = (0, record(EIEOS, eieos=1))
    elif case == "invalid_skp_end":
        t, r = queues[1][4]
        code = (r >> 194) & 7
        queues[1][4] = (t, r ^ (1 << (2 + 8 * (4 + 4 * code))))
    elif case == "invalid_skp_length":
        t, r = queues[1][4]
        queues[1][4] = (t, (r & ~(7 << 194)) | (5 << 194))
    elif case == "false_skp_flag":
        t, r = queues[1][3]
        queues[1][3] = (t, r | (1 << 197))
    elif case == "missing_skp_flag":
        t, r = queues[1][4]
        queues[1][4] = (t, r & ~(1 << 197))
    elif case == "realign_after_start":
        t, r = queues[1][7]
        queues[1][7] = (t, r | (1 << 199))
    elif case == "upstream_fault":
        injection = 1
    elif case == "upstream_fault_during_stall":
        injection = 3
    elif case == "second_arm":
        injection = 2
    elif case != "cohort_stalls_and_all_skp_lengths":
        raise AssertionError(case)
    return queues, payloads, expect_fault, injection


BENCH = r"""
module tb;
reg clk=0; always #2 clk=~clk;
reg rst=0,arm=0,uf=0;reg[3:0]valid=0,skp=0,eieos=0,realign=0,sready=0;
reg[775:0]blocks=0;reg[11:0]codes=0;reg dready=0;
wire[3:0]ready,sv;wire start,active,fault,dv;wire[511:0]data;
wire[775:0]sb;wire[11:0]sc;
soc_pcie_gen3_sds_deskew_v1 #(.MAX_SKEW_CYCLES(64)) dut
(clk,rst,arm,uf,valid,ready,blocks,codes,skp,eieos,realign,
start,active,fault,dv,dready,data,sv,sready,sb,sc);
reg[199:0]mem[0:4*STRIDE-1];integer times[0:4*STRIDE-1];
reg[511:0]expected[0:DATA_COUNT-1];integer counts[0:3];
integer pos[0:3];integer i,l,n,seen=0,starts=0,skps=0,stalled=0;
reg held=0;reg[511:0]hold_data;
initial begin
$readmemh("INPUT",mem);$readmemh("TIMES",times);$readmemh("EXPECTED",expected);
COUNTS
for(l=0;l<4;l=l+1)pos[l]=0;
repeat(3)@(negedge clk);
rst=1;arm=1;@(negedge clk);arm=0;
for(i=0;i<12000;i=i+1)begin
valid=0; blocks=0;codes=0;skp=0;eieos=0;realign=0;
for(l=0;l<4;l=l+1)begin
n=l*STRIDE+pos[l];
if(pos[l]<counts[l] && i>=times[n])begin
valid[l]=1;{realign[l],eieos[l],skp[l],codes[l*3+:3],blocks[l*194+:194]}=mem[n];
end end
dready=(i%13>=5);sready=(i%7>=3)?4'b1111:4'b0101;
if(INJECTION==3 && seen>=4)dready=0;
uf=(INJECTION==1 && i==45);arm=(INJECTION==2 && i==45);
if(INJECTION==3 && held)uf=1;
#1;
if(fault)begin
if(!EXPECT_FAULT)$fatal(1,"UNEXPECTED_COHORT_FAULT");
if(i>FAULT_DEADLINE)$fatal(1,"FAULT_DETECTED_TOO_LATE");
repeat(5)begin
@(negedge clk); uf=0;arm=0;#1;
if(!fault || ready || dv || sv || start || active)$fatal(1,"ABORT_NOT_STICKY");
end
rst=0;@(negedge clk);#1;
if(fault || ready || dv || sv || start || active)$fatal(1,"RESET_NOT_CLEAN");
$display("PASS EXPECTED_ABORT data=%0d skp=%0d",seen,skps);$finish;
end
if(held && active && (data!==hold_data || !dv))$fatal(1,"DATA_NOT_STABLE_DURING_STALL");
if(!active && (dv || sv))$fatal(1,"INACTIVE_EPOCH_RETIRED_DATA");
held=dv && !dready;hold_data=data;
if(start)begin
starts=starts+1;if(starts!=1 || seen!=0 || dv || ready)$fatal(1,"START_NOT_SEPARATE");
end
if(dv)begin
if(starts!=1 || data!==expected[seen])$fatal(1,"DATA_ORDINAL_OR_LANE_MISMATCH");
if(dready)begin
if(ready!==4'b1111)$fatal(1,"NONATOMIC_DATA_HANDSHAKE");seen=seen+1;
end else begin
if(ready)$fatal(1,"STALLED_DATA_CONSUMED");stalled=stalled+1;
end end
for(l=0;l<4;l=l+1)begin
if(sv[l])begin
if(!valid[l] || !skp[l] || sb[l*194+:194]!==blocks[l*194+:194] || sc[l*3+:3]!==codes[l*3+:3])$fatal(1,"SKP_RECORD_CORRUPTION");
if(ready[l]!==sready[l])$fatal(1,"SKP_BACKPRESSURE_LOST");
if(sready[l])skps=skps+1;
end
end
@(posedge clk);
for(l=0;l<4;l=l+1)if(valid[l] && ready[l])pos[l]=pos[l]+1;
@(negedge clk);
if(seen==DATA_COUNT && pos[0]==counts[0] && pos[1]==counts[1] && pos[2]==counts[2] && pos[3]==counts[3])begin
if(EXPECT_FAULT)$fatal(1,"FAULT_WAS_NOT_DETECTED");
if(skps!=EXPECTED_SKPS || stalled==0 || starts!=1)$fatal(1,"INCOMPLETE_EXERCISE");
$display("PASS COHORT data=%0d skp=%0d stalls=%0d",seen,skps,stalled);$finish;
end end
$fatal(1,"BOUNDED_COHORT_DID_NOT_COMPLETE");
end
endmodule
"""


def run(tmp_path, case, source=RTL):
    tmp_path.mkdir(parents=True, exist_ok=True)
    local = ROOT / "hw/soc/tools/oss-cad-suite/bin"
    compiler = local / "iverilog" if (local / "iverilog").is_file() else Path(shutil.which("iverilog") or "/missing/iverilog")
    simulator = compiler.parent / "vvp"
    assert compiler.is_file() and simulator.is_file(), "Real Icarus required; never skip"
    queues, data, fault, injection = fixture(case)
    stride = max(map(len, queues))
    values = [x for q in queues for x in (q + [(0, 0)] * (stride - len(q)))]
    (tmp_path / "input.hex").write_text("".join(f"{r:050x}\n" for _, r in values))
    (tmp_path / "times.hex").write_text("".join(f"{t:08x}\n" for t, _ in values))
    (tmp_path / "expected.hex").write_text("".join(f"{sum(d << (128*l) for l,d in enumerate(row)):0128x}\n" for row in data))
    bench = BENCH
    replacements = {"STRIDE": stride, "DATA_COUNT": len(data), "COUNTS": "\n".join(f"counts[{l}]={len(q)};" for l, q in enumerate(queues)),
                    "INPUT": str(tmp_path / "input.hex"), "TIMES": str(tmp_path / "times.hex"), "EXPECTED_SKPS": sum((r >> 197) & 1 for _, r in values),
                    "EXPECTED": str(tmp_path / "expected.hex"), "EXPECT_FAULT": int(fault), "INJECTION": injection,
                    "FAULT_DEADLINE": 10 if case == "skp_before_first_data" else 1000}
    for old in sorted(replacements, key=len, reverse=True):
        bench = bench.replace(old, str(replacements[old]))
    (tmp_path / "tb.v").write_text(bench)
    command = [str(compiler), "-g2012", "-s", "tb", "-o", str(tmp_path / "sim.vvp"), str(source), str(tmp_path / "tb.v")]
    compiled = subprocess.run(command, capture_output=True, text=True)
    (tmp_path / "compile.log").write_text(compiled.stdout + compiled.stderr)
    assert compiled.returncode == 0, compiled.stderr
    native = subprocess.run([str(simulator), str(tmp_path / "sim.vvp")], capture_output=True, text=True)
    log = native.stdout + native.stderr
    (tmp_path / "run.log").write_text(log)
    (tmp_path / "command.json").write_text(json.dumps({"command": command, "returncode": native.returncode, "case": case,
        "rtl_sha256": hashlib.sha256(source.read_bytes()).hexdigest()}, indent=2) + "\n")
    return native.returncode, log


CASES = ["cohort_stalls_and_all_skp_lengths", "missing_sds", "sds_without_eieos", "skp_before_first_data", "duplicate_sds",
         "malformed_sds", "sds_high_padding", "data_before_sds", "eieos_during_data", "invalid_skp_end", "invalid_skp_length",
         "false_skp_flag", "missing_skp_flag", "realign_after_start", "upstream_fault", "second_arm", "upstream_fault_during_stall",
         "last_allowed_skew_cycle", "one_cycle_after_skew_limit", "long_training_before_sds"]


@pytest.mark.parametrize("case", CASES)
def test_actual_sds_cohort_and_faults(tmp_path, case):
    rc, log = run(tmp_path, case)
    assert rc == 0 and "PASS " in log, log


MUTANTS = {
    "lane_order": ("data_o[lane*128 +: 128]", "data_o[(3-lane)*128 +: 128]", CASES[0]),
    "partial_data_group": ("&(valid_i & is_data)", "|(valid_i & is_data)", CASES[0]),
    "lost_data_stall": ("all_data && data_ready_i", "all_data", CASES[0]),
    "lost_skp_stall": ("skp_valid_o & skp_ready_i", "skp_valid_o", CASES[0]),
    "truncated_skp": ("assign skp_block_o = block_i;", "assign skp_block_o = {64'd0,block_i[711:0]};", CASES[0]),
    "no_sds_timeout": ("age_q==MAX_SKEW_CYCLES", "1'b0", "missing_sds"),
    "first_skp_permitted": ("seen_sds_q[k] && !is_data[k]", "seen_sds_q[k] && !is_data[k] && !is_skp[k]", "skp_before_first_data"),
    "missing_upstream_abort": ("upstream_fault_i ||", "1'b0 ||", "upstream_fault"),
    "rearm_ignored": ("(arm_i && state_q != IDLE)", "1'b0", "second_arm"),
    "sds_without_alignment": ("is_sds[k] && !seen_eieos_q[k]", "1'b0", "sds_without_eieos"),
}


@pytest.mark.parametrize("name", MUTANTS)
def test_actual_hardware_fault_is_observable(tmp_path, name):
    old, new, case = MUTANTS[name]
    original = RTL.read_text()
    assert original.count(old) == 1
    source = tmp_path / "mutant.v"
    source.write_text(original.replace(old, new))
    rc, log = run(tmp_path, case, source)
    assert rc != 0 and "FATAL:" in log, (name, log)
    diagnostics = {
        "lane_order": "DATA_ORDINAL_OR_LANE_MISMATCH",
        "partial_data_group": "DATA_ORDINAL_OR_LANE_MISMATCH",
        "lost_data_stall": "STALLED_DATA_CONSUMED",
        "lost_skp_stall": "SKP_BACKPRESSURE_LOST",
        "truncated_skp": "SKP_RECORD_CORRUPTION",
        "no_sds_timeout": "BOUNDED_COHORT_DID_NOT_COMPLETE",
        "first_skp_permitted": "FAULT_DETECTED_TOO_LATE",
        "missing_upstream_abort": "FAULT_WAS_NOT_DETECTED",
        "rearm_ignored": "FAULT_WAS_NOT_DETECTED",
        "sds_without_alignment": "FAULT_WAS_NOT_DETECTED",
    }
    assert diagnostics[name] in log, (name, log)
