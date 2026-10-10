# SPDX-FileCopyrightText: 2026 Hasan Melih Akbulut
# SPDX-License-Identifier: Apache-2.0
"""Complete packet-boundary tests: actual local FC, sequence/LCRC and APB."""

import random
import cocotb
from cocotb.triggers import Timer
from pcie_rx_flow_common import (
    fc_frame,
    decode_fc,
    frame_bytes,
    tlp_bytes,
    request,
    response,
    CID,
    BAR,
    expected_dllp,
)


class Bench:
    def __init__(self, d):
        self.d = d
        self.frames = []
        self.bus = []
        self.releases = []
        self.partial = []
        self.held = None
        self.accepted = 0
        self.duplicates = 0
        self.rejected = 0
        self.dropped = 0
        self.grants = []

    def v(self, n):
        return int(getattr(self.d, n).value)

    async def tick(self, **kw):
        self.d.clk_i.value = 0
        for n, v in kw.items():
            getattr(self.d, n).value = v
        await Timer(5, unit="ns")
        taken = self.v("rx_valid_i") and self.v("rx_ready_o")
        if self.v("rst_ni") and self.v("link_up_i") and not self.v("retrain_done_i"):
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
                x, sop, eop, kind, replay = beat
                assert bool(sop) == (not self.partial)
                if sop:
                    self.kind = kind
                    self.replay = replay
                assert (kind, replay) == (self.kind, self.replay)
                self.partial.append(x)
                if eop:
                    frame = bytes(self.partial)
                    self.frames.append((kind, replay, frame))
                    self.partial = []
                    if kind:
                        if frame[0] in (0, 0x10):
                            assert frame == expected_dllp(
                                frame[0] == 0x10, ((frame[2] & 15) << 8) | frame[3]
                            )
                        else:
                            decode_fc(frame)
                    else:
                        assert frame == frame_bytes(
                            frame[2:-4], int.from_bytes(frame[:2], "big")
                        )
                        # Hardware has no outbound non-posted request source.
                        assert frame[2] & 31 == 10
            if self.v("psel_o") and self.v("penable_o") and self.v("pready_i"):
                self.bus.append(
                    tuple(
                        self.v(n)
                        for n in ("paddr_o", "pwrite_o", "pstrb_o", "pwdata_o")
                    )
                )
            if self.v("reserve_valid_o") and self.v("reserve_ready_o"):
                self.grants.append(
                    (
                        self.v("reserve_class_o"),
                        self.v("reserve_payload_dw_o"),
                        self.v("reserve_replay_o"),
                    )
                )
        else:
            self.partial = []
            self.held = None
        self.d.clk_i.value = 1
        await Timer(5, unit="ns")
        for field, name in (
            ("accepted", "packet_accepted_o"),
            ("duplicates", "packet_duplicate_o"),
            ("rejected", "packet_rejected_o"),
            ("dropped", "rx_dropped_o"),
        ):
            setattr(self, field, getattr(self, field) + self.v(name))
        if self.v("rx_released_o"):
            self.releases.append(
                (self.v("rx_released_class_o"), self.v("rx_released_data_o"))
            )
        return taken

    async def reset(self):
        await self.tick(
            rst_ni=0,
            link_up_i=0,
            training_i=0,
            retrain_done_i=0,
            function_id_i=CID,
            rx_valid_i=0,
            rx_sop_i=0,
            rx_eop_i=0,
            rx_error_i=0,
            rx_dllp_i=0,
            rx_data_i=0,
            tx_ready_i=1,
            pready_i=1,
            pslverr_i=0,
            prdata_i=0x12345678,
        )
        await self.tick(rst_ni=1, link_up_i=1)

    async def idle(self, n=80, **kw):
        for _ in range(n):
            await self.tick(rx_valid_i=0, rx_sop_i=0, rx_eop_i=0, **kw)

    async def wire(self, frame, dllp=0, error=0):
        for i, x in enumerate(frame):
            for _ in range(500):
                if await self.tick(
                    rx_valid_i=1,
                    rx_data_i=x,
                    rx_sop_i=i == 0,
                    rx_eop_i=i == len(frame) - 1,
                    rx_dllp_i=dllp,
                    rx_error_i=error,
                ):
                    break
            else:
                raise AssertionError("Ingress stalled indefinitely")
        await self.tick(rx_valid_i=0, rx_sop_i=0, rx_eop_i=0, rx_error_i=0)

    async def initialize(self, stall=False):
        if stall:
            await self.tick(tx_ready_i=0)
        for c in range(3):
            await self.wire(fc_frame(0, c, 0 if c == 2 else 8, 0 if c == 2 else 16), 1)
        await self.wire(fc_frame(1, 0, 8, 16), 1)
        if stall:
            await self.idle(40)
            assert (
                not self.v("local_init_done_o")
                and not self.v("initialized_o")
                and not self.v("fc_sent_header_o")
            )
        await self.idle(140, tx_ready_i=1)
        assert self.v("initialized_o") and self.v("local_init_done_o")
        assert not self.v("requester_admission_o") and not self.v(
            "outstanding_requests_o"
        )
        init = [
            decode_fc(f) for k, _, f in self.frames if k and f[0] & 0xC0 in (0x40, 0xC0)
        ]
        for p in (0, 1):
            assert [
                (p, c, 0 if c == 2 else 2, 0 if c == 2 else 4) for c in range(3)
            ] == [x for x in init if x[0] == p][:3]

    async def tlp(self, words, seq):
        await self.wire(frame_bytes(tlp_bytes(words), seq))

    async def ack_all(self):
        frames = [f for k, replay, f in self.frames if not k and not replay]
        if frames:
            await self.wire(expected_dllp(0, int.from_bytes(frames[-1][:2], "big")), 1)

    async def enable(self):
        await self.tlp(request(0x44, CID << 16 | 0x10, [BAR]), 0)
        await self.idle(110)
        await self.ack_all()
        await self.tlp(request(0x44, CID << 16 | 4, [2]), 1)
        await self.idle(110)
        await self.ack_all()
        assert self.v("memory_enable_o") and self.v("bar0_o") == BAR
        self.bus = []

    def completions(self):
        return [f for k, r, f in self.frames if not k and not r]


