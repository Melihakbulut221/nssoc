# SPDX-FileCopyrightText: 2026 Hasan Melih Akbulut
# SPDX-License-Identifier: Apache-2.0
"""Independent polynomial/STP and port-only framing scoreboard; no decorated tests."""

from collections import deque
import random
import zlib
from cocotb.triggers import Timer


def stp(length, sequence):
    # Section4.2.2.3.1 polynomial note: (L0*x14+...+L10*x4) mod(x4+x+1).
    polynomial = sum(((length >> bit) & 1) << (14 - bit) for bit in range(11))
    while polynomial.bit_length() >= 5:
        polynomial ^= 0x13 << (polynomial.bit_length() - 5)
    crc = polynomial
    parity = (length.bit_count() + crc.bit_count()) & 1
    return bytes(
        [
            (length & 15) * 16 + 15,
            (length >> 4) | (parity << 7),
            (crc << 4) | (sequence >> 8),
            sequence & 255,
        ]
    )


def tlp(sequence=0, payload=0, four=False, digest=False, read_length=1):
    assert payload % 4 == 0 and 0 <= payload <= 4096
    fmt = (2 if payload else 0) | int(four)
    length = (payload // 4 if payload else read_length) & 1023
    header = bytes([fmt << 5, 0, (128 if digest else 0) | (length >> 8), length & 255])
    header += bytes([0x12, 0x34, 0x56, 0x78, 0, 0, 0x10, 0])
    if four:
        header += bytes([0xAB, 0xCD, 0xEF, 1])
    body = header + bytes((n * 37 + 19) & 255 for n in range(payload))
    if digest:
        body += bytes([0xDA, 0x7A, 0xB1, 0x7E])
    prefix = bytes([sequence >> 8, sequence & 255])
    body += zlib.crc32(prefix + body).to_bytes(4, "little")
    return prefix + body


def framed(packet, dllp=False, nullify=False):
    if dllp:
        stream = b"\xf0\xac" + packet
    else:
        length = (len(packet) + 2) // 4
        sequence = (packet[0] << 8) | packet[1]
        stream = stp(length, sequence) + packet[2:]
        if nullify:
            stream += b"\xc0" * 4
    stream += bytes((-len(stream)) % 64)
    return [stream[i : i + 64] for i in range(0, len(stream), 64)]


def unstripe(value):
    return bytes((value >> ((i % 4) * 128 + (i // 4) * 8)) & 255 for i in range(64))


class Port:
    def __init__(self, dut, wrapped=False):
        self.d = dut
        self.wrapped = wrapped
        self.expected = deque()
        self.in_frame = False
        self.frames = self.blocks = self.good = self.errors = self.stalls = 0
        self.stalled = None
        self.queues = [deque() for _ in range(4)]
        self.lfsr = [0x1DBFBC, 0x0607BB, 0x1EC760, 0x18C0DB]
        self.words = 0
        self.active_cycles = 0

    def input(self, value=0, valid=0, sop=0, eop=0, dllp=0, error=0, nullify=0):
        for name, value in dict(
            data_i=value,
            valid_i=valid,
            sop_i=sop,
            eop_i=eop,
            dllp_i=dllp,
            error_i=error,
            nullify_i=nullify,
        ).items():
            getattr(self.d, name).value = value

    def observe(self, block):
        self.blocks += 1
        if not self.in_frame and block == bytes(64):
            return
        assert self.expected, ("unexpected data block", block.hex())
        target = self.expected[0]
        assert block == target[0], (
            "framed block mismatch",
            block.hex(),
            target[0].hex(),
        )
        target.popleft()
        self.in_frame = bool(target)
        if not target:
            self.expected.popleft()
            self.frames += 1

    def decode_word(self, value):
        self.words += 1
        for lane in range(4):
            self.queues[lane].extend((value >> (lane * 32 + n)) & 1 for n in range(32))
        while len(self.queues[0]) >= 130:
            lane_bytes = []
            for lane in range(4):
                bits = [self.queues[lane].popleft() for _ in range(130)]
                assert bits[:2] == [0, 1], "wrong Data Block header or alignment"
                decoded = 0
                state = self.lfsr[lane]
                for n, bit in enumerate(bits[2:]):
                    decoded |= (bit ^ ((state >> 22) & 1)) << n
                    state = ((state << 1) & 0x7FFFFF) ^ (
                        0x210125 if state & (1 << 22) else 0
                    )
                self.lfsr[lane] = state
                lane_bytes.append(decoded.to_bytes(16, "little"))
            self.observe(bytes(lane_bytes[n % 4][n // 4] for n in range(64)))

    async def tick(self, ready=True, reset=False, flush=False):
        d = self.d
        d.clk_i.value = 0
        d.rst_ni.value = int(not reset)
        d.flush_i.value = int(flush)
        getattr(d, "word_ready_i" if self.wrapped else "block_ready_i").value = int(
            ready
        )
        await Timer(2, unit="ns")
        active = not (reset or flush)
        if not active:
            self.stalled = None
            self.in_frame = False
            self.expected.clear()
            self.active_cycles = 0
            self.queues = [deque() for _ in range(4)]
            self.lfsr = [0x1DBFBC, 0x0607BB, 0x1EC760, 0x18C0DB]
        valid = int(
            getattr(d, "word_valid_o" if self.wrapped else "block_valid_o").value
        )
        if active:
            self.active_cycles += 1
            if self.wrapped and self.active_cycles > 8:
                assert valid, "continuous Data Stream word starvation"
            value = int(getattr(d, "word_o" if self.wrapped else "payload_o").value)
            if not self.wrapped:
                assert valid == 1 and int(d.header_o.value) == 2, (
                    "Data Stream starvation"
                )
            if self.stalled is not None:
                assert valid and value == self.stalled, "held output changed"
            self.stalled = value if valid and not ready else None
            if valid and ready:
                if self.wrapped:
                    self.decode_word(value)
                else:
                    self.observe(unstripe(value))
            if valid and not ready:
                self.stalls += 1
        else:
            assert valid == 0 and int(d.ready_o.value) == 0
        accepted = active and int(d.valid_i.value) and int(d.ready_o.value)
        d.clk_i.value = 1
        await Timer(2, unit="ns")
        self.good += int(d.packet_good_o.value)
        self.errors += int(d.packet_error_o.value)
        return bool(accepted)

    async def reset(self):
        self.input()
        for _ in range(2):
            await self.tick(reset=True)
        await self.tick()

    async def send(
        self,
        packet,
        dllp=False,
        nullify=False,
        good=True,
        bubbles=False,
        ready_pattern=None,
        error_at=None,
        type_at=None,
    ):
        if good:
            self.expected.append(deque(framed(packet, dllp, nullify)))
        for i, byte in enumerate(packet):
            if bubbles and i % 5 == 1:
                self.input()
                for _ in range(i % 3 + 1):
                    await self.tick()
            self.input(
                byte,
                1,
                i == 0,
                i == len(packet) - 1,
                (not dllp) if type_at == i else dllp,
                error_at == i,
                nullify if i == 0 else 0,
            )
            for wait in range(10000):
                ready = ready_pattern(i, wait) if ready_pattern else True
                if await self.tick(ready):
                    break
            else:
                raise AssertionError("input did not recover")
        self.input()

    async def drain(self, count=120):
        self.input()
        for _ in range(count):
            await self.tick()
        assert not self.expected and not self.in_frame, "missing or truncated packet"
