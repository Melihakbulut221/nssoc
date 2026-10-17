# SPDX-FileCopyrightText: 2026 Hasan Melih Akbulut
# SPDX-License-Identifier: Apache-2.0
"""One 40-bit mode-0 transaction per register; all offsets are generated.

Public operations reject overlapping use of a link, including multi-register
weight/configuration operations. A timeout is not retried: queue reads pop and
writes may already have committed. Re-establish transport alignment explicitly.
"""
from contextlib import contextmanager
from typing import Protocol

from golden.regmap_gen import ADDR, FIELDS


class Transport(Protocol):
    async def send_frame(self, frame: bytes) -> None: ...
    async def recv_frame(self) -> bytes: ...


def encode_frame(write: bool, address: int, data: int = 0) -> bytes:
    if not isinstance(address, int) or address < 0 or address > 0x1fc or address % 4:
        raise ValueError('register address must be aligned in 0x000..0x1fc')
    if not isinstance(data, int) or not 0 <= data <= 0xffffffff:
        raise ValueError('register data must be an unsigned 32-bit integer')
    return bytes([(int(bool(write)) << 7) | (address >> 2)]) + data.to_bytes(4, 'big')


def pack_weights(weights, neurons: int) -> list:
    weights = [list(row) for row in weights]
    if type(neurons) is not int or not 1 <= neurons <= 512 or not weights:
        raise ValueError('nonempty axon-major matrix and 1..512 neurons required')
    if any(len(row) != neurons for row in weights):
        raise ValueError('weight row length does not match neuron count')
    flat = [w for row in weights for w in row]
    if any(not isinstance(w, int) or not -8 <= w <= 7 for w in flat):
        raise ValueError('weights must be signed four-bit integers')
    return [sum((w & 15) << (4 * k) for k, w in enumerate(flat[i:i + 16]))
            for i in range(0, len(flat), 16)]


