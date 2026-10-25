#!/usr/bin/env python3
# SPDX-FileCopyrightText: 2026 Hasan Melih Akbulut
# SPDX-License-Identifier: Apache-2.0
"""Direct balanced GF(2) CRC transforms for four ordered receive DWORDs."""

import argparse
from pathlib import Path

TRANSFORMS = (
    (32, 0xEDB88320, (16, 32, 48, 64, 80, 96, 112, 128)),
    (16, 0xD008, (16, 32, 48)),
)


def rows(width, bits, polynomial):
    state = [1 << n for n in range(width)]
    for bit in range(bits):
        feedback = state[0] ^ (1 << (width + bit))
        state = state[1:] + [0]
        for n in range(width):
            if polynomial & (1 << n):
                state[n] ^= feedback
    return state


def balanced(terms):
    if len(terms) == 1:
        return terms[0]
    middle = len(terms) // 2
    return "(" + balanced(terms[:middle]) + "^" + balanced(terms[middle:]) + ")"


def functions():
    result = [
        " // BEGIN GENERATED CRC CANDIDATES -- generate_pcie_crc_candidates_v3.py"
    ]
    for width, polynomial, counts in TRANSFORMS:
        for bits in counts:
            name = f"crc{width}_{bits}"
            result += [
                f" function automatic [{width - 1}:0] {name};",
                f"   input [{width - 1}:0] state;",
                f"   input [{bits - 1}:0] data;",
                "   begin",
            ]
            for n, mask in enumerate(rows(width, bits, polynomial)):
                terms = [
                    f"state[{i}]" if i < width else f"data[{i - width}]"
                    for i in range(width + bits)
                    if mask & (1 << i)
                ]
                result.append(f"     {name}[{n}]=" + balanced(terms) + ";")
            result += ["   end", " endfunction"]
    result += [" // END GENERATED CRC CANDIDATES"]
    return "\n".join(result) + "\n"


def candidates():
    result = [
        " // BEGIN FIXED CRC CANDIDATES",
        " // Every transform is unconditional and contains no parser-state mux.",
        " wire [31:0] crc_word[0:3];",
        " wire [31:0] crc_carry[0:3],crc_seed[0:3];",
        " wire [31:0] crc_stp0[0:3],crc_stp1[0:3],crc_stp2[0:3],crc_stp3[0:3];",
        " wire [15:0] dllp_seed[0:3],dllp_finish[0:3];",
    ]
    for j in range(4):
        result.append(
            f" assign crc_word[{j}]={{current_block[{384 + j * 8}+:8],current_block[{256 + j * 8}+:8],"
            f"current_block[{128 + j * 8}+:8],current_block[{j * 8}+:8]}};"
        )
        sequence = f"{{crc_word[{j}][31:24],4'b0,crc_word[{j}][19:16]}}"
        result.append(f" assign crc_seed[{j}]=crc32_16(32'hffffffff,{sequence});")
        words = ",".join(f"crc_word[{k}]" for k in range(j, -1, -1))
        result.append(f" assign crc_carry[{j}]=crc32_{32 * (j + 1)}(lcrc,{{{words}}});")
        result.append(
            f" assign dllp_seed[{j}]=crc16_16(16'hffff,crc_word[{j}][31:16]);"
        )
        finish = (
            "crc16_32(dllp_crc,crc_word[0])"
            if j == 0
            else f"crc16_48(16'hffff,{{crc_word[{j}],crc_word[{j - 1}][31:16]}})"
        )
        result.append(f" assign dllp_finish[{j}]={finish};")
        for seed in range(4):
            if j <= seed:
                value = f"crc_seed[{seed}]"
            else:
                words = [f"crc_word[{k}]" for k in range(j, seed, -1)]
                words += [
                    f"crc_word[{seed}][31:24]",
                    "4'b0",
                    f"crc_word[{seed}][19:16]",
                ]
                value = (
                    f"crc32_{16 + 32 * (j - seed)}(32'hffffffff,{{"
                    + ",".join(words)
                    + "})"
                )
            result.append(f" assign crc_stp{seed}[{j}]={value};")
    result += [
        " // 0 denotes the arbitrary registered carry-in; 1..4 denote a STP",
        " // in this slice. A TLP run is contiguous until LOOK; only STP can",
        " // enter TLP again. DLLP lasts exactly one DWORD after SDP, so for",
        " // j>0 its seed is necessarily the preceding word (even from any",
        " // arbitrary initial parser state). CRC values never choose state.",
        " reg [2:0] crc_origin;",
        " // END FIXED CRC CANDIDATES",
    ]
    return "\n".join(result) + "\n"


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--check", type=Path)
    args = parser.parse_args()
    if args.check:
        source = args.check.read_text()
        assert functions() in source and candidates() in source, (
            "CRC candidate source drift"
        )
    else:
        print(functions() + candidates(), end="")


if __name__ == "__main__":
    main()
