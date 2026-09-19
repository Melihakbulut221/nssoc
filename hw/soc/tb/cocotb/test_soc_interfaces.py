# SPDX-FileCopyrightText: 2026 Hasan Melih Akbulut
# SPDX-License-Identifier: Apache-2.0
"""Pin-level protocol tests through APB; no force of internal RTL state."""
import cocotb
from cocotb.triggers import Timer


class Bus:
    def __init__(self, dut):
        self.d = dut
        self.peer = None

    async def step(self, n=1):
        for _ in range(n):
            self.d.clk_i.value = 0
            await Timer(10, unit="ns")
            if self.peer:
                self.peer.tick()
            self.d.clk_i.value = 1
            await Timer(10, unit="ns")

    async def reset(self):
        for name in ('clk_i', 'rst_ni', 'psel_i', 'penable_i', 'pwrite_i',
                     'paddr_i', 'pwdata_i', 'pstrb_i', 'dev_i', 'scl_hold_i',
                     'sda_hold_i', 'spw_disconnect_i'):
            getattr(self.d, name).value = 0
        await self.step(8)
        self.d.rst_ni.value = 1
        await self.step(8)

    async def access(self, dev, addr, data=None, strobe=15, error=False):
        d = self.d
        d.dev_i.value = dev
        d.paddr_i.value = addr
        d.pwrite_i.value = data is not None
        d.pwdata_i.value = data or 0
        d.pstrb_i.value = strobe
        d.psel_i.value = 1
        d.penable_i.value = 0
        await self.step()
        d.penable_i.value = 1
        # Sample ACCESS before its completing edge, including read-pop ports.
        for _ in range(100):
            await Timer(1, unit="ns")
            if int(d.pready_o.value):
                result = int(d.prdata_o.value) if data is None and not error else 0
                assert bool(int(d.pslverr_o.value)) == error, (dev, addr, data)
                await self.step()
                break
            await self.step()
        else:
            raise AssertionError('APB did not terminate')
        d.psel_i.value = 0
        d.penable_i.value = 0
        await self.step()
        return result

    async def rd(self, dev, addr, **kw):
        return await self.access(dev, addr, **kw)

    async def wr(self, dev, addr, data, **kw):
        return await self.access(dev, addr, data, **kw)

    async def byte(self, dev, addr, data=None):
        lane = addr & 3
        value = await self.access(dev, addr & ~3,
                                  None if data is None else data << (8*lane),
                                  strobe=1 << lane)
        return (value >> (8*lane)) & 255

    async def poll(self, dev, addr, mask, expected, count=3000):
        for _ in range(count):
            value = await self.rd(dev, addr)
            if value & mask == expected:
                return value
        raise AssertionError(f'poll {dev}:{addr:x} mask={mask:x} expected={expected:x} got={value:x}')


@cocotb.test()
async def spi_all_modes_and_chip_selects(d):
    b = Bus(d)
    await b.reset()
    for mode in range(4):
        for cs in range(2):
            await b.wr(1, 0, mode | (cs << 2) | 8)
            await b.wr(1, 4, 3)
            for value in [0, 255, 0x81, 0x5a, 0xa5]:
                await b.wr(1, 8, value)
                assert int(d.spi_cs.value) == (1 if cs else 2)
                await b.wr(1, 8, 0, error=True)
                await b.poll(1, 12, 1, 0)
                assert await b.rd(1, 8) == value
                assert int(d.spi_cs.value) == 3
                assert int(d.spi_sck.value) == (mode & 1)
                assert int(d.irq.value) & 2
                await b.wr(1, 12, 2)
                assert not (int(d.irq.value) & 2)
    await b.wr(1, 4, 0, error=True)
    await b.wr(1, 0, 1, strobe=1, error=True)
    await b.rd(1, 0x100, error=True)


@cocotb.test()
async def spacewire_packets_timecodes_and_disconnect(d):
    b = Bus(d)
    await b.reset()
    await b.wr(2, 0, 3)
    await b.wr(5, 0, 3)
    await b.poll(2, 4, 4, 4)
    await b.poll(5, 4, 4, 4)
    await b.wr(5, 20, 0x3f)
    # Exercise credit recycling beyond one 64-entry receiver FIFO.
    for i in range(160):
        v = ((i * 37) & 255) if i % 13 != 12 else 0x100
        await b.poll(2, 4, 8, 8)
        await b.wr(2, 12, v)
        await b.poll(5, 4, 16, 16)
        assert int(d.irq.value) & (1 << 5)
        assert await b.rd(5, 16) == v
    await b.rd(5, 16, error=True)
    # EEP control character in the reverse direction.
    await b.wr(5, 12, 0x101)
    await b.poll(2, 4, 16, 16)
    assert await b.rd(2, 16) == 0x101
    await b.wr(2, 28, 0)
    await b.poll(5, 24, 0x10, 0x10)
    await b.wr(5, 24, 0x10)
    await b.wr(2, 28, 1)
    await b.poll(5, 24, 0x10, 0x10)
    assert await b.rd(5, 32) == 1
    await b.wr(5, 24, 0x10)
    d.spw_disconnect_i.value = 1
    await b.poll(5, 24, 1, 1)
    d.spw_disconnect_i.value = 0
    await b.poll(5, 4, 4, 4)
    await b.wr(2, 0, 4)
    await b.poll(2, 4, 4, 0)


