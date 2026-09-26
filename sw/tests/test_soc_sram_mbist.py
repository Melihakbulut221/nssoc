# SPDX-FileCopyrightText: 2026 Hasan Melih Akbulut
# SPDX-License-Identifier: Apache-2.0
"""Execute MBIST RTL; compare against an independent transaction/fault oracle."""

from itertools import product
from pathlib import Path
import shutil
import subprocess

import pytest

ROOT = Path(__file__).resolve().parents[2]
RTL = ROOT / "hw/soc/rtl/dft/soc_sram_mbist.v"
TB = ROOT / "hw/soc/tb/tb_soc_sram_mbist.v"
MUTATIONS = {
    "comparison": ("rdata_i !== expected", "1'b0"),
    "last_address": ("ADDR_WIDTH'(DEPTH-1)", "ADDR_WIDTH'(DEPTH-2)"),
    "descending": ("address_q <= address_q - 1'b1", "address_q <= address_q + 1'b1"),
    "background": ("background[bit_index] =", "background[0] ="),
    "clear_pass": (
        "background_q == 8'(PARTITIONS + 1)",
        "background_q == 8'(PARTITIONS)",
    ),
    "abort": (
        "rst_ni && !abort_i && (state_q == ISSUE)",
        "rst_ni && (state_q == ISSUE)",
    ),
}


def golden(width, depth):
    """Operation list from the six March elements, not from the DUT states."""
    ones = (1 << width) - 1
    backgrounds = (
        [0]
        + [
            sum(((bit >> group) & 1) << bit for bit in range(width))
            for group in range((width - 1).bit_length())
        ]
        + [0]
    )
    for bg_id, bg in enumerate(backgrounds):
        elements = [
            (False, [("w", bg)]),
            (False, [("r", bg), ("w", bg ^ ones)]),
            (False, [("r", bg ^ ones), ("w", bg)]),
            (True, [("r", bg), ("w", bg ^ ones)]),
            (True, [("r", bg ^ ones), ("w", bg)]),
            (True, [("r", bg)]),
        ]
        for phase, (reverse, operations) in enumerate(elements):
            for address in reversed(range(depth)) if reverse else range(depth):
                for operation, data in operations:
                    yield operation, address, data, phase, bg_id


@pytest.fixture(scope="module")
def compile_rtl(tmp_path_factory):
    compiler, runtime = shutil.which("iverilog"), shutil.which("vvp")
    if not compiler or not runtime:
        pytest.skip("Icarus Verilog is required for MBIST RTL verification")
    cache = {}

    def compile_one(width=4, depth=4, latency=1, mutation=None):
        key = width, depth, latency, mutation
        if key not in cache:
            folder = tmp_path_factory.mktemp("mbist")
            source, binary = folder / "mbist.v", folder / "run.vvp"
            text = RTL.read_text()
            if mutation:
                old, new = MUTATIONS[mutation]
                assert old in text
                text = text.replace(old, new)
            source.write_text(text)
            p = subprocess.run(
                [
                    compiler,
                    "-g2012",
                    "-s",
                    "tb_soc_sram_mbist",
                    f"-Ptb_soc_sram_mbist.WIDTH={width}",
                    f"-Ptb_soc_sram_mbist.DEPTH={depth}",
                    f"-Ptb_soc_sram_mbist.LATENCY={latency}",
                    "-o",
                    str(binary),
                    str(source),
                    str(TB),
                ],
                capture_output=True,
                text=True,
                timeout=30,
            )
            assert p.returncode == 0, p.stderr
            cache[key] = [runtime, str(binary)]
        return cache[key]

    return compile_one


def execute(command, **parameters):
    return subprocess.run(
        command + [f"+{key}={value}" for key, value in parameters.items()],
        capture_output=True,
        text=True,
        timeout=30,
    )


def audit(result, width, depth, faulty=False):
    assert result.returncode == 0, result.stdout + result.stderr
    assert "PASS protocol" in result.stdout
    expected = iter(golden(width, depth))
    pending = None
    first_error = None
    for line in result.stdout.splitlines():
        fields = line.split()
        if fields[0] == "ACCESS":
            assert first_error is None, "access continued after failed comparison"
            op, address, data, phase, bg = next(expected)
            assert (int(fields[1]), int(fields[2])) == (op == "w", address)
            if op == "w":
                assert int(fields[3], 16) == data
            else:
                pending = address, data, phase, bg
        elif fields[0] == "RETURN":
            assert pending is not None
            actual = None if "x" in fields[1] else int(fields[1], 16)
            if actual != pending[1]:
                first_error = (*pending, actual)
            pending = None
        elif fields[0] == "RESULT":
            assert int(fields[1]) == bool(first_error)
            assert fields[2] == "0"
            if first_error:
                address, data, phase, bg, actual = first_error
                assert (
                    int(fields[3]),
                    int(fields[4], 16),
                    int(fields[6]),
                    int(fields[7]),
                ) == (address, data, phase, bg)
                if actual is None:
                    assert "x" in fields[5]
                else:
                    assert int(fields[5], 16) == actual
    assert bool(first_error) == faulty
    if not faulty:
        assert next(expected, None) is None, "March sequence ended prematurely"


@pytest.mark.parametrize(
    "width,depth,latency",
    [(1, 1, 1), (3, 5, 2), (4, 4, 1), (16, 256, 1), (32, 7, 3), (64, 512, 2)],
)
def test_complete_transaction_sequence(compile_rtl, width, depth, latency):
    audit(execute(compile_rtl(width, depth, latency)), width, depth)


