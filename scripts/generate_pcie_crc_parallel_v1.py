#!/usr/bin/env python3
# SPDX-FileCopyrightText: 2026 Hasan Melih Akbulut
# SPDX-License-Identifier: Apache-2.0
"""Generate literal GF(2) reflected CRC transforms, independent of packet logic."""

import argparse
from pathlib import Path


def rows(width, bits, polynomial):
    state = [1 << n for n in range(width)]
    for bit in range(bits):
        feedback = state[0] ^ (1 << (width + bit))
        state = state[1:] + [0]
        for n in range(width):
            if (polynomial >> n) & 1:
                state[n] ^= feedback
    return state


def functions():
    result = [" // BEGIN GENERATED CRC FUNCTIONS -- generate_pcie_crc_parallel_v1.py"]
    for width, polynomial in ((32, 0xEDB88320), (16, 0xD008)):
        for bits in (16, 32):
            name = f"crc{width}_{bits}"
            result += [
                f" function [{width - 1}:0] {name};",
                f"   input [{width - 1}:0] state;",
                f"   input [{bits - 1}:0] data;",
                "   begin",
            ]
            for n, mask in enumerate(rows(width, bits, polynomial)):
                terms = [
                    f"state[{i}]" if i < width else f"data[{i - width}]"
                    for i in range(width + bits)
                    if (mask >> i) & 1
                ]
                result.append(f"     {name}[{n}]=" + "^".join(terms) + ";")
            result += ["   end", " endfunction"]
    result += [" // END GENERATED CRC FUNCTIONS"]
    return "\n".join(result) + "\n"


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--check", type=Path)
    args = p.parse_args()
    if args.check:
        assert functions() in args.check.read_text(), (
            "Generated literal CRC matrix changed"
        )
    else:
        print(functions(), end="")


if __name__ == "__main__":
    main()
