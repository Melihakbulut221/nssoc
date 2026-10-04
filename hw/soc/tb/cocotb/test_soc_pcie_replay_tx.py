# SPDX-FileCopyrightText: 2026 Hasan Melih Akbulut
# SPDX-License-Identifier: Apache-2.0
"""Exact encoded byte replay, queue ownership, modulo ACK and recovery controls."""

import random
import cocotb
from cocotb.triggers import Timer
from test_soc_pcie_tlp_integrity import frame_bytes


def packet(seq, kind=0, payload=b""):
    words = len(payload) // 4
    body = bytes([kind, 0, (words >> 8) & 3, words & 255]) + bytes(range(8)) + payload
    return frame_bytes(body, seq & 4095)


class Bench:
    def __init__(self, d):
        self.d = d
        self.frames = []
        self.current = []
        self.held = None
        self.reservations = []
        self.events = []
        self.cycle = 0
        self.frame_cycles = []

    def v(self, n):
        return int(getattr(self.d, n).value)

    async def tick(self, **signals):
        self.d.clk_i.value = 0
        for n, v in signals.items():
            getattr(self.d, n).value = v
        await Timer(5, unit="ns")
        accepted = self.v("in_valid_i") and self.v("in_ready_o")
        acked = self.v("ack_valid_i") and self.v("ack_ready_o")
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
            beat = (
                tuple(
                    self.v(n)
                    for n in ("tx_data_o", "tx_sop_o", "tx_eop_o", "tx_replay_o")
                )
                if self.v("tx_valid_o")
                else None
            )
            if self.held is not None:
                assert beat == self.held, "Stalled encoded output changed"
            self.held = beat if beat is not None and not self.v("tx_ready_i") else None
            if beat is not None and self.v("tx_ready_i"):
                data, sop, eop, replay = beat
                assert bool(sop) == (not self.current)
                if sop:
                    self.kind = replay
                assert self.kind == replay
                self.current.append(data)
                if eop:
                    self.frames.append((replay, bytes(self.current)))
                    self.current = []
                    self.frame_cycles.append(self.cycle)
        else:
            self.held = None
            self.current = []
        self.d.clk_i.value = 1
        await Timer(5, unit="ns")
        self.cycle += 1
        self.events.append(
            tuple(
                self.v(n) for n in ("replay_started_o", "timeout_o", "protocol_error_o")
            )
        )
        return accepted, acked

    async def reset(self):
        await self.tick(
            rst_ni=0,
            link_up_i=1,
            training_i=0,
            retrain_done_i=0,
            in_valid_i=0,
            in_data_i=0,
            in_sop_i=0,
            in_eop_i=0,
            ack_valid_i=0,
            ack_nak_i=0,
            ack_sequence_i=0,
            reserve_ready_i=1,
            tx_ready_i=1,
        )
        await self.tick(rst_ni=1)
        self.frames.clear()
        self.reservations.clear()
        self.events.clear()
        self.frame_cycles.clear()
        assert (
            self.v("buffered_o") == self.v("outstanding_o") == 0
            and self.v("acknowledged_sequence_o") == 4095
        )

    async def idle(self, n=1, **signals):
        for _ in range(n):
            await self.tick(in_valid_i=0, **signals)

    async def send(self, data):
        for i, byte in enumerate(data):
            for _ in range(20000):
                yes, _ = await self.tick(
                    in_valid_i=1,
                    in_data_i=byte,
                    in_sop_i=i == 0,
                    in_eop_i=i == len(data) - 1,
                )
                if yes:
                    break
            else:
                raise AssertionError("Input deadlock")
        await self.tick(in_valid_i=0)

    async def ack(self, seq, nak=0):
        for _ in range(20000):
            _, yes = await self.tick(
                in_valid_i=0, ack_valid_i=1, ack_nak_i=nak, ack_sequence_i=seq & 4095
            )
            if yes:
                break
        else:
            raise AssertionError("ACK deadlock")
        await self.tick(ack_valid_i=0)

    async def until_frames(self, count, limit=10000):
        for _ in range(limit):
            if len(self.frames) >= count:
                return
            await self.idle()
        raise AssertionError(("Missing frames", count, len(self.frames)))


