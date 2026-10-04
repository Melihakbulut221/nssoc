# SPDX-FileCopyrightText: 2026 Hasan Melih Akbulut
# SPDX-License-Identifier: Apache-2.0
"""Port-only DLLP checks, using the normal-polynomial independent oracle."""

import cocotb
from cocotb.triggers import Timer
from test_soc_pcie_packet_tx import expected_dllp


def dllp(body):
    normal = 0xFFFF
    for octet in body:
        for bit in range(8):
            feedback = ((normal >> 15) ^ (octet >> bit)) & 1
            normal = ((normal << 1) & 0xFFFF) ^ (0x100B if feedback else 0)
    normal ^= 0xFFFF
    field = sum(
        ((normal >> bit) & 1) << ((bit & 8) + 7 - (bit & 7)) for bit in range(16)
    )
    return bytes(body) + field.to_bytes(2, "big")


def fc_frame(phase, category, header, data):
    return dllp(
        [
            (0x40, 0xC0, 0x80)[phase] + category * 16,
            header >> 2,
            ((header & 3) << 6) | (data >> 8),
            data & 255,
        ]
    )


class Bench:
    def __init__(self, d):
        self.d = d
        self.acks, self.fc = [], []
        self.bad = self.unsupported = 0
        self.held = None

    def v(self, name):
        return int(getattr(self.d, name).value)

    async def tick(self, **signals):
        self.d.clk_i.value = 0
        for name, value in signals.items():
            getattr(self.d, name).value = value
        await Timer(5, unit="ns")
        accepted = self.v("rx_valid_i") and self.v("rx_ready_o")
        if self.v("rst_ni"):
            event = (self.v("ack_nak_o"), self.v("ack_sequence_o"))
            if self.held is not None:
                assert self.v("ack_valid_o") and event == self.held
            self.held = (
                event if self.v("ack_valid_o") and not self.v("ack_ready_i") else None
            )
            if self.v("ack_valid_o") and self.v("ack_ready_i"):
                self.acks.append(event)
        else:
            self.held = None
        self.d.clk_i.value = 1
        await Timer(5, unit="ns")
        self.bad += self.v("bad_dllp_o")
        self.unsupported += self.v("unsupported_dllp_o")
        if self.v("fc_valid_o"):
            self.fc.append(
                tuple(
                    self.v(n)
                    for n in ("fc_phase_o", "fc_class_o", "fc_header_o", "fc_data_o")
                )
            )
        return accepted

    async def reset(self):
        await self.tick(
            rst_ni=0,
            rx_valid_i=0,
            rx_data_i=0,
            rx_sop_i=0,
            rx_eop_i=0,
            rx_error_i=0,
            ack_ready_i=1,
        )
        await self.tick(rst_ni=1)
        self.acks.clear()
        self.fc.clear()
        self.bad = self.unsupported = 0

    async def send(self, data, error=-1):
        for i, byte in enumerate(data):
            for _ in range(100):
                if await self.tick(
                    rx_valid_i=1,
                    rx_data_i=byte,
                    rx_sop_i=i == 0,
                    rx_eop_i=i == len(data) - 1,
                    rx_error_i=i == error,
                ):
                    break
            else:
                raise AssertionError("DLLP input deadlock")
        await self.tick(rx_valid_i=0)


@cocotb.test()
async def exhaustive_ack_nak_and_vc0_credit_bit_fields(dut):
    b = Bench(dut)
    await b.reset()
    assert expected_dllp(0, 0) == dllp([0, 0, 0, 0])
    for nak in (0, 1):
        for seq in range(4096):
            await b.send(expected_dllp(nak, seq))
    assert b.acks == [(nak, seq) for nak in (0, 1) for seq in range(4096)]
    expected = []
    for phase in range(3):
        for cls in range(3):
            for header, data in (
                (0, 0),
                (1, 1),
                (3, 255),
                (4, 256),
                (127, 2047),
                (255, 4095),
            ):
                await b.send(fc_frame(phase, cls, header, data))
                expected.append((phase, cls, header, data))
    assert b.fc == expected and not b.bad and not b.unsupported


@cocotb.test()
async def corruption_reserved_vc_and_all_framing_fail_closed(dut):
    b = Bench(dut)
    await b.reset()
    for packet in (
        expected_dllp(0, 0x123),
        expected_dllp(1, 0xFFF),
        fc_frame(2, 2, 0x65, 0x789),
    ):
        for bit in range(48):
            damaged = bytearray(packet)
            damaged[bit // 8] ^= 1 << (bit % 8)
            await b.send(damaged)
    assert b.bad == 144 and not b.acks and not b.fc
    for body in (
        [0, 1, 0, 0],
        [0x10, 0, 0x10, 0],
        [0x41, 0, 0, 0],
        [0x40, 0x40, 0, 0],
        [0x40, 0, 0x10, 0],
        [0x70, 0, 0, 0],
    ):
        await b.send(dllp(body))
    assert b.unsupported == 6 and not b.acks and not b.fc
    p = expected_dllp(0, 12)
    for n in range(1, 6):
        await b.send(p[:n])
    await b.send(p + b"\0")
    for i in range(6):
        await b.send(p, error=i)
    assert b.bad == 156 and not b.acks
    # A new SOP explicitly discards an interrupted frame; only the new one may pass.
    await b.tick(rx_valid_i=1, rx_sop_i=1, rx_eop_i=0, rx_data_i=0, rx_error_i=0)
    await b.send(p)
    assert b.bad == 157 and b.acks == [(0, 12)]


@cocotb.test()
async def held_ack_reset_and_stream_gaps(dut):
    b = Bench(dut)
    await b.reset()
    await b.tick(ack_ready_i=0)
    await b.send(expected_dllp(1, 0x789))
    for _ in range(30):
        await b.tick(rx_valid_i=0)
        assert b.v("ack_valid_o") and not b.v("rx_ready_o")
    await b.tick(ack_ready_i=1)
    assert b.acks == [(1, 0x789)]
    await b.tick(ack_ready_i=0)
    await b.send(expected_dllp(0, 22))
    await b.reset()
    assert not b.v("ack_valid_o")
    p = expected_dllp(0, 23)
    for i, byte in enumerate(p):
        await b.tick(rx_valid_i=0, rx_error_i=1, rx_sop_i=1, rx_eop_i=1)
        await b.tick(
            rx_valid_i=1, rx_error_i=0, rx_data_i=byte, rx_sop_i=i == 0, rx_eop_i=i == 5
        )
    await b.tick(rx_valid_i=0)
    assert b.acks == [(0, 23)] and not b.bad