@cocotb.test()
async def real_local_initialization_and_fair_fc_ack_completion_frames(d):
    b = Bench(d)
    await b.reset()
    await b.initialize(stall=True)
    await b.tlp(request(4, CID << 16, tag=7), 0)
    rng = random.Random(0xCAFE)
    for _ in range(180):
        await b.tick(rx_valid_i=0, tx_ready_i=rng.randrange(4) != 0)
    await b.idle(30, tx_ready_i=1)
    assert b.completions() == [frame_bytes(tlp_bytes(response(data=0xFFFF, tag=7)), 0)]
    assert (1, 0, expected_dllp(0, 0)) in b.frames and b.releases == [(1, 0)]
    assert (b.v("rx_header_limit_o") >> 8) & 255 == 3
    updates = [decode_fc(f) for k, _, f in b.frames if k and f[0] & 0xC0 == 0x80]
    assert (2, 1, 3, 4) in updates and all(
        x[2:] == (0, 0) for x in updates if x[1] == 2
    )
    assert b.grants == [(2, 1, 0)] and not b.bus


@cocotb.test()
async def corrupt_duplicate_future_and_bad_tail_do_not_rewrite_or_return_credits(d):
    b = Bench(d)
    await b.reset()
    await b.initialize()
    await b.enable()
    good = frame_bytes(tlp_bytes(request(0x40, BAR + 0x20, [0x76543210])), 2)
    await b.wire(good)
    await b.idle(90)
    expected_bus = [(0x20, 1, 15, 0x76543210)]
    assert b.bus == expected_bus
    baseline = (b.v("rx_header_limit_o"), b.v("rx_data_limit_o"), len(b.releases))
    await b.wire(good)
    await b.idle(65)
    for bit in (0, 7, 16, 31):
        bad = bytearray(
            frame_bytes(tlp_bytes(request(0x40, BAR + 0x24, [0xFFFFFFFF])), 3)
        )
        bad[-4 + bit // 8] ^= 1 << (bit % 8)
        await b.wire(bad)
        await b.idle(60)
    await b.tlp(request(0x40, BAR + 0x24, [0xFFFFFFFF]), 5)
    await b.idle(65)
    assert b.bus == expected_bus and b.duplicates == 1 and b.rejected == 5
    assert baseline == (
        b.v("rx_header_limit_o"),
        b.v("rx_data_limit_o"),
        len(b.releases),
    )
    # Correct CRC but incompatible packet length, followed by a trailing byte.
    badshape = frame_bytes(tlp_bytes(request(0x40, BAR + 0x28, [1], length=2)), 3)
    await b.wire(badshape)
    await b.idle(20)
    await b.wire(good + b"\0")
    await b.idle(20)
    assert b.dropped == 2 and b.v("rx_recovery_o") and b.bus == expected_bus


@cocotb.test()
async def bounded_pressure_no_side_effect_before_release_and_dllp_progress(d):
    b = Bench(d)
    await b.reset()
    await b.initialize()
    await b.enable()
    await b.tick(pready_i=0, tx_ready_i=0)
    for seq in range(2, 6):
        await b.tlp(request(0x40, BAR + 4 * seq, [seq]), seq)
    await b.idle(15)
    assert not b.bus
    assert b.v("rx_occupied_o") & 255 <= 2
    # A DLLP can enter its independent buffer while queued TLPs are blocked.
    await b.wire(fc_frame(2, 0, 20, 32), 1)
    await b.idle(230, pready_i=1, tx_ready_i=1)
    assert b.bus == [(4 * s, 1, 15, s) for s in range(2, 6)]
    assert b.v("rx_expected_sequence_o") == 6 and b.v("rx_queued_o") == 0
    assert b.v("credit_header_limit_o") & 255 == 20
    assert len(b.releases) == 6 and not b.v("rx_recovery_o")

    # Fill all replay slots without ACKing them. A fifth completion must retain
    # its first byte while stalled, then drain exactly once after a cumulative ACK.
    b = Bench(d)
    await b.reset()
    await b.initialize()
    for seq in range(4):
        await b.tlp(request(4, CID << 16, tag=seq), seq)
        for _ in range(160):
            await b.idle(1)
            if len(b.completions()) == seq + 1:
                break
        else:
            raise AssertionError("Completion did not reach the replay window")
    expected = [
        frame_bytes(tlp_bytes(response(data=0xFFFF, tag=seq)), seq)
        for seq in range(5)
    ]
    assert b.completions() == expected[:4]
    assert b.v("buffered_o") == 4 and b.v("outstanding_o") == 4
    await b.tlp(request(4, CID << 16, tag=4), 4)
    await b.idle(90)
    assert b.completions() == expected[:4] and not b.v("source_error_o")
    await b.wire(expected_dllp(0, 3), 1)
    await b.idle(140)
    assert b.completions() == expected
    assert b.v("buffered_o") == 1 and b.v("outstanding_o") == 1
    assert not b.v("source_error_o") and not b.v("retrain_request_o")


@cocotb.test()
async def unexpected_completions_are_quarantined_and_retraining_restarts_epoch(d):
    b = Bench(d)
    await b.reset()
    await b.initialize()
    await b.tlp(response(data=0x12345678), 0)
    await b.idle(60)
    assert b.dropped == 1 and b.v("rx_recovery_o") and b.v("retrain_request_o")
    assert not b.bus and not b.releases and b.v("rx_expected_sequence_o") == 0
    assert b.v("rx_header_limit_o") >> 16 == 0 and b.v("rx_data_limit_o") >> 24 == 0
    await b.tick(retrain_done_i=1, tx_ready_i=0)
    assert (
        not b.v("initialized_o") and not b.v("rx_recovery_o") and not b.v("tx_valid_o")
    )
    b.frames = []
    await b.tick(retrain_done_i=0, tx_ready_i=1)
    await b.initialize()
    await b.tlp(request(4, CID << 16), 0)
    await b.idle(110)
    assert len(b.completions()) == 1 and b.accepted == 1
    await b.tick(training_i=1)
    await b.idle(20)
    assert not b.v("tx_valid_o")
    await b.tick(rst_ni=0)
    assert not b.v("rx_ready_o") and not b.v("tx_valid_o") and not b.v("psel_o")


@cocotb.test()
async def first_valid_tlp_can_confirm_peer_init2_without_circular_gate(d):
    b = Bench(d)
    await b.reset()
    for c in range(3):
        await b.wire(fc_frame(0, c, 0 if c == 2 else 8, 0 if c == 2 else 16), 1)
    await b.idle(90)
    assert b.v("peer_init1_done_o") and b.v("local_init2_sent_o")
    assert not b.v("peer_init2_seen_o") and not b.v("initialized_o")
    # A TLP is a normative peer-confirmation alternative to another Init2/Update.
    await b.tlp(request(4, CID << 16, tag=6), 0)
    await b.idle(130)
    assert (
        b.v("peer_init2_seen_o") and b.v("local_init_done_o") and b.v("initialized_o")
    )
    assert b.completions() == [frame_bytes(tlp_bytes(response(data=0xFFFF, tag=6)), 0)]
    assert b.releases == [(1, 0)]
