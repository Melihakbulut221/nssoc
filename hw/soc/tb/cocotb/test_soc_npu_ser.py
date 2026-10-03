# SPDX-FileCopyrightText: 2026 Hasan Melih Akbulut
# SPDX-License-Identifier: Apache-2.0
"""Direct serial-master waveform, atomic capture, reset and bound-expiry tests."""
import os
import random

import cocotb
from cocotb.triggers import Timer

HALF = int(os.environ.get('TEST_SER_HALF', '2'))


async def tick(dut):
    dut.clk_i.value = 0
    await Timer(5, unit='ns')
    dut.clk_i.value = 1
    await Timer(5, unit='ns')


async def reset(dut):
    dut.start_i.value = 0
    dut.we_i.value = 0
    dut.addr_i.value = 0
    dut.wdata_i.value = 0
    dut.ser_miso_i.value = 0
    dut.rst_ni.value = 0
    await tick(dut)
    dut.rst_ni.value = 1
    await tick(dut)
    assert int(dut.busy_o.value) == int(dut.done_o.value) == 0
    assert int(dut.ser_cs_n_o.value) == 1 and int(dut.ser_sck_o.value) == 0


async def frame(dut, write, address, data, response):
    dut.we_i.value = write
    dut.addr_i.value = address
    dut.wdata_i.value = data
    dut.start_i.value = 1
    await tick(dut)
    assert int(dut.busy_o.value) == 1 and int(dut.ser_cs_n_o.value) == 0
    dut.start_i.value = 0
    # The command-byte MISO samples must be discarded; only the final 32
    # samples form the read response, on both reads and writes.
    miso_bits = [int(bit) for bit in f'{(0xa5 << 32) | response:040b}']
    captured, rises, falls = [], [], []
    previous_sck, previous_cs, index, deselected = 0, 0, 0, None
    for cycle in range(1, 87 * HALF + 3):
        dut.ser_miso_i.value = miso_bits[min(index, 39)]
        # Start while busy is ignored; request fields may change immediately.
        dut.start_i.value = int(cycle == 4 * HALF)
        dut.we_i.value = not write
        dut.addr_i.value = address ^ 127
        dut.wdata_i.value = data ^ 0xffffffff
        await tick(dut)
        sck, cs = int(dut.ser_sck_o.value), int(dut.ser_cs_n_o.value)
        if sck and not previous_sck:
            assert cs == 0
            rises.append(cycle)
            captured.append(int(dut.ser_mosi_o.value))
        if previous_sck and not sck:
            falls.append(cycle)
            index += 1
        if cs and not previous_cs:
            deselected = cycle
        assert int(dut.timeout_o.value) == 0
        previous_sck, previous_cs = sck, cs
        if int(dut.done_o.value):
            assert not int(dut.busy_o.value)
            assert len(captured) == len(rises) == len(falls) == 40
            assert int(''.join(map(str, captured)), 2) == (write << 39) | (address << 32) | data
            assert int(dut.rdata_o.value) == response
            assert rises[0] >= 2 * HALF
            assert all(b - a == 2 * HALF for a, b in zip(rises, rises[1:]))
            assert all(b - a == HALF for a, b in zip(rises, falls))
            assert deselected is not None and cycle - deselected >= 2 * HALF
            await tick(dut)
            assert int(dut.done_o.value) == 0
            return
    raise AssertionError('serial frame did not finish within its bound')


@cocotb.test()
async def waveform_and_request_capture(dut):
    await reset(dut)
    rng = random.Random(103)
    for write in (0, 1):
        for address in (0, 1, 127):
            await frame(dut, write, address, rng.getrandbits(32), rng.getrandbits(32))


@cocotb.test()
async def reset_aborts_then_next_frame_completes(dut):
    await reset(dut)
    dut.start_i.value = 1
    await tick(dut)
    dut.start_i.value = 0
    for _ in range(9 * HALF): await tick(dut)
    assert int(dut.busy_o.value)
    dut.rst_ni.value = 0
    await Timer(1, unit='ns')
    assert int(dut.ser_cs_n_o.value) == 1
    assert int(dut.ser_sck_o.value) == int(dut.busy_o.value) == int(dut.done_o.value) == 0
    await tick(dut)
    dut.rst_ni.value = 1
    await tick(dut)
    await frame(dut, 0, 25, 0, 0xa5a51234)


@cocotb.test()
async def guard_upset_produces_explicit_timeout_and_recovers(dut):
    await reset(dut)
    dut.start_i.value = 1
    await tick(dut)
    dut.start_i.value = 0
    # Directed upset beyond, rather than exactly at, the bound verifies >=.
    # This changes only the guard storage, not clocks or downstream memories.
    dut.guard.value = (1 << len(dut.guard)) - 1
    await tick(dut)
    assert int(dut.done_o.value) == int(dut.timeout_o.value) == 1
    assert int(dut.busy_o.value) == int(dut.rdata_o.value) == 0
    assert int(dut.ser_cs_n_o.value) == 1 and int(dut.ser_sck_o.value) == 0
    await tick(dut)
    assert int(dut.done_o.value) == int(dut.timeout_o.value) == 0
    await frame(dut, 1, 127, 0x12345678, 0xabcdef01)
