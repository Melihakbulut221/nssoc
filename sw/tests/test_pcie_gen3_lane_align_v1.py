# SPDX-FileCopyrightText: 2026 Hasan Melih Akbulut
# SPDX-License-Identifier: Apache-2.0
"""Actual public-port bitstream tests, independent of RTL shift/register layout."""

import json
from pathlib import Path
import random
import shutil
import subprocess

import pytest

ROOT = Path(__file__).resolve().parents[2]
RTL = ROOT / "hw/soc/rtl/pcie/soc_pcie_gen3_lane_align_v1.v"
EIEOS = 1 | (int.from_bytes(bytes([0, 255] * 8), "little") << 2)
MASK = (1 << 130) - 1


def bits(value, count=130):
    return [(value >> i) & 1 for i in range(count)]


def words(stream):
    return [
        sum(b << j for j, b in enumerate(stream[i : i + 32]))
        for i in range(0, len(stream), 32)
    ]


def rows(stream, search=1):
    return [(w, search, 1, 0, 1) for w in words(stream)]


def reset():
    return [(0, 1, 0, 0, 0)] * 3


def data(n, seed):
    rng = random.Random(seed)
    return [(rng.getrandbits(128) << 2) | (1 if i % 5 == 0 else 2) for i in range(n)]


def flat(blocks):
    return [b for word in blocks for b in bits(word)]


def run(tmp_path, cycles, source=RTL):
    """No Cocotb/Python embedding; execute actual Icarus with finite stimulus."""
    tmp_path.mkdir(parents=True, exist_ok=True)
    tool = shutil.which("iverilog")
    vvp = shutil.which("vvp")
    assert tool and vvp, "Actual Icarus and vvp required, never skip"
    stimulus = tmp_path / "input.hex"
    stimulus.write_text(
        "".join(
            f"{(w | (s << 32) | (v << 33) | (f << 34) | (r << 35)):09x}\n"
            for w, s, v, f, r in cycles
        )
    )
    bench = tmp_path / "tb.v"
    bench.write_text(
        """module tb;
reg clk=0; always #2 clk=~clk;
reg rst=0, valid=0, search=0, force_align=0; reg[31:0] raw=0;
wire aligned,bv,eo,ro,lo;wire[129:0] block;
soc_pcie_gen3_lane_align_v1 dut(clk,rst,valid,raw,search,force_align,aligned,bv,block,eo,ro,lo);
reg[35:0] stim[0:COUNT-1];integer i;
initial begin
$readmemh("INPUT",stim);
for(i=0;i<COUNT;i=i+1)begin
@(negedge clk);{rst,force_align,valid,search,raw}=stim[i];
@(posedge clk);#1;$display("ROW %0d %b %b %b %b %b %033h",i,aligned,bv,eo,ro,lo,block);
end
$finish;end
endmodule
""".replace("COUNT", str(len(cycles))).replace("INPUT", str(stimulus))
    )
    exe = tmp_path / "sim.vvp"
    command = [tool, "-g2012", "-s", "tb", "-o", str(exe), str(source), str(bench)]
    compiled = subprocess.run(command, text=True, capture_output=True)
    (tmp_path / "compile.log").write_text(compiled.stdout + compiled.stderr)
    if compiled.returncode:
        raise RuntimeError(compiled.stderr)
    native = subprocess.run([vvp, str(exe)], text=True, capture_output=True)
    (tmp_path / "run.log").write_text(native.stdout + native.stderr)
    if native.returncode:
        raise RuntimeError(native.stderr)
    out = []
    for line in native.stdout.splitlines():
        if line.startswith("ROW "):
            _, i, a, v, e, r, l, b = line.split()
            out.append(
                dict(
                    cycle=int(i),
                    aligned=int(a),
                    valid=int(v),
                    eieos=int(e),
                    realign=int(r),
                    loss=int(l),
                    block=int(b, 16),
                )
            )
    if len(out) != len(cycles):
        raise RuntimeError("Incomplete native public-port trace")
    (tmp_path / "commands.json").write_text(
        json.dumps(dict(compile=command, simulate=[vvp, str(exe)]), indent=2) + "\n"
    )
    return out


