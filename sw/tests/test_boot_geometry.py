# SPDX-FileCopyrightText: 2026 Hasan Melih Akbulut
# SPDX-License-Identifier: Apache-2.0
"""Exercise the exact C predicate used by the ROM, including corrupt headers."""

import ctypes
import importlib.util
from pathlib import Path
import random
import shutil
import struct
import subprocess

import pytest

ROOT = Path(__file__).resolve().parents[2]


@pytest.fixture(scope="module")
def geometry(tmp_path_factory):
    cc = shutil.which("cc")
    if cc is None:
        pytest.skip("host C compiler required to test the ROM's C predicate")
    out = tmp_path_factory.mktemp("boot-geometry")
    source = out / "wrapper.c"
    source.write_text('#include "boot_geometry.h"\n'
                      'int check(uint32_t l,uint32_t n,uint32_t e,uint32_t b,'
                      'uint32_t p,uint32_t s,uint32_t h) {\n'
                      'return boot_geometry_valid(l,n,e,b,p,s,h); }\n')
    lib = out / "geometry.so"
    subprocess.run([cc, "-std=c11", "-Wall", "-Wextra", "-Werror", "-O2",
                    "-shared", "-fPIC", "-I", str(ROOT / "hw/soc/tb/sw"),
                    str(source), "-o", str(lib)], check=True, capture_output=True)
    function = ctypes.CDLL(str(lib)).check
    function.argtypes = [ctypes.c_uint32] * 7
    function.restype = ctypes.c_int
    return function


@pytest.mark.parametrize("load,size,entry,accepted", [
    (0, 4, 0, True), (0, 4, 2, True),  # RV32C halfword alignment
    (0, 4, 1, False), (0, 4, 3, False),
    (0, 4, 4, False), (0, 0, 0, False),
    (0, 6, 0, False), (2, 4, 2, False),
    (0, 0x3FE0, 0, True), (0, 0x3FE4, 0, False),
    (0, 0x4000, 0, False),
    (0x7EFC, 4, 0x7EFC, True), (0x7F00, 4, 0x7F00, False),
    (0xFFFFFFFC, 8, 0xFFFFFFFC, False),
])
def test_header_boundaries(geometry, load, size, entry, accepted):
    assert bool(geometry(load, size, entry, 0, 0x7F00, 0x4000, 32)) == accepted


def test_nonzero_ram_base_and_invalid_limits(geometry):
    assert geometry(0x1000, 4, 0x1002, 0x1000, 0x2000, 1024, 32)
    assert not geometry(0, 4, 0, 0x1000, 0x2000, 1024, 32)
    assert not geometry(0, 4, 0, 0x2000, 0x1000, 1024, 32)
    assert not geometry(0, 4, 0, 0, 0x2000, 16, 32)
    assert not geometry(0, 0x10000, 0, 0, 0x20000, 0x20000, 32)


def test_mathematical_range_oracle(geometry):
    rng = random.Random(0xB007)
    accepted = 0
    for i in range(10000):
        if i % 2:
            base = rng.randrange(0, 0xFFFFFF00) & ~3
            load = base + rng.randrange(0, 64) * 4
            size = rng.randrange(0, 65) * 4
            entry = load + rng.randrange(0, 130) * 2
            priv = min(0xFFFFFFFF, base + rng.randrange(0, 600))
            slot, header = rng.randrange(0, 600), 32
        else:
            load, size, entry, base, priv, slot, header = [rng.getrandbits(32) for _ in range(7)]
        expected = (base <= load < load + size <= priv
                    and 0 < size <= 65535 and header + size <= slot
                    and load % 4 == 0 and size % 4 == 0
                    and load <= entry < load + size and entry % 2 == 0)
        actual = bool(geometry(load, size, entry, base, priv, slot, header))
        assert actual == expected, (load, size, entry, base, priv, slot, header)
        accepted += actual
    assert accepted > 100  # ensure the random campaign is not all rejections


@pytest.mark.parametrize("mode", ["entry", "length"])
def test_geometry_counterfactual_keeps_a_valid_header_checksum(geometry, mode):
    spec = importlib.util.spec_from_file_location("boot_image", ROOT / "hw/soc/flow/gen_boot_image.py")
    generator = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(generator)
    blob = generator.build_slot(bytes(64), 0, 0, 1, mode)
    magic, load, size, entry, *rest = struct.unpack("<8I", blob[:32])
    assert magic == generator.MAGIC
    assert sum((magic, load, size, entry, *rest)) % 2**32 == 0
    assert not geometry(load, size, entry, 0, 0x7F00, 0x4000, 32)
