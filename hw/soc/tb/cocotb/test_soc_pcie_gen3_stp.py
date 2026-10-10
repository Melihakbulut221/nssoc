# SPDX-FileCopyrightText: 2026 Hasan Melih Akbulut
# SPDX-License-Identifier: Apache-2.0
import cocotb
from cocotb.triggers import Timer
from pcie_gen3_framer_support import stp


@cocotb.test()
async def every_crc_length_and_sequence_field(d):
    # Literal independently polynomial-derived anchors and complete 11-bit domain.
    assert stp(6, 0x123) == bytes.fromhex("6f 80 21 23")
    for length in range(2048):
        for sequence in (0, 0xFFF, (length * 713) & 0xFFF):
            d.length_dw_i.value = length
            d.sequence_i.value = sequence
            await Timer(2, unit="ns")
            assert int(d.token_o.value) == int.from_bytes(
                stp(length, sequence), "little"
            )
