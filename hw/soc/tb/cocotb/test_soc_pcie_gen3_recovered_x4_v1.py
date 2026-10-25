# SPDX-FileCopyrightText: 2026 Hasan Melih Akbulut
# SPDX-License-Identifier: Apache-2.0
"""Independent serialized-bit oracle, four clocks, only public DUT ports."""
from collections import deque
import random

import cocotb
from cocotb.triggers import Timer

EIEOS = (int("ff00" * 8, 16) << 2) | 1


class Link:
    def __init__(self, d):
        self.d = d
        self.periods = [3899, 4001, 3997, 4103]
        self.clocks = self.raw = self.raw_valid = 0
        self.enabled = [False] * 4
        self.paused = [False] * 4
        self.ready = 15
        self.offsets = [0, 1, 17, 31]
        self.bits = [0] * 4
        self.count = [0] * 4
        self.index = [0] * 4
        self.expected = [deque() for _ in range(4)]
        self.seen = [0] * 4
        self.held = [None] * 4
        self.error = None
        self.allow_fault = False
        self.tasks = []

    async def until(self, condition, limit=50000):
        for _ in range(limit):
            if self.error:
                raise self.error
            if condition():
                return
            await Timer(1000, unit="ps")
        raise AssertionError("Bounded four-lane scenario did not complete")

    async def start(self):
        d = self.d
        for n in ("por_ni", "reset_i", "recovered_clk_i", "common_clk_i",
                  "raw_valid_i", "raw_i", "align_control_i", "force_realign_i", "ready_i"):
            getattr(d, n).value = 0
        await Timer(1, unit="ps")
        self.tasks = [cocotb.start_soon(self.writer(k)) for k in range(4)]
        self.tasks.append(cocotb.start_soon(self.reader()))
        await Timer(50000, unit="ps")
        d.align_control_i.value = 15
        d.por_ni.value = 1
        await self.until(lambda: int(d.active_o.value))
        self.begin_words()

    def begin_words(self):
        for lane in range(4):
            self.bits[lane] = 0
            self.count[lane] = self.offsets[lane]
            self.index[lane] = self.seen[lane] = 0
            self.expected[lane].clear()
            self.held[lane] = None
        self.enabled = [True] * 4

    def next_word(self, lane):
        while self.count[lane] < 32:
            i = self.index[lane]
            if i == 0 or i % 19 == 0:
                value, code, skp, eieos, realign, nbits = EIEOS, 2, 0, 1, int(i == 0), 130
            elif i % 3 == 0:
                code = (i // 3 + lane) % 5
                symbols = [0xAA] * (4 + 4 * code) + [0xE1, lane + 0x30, i & 255, 0xA5]
                value = (int.from_bytes(bytes(symbols), "little") << 2) | 1
                skp, eieos, realign, nbits = 1, 0, 0, 66 + 32 * code
            else:
                payload = random.Random(0xABC000 + lane * 100000 + i).getrandbits(128)
                value, code, skp, eieos, realign, nbits = (payload << 2) | 2, 2, 0, 0, 0, 130
            self.expected[lane].append((value, code, skp, eieos, realign))
            self.bits[lane] |= value << self.count[lane]
            self.count[lane] += nbits
            self.index[lane] += 1
        word = self.bits[lane] & 0xFFFFFFFF
        self.bits[lane] >>= 32
        self.count[lane] -= 32
        return word

    async def writer(self, lane):
        d = self.d
        mask = 1 << lane
        await Timer(lane * 137 + 13, unit="ps")
        try:
            while True:
                self.clocks &= ~mask
                d.recovered_clk_i.value = self.clocks
                if self.paused[lane]:
                    await Timer(100, unit="ps")
                    continue
                running = bool(int(d.lane_running_o.value) & mask)
                valid = self.enabled[lane] and running
                self.raw_valid = (self.raw_valid & ~mask) | (mask if valid else 0)
                if valid:
                    self.raw = (self.raw & ~(0xFFFFFFFF << (lane * 32))) | (self.next_word(lane) << (lane * 32))
                d.raw_valid_i.value = self.raw_valid
                d.raw_i.value = self.raw
                await Timer(self.periods[lane] // 2, unit="ps")
                self.clocks |= mask
                d.recovered_clk_i.value = self.clocks
                await Timer(self.periods[lane] - self.periods[lane] // 2, unit="ps")
        except Exception as error:
            self.error = error
            raise

    async def reader(self):
        d = self.d
        await Timer(997, unit="ps")
        try:
            while True:
                d.common_clk_i.value = 0
                d.ready_i.value = self.ready
                await Timer(2000, unit="ps")
                valid = int(d.valid_o.value)
                reset = not int(d.por_ni.value) or int(d.reset_i.value)
                fault = int(d.fault_o.value)
                if reset or fault or not int(d.active_o.value):
                    assert valid == 0, "A lane escaped the common startup/fault barrier"
                    self.held = [None] * 4
                else:
                    assert self.allow_fault or not int(d.lane_fault_o.value), "Unexpected lane epoch fault"
                    for lane in range(4):
                        item = None
                        if valid & (1 << lane):
                            item = (int(d.block_o.value[194 * lane + 193 : 194 * lane]),
                                    int(d.length_code_o.value[3 * lane + 2 : 3 * lane]),
                                    int(d.skp_o.value[lane]),
                                    int(d.eieos_o.value[lane]),
                                    int(d.realign_o.value[lane]))
                        if self.held[lane] is not None:
                            assert item == self.held[lane], "Held lane record changed"
                        ready = int(d.ready_i.value) & (1 << lane)
                        self.held[lane] = item if item is not None and not ready else None
                        if item is not None and ready:
                            assert self.expected[lane], "Unsent or duplicated lane record"
                            expected = self.expected[lane].popleft()
                            assert item == expected, f"Serialized lane oracle mismatch lane={lane} record={self.seen[lane]} actual={item} expected={expected}"
                            self.seen[lane] += 1
                d.common_clk_i.value = 1
                await Timer(2000, unit="ps")
        except Exception as error:
            self.error = error
            raise

    async def reset(self, por=False):
        self.enabled = [False] * 4
        self.d.force_realign_i.value = 0
        if por:
            self.d.por_ni.value = 0
        else:
            self.d.reset_i.value = 1
        await Timer(50000, unit="ps")
        assert int(self.d.valid_o.value) == int(self.d.fault_o.value) == 0
        self.ready = 15
        self.allow_fault = False
        self.d.por_ni.value = 1
        self.d.reset_i.value = 0
        await self.until(lambda: int(self.d.active_o.value))
        self.begin_words()

    async def close(self):
        for task in self.tasks:
            task.cancel()
        await Timer(1, unit="ps")
        if self.error:
            raise self.error


@cocotb.test()
async def all_bit_phases_variable_skp_and_independent_clocks(d):
    link = Link(d)
    try:
        await link.start()
        for phase in range(8):
            link.offsets = [phase * 4 + k for k in range(4)]
            await link.reset(por=bool(phase & 1))
            await link.until(lambda: min(link.seen) >= 140)
            assert int(d.lane_aligned_o.value) == 15
            assert int(d.fault_o.value) == 0
    finally:
        await link.close()


@cocotb.test()
async def independent_lane_stalls_hold_all_record_bits(d):
    link = Link(d)
    try:
        await link.start()
        await link.until(lambda: min(link.seen) >= 30)
        for lane in range(4):
            before = list(link.seen)
            link.ready = 15 ^ (1 << lane)
            await Timer(180000, unit="ps")
            assert link.seen[lane] <= before[lane] + 1
            assert all(link.seen[k] > before[k] for k in range(4) if k != lane)
            link.ready = 15
            await link.until(lambda: link.seen[lane] > before[lane] + 15)
        assert not int(d.fault_o.value)
    finally:
        await link.close()


@cocotb.test()
async def one_lane_loss_aborts_all_and_coordinated_reset_restarts(d):
    link = Link(d)
    try:
        await link.start()
        await link.until(lambda: min(link.seen) >= 35)
        link.allow_fault = True
        link.enabled[2] = False
        await link.until(lambda: int(d.fault_o.value), limit=3000)
        assert int(d.lane_fault_o.value) & 4
        for _ in range(40):
            await Timer(4000, unit="ps")
            assert int(d.valid_o.value) == int(d.active_o.value) == 0
            assert int(d.fault_o.value)
        await link.reset()
        await link.until(lambda: min(link.seen) >= 45)
    finally:
        await link.close()


@cocotb.test()
async def overflowing_one_unthrottleable_lane_aborts_epoch(d):
    link = Link(d)
    try:
        await link.start()
        await link.until(lambda: min(link.seen) >= 20)
        link.allow_fault = True
        link.ready = 13
        await link.until(lambda: int(d.fault_o.value), limit=3000)
        assert int(d.lane_fault_o.value) & 2
        assert int(d.valid_o.value) == 0
        await link.reset(por=True)
        await link.until(lambda: min(link.seen) >= 25)
    finally:
        await link.close()


@cocotb.test()
async def explicit_realign_fault_is_not_silent_lane_reordering(d):
    link = Link(d)
    try:
        await link.start()
        await link.until(lambda: min(link.seen) >= 25)
        link.allow_fault = True
        d.force_realign_i.value = 8
        await link.until(lambda: int(d.fault_o.value), limit=3000)
        assert int(d.lane_fault_o.value) & 8
        assert int(d.valid_o.value) == 0
        await link.reset()
        await link.until(lambda: min(link.seen) >= 25)
    finally:
        await link.close()


@cocotb.test()
async def stopped_recovered_clock_holds_common_startup(d):
    link = Link(d)
    try:
        await link.start()
        link.enabled = [False] * 4
        d.reset_i.value = 1
        await Timer(50000, unit="ps")
        link.paused[3] = True
        d.reset_i.value = 0
        for _ in range(70):
            await Timer(4000, unit="ps")
            assert int(d.active_o.value) == 0, "Stopped fourth lane escaped all-lane startup barrier"
            assert int(d.valid_o.value) == 0
        link.paused[3] = False
        await link.until(lambda: int(d.active_o.value))
        link.begin_words()
        await link.until(lambda: min(link.seen) >= 50)
    finally:
        await link.close()


@cocotb.test()
async def reset_discards_all_four_held_records(d):
    link = Link(d)
    try:
        await link.start()
        await link.until(lambda: min(link.seen) >= 25)
        link.ready = 0
        await link.until(lambda: all(x is not None for x in link.held))
        await link.reset()
        await link.until(lambda: min(link.seen) >= 50)
    finally:
        await link.close()
