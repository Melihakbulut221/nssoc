# SPDX-FileCopyrightText: 2026 Hasan Melih Akbulut
# SPDX-License-Identifier: Apache-2.0
import asyncio

import pytest
from golden.regmap_gen import ADDR
from pilotlink import PilotLink, encode_frame, pack_weights
from pilotlink.host import SerialTransport
from pilotlink.rp2040 import RP2040SPI, serve_once


class Registers:
    def __init__(self):
        self.values = {ADDR['STATUS']: 4, ADDR['CFG_NEUR']: 8, ADDR['CFG_AXON']: 8}
        self.frames, self.reply = [], None

    async def send_frame(self, frame):
        assert self.reply is None
        self.frames.append(frame)
        address, data = (frame[0] & 127) * 4, int.from_bytes(frame[1:], 'big')
        if frame[0] & 128:
            self.values[address] = data
        self.reply = b'\0' + self.values.get(address, 0).to_bytes(4, 'big')

    async def recv_frame(self):
        reply, self.reply = self.reply, None
        return reply


def link(registers=None, **kwargs):
    return PilotLink(registers or Registers(), neurons=8, axons=8, **kwargs)


@pytest.mark.parametrize('address', [-4, 1, 3, 0x200, 1.5])
def test_bad_addresses_are_rejected_before_transport(address):
    with pytest.raises(ValueError):
        encode_frame(False, address)


@pytest.mark.parametrize('data', [-1, 1 << 32, 2.5])
def test_bad_data_are_rejected(data):
    with pytest.raises(ValueError):
        encode_frame(True, 0, data)


def test_frame_endianness_and_signed_weight_order():
    assert encode_frame(True, 0x1fc, 0x89abcdef) == bytes.fromhex('ff89abcdef')
    assert encode_frame(False, 0x64) == bytes.fromhex('1900000000')
    assert pack_weights([[-8, -1, 0, 7]], 4) == [0x70f8]


@pytest.mark.parametrize('weights,neurons', [([[8]], 1), ([[-9]], 1), ([[0]], 2), ([], 8)])
def test_weight_shape_and_range(weights, neurons):
    with pytest.raises(ValueError):
        pack_weights(weights, neurons)


def test_register_and_weight_api_uses_physical_stride():
    async def run():
        regs = Registers(); p = link(regs)
        await p.write(ADDR['SCRATCH'], 0xa5a51234)
        assert await p.read(ADDR['SCRATCH']) == 0xa5a51234
        assert await p.geometry() == (8, 8)
        await p.load_weights([[-1] * 8, [7] * 8], 8)
        assert regs.values[ADDR['W_DATA_LO']] == 0xffffffff
        assert regs.values[ADDR['W_DATA_HI']] == 0x77777777
        before = len(regs.frames)
        with pytest.raises(ValueError):
            await p.load_weights([[0] * 8] * 8, 8, first_word=1)
        assert len(regs.frames) == before
        # Active neuron count does not change the elaborated weight stride.
        regs.values[ADDR['CFG_NEUR']] = 3
        with pytest.raises(ValueError):
            await p.load_weights([[0] * 3], 3)
    asyncio.run(run())


def test_busy_timeout_and_enabled_configuration_fail_without_writes():
    async def run():
        regs = Registers(); p = link(regs, poll_limit=3)
        regs.values[ADDR['STATUS']] = 1
        with pytest.raises(TimeoutError):
            await p.configure(threshold=12)
        assert len(regs.frames) == 4  # CTRL + exactly three status reads
        assert not any(f[0] & 128 for f in regs.frames)
        regs.values[ADDR['CTRL']] = 1
        with pytest.raises(RuntimeError):
            await p.configure(threshold=12)
        assert not any(f[0] & 128 for f in regs.frames)
    asyncio.run(run())


