# SPDX-FileCopyrightText: 2026 Hasan Melih Akbulut
# SPDX-License-Identifier: Apache-2.0
"""Descriptor-level PCIe tests; no serial-link/PHY or compliance claim.

The scoreboard observes only ports. Header constants are PCIe DWORD fields,
not imported from the DUT. Test-only IDs 1234:5678 are not product assignments.
"""
import os
import random

import cocotb
from cocotb.triggers import Timer

TIMEOUT = int(os.environ.get('PCIE_APB_TIMEOUT', '8'))
CONFIG_ID = int(os.environ.get('PCIE_CFG_ID', str(0x56781234)))
CID, RID, BAR = 0x0200, 0x0100, 0x80000000


def packet(kind, address=0, data=0, be=15, tag=0x5a, length=1,
           last_be=0, flags=0, payload=None, rid=RID):
    """DW0 first in header[127:96]; single payload DWORD is separate."""
    is64 = bool(kind & 0x20)
    words = [(kind << 24) | flags | length,
             (rid << 16) | (tag << 8) | (last_be << 4) | be,
             address >> 32 if is64 else address,
             address & 0xffffffff if is64 else 0]
    hdr = sum((v & 0xffffffff) << (96 - 32*i) for i, v in enumerate(words))
    return hdr, data, int(bool(kind & 0x40)) if payload is None else payload


def completion(status=0, data=None, tag=0x5a, count=4, lower=0, rid=RID, cid=CID):
    return (((0x4a000001 if data is not None else 0x0a000000) << 96)
            | ((cid << 16 | status << 13 | count) << 64)
            | ((rid << 16 | tag << 8 | lower) << 32),
            data if data is not None else 0, int(data is not None))


class Bench:
    def __init__(self, dut):
        self.d = dut
        self.bus = []
        self.responses = []
        self.errors = 0

    def v(self, name):
        return int(getattr(self.d, name).value)

    async def tick(self, **signals):
        self.d.clk_i.value = 0
        for name, value in signals.items():
            getattr(self.d, name).value = value
        await Timer(5, unit='ns')
        accepted = self.v('rx_valid_i') and self.v('rx_ready_o')
        if self.v('psel_o') and self.v('penable_o') and self.v('pready_i'):
            self.bus.append(tuple(self.v(n) for n in ('paddr_o', 'pwrite_o', 'pstrb_o', 'pwdata_o')))
        if self.v('tx_valid_o') and self.v('tx_ready_i'):
            self.responses.append(tuple(self.v(n) for n in ('tx_hdr_o', 'tx_data_o', 'tx_has_data_o')))
        self.d.clk_i.value = 1
        await Timer(5, unit='ns')
        self.errors += self.v('error_o')
        return accepted

    async def reset(self):
        await self.tick(rst_ni=0, rx_valid_i=0, rx_hdr_i=0, rx_data_i=0,
                        rx_payload_dw_i=0, function_id_i=CID, tx_ready_i=1,
                        pready_i=1, pslverr_i=0, prdata_i=0x76543210)
        assert not self.v('psel_o') and not self.v('tx_valid_o')
        await self.tick(rst_ni=1)
        self.bus.clear(); self.responses.clear(); self.errors = 0

    async def send(self, p):
        for _ in range(max(40, TIMEOUT+8)):
            if await self.tick(rx_hdr_i=p[0], rx_data_i=p[1], rx_payload_dw_i=p[2], rx_valid_i=1):
                await self.tick(rx_valid_i=0)
                return
        raise AssertionError('RX handshake timed out')

    async def drain(self):
        for _ in range(max(40, TIMEOUT+8)):
            await self.tick(rx_valid_i=0)
            if self.v('rx_ready_o'):
                return
        raise AssertionError('Backend failed to return idle')

    async def transact(self, p):
        before = len(self.responses)
        await self.send(p)
        await self.drain()
        return self.responses[before:]

    async def cfg(self, offset, data=None, be=15, tag=0x5a):
        return await self.transact(packet(0x04 if data is None else 0x44,
                                         CID << 16 | offset, data or 0, be=be, tag=tag))

    async def enable(self):
        assert await self.cfg(0x10, BAR) == [completion()]
        assert await self.cfg(4, 2) == [completion()]
        assert self.v('bar0_o') == BAR and self.v('memory_enable_o')
        self.bus.clear(); self.responses.clear(); self.errors = 0