def observed(trace):
    return [(r["cycle"], r["block"]) for r in trace if r["valid"]]


def phase_case(tmp_path, source=RTL):
    cycles = []
    expected = []
    acquisitions = []
    for phase in range(32):
        cycles += reset()
        start = len(cycles)
        blocks = [EIEOS] + data(256, 1000 + phase)
        stream = [0] * phase + flat(blocks)
        cycles += rows(stream)
        expected += [
            (start + (phase + 130 * (i + 1) - 1) // 32, w) for i, w in enumerate(blocks)
        ]
        acquisitions.append(expected[-len(blocks)][0])
    trace = run(tmp_path, cycles, source)
    assert observed(trace) == expected, (
        "Exact all32 phase/130bit/header/payload/cadence mismatch"
    )
    assert [r["cycle"] for r in trace if r["realign"]] == acquisitions, (
        "Acquisition must occur once per phase"
    )
    assert [r["cycle"] for r in trace if r["eieos"]] == acquisitions
    assert not any(r["loss"] for r in trace)
    for first in acquisitions:
        assert trace[first]["aligned"] and trace[first]["valid"]
        assert not any(r["aligned"] or r["valid"] for r in trace[first - 4 : first])
    # Every256 steady blocks take1040 raw32 clocks, i.e. exactly16/65.
    for phase in range(32):
        chunk = expected[phase * 257 : (phase + 1) * 257]
        assert chunk[-1][0] - chunk[0][0] == 1040


def reject_case(tmp_path, source=RTL):
    cycles = []
    for bit in range(130):
        cycles += reset() + rows([0] * 13 + bits(EIEOS ^ (1 << bit)) + [0] * 256)
    # No complete EIEOS: valid-looking headers alone cannot establish alignment.
    cycles += reset() + rows(flat(data(512, 811)))
    # Startup suffix plus zeros cannot exploit reset history as real received bits.
    cycles += reset() + rows(bits(EIEOS)[31:] + [0] * 256)
    trace = run(tmp_path, cycles, source)
    assert not any(
        r["aligned"] or r["valid"] or r["eieos"] or r["realign"] for r in trace
    ), "False or corrupted pattern acquired"


def frozen_case(tmp_path, source=RTL):
    blocks = [EIEOS] + data(255, 123)
    # Put a full EIEOS one bit after a valid Data header. It crosses the next
    # block's header, which is also valid01. Search-off must ignore this alias.
    stream = flat(blocks)
    for block_index in range(8, 240, 8):
        p = block_index * 130
        stream[p] = 0
        stream[p + 1 : p + 131] = bits(EIEOS)
        stream[p + 131] = 0
    blocks = [
        sum(stream[i + j] << j for j in range(130)) for i in range(0, len(stream), 130)
    ]
    cycles = reset()
    start = len(cycles)
    wr = rows(stream)
    # Exact EIEOS acquisition is word4; disable search for all following words.
    wr = [(w, int(i < 5), v, f, r) for i, (w, s, v, f, r) in enumerate(wr)]
    cycles += wr
    trace = run(tmp_path, cycles, source)
    assert observed(trace) == [
        (start + (130 * (i + 1) - 1) // 32, w) for i, w in enumerate(blocks)
    ], "Locked EIEOS alias moved alignment"
    assert sum(r["realign"] for r in trace) == 1 and sum(r["eieos"] for r in trace) == 1
    assert not any(r["loss"] for r in trace)


def relock_case(tmp_path, source=RTL):
    cycles = []
    expect_tail = []
    for phase in range(1, 32):
        cycles += reset()
        start = len(cycles)
        lead = [EIEOS] + data(3, phase)
        tail = [EIEOS] + data(15, 900 + phase)
        stream = flat(lead) + [0] * phase + flat(tail)
        cycles += rows(stream)
        begin = start + (len(lead) * 130 + phase + 129) // 32
        expect_tail.append(
            (
                begin,
                [
                    (start + (len(lead) * 130 + phase + 130 * (i + 1) - 1) // 32, w)
                    for i, w in enumerate(tail)
                ],
            )
        )
    trace = run(tmp_path, cycles, source)
    for begin, expected in expect_tail:
        assert (
            trace[begin]["realign"]
            and trace[begin]["eieos"]
            and trace[begin]["aligned"]
        ), "Fresh search must move boundary"
        assert observed(trace[begin : expected[-1][0] + 1]) == expected, (
            "Reacquire must retain residual bits exactly"
        )


def loss_case(tmp_path, source=RTL):
    cycles = []
    ranges = []
    for header in (0, 3):
        cycles += reset()
        start = len(cycles)
        stream = flat(
            [EIEOS] + data(3, 41) + [(0xCAFE << 2) | header] + [EIEOS] + data(16, 42)
        )
        wr = rows(stream)
        wr = [(w, int(i < 5), v, f, r) for i, (w, s, v, f, r) in enumerate(wr)]
        cycles += wr
        fault = start + (5 * 130 - 1) // 32
        end = len(cycles)
        # Enabling search itself cannot acquire; only a new exact full pattern.
        next_start = len(cycles)
        tail = [EIEOS] + data(8, 43)
        cycles += rows(flat(tail))
        reacq = next_start + 4
        ranges.append((fault, end, reacq, tail, next_start))
    trace = run(tmp_path, cycles, source)
    for fault, end, reacq, tail, start in ranges:
        assert (
            trace[fault]["loss"]
            and not trace[fault]["valid"]
            and not trace[fault]["aligned"]
        )
        assert not any(r["valid"] or r["aligned"] for r in trace[fault:reacq]), (
            "Reasserted while disabled or before EIEOS"
        )
        assert observed(trace[reacq : start + (len(tail) * 130 - 1) // 32 + 1]) == [
            (start + (130 * (i + 1) - 1) // 32, w) for i, w in enumerate(tail)
        ]


def flush_case(tmp_path, source=RTL):
    cycles = []
    checks = []
    for mode in ("force", "gap", "reset"):
        cycles += reset()
        cycles += rows(flat([EIEOS] + data(3, 51)))
        at = len(cycles)
        cycles.append(
            (0, 0, int(mode != "gap"), int(mode == "force"), int(mode != "reset"))
        )
        # Complete patterns remain ignored until explicitly search-enabled.
        cycles += rows(flat([EIEOS] + data(8, 52)), search=0)
        stop = len(cycles)
        start = len(cycles)
        tail = [EIEOS] + data(8, 53)
        cycles += rows(flat(tail))
        checks.append((at, stop, start, tail, mode))
    trace = run(tmp_path, cycles, source)
    for at, stop, start, tail, mode in checks:
        assert not any(r["valid"] or r["aligned"] for r in trace[at:stop]), (
            "Discontinuity flush/disabled search failed"
        )
        assert bool(trace[at]["loss"]) == (mode != "reset")
        assert observed(trace[start : start + (len(tail) * 130 - 1) // 32 + 1]) == [
            (start + (130 * (i + 1) - 1) // 32, w) for i, w in enumerate(tail)
        ]


def control_edges_case(tmp_path, source=RTL):
    blocks = [EIEOS] + data(128, 62)
    cycles = reset()
    start = len(cycles)
    wr = rows(flat(blocks))
    wr = [
        (w, int(i < 5 or (i // 7) % 2), v, f, r) for i, (w, s, v, f, r) in enumerate(wr)
    ]
    cycles += wr
    stop = len(cycles)
    # Search falls exactly on the clock containing the last EIEOS bit: no lock.
    cycles += reset()
    forbidden_start = len(cycles)
    wr = rows(flat([EIEOS] + data(8, 64)))
    wr = [(w, int(i < 4), v, f, r) for i, (w, s, v, f, r) in enumerate(wr)]
    cycles += wr
    forbidden_end = len(cycles)
    # Force has priority even when that same raw word completes a full EIEOS.
    cycles += reset()
    force_start = len(cycles)
    wr = rows(bits(EIEOS))
    wr = [(w, s, v, int(i == 4), r) for i, (w, s, v, f, r) in enumerate(wr)]
    cycles += wr
    trace = run(tmp_path, cycles, source)
    assert observed(trace[start:stop]) == [
        (start + (130 * (i + 1) - 1) // 32, w) for i, w in enumerate(blocks)
    ], "Search toggling alone altered established boundary"
    assert sum(r["realign"] for r in trace[start:stop]) == 1
    assert not any(
        r["valid"] or r["aligned"] for r in trace[forbidden_start:forbidden_end]
    ), "Disabled acquisition on exact final-bit edge"
    assert not any(r["valid"] or r["aligned"] for r in trace[force_start:]), (
        "Force must override exact acquisition edge"
    )


CASES = {
    "phases": phase_case,
    "reject": reject_case,
    "frozen": frozen_case,
    "relock": relock_case,
    "loss": loss_case,
    "flush": flush_case,
    "control_edges": control_edges_case,
}


@pytest.mark.parametrize("name", CASES)
def test_actual_lane_alignment(tmp_path, name):
    CASES[name](tmp_path)


FAULTS = (
    (
        "short_pattern",
        "search_window[i +: 130] == EIEOS",
        "search_window[i +: 2] == EIEOS[1:0]",
        "reject",
    ),
    (
        "wrong_payload",
        "128'hff00ff00ff00ff00ff00ff00ff00ff00",
        "128'h00ff00ff00ff00ff00ff00ff00ff00ff",
        "phases",
    ),
    ("wrong_header", "2'b01};", "2'b10};", "phases"),
    (
        "no_search_gate",
        "block_align_control_i && (history_count_q",
        "1'b1 && (history_count_q",
        "frozen",
    ),
    (
        "never_search",
        "block_align_control_i && (history_count_q",
        "1'b0 && (history_count_q",
        "phases",
    ),
    ("miss_phase31", "i < 32", "i < 31", "phases"),
    (
        "drop_residual",
        "pending_count_q <= 31 - match_end",
        "pending_count_q <= 0",
        "phases",
    ),
    (
        "wrong_residual",
        "search_window >> (130 + match_end)",
        "search_window >> (129 + match_end)",
        "phases",
    ),
    ("wrong_cadence", "pending_count_q - 8'd98", "pending_count_q - 8'd97", "phases"),
    (
        "accept_invalid",
        "appended[1:0] == 2'b01 || appended[1:0] == 2'b10",
        "1'b1",
        "loss",
    ),
    (
        "ignore_force",
        "force_realign_i || !raw_valid_i",
        "1'b0 || !raw_valid_i",
        "flush",
    ),
    (
        "ignore_gap",
        "force_realign_i || !raw_valid_i",
        "force_realign_i || 1'b0",
        "flush",
    ),
)


@pytest.mark.parametrize("name,before,after,case", FAULTS, ids=[x[0] for x in FAULTS])
def test_actual_lane_alignment_fault(tmp_path, name, before, after, case):
    original = RTL.read_text()
    assert original.count(before) == 1
    source = tmp_path / "mutant.v"
    source.write_text(original.replace(before, after))
    with pytest.raises(AssertionError):
        CASES[case](tmp_path, source)
    # A tool failure cannot qualify: complete finite ROW trace must exist.
    assert (tmp_path / "run.log").is_file()
    assert "ROW " in (tmp_path / "run.log").read_text()
    assert not (tmp_path / "compile.log").read_text().lower().count("error")
