# SPDX-FileCopyrightText: 2026 Hasan Melih Akbulut
# SPDX-License-Identifier: Apache-2.0
"""Finite three-class storage component: real bytes, consumer outcomes, no APB."""

import cocotb
from cocotb.triggers import Timer
from pcie_rx_flow_common import frame_bytes, tlp_bytes, request, fc_frame


class Bench:
    def __init__(self, d):
        self.d = d
        self.frames = []
        self.current = []
        self.releases = []
        self.held = None

    def v(self, n):
        return int(getattr(self.d, n).value)

    async def tick(self, **kw):
        self.d.clk_i.value = 0
        for n, v in kw.items():
            getattr(self.d, n).value = v
        await Timer(5, unit="ns")
        accepted = self.v("rx_valid_i") and self.v("rx_ready_o")
        if self.v("rst_ni") and self.v("link_up_i"):
            if self.v("out_valid_o"):
                beat = tuple(
                    self.v(n)
                    for n in (
                        "out_data_o",
                        "out_sop_o",
                        "out_eop_o",
                        "out_dllp_o",
                        "out_error_o",
                    )
                )
                if self.held is not None:
                    assert beat == self.held
                self.held = beat if not self.v("out_ready_i") else None
                if self.v("out_ready_i"):
                    assert bool(beat[1]) == (not self.current)
                    if beat[1]:
                        self.kind = beat[3]
                        self.bad = beat[4]
                    assert beat[3] == self.kind and beat[4] == self.bad
                    self.current.append(beat[0])
                    if beat[2]:
                        self.frames.append((self.kind, self.bad, bytes(self.current)))
                        self.current = []
            else:
                assert self.held is None
        else:
            self.held = None
            self.current = []
        self.d.clk_i.value = 1
        await Timer(5, unit="ns")
        if self.v("released_o"):
            self.releases.append(
                (self.v("released_class_o"), self.v("released_data_o"))
            )
        return accepted

    async def reset(self):
        await self.tick(
            rst_ni=0,
            link_up_i=0,
            training_i=0,
            initialized_i=1,
            rx_valid_i=0,
            rx_data_i=0,
            rx_sop_i=0,
            rx_eop_i=0,
            rx_error_i=0,
            rx_dllp_i=0,
            out_ready_i=0,
            packet_accepted_i=0,
            packet_duplicate_i=0,
            packet_rejected_i=0,
        )
        await self.tick(rst_ni=1, link_up_i=1)

    async def idle(self, n=5, **kw):
        for _ in range(n):
            await self.tick(rx_valid_i=0, **kw)

    async def send(self, frame, dllp=0, error=0):
        for i, x in enumerate(frame):
            for _ in range(300):
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
                raise AssertionError("RX blocked")
        await self.idle(3, rx_sop_i=0, rx_eop_i=0, rx_error_i=0)

    async def consume(self, outcome="accepted"):
        count = len(self.frames)
        for _ in range(120):
            await self.tick(rx_valid_i=0, out_ready_i=1)
            if len(self.frames) > count:
                break
        else:
            raise AssertionError("No complete output")
        await self.tick(out_ready_i=0, **{"packet_" + outcome + "_i": 1})
        await self.tick(**{"packet_" + outcome + "_i": 0})


@cocotb.test()
async def three_dedicated_classes_actual_ownership_order_and_release(d):
    b = Bench(d)
    await b.reset()
    packets = [
        frame_bytes(
            tlp_bytes(request(kind, payload=([c + 8] if kind & 0x40 else []))), c
        )
        for c, kind in enumerate((0x40, 0x04, 0x4A))
    ]
    for f in packets:
        await b.send(f)
    assert b.v("occupied_o") == 0x010101 and b.v("queued_o") == 3
    assert b.v("header_limit_o") == 0x020202 and b.v("data_limit_o") == 0x004004004
    for _ in packets:
        await b.consume()
    assert [f[2] for f in b.frames] == packets and b.releases == [
        (0, 1),
        (1, 0),
        (2, 1),
    ]
    assert b.v("header_limit_o") == 0x030303 and b.v("data_limit_o") == 0x005004005
    assert not b.v("occupied_o") and not b.v("queued_o")