@cocotb.test()
async def configuration_bar_probe_and_write_masks(dut):
    b = Bench(dut); await b.reset()
    assert await b.cfg(0) == [completion(data=CONFIG_ID)]
    assert await b.cfg(0, 0xffffffff) == [completion()]
    assert await b.cfg(0) == [completion(data=CONFIG_ID)]
    assert await b.cfg(0x10, 0xffffffff) == [completion()]
    assert await b.cfg(0x10) == [completion(data=0xfffff000)]
    assert await b.cfg(0x10, 0x81234fff) == [completion()]
    assert await b.cfg(0x10) == [completion(data=0x81234000)]
    assert await b.cfg(0x10, 0x56000000, be=8) == [completion()]
    assert await b.cfg(0x10) == [completion(data=0x56234000)]
    assert await b.cfg(4, 0xffffffff, be=2) == [completion()]
    assert not b.v('memory_enable_o')
    assert await b.cfg(4, 0xffffffff, be=1) == [completion()]
    assert await b.cfg(4) == [completion(data=2)]
    assert await b.cfg(0, be=3) == [completion(data=CONFIG_ID & 0xffff)]
    assert await b.cfg(0xffc) == [completion(data=0)]
    assert not b.bus


@cocotb.test()
async def all_byte_enables_tags_and_32_64_bit_headers(dut):
    b = Bench(dut); await b.reset(); await b.enable()
    # AMD PG156 completion descriptor: zero-length MRd has Byte Count 1.
    assert completion(data=0, count=1) == (0x4a0000010200000101005a0000000000, 0, 1)
    for wide in [0, 0x20]:
        for be in range(16):
            tag = (be * 17) & 255
            before = len(b.bus)
            assert await b.transact(packet(0x40 | wide, BAR+0x17c, 0xdeadbeef, be, tag)) == []
            assert len(b.bus) == before + bool(be)
            if be: assert b.bus[-1] == (0x17c, 1, be, 0xdeadbeef)
            before = len(b.bus)
            actual = await b.transact(packet(wide, BAR+0x17c, be=be, tag=tag))
            enabled = [i for i in range(4) if be & (1 << i)]
            count = enabled[-1]-enabled[0]+1 if enabled else 1
            low = 0x7c+(enabled[0] if enabled else 0)
            assert actual == [completion(data=0x76543210 if be else 0, tag=tag, count=count, lower=low)]
            assert len(b.bus) == before + bool(be)
            if be: assert b.bus[-1][:3] == (0x17c, 0, 0)
    assert b.errors == 0


@cocotb.test()
async def disabled_window_malformed_and_unsupported_have_no_bus_effect(dut):
    b = Bench(dut); await b.reset()
    assert await b.transact(packet(0, BAR)) == [completion(status=1, count=0)]
    assert await b.transact(packet(0x40, BAR, 55)) == []
    await b.enable()
    for p in [packet(0, BAR+0x1000), packet(0, BAR-4), packet(0x20, 0x180000000),
              packet(0, BAR+1), packet(0, BAR, length=0), packet(0, BAR, length=2),
              packet(0, BAR, last_be=15), packet(2, BAR),
              packet(5, CID << 16), packet(4, (CID+1) << 16)]:
        assert await b.transact(p) == [completion(status=1, count=0)]
    # Truncated/extra data, poison/digest, hints and translated requests are
    # malformed/unsupported descriptors: reported and dropped, never issued.
    for p in [packet(0x40, BAR, payload=0), packet(0x40, BAR, payload=2),
              packet(0, BAR, payload=1), packet(0, BAR, flags=1 << 14),
              packet(0, BAR, flags=1 << 15), packet(0, BAR, flags=1 << 10),
              packet(0, BAR, flags=1 << 16), packet(0x0a, payload=0),
              packet(0x30, payload=0), packet(0x80, payload=0)]:
        assert await b.transact(p) == []
    assert not b.bus and b.errors == 20


