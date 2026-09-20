# SPDX-FileCopyrightText: 2026 Hasan Melih Akbulut
# SPDX-License-Identifier: Apache-2.0
"""Direct bank transforms, asynchronous reset and triplicated storage upset checks."""
import random
import cocotb
from cocotb.triggers import Timer

WIDTHS = (4, 5, 8, 32, 64)
RESET = 0x0123456789abcdef


async def capture(dut, value):
    dut.clk_i.value = 0
    dut.data.value = value
    await Timer(5, unit='ns')
    dut.clk_i.value = 1
    await Timer(1, unit='ns')
    for width in WIDTHS:
        mask = (1 << width) - 1
        for lane in 'abc':
            assert int(getattr(dut, f'{lane}{width}').value) == value & mask
        assert int(getattr(dut, f'voted{width}').value) == value & mask
        assert int(getattr(dut, f'mismatch{width}').value) == 0


@cocotb.test()
async def all_storage_bits_single_upset_masked_and_recaptured(dut):
    dut.rst_ni.value = 1
    await Timer(1, unit='ns')
    dut.rst_ni.value = 0
    await Timer(1, unit='ns')
    for width in WIDTHS:
        assert int(getattr(dut, f'voted{width}').value) == RESET & ((1 << width) - 1)
    dut.rst_ni.value = 1
    rng = random.Random(41)
    for value in [0, (1 << 64) - 1, *(rng.getrandbits(64) for _ in range(12))]:
        await capture(dut, value)
    # Every storage bit, including odd-width mixed transforms. A bank alone
    # need not correct an upset; the two untouched replicas must outvote it.
    for width in WIDTHS:
        for lane in 'abc':
            for bit in range(width):
                value = rng.getrandbits(64)
                await capture(dut, value)
                bank = getattr(dut, f'bank_{lane}{width}')
                bank.bits.value = int(bank.bits.value) ^ (1 << bit)
                await Timer(1, unit='ns')
                assert int(getattr(dut, f'voted{width}').value) == value & ((1 << width) - 1)
                assert int(getattr(dut, f'mismatch{width}').value) == 1
                await capture(dut, value)
    # Negative control: two aligned faulty polarity replicas exceed TMR's
    # single-replica contract, and the voter must demonstrably become wrong.
    await capture(dut, 0)
    dut.bank_a8.bits.value = int(dut.bank_a8.bits.value) ^ 1
    dut.bank_b8.bits.value = int(dut.bank_b8.bits.value) ^ 1
    await Timer(1, unit='ns')
    assert int(dut.voted8.value) == 1
    assert int(dut.mismatch8.value) == 1
    # Asynchronous reset, without a clock, restores both polarity and MIX.
    dut.clk_i.value = 0
    dut.rst_ni.value = 0
    await Timer(1, unit='ns')
    for width in WIDTHS:
        assert int(getattr(dut, f'voted{width}').value) == RESET & ((1 << width) - 1)
        assert int(getattr(dut, f'mismatch{width}').value) == 0
