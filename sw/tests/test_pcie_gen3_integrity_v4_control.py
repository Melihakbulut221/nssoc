# SPDX-FileCopyrightText: 2026 Hasan Melih Akbulut
# SPDX-License-Identifier: Apache-2.0
"""Actual Boolean transition composition and full frozen-parser comparisons."""

import hashlib
import random
import re
import runpy
from pathlib import Path
import pytest

ROOT = Path(__file__).resolve().parents[2]
RTL = ROOT / "hw/soc/rtl/pcie"
GEN = runpy.run_path(str(ROOT / "scripts/generate_pcie_integrity_control_v4.py"))
OLD = runpy.run_path(str(ROOT / "sw/tests/test_pcie_gen3_integrity_v3_crc.py"))


def test_exact_generated_inverse_and_wrapper_bridge():
    source = (RTL / "soc_pcie_gen3_framer_rx_integrity_v4.v").read_text()
    assert source == GEN["candidate"]()
    source = source.replace(GEN["control"](), "").replace(
        "integrity_v4", "integrity_v3"
    )
    source = source.replace("`default_nettype none\n", "").replace(
        "`default_nettype wire\n", ""
    )
    for old, new in GEN["CHANGES"]:
        assert source.count(new) == 1
        source = source.replace(new, old)
    assert source == (RTL / "soc_pcie_gen3_framer_rx_integrity_v3.v").read_text()
    for name in [
        "hw/soc/rtl/pcie/soc_pcie_gen3_continuous_rx_integrity_v3.v",
        "scripts/check_pcie_gen3_continuous_rx_integrity_v3.py",
        "hw/soc/tb/cocotb/test_soc_pcie_gen3_continuous_rx_integrity_v3.py",
        "hw/soc/tb/cocotb/Makefile.soc_pcie_gen3_continuous_rx_integrity_v3",
    ]:
        original = ROOT / name
        current = ROOT / name.replace("_v3", "_v4")
        text = current.read_text().replace("integrity_v4", "integrity_v3")
        if current.suffix == ".v":
            text = text.replace("`default_nettype none\n", "").replace(
                "`default_nettype wire\n", ""
            )
        assert text == original.read_text()


def sequential_transition(mode, flags):
    stp, sdp, idl, eds, edb, final, bad = [bool(flags & (1 << i)) for i in range(7)]
    if mode >= 5:
        return mode
    if mode == 1:
        return (7 if bad else 2) if final else 1
    if mode == 3:
        return 0
    if mode == 4:
        return 4
    if mode == 2:
        if edb:
            return 0
        if not (stp or sdp or idl or eds):
            return 6
    if idl:
        return 0
    if eds:
        return 5
    if stp:
        return 4
    if sdp:
        return 3
    return 5


def product(left, right):
    # Independent matrix interpretation: enumerate every source's intermediate
    # destination and the successor's destination (including nondeterminism).
    out = 0
    for source in range(8):
        for mid in range(8):
            if right & (1 << (mid * 8 + source)):
                for dest in range(8):
                    if left & (1 << (dest * 8 + mid)):
                        out |= 1 << (dest * 8 + source)
    return out


