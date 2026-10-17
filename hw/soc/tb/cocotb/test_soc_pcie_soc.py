# SPDX-FileCopyrightText: 2026 Hasan Melih Akbulut
# SPDX-License-Identifier: Apache-2.0
"""Real CPU ROM and PCIe traffic; only fixture input ports are driven."""

import random
import cocotb
from cocotb.triggers import Timer
from pcie_rx_flow_common import (
    fc_frame,
    decode_fc,
    frame_bytes,
    tlp_bytes,
    request,
    response,
    CID,
    BAR,
    expected_dllp,
)


class Bench:
    def __init__(self, d):
        self.d = d
        self.frames = []
        self.partial = []
        self.held = None
        self.cpu = []
        self.pcie = []
        self.contentions = 0
        self.edges = 0
        self.prev_gpio = None
        self.seq = 0
        self.txseq = 0
        self.errors = 0

    def v(self, n):
        return int(getattr(self.d, n).value)

    async def tick(self, **kw):
        self.d.clk_i.value = 0
        for n, v in kw.items():
            getattr(self.d, n).value = v
        await Timer(10, unit="ns")
        taken = self.v("rx_valid_i") and self.v("rx_ready_o")
        if self.v("rst_ni"):
            assert self.v("alerts_o") == 0
            self.errors += self.v("error_o")
            row = tuple(self.v(n) for n in ("bus_addr_o", "bus_write_o", "bus_data_o"))
            if self.v("cpu_access_o"):
                self.cpu.append(row)
                assert row[0] in (0x2008, 0x2074, 0x201C), row
                assert not self.v("pcie_access_o")
            if self.v("pcie_access_o"):
                self.pcie.append(row)
                assert row[0] >> 12 == 2, row
            self.contentions += self.v("contention_o")
            gpio = self.v("gpio_o") & 1
            if self.prev_gpio is not None:
                self.edges += gpio != self.prev_gpio
            self.prev_gpio = gpio
        if self.v("rst_ni") and self.v("link_up_i") and not self.v("retrain_done_i"):
            beat = tuple(
                self.v(n)
                for n in (
                    "tx_data_o",
                    "tx_sop_o",
                    "tx_eop_o",
                    "tx_dllp_o",
                    "tx_replay_o",
                )
            )
            if self.held is not None:
                assert self.v("tx_valid_o") and beat == self.held
            self.held = (
                beat if self.v("tx_valid_o") and not self.v("tx_ready_i") else None
            )
            if self.v("tx_valid_o") and self.v("tx_ready_i"):
                x, sop, eop, kind, replay = beat
                assert bool(sop) == (not self.partial)
                if sop:
                    self.kind = kind
                    self.replay = replay
                assert (kind, replay) == (self.kind, self.replay)
                self.partial.append(x)
                if eop:
                    f = bytes(self.partial)
                    self.partial = []
                    self.frames.append((kind, replay, f))
                    if kind:
                        if f[0] not in (0, 0x10):
                            decode_fc(f)
                        else:
                            assert f == expected_dllp(
                                f[0] == 0x10, ((f[2] & 15) << 8) | f[3]
                            )
                    else:
                        assert f == frame_bytes(f[2:-4], int.from_bytes(f[:2], "big"))
        else:
            self.partial = []
            self.held = None
        self.d.clk_i.value = 1
        await Timer(10, unit="ns")
        return taken

    async def idle(self, n=100, **kw):
        for _ in range(n):
            await self.tick(rx_valid_i=0, rx_sop_i=0, rx_eop_i=0, **kw)

    async def reset(self):
        await self.tick(
            rst_ni=0,
            link_up_i=0,
            training_i=0,
            retrain_done_i=0,
            function_id_i=CID,
            rx_valid_i=0,
            rx_sop_i=0,
            rx_eop_i=0,
            rx_error_i=0,
            rx_dllp_i=0,
            rx_data_i=0,
            tx_ready_i=1,
        )
        await self.idle(8)
        await self.idle(300, rst_ni=1)
        assert len(self.cpu) > 15 and self.edges > 5 and self.v("gpio_oe_o") == 65535
        self.seq = 0
        self.txseq = 0

    async def wire(self, f, dllp=0):
        for i, x in enumerate(f):
            for _ in range(600):
                if await self.tick(
                    rx_valid_i=1,
                    rx_data_i=x,
                    rx_sop_i=i == 0,
                    rx_eop_i=i == len(f) - 1,
                    rx_dllp_i=dllp,
                ):
                    break
            else:
                raise AssertionError("Ingress deadlock")
        await self.tick(rx_valid_i=0, rx_sop_i=0, rx_eop_i=0)

    async def initialize(self):
        await self.tick(link_up_i=1)
        for c in range(3):
            await self.wire(fc_frame(0, c, 0 if c == 2 else 8, 0 if c == 2 else 16), 1)
        await self.wire(fc_frame(1, 0, 8, 16), 1)
        await self.idle(150)
        assert self.v("initialized_o")

    async def transact(self, words, expected=None, stall=False):
        start = len(self.frames)
        await self.wire(frame_bytes(tlp_bytes(words), self.seq))
        self.seq = (self.seq + 1) & 4095
        if stall:
            rng = random.Random(self.seq)
            for _ in range(140):
                await self.tick(tx_ready_i=rng.randrange(4) != 0)
        await self.idle(160, tx_ready_i=1)
        completions = [f for k, r, f in self.frames[start:] if not k and not r]
        if expected is not None:
            assert completions == [frame_bytes(tlp_bytes(expected), self.txseq)], (
                completions
            )
            await self.wire(expected_dllp(0, self.txseq), 1)
            self.txseq += 1
        return completions

    async def enable(self):
        await self.transact(request(0x44, CID << 16 | 0x10, [BAR]), response())
        await self.transact(request(0x44, CID << 16 | 4, [2]), response())


