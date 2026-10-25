# SPDX-FileCopyrightText: 2026 Hasan Melih Akbulut
# SPDX-License-Identifier: Apache-2.0
"""Actual public-port bitstream tests, independent of RTL shift/register layout."""

import json
import hashlib
from pathlib import Path
import random
import shutil
import subprocess

import pytest

ROOT = Path(__file__).resolve().parents[2]
RTL = ROOT / "hw/soc/rtl/pcie/soc_pcie_gen3_lane_align_v3.v"
EIEOS = 1 | (int.from_bytes(bytes([0, 255] * 8), "little") << 2)
SDS = 1 | (int.from_bytes(bytes([0xE1] + [0x55] * 15), "little") << 2)
MASK = (1 << 194) - 1


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
wire aligned,bv,eo,ro,lo,skp,locked,sds;wire[2:0] code;wire[193:0] block;
soc_pcie_gen3_lane_align_v3 dut(clk,rst,valid,raw,search,force_align,aligned,bv,block,code,skp,eo,ro,lo,locked,sds);
reg[35:0] stim[0:COUNT-1];integer i;
initial begin
$readmemh("INPUT",stim);
for(i=0;i<COUNT;i=i+1)begin
@(negedge clk);{rst,force_align,valid,search,raw}=stim[i];
@(posedge clk);#1;$display("ROW %0d %b %b %b %b %b %d %b %049h %b %b",i,aligned,bv,eo,ro,lo,code,skp,block,locked,sds);
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
            _, i, a, v, e, r, l, c, s, b, lk, sd = line.split()
            out.append(
                dict(
                    cycle=int(i),
                    aligned=int(a),
                    valid=int(v),
                    eieos=int(e),
                    realign=int(r),
                    loss=int(l),
                    block=int(b, 16),
                    code=int(c),
                    skp=int(s),
                    locked=int(lk),
                    sds=int(sd),
                )
            )
    if len(out) != len(cycles):
        raise RuntimeError("Incomplete native public-port trace")
    (tmp_path / "commands.json").write_text(
        json.dumps(dict(compile=command, simulate=[vvp, str(exe)]), indent=2) + "\n"
    )
    return out


def observed(trace):
    return [(r["cycle"], r["block"], r["code"], r["skp"]) for r in trace if r["valid"]]


def skp(code, trailer=b"\x12\x34\x56"):
    payload = bytes([0xAA] * (4 + 4 * code) + [0xE1]) + trailer
    return 1 | (int.from_bytes(payload, "little") << 2), 66 + 32 * code, code, 1


def normal(value, header=2):
    return (value << 2) | header, 130, 2, 0


