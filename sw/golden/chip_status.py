# SPDX-FileCopyrightText: 2026 Hasan Melih Akbulut
# SPDX-License-Identifier: Apache-2.0
"""Decode the dedicated read-only 192-bit MBIST status port (LSB first).

Version 1 includes Ethernet MBIST. Version 2 is the core-only release and
has no Ethernet status fields. This is not JTAG, scan or ATPG coverage.
The host requests a fresh frame and waits for ready low then high before
sampling 192 bits, packed least-significant bit first within each byte.
"""
import argparse
import json

FIELDS = {
    'busy': (0, 1), 'done': (1, 1), 'failed': (2, 1),
    'eth_done': (3, 2), 'eth_failed': (5, 2), 'fail_address': (7, 13),
    'expected': (20, 64), 'actual': (84, 64),
    'phase': (148, 3), 'background': (151, 8),
}
CORE_FIELDS = {
    'busy': (0, 1), 'done': (1, 1), 'failed': (2, 1),
    'fail_address': (3, 13), 'expected': (16, 64), 'actual': (80, 64),
    'phase': (144, 3), 'background': (147, 8),
}


def decode(frame: bytes) -> dict[str, int]:
    if len(frame) != 24:
        raise ValueError('Expected exactly 24 bytes / 192 serial bits')
    value = int.from_bytes(frame, 'little')
    magic = value >> 160
    if magic == 0x4D420001:
        fields, payload_bits = FIELDS, 159
    elif magic == 0x4D420002:
        fields, payload_bits = CORE_FIELDS, 155
    else:
        raise ValueError('Invalid MBIST frame magic or unsupported version')
    if (value >> payload_bits) & ((1 << (160 - payload_bits)) - 1):
        raise ValueError('Reserved status bits must be zero')
    return {name: (value >> lsb) & ((1 << width)-1) for name, (lsb, width) in fields.items()}


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