@pytest.mark.parametrize("fault", [1, 2, 3, 4])
def test_each_stuck_and_transition_fault(compile_rtl, fault):
    for address, bit in product(range(4), repeat=2):
        audit(execute(compile_rtl(), fault=fault, victim=address, vb=bit), 4, 4, True)


def test_each_address_alias(compile_rtl):
    for victim, aggressor in product(range(4), repeat=2):
        if victim != aggressor:
            audit(
                execute(compile_rtl(), fault=5, victim=victim, aggressor=aggressor),
                4,
                4,
                True,
            )


@pytest.mark.parametrize("same_word", [False, True])
def test_each_inversion_coupling(compile_rtl, same_word):
    for victim, aggressor, vb, ab in product(range(4), repeat=4):
        if (victim == aggressor) != same_word or (same_word and vb == ab):
            continue
        audit(
            execute(
                compile_rtl(),
                fault=7 if same_word else 6,
                victim=victim,
                aggressor=aggressor,
                vb=vb,
                ab=ab,
            ),
            4,
            4,
            True,
        )


@pytest.mark.parametrize("same_word", [False, True])
def test_each_state_coupling(compile_rtl, same_word):
    for victim, aggressor, vb, ab in product(range(4), repeat=4):
        if (victim == aggressor) != same_word or (same_word and vb == ab):
            continue
        for polarity, forced in product(range(2), repeat=2):
            audit(
                execute(
                    compile_rtl(),
                    fault=8 if same_word else 10,
                    victim=victim,
                    aggressor=aggressor,
                    vb=vb,
                    ab=ab,
                    polarity=polarity,
                    forced=forced,
                ),
                4,
                4,
                True,
            )


def test_unknown_read_is_not_a_pass(compile_rtl):
    audit(execute(compile_rtl(), fault=9), 4, 4, True)


@pytest.mark.parametrize("mode", [1, 2, 3, 4])
def test_abort_reset_and_start_while_busy(compile_rtl, mode):
    result = execute(compile_rtl(latency=3), mode=mode)
    assert result.returncode == 0, result.stdout + result.stderr
    assert "PASS protocol" in result.stdout and "RESULT 0 0" in result.stdout


@pytest.mark.parametrize("mutation", MUTATIONS)
def test_controller_mutations_are_detected(compile_rtl, mutation):
    result = execute(
        compile_rtl(mutation=mutation),
        fault=1 if mutation == "comparison" else 0,
        mode=4 if mutation == "abort" else 0,
    )
    if mutation == "abort":
        assert result.returncode != 0 and "interrupted request leaked" in result.stdout
    elif result.returncode == 0:
        with pytest.raises((AssertionError, StopIteration)):
            audit(result, 4, 4, faulty=mutation == "comparison")


@pytest.mark.parametrize("mode,fault", [(0, 0), (1, 0), (2, 0), (3, 0), (0, 1)])
def test_raw_port_ownership(tmp_path, mode, fault):
    compiler, runtime = shutil.which("iverilog"), shutil.which("vvp")
    if not compiler or not runtime:
        pytest.skip("Icarus Verilog is required for MBIST RTL verification")
    binary = tmp_path / "port.vvp"
    p = subprocess.run(
        [
            compiler,
            "-g2012",
            "-s",
            "tb_soc_sram_test_port",
            "-o",
            str(binary),
            str(RTL),
            str(RTL.with_name("soc_sram_test_port.v")),
            str(TB.with_name("tb_soc_sram_test_port.v")),
        ],
        capture_output=True,
        text=True,
        timeout=30,
    )
    assert p.returncode == 0, p.stderr
    result = execute([runtime, str(binary)], mode=mode, fault=fault)
    assert result.returncode == 0 and "PASS test-port" in result.stdout, (
        result.stdout + result.stderr
    )


@pytest.fixture(scope="module")
def synthesized_port(tmp_path_factory):
    yosys, compiler, runtime = (
        shutil.which(tool) for tool in ["yosys", "iverilog", "vvp"]
    )
    if not all([yosys, compiler, runtime]):
        pytest.skip(
            "Yosys and Icarus Verilog are required for synthesized MBIST replay"
        )
    folder = tmp_path_factory.mktemp("mbist-synthesis")
    netlist = folder / "netlist.v"
    script = (
        f"read_verilog -sv {RTL} {RTL.with_name('soc_sram_test_port.v')}; "
        "chparam -set WIDTH 16 -set DEPTH 512 soc_sram_test_port; "
        f"synth -top soc_sram_test_port -flatten; check -assert; write_verilog -noattr {netlist}"
    )
    p = subprocess.run(
        [yosys, "-p", script], capture_output=True, text=True, timeout=120
    )
    (folder / "synthesis.log").write_text(p.stdout + p.stderr)
    assert p.returncode == 0, p.stdout + p.stderr
    binary = folder / "gate.vvp"
    p = subprocess.run(
        [
            compiler,
            "-g2012",
            "-DMBIST_GATE",
            "-s",
            "tb_soc_sram_test_port",
            "-o",
            str(binary),
            str(netlist),
            str(TB.with_name("tb_soc_sram_test_port.v")),
        ],
        capture_output=True,
        text=True,
        timeout=30,
    )
    assert p.returncode == 0, p.stderr
    return [runtime, str(binary)]


@pytest.mark.parametrize("mode,fault", [(0, 0), (1, 0), (2, 0), (3, 0), (0, 1)])
def test_synthesized_port(synthesized_port, mode, fault):
    result = execute(synthesized_port, mode=mode, fault=fault)
    assert result.returncode == 0 and "PASS test-port" in result.stdout, (
        result.stdout + result.stderr
    )