@cocotb.test()
async def full_queue_cumulative_ack_only_fully_sent_and_nak_preserves_bytes(dut):
    b = Bench(dut)
    await b.reset()
    await b.tick(reserve_ready_i=0)
    frames = [
        packet(0),
        packet(1, 0x40, b"abcd"),
        packet(2, 0x4A, b"abcdefgh"),
        packet(3, 0x10),
    ]
    for p in frames:
        await b.send(p)
    assert (
        b.v("buffered_o") == 4
        and not b.v("in_ready_o")
        and not b.frames
        and not b.reservations
    )
    await b.ack(2)
    assert b.v("buffered_o") == 4 and sum(e[2] for e in b.events) == 1
    await b.tick(reserve_ready_i=1)
    rng = random.Random(77)
    for _ in range(250):
        await b.tick(tx_ready_i=rng.randrange(2))
    await b.idle(tx_ready_i=1)
    await b.until_frames(4)
    assert b.frames == [(0, p) for p in frames]
    assert b.reservations == [(1, 0, 0), (0, 1, 0), (2, 2, 0), (0, 0, 0)]
    await b.ack(1)
    assert b.v("buffered_o") == b.v("outstanding_o") == 2
    await b.ack(0)  # stale: cannot reclaim anything
    assert b.v("buffered_o") == 2
    await b.ack(1, nak=1)
    await b.until_frames(6)
    assert b.frames[4:] == [(1, p) for p in frames[2:]] and len(b.reservations) == 4
    await b.ack(3)
    assert b.v("buffered_o") == b.v("outstanding_o") == 0


@cocotb.test()
async def pending_ack_during_replay_and_new_frame_credit_are_atomic(dut):
    b = Bench(dut)
    await b.reset()
    await b.send(packet(0))
    await b.until_frames(1)
    await b.send(packet(1))
    await b.until_frames(2)
    await b.ack(4095, nak=1)
    await b.tick(tx_ready_i=0)
    await b.idle(5)
    assert b.v("tx_valid_o") and b.v("tx_replay_o")
    await b.tick(ack_valid_i=1, ack_nak_i=0, ack_sequence_i=1)
    await b.idle(10)
    assert not b.v("ack_ready_o") and b.v("outstanding_o") == 2
    await b.tick(tx_ready_i=1)
    for _ in range(100):
        if not b.v("outstanding_o"):
            break
        await b.idle()
    await b.tick(ack_valid_i=0)
    assert b.frames == [(0, packet(0)), (0, packet(1)), (1, packet(0)), (1, packet(1))]
    assert b.v("buffered_o") == 0 and len(b.reservations) == 2
    # Queued packet while a second is captured must not debit the first repeatedly.
    await b.tick(reserve_ready_i=0)
    await b.send(packet(2))
    await b.tick(in_valid_i=1, in_sop_i=1, in_eop_i=0, in_data_i=0)
    await b.tick(in_valid_i=0, reserve_ready_i=1)
    await b.idle(20)
    assert len(b.reservations) == 2 and not b.v("reserve_valid_o")
    await b.reset()  # discard unfinished source frame and all ownership
    await b.idle(20)
    assert not b.frames


@cocotb.test()
async def timeout_duplicate_ack_training_pause_exhaustion_and_recovery(dut):
    b = Bench(dut)
    await b.reset()
    p = packet(0)
    await b.send(p)
    await b.until_frames(1)
    await b.idle(400, training_i=1)
    assert not any(e[1] for e in b.events)
    await b.idle(500, training_i=0)
    await b.ack(4095)  # duplicate does not restart the timer
    await b.idle(530)
    assert sum(e[1] for e in b.events) == 1
    await b.until_frames(2)
    await b.idle(4000)
    assert b.frames == [(0, p)] + [(1, p)] * 3 and len(b.reservations) == 1
    assert (
        b.v("retry_exhausted_o") and b.v("retrain_request_o") and b.v("buffered_o") == 1
    )
    await b.tick(retrain_done_i=1)
    await b.tick(retrain_done_i=0)
    await b.until_frames(5)
    assert b.frames[-1] == (1, p) and not b.v("retry_exhausted_o")
    await b.ack(0)
    await b.idle(1100)
    assert b.v("outstanding_o") == 0 and len(b.frames) == 5
    await b.tick(link_up_i=0)
    await b.tick(link_up_i=1)
    assert b.v("acknowledged_sequence_o") == 4095 and b.v("buffered_o") == 0