class PilotLink:
    def __init__(self, transport: Transport, *, neurons: int, axons: int, poll_limit: int = 400):
        if not isinstance(poll_limit, int) or poll_limit < 1:
            raise ValueError('poll_limit must be positive')
        if type(neurons) is not int or type(axons) is not int or not 1 <= neurons <= 512 or not 1 <= axons <= 512:
            raise ValueError('explicit elaborated geometry must be within 1..512')
        self.neurons, self.axons = neurons, axons
        self.transport = transport
        self.poll_limit = poll_limit
        self._active = False
        self._failed = False

    @contextmanager
    def _operation(self):
        if self._failed:
            raise IOError('link alignment lost; reset transport and create a new link')
        if self._active:
            raise RuntimeError('concurrent operations on one PilotLink are unsupported')
        self._active = True
        try:
            yield
        finally:
            self._active = False

    async def _frame(self, write, address, data=0):
        frame = encode_frame(write, address, data)
        try:
            await self.transport.send_frame(frame)
            reply = await self.transport.recv_frame()
            if len(reply) != 5:
                raise IOError('incomplete serial frame; alignment must be re-established')
            return int.from_bytes(reply[1:], 'big')
        except BaseException:
            self._failed = True
            raise

    async def read(self, address: int) -> int:
        with self._operation():
            return await self._frame(False, address)

    async def write(self, address: int, data: int) -> None:
        with self._operation():
            await self._frame(True, address, data)

    async def geometry(self):
        with self._operation():
            return (await self._frame(False, ADDR['CFG_NEUR']),
                    await self._frame(False, ADDR['CFG_AXON']))

    async def _idle(self):
        for _ in range(self.poll_limit):
            status = await self._frame(False, ADDR['STATUS'])
            if not status & (1 << FIELDS['STATUS']['BUSY']):
                return
        raise TimeoutError('pilot did not become idle within the poll bound')

    async def _disabled(self):
        if await self._frame(False, ADDR['CTRL']) & (1 << FIELDS['CTRL']['EN']):
            raise RuntimeError('disable the pilot before changing configuration or weights')
        await self._idle()

    async def state_clear(self):
        with self._operation():
            await self._frame(True, ADDR['CTRL'], 1 << FIELDS['CTRL']['STATE_CLR'])
            await self._idle()
            # Establish each complete state/check word through the serial debug
            # registers. An all-zero write alone can retain X in mapped gates.
            for neuron in range(self.neurons):
                await self._frame(True, ADDR['N_ADDR'], neuron)
                if await self._frame(False, ADDR['N_ADDR']) != neuron:
                    raise IOError('neuron address readback failed')
                for pattern in (0xfffff, 0):
                    await self._frame(True, ADDR['N_DATA'], pattern)
                    if await self._frame(False, ADDR['N_DATA']) != pattern:
                        raise IOError('neuron state readback failed')

    async def configure(self, *, threshold, v_reset=0, leak_shift=0,
                        syn_shift=0, refractory=0, leak_enabled=True, tile_offset=0):
        values = (threshold, v_reset, leak_shift, syn_shift, refractory, tile_offset)
        if any(not isinstance(x, int) for x in values):
            raise ValueError('configuration values must be integers')
        if not (1 <= threshold <= 32767 and -32768 <= v_reset < threshold
                and 0 <= leak_shift <= 15 and 0 <= syn_shift <= 7
                and 0 <= refractory <= 15 and 0 <= tile_offset <= 1023):
            raise ValueError('configuration outside the pilot register contract')
        with self._operation():
            await self._disabled()
            for name, value in [('CFG_THRESH', threshold), ('CFG_VRESET', v_reset & 65535),
                                ('CFG_LEAK', leak_shift), ('CFG_SYNSHIFT', syn_shift),
                                ('CFG_REFR', refractory), ('CFG_FLAGS', int(bool(leak_enabled)) << FIELDS['CFG_FLAGS']['LEAK_EN']),
                                ('PASS_TILE_OFF', tile_offset)]:
                await self._frame(True, ADDR[name], value)

    async def load_weights(self, weights, neurons: int, *, first_word=0):
        words = pack_weights(weights, neurons)
        if not isinstance(first_word, int) or first_word < 0:
            raise ValueError('first_word must be nonnegative')
        if neurons != self.neurons or first_word * 16 + len(words) * 16 > ((self.neurons * self.axons + 15) // 16) * 16:
            raise ValueError('weight block exceeds the explicitly supplied physical geometry')
        with self._operation():
            await self._disabled()
            await self._frame(True, ADDR['W_ADDR'], first_word)
            for word in words:
                await self._frame(True, ADDR['W_DATA_LO'], word & 0xffffffff)
                await self._frame(True, ADDR['W_DATA_HI'], word >> 32)

    async def enable(self, *, scrub=True):
        with self._operation():
            await self._frame(True, ADDR['CTRL'], (1 << FIELDS['CTRL']['EN']) |
                              (int(bool(scrub)) << FIELDS['CTRL']['SCRUB_EN']))

    async def _drain(self):
        events: list[int] = []
        for _ in range(self.poll_limit):
            status = await self._frame(False, ADDR['STATUS'])
            if not status & (1 << FIELDS['STATUS']['BUSY']) and status & (1 << FIELDS['STATUS']['EVQ_OUT_EMPTY']):
                return events
            word = await self._frame(False, ADDR['EVQ_OUT'])
            if word & (1 << 31):
                events.append(word & 65535)
        raise TimeoutError('pilot output did not drain within the poll bound')

    async def drain(self):
        with self._operation():
            return await self._drain()

    async def run_frames(self, frames):
        frames = [list(frame) for frame in frames]
        if any(not isinstance(axon, int) or not 0 <= axon < (1 << 14)
               for frame in frames for axon in frame):
            raise ValueError('axon indices must fit the 14-bit event payload')
        with self._operation():
            if not await self._frame(False, ADDR['CTRL']) & (1 << FIELDS['CTRL']['EN']):
                raise RuntimeError('enable the pilot before running events')
            axons = await self._frame(False, ADDR['CFG_AXON'])
            if any(axon >= axons for frame in frames for axon in frame):
                raise ValueError('axon index exceeds configured geometry')
            output = []
            for frame in frames:
                events = []
                for axon in frame:
                    await self._frame(True, ADDR['EVQ_IN'], axon)
                    events.extend(await self._drain())
                await self._frame(True, ADDR['EVQ_IN'], 1 << 14)  # TICK, docs/10 E8
                events.extend(await self._drain())
                output.append(events)
            return output