def append_stream(cycles, blocks, phase=0, search_after_acquire=False):
    start = len(cycles)
    stream = [0] * phase
    expected = []
    for value, length, code, is_skp in blocks:
        stream += bits(value, length)
        expected.append((start + (len(stream) - 1) // 32, value, code, is_skp))
    first = expected[0][0] - start
    cycles += [
        (w, int(search_after_acquire or i <= first), 1, 0, 1)
        for i, w in enumerate(words(stream))
    ]
    return expected


def phase_case(tmp_path, source=RTL):
    rng = random.Random(508194)
    cycles, expected, acquire = [], [], []
    for phase in range(32):
        cycles += reset()
        blocks = [(EIEOS, 130, 2, 0)]
        # All25 adjacent length transitions, opaque trailer aliases and data
        # words starting with AA/E1 must preserve the independently built bits.
        for first in range(5):
            for second in range(5):
                blocks += [
                    skp(first, bytes([0xAA, 0xE1, first])),
                    skp(second, rng.randbytes(3)),
                    normal((rng.getrandbits(120) << 8) | 0xAA),
                    normal(int.from_bytes(bytes([0x66] * 16), "little"), 1),
                ]
        observed_blocks = append_stream(cycles, blocks, phase)
        expected += observed_blocks
        acquire.append(observed_blocks[0][0])
    trace = run(tmp_path, cycles, source)
    assert observed(trace) == expected, "VARIABLE_BITSTREAM_CADENCE_OR_CONTENT"
    assert [x["cycle"] for x in trace if x["eieos"]] == acquire
    assert [x["cycle"] for x in trace if x["realign"]] == acquire
    assert not any(x["loss"] for x in trace), "LEGAL_STREAM_LOST_LOCK"


def malformed_case(tmp_path, source=RTL):
    cycles, regions = [], []
    # All accessible first4N+1 bytes except the first identifying AA. A change
    # of the first byte can identify a different OS, which this block delegates.
    for code in range(5):
        good, length, _, _ = skp(code)
        for byte in range(1, 5 + 4 * code):
            for bit in range(8):
                cycles += reset()
                start = len(cycles)
                bad = good ^ (1 << (2 + 8 * byte + bit))
                append_stream(
                    cycles, [(EIEOS, 130, 2, 0), (bad, length, code, 1), normal(0)]
                )
                regions.append((start, len(cycles)))
    # Too short, nonmultiple prefix and a sixth group cannot establish a boundary.
    for n in (0, 1, 2, 3, 5, 6, 7, 9, 10, 11, 13, 14, 15, 17, 18, 19, 21, 24):
        payload = bytes([0xAA] * n + [0xE1, 0x12, 0x34, 0x56])
        # Zero AA is a different OS identifier, not classified as SKP here.
        if not n:
            continue
        cycles += reset()
        start = len(cycles)
        stream = (
            bits(EIEOS)
            + bits(1 | (int.from_bytes(payload, "little") << 2), len(payload) * 8 + 2)
            + [0] * 224
        )
        chunk = rows(stream)
        cycles += [(w, int(i < 5), v, f, r) for i, (w, s, v, f, r) in enumerate(chunk)]
        regions.append((start, len(cycles)))
    trace = run(tmp_path, cycles, source)
    for start, end in regions:
        chunk = trace[start:end]
        assert sum(x["loss"] for x in chunk) == 1, "MALFORMED_SKP_NOT_REJECTED"
        assert sum(x["valid"] for x in chunk) == 1, "MALFORMED_SKP_RELEASED"
        assert not chunk[-1]["aligned"], "MALFORMED_SKP_REACQUIRED_WITHOUT_SEARCH"


def restart_case(tmp_path, source=RTL):
    cycles, starts = [], []
    for prefix in range(1, 7):
        for mode in ("gap", "force", "reset"):
            cycles += reset()
            # Force interruption while a variable-length block is incomplete.
            long, length, _, _ = skp(4)
            # Build one contiguous serial stream: independently padding the
            # EIEOS to32 bits would lose alignment before exercising the reset.
            chunk = rows(bits(EIEOS) + bits(long, length))[: (130 + prefix * 32) // 32]
            cycles += [
                (w, int(i < 5), v, f, r) for i, (w, s, v, f, r) in enumerate(chunk)
            ]
            interrupt = len(cycles)
            cycles += [
                (0, 0, int(mode != "gap"), int(mode == "force"), int(mode != "reset"))
            ]
            cycles += [(0, 0, 1, 0, 1)] * 8
            expected = append_stream(
                cycles,
                [(EIEOS, 130, 2, 0), skp(prefix % 5), normal(0x123456)],
                phase=prefix,
            )
            starts.append((interrupt, expected))
    trace = run(tmp_path, cycles, source)
    for interrupt, expected in starts:
        assert trace[interrupt - 1]["aligned"], "TEST_MUST_INTERRUPT_LOCKED_PARTIAL_SKP"
        assert not trace[interrupt]["aligned"] and not trace[interrupt]["valid"]
        assert not any(
            x["aligned"] or x["valid"] for x in trace[interrupt + 1 : interrupt + 9]
        )
        for cycle, value, code, is_skp in expected:
            x = trace[cycle]
            assert x["valid"] and (x["block"], x["code"], x["skp"]) == (
                value,
                code,
                is_skp,
            ), "RESTART_STALE_BITS"


def reacquire_case(tmp_path, source=RTL):
    cycles, expected = [], []
    for phase in range(32):
        for prefix in (4, 31, 66, 97, 130, 161, 193):
            cycles += reset()
            start = len(cycles)
            value, length, _, _ = skp(4)
            stream = [0] * phase + bits(EIEOS) + bits(value, length)[:prefix]
            stream += bits(EIEOS) + bits(2 | (0x123456789ABCDEF << 2))
            cycles += rows(stream)
            expected += [
                (start + (phase + 130 + prefix + 129) // 32, EIEOS, 2, 0),
                (
                    start + (phase + 130 + prefix + 259) // 32,
                    2 | (0x123456789ABCDEF << 2),
                    2,
                    0,
                ),
            ]
    trace = run(tmp_path, cycles, source)
    for cycle, value, code, is_skp in expected:
        x = trace[cycle]
        assert (
            x["valid"]
            and x["aligned"]
            and (x["block"], x["code"], x["skp"]) == (value, code, is_skp)
        ), "EIEOS_REACQUISITION_FAILED"


def corrupted_eieos_case(tmp_path, source=RTL):
    cycles = []
    for bit in range(130):
        cycles += reset() + rows([0] * 13 + bits(EIEOS ^ (1 << bit)) + [0] * 256)
    trace = run(tmp_path, cycles, source)
    assert not any(x["aligned"] or x["valid"] or x["eieos"] for x in trace), (
        "CORRUPT_EIEOS_ACQUIRED"
    )


BASE_CASES = {
    x.__name__: x
    for x in (
        phase_case,
        malformed_case,
        restart_case,
        reacquire_case,
        corrupted_eieos_case,
    )
}


@pytest.mark.parametrize("case", BASE_CASES.values())
def test_actual_variable_lane_ports(tmp_path, case):
    case(tmp_path)


FAULTS = [
    (
        "fixed130",
        "consume_bits = 2 + (symbol + 4)*8;",
        "consume_bits = 130;",
        phase_case,
        "VARIABLE_BITSTREAM",
    ),
    (
        "header",
        "appended[1:0] == 2'b01 && appended_count",
        "appended[1:0] == 2'b10 && appended_count",
        phase_case,
        "VARIABLE_BITSTREAM",
    ),
    (
        "end",
        "character == 8'he1",
        "character == 8'he0",
        phase_case,
        "VARIABLE_BITSTREAM",
    ),
    (
        "mask",
        "appended[193:0] & block_mask",
        "appended[193:0]",
        phase_case,
        "VARIABLE_BITSTREAM",
    ),
    (
        "consume",
        "appended >> consume_bits",
        "appended >> (consume_bits-1)",
        phase_case,
        "VARIABLE_BITSTREAM",
    ),
    (
        "length",
        "consume_code = (symbol - 4)/4;",
        "consume_code = 2;",
        phase_case,
        "VARIABLE_BITSTREAM",
    ),
    ("trailer", "(symbol + 4)*8", "(symbol + 3)*8", phase_case, "VARIABLE_BITSTREAM"),
    (
        "prefix",
        "character != 8'haa || symbol == 20",
        "symbol == 20",
        malformed_case,
        "MALFORMED_SKP",
    ),
    ("boundary", "symbol % 4 == 0", "1'b1", malformed_case, "MALFORMED_SKP"),
    ("loss", "loss_o <= 1'b1;", "loss_o <= 1'b0;", malformed_case, "MALFORMED_SKP"),
    (
        "restart",
        "if (force_realign_i || !raw_valid_i)",
        "if (!raw_valid_i)",
        restart_case,
        None,
    ),
    (
        "search",
        "else if (match_found)",
        "else if (match_found && !aligned_o)",
        reacquire_case,
        "EIEOS_REACQUISITION",
    ),
]


@pytest.mark.parametrize("fault,old,new,case,message", FAULTS)
def test_actual_mutation_controls(tmp_path, fault, old, new, case, message):
    original = RTL.read_text()
    assert old in original
    mutant = tmp_path / (fault + ".v")
    mutant.write_text(original.replace(old, new))
    with pytest.raises(AssertionError, match=message):
        case(tmp_path / "actual", mutant)


def false_eieos_data_pair(offset):
    """Two legal DATA blocks containing an unaligned EIEOS across their boundary."""
    pattern = bits(EIEOS)
    assert 2 <= offset < 129 and pattern[130 - offset : 132 - offset] == [0, 1]
    serial = bits(2) + bits(2)
    serial[offset : offset + 130] = pattern
    assert serial[:2] == serial[130:132] == [0, 1]
    return [
        (sum(bit << j for j, bit in enumerate(serial[i : i + 130])), 130, 2, 0)
        for i in (0, 130)
    ]


def locked_phase_case(tmp_path, source=RTL):
    cycles, expected, lock_regions, acquisitions, sds_cycles, eieos_cycles = (
        [],
        [],
        [],
        [],
        [],
        [],
    )
    offsets = [k for k in range(2, 129) if bits(EIEOS)[130 - k : 132 - k] == [0, 1]]
    assert offsets, "Independent false-pattern fixture must actually contain EIEOS"
    for phase in range(32):
        cycles += reset()
        blocks = [(EIEOS, 130, 2, 0), (SDS, 130, 2, 0)]
        # All 25 SKP-length transitions remain valid after local lock, while
        # raw search is deliberately left enabled for the entire DATA stream.
        for a in range(5):
            for b in range(5):
                blocks += [
                    skp(a),
                    skp(b),
                    *false_eieos_data_pair(offsets[(a * 5 + b) % len(offsets)]),
                ]
        # Exact aligned EIEOS is still classified, but cannot adjust alignment.
        blocks += [
            (EIEOS, 130, 2, 0),
            (SDS, 130, 2, 0),
            normal(SDS >> 2),
            normal(0x4567),
        ]
        exp = append_stream(cycles, blocks, phase, search_after_acquire=True)
        expected += exp
        acquisitions.append(exp[0][0])
        sds_cycles += [exp[1][0], exp[-3][0]]
        eieos_cycles += [exp[0][0], exp[-4][0]]
        lock_regions.append((exp[1][0], len(cycles)))
    trace = run(tmp_path, cycles, source)
    assert observed(trace) == expected, "LOCKED_BITSTREAM_CADENCE_OR_CONTENT"
    assert [r["cycle"] for r in trace if r["realign"]] == acquisitions, (
        "LOCKED_FALSE_REALIGNMENT"
    )
    assert [r["cycle"] for r in trace if r["sds"]] == sds_cycles, "SDS_CLASSIFICATION"
    assert [r["cycle"] for r in trace if r["eieos"]] == eieos_cycles, (
        "ALIGNED_EIEOS_CLASSIFICATION"
    )
    assert not any(r["loss"] for r in trace), "LOCKED_LEGAL_STREAM_LOSS"
    for start, end in lock_regions:
        assert all(r["locked"] and r["aligned"] for r in trace[start:end]), (
            "LOCAL_SDS_LOCK_MISSING"
        )
        assert not trace[start - 1]["locked"], "PREMATURE_SDS_LOCK"


def malformed_sds_case(tmp_path, source=RTL):
    cycles, regions = [], []
    # Every payload-bit corruption remains a legal ordinary OS, never SDS.
    for bit in range(2, 130):
        cycles += reset()
        start = len(cycles)
        append_stream(
            cycles, [(EIEOS, 130, 2, 0), (SDS ^ (1 << bit), 130, 2, 0), normal(0)]
        )
        regions.append((start, len(cycles)))
    # Correct payload with DATA or invalid header must not lock either.
    for header in (0, 2, 3):
        cycles += reset()
        start = len(cycles)
        append_stream(
            cycles, [(EIEOS, 130, 2, 0), ((SDS & ~3) | header, 130, 2, 0), normal(0)]
        )
        regions.append((start, len(cycles)))
    # Every proper prefix followed by a contradictory suffix must not lock.
    # Supplied padding is real input, so a zero tail alone can complete SDS.
    for count in range(2, 130):
        cycles += reset()
        start = len(cycles)
        chunk = rows(
            bits(EIEOS) + bits(SDS)[:count] + [1 - bits(SDS)[count]] + [0] * 160
        )
        cycles += [(w, int(i < 5), v, f, r) for i, (w, s, v, f, r) in enumerate(chunk)]
        regions.append((start, len(cycles)))
    trace = run(tmp_path, cycles, source)
    for start, end in regions:
        assert not any(r["sds"] or r["locked"] for r in trace[start:end]), (
            "MALFORMED_OR_PARTIAL_SDS_LOCK"
        )


def pre_sds_realign_case(tmp_path, source=RTL):
    cycles, last_acquisitions, locks = [], [], []
    for phase in range(32):
        cycles += reset()
        start = len(cycles)
        # Each incomplete ordinary block is interrupted by a new EIEOS at a
        # different raw offset before SDS. Search must remain active locally.
        stream = [0] * phase + bits(EIEOS)
        for n in (17, 53, 91):
            stream += bits(2 | (0x1234 << 2))[:n] + bits(EIEOS)
        last = start + (len(stream) - 1) // 32
        stream += bits(SDS) + bits(2 | (0x334455 << 2))
        cycles += rows(stream)
        last_acquisitions.append(last)
        locks.append(start + (len(stream) - 131) // 32)
    trace = run(tmp_path, cycles, source)
    for acquired, locked in zip(last_acquisitions, locks, strict=True):
        assert trace[acquired]["realign"] and trace[acquired]["eieos"], (
            "PRE_SDS_REALIGNMENT_DISABLED"
        )
        assert not trace[acquired]["locked"], "LOCK_BEFORE_SDS"
        assert trace[locked]["sds"] and trace[locked]["locked"], (
            "SDS_AFTER_REALIGNMENT_MISSING"
        )


def lock_restart_case(tmp_path, source=RTL):
    cycles, checks = [], []
    for mode in ("gap", "force", "reset", "header", "skp"):
        for phase in range(32):
            cycles += reset()
            exp = append_stream(
                cycles,
                [(EIEOS, 130, 2, 0), (SDS, 130, 2, 0)],
                phase,
                search_after_acquire=True,
            )
            lock = exp[-1][0]
            # Fill the raw-word residual with subsequent bits of the same
            # stream. For header/SKP test build contiguous source from scratch.
            if mode in ("header", "skp"):
                start = lock - (phase + 259) // 32
                del cycles[start:]
                bad = bits(0) if mode == "header" else bits(1 | (0x22AA << 2))
                cycles += rows([0] * phase + bits(EIEOS) + bits(SDS) + bad + [0] * 192)
                interrupt = lock + 1
            else:
                interrupt = len(cycles)
                cycles += [
                    (
                        0,
                        1,
                        int(mode != "gap"),
                        int(mode == "force"),
                        int(mode != "reset"),
                    )
                ]
            end = len(cycles)
            cycles += [(0, 0, 1, 0, 1)] * 6
            new = append_stream(
                cycles,
                [(EIEOS, 130, 2, 0), (SDS, 130, 2, 0), normal(0)],
                (phase + 7) % 32,
                search_after_acquire=True,
            )
            checks.append((mode, lock, interrupt, end, new))
    trace = run(tmp_path, cycles, source)
    for mode, lock, interrupt, end, new in checks:
        assert trace[lock]["sds"] and trace[lock]["locked"], (
            "RESTART_REQUIRES_INITIAL_LOCK"
        )
        tail = trace[interrupt:end]
        if mode != "reset":
            assert sum(r["loss"] for r in tail) == 1, "LOCK_LOSS_NOT_REPORTED"
        assert not trace[end - 1]["locked"] and not trace[end - 1]["aligned"], (
            "LOCK_NOT_CLEARED"
        )
        for cycle, value, code, is_skp in new:
            assert trace[cycle]["valid"] and trace[cycle]["block"] == value, (
                "POST_UNLOCK_STALE_BITS"
            )
        assert trace[new[1][0]]["locked"] and trace[new[1][0]]["sds"], "RELOCK_FAILED"


def disabled_search_sds_case(tmp_path, source=RTL):
    cycles = []
    for phase in range(32):
        cycles += reset() + rows(
            [0] * phase + bits(EIEOS) + bits(SDS) + bits(2), search=0
        )
    disabled_end = len(cycles)
    cycles += reset()
    blocks = [(EIEOS, 130, 2, 0), (SDS, 130, 2, 0), (EIEOS, 130, 2, 0), normal(0)]
    exp = append_stream(cycles, blocks, phase=19)
    trace = run(tmp_path, cycles, source)
    assert not any(
        r["aligned"] or r["valid"] or r["locked"] for r in trace[:disabled_end]
    ), "DISABLED_SEARCH_ACQUIRED"
    assert observed(trace) == exp, "DISABLED_SEARCH_CHANGED_ALIGNED_EXTRACTION"
    assert trace[exp[1][0]]["locked"] and trace[exp[1][0]]["sds"], (
        "SDS_MUST_NOT_REQUIRE_SEARCH"
    )
    assert trace[exp[2][0]]["eieos"] and not trace[exp[2][0]]["realign"], (
        "ALIGNED_EIEOS_CLASSIFICATION"
    )


def incomplete_sds_gap_case(tmp_path, source=RTL):
    cycles, regions = [], []
    for phase in range(32):
        stream = [0] * phase + bits(EIEOS) + bits(SDS)
        raw = rows(stream)
        for cut in range((phase + 129) // 32 + 1, (phase + 259) // 32 + 1):
            cycles += reset()
            start = len(cycles)
            cycles += raw[:cut]
            gap = len(cycles)
            cycles += [(0, 1, 0, 0, 1)]
            cycles += raw[cut:] + rows([0] * 192)
            end = len(cycles)
            new = append_stream(
                cycles,
                [(EIEOS, 130, 2, 0), (SDS, 130, 2, 0), normal(0)],
                phase,
                search_after_acquire=True,
            )
            regions.append((start, gap, end, new))
    trace = run(tmp_path, cycles, source)
    for start, gap, end, new in regions:
        assert trace[gap - 1]["aligned"], "PARTIAL_SDS_FIXTURE_REQUIRES_ALIGNMENT"
        assert not any(r["locked"] or r["sds"] for r in trace[start:end]), (
            "INCOMPLETE_SDS_LOCK"
        )
        assert trace[gap]["loss"] and not trace[gap]["aligned"], (
            "PARTIAL_GAP_MUST_LOSE_ALIGNMENT"
        )
        assert trace[new[1][0]]["locked"] and trace[new[1][0]]["sds"], (
            "PARTIAL_GAP_RESTART"
        )


SDS_CASES = {
    x.__name__: x
    for x in (
        locked_phase_case,
        malformed_sds_case,
        pre_sds_realign_case,
        lock_restart_case,
        disabled_search_sds_case,
        incomplete_sds_gap_case,
    )
}
CASES = {**BASE_CASES, **SDS_CASES}


@pytest.mark.parametrize("case", SDS_CASES.values())
def test_actual_local_sds_ports(tmp_path, case):
    case(tmp_path)


SDS_FAULTS = [
    (
        "ignore_external_search",
        "block_align_control_i && !locked_o",
        "!locked_o",
        disabled_search_sds_case,
        "DISABLED_SEARCH_ACQUIRED",
    ),
    (
        "premature_lock",
        "end else if (aligned_o) begin",
        "end else if (aligned_o) begin\n                    if (appended_count >= 10 && appended[9:2] == 8'he1) locked_o <= 1'b1;",
        incomplete_sds_gap_case,
        "INCOMPLETE_SDS",
    ),
    (
        "search_after_lock",
        "block_align_control_i && !locked_o",
        "block_align_control_i",
        locked_phase_case,
        "LOCKED",
    ),
    (
        "never_lock",
        "locked_o <= 1'b1;",
        "locked_o <= 1'b0;",
        locked_phase_case,
        "LOCKED|LOCAL",
    ),
    (
        "identifier_only",
        "appended[129:0] == SDS",
        "appended[9:2] == 8'he1",
        malformed_sds_case,
        "MALFORMED",
    ),
    (
        "ignore_sds_header",
        "appended[129:0] == SDS",
        "appended[129:2] == SDS[129:2]",
        malformed_sds_case,
        "MALFORMED",
    ),
    (
        "wrong_symbol_order",
        "{{15{8'h55}}, 8'he1, 2'b01}",
        "{8'he1, {15{8'h55}}, 2'b01}",
        locked_phase_case,
        "LOCKED|SDS",
    ),
    (
        "stale_lock",
        "                locked_o <= 1'b0;\n                loss_o <= aligned_o;",
        "                locked_o <= locked_o;\n                loss_o <= aligned_o;",
        lock_restart_case,
        "LOCK|RESTART",
    ),
    (
        "pulse_lock",
        "sds_o <= 1'b0;\n            realign_o",
        "sds_o <= 1'b0;\n            locked_o <= 1'b0;\n            realign_o",
        locked_phase_case,
        "LOCKED|LOCAL",
    ),
    (
        "unclassified_aligned_eieos",
        "eieos_o <= consume_bits == 130 && appended[129:0] == EIEOS;",
        "eieos_o <= 1'b0;",
        disabled_search_sds_case,
        "ALIGNED_EIEOS",
    ),
    (
        "aligned_realign",
        "eieos_o <= consume_bits == 130 && appended[129:0] == EIEOS;",
        "eieos_o <= consume_bits == 130 && appended[129:0] == EIEOS;\n                        realign_o <= appended[129:0] == EIEOS;",
        disabled_search_sds_case,
        "ALIGNED_EIEOS",
    ),
    (
        "require_search_for_sds",
        "appended[129:0] == SDS",
        "block_align_control_i && appended[129:0] == SDS",
        disabled_search_sds_case,
        "SDS_MUST",
    ),
]


@pytest.mark.parametrize("fault,old,new,case,message", SDS_FAULTS)
def test_actual_sds_mutants(tmp_path, fault, old, new, case, message):
    original = RTL.read_text()
    assert old in original, "Mutation must target actual frozen source"
    mutant = tmp_path / (fault + ".v")
    mutant.write_text(original.replace(old, new))
    with pytest.raises(AssertionError, match=message):
        case(tmp_path / "actual", mutant)


def test_exact_v2_algorithm_conservation():
    """Only declared local-lock/classifier additions change the frozen V2 body."""
    old = ROOT / "hw/soc/rtl/pcie/soc_pcie_gen3_lane_align_v2.v"
    assert (
        hashlib.sha256(old.read_bytes()).hexdigest()
        == "ad5671d1f04a632118d982e94b3d034251d8fe3ea7e9b7c6f61d0aa68e646fd4"
    )
    body = RTL.read_text().split("module ", 1)[1]
    body = body.replace("lane_align_v3", "lane_align_v2")
    body = body.replace(
        "output reg loss_o,\n    output reg locked_o,\n    output reg sds_o",
        "output reg loss_o",
    )
    body = body.replace(
        "    localparam [129:0] SDS = {{15{8'h55}}, 8'he1, 2'b01};\n", ""
    )
    body = body.replace("block_align_control_i && !locked_o", "block_align_control_i")
    body = "\n".join(
        line
        for line in body.split("\n")
        if not any(token in line for token in ("locked_o <= 1'b0;", "sds_o <= 1'b0;"))
    )
    addition = """                        eieos_o <= consume_bits == 130 && appended[129:0] == EIEOS;
                        sds_o <= consume_bits == 130 && appended[129:0] == SDS;
                        if (consume_bits == 130 && appended[129:0] == SDS)
                            locked_o <= 1'b1;
"""
    assert body.count(addition) == 1
    body = body.replace(addition, "").replace("`default_nettype wire\n", "")
    assert body == old.read_text().split("module ", 1)[1]
