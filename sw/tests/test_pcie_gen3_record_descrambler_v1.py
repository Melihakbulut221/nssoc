# SPDX-FileCopyrightText: 2026 Hasan Melih Akbulut
# SPDX-License-Identifier: Apache-2.0
"""Serial transmitted-bit oracle for OS-aware Gen3 LFSR and lane parity."""
import hashlib
import json
from pathlib import Path
import random
import shutil
import subprocess

import pytest

ROOT = Path(__file__).resolve().parents[2]
RTL = ROOT / "hw/soc/rtl/pcie/soc_pcie_gen3_record_descrambler_v1.v"
SEEDS = (0x1DBFBC, 0x0607BB, 0x1EC760, 0x18C0DB, 0x010F12, 0x19CFC9, 0x0277CE, 0x1BB807)
EIEOS = int.from_bytes(bytes([0, 255] * 8), "little") * 4 + 1
SDS = int.from_bytes(bytes([0xE1] + [0x55] * 15), "little") * 4 + 1


def transform(state, value=0):
    result = 0
    for bit in range(128):
        outgoing = (state >> 22) & 1
        result |= (((value >> bit) & 1) ^ outgoing) << bit
        state = ((state << 1) & 0x7FFFFF) ^ (0x210125 if outgoing else 0)
    return state, result


def rec(block, code=2, skp=0, eieos=0, realign=0):
    return block | (code << 194) | (skp << 197) | (eieos << 198) | (realign << 199)


def stimulus(lane, case="clean"):
    rng = random.Random(0x83716 + lane)
    state = SEEDS[lane]
    parity = 0
    previous_data = False
    lane_error = lfsr_error = 0
    inputs, outputs, status = [], [], []

    def append(raw, expected=None, fault=0):
        inputs.append(raw)
        if not fault:
            outputs.append(raw if expected is None else expected)
        status.append(fault | (lane_error << 1) | (lfsr_error << 2))

    if case == "data_before_eieos":
        append(rec(2), fault=1)
        return inputs, outputs, status
    for epoch in range(8):
        append(rec(EIEOS, eieos=1, realign=int(epoch == 0)))
        state, parity, previous_data = SEEDS[lane], 0, False
        # Raw OS contents remain raw; this exercises state progression only,
        # without claiming a training-field/DC-balance decoder.
        for _ in range(epoch):
            os_payload = (rng.getrandbits(120) << 8) | 0x1E
            append(rec((os_payload << 2) | 1))
            state, _ = transform(state)
        append(rec(SDS))
        state, _ = transform(state)
        parity, previous_data = 0, False
        for number in range(12):
            plain = rng.getrandbits(128)
            state, encoded = transform(state, plain)
            parity ^= encoded.bit_count() & 1
            append(rec((encoded << 2) | 2), rec((plain << 2) | 2))
            previous_data = True
            for repeat in range(1 + int(number % 4 == 0)):
                code = (number + epoch + repeat) % 5
                bit7 = parity if previous_data else 1 ^ ((state >> 22) & 1)
                upper = ((state >> 16) & 0x7F) | (bit7 << 7)
                trailer = [upper, (state >> 8) & 255, state & 255]
                if epoch == 1 and number == 2 and repeat == 0:
                    if case == "bad_parity":
                        trailer[0] ^= 0x80
                        lane_error = 1
                    elif case == "bad_lfsr":
                        trailer[2] ^= 1
                        lfsr_error = 1
                if epoch == 1 and number == 4 and repeat == 1 and case == "bad_nondata_indicator":
                    trailer[0] ^= 0x80
                    lfsr_error = 1
                body = bytes([0xAA] * (4 + 4 * code) + [0xE1] + trailer)
                append(rec((int.from_bytes(body, "little") << 2) | 1, code, skp=1))
                parity, previous_data = 0, False
    if case == "invalid_header":
        append(rec(0), fault=1)
    elif case == "invalid_skp_end":
        append(rec((int.from_bytes(bytes([0xAA]*4+[0xE0, 0, 0, 0]), "little") << 2) | 1, 0, skp=1), fault=1)
    elif case == "invalid_metadata":
        append(rec(EIEOS, eieos=0), fault=1)
    elif case == "invalid_length":
        append(rec(2, code=5), fault=1)
    elif case == "high_padding":
        append(rec((1 << 193) | 2), fault=1)
    elif case not in {"clean", "bad_parity", "bad_lfsr", "bad_nondata_indicator"}:
        raise AssertionError(case)
    return inputs, outputs, status


