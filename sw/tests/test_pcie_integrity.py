# SPDX-FileCopyrightText: 2026 Hasan Melih Akbulut
# SPDX-License-Identifier: Apache-2.0
"""Independent CRC algebra and actual port-suite negative controls; no link claim."""

import hashlib
import json
from pathlib import Path
import random
import shutil
import subprocess
import sys
import zlib

import pytest

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "scripts"))
import check_pcie_integrity as driver  # noqa: E402


def reverse32(value):
    return int(f"{value:032b}"[::-1], 2)


def normal_step(reflected_state, byte):
    normal = reverse32(reflected_state)
    for bit in range(8):
        feedback = ((normal >> 31) ^ ((byte >> bit) & 1)) & 1
        normal = (normal * 2) & 0xFFFFFFFF
        if feedback:
            normal ^= 0x04C11DB7
    return reverse32(normal)


def reference(data):
    state = 0xFFFFFFFF
    for byte in data:
        state = normal_step(state, byte)
    return (state ^ 0xFFFFFFFF).to_bytes(4, "little")


@pytest.mark.parametrize(
    "data,expected",
    [
        (b"123456789", "2639f4cb"),
        (b"", "00000000"),
        (bytes.fromhex("0abc400000010138970f8234503078563412"), "ad7c660b"),
        (bytes.fromhex("0000000000010138970f82345000"), "ad595ccd"),
    ],
)
def test_normal_polynomial_and_independent_zlib_match_literal_wire_vectors(
    data, expected
):
    assert reference(data).hex() == expected
    assert zlib.crc32(data).to_bytes(4, "little").hex() == expected
    state = 0xFFFFFFFF
    for byte in data + bytes.fromhex(expected):
        state = normal_step(state, byte)
    assert state == 0xDEBB20E3


def test_normal_oracle_and_zlib_cover_random_packet_and_reserved_sequence_bytes():
    rng = random.Random(0x32C1)
    for length in range(2, 103):
        data = bytes(rng.randrange(256) for _ in range(length))
        assert reference(data) == zlib.crc32(data).to_bytes(4, "little")


def native_tools():
    if not shutil.which("iverilog") or not shutil.which("vvp"):
        pytest.skip("Native Icarus required for CRC controls")


def test_actual_crc_primitive_all_byte_values_and_state_basis(tmp_path):
    native_tools()
    rng = random.Random(0x1234)
    vectors = [(state, byte) for state in (0, 0xFFFFFFFF) for byte in range(256)]
    vectors += [
        (1 << bit, byte)
        for bit in range(32)
        for byte in (0, 1, 2, 4, 8, 16, 32, 64, 128)
    ]
    vectors += [(rng.getrandbits(32), rng.randrange(256)) for _ in range(1024)]
    assertions = "\n".join(
        f"state=32'h{state:08x};data=8'h{byte:02x};#1;if(result!==32'h{normal_step(state, byte):08x})$fatal(1,\"CRC vector {i}\");"
        for i, (state, byte) in enumerate(vectors)
    )
    tb = tmp_path / "tb.v"
    tb.write_text(
        "module tb;reg[31:0]state;reg[7:0]data;wire[31:0]result;"
        "soc_pcie_crc32_byte dut(state,data,result);initial begin\n"
        + assertions
        + '\n$display("CRC_NATIVE_PASS");$finish;end endmodule\n'
    )
    exe = tmp_path / "sim"
    subprocess.run(
        [
            "iverilog",
            "-g2012",
            "-s",
            "tb",
            "-o",
            str(exe),
            str(tb),
            str(ROOT / driver.SOURCES[0]),
        ],
        check=True,
        capture_output=True,
        timeout=30,
    )
    run = subprocess.run(
        ["vvp", str(exe)], check=True, capture_output=True, text=True, timeout=30
    )
    assert run.stdout.splitlines().count("CRC_NATIVE_PASS") == 1
    assert len(vectors) == 1824


