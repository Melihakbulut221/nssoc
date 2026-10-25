# SPDX-FileCopyrightText: 2026 Hasan Melih Akbulut
# SPDX-License-Identifier: Apache-2.0
"""Port-only elastic transport; independent polynomial and serial-bit oracles."""

from collections import deque
import random
import zlib

import cocotb
from cocotb.triggers import Timer

SEEDS = (0x1DBFBC, 0x0607BB, 0x1EC760, 0x18C0DB)


def crc4(length):
    dividend = int(f"{length:011b}"[::-1], 2) << 4
    for position in range(14, 3, -1):
        if dividend & (1 << position):
            dividend ^= 0b10011 << (position - 4)
    return dividend


def start_token(length, sequence):
    crc = crc4(length)
    parity = (length.bit_count() + crc.bit_count()) % 2
    return bytes(
        (
            (length % 16) * 16 + 15,
            (length // 16) + parity * 128,
            crc * 16 + (sequence >> 8),
            sequence & 255,
        )
    )


def packet(sequence, payload=0, four=False, digest=False):
    count = (payload // 4 if payload else 1) & 1023
    result = bytes(
        (
            sequence >> 8,
            sequence & 255,
            (0x40 if payload else 0) | (0x20 if four else 0),
            0,
            (128 if digest else 0) | (count >> 8),
            count & 255,
        )
    )
    result += bytes.fromhex("1234567800001000")
    if four:
        result += bytes.fromhex("00000001")
    result += bytes((i * 29 + sequence + 17) % 256 for i in range(payload))
    if digest:
        result += bytes.fromhex("deadbeef")
    return result + zlib.crc32(result).to_bytes(4, "little")


def frame(data, dllp=False, nullify=False):
    if dllp:
        result = b"\xf0\xac" + data
    else:
        result = (
            start_token((len(data) + 2) // 4, int.from_bytes(data[:2], "big"))
            + data[2:]
        )
        if nullify:
            result += b"\xc0" * 4
    return result + bytes(-len(result) % 64)


def step(state):
    outgoing = (state >> 22) & 1
    # Polynomial exponents, independently accumulated rather than a copied mask.
    state = (state * 2) % (1 << 23)
    if outgoing:
        for exponent in (21, 16, 8, 5, 2, 0):
            state ^= 1 << exponent
    return outgoing, state


def encoded_words(stream, bad_header=False):
    """Independent transmitter for RX-only malformed/packed stream controls."""
    stream += bytes(-len(stream) % 1024)  # 16 blocks =65 complete32-bit words/lane.
    states = list(SEEDS)
    lanes = [[] for _ in range(4)]
    for block in range(len(stream) // 64):
        for lane in range(4):
            lanes[lane].extend([1 if bad_header and block == lane == 0 else 0, 1])
            for index in range(16):
                byte = stream[block * 64 + index * 4 + lane]
                for bit in range(8):
                    mask, states[lane] = step(states[lane])
                    lanes[lane].append(((byte >> bit) & 1) ^ mask)
    return deque(
        sum(
            lanes[lane][position + n] << (lane * 32 + n)
            for lane in range(4)
            for n in range(32)
        )
        for position in range(0, len(lanes[0]), 32)
    )


class Link:
    def __init__(self, dut, loopback=True):
        self.d = dut
        self.rng = random.Random(0x9831)
        self.loopback = loopback
        self.tx_good = self.tx_bad = self.rx_good = self.nulls = self.errors = (
            self.ends
        ) = 0
        self.completed = self.word_count = self.block_count = self.stalls = 0
        self.epoch()

    def epoch(self):
        self.queue = deque()
        self.rx_word_held = False
        self.tx_held = self.byte_held = None
        self.lanes = [deque() for _ in range(4)]
        self.states = list(SEEDS)
        self.expected_blocks = deque()
        self.frame_active = False
        self.expected_packets = deque()
        self.expected_events = deque()
        self.output = bytearray()

    def input(
        self,
        byte=0,
        valid=False,
        sop=False,
        eop=False,
        dllp=False,
        error=False,
        nullify=False,
    ):
        for name, value in dict(
            tx_data_i=byte,
            tx_valid_i=valid,
            tx_sop_i=sop,
            tx_eop_i=eop,
            tx_dllp_i=dllp,
            tx_error_i=error,
            tx_nullify_i=nullify,
        ).items():
            getattr(self.d, name).value = int(value)

    def expect(self, data, dllp=False, nullify=False, tx=True):
        if tx:
            wire = frame(data, dllp, nullify)
            self.expected_blocks.append(
                deque(wire[i : i + 64] for i in range(0, len(wire), 64))
            )
        if nullify:
            self.expected_events.append(("null", int.from_bytes(data[:2], "big")))
        else:
            self.expected_packets.append((data, dllp))
            self.expected_events.append(
                ("good", None if dllp else int.from_bytes(data[:2], "big"))
            )

    def observe_tx_word(self, value):
        self.word_count += 1
        for lane in range(4):
            self.lanes[lane].extend((value >> (lane * 32 + n)) & 1 for n in range(32))
        while len(self.lanes[0]) >= 130:
            lane_bytes = []
            for lane in range(4):
                bits = [self.lanes[lane].popleft() for _ in range(130)]
                assert bits[:2] == [0, 1], "TX serialized Data Block header"
                decoded = 0
                for n, bit in enumerate(bits[2:]):
                    mask, self.states[lane] = step(self.states[lane])
                    decoded |= (bit ^ mask) << n
                lane_bytes.append(decoded.to_bytes(16, "little"))
            block = bytes(lane_bytes[i % 4][i // 4] for i in range(64))
            self.block_count += 1
            if not self.frame_active and block == bytes(64):
                continue
            assert self.expected_blocks, ("Unexpected TX symbols", block.hex())
            assert block == self.expected_blocks[0].popleft(), (
                "Independent TX bit/CRC4/stripe/scrambler mismatch"
            )
            self.frame_active = bool(self.expected_blocks[0])
            if not self.frame_active:
                self.expected_blocks.popleft()

    async def tick(
        self,
        reset=False,
        flush=False,
        start=False,
        abort=False,
        byte_ready=None,
        wire_ready=None,
    ):
        d = self.d
        d.clk_i.value = 0
        d.rst_ni.value = int(not reset)
        d.flush_i.value = int(flush)
        d.rx_stream_start_i.value = int(start)
        d.rx_stream_abort_i.value = int(abort)
        active = not (reset or flush)
        if not active:
            self.epoch()
        tx_ready = self.loopback and len(self.queue) < 9 and self.rng.random() < 0.7
        if wire_ready is not None:
            tx_ready = bool(wire_ready) and self.loopback and len(self.queue) < 9
        d.tx_word_ready_i.value = int(tx_ready)
        if self.queue and (self.rx_word_held or self.rng.random() < 0.75):
            self.rx_word_held = True
        d.rx_word_valid_i.value = int(
            self.rx_word_held and active and not start and not abort
        )
        d.rx_word_i.value = self.queue[0] if self.queue else 0
        ready = self.rng.random() < 0.65 if byte_ready is None else byte_ready
        d.rx_ready_i.value = int(ready)
        await Timer(2, unit="ns")
        tx_pop = active and int(d.tx_word_valid_o.value) and tx_ready
        tx_value = int(d.tx_word_o.value)
        if active:
            if self.tx_held is not None:
                assert int(d.tx_word_valid_o.value) and tx_value == self.tx_held
            self.tx_held = (
                tx_value if int(d.tx_word_valid_o.value) and not tx_ready else None
            )
            if tx_pop:
                self.observe_tx_word(tx_value)
            if int(d.tx_word_valid_o.value) and not tx_ready:
                self.stalls += 1
        rx_pop = int(d.rx_word_valid_i.value) and int(d.rx_word_ready_o.value)
        accepted = active and int(d.tx_valid_i.value) and int(d.tx_ready_o.value)
        valid = int(d.rx_valid_o.value)
        output = tuple(
            int(getattr(d, n).value)
            for n in ("rx_data_o", "rx_sop_o", "rx_eop_o", "rx_dllp_o")
        )
        if active and not start and not abort:
            if self.byte_held is not None:
                assert valid and output == self.byte_held, (
                    "Held complete RX byte changed"
                )
            self.byte_held = output if valid and not ready else None
            if valid and ready:
                assert self.expected_packets, "Unexpected RX packet delivery"
                expected, dllp = self.expected_packets[0]
                byte, sop, eop, actual_dllp = output
                assert bool(actual_dllp) == dllp and bool(sop) == (
                    len(self.output) == 0
                )
                assert byte == expected[len(self.output)], (
                    "Sequence/TLP/DLLP/LCRC byte changed"
                )
                self.output.append(byte)
                assert bool(eop) == (len(self.output) == len(expected))
                if eop:
                    assert bytes(self.output) == expected
                    self.expected_packets.popleft()
                    self.output.clear()
                    self.completed += 1
        else:
            self.byte_held = None
            assert not valid
        d.clk_i.value = 1
        await Timer(2, unit="ns")
        if rx_pop:
            self.queue.popleft()
            self.rx_word_held = False
        if tx_pop:
            self.queue.append(tx_value)
        self.tx_good += int(d.tx_packet_good_o.value)
        self.tx_bad += int(d.tx_packet_error_o.value)
        for name, kind in (
            ("rx_packet_good_o", "good"),
            ("rx_packet_nullified_o", "null"),
        ):
            if int(getattr(d, name).value):
                assert self.expected_events, (
                    "Unexpected receive acceptance/nullification"
                )
                wanted, seq = self.expected_events.popleft()
                assert wanted == kind
                if seq is not None:
                    assert int(d.rx_sequence_o.value) == seq
                if kind == "good":
                    self.rx_good += 1
                else:
                    self.nulls += 1
        self.errors += int(d.rx_framing_error_o.value)
        self.ends += int(d.rx_stream_end_o.value)
        return bool(accepted)

    async def reset(self):
        self.input()
        await self.tick(reset=True)
        await self.tick(reset=True)
        await self.tick(start=True)

    async def send(
        self, data, dllp=False, nullify=False, expected=True, error_index=None
    ):
        if expected:
            self.expect(data, dllp, nullify)
        for index, byte in enumerate(data):
            if index % 5 == 2:
                self.input()
                await self.tick()
            self.input(
                byte,
                True,
                index == 0,
                index + 1 == len(data),
                dllp,
                index == error_index,
                nullify,
            )
            for _ in range(5000):
                if await self.tick():
                    break
            else:
                raise AssertionError("Packet ingress did not progress")
        self.input()

    async def settle(self, extra=70):
        self.input()
        for _ in range(12000):
            if (
                not self.expected_packets
                and not self.expected_events
                and not self.expected_blocks
            ):
                break
            await self.tick()
        else:
            raise AssertionError("Bounded expected packets did not complete")
        for _ in range(extra):
            await self.tick()


@cocotb.test()
async def actual_packet_loopback_and_independent_serial_oracle(d):
    assert start_token(6, 0x123).hex() == "6f802123"
    link = Link(d)
    await link.reset()
    samples = [
        packet(0),
        packet(0xFFF, 128, True),
        packet(0x123, 20, False, True),
        packet(1, 0, True, True),
    ]
    # Framing preserves arbitrary supplied LCRC bytes; this layer does not claim
    # link-integrity acceptance. Downstream LCRC must reject this damaged tail.
    damaged = bytearray(packet(0x321, 8))
    damaged[-1] ^= 1
    samples.append(bytes(damaged))
    for data in samples:
        await link.send(data)
    for dllp in (bytes.fromhex("000012345678"), bytes.fromhex("ffffffffffff")):
        await link.send(dllp, dllp=True)
    await link.settle()
    assert link.completed == link.rx_good == link.tx_good == 7
    assert (
        link.errors == link.tx_bad == 0 and link.word_count > 150 and link.stalls > 40
    )


@cocotb.test()
async def nullification_and_rejected_packet_never_deliver(d):
    link = Link(d)
    await link.reset()
    await link.send(packet(0xAFE, 44), nullify=True)
    await link.send(packet(0xAFF, 4))
    bad_prefix = bytearray(packet(3))
    bad_prefix[0] |= 0x80
    bad_shape = bytearray(packet(4))
    bad_shape[2] = 0xE0
    for bad in (
        bytes(bad_prefix),
        bytes(bad_shape),
        packet(5)[:-4],
        packet(6, 132, True),
    ):
        await link.send(bad, expected=False)
    await link.send(packet(7), expected=False, error_index=10)
    await link.send(packet(8, 8))
    for index, byte in enumerate(packet(9, 16)[:11]):
        link.input(byte, True, index == 0)
        for _ in range(5000):
            if await link.tick():
                break
        else:
            raise AssertionError("Partial packet ingress did not progress")
    await link.send(packet(10))  # A real new SOP replaces the partial old frame.
    await link.settle()
    assert link.completed == link.rx_good == 3 and link.nulls == 1
    assert link.tx_bad >= 6 and link.errors == 0


@cocotb.test()
async def independent_wire_faults_headers_and_end_tokens(d):
    for fault in ("crc", "header", "truncated", "edb"):
        link = Link(d, loopback=False)
        await link.reset()
        data = packet(0x456, 4)
        stream = bytearray(frame(data))
        if fault == "crc":
            stream[2] ^= 0x10
            stream[1] ^= 0x80
        elif fault == "truncated":
            # Stop well before a complete encoded packet and explicitly abort.
            link.queue = encoded_words(stream)
            while len(link.queue) > 63:
                await link.tick()
            await link.tick(abort=True)
            for _ in range(30):
                await link.tick()
            assert link.errors == 1 and link.completed == 0 and int(d.rx_halted_o.value)
            continue
        elif fault == "edb":
            end = len(data) + 2
            stream[end : end + 4] = bytes.fromhex("c0c0c001")
        link.queue = encoded_words(bytes(stream), bad_header=fault == "header")
        for _ in range(500):
            await link.tick()
        assert link.errors == 1 and link.completed == 0 and int(d.rx_halted_o.value)
        assert int(d.rx_word_ready_o.value) == 0
    link = Link(d, loopback=False)
    await link.reset()
    data = packet(0x789)
    # Packed immediate STP->SDP->IDL with a final legal EDS at symbol60.
    packed = frame(data)[: len(data) + 2] + b"\xf0\xac" + bytes.fromhex("001122334455")
    packed += bytes(60 - len(packed)) + bytes.fromhex("1f809000")
    link.expect(data, tx=False)
    link.expect(bytes.fromhex("001122334455"), dllp=True, tx=False)
    link.queue = encoded_words(packed)
    await link.settle(250)
    assert link.completed == 2 and link.ends == 1 and link.errors == 0
    assert not int(d.rx_active_o.value) and not int(d.rx_halted_o.value)


@cocotb.test()
async def flush_abort_restart_clear_partial_words_and_held_packets(d):
    link = Link(d)
    await link.reset()
    # Each cut covers a different partial serial block/descrambler beat epoch.
    for cut in (1, 3, 5, 9, 17):
        for _ in range(cut):
            await link.tick()
        await link.tick(abort=True)
        assert not int(d.rx_word_ready_o.value)
        await link.tick(flush=True)
        await link.tick(start=True)
        await link.send(packet(cut, 8))
        await link.settle(4)
    data = packet(0x55, 128, True)
    await link.send(data)
    for _ in range(3000):
        await link.tick(byte_ready=False)
        if int(d.rx_valid_o.value):
            break
    else:
        raise AssertionError("Expected a quarantined complete held packet")
    for _ in range(37):
        await link.tick(byte_ready=False)
    before = link.completed
    await link.tick(flush=True)
    await link.tick(start=True)
    await link.send(packet(0xFFF, 0, True))
    await link.settle()
    assert link.completed == before + 1 and link.errors == 5


@cocotb.test()
async def receive_epoch_restart_cancels_all_four_lane_partial_state(d):
    for cut in (1, 4, 5, 8, 11, 19):
        link = Link(d, loopback=False)
        await link.reset()
        # Enough payload to exercise raw/decoded and packet staging ownership.
        # No expected delivery is permitted before this deliberately early cut.
        old = packet(0x987, 128, True)
        link.expect(old, tx=False)
        link.queue = encoded_words(frame(old))
        initial_words = len(link.queue)
        for _ in range(1000):
            if initial_words - len(link.queue) >= cut:
                break
            await link.tick(byte_ready=False)
        else:
            raise AssertionError("RX partial-word control did not advance")
        link.epoch()
        # Restart RX only while active; there is no global/TX reset here.
        await link.tick(start=True)
        fresh = packet(cut, 12, digest=True)
        link.expect(fresh, tx=False)
        link.queue = encoded_words(frame(fresh))
        await link.settle(20)
        assert link.completed == 1 and link.errors == 0
    # Asynchronous reset with a fully accepted, stalled output packet.
    link = Link(d, loopback=False)
    await link.reset()
    old = packet(0x345)
    link.expect(old, tx=False)
    link.queue = encoded_words(frame(old))
    for _ in range(1000):
        await link.tick(byte_ready=False)
        if int(d.rx_valid_o.value):
            break
    else:
        raise AssertionError("Reset control requires a real held output byte")
    await link.reset()
    fresh = packet(0xFFF)
    link.expect(fresh, tx=False)
    link.queue = encoded_words(frame(fresh))
    await link.settle(20)
    assert link.completed == 1