@cocotb.test()
async def apb_wait_states_and_completion_backpressure(dut):
    b = Bench(dut); await b.reset(); await b.enable()
    rng = random.Random(221)
    for index in range(25):
        await b.tick(pready_i=0, tx_ready_i=0)
        p = packet(0, BAR+4*index, tag=index, rid=0xa100+index)
        await b.send(p)
        stable = tuple(b.v(n) for n in ('paddr_o','pwrite_o','pstrb_o','pwdata_o'))
        for _ in range(rng.randrange(0, min(6, TIMEOUT))):
            assert b.v('psel_o') and b.v('penable_o') and not b.v('rx_ready_o')
            assert tuple(b.v(n) for n in ('paddr_o','pwrite_o','pstrb_o','pwdata_o')) == stable
            await b.tick()
        data = rng.getrandbits(32)
        await b.tick(pready_i=1, prdata_i=data)
        expected = completion(data=data, tag=index, rid=0xa100+index, lower=4*index)
        for _ in range(rng.randrange(1, 8)):
            assert tuple(b.v(n) for n in ('tx_hdr_o','tx_data_o','tx_has_data_o')) == expected
            assert b.v('tx_valid_o') and not b.v('rx_ready_o') and not b.v('psel_o')
            # Changing live descriptor and function ID cannot alter a held completion.
            await b.tick(rx_hdr_i=rng.getrandbits(128), function_id_i=0xbeef)
        await b.tick(tx_ready_i=1, function_id_i=CID)
        assert b.responses[-1] == expected
    assert len(b.bus) == 25 and b.errors == 0


@cocotb.test()
async def apb_errors_timeouts_and_recovery(dut):
    b = Bench(dut); await b.reset(); await b.enable()
    for write in [False, True]:
        for timeout in [False, True]:
            await b.tick(pready_i=not timeout, pslverr_i=not timeout)
            actual = await b.transact(packet(0x40 if write else 0, BAR+0x20, 88))
            assert actual == ([] if write else [completion(status=4, count=0)])
            await b.tick(pready_i=1, pslverr_i=0)
            assert await b.transact(packet(0, BAR)) == [completion(data=0x76543210)]
    assert b.errors == 4
    # Readiness on the last allowed APB cycle wins over the timeout.
    await b.tick(pready_i=0)
    await b.send(packet(0, BAR))
    for _ in range(TIMEOUT-1): await b.tick()
    await b.tick(pready_i=1)
    await b.drain()
    assert b.responses[-1] == completion(data=0x76543210)
    assert b.errors == 4


@cocotb.test()
async def reset_aborts_each_phase_and_clears_decode(dut):
    b = Bench(dut)
    for phase in ['idle','setup','access','response']:
        await b.reset(); await b.enable()
        if phase != 'idle':
            await b.tick(pready_i=0, tx_ready_i=0,
                         rx_valid_i=1, rx_hdr_i=packet(0,BAR)[0], rx_payload_dw_i=0)
            if phase in ['access','response']: await b.tick(rx_valid_i=0)
            if phase == 'response': await b.tick(pready_i=1)
        await b.reset()
        assert b.v('bar0_o') == 0 and b.v('memory_enable_o') == 0
        for _ in range(10): await b.tick()
        assert not b.responses and not b.bus
        assert await b.cfg(0) == [completion(data=CONFIG_ID)]