@cocotb.test()
async def real_cpu_and_pcie_share_gpio_without_cross_ack(d):
    b = Bench(d)
    await b.reset()
    await b.initialize()
    await b.enable()
    before = len(b.cpu)
    for i in range(8):
        mask = 1 << (8 + i)
        assert await b.transact(request(0x40, BAR + 0x54, [mask]), stall=True) == []
        assert b.v("gpio_o") & mask
        # CAP is stable while the real CPU continues toggling GPIO bit zero.
        cap = 0x0001010F
        await b.transact(
            request(0, BAR + 0x1C, tag=i), response(data=cap, tag=i, lower=0x1C)
        )
    assert len(b.cpu) > before + 60 and b.contentions > 0 and len(b.pcie) == 16
    assert b.v("gpio_o") & 0xFF00 == 0xFF00
    assert b.errors == 0 and not b.v("retrain_request_o")
    d._log.info(
        "CPU_GPIO cpu_transactions=%d pcie_transactions=%d contention_cycles=%d bit0_edges=%d",
        len(b.cpu),
        len(b.pcie),
        b.contentions,
        b.edges,
    )


@cocotb.test()
async def partial_write_wrong_bar_and_link_reset_are_contained(d):
    b = Bench(d)
    await b.reset()
    await b.initialize()
    await b.enable()
    await b.transact(request(0x40, BAR + 0x54, [0x4000]))
    assert b.v("gpio_o") & 0x4000
    count = len(b.pcie)
    await b.transact(request(0x40, BAR + 4, [0], be=1))
    assert b.v("gpio_o") & 0x4000 and len(b.pcie) == count and b.errors > 0
    await b.transact(
        request(0, BAR + 0x1000, tag=8), response(tag=8, count=0, status=1)
    )
    assert len(b.pcie) == count
    # Discard an actual half received write by link loss. CPU must keep running.
    f = frame_bytes(tlp_bytes(request(0x40, BAR + 0x54, [0x8000])), b.seq)
    for i, x in enumerate(f[:9]):
        assert await b.tick(
            rx_valid_i=1, rx_data_i=x, rx_sop_i=i == 0, rx_eop_i=0, rx_dllp_i=0
        )
    cpus = len(b.cpu)
    await b.idle(150, link_up_i=0)
    assert len(b.cpu) > cpus + 10 and b.v("gpio_o") & 0x8000 == 0
    assert len(b.pcie) == count and not b.v("initialized_o")
    b.seq = 0
    b.txseq = 0
    await b.initialize()
    await b.enable()
    await b.transact(request(0x40, BAR + 0x54, [0x8000]))
    assert b.v("gpio_o") & 0xC000 == 0xC000
    await b.reset()
    assert b.v("gpio_o") & 0xFFFE == 0 and not b.v("initialized_o")
