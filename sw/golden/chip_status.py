# SPDX-FileCopyrightText: 2026 Hasan Melih Akbulut
# SPDX-License-Identifier: Apache-2.0
"""Decode the dedicated read-only 192-bit MBIST status port (LSB first).

This is not JTAG, a core scan chain or an ATPG coverage result. The host must
request a fresh frame and observe ready low then high before sampling 192 bits.
Bytes contain successive groups of eight wire bits, least significant bit first.
"""
import argparse
import json

FIELDS = {
    'busy': (0, 1), 'done': (1, 1), 'failed': (2, 1),
    'eth_done': (3, 2), 'eth_failed': (5, 2), 'fail_address': (7, 13),
    'expected': (20, 64), 'actual': (84, 64),
    'phase': (148, 3), 'background': (151, 8),
}


def decode(frame: bytes) -> dict[str, int]:
    if len(frame) != 24:
        raise ValueError('Expected exactly 24 bytes / 192 serial bits')
    value = int.from_bytes(frame, 'little')
    if value >> 160 != 0x4D420001:
        raise ValueError('Invalid MBIST frame magic or unsupported version')
    if value & (1 << 159):
        raise ValueError('Reserved status bit must be zero')
    return {name: (value >> lsb) & ((1 << width)-1) for name, (lsb, width) in FIELDS.items()}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('frame_hex', help='24 wire-order bytes as 48 hex digits')
    args = parser.parse_args()
    try:
        result = decode(bytes.fromhex(args.frame_hex))
    except ValueError as exc:
        parser.error(str(exc))
    print(json.dumps(result, indent=2))


if __name__ == '__main__':
    main()
