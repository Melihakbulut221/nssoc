# SPDX-FileCopyrightText: 2026 Hasan Melih Akbulut
# SPDX-License-Identifier: Apache-2.0
"""Pin-level protocol tests through APB; no force of internal RTL state."""
from peripheral_registers import SPI, SPW, I2C
import cocotb
import os
from cocotb.triggers import Timer

FULL_PROFILE = os.environ.get('SOC_INTERFACE_PROFILE', 'base') == 'full'


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
                     'sda_hold_i', 'spw_disconnect_i', 'spi_external_i',
                     'spi_miso_i'):
            getattr(self.d, name).value = 0
        await self.step(8)
        self.d.rst_ni.value = 1
        await self.step(8)
        assert bool(int(self.d.lgpl_profile_o.value)) == FULL_PROFILE

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
            await b.wr(1, SPI['CTRL'], mode | (cs << 2) | 8)
            await b.wr(1, SPI['DIV'], 3)
            for value in [0, 255, 0x81, 0x5a, 0xa5]:
                await b.wr(1, SPI['DATA'], value)
                assert int(d.spi_cs.value) == (1 if cs else 2)
                await b.wr(1, SPI['DATA'], 0, error=True)
                await b.poll(1, SPI['STATUS'], 1, 0)
                assert await b.rd(1, SPI['DATA']) == value
                assert int(d.spi_cs.value) == 3
                assert int(d.spi_sck.value) == (mode & 1)
                assert int(d.irq.value) & 2
                await b.wr(1, SPI['STATUS'], 2)
                assert not (int(d.irq.value) & 2)
    await b.wr(1, SPI['DIV'], 0, error=True)
    await b.wr(1, SPI['CTRL'], 1, strobe=1, error=True)
    await b.rd(1, 0x100, error=True)


@cocotb.test(skip=not FULL_PROFILE)
async def spacewire_packets_timecodes_and_disconnect(d):
    b = Bus(d)
    await b.reset()
    await b.wr(2, SPW['CTRL'], 3)
    await b.wr(5, SPW['CTRL'], 3)
    await b.poll(2, SPW['STATUS'], 4, 4)
    await b.poll(5, SPW['STATUS'], 4, 4)
    await b.wr(5, SPW['IRQEN'], 0x3f)
    # Exercise credit recycling beyond one 64-entry receiver FIFO.
    for i in range(160):
        v = ((i * 37) & 255) if i % 13 != 12 else 0x100
        await b.poll(2, SPW['STATUS'], 8, 8)
        await b.wr(2, SPW['TX'], v)
        await b.poll(5, SPW['STATUS'], 16, 16)
        assert int(d.irq.value) & (1 << 5)
        assert await b.rd(5, SPW['RX']) == v
    await b.rd(5, SPW['RX'], error=True)
    # EEP control character in the reverse direction.
    await b.wr(5, SPW['TX'], 0x101)
    await b.poll(2, SPW['STATUS'], 16, 16)
    assert await b.rd(2, SPW['RX']) == 0x101
    await b.wr(2, SPW['TIME_TX'], 0)
    await b.poll(5, SPW['EVENTS'], 0x10, 0x10)
    await b.wr(5, SPW['EVENTS'], 0x10)
    await b.wr(2, SPW['TIME_TX'], 1)
    await b.poll(5, SPW['EVENTS'], 0x10, 0x10)
    assert await b.rd(5, SPW['TIME_RX']) == 1
    await b.wr(5, SPW['EVENTS'], 0x10)
    d.spw_disconnect_i.value = 1
    await b.poll(5, SPW['EVENTS'], 1, 1)
    d.spw_disconnect_i.value = 0
    await b.poll(5, SPW['STATUS'], 4, 4)
    await b.wr(2, SPW['CTRL'], 4)
    await b.poll(2, SPW['STATUS'], 4, 0)


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
        self.master_acks = []

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
                self.master_acks.append(not bool(sda))
                self.state = 'next_read' if not sda else 'wait'
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
            elif self.state == 'next_read':
                self.bits = 0
                self.state = 'read'
                self.d.sda_hold_i.value = not bool(self.read_data & 0x80)
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


