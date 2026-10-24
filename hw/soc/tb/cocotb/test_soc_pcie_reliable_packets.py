# SPDX-FileCopyrightText: 2026 Hasan Melih Akbulut
# SPDX-License-Identifier: Apache-2.0
"""Public byte/APB integration of CRC DLLPs, reservation and exact retries."""

import cocotb
from cocotb.triggers import Timer
from test_soc_pcie_packet_endpoint import Bench as EndpointBench
from test_soc_pcie_tlp_stream import Bench as StreamBench, request, response, CID, BAR
from test_soc_pcie_tlp_integrity import frame_bytes, tlp_bytes
from test_soc_pcie_packet_tx import expected_dllp
from test_soc_pcie_dllp_rx import fc_frame


class Bench(EndpointBench):
    def __init__(self, d):
        super().__init__(d)
        self.reservations = []
        self.fc = []
        self.bad = 0

    async def tick(self, **signals):
        self.d.clk_i.value = 0
        for n, v in signals.items():
            getattr(self.d, n).value = v
        await Timer(5, unit="ns")
        accepted = self.v("rx_valid_i") and self.v("rx_ready_o")
        if self.v("rst_ni") and self.v("link_up_i"):
            if self.v("reserve_valid_o") and self.v("reserve_ready_i"):
                self.reservations.append(
                    tuple(
                        self.v(n)
                        for n in (
                            "reserve_class_o",
                            "reserve_payload_dw_o",
                            "reserve_replay_o",
                        )
                    )
                )
            beat = tuple(
                self.v(n)
                for n in (
                    "tx_data_o",
                    "tx_sop_o",
                    "tx_eop_o",
                    "tx_dllp_o",
                    "tx_replay_o",
                )
            )
            if self.held is not None:
                assert self.v("tx_valid_o") and beat == self.held
            self.held = (
                beat if self.v("tx_valid_o") and not self.v("tx_ready_i") else None
            )
            if self.v("tx_valid_o") and self.v("tx_ready_i"):
                data, sop, eop, kind, replay = beat
                assert bool(sop) == (not self.current)
                if sop:
                    self.kind = (kind, replay)
                assert self.kind == (kind, replay)
                self.current.append(data)
                if eop:
                    frame = bytes(self.current)
                    self.frames.append((kind, replay, frame))
                    self.current = []
                    if kind:
                        assert frame == expected_dllp(
                            frame[0] == 0x10, (frame[2] << 8) | frame[3]
                        )
                    else:
                        seq = (frame[0] << 8) | frame[1]
                        assert frame == frame_bytes(frame[2:-4], seq)
                        if not replay:
                            assert seq == self.tx_sequence
                            self.tx_sequence = (seq + 1) & 4095
                            header = 4 if frame[2] & 0x20 else 3
                            self.packets.append(
                                [
                                    int.from_bytes(
                                        frame[i : i + 4],
                                        "big" if (i - 2) // 4 < header else "little",
                                    )
                                    for i in range(2, len(frame) - 4, 4)
                                ]
                            )
            if self.v("psel_o") and self.v("penable_o") and self.v("pready_i"):
                self.bus.append(
                    tuple(
                        self.v(n)
                        for n in ("paddr_o", "pwrite_o", "pstrb_o", "pwdata_o")
                    )
                )
        else:
            self.held = None
            self.current = []
            self.tx_sequence = 0
        self.d.clk_i.value = 1
        await Timer(5, unit="ns")
        self.errors += self.v("error_o")
        self.bad += self.v("bad_dllp_o")
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
        if self.v("fc_valid_o"):
            self.fc.append(
                tuple(
                    self.v(n)
                    for n in ("fc_phase_o", "fc_class_o", "fc_header_o", "fc_data_o")
                )
            )
        return accepted

    async def reset(self):
        for n, v in dict(
            link_up_i=1, training_i=0, retrain_done_i=0, rx_dllp_i=0, reserve_ready_i=1
        ).items():
            getattr(self.d, n).value = v
        await StreamBench.reset(self)
        self.frames.clear()
        self.events.clear()
        self.reservations.clear()
        self.fc.clear()
        self.bad = 0

    async def control(self, data, error=None):
        await self.tick(rx_dllp_i=1)
        await self.wire(data, bad_at=error)
        await self.tick(rx_dllp_i=0)


