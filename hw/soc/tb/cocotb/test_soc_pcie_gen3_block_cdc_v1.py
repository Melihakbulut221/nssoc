# SPDX-FileCopyrightText: 2026 Hasan Melih Akbulut
# SPDX-License-Identifier: Apache-2.0
"""Two independent clocks; public-port FIFO oracle, no internal signal reads."""
from collections import deque
import os
import random

import cocotb
from cocotb.triggers import Timer

DEPTH = int(os.environ.get("CDC_DEPTH", "32"))


def record(index, code=None):
    rng = random.Random(0xCDC000 + index)
    # Deliberately preserve arbitrary upper bits even for a 66-bit block.
    return (rng.getrandbits(194), index % 5 if code is None else code,
            (index >> 1) & 1, (index >> 2) & 1, (index >> 3) & 1)


class Link:
    def __init__(self, d, wr_ps=3800, rd_ps=4001, phase_ps=719):
        self.d = d
        self.wr_ps, self.rd_ps, self.phase_ps = wr_ps, rd_ps, phase_ps
        self.pending, self.expected = deque(), deque()
        self.gap, self.gap_left = 3, 0
        self.ready, self.allow_fault = True, False
        self.pause_wr, self.pause_rd = False, False
        self.wr_cycles = self.rd_cycles = 0
        self.writes = self.reads = 0
        self.held = None
        self.tasks = []
        self.error = None
        self.loss = False

    def reset_asserted(self):
        return not int(self.d.por_ni.value) or int(self.d.wr_reset_i.value) or int(self.d.rd_reset_i.value)

    async def start(self):
        d = self.d
        for name in ("por_ni", "wr_clk_i", "rd_clk_i", "wr_reset_i", "rd_reset_i", "wr_valid_i",
                     "wr_block_i", "wr_length_code_i", "wr_skp_i", "wr_eieos_i", "wr_realign_i",
                     "wr_loss_i", "rd_ready_i"):
            getattr(d, name).value = 0
        await Timer(1, unit="ps")  # Apply initial public input values before monitors.
        self.tasks = [cocotb.start_soon(self.writer()), cocotb.start_soon(self.reader())]
        await Timer(50000, unit="ps")
        d.por_ni.value = 1
        await self.until(lambda: int(d.wr_running_o.value) and int(d.rd_running_o.value))

    async def until(self, condition, limit=10000):
        for _ in range(limit):
            if self.error:
                raise self.error
            if condition():
                return
            await Timer(1000, unit="ps")
        raise AssertionError("Bounded digital scenario did not complete")

    async def writer(self):
        d = self.d
        try:
            while True:
                d.wr_clk_i.value = 0
                if self.pause_wr:
                    await Timer(100, unit="ps")
                    continue
                live = not self.reset_asserted() and int(d.wr_running_o.value)
                item = self.pending[0] if live and self.pending and self.gap_left == 0 else None
                d.wr_valid_i.value = item is not None
                d.wr_loss_i.value = self.loss
                if item is not None:
                    for name, value in zip(("wr_block_i", "wr_length_code_i", "wr_skp_i", "wr_eieos_i", "wr_realign_i"), item):
                        getattr(d, name).value = value
                await Timer(self.wr_ps // 2, unit="ps")
                accepted = int(d.wr_accept_o.value)
                active = not self.reset_asserted() and int(d.wr_running_o.value)
                if active and item is not None:
                    if not self.allow_fault:
                        assert accepted, "Live no-backpressure block was not accepted"
                    if accepted:
                        self.expected.append(item)
                        self.writes += 1
                    self.pending.popleft()  # Never wait/retry a rejected physical input.
                    self.gap_left = self.gap - 1
                elif self.gap_left:
                    self.gap_left -= 1
                if accepted:
                    assert active and item is not None and not self.loss and item[1] <= 4
                d.wr_clk_i.value = 1
                self.wr_cycles += 1
                await Timer(self.wr_ps - self.wr_ps // 2, unit="ps")
                if not self.allow_fault and not self.reset_asserted():
                    assert not int(d.wr_fault_o.value), "Unexpected recovered-domain fault"
        except BaseException as error:
            self.error = error
            raise

    async def reader(self):
        d = self.d
        await Timer(self.phase_ps, unit="ps")
        try:
            while True:
                d.rd_clk_i.value = 0
                if self.pause_rd:
                    await Timer(100, unit="ps")
                    continue
                d.rd_ready_i.value = self.ready
                await Timer(self.rd_ps // 2, unit="ps")
                valid, running = int(d.rd_valid_o.value), int(d.rd_running_o.value)
                ready_at_edge = int(d.rd_ready_i.value)
                item = tuple(int(getattr(d, n).value) for n in
                             ("rd_block_o", "rd_length_code_o", "rd_skp_o", "rd_eieos_o", "rd_realign_o")) if valid else None
                if self.reset_asserted() or not running:
                    assert not valid, "Output escaped reset/fault/startup barrier"
                    self.held = None
                else:
                    if self.held is not None:
                        assert valid and item == self.held, "Held complete-block output changed"
                    self.held = item if valid and not ready_at_edge else None
                    if valid and ready_at_edge:
                        assert self.expected, "Output fabricated/repeated an unaccepted block"
                        assert item == self.expected.popleft(), "Complete block/metadata ordering mismatch"
                        self.reads += 1
                d.rd_clk_i.value = 1
                self.rd_cycles += 1
                await Timer(self.rd_ps - self.rd_ps // 2, unit="ps")
        except BaseException as error:
            self.error = error
            raise

    async def send(self, count, first=0, gap=3):
        self.gap = gap
        self.pending.extend(record(i) for i in range(first, first + count))
        await self.until(lambda: not self.pending, limit=count * gap * self.wr_ps // 1000 + 100)

    async def drain(self):
        self.ready = True
        await self.until(lambda: not self.pending and not self.expected)
        await Timer(30000, unit="ps")
        assert not int(self.d.rd_valid_o.value), "Duplicate after expected drain"
        if self.error:
            raise self.error

    async def reset(self, domain="wr", stopped=None):
        d = self.d
        self.pending.clear()
        self.expected.clear()
        self.held = None
        self.loss = False
        self.gap_left = 0
        signal = getattr(d, domain + "_reset_i")
        signal.value = 1
        await Timer(1100, unit="ps")
        assert not int(d.rd_valid_o.value) and not int(d.wr_accept_o.value)
        if stopped == "wr":
            self.pause_wr = True
        elif stopped == "rd":
            self.pause_rd = True
        await Timer(50000, unit="ps")
        signal.value = 0
        if stopped:
            await Timer(100000, unit="ps")
            assert not int(d.wr_running_o.value) and not int(d.rd_running_o.value), "Stopped domain escaped restart barrier"
            self.pause_wr = self.pause_rd = False
        await self.until(lambda: int(d.wr_running_o.value) and int(d.rd_running_o.value))
        self.allow_fault = False
        assert not int(d.wr_fault_o.value) and not int(d.rd_fault_o.value)

    def close(self):
        for task in self.tasks:
            task.cancel()


@cocotb.test()
async def asynchronous_metadata_and_drift(d):
    link = Link(d, 4000, 4001, 137)
    await link.start()
    await link.send(1600, gap=3)
    await link.drain()
    assert link.writes == link.reads == 1600
    link.close()


@cocotb.test()
async def fast_reader_full_rate_and_many_wraps(d):
    link = Link(d, 4001, 1900, 617)
    await link.start()
    await link.send(2048, first=5000, gap=1)
    await link.drain()
    assert link.writes == link.reads == 2048
    link.close()


@cocotb.test()
async def held_output_and_bounded_pressure(d):
    link = Link(d)
    await link.start()
    link.ready = False
    await link.send(DEPTH // 2, gap=3)
    await Timer(170000, unit="ps")
    assert int(d.rd_valid_o.value)
    await link.drain()
    for index in range(30):
        link.ready = index % 3 != 0
        await link.send(2, first=9000 + index * 2, gap=4)
    await link.drain()
    assert link.writes == link.reads
    link.close()


@cocotb.test()
async def exact_ram_prefetch_capacity_overflow_and_restart(d):
    link = Link(d)
    await link.start()
    link.ready = False
    link.allow_fault = True
    link.gap = 4
    link.pending.extend(record(i + 10000) for i in range(DEPTH + 8))
    await link.until(lambda: int(d.wr_fault_o.value))
    assert int(d.wr_overflow_o.value), "Unaccepted input did not report overflow"
    assert link.writes == DEPTH + 2, (link.writes, DEPTH)
    await link.until(lambda: int(d.rd_fault_o.value))
    link.ready = True
    reads = link.reads
    await Timer(100000, unit="ps")
    assert link.reads == reads and not int(d.rd_valid_o.value)
    assert not int(d.wr_running_o.value) and int(d.wr_fault_o.value)
    await link.reset("wr")
    await link.send(40, first=20000)
    await link.drain()
    link.close()


@cocotb.test()
async def either_domain_reset_with_held_output(d):
    link = Link(d)
    await link.start()
    for epoch, domain in enumerate(("wr", "rd", "wr", "rd")):
        link.ready = False
        await link.send(DEPTH // 2, first=30000 + epoch * 100)
        await link.until(lambda: int(d.rd_valid_o.value))
        link.ready = True
        await link.reset(domain)
        await link.send(DEPTH * 3, first=40000 + epoch * 200)
        await link.drain()
    link.close()


@cocotb.test()
async def stopped_clock_reset_and_restart(d):
    link = Link(d)
    await link.start()
    for domain in ("wr", "rd"):
        link.ready = False
        await link.send(DEPTH // 2, first=50000)
        await link.reset(domain, stopped=domain)
        link.ready = True
        await link.send(50, first=60000)
        await link.drain()
    link.close()


@cocotb.test()
async def alignment_loss_and_illegal_length_fail_closed(d):
    link = Link(d)
    await link.start()
    for fault in ("loss", "length"):
        link.ready = False
        await link.send(2, first=70000)
        link.allow_fault = True
        if fault == "loss":
            link.loss = True
        else:
            link.pending.append(record(71000, code=7))
        await link.until(lambda: int(d.wr_fault_o.value))
        assert not int(d.wr_overflow_o.value), "Non-capacity fault mislabeled overflow"
        await link.until(lambda: int(d.rd_fault_o.value))
        assert not int(d.rd_valid_o.value)
        await link.reset("rd")
        link.ready = True
        await link.send(50, first=72000)
        await link.drain()
    link.close()
