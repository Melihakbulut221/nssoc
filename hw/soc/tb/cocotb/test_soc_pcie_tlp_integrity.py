# SPDX-FileCopyrightText: 2026 Hasan Melih Akbulut
# SPDX-License-Identifier: Apache-2.0
"""Port-only classic LCRC quarantine checks, also usable on mapped cells."""

import random
import zlib

import cocotb
from test_soc_pcie_tlp_stream import Bench as StreamBench, request, response, CID, BAR


def normal_lcrc(data):
    """Independent normal-polynomial, left-shifting serial reference.

    Bits arrive 0..7 per byte. Reverse each octet of the complemented
    normal remainder, highest polynomial octet first, to get wire bytes.
    Unlike the RTL this never uses a reflected polynomial or right shift.
    """
    remainder = 0xFFFFFFFF
    for byte in data:
        for bit in range(8):
            feedback = ((remainder >> 31) ^ ((byte >> bit) & 1)) & 1
            remainder = (remainder << 1) & 0xFFFFFFFF
            if feedback:
                remainder ^= 0x04C11DB7
    value = remainder ^ 0xFFFFFFFF
    return bytes(
        int(f"{(value >> shift) & 255:08b}"[::-1], 2) for shift in (24, 16, 8, 0)
    )


def frame_bytes(tlp, sequence=0xABC, reserved=0):
    protected = bytes([(reserved << 4) | (sequence >> 8), sequence & 255]) + bytes(tlp)
    crc = zlib.crc32(protected).to_bytes(4, "little")
    assert crc == normal_lcrc(protected)
    return protected + crc


def tlp_bytes(words):
    header = 4 if words[0] & (1 << 29) else 3
    return b"".join(
        word.to_bytes(4, "big" if i < header else "little")
        for i, word in enumerate(words)
    )


class Bench(StreamBench):
    async def wire(self, packet, bad_at=None, gap=False):
        for index, byte in enumerate(packet):
            if gap:
                await self.tick(
                    rx_valid_i=0, rx_sop_i=1, rx_eop_i=1, rx_error_i=1, rx_data_i=255
                )
            await self.word(byte, index == 0, index == len(packet) - 1, index == bad_at)
        await self.tick(rx_valid_i=0, rx_sop_i=0, rx_eop_i=0, rx_error_i=0)

    async def send(self, words, bad_at=None, gap=False, sequence=0xABC, reserved=0):
        await self.wire(frame_bytes(tlp_bytes(words), sequence, reserved), bad_at, gap)

    async def idle(self, n=150, **signals):
        await super().idle(n, **signals)


@cocotb.test()
async def valid_headers_payload_lanes_and_sequence_coverage(dut):
    b = Bench(dut)
    await b.reset()
    assert await b.transact(request(4, CID << 16), gap=True) == [
        response(data=0x0000FFFF)
    ]
    await b.enable()
    for wide in (0, 0x20):
        for be in range(16):
            previous = len(b.bus)
            await b.send(
                request(0x40 | wide, BAR + 0x24, [0x78563412], be=be),
                gap=True,
                sequence=(be << 8) | 0x5A,
                reserved=be,
            )
            await b.idle()
            assert b.bus[previous:] == ([(0x24, 1, be, 0x78563412)] if be else [])
            assert (
                b.v("rx_sequence_o") == (be << 8) | 0x5A and b.v("rx_reserved_o") == be
            )
    await b.send(request(0x40, BAR + 0x28, [0xABCDEF01]), sequence=0xFFF, reserved=15)
    await b.idle()
    assert b.v("rx_sequence_o") == 0xFFF and b.v("rx_reserved_o") == 15
    assert b.bus[-1] == (0x28, 1, 15, 0xABCDEF01)
    assert b.errors == 0


