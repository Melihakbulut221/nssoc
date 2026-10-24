# SPDX-FileCopyrightText: 2026 Hasan Melih Akbulut
# SPDX-License-Identifier: Apache-2.0
"""Only public ports; exact packet bytes checked by two independent CRC oracles."""

import random
import cocotb
from cocotb.triggers import Timer
from test_soc_pcie_tlp_stream import Bench as StreamBench, request, response, CID, BAR
from test_soc_pcie_tlp_integrity import frame_bytes, tlp_bytes


class Bench(StreamBench):
    def __init__(self, dut):
        super().__init__(dut)
        self.acks, self.frames, self.events = [], [], []
        self.ack_held = None
        self.tx_sequence = 0

    async def tick(self, **signals):
        self.d.clk_i.value = 0
        for name, value in signals.items():
            getattr(self.d, name).value = value
        await Timer(5, unit="ns")
        accepted = self.v("rx_valid_i") and self.v("rx_ready_o")
        if self.v("rst_ni"):
            beat = tuple(self.v(n) for n in ("tx_data_o", "tx_sop_o", "tx_eop_o"))
            if self.held is not None:
                assert self.v("tx_valid_o") and beat == self.held, "Stalled TX changed"
            self.held = (
                beat if self.v("tx_valid_o") and not self.v("tx_ready_i") else None
            )
            ack = (self.v("ack_nak_o"), self.v("ack_sequence_o"))
            if self.ack_held is not None:
                assert self.v("ack_valid_o") and ack == self.ack_held, (
                    "Stalled ACK changed"
                )
            self.ack_held = (
                ack if self.v("ack_valid_o") and not self.v("ack_ready_i") else None
            )
            if self.v("ack_valid_o") and self.v("ack_ready_i"):
                self.acks.append(ack)
            if self.v("tx_valid_o") and self.v("tx_ready_i"):
                data, sop, eop = beat
                assert bool(sop) == (not self.current)
                self.current.append(data)
                if eop:
                    frame = bytes(self.current)
                    assert frame[:2] == bytes(
                        [self.tx_sequence >> 8, self.tx_sequence & 255]
                    )
                    assert frame == frame_bytes(frame[2:-4], self.tx_sequence)
                    words = []
                    header = 4 if frame[2] & 0x20 else 3
                    for i in range(2, len(frame) - 4, 4):
                        words.append(
                            int.from_bytes(
                                frame[i : i + 4],
                                "big" if (i - 2) // 4 < header else "little",
                            )
                        )
                    self.packets.append(words)
                    self.frames.append(frame)
                    self.current = []
                    self.tx_sequence = (self.tx_sequence + 1) & 4095
            if self.v("psel_o") and self.v("penable_o") and self.v("pready_i"):
                self.bus.append(
                    tuple(
                        self.v(n)
                        for n in ("paddr_o", "pwrite_o", "pstrb_o", "pwdata_o")
                    )
                )
        else:
            self.held = None
            self.ack_held = None
            self.current = []
            self.tx_sequence = 0
        self.d.clk_i.value = 1
        await Timer(5, unit="ns")
        self.errors += self.v("error_o")
        self.events.append(
            tuple(
                self.v(n)
                for n in (
                    "packet_accepted_o",
                    "packet_duplicate_o",
                    "packet_rejected_o",
                )
            )
        )
        return accepted

    async def reset(self):
        self.d.ack_ready_i.value = 1
        await super().reset()
        self.acks.clear()
        self.frames.clear()
        self.events.clear()
        assert self.v("rx_expected_sequence_o") == self.v("tx_next_sequence_o") == 0

    async def wire(self, packet, bad_at=None, gap=False):
        for i, byte in enumerate(packet):
            if gap:
                await self.tick(rx_valid_i=0, rx_error_i=1, rx_eop_i=1, rx_sop_i=1)
            await self.word(byte, i == 0, i == len(packet) - 1, i == bad_at)
        await self.tick(rx_valid_i=0, rx_sop_i=0, rx_eop_i=0, rx_error_i=0)

    async def send(self, words, sequence=None, bad_at=None, gap=False):
        if sequence is None:
            sequence = self.v("rx_expected_sequence_o")
        await self.wire(frame_bytes(tlp_bytes(words), sequence), bad_at, gap)

    async def idle(self, n=100, **signals):
        await super().idle(n, **signals)


@cocotb.test()
async def accepted_packets_generate_real_prefix_lcrc_and_mixed_byte_order(dut):
    b = Bench(dut)
    await b.reset()
    assert await b.transact(request(4, CID << 16), gap=True) == [
        response(data=0x0000FFFF)
    ]
    assert b.frames[0] == frame_bytes(tlp_bytes(response(data=0x0000FFFF)), 0)
    assert b.acks == [(0, 0)] and b.v("rx_expected_sequence_o") == 1
    await b.enable()
    for wide in (0, 0x20):
        for be in range(16):
            old = len(b.bus)
            await b.send(request(0x40 | wide, BAR + 0x24, [0x78563412], be=be))
            await b.idle(60)
            assert b.bus[old:] == ([(0x24, 1, be, 0x78563412)] if be else [])
    assert await b.transact(request(0, BAR + 0x24, tag=0x12)) == [
        response(data=0xD3C2B1A0, tag=0x12, lower=0x24)
    ]
    assert not b.errors


