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
RTL = ROOT / "hw/soc/rtl/pcie/soc_pcie_gen3_lane_align_v2.v"
EIEOS = 1 | (int.from_bytes(bytes([0, 255] * 8), "little") << 2)
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
wire aligned,bv,eo,ro,lo,skp;wire[2:0] code;wire[193:0] block;
soc_pcie_gen3_lane_align_v2 dut(clk,rst,valid,raw,search,force_align,aligned,bv,block,code,skp,eo,ro,lo);
reg[35:0] stim[0:COUNT-1];integer i;
initial begin
$readmemh("INPUT",stim);
for(i=0;i<COUNT;i=i+1)begin
@(negedge clk);{rst,force_align,valid,search,raw}=stim[i];
@(posedge clk);#1;$display("ROW %0d %b %b %b %b %b %d %b %049h",i,aligned,bv,eo,ro,lo,code,skp,block);
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
            _, i, a, v, e, r, l, c, s, b = line.split()
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


CASES = {
    x.__name__: x
    for x in (
        phase_case,
        malformed_case,
        restart_case,
        reacquire_case,
        corrupted_eieos_case,
    )
}


@pytest.mark.parametrize("case", CASES.values())
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