@pytest.mark.parametrize(
    "fault", [None, "reverse_composition", "stop_look_state", "carry_bad_ignored"]
)
def test_actual_transition_and_matrix_functions(tmp_path, fault):
    source = (RTL / "soc_pcie_gen3_framer_rx_integrity_v4.v").read_text()
    functions = "\n".join(
        re.findall(
            r" function automatic \[(?:63|7):0\] control_.*? endfunction", source, re.S
        )
    )
    assert functions.count("function automatic") == 3
    if fault == "reverse_composition":
        functions = (
            functions.replace("later[destination*8+", "SWAP[destination*8+")
            .replace("earlier[", "later[")
            .replace("SWAP[", "earlier[")
        )
    elif fault == "stop_look_state":
        functions = functions.replace("6:destination=3'd6;", "6:destination=3'd5;")
    elif fault == "carry_bad_ignored":
        functions = functions.replace("carry_bad?3'd7:3'd2", "carry_bad?3'd2:3'd2")
    lines = ["`default_nettype none", "module tb;", functions, "initial begin"]
    count = 0
    for flags in range(128):
        table = sum(
            1 << (sequential_transition(mode, flags) * 8 + mode) for mode in range(8)
        )
        args = ",".join(f"1'b{(flags >> i) & 1}" for i in range(7))
        lines.append(
            f'if(control_transition({args})!==64\'h{table:x}) $fatal(1,"CONTROL_TABLE_{count}");'
        )
        count += 1
    # Every pair of single-edge matrices checks every composition coordinate;
    # dense random matrices also check OR union and multiple intermediate paths.
    vectors = [(1 << a, 1 << b) for a in range(64) for b in range(64)]
    rng = random.Random(1845819)
    vectors.extend((rng.getrandbits(64), rng.getrandbits(64)) for _ in range(256))
    for left, right in vectors:
        expected = product(left, right)
        lines.append(
            f"if(control_compose(64'h{left:x},64'h{right:x})!==64'h{expected:x}) $fatal(1,\"CONTROL_MATRIX_{count}\");"
        )
        count += 1
    for _ in range(256):
        matrix, initial = rng.getrandbits(64), rng.getrandbits(8)
        expected = sum(
            int(
                any(
                    initial & (1 << i) and matrix & (1 << (d * 8 + i)) for i in range(8)
                )
            )
            << d
            for d in range(8)
        )
        lines.append(
            f"if(control_apply(64'h{matrix:x},8'h{initial:x})!==8'h{expected:x}) $fatal(1,\"CONTROL_APPLY_{count}\");"
        )
        count += 1
    lines += [
        f'$display("PASS {count} ACTUAL_CONTROL_FUNCTION_VECTORS");$finish;end endmodule',
        "`default_nettype wire",
    ]
    result, log = OLD["simulate"](tmp_path, "\n".join(lines))
    if fault:
        assert result.returncode != 0 and (
            "CONTROL_TABLE_" in log or "CONTROL_MATRIX_" in log
        )
    else:
        assert result.returncode == 0 and f"PASS {count}" in log


@pytest.mark.parametrize(
    "fault",
    [None, "carried_wrap", "header_after_stp", "ending_mask", "look_stopped_state"],
)
def test_actual_v3_v4_parser_state_comparison(tmp_path, fault):
    source = (RTL / "soc_pcie_gen3_framer_rx_integrity_v4.v").read_text()
    edits = {
        "carried_wrap": ("remaining==(control_word+1)", "remaining==control_word"),
        "header_after_stp": (
            "control_modes[control_word][4] &&",
            "control_modes[control_word][1] &&",
        ),
        "ending_mask": ("!ending && (|control_modes", "1'b1 && (|control_modes"),
        "look_stopped_state": (
            "control_modes[control_word][2]||control_modes[control_word][6]",
            "control_modes[control_word][2]||1'b0",
        ),
    }
    if fault:
        old, new = edits[fault]
        assert old in source
        source = source.replace(old, new)
    candidate = tmp_path / "candidate.v"
    candidate.write_text(source)
    bench = OLD["parser_miter"]().replace("_v3", "_v4").replace("_v2", "_v3")
    result, log = OLD["simulate"](
        tmp_path, bench, [RTL / "soc_pcie_gen3_framer_rx_integrity_v3.v", candidate]
    )
    if fault:
        assert result.returncode != 0 and "PARSER_ARBITRARY_STATE_MISMATCH" in log
    else:
        assert result.returncode == 0 and "PASS 32768" in log
    (tmp_path / "candidate.sha256").write_text(
        hashlib.sha256(source.encode()).hexdigest() + "\n"
    )