@cocotb.test(skip=not FULL_PROFILE)
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
    await b.rd(3, I2C['STATUS'], error=True)  # multi-byte accesses are not silently truncated
    await b.rd(3, 0x100, strobe=1, error=True)


@cocotb.test()
async def reset_aborts_serial_transactions(d):
    b = Bus(d)
    await b.reset()
    await b.wr(1, SPI['DIV'], 100)
    await b.wr(1, SPI['DATA'], 0x59)
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
    assert await b.rd(1, SPI['STATUS']) == 0
    assert await b.rd(0, 24) == 0
    assert not (await b.rd(0, 0) & 1)
    if FULL_PROFILE:
        assert await b.rd(2, SPW['CTRL']) == 4
    else:
        await b.rd(2, SPW['CTRL'], error=True)


@cocotb.test(skip=FULL_PROFILE)
async def disabled_optional_slots_return_errors(d):
    b = Bus(d)
    await b.reset()
    for dev in (2, 3, 4, 5):
        await b.rd(dev, 0, error=True)
        await b.wr(dev, 0, 0xffffffff, error=True)
    assert int(d.irq.value) & 0x3c == 0
    assert int(d.can_bus.value) == 1


@cocotb.test(skip=not FULL_PROFILE)
async def spacewire_credit_backpressure_preserves_order(d):
    b = Bus(d)
    await b.reset()
    await b.wr(2, SPW['CTRL'], 3)
    await b.wr(5, SPW['CTRL'], 3)
    await b.poll(2, SPW['STATUS'], 4, 4)
    expected = []
    # Do not drain RX. Flow control must stall the transmitter without loss.
    for _ in range(300):
        if await b.rd(2, SPW['STATUS']) & 8:
            val = len(expected) & 255
            await b.wr(2, SPW['TX'], val)
            expected.append(val)
        await b.step(30)
    assert len(expected) >= 64 and len(expected) < 100
    await b.wr(2, SPW['TX'], 0xde, error=True)
    received = []
    for _ in expected:
        await b.poll(5, SPW['STATUS'], 16, 16)
        received.append(await b.rd(5, SPW['RX']))
    assert received == expected
    await b.poll(2, SPW['STATUS'], 8, 8)
    await b.wr(2, SPW['TX'], 0x100)
    await b.poll(5, SPW['STATUS'], 16, 16)
    assert await b.rd(5, SPW['RX']) == 0x100
    await b.wr(2, SPW['STATUS'], 0, error=True)
    await b.wr(2, SPW['CTRL'], 0, strobe=1, error=True)
    await b.rd(2, 0x100, error=True)


@cocotb.test()
async def spi_continuous_chip_select_frames(d):
    b = Bus(d)
    await b.reset()
    for mode in range(4):
        control = mode | 16
        await b.wr(1, SPI['CTRL'], control)
        for byte in (0x9f, 0, 0, 0, 0x5a):
            await b.wr(1, SPI['DATA'], byte)
            await b.poll(1, SPI['STATUS'], 1, 0)
            assert await b.rd(1, SPI['DATA']) == byte
            assert int(d.spi_cs.value) == 2
            await b.step(30)
            assert int(d.spi_cs.value) == 2
        await b.wr(1, SPI['CTRL'], control ^ 4, error=True)
        await b.wr(1, SPI['CTRL'], mode)  # explicit CS release
        assert int(d.spi_cs.value) == 3


class SPIPeer:
    """Exchange unrelated data and check the physical sampling edge."""
    def __init__(self, d, cpol, cpha, response):
        self.d, self.cpol, self.cpha, self.response = d, cpol, cpha, response
        self.prev_sck, self.prev_cs = cpol, 3
        self.prev_mosi = 0
        self.sampled = []
        self.edges = 0
        self.frames = 0

    def tick(self):
        sck, cs, mosi = (int(self.d.spi_sck.value), int(self.d.spi_cs.value),
                         int(self.d.spi_mosi.value))
        if cs != 3 and self.prev_cs == 3:
            assert sck == self.cpol
            self.d.spi_miso_i.value = (self.response >> 7) & 1
        elif cs == 3 and self.prev_cs != 3:
            assert self.edges == 16 and len(self.sampled) == 8
            assert sck == self.cpol
            self.frames += 1
        if cs != 3 and sck != self.prev_sck:
            self.edges += 1
            leading = sck != self.cpol
            if leading != bool(self.cpha):
                assert mosi == self.prev_mosi, 'MOSI changed at the sampling edge'
                self.sampled.append(mosi)
            else:
                bit = 7 - len(self.sampled)
                self.d.spi_miso_i.value = (self.response >> bit) & 1 if bit >= 0 else 0
        self.prev_sck, self.prev_cs, self.prev_mosi = sck, cs, mosi


