# SPDX-FileCopyrightText: 2026 Hasan Melih Akbulut
# SPDX-License-Identifier: Apache-2.0
"""Port-only packet framing tests; no link/CRC/PHY compliance claim."""
import random
import os

import cocotb
from cocotb.triggers import Timer

CID, RID, BAR = 0x0200, 0x0138, 0x82345000
CONFIG_ID = int(os.environ.get('PCIE_CFG_ID', str(0x56781234)))


def request(kind, address=0, payload=(), be=15, tag=0x97, length=1):
    words = [(kind << 24) | length, (RID << 16) | (tag << 8) | be]
    words += [address >> 32, address & 0xffffffff] if kind & 0x20 else [address]
    return words + list(payload)


def response(data=None, tag=0x97, count=4, lower=0, status=0):
    words = [0x4a000001 if data is not None else 0x0a000000,
             (CID << 16) | (status << 13) | count,
             (RID << 16) | (tag << 8) | lower]
    return words + ([] if data is None else [data])


class Bench:
    def __init__(self, dut):
        self.d = dut
        self.bus, self.packets, self.current = [], [], []
        self.errors = 0
        self.held = None

    def v(self, name):
        return int(getattr(self.d, name).value)

    async def tick(self, **signals):
        self.d.clk_i.value = 0
        for name, value in signals.items():
            getattr(self.d, name).value = value
        await Timer(5, unit='ns')
        accepted = self.v('rx_valid_i') and self.v('rx_ready_o')
        if self.v('rst_ni'):
            beat = tuple(self.v(n) for n in ('tx_data_o', 'tx_sop_o', 'tx_eop_o'))
            if self.held is not None:
                assert self.v('tx_valid_o') and beat == self.held, 'Stalled TX changed'
            self.held = beat if self.v('tx_valid_o') and not self.v('tx_ready_i') else None
            if self.v('tx_valid_o') and self.v('tx_ready_i'):
                data, sop, eop = beat
                assert bool(sop) == (not self.current), 'Broken completion boundary'
                self.current.append(data)
                if eop:
                    self.packets.append(self.current)
                    self.current = []
            if self.v('psel_o') and self.v('penable_o') and self.v('pready_i'):
                self.bus.append(tuple(self.v(n) for n in ('paddr_o', 'pwrite_o', 'pstrb_o', 'pwdata_o')))
        else:
            self.held = None
            self.current = []
        self.d.clk_i.value = 1
        await Timer(5, unit='ns')
        self.errors += self.v('error_o')
        return accepted

    async def reset(self):
        await self.tick(rst_ni=0, rx_valid_i=0, rx_data_i=0, rx_sop_i=0,
                        rx_eop_i=0, rx_error_i=0, tx_ready_i=1,
                        function_id_i=CID, pready_i=1, pslverr_i=0, prdata_i=0xd3c2b1a0)
        assert not self.v('rx_ready_o') and not self.v('tx_valid_o') and not self.v('psel_o')
        await self.tick(rst_ni=1)
        self.bus.clear(); self.packets.clear(); self.errors = 0

    async def word(self, data, sop=False, eop=False, error=False):
        for _ in range(80):
            if await self.tick(rx_valid_i=1, rx_data_i=data, rx_sop_i=sop,
                               rx_eop_i=eop, rx_error_i=error):
                return
        raise AssertionError('Input did not accept a beat')

    async def send(self, words, bad_at=None, gap=False):
        for index, word in enumerate(words):
            if gap:
                await self.tick(rx_valid_i=0, rx_sop_i=1, rx_eop_i=1, rx_error_i=1, rx_data_i=0xffffffff)
            await self.word(word, index == 0, index == len(words)-1, index == bad_at)
        await self.tick(rx_valid_i=0, rx_sop_i=0, rx_eop_i=0, rx_error_i=0)

    async def idle(self, n=35, **signals):
        for _ in range(n):
            await self.tick(rx_valid_i=0, **signals)

    async def transact(self, words, **kwargs):
        old = len(self.packets)
        await self.send(words, **kwargs)
        await self.idle()
        return self.packets[old:]

    async def enable(self):
        assert await self.transact(request(0x44, CID << 16 | 0x10, [BAR])) == [response()]
        assert await self.transact(request(0x44, CID << 16 | 4, [2])) == [response()]
        assert self.v('bar0_o') == BAR and self.v('memory_enable_o')
        self.bus.clear(); self.packets.clear(); self.errors = 0


