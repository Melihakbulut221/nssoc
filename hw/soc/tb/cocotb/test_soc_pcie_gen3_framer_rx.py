# SPDX-FileCopyrightText: 2026 Hasan Melih Akbulut
# SPDX-License-Identifier: Apache-2.0
"""Independent receive-port oracle. Never imports the TX framer or its helper."""

import os
from collections import deque

import cocotb
from cocotb.triggers import Timer

CAP = int(os.environ.get("PCIE_FRAMER_CAPACITY", "150"))
HALF = 8 if os.environ.get("PCIE_NATIVE") == "1" else 1


def crc4(length):
    # Polynomial long division over L0*x14 ... L10*x4; no RTL XOR equations.
    remainder = sum(((length >> i) & 1) << (14 - i) for i in range(11))
    for power in range(14, 3, -1):
        if remainder & (1 << power):
            remainder ^= 0b10011 << (power - 4)
    return remainder


def start_token(length, sequence):
    c = crc4(length)
    parity = (length.bit_count() + c.bit_count()) & 1
    return bytes(
        [
            (length & 15) << 4 | 15,
            length >> 4 | parity << 7,
            c << 4 | sequence >> 8,
            sequence & 255,
        ]
    )


def packet(sequence, payload=0, four=False, digest=False, read_length=1):
    assert payload % 4 == 0
    length = payload // 4 if payload else read_length
    fmt = (2 if payload else 0) | bool(four)
    header = bytes(
        [fmt << 5, 0, (0x80 if digest else 0) | ((length >> 8) & 3), length & 255]
    )
    header += bytes.fromhex("12345678 87654321") + (
        bytes.fromhex("01020304") if four else b""
    )
    body = header + bytes((i * 29 + 77) & 255 for i in range(payload))
    body += bytes.fromhex("aabbccdd") if digest else b""
    body += bytes.fromhex("91a40df3")  # Opaque caller LCRC: not checked by framer.
    encoded = bytes([sequence >> 8, sequence & 255]) + body
    wire = start_token((len(body) + 4) // 4, sequence) + body
    return encoded, wire


def striped(data):
    assert len(data) == 64
    # Independent lane-by-lane construction, lane n carries n, n+4, ... .
    return sum(
        int.from_bytes(data[lane::4], "little") << (128 * lane) for lane in range(4)
    )


class Port:
    def __init__(self, d):
        self.d = d
        self.expected = deque()
        self.assembling = bytearray()
        self.received = []
        self.good = 0
        self.errors = 0
        self.nullified = []
        self.ends = 0
        self.held = None
        self.cycles = 0
        self.stalls = 0

    async def tick(
        self,
        block=None,
        ready=True,
        headers=0xAA,
        error=False,
        reset=False,
        flush=False,
        start=False,
        abort=False,
    ):
        d = self.d
        d.clk_i.value = 0
        d.rst_ni.value = not reset
        d.flush_i.value = flush
        d.stream_start_i.value = start
        d.stream_abort_i.value = abort
        d.block_valid_i.value = block is not None
        d.headers_i.value = headers
        d.payload_i.value = block or 0
        d.block_error_i.value = error
        d.ready_i.value = ready
        await Timer(HALF, unit="ns")
        accepted = bool(int(d.block_ready_o.value)) and block is not None
        valid = bool(int(d.valid_o.value))
        if reset or flush or start or abort:
            self.held = None
            self.assembling.clear()
        elif self.held is not None:
            assert valid
            assert self.held == (
                int(d.data_o.value),
                int(d.sop_o.value),
                int(d.eop_o.value),
                int(d.dllp_o.value),
            )
        if valid:
            current = (
                int(d.data_o.value),
                int(d.sop_o.value),
                int(d.eop_o.value),
                int(d.dllp_o.value),
            )
            if not ready:
                self.stalls += 1
                self.held = current
            else:
                self.held = None
                byte, sop, eop, dllp = current
                assert self.expected, ("premature/unexpected packet output", current)
                assert sop == (len(self.assembling) == 0)
                expected, kind = self.expected[0]
                assert dllp == kind and byte == expected[len(self.assembling)]
                self.assembling.append(byte)
                assert eop == (len(self.assembling) == len(expected))
                if eop:
                    assert bytes(self.assembling) == expected
                    self.received.append(self.expected.popleft())
                    self.assembling.clear()
        d.clk_i.value = 1
        await Timer(HALF, unit="ns")
        self.good += int(d.packet_good_o.value)
        self.errors += int(d.framing_error_o.value)
        self.ends += int(d.stream_end_o.value)
        if int(d.packet_nullified_o.value):
            self.nullified.append(int(d.sequence_o.value))
        self.cycles += 1
        return accepted

    async def reset(self):
        await self.tick(reset=True)
        await self.tick(reset=True)
        await self.tick(start=True)
        await self.tick()
        assert int(self.d.active_o.value) and not int(self.d.halted_o.value)

    async def send(self, data, pad=True, stalled=False, headers=0xAA, error=False):
        if pad:
            data += bytes((-len(data)) % 64)
        assert len(data) % 64 == 0
        for offset in range(0, len(data), 64):
            block = striped(data[offset : offset + 64])
            for wait in range(20000):
                ready = not stalled or self.cycles % 7 in (0, 3, 4)
                if await self.tick(block, ready=ready, headers=headers, error=error):
                    break
            else:
                assert False, "input ready deadlock"
            # Real source bubbles cannot be mistaken for truncation/timeout.
            if stalled:
                for _ in range(offset % 5):
                    await self.tick(ready=False)

    async def settle(self, clocks=100):
        for _ in range(clocks):
            await self.tick()

    async def finish(self):
        for _ in range(25000):
            if not self.expected and not self.assembling:
                await self.settle(40)
                return
            await self.tick(ready=self.cycles % 5 != 1)
        assert False, "complete packet not delivered"

    async def rejected(self, data, headers=0xAA, error=False):
        before = self.errors
        await self.send(data, headers=headers, error=error)
        await self.settle(100)
        assert self.errors == before + 1 and int(self.d.halted_o.value)
        assert not int(self.d.active_o.value) and not int(self.d.valid_o.value)
        assert not int(self.d.block_ready_o.value)
        assert not self.received and not self.expected and self.good == 0


@cocotb.test()
async def packed_successors_every_legal_lane0_position(d):
    p = Port(d)
    await p.reset()
    assert start_token(6, 0x123) == bytes.fromhex("6f802123")
    for offset in range(16):
        a, aw = packet(offset * 251 & 4095, 4, bool(offset & 1), bool(offset & 2))
        b, bw = packet(4095 - offset, 0, read_length=1023)
        dllp = bytes.fromhex("1045abcd0091")
        p.expected.extend([(a, False), (dllp, True), (b, False)])
        # STP -> immediate SDP -> immediate STP, all within/crossing one block.
        await p.send(
            bytes(offset * 4) + aw + b"\xf0\xac" + dllp + bw + bytes(4), stalled=True
        )
        await p.finish()
    assert len(p.received) == 48 and p.good == 48 and not p.errors and p.stalls


@cocotb.test()
async def nullification_full_token_and_next_packet(d):
    p = Port(d)
    await p.reset()
    a, aw = packet(0x123, 44)  # exactly64 wire bytes: EDB is next block.
    b, bw = packet(0xFFF, 4, True, True)
    assert len(aw) == 64
    p.expected.append((b, False))
    await p.send(aw, pad=False)
    await p.settle(150)
    assert p.good == 0 and not p.nullified and not p.received
    await p.send(bytes.fromhex("c0c0c0c0") + bw + bytes(4), stalled=True)
    await p.finish()
    assert p.nullified == [0x123] and p.good == 1 and not p.errors
    # A non-nullified complete TLP also waits indefinitely for its successor.
    p.expected.append((a, False))
    await p.send(aw, pad=False)
    await p.settle(150)
    assert p.good == 1
    await p.send(bytes(64))
    await p.finish()
    assert p.good == 2


@cocotb.test()
async def damaged_stp_crc_parity_lengths_and_header_shape(d):
    for bit in list(range(4, 16)) + list(range(20, 24)):
        p = Port(d)
        await p.reset()
        _, wire = packet(0xA35, 4)
        token = int.from_bytes(wire[:4], "little") ^ (1 << bit)
        await p.rejected(token.to_bytes(4, "little") + wire[4:])
    # Balanced two-bit corruption preserves even parity, so CRC must reject it.
    # This catches a real disabled-CRC mutant that single-bit faults cannot.
    for bit in range(20, 24):
        p = Port(d)
        await p.reset()
        _, wire = packet(0xA35, 4)
        token = int.from_bytes(wire[:4], "little") ^ (1 << bit) ^ (1 << 15)
        await p.rejected(token.to_bytes(4, "little") + wire[4:])
    for length in (0, 2, 3, 4, 1152, 1535, 1536, 2047, (CAP + 6) // 4):
        p = Port(d)
        await p.reset()
        await p.rejected(start_token(length, 123) + bytes(60))
    for mode in ("fmt", "length", "digest", "four"):
        p = Port(d)
        await p.reset()
        _, wire = packet(15, 4)
        bad = bytearray(wire)
        if mode == "fmt":
            bad[4] |= 0x80
        elif mode == "length":
            bad[7] ^= 1
        elif mode == "digest":
            bad[6] ^= 0x80
        else:
            bad[4] ^= 0x20
        await p.rejected(bytes(bad) + bytes(4))


@cocotb.test()
async def bad_tokens_edb_idl_headers_and_stream_end(d):
    patterns = [
        bytes.fromhex(x)
        for x in (
            "c0c0c0c0",
            "f0ad0000",
            "00010000",
            "00000100",
            "00000001",
            "01000000",
            "1f809000",
        )
    ]
    for data in patterns:
        p = Port(d)
        await p.reset()
        await p.rejected(data)
    for lane in range(4):
        for header in (0, 1, 3):
            p = Port(d)
            await p.reset()
            headers = (0xAA & ~(3 << (lane * 2))) | (header << (lane * 2))
            await p.rejected(bytes(64), headers=headers)
    p = Port(d)
    await p.reset()
    await p.rejected(bytes(64), error=True)
    for byte in range(4):
        p = Port(d)
        await p.reset()
        _, wire = packet(0x321, 4)
        edb = bytearray.fromhex("c0c0c0c0")
        edb[byte] ^= 1
        await p.rejected(wire + edb)
    p = Port(d)
    await p.reset()
    a, wire = packet(123, 4)
    p.expected.append((a, False))
    await p.send(wire + bytes(60 - len(wire)) + bytes.fromhex("1f809000"), pad=False)
    await p.finish()
    assert p.ends == 1 and not p.errors and not int(d.active_o.value)
    assert not int(d.halted_o.value) and not int(d.block_ready_o.value)
    # Immediate EDS is a retained successor, not an intervening IDL shortcut.
    await p.tick(start=True)
    a, wire = packet(456, 40)
    assert len(wire) == 60
    p.expected.append((a, False))
    await p.send(wire + bytes.fromhex("1f809000"), pad=False, stalled=True)
    await p.finish()
    assert p.ends == 2 and not p.errors and not int(d.active_o.value)
    await p.tick(start=True)
    await p.send(bytes(64))
    await p.settle()
    assert int(d.active_o.value)


@cocotb.test()
async def truncation_abort_reset_flush_and_held_packet(d):
    p = Port(d)
    await p.reset()
    _, long_wire = packet(123, 128, True)
    await p.send(long_wire[:64], pad=False)
    await p.settle(100)
    assert not p.good and not p.errors
    await p.tick(abort=True)
    assert p.errors == 1 and int(d.halted_o.value)
    await p.tick(start=True)
    # SDP plus its first two bytes at the final DW cannot deliver a partial DLLP.
    await p.send(bytes(60) + bytes.fromhex("f0ac0010"), pad=False)
    await p.settle(150)
    assert not p.good and p.errors == 1
    await p.tick(abort=True)
    assert p.errors == 2 and int(d.halted_o.value)
    await p.tick(start=True)
    # Explicit flush silently abandons an incomplete packet and deactivates.
    await p.send(long_wire[:64], pad=False)
    await p.settle(20)
    await p.tick(flush=True)
    assert not int(d.active_o.value) and not int(d.valid_o.value)
    await p.tick(start=True)
    a, wire = packet(321, 4)
    p.expected.append((a, False))
    await p.send(wire + bytes(4), stalled=True)
    for _ in range(100):
        await p.tick(ready=False)
        if int(d.valid_o.value):
            break
    assert int(d.valid_o.value)
    for _ in range(20):
        await p.tick(ready=False)
    # Reset held packet, no tail may leak into a freshly started stream.
    p.expected.clear()
    await p.tick(reset=True)
    await p.tick(start=True)
    await p.send(bytes(64))
    await p.settle(100)
    p.expected.append((a, False))
    await p.send(wire + bytes(4))
    await p.finish()
    assert p.received == [(a, False)]


@cocotb.test()
async def maximum_packet_and_immediate_dllp_at_boundary(d):
    p = Port(d)
    await p.reset()
    payload = ((CAP - 22) // 4) * 4
    a, wire = packet(4095, payload, True)
    assert len(a) == CAP
    dllp = bytes.fromhex("00000fff1234")
    p.expected.extend([(a, False), (dllp, True)])
    await p.send(wire + b"\xf0\xac" + dllp + bytes(4), stalled=True)
    await p.finish()
    assert len(p.received) == 2 and p.good == 2 and not p.errors
