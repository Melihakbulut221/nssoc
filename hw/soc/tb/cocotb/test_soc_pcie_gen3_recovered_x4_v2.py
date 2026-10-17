# SPDX-FileCopyrightText: 2026 Hasan Melih Akbulut
# SPDX-License-Identifier: Apache-2.0
"""Four independently serialized raw lanes; scoreboards see only public ports."""
from collections import deque
import random

import cocotb
from cocotb.triggers import Timer

EIEOS = (int("ff00" * 8, 16) << 2) | 1
SDS = (int.from_bytes(bytes([0xE1] + [0x55] * 15), "little") << 2) | 1


class Link:
    def __init__(self, d):
        self.d = d
        self.periods = [3899, 4001, 3997, 4103]
        self.clocks = self.raw = self.raw_valid = 0
        self.enabled = [False] * 4
        self.paused = [False] * 4
        self.offsets = [0, 1, 17, 31]
        self.bits = [0] * 4
        self.count = [0] * 4
        self.index = [0] * 4
        self.expected = [deque() for _ in range(4)]
        self.skp_expected = [deque() for _ in range(4)]
        self.seen = self.starts = 0
        self.skp_seen = [0] * 4
        self.held = None
        self.skp_held = [None] * 4
        self.error = None
        self.allow_fault = False
        self.data_ready = 1
        self.skp_ready = 15
        self.tasks = []
        self.bad_first_lane = None

    async def until(self, condition, limit=50000):
        for _ in range(limit):
            if self.error:
                raise self.error
            if condition():
                return
            await Timer(1000, unit="ps")
        raise AssertionError("Bounded raw x4 deskew scenario did not complete")

    async def start(self, auto_arm=True):
        d = self.d
        for n in ("por_ni", "reset_i", "recovered_clk_i", "common_clk_i", "arm_i",
                  "raw_valid_i", "raw_i", "align_control_i", "force_realign_i", "data_ready_i", "skp_ready_i"):
            getattr(d, n).value = 0
        await Timer(1, unit="ps")
        self.tasks = [cocotb.start_soon(self.writer(k)) for k in range(4)]
        self.tasks.append(cocotb.start_soon(self.reader()))
        await Timer(50000, unit="ps")
        d.align_control_i.value = 15
        d.por_ni.value = 1
        if auto_arm:
            await self.arm()

    async def arm(self):
        await self.until(lambda: int(self.d.lanes_ready_o.value))
        # Exactly one common rising edge; readers drive the clock independently.
        await self.until(lambda: not int(self.d.common_clk_i.value))
        self.d.arm_i.value = 1
        await self.until(lambda: int(self.d.common_clk_i.value))
        await Timer(1, unit="ps")
        self.d.arm_i.value = 0
        self.begin_words()

    def begin_words(self):
        self.seen = self.starts = 0
        self.held = None
        for lane in range(4):
            self.bits[lane] = 0
            self.count[lane] = self.offsets[lane]
            self.index[lane] = self.skp_seen[lane] = 0
            self.expected[lane].clear()
            self.skp_expected[lane].clear()
            self.skp_held[lane] = None
        self.enabled = [True] * 4

    def next_word(self, lane):
        while self.count[lane] < 32:
            i = self.index[lane]
            if i <= lane:
                value, nbits = EIEOS, 130
            elif i == lane + 1:
                value, nbits = SDS, 130
            else:
                group, phase = divmod(i - lane - 2, 3)
                if phase == 0 and not (group == 0 and lane == self.bad_first_lane):
                    payload = random.Random(0xACD000 + lane * 100000 + group).getrandbits(128)
                    if group % 13 == 4:
                        payload = EIEOS >> 2  # legal DATA never realigns after SDS
                    value, nbits = (payload << 2) | 2, 130
                    self.expected[lane].append(payload)
                else:
                    code = ((group if phase == 1 else group // 5) + lane) % 5
                    symbols = [0xAA] * (4 + 4 * code) + [0xE1, 0xAA, 0xE1, group & 255]
                    value = (int.from_bytes(bytes(symbols), "little") << 2) | 1
                    nbits = 66 + 32 * code
                    self.skp_expected[lane].append((value, code))
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
                d.data_ready_i.value = self.data_ready
                d.skp_ready_i.value = self.skp_ready
                await Timer(2000, unit="ps")
                valid = int(d.data_valid_o.value)
                skp_valid = int(d.skp_valid_o.value)
                reset = not int(d.por_ni.value) or int(d.reset_i.value)
                fault = int(d.fault_o.value)
                if not reset and not self.allow_fault:
                    assert not fault, "Unexpected raw x4 epoch fault"
                if reset or fault or not int(d.active_o.value):
                    assert valid == skp_valid == 0, "Inactive epoch exposed DATA or SKP"
                    self.held = None
                    self.skp_held = [None] * 4
                else:
                    if int(d.stream_start_o.value):
                        self.starts += 1
                        assert self.starts == 1 and not valid, "SDS start not separate from DATA"
                    item = int(d.data_o.value) if valid else None
                    if self.held is not None:
                        assert item == self.held, "Held DATA quartet changed"
                    self.held = item if valid and not int(d.data_ready_i.value) else None
                    if valid and int(d.data_ready_i.value):
                        assert self.starts == 1 and all(self.expected), "DATA before complete SDS cohort or invented record"
                        expected = sum(self.expected[l].popleft() << (128*l) for l in range(4))
                        assert item == expected, "Raw serialized DATA ordinal/lane mismatch"
                        self.seen += 1
                    for lane in range(4):
                        skp_item = None
                        if skp_valid & (1 << lane):
                            skp_item = (int(d.skp_block_o.value[194*lane+193:194*lane]), int(d.skp_length_code_o.value[3*lane+2:3*lane]))
                        if self.skp_held[lane] is not None:
                            assert skp_item == self.skp_held[lane], "Held SKP record changed"
                        ready = int(d.skp_ready_i.value) & (1 << lane)
                        self.skp_held[lane] = skp_item if skp_item is not None and not ready else None
                        if skp_item is not None and ready:
                            assert self.skp_expected[lane], "Invented SKP event"
                            assert skp_item == self.skp_expected[lane].popleft(), "Raw serialized SKP bits/length mismatch"
                            self.skp_seen[lane] += 1
                d.common_clk_i.value = 1
                await Timer(2000, unit="ps")
        except Exception as error:
            self.error = error
            raise

    async def reset(self, por=False):
        self.enabled = [False] * 4
        self.d.force_realign_i.value = 0
        self.d.arm_i.value = 0
        if por:
            self.d.por_ni.value = 0
        else:
            self.d.reset_i.value = 1
        await Timer(50000, unit="ps")
        assert int(self.d.data_valid_o.value) == int(self.d.skp_valid_o.value) == int(self.d.fault_o.value) == 0
        self.data_ready, self.skp_ready = 1, 15
        self.allow_fault = False
        self.d.por_ni.value = 1
        self.d.reset_i.value = 0
        await self.arm()

    async def close(self):
        for task in self.tasks:
            task.cancel()
        await Timer(1, unit="ps")
        if self.error:
            raise self.error


@cocotb.test()
async def independent_clocks_all_bit_phases_and_skp_lengths(d):
    link = Link(d)
    try:
        await link.start()
        for phase in range(8):
            link.offsets = [phase*4+k for k in range(4)]
            await link.reset(por=bool(phase & 1))
            await link.until(lambda: link.seen >= 80)
            assert min(link.skp_seen) >= 150
            assert int(d.lane_locked_o.value) == 15
    finally:
        await link.close()


@cocotb.test()
async def independent_skp_and_atomic_data_stalls(d):
    link = Link(d)
    try:
        await link.start()
        await link.until(lambda: link.seen >= 8)
        for lane in range(4):
            link.skp_ready = 15 ^ (1 << lane)
            await Timer(64000, unit="ps")
            link.skp_ready = 15
            await Timer(96000, unit="ps")
        before = link.seen
        link.data_ready = 0
        await Timer(64000, unit="ps")
        assert link.seen <= before + 1
        link.data_ready = 1
        await link.until(lambda: link.seen >= before + 8)
    finally:
        await link.close()


@cocotb.test()
async def first_skp_after_sds_faults_and_reset_recovers(d):
    link = Link(d)
    link.bad_first_lane = 2
    link.allow_fault = True
    try:
        await link.start()
        await link.until(lambda: int(d.fault_o.value))
        assert link.seen == 0
        link.bad_first_lane = None
        await link.reset()
        await link.until(lambda: link.seen >= 12)
    finally:
        await link.close()


@cocotb.test()
async def raw_loss_aborts_common_epoch_and_reset_recovers(d):
    link = Link(d)
    try:
        await link.start()
        await link.until(lambda: link.seen >= 12)
        link.allow_fault = True
        link.enabled[1] = False
        await link.until(lambda: int(d.fault_o.value), limit=80)
        await link.reset(por=True)
        await link.until(lambda: link.seen >= 12)
    finally:
        await link.close()


@cocotb.test()
async def backpressure_overflow_aborts_epoch(d):
    link = Link(d)
    try:
        await link.start()
        await link.until(lambda: link.seen >= 8)
        link.allow_fault = True
        link.data_ready = 0
        link.skp_ready = 0
        await link.until(lambda: int(d.fault_o.value))
        assert int(d.lane_fault_o.value) != 0
        await link.reset()
        await link.until(lambda: link.seen >= 12)
    finally:
        await link.close()


@cocotb.test()
async def second_arm_aborts_instead_of_repairing_lane_order(d):
    link = Link(d)
    try:
        await link.start()
        await link.until(lambda: link.seen >= 8)
        link.allow_fault = True
        d.arm_i.value = 1
        await link.until(lambda: int(d.fault_o.value))
        d.arm_i.value = 0
        await link.reset()
        await link.until(lambda: link.seen >= 12)
    finally:
        await link.close()


@cocotb.test()
async def forced_realign_aborts_the_locked_epoch(d):
    link = Link(d)
    try:
        await link.start()
        await link.until(lambda: link.seen >= 8)
        link.allow_fault = True
        d.force_realign_i.value = 4
        await link.until(lambda: int(d.fault_o.value), limit=80)
        await link.reset()
        await link.until(lambda: link.seen >= 12)
    finally:
        await link.close()


@cocotb.test()
async def stopped_recovered_clock_prevents_cohort_start(d):
    link = Link(d)
    link.paused[3] = True
    try:
        await link.start(auto_arm=False)
        await Timer(200000, unit="ps")
        assert int(d.lanes_ready_o.value) == int(d.active_o.value) == int(d.data_valid_o.value) == 0
        assert int(d.fault_o.value) == 0
        link.paused[3] = False
        await link.arm()
        await link.until(lambda: link.seen >= 12)
    finally:
        await link.close()


@cocotb.test()
async def early_arm_fails_and_clean_reset_recovers(d):
    link = Link(d)
    link.paused[3] = True
    link.allow_fault = True
    try:
        await link.start(auto_arm=False)
        await link.until(lambda: not int(d.common_clk_i.value))
        d.arm_i.value = 1
        await link.until(lambda: int(d.common_clk_i.value))
        await Timer(1, unit="ps")
        d.arm_i.value = 0
        await link.until(lambda: int(d.fault_o.value), limit=16)
        assert int(d.active_o.value) == int(d.data_valid_o.value) == 0
        d.arm_i.value = 0
        link.paused[3] = False
        await link.reset()
        await link.until(lambda: link.seen >= 12)
    finally:
        await link.close()
