# SPDX-FileCopyrightText: 2026 Hasan Melih Akbulut
# SPDX-License-Identifier: Apache-2.0
"""Boot contents must survive mapping as immutable, correctly encoded words."""
import hashlib
import importlib.util
import json
from pathlib import Path
import random
import shutil
import struct
import subprocess

import pytest

ROOT = Path(__file__).resolve().parents[2]
spec = importlib.util.spec_from_file_location('logic_rom', ROOT / 'hw/soc/flow/gen_logic_boot_rom.py')
rom = importlib.util.module_from_spec(spec)
spec.loader.exec_module(rom)


@pytest.mark.parametrize('size', [0, 8065, 8192])
def test_invalid_image_aperture(size):
    with pytest.raises(ValueError, match='1..8064 bytes'):
        rom.contents(bytes(size))


@pytest.mark.parametrize('raw,value', [(b'\x81', 0x81), (b'\x81\x23\x45', 0x452381),
                                      (b'\x81\x23\x45\x67', 0x67452381)])
def test_byte_order_reset_offset_and_tail(raw, value):
    codes = rom.contents(raw)
    assert len(codes) == 2048
    assert codes[:32] == [0] * 32
    assert codes[32] & 0xffffffff == value
    assert codes[33:] == [0] * 2015


def test_manifest_reproducible_and_changed_image_rejected(tmp_path):
    image = tmp_path / 'loader.bin'
    image.write_bytes(b'\x13\0\0\0')
    output = tmp_path / 'rom output'
    manifest = rom.generate(image, output)
    assert manifest == rom.generate(image, output)
    assert manifest == json.loads((output / 'manifest.json').read_text())
    rtl = (output / 'soc_logic_boot_rom.v').read_bytes()
    assert hashlib.sha256(rtl).hexdigest() == manifest['rtl_sha256']
    assert b'readmemh(' not in rtl
    image.write_bytes(b'\x73\0\0\0')
    with pytest.raises(ValueError, match='Existing ROM output differs'):
        rom.generate(image, output)
    assert (output / 'soc_logic_boot_rom.v').read_bytes() == rtl


@pytest.mark.parametrize('corrupt', [False, True])
@pytest.mark.parametrize('rdreg', [0, 1])
def test_all_addresses_against_frozen_encoder_and_corruption_control(tmp_path, corrupt, rdreg):
    compiler, simulator = shutil.which('iverilog'), shutil.which('vvp')
    if not compiler or not simulator:
        pytest.skip('Icarus compiler/runtime required for actual ROM RTL verification')
    rng = random.Random(392048)
    words = [rng.getrandbits(32) for _ in range(2016)]
    raw = b''.join(struct.pack('<I', w) for w in words)
    image = tmp_path / 'loader.bin'
    image.write_bytes(raw)
    generated = tmp_path / 'rom'
    rom.generate(image, generated)
    expected = tmp_path / 'expected.hex'
    expected.write_text(''.join(f'{w:08x}\n' for w in [0] * 32 + words))
    source = generated / 'soc_logic_boot_rom.v'
    if corrupt:
        code = rom.contents(raw)[32]
        text = source.read_text()
        literal = f"39'h{code:010x}"
        assert text.count(literal) == 1
        source.write_text(text.replace(literal, f"39'h{code ^ 1:010x}"))
    executable = tmp_path / 'rom.vvp'
    subprocess.run([compiler, '-g2012', '-s', 'tb_logic_rom', f'-Ptb_logic_rom.RDREG={rdreg}', '-o', str(executable),
                    f'-DROM_EXPECTED_HEX="{expected}"',
                    str(ROOT / 'hw/soc/tb/tb_soc_logic_boot_rom.v'), str(source),
                    str(ROOT / 'hw/soc/rtl/soc_mem_ecc.v'),
                    str(ROOT / 'hw/rtl/secded_enc.v'), str(ROOT / 'hw/rtl/secded_dec.v')],
                   check=True, capture_output=True, text=True, timeout=60)
    result = subprocess.run([simulator, str(executable)], capture_output=True, text=True, timeout=60)
    if corrupt:
        assert result.returncode != 0
        assert 'ROM codeword mismatch 32' in result.stdout
    else:
        assert result.returncode == 0, result.stdout + result.stderr
        assert 'LOGIC_ROM PASS reads=4113 rejected_writes=17 words=2048' in result.stdout