@cocotb.test()
async def spi_independent_peer_checks_edges(d):
    b = Bus(d)
    await b.reset()
    d.spi_external_i.value = 1
    for cpol in (0, 1):
        for cpha in (0, 1):
            for cs in (0, 1):
                await b.wr(1, SPI['CTRL'], cpol | (cpha << 1) | (cs << 2))
                await b.wr(1, SPI['DIV'], 2)  # fastest permitted half-period
                for tx, rx in ((0x96, 0x3c), (0x00, 0xff), (0xff, 0x00)):
                    peer = SPIPeer(d, cpol, cpha, rx)
                    b.peer = peer
                    await b.wr(1, SPI['DATA'], tx)
                    await b.poll(1, SPI['STATUS'], 1, 0)
                    assert await b.rd(1, SPI['DATA']) == rx
                    assert peer.sampled == [(tx >> bit) & 1 for bit in range(7, -1, -1)]
                    assert peer.frames == 1
                    b.peer = None


@cocotb.test()
async def i2c_burst_read_write_and_final_nack(d):
    b = Bus(d)
    await b.reset()
    peer = I2CPeer(d, read_data=0x69)
    b.peer = peer
    await b.wr(0, 4, 8)
    await b.wr(0, 8, 0x52)
    payload = [0x19, 0x80, 0xff, 0x00]
    for i, value in enumerate(payload):
        await b.wr(0, 16, value)
        await b.wr(0, 12, 2 | (4 if i == 0 else 0))
        await b.poll(0, 0, 1, 0)
    assert peer.received == payload
    assert peer.starts == 1 and peer.stops == 0
    for i in range(4):
        await b.wr(0, 12, 1 | (4 if i == 0 else 0) | (8 if i == 3 else 0))
        await b.poll(0, 0, 1, 0)
        assert await b.rd(0, 16) == 0x69
    assert peer.starts == 2 and peer.stops == 1
    assert peer.master_acks == [True, True, True, False]
    assert not (await b.rd(0, 24) & 10), 'unexpected NACK or timeout'


@cocotb.test(skip=not FULL_PROFILE)
async def can_extended_id_eight_bytes_and_remote_frame(d):
    b = Bus(d)
    await b.reset()
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
    ident = 0x1abcde5
    id_bytes = [(ident >> 21) & 255, (ident >> 13) & 255,
                (ident >> 5) & 255, (ident & 31) << 3]
    payload = [0x00, 0xff, 0x55, 0xaa, 0x01, 0x80, 0x3c, 0xc3]
    # Reverse direction for RTR, verifying both instances transmit and receive.
    for tx, rx, remote in ((3, 4, False), (4, 3, True)):
        info = 0x88 | (0x40 if remote else 0)
        await b.byte(tx, 16, info)
        for i, value in enumerate(id_bytes):
            await b.byte(tx, 17+i, value)
        if not remote:
            for i, value in enumerate(payload):
                await b.byte(tx, 21+i, value)
        await b.byte(tx, 1, 1)
        for _ in range(8000):
            if await b.byte(rx, 2) & 1:
                break
        else:
            raise AssertionError('extended CAN frame not received')
        assert await b.byte(rx, 16) == info
        assert [await b.byte(rx, 17+i) for i in range(4)] == id_bytes
        if not remote:
            assert [await b.byte(rx, 21+i) for i in range(8)] == payload
        assert int(d.irq.value) & (1 << rx)
        await b.byte(rx, 1, 4)
        assert not (await b.byte(rx, 2) & 1)
        await b.step(500)
