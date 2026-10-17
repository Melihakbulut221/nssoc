# SPDX-FileCopyrightText: 2026 Hasan Melih Akbulut
# SPDX-License-Identifier: Apache-2.0
"""Port-only, bit-serial independent oracle; no DUT internal-state references."""

from collections import deque
import os
import random

import cocotb
from cocotb.triggers import Timer


class Stream:
    def __init__(self, dut, seed):
        self.d = dut
        self.rng = random.Random(seed)
        self.depth = int(os.environ.get("PCIE_FIFO_DEPTH", "4"))
        self.serial = [deque() for _ in range(4)]
        self.queue = deque()
        self.running = self.overflow = False
        self.captured = self.delivered = self.replacements = 0
        self.residues = set()
        self.header_codes = set()
        self.d.clk_i.value = 0

    async def cycle(self, ready=True, start=False, flush=False, reset=False):
        d = self.d
        words = [self.rng.getrandbits(32) for _ in range(4)]
        d.clk_i.value = 0
        d.rst_ni.value = int(not reset)
        d.start_i.value = int(start)
        d.flush_i.value = int(flush)
        d.block_ready_i.value = int(ready)
        d.word_i.value = sum(v << (32 * i) for i, v in enumerate(words))
        await Timer(2, unit="ns")
        enabled = self.running and not (reset or start or flush)
        valid = enabled and bool(self.queue)
        assert int(d.active_o.value) == enabled
        assert int(d.block_valid_o.value) == valid
        if valid:
            headers, payload = self.queue[0]
            assert int(d.headers_o.value) == headers, "lane/header conservation"
            assert int(d.payload_o.value) == payload, "serial payload conservation"
        was_full = len(self.queue) == self.depth
        pop = valid and ready
        if reset or start or flush:
            self.running = start and not (reset or flush)
            self.overflow = False
            self.queue.clear()
            for lane in self.serial:
                lane.clear()
        elif enabled:
            if pop:
                self.queue.popleft()
                self.delivered += 1
            for lane, word in zip(self.serial, words):
                lane.extend((word >> i) & 1 for i in range(32))
            if len(self.serial[0]) >= 130:
                if len(self.queue) == self.depth:
                    self.running = False
                    self.overflow = True
                    self.queue.clear()
                    for lane in self.serial:
                        lane.clear()
                else:
                    blocks = [sum(lane.popleft() << i for i in range(130))
                              for lane in self.serial]
                    self.queue.append((sum((v & 3) << (2 * i) for i, v in enumerate(blocks)),
                                       sum((v >> 2) << (128 * i) for i, v in enumerate(blocks))))
                    self.header_codes.update(v & 3 for v in blocks)
                    self.captured += 1
                    self.replacements += was_full and pop
            self.residues.add(len(self.serial[0]))
        d.clk_i.value = 1
        await Timer(2, unit="ns")
        assert int(d.overflow_o.value) == self.overflow, "overflow must be sticky until explicit new epoch"
        assert int(d.active_o.value) == (self.running and not (reset or start or flush))

    async def begin(self):
        await self.cycle(reset=True)
        await self.cycle(start=True)


@cocotb.test()
async def sustained_word_per_cycle(d):
    s = Stream(d, 731)
    await s.begin()
    for _ in range(8450):
        await s.cycle()
    assert s.captured == 2080 and s.delivered == 2079
    assert s.residues == set(range(0, 130, 2))
    assert s.header_codes == {0, 1, 2, 3}, "raw headers must not be silently classified"
    assert not s.overflow


@cocotb.test()
async def full_fifo_pop_and_capture_same_cycle(d):
    s = Stream(d, 888)
    await s.begin()
    for _ in range(1000):
        # Hold exactly until an incoming block would fill/replace the last slot.
        replacement_due = len(s.queue) == s.depth and len(s.serial[0]) + 32 >= 130
        await s.cycle(ready=replacement_due)
        assert not s.overflow
    assert s.replacements > 200
    for _ in range(20):
        await s.cycle()
    assert not s.overflow


@cocotb.test()
async def overflow_halts_until_explicit_restart(d):
    s = Stream(d, 919)
    await s.begin()
    for _ in range(((s.depth + 1) * 130 + 31) // 32 + 1):
        await s.cycle(ready=False)
    assert s.overflow and not s.running
    for _ in range(50):
        await s.cycle()
    await s.cycle(start=True)
    assert not s.overflow
    for _ in range(300):
        await s.cycle()
    assert s.delivered > 60


@cocotb.test()
async def reset_flush_and_new_epoch_do_not_leak_stale_blocks(d):
    s = Stream(d, 606)
    await s.begin()
    for cycle in range(2400):
        await s.cycle(ready=cycle % 7 > 2,
                      reset=cycle % 211 == 61,
                      flush=cycle % 197 == 51,
                      start=cycle % 97 == 20)
    await s.cycle(start=True, flush=True)
    assert not s.running
    for _ in range(30):
        await s.cycle()
    await s.cycle(start=True)
    for _ in range(260):
        await s.cycle()
    assert not s.overflow and s.delivered > 200