@cocotb.test()
async def crc_checked_ack_nak_credit_hooks_and_exact_completion_replay(dut):
    b = Bench(dut)
    await b.reset()
    await b.tick(reserve_ready_i=0)
    await b.send(request(4, CID << 16))
    await b.idle(100)
    assert (
        b.frames == [(1, 0, expected_dllp(0, 0))]
        and b.v("buffered_o") == 1
        and not b.reservations
    )
    for phase in range(3):
        await b.control(fc_frame(phase, 2, 27, 0x345))
    assert b.fc == [(p, 2, 27, 0x345) for p in range(3)]
    await b.tick(reserve_ready_i=1)
    await b.idle(50)
    p = frame_bytes(tlp_bytes(response(data=0xFFFF)), 0)
    assert b.frames[-1] == (0, 0, p) and b.reservations == [(2, 1, 0)]
    bad = bytearray(expected_dllp(0, 0))
    bad[3] ^= 1
    await b.control(bad)
    await b.idle(10)
    assert b.v("outstanding_o") == 1 and b.bad == 1
    await b.control(expected_dllp(1, 4095))
    await b.idle(80)
    assert b.frames[-1] == (0, 1, p) and len(b.reservations) == 1
    await b.control(expected_dllp(0, 0))
    await b.idle(10)
    assert b.v("buffered_o") == 0 and b.v("acknowledged_sequence_o") == 0 and not b.bus


@cocotb.test()
async def multiple_stored_completions_cumulative_ack_and_duplicate_no_apb(dut):
    b = Bench(dut)
    await b.reset()
    await b.enable()
    # Free both configuration completions; the wire ACK cannot affect RX sequence.
    await b.control(expected_dllp(0, 1))
    await b.idle(5)
    assert b.v("buffered_o") == 0
    await b.tick(reserve_ready_i=0)
    for i in range(3):
        await b.send(request(0, BAR + 4 * i, tag=i))
        await b.idle(50)
    assert len(b.bus) == 3 and b.v("buffered_o") == 3 and b.v("outstanding_o") == 0
    old = len(b.reservations)
    await b.control(expected_dllp(0, 4))
    await b.idle(5)
    assert b.v("buffered_o") == 3
    await b.tick(reserve_ready_i=1)
    await b.idle(130)
    assert b.v("outstanding_o") == 3 and len(b.reservations) == old + 3
    original = [f for f in b.frames if not f[0] and not f[1]][-3:]
    await b.control(expected_dllp(0, 2))
    await b.control(expected_dllp(1, 2))
    await b.idle(100)
    assert [f[2] for f in b.frames if f[1]] == [f[2] for f in original[1:]]
    assert len(b.bus) == 3 and len(b.reservations) == old + 3
    await b.control(expected_dllp(0, 4))
    await b.idle(5)
    seq = b.v("rx_expected_sequence_o")
    w = request(0x40, BAR + 0x30, [0x12345678])
    await b.send(w)
    await b.idle(40)
    await b.send(w, sequence=seq)
    await b.idle(40)
    assert b.bus[-1] == (0x30, 1, 15, 0x12345678) and len(b.bus) == 4


@cocotb.test()
async def stalled_arbitration_type_error_and_link_reset_discard_retries(dut):
    b = Bench(dut)
    await b.reset()
    await b.tick(tx_ready_i=0)
    await b.send(request(4, CID << 16))
    await b.idle(50)
    assert b.v("tx_valid_o")
    await b.idle(30)
    await b.tick(tx_ready_i=1)
    await b.idle(60)
    assert len(b.frames) == 2 and b.v("outstanding_o") == 1
    await b.tick(link_up_i=0)
    await b.tick(link_up_i=1)
    b.frames.clear()
    b.packets.clear()
    await b.idle(1100)
    assert (
        not b.frames and b.v("buffered_o") == 0 and b.v("rx_expected_sequence_o") == 0
    )
    # A physical frame-type flip is an error on the already selected receiver.
    p = frame_bytes(tlp_bytes(request(4, CID << 16)), 0)
    for i, byte in enumerate(p):
        await b.word(byte, i == 0, i == len(p) - 1, 0)
        if i == 3:
            await b.tick(rx_valid_i=0, rx_dllp_i=1)
    await b.tick(rx_valid_i=0, rx_dllp_i=0)
    await b.idle(50)
    assert b.v("rx_expected_sequence_o") == 0 and not b.packets and not b.bus
    await b.reset()
    await b.send(request(4, CID << 16))
    await b.idle(80)
    assert b.packets == [response(data=0xFFFF)]


@cocotb.test()
async def stalled_replay_first_byte_cannot_be_preempted_by_new_ack(dut):
    b = Bench(dut)
    await b.reset()
    await b.send(request(4, CID << 16))
    await b.idle(80)
    original = b.frames[-1][2]
    await b.tick(tx_ready_i=0)
    await b.control(expected_dllp(1, 4095))
    await b.idle(10)
    assert b.v("tx_valid_o") and b.v("tx_replay_o") and not b.v("tx_dllp_o")
    await b.send(request(4, CID << 16))
    await b.idle(40)
    await b.tick(tx_ready_i=1)
    await b.idle(100)
    assert b.frames[2] == (0, 1, original)
    assert b.frames[3] == (1, 0, expected_dllp(0, 1))
    assert b.frames[4][0:2] == (0, 0) and len(b.reservations) == 2
    await b.control(expected_dllp(0, 1))
    await b.idle(10)
    assert b.v("buffered_o") == 0
