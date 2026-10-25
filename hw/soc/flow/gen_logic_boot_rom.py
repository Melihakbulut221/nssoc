#!/usr/bin/env python3
# SPDX-FileCopyrightText: 2026 Hasan Melih Akbulut
# SPDX-License-Identifier: Apache-2.0
"""Generate immutable, SECDED-coded boot ROM gates from a compiled loader.

The fixed map has 2048 words and its reset vector starts at word 32.
The binary is little-endian and occupies the remainder of that aperture.
This generates case literals, never readmemh or initialized storage.
"""
import argparse
import hashlib
import json
from pathlib import Path
import struct
import sys

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / 'sw'))
from golden.secded import encode

TEMPLATE = ROOT / 'hw/soc/rtl/soc_logic_boot_rom.v.in'
WORDS = 2048
FIRST_WORD = 32


def contents(raw):
    if not raw or len(raw) > (WORDS - FIRST_WORD) * 4:
        raise ValueError('Loader must contain 1..8064 bytes for the fixed ROM aperture')
    padded = raw + bytes((-len(raw)) % 4)
    words = [0] * FIRST_WORD + [x[0] for x in struct.iter_unpack('<I', padded)]
    words += [0] * (WORDS - len(words))
    result = []
    for word in words:
        check = encode(word) >> 64
        if check >= 128:
            raise ValueError('Golden codec no longer supports the 39-bit shortening')
        result.append(word | (check << 32))
    return result


def generate(image, output):
    image, output = Path(image), Path(output)
    raw = image.read_bytes()
    codes = contents(raw)
    template = TEMPLATE.read_text()
    if template.count('@ROM_CASE@') != 1:
        raise ValueError('Unsupported ROM template')
    cases = '\n'.join(f"   11'd{i}: lookup=39'h{code:010x};"
                      for i, code in enumerate(codes) if code)
    rtl = template.replace('@ROM_CASE@', cases)
    digest = lambda data: hashlib.sha256(data).hexdigest()
    manifest = {
        'format': 1, 'module': 'soc_logic_boot_rom',
        'image_bytes': len(raw), 'image_sha256': digest(raw),
        'words': WORDS, 'first_image_word': FIRST_WORD, 'codeword_bits': 39,
        'template_sha256': digest(template.encode()),
        'golden_codec_sha256': digest((ROOT / 'sw/golden/secded.py').read_bytes()),
        'rtl_sha256': digest(rtl.encode()),
        'scope': 'Fixed standard-cell ROM contents. No SRAM preload or writable code storage. Physical and fault qualification remain separate.'}
    outputs = {'soc_logic_boot_rom.v': rtl,
               'manifest.json': json.dumps(manifest, indent=2) + '\n'}
    # Repeat builds are allowed only when they reproduce the same image.
    # Never quietly replace the firmware identity in an existing build.
    for name, text in outputs.items():
        path = output / name
        if path.exists() and path.read_text() != text:
            raise ValueError(f'Existing ROM output differs: {path}; use a new output directory')
    output.mkdir(parents=True, exist_ok=True)
    for name, text in outputs.items():
        path = output / name
        if not path.exists():
            with path.open('x') as stream:
                stream.write(text)
    return manifest


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--image', required=True, type=Path)
    parser.add_argument('--output', required=True, type=Path)
    args = parser.parse_args()
    try:
        result = generate(args.image, args.output)
    except (ValueError, OSError) as error:
        parser.exit(2, str(error) + '\n')
    print(json.dumps(result, indent=2))


if __name__ == '__main__':
    main()
