# SPDX-FileCopyrightText: 2026 Hasan Melih Akbulut
# SPDX-License-Identifier: Apache-2.0
"""Actual nonstop raw words, independent serial scrambler/STP and packet oracle."""

from collections import deque
import zlib

import cocotb
from cocotb.triggers import Timer
from test_soc_pcie_gen3_packet_duplex import encoded_words, frame, packet


class Receiver:
    def __init__(self, d):
        self.d = d
        self.expected = deque()
        self.received = bytearray()
        self.completed = self.good = self.nullified = self.errors = self.ends = 0
        self.held = None

    async def cycle(self, word=0, ready=True, start=False, reset=False, flush=False, abort=False):
        d = self.d
        d.clk_i.value = 0
        d.rst_ni.value = int(not reset)
        d.flush_i.value = int(flush)
        d.stream_start_i.value = int(start)
        d.stream_abort_i.value = int(abort)
        d.word_i.value = word
        d.ready_i.value = int(ready)
        await Timer(2, unit="ns")
        valid = int(d.valid_o.value)
        if reset or flush or start or abort:
            assert not valid
            self.held = None
        elif valid:
            beat = tuple(int(getattr(d, n).value) for n in ("data_o", "sop_o", "eop_o", "dllp_o"))
            if self.held is not None:
                assert beat == self.held, "stalled packet byte changed"
            self.held = beat if not ready else None
            if ready:
                data, sop, eop, dllp = beat
                assert self.expected, "unexpected or nullified packet output"
                expected, kind = self.expected[0]
                assert bool(sop) == (len(self.received) == 0)
                assert dllp == kind
                self.received.append(data)
                assert len(self.received) <= len(expected)
                assert bool(eop) == (len(self.received) == len(expected))
                if eop:
                    assert bytes(self.received) == expected
                    self.expected.popleft()
                    self.received.clear()
                    self.completed += 1
        elif self.held is not None:
            assert int(d.overflow_o.value) or int(d.halted_o.value), "held packet vanished"
            self.held = None
        d.clk_i.value = 1
        await Timer(2, unit="ns")
        self.good += int(d.packet_good_o.value)
        self.nullified += int(d.packet_nullified_o.value)
        self.errors += int(d.framing_error_o.value)
        self.ends += int(d.stream_end_o.value)

    async def begin(self):
        await self.cycle(reset=True)
        await self.cycle(start=True)

    async def stream(self, data, ready=lambda n: True, bad_header=False):
        for n, word in enumerate(encoded_words(data, bad_header=bad_header)):
            await self.cycle(word, ready=ready(n))


def zero_payload_packet(sequence):
    data = packet(sequence, payload=128)[:-4]
    data = data[:14] + bytes(128)
    return data + zlib.crc32(data).to_bytes(4, "little")


@cocotb.test()
async def continuous_idle_and_stalled_packet_output(d):
    r = Receiver(d)
    await r.begin()
    await r.stream(bytes(64 * 256))
    assert r.errors == 0 and not int(d.overflow_o.value) and int(d.active_o.value)
    # Restart the external epoch and therefore the independent bit-serial seed.
    await r.cycle(start=True)
    data = packet(0x321, payload=128)
    r.expected.append((data, False))
    await r.stream(frame(data) + bytes(64 * 160), ready=lambda n: n > 320)
    assert r.completed == r.good == 1 and not r.expected
    assert r.errors == 0 and not int(d.overflow_o.value)


@cocotb.test()
async def zero_tlp_payload_is_not_idle_and_nullification_is_preserved(d):
    r = Receiver(d)
    await r.begin()
    data = zero_payload_packet(0x841)
    r.expected.append((data, False))
    # Place STP at the last DWORD of the first block: the middle all-zero
    # payload block MUST remain owned by TLP, never bypassed as IDL.
    await r.stream(bytes(60) + frame(data) + bytes(64 * 96))
    assert r.completed == 1 and r.errors == 0 and not int(d.overflow_o.value)
    await r.cycle(start=True)
    await r.stream(frame(packet(0xabc), nullify=True) + bytes(64 * 32))
    assert r.nullified == 1 and r.completed == 1 and r.errors == 0


@cocotb.test()
async def raw_header_error_and_dense_packet_overflow_require_restart(d):
    r = Receiver(d)
    await r.begin()
    await r.stream(bytes(64 * 16), bad_header=True)
    assert r.errors == 1 and int(d.halted_o.value) and not int(d.active_o.value)
    await r.cycle(start=True)
    # A real held packet plus a successor STP forbids bypassing future zero
    # blocks. The unthrottled source must report overflow, not silently drop.
    await r.stream(frame(packet(1)) + frame(zero_payload_packet(2)) + bytes(64 * 64),
                   ready=lambda n: False)
    assert int(d.overflow_o.value) and int(d.halted_o.value)
    assert r.errors == 2
    await r.cycle(start=True)
    data = packet(3)
    r.expected.append((data, False))
    await r.stream(frame(data) + bytes(64 * 32))
    assert not int(d.overflow_o.value) and int(d.active_o.value)
    assert r.completed == 1 and not r.expected


@cocotb.test()
async def dllp_end_of_stream_and_partial_epoch_abort(d):
    r = Receiver(d)
    await r.begin()
    raw = encoded_words(frame(packet(12)))
    for _ in range(3):
        await r.cycle(raw.popleft())
    await r.cycle(abort=True)
    assert r.errors == 1 and not int(d.active_o.value)
    await r.cycle(start=True)
    data = bytes.fromhex("001122334455")
    r.expected.append((data, True))
    await r.stream(frame(data, dllp=True) + bytes(64 * 32) + bytes(60) + bytes.fromhex("1f809000"))
    assert r.completed == 1 and not r.expected
    assert r.ends == 1 and not int(d.active_o.value) and not int(d.halted_o.value)
    await r.cycle(start=True, flush=True)
    assert not int(d.active_o.value)


@cocotb.test()
async def lookahead_at_exact_block_boundary_releases_packet(d):
    r = Receiver(d)
    await r.begin()
    data = packet(0x731)
    assert len(data) == 18
    r.expected.append((data, False))
    # Eleven IDL DWORDs plus this five-DWORD TLP exactly fill the block.
    # The next all-IDL block must release LOOK without being stored first.
    await r.stream(bytes(44) + frame(data) + bytes(64 * 64))
    assert r.completed == r.good == 1 and not r.expected
    assert not r.errors and not int(d.overflow_o.value)


@cocotb.test()
async def packed_successor_owns_future_zero_blocks(d):
    r = Receiver(d)
    await r.begin()
    first, second = packet(16), zero_payload_packet(17)
    r.expected.extend([(first, False), (second, False)])
    # No IDL padding separates the two STPs. During emission of the first
    # packet, its held nonzero successor owns the following zero body block.
    packed = frame(first)[:len(first) + 2] + frame(second)
    await r.stream(packed + bytes(64 * 96))
    assert r.completed == r.good == 2 and not r.expected
    assert r.errors == 0 and not int(d.overflow_o.value)