@pytest.mark.parametrize(
    "fault,filename,before,after",
    [
        ("crc_bypass", "soc_pcie_lcrc_rx.v", "crc_next==32'hdebb20e3", "1'b1"),
        (
            "payload_lane_swap",
            "soc_pcie_tlp_integrity.v",
            "word_data[8*byte_index+:8]",
            "word_data[8*(3-byte_index)+:8]",
        ),
        (
            "discard_backpressure",
            "soc_pcie_lcrc_rx.v",
            "if (tlp_ready_i) begin",
            "if (1'b1) begin",
        ),
    ],
)
def test_real_port_suite_rejects_integrity_lane_and_stall_mutations(
    tmp_path, fault, filename, before, after
):
    native_tools()
    if not (Path(sys.executable).parent / "cocotb-config").is_file():
        pytest.skip("Cocotb runtime required for functional mutation controls")
    rtl = tmp_path / "rtl"
    rtl.mkdir()
    for name in driver.SOURCES:
        shutil.copyfile(ROOT / name, rtl / Path(name).name)
    path = rtl / filename
    text = path.read_text()
    assert text.count(before) == 1
    path.write_text(text.replace(before, after))
    out = tmp_path / fault
    run = subprocess.run(
        [
            sys.executable,
            str(ROOT / "scripts/check_pcie_integrity.py"),
            "--out",
            str(out),
            "--rtl-dir",
            str(rtl),
        ],
        capture_output=True,
        text=True,
        timeout=90,
    )
    result = json.loads((out / "result.json").read_text())
    assert run.returncode != 0 and result["returncode"] != 0
    assert result["tests"]["failed"] > 0 and result["tests"]["skipped"] == 0
    assert (
        result["tests"]["passed"] + result["tests"]["failed"]
        == result["expected_tests"]
    )
    assert (
        result["xml"]["sha256"]
        == hashlib.sha256((out / "results.xml").read_bytes()).hexdigest()
    )


def test_mapped_mode_never_combines_default_rtl_sources(tmp_path):
    run = subprocess.run(
        [
            sys.executable,
            str(ROOT / "scripts/check_pcie_integrity.py"),
            "--out",
            str(tmp_path / "out"),
            "--netlist",
            "mapped.v",
            "--models",
            "models.v",
            "--rtl-dir",
            "rtl",
        ],
        capture_output=True,
        text=True,
    )
    assert (
        run.returncode == 2
        and "never mixes RTL" in run.stderr
        and not (tmp_path / "out").exists()
    )


@pytest.mark.parametrize("wrong_polynomial", [False, True])
def test_exhaustive_crc_state_byte_relation_and_negative_counterexample(
    tmp_path, wrong_polynomial
):
    yosys = shutil.which("yosys")
    if not yosys:
        pytest.skip("Native Yosys required for exhaustive CRC relation")
    source = (ROOT / driver.SOURCES[0]).read_text()
    if wrong_polynomial:
        assert source.count("32'hedb88320") == 1
        source = source.replace("32'hedb88320", "32'hedb88321")
    rtl = tmp_path / "crc.v"
    rtl.write_text(source)
    proof = ROOT / "hw/soc/formal/pcie_crc32_byte_formal.v"
    verify = "" if wrong_polynomial else "-verify"
    help_result = subprocess.run(
        [yosys, "-Q", "-T", "-p", "help chformal"],
        check=True,
        capture_output=True,
        text=True,
        timeout=15,
    )
    (tmp_path / "chformal-help.log").write_text(help_result.stdout)
    # New frontends emit $check; older Yosys already emits $assert and has no
    # -lower mode. Lowering preserves the assertion rather than removing it.
    lower = "chformal -lower; " if "-lower" in help_result.stdout else ""
    command = (
        f"read_verilog -formal {rtl} {proof}; "
        "prep -top pcie_crc32_byte_formal -flatten; "
        f"{lower}select -assert-count 1 t:$assert; "
        "select -assert-none t:$assume t:$check; "
        f"sat {verify} -prove-asserts -show-inputs "
        f"-dump_json {tmp_path}/counterexample.json "
        f"-dump_vcd {tmp_path}/counterexample.vcd"
    )
    (tmp_path / "proof.ys").write_text(command + "\n")
    result = subprocess.run(
        [yosys, "-p", command], capture_output=True, text=True, timeout=45
    )
    (tmp_path / "proof.log").write_text(result.stdout + result.stderr)
    if wrong_polynomial:
        assert result.returncode == 0 and "model found: FAIL" in result.stdout
        assert (tmp_path / "counterexample.json").stat().st_size > 0 and (
            tmp_path / "counterexample.vcd"
        ).stat().st_size > 0
    else:
        assert result.returncode == 0 and "no model found: SUCCESS" in result.stdout
    assert "Import constraint from assume" not in result.stdout


def test_current_python_cocotb_precedes_other_runtime_wrappers(tmp_path):
    fake = tmp_path / "other-runtime"
    fake.mkdir()
    (fake / "cocotb-config").write_text("#!/bin/sh\necho wrong-Python\n")
    (fake / "cocotb-config").chmod(0o755)
    env = driver.tool_environment(fake)
    assert env["PATH"].split(":")[:2] == [str(Path(sys.executable).parent), str(fake)]
    own = Path(sys.executable).parent / "cocotb-config"
    if own.is_file():
        assert Path(shutil.which("cocotb-config", path=env["PATH"])) == own
