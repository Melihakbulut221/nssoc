# SPDX-FileCopyrightText: 2026 Hasan Melih Akbulut
# SPDX-License-Identifier: Apache-2.0
"""Public-port ACK/NAK byte/CRC oracle and packet arbitration controls."""
import random

import cocotb
from cocotb.triggers import Timer


def expected_dllp(nak, sequence):
    """Normal polynomial and explicit spec bit mapping, unlike reflected RTL."""
    data = bytes((0x10 if nak else 0, 0, sequence >> 8, sequence & 255))
    normal = 0xffff
    for octet in data:
        for bit in range(8):
            feedback = ((normal >> 15) ^ (octet >> bit)) & 1
            normal = ((normal << 1) & 0xffff) ^ (0x100b if feedback else 0)
    normal ^= 0xffff
    field = 0
    for bit in range(16):
        field |= ((normal >> bit) & 1) << ((bit & 8) + 7 - (bit & 7))
    return data + field.to_bytes(2, 'big')


class Driver:
    def __init__(self, dut):
        self.dut = dut
        self.frames = []
        self.partial = []
        self.kind = None
        self.held = None

    async def tick(self, reset=False, ready=True, ack=None, tlp=None):
        d = self.dut
        d.clk_i.value = 0
        d.rst_ni.value = int(not reset)
        d.tx_ready_i.value = int(ready)
        d.ack_valid_i.value = int(ack is not None)
        d.ack_nak_i.value, d.ack_sequence_i.value = ack or (0, 0)
        d.tlp_valid_i.value = int(tlp is not None)
        d.tlp_data_i.value, d.tlp_sop_i.value, d.tlp_eop_i.value = tlp or (0, 0, 0)
        await Timer(5, unit='ns')
        valid = int(d.tx_valid_o.value)
        value = tuple(int(getattr(d, name).value) for name in
                      ('tx_data_o', 'tx_sop_o', 'tx_eop_o', 'tx_dllp_o'))
        ack_ready, tlp_ready = int(d.ack_ready_o.value), int(d.tlp_ready_o.value)
        if reset:
            assert not valid and not ack_ready and not tlp_ready
            self.partial, self.held, self.kind = [], None, None
        else:
            if self.held is not None:
                assert valid and value == self.held, 'Output changed under backpressure'
            self.held = value if valid and not ready else None
            if valid and ready:
                data, sop, eop, kind = value
                assert bool(sop) == (not self.partial), 'Frame split/interleaving or missing SOP'
                if sop:
                    self.kind = kind
                assert kind == self.kind, 'Packet type changed inside frame'
                self.partial.append(data)
                if eop:
                    self.frames.append((kind, bytes(self.partial)))
                    self.partial = []
        d.clk_i.value = 1
        await Timer(5, unit='ns')
        return ack_ready, tlp_ready

    async def reset(self):
        for _ in range(3):
            await self.tick(reset=True)
        await self.tick()

    async def dllp(self, nak, seq, randomizer=None):
        target = len(self.frames) + 1
        for _ in range(100):
            ar, _ = await self.tick(ack=(nak, seq), ready=False)
            if ar:
                break
        else:
            raise AssertionError('ACK request blocked indefinitely')
        for _ in range(200):
            ready = True if randomizer is None else randomizer.randrange(4) != 0
            await self.tick(ready=ready)
            if len(self.frames) == target:
                assert self.frames[-1] == (1, expected_dllp(nak, seq))
                return
        raise AssertionError('DLLP did not finish')


@cocotb.test()
async def all_ack_nak_sequence_encodings(dut):
    d = Driver(dut)
    await d.reset()
    rng = random.Random(0xd008)
    for nak in (0, 1):
        for seq in range(4096):
            await d.dllp(nak, seq, rng if seq % 17 == 0 else None)
    assert len(d.frames) == 8192


@cocotb.test()
async def simultaneous_streams_remain_framed_ordered_and_fair(dut):
    d = Driver(dut)
    await d.reset()
    rng = random.Random(701)
    packets = [bytes(rng.randrange(256) for _ in range(8 + i % 27)) for i in range(90)]
    acknowledgments = [(i % 2, (i * 257) & 4095) for i in range(90)]
    ar, _ = await d.tick(ack=acknowledgments[0], ready=False)
    assert ar
    ai, pi, bi = 1, 0, 0
    offered = False
    for _ in range(20000):
        if pi < len(packets) and not offered:
            offered = rng.randrange(4) != 0
        tlp = None if not offered else (packets[pi][bi], bi == 0, bi == len(packets[pi]) - 1)
        ack = acknowledgments[ai] if ai < len(acknowledgments) else None
        ar, tr = await d.tick(ready=rng.randrange(3) != 0, ack=ack, tlp=tlp)
        if ack is not None and ar:
            ai += 1
        if tlp is not None and tr:
            bi += 1
            offered = False
            if bi == len(packets[pi]):
                pi, bi = pi + 1, 0
        if len(d.frames) == 180:
            break
    assert len(d.frames) == 180
    assert [data for kind, data in d.frames if kind] == [expected_dllp(*a) for a in acknowledgments]
    assert [data for kind, data in d.frames if not kind] == packets
    # Sources remain saturated after initial dispatch: no starvation of either
    # stream. Bubbles within a selected packet cannot permit interleaving.
    assert [kind for kind, _ in d.frames[:160]] == [1, 0] * 80


@cocotb.test()
async def first_stalled_tlp_cannot_be_preempted_by_later_ack(dut):
    d = Driver(dut)
    await d.reset()
    first = (0x91, 1, 0)
    await d.tick(ready=False, tlp=first)
    ar, _ = await d.tick(ready=False, ack=(1, 0xabc), tlp=first)
    assert ar
    for _ in range(7):
        await d.tick(ready=False, tlp=first)
    await d.tick(tlp=first)
    for _ in range(5):
        await d.tick()  # selected source bubbles, queued DLLP must wait
    assert d.frames == []
    await d.tick(tlp=(0x42, 0, 1))
    for _ in range(10):
        await d.tick()
    assert d.frames == [(0, b'\x91\x42'), (1, expected_dllp(1, 0xabc))]


@cocotb.test()
async def reset_flushes_every_dllp_byte_and_selected_tlp(dut):
    d = Driver(dut)
    await d.reset()
    for taken in range(6):
        ar, _ = await d.tick(ack=(1, 0xfff), ready=False)
        assert ar
        for _ in range(taken):
            await d.tick()
        await d.tick(ready=False)
        before = len(d.frames)
        await d.reset()
        assert len(d.frames) == before
        await d.dllp(0, taken)
    await d.tick(tlp=(0x12, 1, 0))
    await d.tick(tlp=(0x34, 0, 0), ready=False)
    await d.reset()
    await d.tick(tlp=(0x55, 1, 1))
    await d.dllp(1, 4095)
    assert d.frames[-2:] == [(0, b'\x55'), (1, expected_dllp(1, 4095))]