class I2CPeer:
    """Independent 7-bit addressed slave, sampled only on SCL/SDA pins."""
    def __init__(self, d, address=0x52, read_data=0xa6, ack=True):
        self.d, self.address, self.read_data, self.ack = d, address, read_data, ack
        self.prev_scl = self.prev_sda = 1
        self.state = 'idle'
        self.bits = self.byte = 0
        self.received = []
        self.starts = self.stops = 0
        self.reading = False
        self.ack_clock = False

    def tick(self):
        scl, sda = int(self.d.scl.value), int(self.d.sda.value)
        rising, falling = scl and not self.prev_scl, not scl and self.prev_scl
        start = scl and self.prev_scl and self.prev_sda and not sda
        stop = scl and self.prev_scl and not self.prev_sda and sda
        if start:
            self.state = 'address'; self.bits = self.byte = 0; self.starts += 1
        elif stop:
            self.state = 'idle'; self.stops += 1
            self.d.sda_hold_i.value = 0
        elif rising:
            if self.state in ('address', 'write'):
                self.byte = ((self.byte << 1) | sda) & 255
                self.bits += 1
                if self.bits == 8:
                    if self.state == 'address':
                        self.reading = bool(self.byte & 1)
                        self.accept = (self.byte >> 1) == self.address and self.ack
                    else:
                        self.received.append(self.byte)
                    self.state = 'ack'; self.ack_clock = False
            elif self.state == 'ack':
                self.ack_clock = True
            elif self.state == 'read':
                self.bits += 1
            elif self.state == 'master_ack':
                self.state = 'wait'
        elif falling:
            if self.state == 'ack':
                if not self.ack_clock:
                    self.d.sda_hold_i.value = self.accept
                else:
                    self.bits = self.byte = 0
                    self.state = ('read' if self.reading else 'write') if self.accept else 'wait'
                    self.d.sda_hold_i.value = (not bool(self.read_data & 0x80)) if self.state == 'read' else 0
            elif self.state == 'read':
                if self.bits == 8:
                    self.d.sda_hold_i.value = 0
                    self.state = 'master_ack'
                else:
                    self.d.sda_hold_i.value = not bool(self.read_data & (0x80 >> self.bits))
        self.prev_scl, self.prev_sda = scl, sda


@cocotb.test()
async def i2c_write_read_repeated_start_and_nack(d):
    b = Bus(d)
    await b.reset()
    peer = I2CPeer(d); b.peer = peer
    await b.wr(0, 4, 8)
    await b.wr(0, 8, 0x52)
    await b.wr(0, 20, 15)
    await b.wr(0, 16, 0x39)
    # WRITE+START without STOP, followed by a repeated-start READ+STOP.
    await b.wr(0, 12, 6)
    await b.poll(0, 0, 1, 0)
    assert peer.received == [0x39]
    assert peer.starts == 1 and peer.stops == 0
    assert (await b.rd(0, 24)) & 1
    await b.wr(0, 24, 15)
    await b.wr(0, 12, 13)
    await b.poll(0, 0, 1, 0)
    assert await b.rd(0, 16) == 0xa6
    assert peer.starts == 2 and peer.stops == 1
    await b.wr(0, 24, 15)
    await b.step(2)
    assert not int(d.irq.value) & 1
    await b.wr(0, 8, 0x53)  # unaddressed device NACK
    await b.wr(0, 12, 14)
    await b.poll(0, 0, 1, 0)
    assert (await b.rd(0, 24)) & 2
    assert int(d.irq.value) & 1
    await b.rd(0, 16, error=True)


@cocotb.test()
async def i2c_stretch_timeout_abort_and_invalid_access(d):
    b = Bus(d)
    await b.reset()
    peer = I2CPeer(d); b.peer = peer
    await b.wr(0, 4, 8)
    await b.wr(0, 8, 0x52)
    await b.wr(0, 16, 0x73)
    await b.wr(0, 12, 14)
    await b.step(100)
    d.scl_hold_i.value = 1
    await b.step(200)
    assert await b.rd(0, 0) & 1
    await b.wr(0, 12, 14, error=True)
    await b.wr(0, 4, 5, error=True)
    d.scl_hold_i.value = 0
    await b.poll(0, 0, 1, 0)
    assert peer.received == [0x73]
    await b.wr(0, 24, 15)
    d.scl_hold_i.value = 1
    await b.wr(0, 12, 14)
    await b.poll(0, 0, 1, 0, count=5000)
    assert (await b.rd(0, 24)) & 8
    d.scl_hold_i.value = 0
    await b.step(10)
    await b.wr(0, 12, 14)
    await b.wr(0, 12, 16)  # explicit abort
    assert not (await b.rd(0, 0) & 1)
    await b.step(10)
    assert int(d.scl.value) and int(d.sda.value)
    await b.wr(0, 4, 0, error=True)
    await b.rd(0, 0x100, error=True)
    await b.wr(0, 8, 0, strobe=1, error=True)


