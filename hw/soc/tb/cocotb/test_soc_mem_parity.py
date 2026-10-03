# SPDX-FileCopyrightText: 2026 Hasan Melih Akbulut
# SPDX-License-Identifier: Apache-2.0
"""Same bus stimuli, separate RTL array and untouched IHP SRAM models.

RAM contents are established only by accepted full-word writes. Initial values
and data on write responses are deliberately unspecified by the shared bus
contract. Read data, grants, response latency, errors and ECC pulses must agree
and must independently match a Python byte-enable scoreboard. No memory force,
deposit, model patch or hierarchical preload is used.
"""
import os
import random
from collections import deque

import cocotb
from cocotb.triggers import Timer


def value(signal):
    bits = str(signal.value).lower()
    assert 'x' not in bits and 'z' not in bits, f'{signal._path} is {bits}'
    return int(signal.value)


class Pair:
    def __init__(self, dut):
        self.d = dut
        self.words = int(os.environ['PARITY_WORDS'])
        self.rdreg = int(os.environ['PARITY_RDREG'])
        self.expected = [None] * self.words
        self.pending = deque([None] * self.rdreg)
        self.reads = self.writes = self.cycles = 0

    async def cycle(self, req=0, addr=0, we=0, be=15, data=0, reset=False):
        d = self.d
        d.clk_i.value = 0
        d.rst_ni.value = not reset
        d.req_i.value = req
        d.addr_i.value = addr * 4
        d.we_i.value = we
        d.be_i.value = be
        d.wdata_i.value = data
        await Timer(5, unit='ns')
        assert value(d.a_gnt) == value(d.b_gnt) == req
        if reset:
            self.pending = deque([None] * self.rdreg)
            response = None
        else:
            event = None
            if req:
                if we:
                    old = self.expected[addr]
                    assert old is not None or be == 15, 'initialize full word first'
                    mask = sum(255 << (lane * 8) for lane in range(4) if be & (1 << lane))
                    self.expected[addr] = ((old or 0) & ~mask) | (data & mask)
                    self.writes += 1
                else:
                    assert self.expected[addr] is not None
                    self.reads += 1
                event = (we, self.expected[addr])
            self.pending.append(event)
            response = self.pending.popleft()
        d.clk_i.value = 1
        await Timer(4, unit='ns')
        assert value(d.a_valid) == value(d.b_valid) == int(response is not None)
        assert value(d.a_err) == value(d.b_err) == 0
        for a, b in ((d.a_sec, d.b_sec), (d.a_ded, d.b_ded), (d.a_rd, d.b_rd)):
            assert value(a) == value(b), f'ECC/report mismatch {a._path}'
        assert value(d.a_sec) == value(d.b_sec) == 0
        assert value(d.a_ded) == value(d.b_ded) == 0
        if response is not None and not response[0]:
            assert value(d.a_data) == value(d.b_data) == response[1]
        await Timer(1, unit='ns')
        self.cycles += 1


@cocotb.test()
async def ram_bus_parity(dut):
    p = Pair(dut)
    await p.cycle(reset=True)
    await p.cycle(reset=True)
    # Every row, bank and bit lane receives a deterministic nonzero pattern.
    for addr in range(p.words):
        await p.cycle(1, addr, 1, 15, (addr * 0x9e3779b9 ^ 0xa5963c5a) & 0xffffffff)
    for addr in range(p.words):
        await p.cycle(1, addr)
    # Include each byte-enable and bank boundary explicitly, then sustained
    # mixed pipelined traffic under three fixed independent seeds.
    for be in range(16):
        for addr in (0, 1, 2047, 2048, p.words - 2, p.words - 1):
            await p.cycle(1, addr, 1, be, 0xdeadbeef ^ be)
            await p.cycle(1, addr)
    for seed in (7, 29, 103):
        rng = random.Random(seed)
        for _ in range(1500):
            await p.cycle(rng.randrange(4) != 0, rng.randrange(p.words),
                          rng.randrange(2), rng.randrange(16), rng.getrandbits(32))
    for _ in range(3):
        await p.cycle()
    # A reset cancels a pending response but retains established SRAM data.
    await p.cycle(1, 0)
    await p.cycle(reset=True)
    await p.cycle()
    for addr in (0, 2047, 2048, p.words - 1):
        await p.cycle(1, addr)
    dut.scrub_en_i.value = 1
    for n in range(p.words * 10):
        # Exercise background scrubbing while foreground requests contend.
        await p.cycle(n % 5 == 0, n % p.words)
    dut.scrub_en_i.value = 0
    for _ in range(4):
        await p.cycle()
    dut._log.info('RAM PARITY PASS cycles=%d reads=%d writes=%d',
                  p.cycles, p.reads, p.writes)