@cocotb.test()
async def every_single_bit_in_prefix_tlp_and_lcrc_is_quarantined(dut):
    b = Bench(dut)
    await b.reset()
    await b.enable()
    packet = frame_bytes(tlp_bytes(request(0x40, BAR + 0x30, [0x12345678])))
    assert packet.hex() == "0abc400000010138970f8234503078563412ad7c660b"
    for bit in range(len(packet) * 8):
        damaged = bytearray(packet)
        damaged[bit // 8] ^= 1 << (bit % 8)
        before = b.errors
        await b.wire(damaged)
        await b.idle(25)
        assert not b.bus and not b.packets and not b.v("psel_o")
        assert b.errors > before
    await b.send(request(0x40, BAR + 0x30, [0x12345678]))
    await b.idle()
    assert b.bus == [(0x30, 1, 15, 0x12345678)]


@cocotb.test()
async def no_apb_or_config_side_effect_until_all_four_crc_bytes(dut):
    b = Bench(dut)
    await b.reset()
    packet = frame_bytes(tlp_bytes(request(0x44, CID << 16 | 4, [2])))
    for i, byte in enumerate(packet[:-1]):
        await b.word(byte, i == 0, False)
        await b.idle(2)
        assert not b.v("memory_enable_o") and not b.v("psel_o") and not b.packets
    for _ in range(20):
        await b.idle(1)
    assert not b.v("memory_enable_o")
    await b.word(packet[-1], eop=True)
    await b.idle()
    assert b.v("memory_enable_o") and b.packets == [response()]
    await b.enable()
    packet = frame_bytes(tlp_bytes(request(0x60, BAR + 0x30, [0x87654321])))
    for i, byte in enumerate(packet[:-1]):
        await b.word(byte, i == 0, False)
        await b.idle(2)
        assert not b.bus and not b.v("psel_o")
    await b.word(packet[-1], eop=True, error=True)
    await b.idle()
    assert not b.bus and not b.packets


@cocotb.test()
async def malformed_overflow_fault_sideband_and_sop_recovery(dut):
    b = Bench(dut)
    await b.reset()
    await b.enable()
    good = frame_bytes(tlp_bytes(request(0x40, BAR, [0xA1B2C3D4])))
    # Exactly 8 DWORDs can pass the quarantine even though the backend rejects
    # this unsupported multi-DWORD request. One extra byte cannot pass it.
    maximum = tlp_bytes(request(0x40, BAR, [1] * 5, length=5))
    assert len(maximum) == 32
    for extra in (b"", b"\x00"):
        packet = frame_bytes(maximum + extra)
        for i, byte in enumerate(packet):
            await b.word(byte, i == 0, i == len(packet) - 1)
        assert bool(b.v("packet_good_o")) == (not extra)
        await b.idle()
        assert not b.bus and not b.packets
    malformed = [
        good[:-1],
        good + b"\x00",
        good + good,
        frame_bytes(b"\x00" * 11),
        frame_bytes(b"\x00" * 13),
        frame_bytes(tlp_bytes(request(0x40, BAR, [1] * 6, length=6))),
        bytes([0]),
    ]
    for packet in malformed:
        before = b.errors
        await b.wire(packet)
        await b.idle()
        assert not b.bus and not b.packets and b.errors > before
    for index in range(len(good)):
        await b.wire(good, bad_at=index)
        await b.idle(25)
        assert not b.bus and not b.packets
    # Aligned, valid LCRC does not bypass backend length/TD checks.
    for words in [
        request(0x40, BAR, [1, 2]),
        [x | (1 << 15) if i == 0 else x for i, x in enumerate(request(0x40, BAR, [1]))],
    ]:
        await b.send(words)
        await b.idle()
        assert not b.bus
    for index, byte in enumerate(good[:9]):
        await b.word(byte, index == 0)
    await b.send(request(0x40, BAR + 0x34, [0xA1B2C3D4]))
    await b.idle()
    assert b.bus == [(0x34, 1, 15, 0xA1B2C3D4)]
    b.bus.clear()
    await b.word(0xA5)
    await b.word(0x5A)
    assert await b.transact(request(4, CID << 16)) == [response(data=0x0000FFFF)]
    assert not b.bus


@cocotb.test()
async def completion_backpressure_and_apb_waits_are_lossless(dut):
    b = Bench(dut)
    await b.reset()
    await b.enable()
    await b.tick(tx_ready_i=0, pready_i=0)
    await b.send(request(0, BAR + 4, tag=1))
    await b.idle(100)
    assert b.v("psel_o") and b.v("penable_o") and not b.bus
    await b.tick(pready_i=1)
    await b.idle(10)
    for tag in range(2, 5):
        await b.send(request(0, BAR + tag * 4, tag=tag))
        await b.idle(80)
    assert not b.v("rx_ready_o") and b.v("tx_valid_o")
    await b.idle(40)
    rng = random.Random(0x4321)
    for _ in range(600):
        await b.tick(rx_valid_i=0, tx_ready_i=rng.randrange(2))
    await b.idle(tx_ready_i=1)
    assert b.packets == [
        response(data=0xD3C2B1A0, tag=t, lower=t * 4) for t in range(1, 5)
    ]
    assert len(b.bus) == 4 and b.v("rx_ready_o") and not b.current
    assert not b.errors


@cocotb.test()
async def reset_flushes_partial_validated_and_stalled_packets(dut):
    b = Bench(dut)
    await b.reset()
    await b.enable()
    packet = frame_bytes(tlp_bytes(request(0x40, BAR, [0x12345678])))
    for stop in (1, 2, 8, len(packet) - 1):
        for i, byte in enumerate(packet[:stop]):
            await b.word(byte, i == 0)
        await b.reset()
        await b.idle()
        assert not b.bus and not b.packets and not b.v("memory_enable_o")
        await b.enable()
    # Reset immediately after successful CRC, while the validated packet is buffered.
    for i, byte in enumerate(packet):
        await b.word(byte, i == 0, i == len(packet) - 1)
    assert b.v("packet_good_o")
    await b.reset()
    await b.idle()
    assert not b.bus and not b.packets
    await b.enable()
    await b.tick(tx_ready_i=0)
    await b.send(request(0, BAR))
    await b.idle()
    assert b.v("tx_valid_o")
    await b.reset()
    await b.idle()
    assert not b.v("tx_valid_o") and not b.v("psel_o")
    assert await b.transact(request(4, CID << 16)) == [response(data=0x0000FFFF)]