@cocotb.test()
async def real_packet_headers_payload_and_completion_order(dut):
    b = Bench(dut); await b.reset()
    assert await b.transact(request(0x04, CID << 16), gap=True) == [response(data=CONFIG_ID)]
    await b.enable()
    for wide in (0, 0x20):
        for be in range(16):
            before = len(b.bus)
            assert await b.transact(request(0x40 | wide, BAR+0x24, [0x87654321], be=be), gap=True) == []
            assert b.bus[before:] == ([(0x24, 1, be, 0x87654321)] if be else [])
            old = len(b.bus)
            bits = [i for i in range(4) if be >> i & 1]
            expected = response(data=0xd3c2b1a0 if be else 0,
                                count=bits[-1]-bits[0]+1 if be else 1,
                                lower=0x24+(bits[0] if be else 0))
            assert await b.transact(request(wide, BAR+0x24, be=be)) == [expected]
            assert len(b.bus)-old == bool(be)
    assert b.errors == 0


@cocotb.test()
async def no_side_effect_before_complete_clean_eop(dut):
    b = Bench(dut); await b.reset(); await b.enable()
    words = request(0x60, BAR+0x30, [0x78563412])
    for index, word in enumerate(words):
        await b.word(word, sop=index == 0)
        await b.idle(5)
        assert not b.bus and not b.v('psel_o')
    # A late integrity failure invalidates the whole buffered packet.
    await b.word(0, eop=True, error=True)
    await b.idle()
    assert not b.bus and not b.packets and b.errors
    assert await b.transact(request(0x40, BAR+0x30, [0x78563412])) == []
    assert b.bus == [(0x30, 1, 15, 0x78563412)]


@cocotb.test()
async def malformed_lengths_integrity_and_prefixes_are_drained(dut):
    b = Bench(dut); await b.reset(); await b.enable()
    malformed = [[0x40000001], [0x40000001, RID << 16 | 15],
                 request(0x40, BAR), request(0x40, BAR, [1, 2]),
                 request(0, BAR, [1]), request(0x80, BAR, [1]),
                 request(0x40, BAR, [1]*1024, length=0),
                 request(0x40, BAR, [1]*2050)]
    for words in malformed:
        assert await b.transact(words) == []
        assert not b.bus
    good = request(0x60, BAR, [0x11223344])
    for index in range(len(good)):
        assert await b.transact(good, bad_at=index) == []
        assert not b.bus
    assert b.errors >= len(malformed)+len(good)
    # Recovery works after every discarded frame; no stale header or payload.
    assert await b.transact(request(0x04, CID << 16, tag=0x52)) == [response(data=CONFIG_ID, tag=0x52)]


@cocotb.test()
async def new_sop_resynchronizes_partial_and_orphan_packets(dut):
    b = Bench(dut); await b.reset(); await b.enable()
    await b.word(0x40000001, sop=True)
    await b.word(RID << 16 | 15)
    assert await b.transact(request(0x40, BAR+0x34, [0xa1b2c3d4])) == []
    assert b.bus == [(0x34, 1, 15, 0xa1b2c3d4)] and b.errors
    b.bus.clear()
    await b.word(0xdeadbeef)  # Orphan beat; drain until EOP or fresh SOP.
    await b.word(0xcafef00d)
    assert await b.transact(request(0x04, CID << 16)) == [response(data=CONFIG_ID)]
    assert not b.bus


@cocotb.test()
async def output_stalls_propagate_without_loss_or_duplication(dut):
    b = Bench(dut); await b.reset(); await b.enable()
    await b.tick(tx_ready_i=0)
    # One completion in serializer, one in backend, one complete RX waiting.
    for tag in range(3):
        await b.send(request(0, BAR+tag*4, tag=tag))
        await b.idle(15)
    assert not b.v('rx_ready_o') and b.v('tx_valid_o')
    await b.idle(20)
    rng = random.Random(0x3c4)
    for _ in range(160):
        await b.tick(rx_valid_i=0, tx_ready_i=rng.randrange(2))
    await b.idle(tx_ready_i=1)
    assert b.packets == [response(data=0xd3c2b1a0, tag=t, lower=t*4) for t in range(3)]
    assert len(b.bus) == 3 and not b.current and b.v('rx_ready_o')
    assert not b.errors


@cocotb.test()
async def reset_aborts_partial_packets_bus_and_held_completions(dut):
    b = Bench(dut)
    words = request(0x60, BAR, [0x01234567])
    for stop in range(1, len(words)+1):
        await b.reset(); await b.enable()
        for index, word in enumerate(words[:stop]):
            await b.word(word, sop=index == 0)
        await b.reset(); await b.idle()
        assert not b.bus and not b.packets and not b.v('memory_enable_o')
    await b.enable()
    await b.tick(pready_i=0)
    await b.send(request(0, BAR))
    for _ in range(5):
        if b.v('penable_o'):
            break
        await b.tick(rx_valid_i=0)
    assert b.v('penable_o')
    await b.reset(); await b.idle()
    assert not b.bus and not b.packets
    await b.tick(tx_ready_i=0)
    await b.send(request(0x04, CID << 16)); await b.idle(15)
    assert b.v('tx_valid_o')
    await b.reset(); await b.idle()
    assert not b.packets and not b.current
    assert await b.transact(request(0x04, CID << 16)) == [response(data=CONFIG_ID)]
