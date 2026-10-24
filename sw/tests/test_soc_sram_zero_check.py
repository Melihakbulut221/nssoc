# SPDX-FileCopyrightText: 2026 Hasan Melih Akbulut
# SPDX-License-Identifier: Apache-2.0
"""Check synchronous cross-port reads, first failure and captured-word authority."""
from pathlib import Path
import subprocess
import shutil

import pytest

ROOT = Path(__file__).resolve().parents[2]
RTL = ROOT / "hw/soc/rtl/dft/soc_sram_zero_check.v"
TB = ROOT / "hw/soc/tb/tb_soc_sram_zero_check.v"
TOOLS = ROOT / "hw/soc/tools/oss-cad-suite/bin"


@pytest.fixture(scope="module")
def compiled(tmp_path_factory):
    cache = {}
    compiler = shutil.which("iverilog") or str(TOOLS / "iverilog")
    runtime = shutil.which("vvp") or str(TOOLS / "vvp")

    def get(pipeline=1, width=16, address=3, mutation=None):
        key = (pipeline, width, address, mutation)
        if key not in cache:
            folder = tmp_path_factory.mktemp("zero-check")
            rtl, binary = folder / "rtl.v", folder / "run.vvp"
            text = RTL.read_text()
            if mutation:
                old, new = mutation
                assert old in text
                text = text.replace(old, new)
            rtl.write_text(text)
            result = subprocess.run(
                [
                    compiler, "-g2012", "-s", "tb_soc_sram_zero_check",
                    f"-Ptb_soc_sram_zero_check.PIPELINE_COMPARE={pipeline}",
                    f"-Ptb_soc_sram_zero_check.WIDTH={width}",
                    f"-Ptb_soc_sram_zero_check.ADDR_WIDTH={address}",
                    "-o", str(binary), str(rtl), str(TB),
                ],
                capture_output=True, text=True, timeout=30,
            )
            assert result.returncode == 0, result.stderr
            cache[key] = [runtime, str(binary)]
        return cache[key]

    return get


def run(command, **parameters):
    result = subprocess.run(
        command + [f"+{key}={value}" for key, value in parameters.items()],
        capture_output=True, text=True, timeout=20,
    )
    passed = result.returncode == 0 and "PASS zero-check" in result.stdout
    return passed, result.stdout + result.stderr


@pytest.mark.parametrize("pipeline", [0, 1])
@pytest.mark.parametrize("width,address", [(1, 1), (3, 2), (16, 3), (16, 11)])
def test_full_address_sequence_and_latency(compiled, pipeline, width, address):
    passed, log = run(compiled(pipeline, width, address))
    assert passed, log


@pytest.mark.parametrize("pipeline", [0, 1])
@pytest.mark.parametrize("fault", [1, 2, 3])
def test_every_address_and_fault_bit(compiled, pipeline, fault):
    for victim in range(8):
        for bit in range(16) if fault == 1 else [0]:
            passed, log = run(compiled(pipeline), fault=fault, victim=victim, bitno=bit)
            assert passed, log


@pytest.mark.parametrize("fault", [0, 1, 2, 3])
def test_captured_word_authoritative(compiled, fault):
    passed, log = run(compiled(), fault=fault, victim=5, perturb=1)
    assert passed, log


@pytest.mark.parametrize("fault", [0, 1])
def test_reset_cancels_captured_word_and_restarts(compiled, fault):
    passed, log = run(compiled(), fault=fault, victim=3, reset_capture=1, perturb=1)
    assert passed, log


@pytest.mark.parametrize("pipeline", [0, 1])
@pytest.mark.parametrize("illegal_state", [5, 6, 7, 8])
def test_illegal_state_fails_closed(compiled, pipeline, illegal_state):
    passed, log = run(compiled(pipeline), illegal_state=illegal_state)
    assert passed, log


@pytest.mark.parametrize("mutation,parameters", [
    (("if (compare_data !== {WIDTH{1'b0}})", "if (1'b0)"), dict(fault=1)),
    (("PIPELINE_COMPARE ? read_data_q : rdata_i", "rdata_i"), dict(perturb=1)),
    (("else if (&addr_o)", "else if (addr_o == 1)"), {}),
    (("addr_o <= addr_o + 1'b1", "addr_o <= addr_o + 2'd2"), {}),
])
def test_faults_in_checker_rejected(compiled, mutation, parameters):
    passed, log = run(compiled(mutation=mutation), **parameters)
    assert not passed, log