@cocotb.test()
async def full_class_pressure_retains_packet_and_dllp_bypasses(d):
    b = Bench(d)
    await b.reset()
    packets = [frame_bytes(tlp_bytes(request(0x40, payload=[i])), i) for i in range(3)]
    for f in packets:
        await b.send(f)
    assert b.v("occupied_o") == 2 and b.v("queued_o") == 2
    await b.tick(rx_valid_i=1, rx_sop_i=1, rx_dllp_i=0)
    assert not b.v("rx_ready_o")
    control = fc_frame(2, 2, 7, 9)
    await b.send(control, dllp=1)
    await b.idle(8, out_ready_i=1)
    assert b.frames == [(1, 0, control)]
    await b.idle(45, out_ready_i=1)
    assert b.frames[1][2] == packets[0]
    await b.tick(out_ready_i=0, packet_accepted_i=1)
    await b.tick(packet_accepted_i=0)
    await b.idle(3)
    assert b.v("queued_o") == 2 and b.v("occupied_o") == 2
    await b.consume("duplicate")
    await b.consume("rejected")
    assert [f[2] for f in b.frames[1:]] == packets
    assert b.releases == [(0, 1)] and (b.v("header_limit_o") & 255) == 3


@cocotb.test()
async def modulo_release_and_bad_shapes_never_mint_credit(d):
    b = Bench(d)
    await b.reset()
    frame = frame_bytes(tlp_bytes(request(0x40, payload=[0xAABBCCDD])), 0)
    for _ in range(260):
        await b.send(frame)
        await b.consume()
    assert b.v("header_limit_o") & 255 == 6 and b.v("data_limit_o") & 4095 == 264
    limits = (b.v("header_limit_o"), b.v("data_limit_o"))
    malformed = [
        frame[:-1],
        frame + b"\0",
        frame_bytes(tlp_bytes(request(0x40, payload=[1] * 6, length=6)), 0),
        b"\x00",
        frame_bytes(tlp_bytes([0x40000002, 0, 0, 1]), 0),
    ]
    old = len(b.frames)
    for f in malformed:
        await b.send(f)
        await b.idle(5, out_ready_i=1)
    assert len(b.frames) == old and limits == (
        b.v("header_limit_o"),
        b.v("data_limit_o"),
    )
    assert b.v("protocol_error_o") and b.v("recovery_request_o")
    await b.tick(link_up_i=0)
    assert (
        not b.v("protocol_error_o")
        and not b.v("queued_o")
        and b.v("header_limit_o") == 0x020202
    )


@cocotb.test()
async def held_frame_training_reset_and_framing_error_are_preserved(d):
    b = Bench(d)
    await b.reset()
    frame = frame_bytes(tlp_bytes(request(0x04)), 0)
    await b.send(frame, error=1)
    await b.idle(5, out_ready_i=1)
    await b.idle(10, out_ready_i=0, training_i=1)
    await b.idle(50, out_ready_i=1)
    assert b.frames == [(0, 1, frame)]
    await b.tick(packet_rejected_i=1)
    await b.tick(packet_rejected_i=0)
    assert not b.releases
    await b.tick(rst_ni=0)
    assert not b.v("out_valid_o") and not b.v("rx_ready_o")


@cocotb.test()
async def data_and_header_counter_wrap_matches_accepted_maximum_packets(d):
    b = Bench(d)
    await b.reset()
    # Exactly 32 TLP bytes = 3 header DW + 5 payload DW -> two data credits.
    frame = frame_bytes(tlp_bytes(request(0x40, payload=[1, 2, 3, 4, 5], length=5)), 0)
    assert len(frame) == 38
    for _ in range(2050):
        await b.send(frame)
        await b.consume()
    assert b.v("header_limit_o") & 255 == 4
    assert b.v("data_limit_o") & 4095 == 8
    assert b.releases == [(0, 2)] * 2050 and not b.v("protocol_error_o")
