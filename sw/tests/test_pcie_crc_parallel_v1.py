# SPDX-FileCopyrightText: 2026 Hasan Melih Akbulut
# SPDX-License-Identifier: Apache-2.0
"""Actual literal Verilog matrices versus an independent normal serial model."""

import importlib.util
from pathlib import Path
import random
import shutil
import subprocess

ROOT = Path(__file__).resolve().parents[2]
spec = importlib.util.spec_from_file_location(
    "matrices", ROOT / "scripts/generate_pcie_crc_parallel_v1.py"
)
g = importlib.util.module_from_spec(spec)
spec.loader.exec_module(g)


def reverse(value, width):
    return int(f"{value:0{width}b}"[::-1], 2)


def normal_reference(state, data, width, bits):
    # Separate representation and shift direction from RTL matrix generation.
    r = reverse(state, width)
    poly = 0x04C11DB7 if width == 32 else 0x100B
    for bit in range(bits):
        feedback = ((r >> (width - 1)) ^ (data >> bit)) & 1
        r = (r << 1) & ((1 << width) - 1)
        if feedback:
            r ^= poly
    return reverse(r, width)


def test_literal_hdl_crc_matrices_basis_and_random(tmp_path):
    source = (
        ROOT / "hw/soc/rtl/pcie/soc_pcie_gen3_framer_rx_integrity_v1.v"
    ).read_text()
    text = g.functions()
    assert text in source
    rng = random.Random(0x330016)
    lines = ["module tb;", text, "initial begin"]
    count = 0
    for width in (16, 32):
        for bits in (16, 32):
            vectors = (
                [(0, 0)]
                + [(1 << i, 0) for i in range(width)]
                + [(0, 1 << i) for i in range(bits)]
            )
            vectors += [
                (rng.getrandbits(width), rng.getrandbits(bits)) for _ in range(100)
            ]
            for state, data in vectors:
                expected = normal_reference(state, data, width, bits)
                lines.append(
                    f"if(crc{width}_{bits}({width}'h{state:x},{bits}'h{data:x})!=={width}'h{expected:x}) $fatal(1,\"matrix {count}\");"
                )
                count += 1
    lines += [f'$display("PASS {count}"); $finish; end endmodule']
    tb = tmp_path / "tb.v"
    tb.write_text("\n".join(lines))
    exe = tmp_path / "sim.vvp"
    subprocess.run(
        [shutil.which("iverilog"), "-g2012", "-s", "tb", "-o", str(exe), str(tb)],
        check=True,
        capture_output=True,
        text=True,
    )
    r = subprocess.run(
        [shutil.which("vvp"), str(exe)], check=True, capture_output=True, text=True
    )
    assert f"PASS {count}" in r.stdout


def test_primary_dllp_and_nullified_lcrc_residues():
    def fold(data, width):
        r = (1 << width) - 1
        for byte in data:
            r = normal_reference(r, byte, width, 8)
        return r

    for wire in ("00000003504e", "00000004370c", "100000021a32"):
        assert fold(bytes.fromhex(wire), 16) == 0x556F
    import zlib

    for body in (bytes.fromhex("0abc040000011234567800001000"), bytes(150)):
        crc = zlib.crc32(body).to_bytes(4, "little")
        assert fold(body + crc, 32) == 0xDEBB20E3
        assert fold(body + bytes(x ^ 255 for x in crc), 32) == 0