def test_short_reply_is_not_retried():
    async def run():
        class Short(Registers):
            async def recv_frame(self): return b'\0'
        regs = Short(); p = link(regs)
        with pytest.raises(IOError):
            await p.write(ADDR['SCRATCH'], 123)
        with pytest.raises(IOError):
            await p.read(ADDR['ID'])
        assert len(regs.frames) == 1
    asyncio.run(run())


def test_concurrent_operation_is_rejected():
    async def run():
        entered, release = asyncio.Event(), asyncio.Event()
        class Paused(Registers):
            async def send_frame(self, frame):
                await super().send_frame(frame); entered.set(); await release.wait()
        p = link(Paused())
        first = asyncio.create_task(p.read(ADDR['ID']))
        await entered.wait()
        with pytest.raises(RuntimeError):
            await p.write(ADDR['SCRATCH'], 1)
        release.set(); await first
    asyncio.run(run())


class Serial:
    timeout = write_timeout = 1
    def __init__(self, response=b'\0\x12\x34\x56\x78'):
        self.response, self.writes = response, []
    def write(self, frame): self.writes.append(frame); return len(frame)
    def read(self, size): assert size == 5; return self.response


def test_serial_reply_and_poisoned_timeout():
    async def run():
        port = Serial(); p = PilotLink(SerialTransport(port), neurons=8, axons=8)
        assert await p.read(ADDR['ID']) == 0x12345678
        port.response = b'\0'
        with pytest.raises(TimeoutError): await p.read(ADDR['ID'])
        with pytest.raises(IOError): await p.read(ADDR['ID'])
        assert len(port.writes) == 2  # third call must never send
    asyncio.run(run())


@pytest.mark.parametrize('timeout', [None, 0, -1, float('inf'), float('nan')])
def test_serial_requires_bounded_io(timeout):
    port = Serial(); port.timeout = timeout
    with pytest.raises(ValueError): SerialTransport(port)


def test_rp2040_full_duplex_cs_gaps_and_exception_cleanup():
    events = []
    class SPI:
        def write_readinto(self, tx, rx):
            events.append(('exchange', bytes(tx))); rx[:] = b'\0\x12\x34\x56\x78'
    spi = RP2040SPI(SPI(), lambda v: events.append(('cs', v)),
                    serial_hz=100000, system_hz=1000000,
                    sleep_us=lambda us: events.append(('wait', us)))
    assert spi.exchange(b'12345') == b'\0\x12\x34\x56\x78'
    assert events == [('cs', 1), ('wait', 10), ('cs', 0), ('wait', 10),
                      ('exchange', b'12345'), ('wait', 10), ('cs', 1), ('wait', 10)]
    class Broken:
        def write_readinto(self, tx, rx): raise OSError('SPI error')
    spi.spi = Broken()
    with pytest.raises(OSError): spi.exchange(b'12345')
    assert events[-2:] == [('cs', 1), ('wait', 10)]


def test_bridge_refuses_partial_request_before_spi():
    class UART:
        def any(self): return 2
        def read(self, size): return b'12'
    class SPI:
        def exchange(self, frame): raise AssertionError('must not clock incomplete command')
    with pytest.raises(OSError): serve_once(UART(), SPI())


def test_disabled_event_submission_is_rejected_without_queue_write():
    async def run():
        regs = Registers(); p = link(regs)
        with pytest.raises(RuntimeError): await p.run_frames([[0]])
        assert not any(f[0] & 128 for f in regs.frames)
    asyncio.run(run())


def test_state_clear_verifies_every_address_pattern_and_zero():
    async def run():
        regs = Registers(); p = link(regs)
        await p.state_clear()
        writes = [(int(f[0] & 127) * 4, int.from_bytes(f[1:], 'big'))
                  for f in regs.frames if f[0] & 128]
        assert writes[0] == (ADDR['CTRL'], 2)
        assert writes[1:] == [(a, v) for n in range(8) for a, v in
                             [(ADDR['N_ADDR'], n), (ADDR['N_DATA'], 0xfffff), (ADDR['N_DATA'], 0)]]
    asyncio.run(run())