@cocotb.test()
async def duplicate_future_half_range_and_nak_suppression(dut):
    b = Bench(dut)
    await b.reset()
    await b.enable()
    words = request(0x40, BAR + 0x30, [0x12345678])
    expected = b.v("rx_expected_sequence_o")
    before = len(b.acks)
    for seq in ((expected - 1) & 4095, (expected - 2048) & 4095):
        await b.send(words, sequence=seq)
        await b.idle(60)
        assert not b.bus and b.v("rx_expected_sequence_o") == expected
    assert b.acks[before:] == [(0, expected - 1)] * 2
    assert sum(x[1] for x in b.events) == 2
    for seq in ((expected - 2049) & 4095, (expected + 1) & 4095):
        await b.send(words, sequence=seq)
        await b.idle(60)
        assert not b.bus and b.v("rx_expected_sequence_o") == expected
    assert b.acks[before + 2 :] == [(1, expected - 1)]
    await b.send(words)
    await b.idle(60)
    assert b.bus == [(0x30, 1, 15, 0x12345678)]
    await b.send(words, sequence=(expected + 2) & 4095)
    await b.idle(60)
    assert b.acks[-2:] == [(0, expected), (1, expected)]
    assert len(b.bus) == 1


@cocotb.test()
async def every_wire_bit_corruption_and_framing_fault_cannot_advance_sequence_or_apb(
    dut,
):
    b = Bench(dut)
    await b.reset()
    await b.enable()
    expected = b.v("rx_expected_sequence_o")
    packet = frame_bytes(tlp_bytes(request(0x40, BAR + 0x30, [0x12345678])), expected)
    ack_start = len(b.acks)
    for bit in range(len(packet) * 8):
        damaged = bytearray(packet)
        damaged[bit // 8] ^= 1 << (bit % 8)
        await b.wire(damaged)
        await b.idle(8)
        assert not b.bus and not b.packets and b.v("rx_expected_sequence_o") == expected
    for damaged in (
        packet[:-1],
        packet + b"\0",
        frame_bytes(b"\0" * 13, expected),
        frame_bytes(b"\0" * 36, expected),
    ):
        await b.wire(damaged)
        await b.idle(20)
        assert not b.bus and b.v("rx_expected_sequence_o") == expected
    await b.wire(packet, bad_at=len(packet) - 1)
    await b.idle(20)
    assert b.acks[ack_start:] == [(1, expected - 1)]
    await b.wire(packet)
    await b.idle()
    assert (
        b.bus == [(0x30, 1, 15, 0x12345678)]
        and b.v("rx_expected_sequence_o") == expected + 1
    )


@cocotb.test()
async def ack_and_wire_output_backpressure_preserve_records_and_packets(dut):
    b = Bench(dut)
    await b.reset()
    await b.enable()
    await b.tick(ack_ready_i=0, tx_ready_i=0, pready_i=0)
    await b.send(request(0, BAR + 4, tag=1))
    await b.idle(30)
    assert b.v("ack_valid_o") and not b.v("rx_ready_o") and not b.bus
    await b.idle(20, pready_i=1)
    assert b.v("tx_valid_o") and b.v("tx_next_sequence_o") == 2
    await b.idle(20, ack_ready_i=1)
    await b.send(request(0, BAR + 8, tag=2))
    await b.idle(40)
    rng = random.Random(712)
    for _ in range(160):
        await b.tick(rx_valid_i=0, tx_ready_i=rng.randrange(2))
    await b.idle(tx_ready_i=1)
    assert b.packets == [response(data=0xD3C2B1A0, tag=i, lower=4 * i) for i in (1, 2)]
    assert len(b.bus) == 2 and not b.errors


@cocotb.test()
async def reset_flushes_pending_ack_prefix_crc_and_partial_receive(dut):
    b = Bench(dut)
    await b.reset()
    packet = frame_bytes(tlp_bytes(request(0x44, CID << 16 | 4, [2])), 0)
    for stop in (1, 8, len(packet) - 1):
        for i, byte in enumerate(packet[:stop]):
            await b.word(byte, i == 0)
        await b.reset()
        await b.idle(20)
        assert not b.v("memory_enable_o") and not b.acks and not b.frames
    await b.tick(ack_ready_i=0, tx_ready_i=0)
    await b.send(request(4, CID << 16))
    await b.idle(50)
    assert b.v("ack_valid_o") and b.v("tx_valid_o")
    await b.reset()
    await b.idle(20)
    assert not b.v("ack_valid_o") and not b.v("tx_valid_o")
    # Send part of a completion including prefix/header, then reset while held.
    await b.send(request(4, CID << 16))
    while len(b.current) < 17:
        await b.tick(rx_valid_i=0)
    await b.tick(tx_ready_i=0)
    await b.idle(5)
    assert b.v("tx_next_sequence_o") == 0
    await b.reset()
    await b.idle(20)
    assert await b.transact(request(4, CID << 16)) == [response(data=0xFFFF)]
    assert b.frames[-1][:2] == b"\0\0"


@cocotb.test()
async def actual_4096_packet_rx_and_tx_wraparound_and_duplicate_after_wrap(dut):
    b = Bench(dut)
    await b.reset()
    for sequence in range(4097):
        old = len(b.frames)
        await b.send(
            request(4, CID << 16, tag=sequence & 255), sequence=sequence & 4095
        )
        for _ in range(160):
            if len(b.frames) > old:
                break
            await b.tick(rx_valid_i=0)
        assert len(b.frames) == old + 1
        assert b.packets[-1] == response(data=0xFFFF, tag=sequence & 255)
        assert b.v("rx_expected_sequence_o") == ((sequence + 1) & 4095)
    assert b.v("tx_next_sequence_o") == 1
    old = len(b.frames)
    await b.send(request(4, CID << 16), sequence=4095)
    await b.idle(60)
    assert (
        len(b.frames) == old
        and b.acks[-1] == (0, 0)
        and b.v("rx_expected_sequence_o") == 1
    )