@cocotb.test()
async def modulo_wrap_4097_real_packets_and_cumulative_window(dut):
    b = Bench(dut)
    await b.reset()
    for seq in range(4093):
        await b.send(packet(seq))
        await b.until_frames(seq + 1)
        await b.ack(seq)
    for seq in range(4093, 4097):
        await b.send(packet(seq))
    await b.until_frames(4097)
    assert b.v("outstanding_o") == 4
    await b.ack(4094)
    assert b.v("buffered_o") == 2 and b.v("acknowledged_sequence_o") == 4094
    await b.ack(4094, nak=1)
    await b.until_frames(4099)
    assert b.frames[-2:] == [(1, packet(4095)), (1, packet(0))]
    await b.ack(0)
    assert b.v("buffered_o") == 0 and len(b.reservations) == 4097
    assert all(
        frame == packet(i) and kind == 0
        for i, (kind, frame) in enumerate(b.frames[:4097])
    )


@cocotb.test()
async def corrupted_source_wrong_sequence_capacity_and_reset_cannot_escape(dut):
    b = Bench(dut)
    p = packet(0)
    for bit in (0, 15, 16, 31, 79, 112, 143):
        await b.reset()
        bad = bytearray(p)
        bad[bit // 8] ^= 1 << (bit % 8)
        await b.send(bad)
        await b.idle(10)
        assert (
            b.v("source_error_o")
            and b.v("retrain_request_o")
            and not b.frames
            and not b.reservations
        )
        await b.tick(retrain_done_i=1)
        await b.idle(5)
        assert b.v("source_error_o") and b.v("retrain_request_o")
    for bad in (packet(1), packet(0, 0x40, bytes(24))[:39]):
        await b.reset()
        await b.send(bad)
        await b.idle(5)
        assert b.v("source_error_o") and not b.frames
    await b.reset()
    await b.send(packet(0, 0x40, bytes(20)))
    await b.until_frames(1)
    assert len(b.frames[0][1]) == 38
    await b.reset()
    await b.tick(tx_ready_i=0)
    await b.send(p)
    await b.idle(5)
    assert b.v("tx_valid_o")
    await b.reset()
    await b.idle(30)
    assert not b.frames and not b.v("tx_valid_o")


@cocotb.test()
async def expiry_preempts_new_credit_and_frame_but_not_an_inflight_packet(dut):
    b = Bench(dut)
    await b.reset()
    await b.send(packet(0))
    await b.until_frames(1)
    expiry = b.frame_cycles[0] + 1024
    await b.tick(reserve_ready_i=0)
    await b.send(packet(1))
    while b.cycle < expiry:
        await b.idle()
    await b.tick(reserve_ready_i=1)
    assert b.v("timeout_o") and len(b.reservations) == 1
    await b.until_frames(3)
    assert b.frames == [(0, packet(0)), (1, packet(0)), (0, packet(1))]
    assert len(b.reservations) == 2
    await b.ack(1)
    assert b.v("buffered_o") == 0
    # Training pauses new scheduling and the timer, never splits an already
    # reserved frame. Further source packets may fill the bounded store.
    await b.tick(tx_ready_i=0)
    await b.send(packet(2))
    await b.idle(3)
    assert b.v("tx_valid_o")
    await b.tick(training_i=1, tx_ready_i=1)
    await b.until_frames(4)
    await b.send(packet(3))
    await b.idle(1100)
    assert len(b.frames) == 4 and len(b.reservations) == 3
    assert not b.v("reserve_valid_o") and not b.v("retry_exhausted_o")
    await b.tick(training_i=0)
    await b.until_frames(5)
    await b.ack(3)
    assert b.v("buffered_o") == 0


@cocotb.test()
async def early_ack_is_classified_before_waiting_for_transmit_end(dut):
    b = Bench(dut)
    await b.reset()
    await b.tick(tx_ready_i=0)
    await b.send(packet(0))
    await b.idle(3)
    assert b.v("tx_valid_o") and b.v("outstanding_o") == 0
    await b.tick(ack_valid_i=1, ack_nak_i=0, ack_sequence_i=0)
    await b.idle(8)
    assert not b.v("ack_ready_o")
    await b.tick(tx_ready_i=1)
    for _ in range(100):
        _, accepted = await b.tick(in_valid_i=0)
        if accepted:
            break
    else:
        raise AssertionError("Deferred invalid ACK never consumed")
    await b.tick(ack_valid_i=0)
    assert b.v("outstanding_o") == b.v("buffered_o") == 1
    assert b.v("acknowledged_sequence_o") == 4095
    assert sum(e[2] for e in b.events) == 1
    # The same sequence is valid only as a later received ACK.
    await b.ack(0)
    assert b.v("buffered_o") == 0
    # 2048 is outside the small forward window; 2049 is stale modulo 4096.
    await b.ack(2048)
    assert sum(e[2] for e in b.events) == 2
    await b.ack(2049)
    assert sum(e[2] for e in b.events) == 2