@cocotb.test()
async def can_two_node_standard_frame_and_byte_lanes(d):
    b = Bus(d)
    await b.reset()
    # SJA1000 PeliCAN: reset, extended register mode, accept all IDs,
    # 1 MHz nominal bit rate on the 50 MHz system clock (BRP=0, 25 TQ).
    for dev in (3, 4):
        await b.byte(dev, 0, 1)
        await b.byte(dev, 31, 0x80)
        await b.byte(dev, 6, 0)
        await b.byte(dev, 7, 0x7f)
        for addr in range(16, 20):
            await b.byte(dev, addr, 0)
        for addr in range(20, 24):
            await b.byte(dev, addr, 255)
        await b.byte(dev, 4, 1)
        await b.byte(dev, 0, 0)
    await b.step(1000)
    ident, payload = 0x321, [0x12, 0x34, 0x56]
    for addr, val in [(16, len(payload)), (17, ident >> 3), (18, (ident & 7) << 5)]:
        await b.byte(3, addr, val)
    for i, val in enumerate(payload):
        await b.byte(3, 19+i, val)
    await b.byte(3, 1, 1)
    for _ in range(4000):
        status = await b.byte(4, 2)
        if status & 1:
            break
    else:
        raise AssertionError(f'CAN frame not received: status {status:x}')
    assert int(d.irq.value) & (1 << 4)
    assert await b.byte(4, 16) & 15 == len(payload)
    assert await b.byte(4, 17) == ident >> 3
    assert await b.byte(4, 18) >> 5 == ident & 7
    assert [await b.byte(4, 19+i) for i in range(3)] == payload
    await b.byte(4, 1, 4)  # release RX buffer
    assert not (await b.byte(4, 2) & 1)
    await b.rd(3, 0, error=True)  # multi-byte accesses are not silently truncated
    await b.rd(3, 0x100, strobe=1, error=True)


@cocotb.test()
async def reset_aborts_serial_transactions(d):
    b = Bus(d)
    await b.reset()
    await b.wr(1, 4, 100)
    await b.wr(1, 8, 0x59)
    assert int(d.spi_cs.value) == 2
    await b.wr(0, 4, 100)
    await b.wr(0, 12, 14)
    await b.step(10)
    d.rst_ni.value = 0
    await b.step(8)
    assert int(d.spi_cs.value) == 3
    assert int(d.scl.value) == 1 and int(d.sda.value) == 1
    d.rst_ni.value = 1
    await b.step(8)
    assert await b.rd(1, 12) == 0
    assert await b.rd(0, 24) == 0
    assert not (await b.rd(0, 0) & 1)
    assert await b.rd(2, 0) == 4


@cocotb.test()
async def spacewire_credit_backpressure_preserves_order(d):
    b = Bus(d)
    await b.reset()
    await b.wr(2, 0, 3)
    await b.wr(5, 0, 3)
    await b.poll(2, 4, 4, 4)
    expected = []
    # Do not drain RX. Flow control must stall the transmitter without loss.
    for _ in range(300):
        if await b.rd(2, 4) & 8:
            val = len(expected) & 255
            await b.wr(2, 12, val)
            expected.append(val)
        await b.step(30)
    assert len(expected) >= 64 and len(expected) < 100
    await b.wr(2, 12, 0xde, error=True)
    received = []
    for _ in expected:
        await b.poll(5, 4, 16, 16)
        received.append(await b.rd(5, 16))
    assert received == expected
    await b.poll(2, 4, 8, 8)
    await b.wr(2, 12, 0x100)
    await b.poll(5, 4, 16, 16)
    assert await b.rd(5, 16) == 0x100
    await b.wr(2, 4, 0, error=True)
    await b.wr(2, 0, 0, strobe=1, error=True)
    await b.rd(2, 0x100, error=True)


@cocotb.test()
async def spi_continuous_chip_select_frames(d):
    b = Bus(d)
    await b.reset()
    for mode in range(4):
        control = mode | 16
        await b.wr(1, 0, control)
        for byte in (0x9f, 0, 0, 0, 0x5a):
            await b.wr(1, 8, byte)
            await b.poll(1, 12, 1, 0)
            assert await b.rd(1, 8) == byte
            assert int(d.spi_cs.value) == 2
            await b.step(30)
            assert int(d.spi_cs.value) == 2
        await b.wr(1, 0, control ^ 4, error=True)
        await b.wr(1, 0, mode)  # explicit CS release
        assert int(d.spi_cs.value) == 3