BENCH = r"""
module tb;
reg clk=0;always #2 clk=~clk;
reg rst=0,flush=0,valid=0,ready=0;reg[199:0]item=0;
wire ri,vo,ff,le,lm;wire[199:0]result;
soc_pcie_gen3_record_descrambler_v1 #(.LANE_ID(LANE_VALUE)) dut
(clk,rst,flush,valid,ri,item[193:0],item[196:194],item[197],item[198],item[199],
vo,ready,result[193:0],result[196:194],result[197],result[198],result[199],ff,le,lm);
reg[199:0]inputs[0:INPUT_COUNT-1],expected[0:OUTPUT_SLOTS-1];reg[2:0]status[0:INPUT_COUNT-1];
integer sent=0,seen=0,i,stalls=0;reg held=0;reg[199:0]old;
initial begin
$readmemh("INPUT_FILE",inputs);$readmemh("OUTPUT_FILE",expected);$readmemh("STATUS_FILE",status);
repeat(3)@(negedge clk);rst=1;
for(i=0;i<20000;i=i+1)begin
valid=sent<INPUT_COUNT;item=valid?inputs[sent]:0;ready=i%11>=4;
#1;
if(held && (result!==old || !vo))$fatal(1,"HELD_RECORD_CHANGED");
held=vo && !ready;old=result;
if(vo)begin
if(seen>=OUTPUT_COUNT || result!==expected[seen])$fatal(1,"DECODED_RECORD_OR_METADATA_MISMATCH");
if(!ready)stalls=stalls+1;
end
@(posedge clk);
if(vo && ready)seen=seen+1;
if(valid && ri)sent=sent+1;
#1;
if(sent && {lm,le,ff}!==status[sent-1])$fatal(1,"STATUS_OR_PARITY_POLICY_MISMATCH");
if(ff)begin
if(!EXPECT_FORMAT_FAULT || vo || ri)$fatal(1,"INVALID_FORMAT_ABORT_POLICY");
end
@(negedge clk);
if(sent==INPUT_COUNT && (seen==OUTPUT_COUNT || ff))begin
if(seen!=OUTPUT_COUNT)$fatal(1,"GOOD_PREFIX_LOST");
if(OUTPUT_COUNT>0 && stalls==0)$fatal(1,"NO_BACKPRESSURE_EXERCISED");
flush=1;@(negedge clk);#1;
if(vo || ri || ff || le || lm)$fatal(1,"FLUSH_DID_NOT_CLEAR_EPOCH");
$display("PASS records=%0d stalls=%0d",seen,stalls);$finish;
end end
$fatal(1,"BOUNDED_RECORD_STREAM_DID_NOT_COMPLETE");
end
endmodule
"""


def run(tmp_path, lane=0, case="clean", source=RTL):
    tmp_path.mkdir(parents=True, exist_ok=True)
    tools = ROOT / "hw/soc/tools/oss-cad-suite/bin"
    compiler = tools / "iverilog" if (tools / "iverilog").is_file() else Path(shutil.which("iverilog") or "/missing/iverilog")
    simulator = compiler.parent / "vvp"
    assert compiler.is_file() and simulator.is_file(), "Actual RTL compiler required; never skip"
    inputs, outputs, status = stimulus(lane, case)
    (tmp_path / "inputs.hex").write_text("".join(f"{n:050x}\n" for n in inputs))
    (tmp_path / "outputs.hex").write_text("".join(f"{n:050x}\n" for n in outputs or [0]))
    (tmp_path / "status.hex").write_text("".join(f"{n:x}\n" for n in status))
    replacements = dict(LANE_VALUE=lane, INPUT_COUNT=len(inputs), OUTPUT_COUNT=len(outputs), OUTPUT_SLOTS=max(1, len(outputs)),
        INPUT_FILE=str(tmp_path / "inputs.hex"), OUTPUT_FILE=str(tmp_path / "outputs.hex"), STATUS_FILE=str(tmp_path / "status.hex"), EXPECT_FORMAT_FAULT=int(bool(status[-1] & 1)))
    bench = BENCH
    for k in sorted(replacements, key=len, reverse=True):
        bench = bench.replace(k, str(replacements[k]))
    tb = tmp_path / "tb.v"
    tb.write_text(bench)
    command = [str(compiler), "-g2012", "-s", "tb", "-o", str(tmp_path / "sim.vvp"), str(source), str(tb)]
    compiled = subprocess.run(command, capture_output=True, text=True)
    (tmp_path / "compile.log").write_text(compiled.stdout + compiled.stderr)
    assert compiled.returncode == 0, compiled.stderr
    native = subprocess.run([str(simulator), str(tmp_path / "sim.vvp")], capture_output=True, text=True)
    log = native.stdout + native.stderr
    (tmp_path / "run.log").write_text(log)
    (tmp_path / "command.json").write_text(json.dumps(dict(command=command, lane=lane, case=case, returncode=native.returncode,
        source_sha256=hashlib.sha256(source.read_bytes()).hexdigest()), indent=2) + "\n")
    return native.returncode, log


@pytest.mark.parametrize("lane", range(8))
def test_all_assigned_lane_seeds_training_sds_skp_and_stalls(tmp_path, lane):
    rc, log = run(tmp_path, lane)
    assert rc == 0 and "PASS " in log, log


@pytest.mark.parametrize("case", ["bad_parity", "bad_lfsr", "bad_nondata_indicator", "data_before_eieos", "invalid_header",
                                  "invalid_skp_end", "invalid_metadata", "invalid_length", "high_padding"])
def test_reporting_and_real_format_faults(tmp_path, case):
    rc, log = run(tmp_path, 3, case)
    assert rc == 0 and "PASS " in log, log


MUTANTS = {
    "seed_at_sds": ("state_q<=advanced;", "state_q<=is_sds ? seed(LANE_ID) : advanced;", "clean"),
    "no_os_advance": ("state_q<=advanced;", "state_q<=is_data ? advanced : state_q;", "clean"),
    "advance_at_skp": ("end else if(skp_i) begin", "end else if(skp_i) begin state_q<=advanced;", "clean"),
    "parity_after_descramble": ("parity_q ^ ^block_i[129:2]", "parity_q ^ ^decoded", "clean"),
    "parity_retrains": ("lane_error_o<=1;", "begin lane_error_o<=1;format_fault_o<=1;end", "bad_parity"),
    "ignore_parity_error": ("lane_error_o<=1;", "lane_error_o<=0;", "bad_parity"),
    "load_received_lfsr": ("end else if(skp_i) begin", "end else if(skp_i) begin state_q<=received_lfsr;", "bad_lfsr"),
    "ignore_lfsr_error": ("lfsr_mismatch_o<=1;", "lfsr_mismatch_o<=0;", "bad_lfsr"),
    "ignore_nondata_indicator": ("(!previous_data_q && trailer[7]!=!state_q[22])", "1'b0", "bad_nondata_indicator"),
    "swap_lfsr_trailer_bytes": ("{trailer[6:0],trailer[15:8],trailer[23:16]}", "{trailer[6:0],trailer[23:16],trailer[15:8]}", "clean"),
    "advance_while_stalled": ("end else if(ready_o) begin", "end else if(enabled) begin", "clean"),
}


@pytest.mark.parametrize("name", MUTANTS)
def test_actual_policy_mutation_is_detected(tmp_path, name):
    old, new, case = MUTANTS[name]
    text = RTL.read_text()
    assert text.count(old) == 1
    source = tmp_path / "mutant.v"
    source.write_text(text.replace(old, new))
    rc, log = run(tmp_path, 2, case, source)
    assert rc != 0 and any(s in log for s in ("DECODED_RECORD_OR_METADATA_MISMATCH", "STATUS_OR_PARITY_POLICY_MISMATCH", "HELD_RECORD_CHANGED")), (name, log)
