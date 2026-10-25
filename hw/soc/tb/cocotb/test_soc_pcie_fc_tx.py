# SPDX-FileCopyrightText: 2026 Hasan Melih Akbulut
# SPDX-License-Identifier: Apache-2.0
"""Port-only actual six-byte FC frames, accepted-EOP counters and init phases."""

import random
import cocotb
from cocotb.triggers import Timer
from pcie_rx_flow_common import decode_fc


class Bench:
    def __init__(self, d):
        self.d = d
        self.frames = []
        self.current = []
        self.held = None
        self.commits = []

    def v(self, n):
        return int(getattr(self.d, n).value)

    async def tick(self, **kw):
        self.d.clk_i.value = 0
        for n, v in kw.items():
            getattr(self.d, n).value = v
        await Timer(5, unit="ns")
        if self.v("rst_ni") and self.v("link_up_i"):
            beat = tuple(self.v(n) for n in ("tx_data_o", "tx_sop_o", "tx_eop_o"))
            if self.held is not None:
                assert self.v("tx_valid_o") and beat == self.held
            self.held = (
                beat if self.v("tx_valid_o") and not self.v("tx_ready_i") else None
            )
            if self.v("tx_valid_o") and self.v("tx_ready_i"):
                assert bool(beat[1]) == (not self.current)
                self.current.append(beat[0])
                if beat[2]:
                    self.frames.append(decode_fc(bytes(self.current)))
                    self.current = []
        else:
            self.current = []
            self.held = None
        self.d.clk_i.value = 1
        await Timer(5, unit="ns")
        if self.v("sent_valid_o"):
            self.commits.append((self.v("sent_phase_o"), self.v("sent_class_o")))

    async def reset(self):
        await self.tick(
            rst_ni=0,
            link_up_i=0,
            training_i=0,
            peer_init1_done_i=0,
            peer_init2_seen_i=0,
            header_limit_i=0x000202,
            data_limit_i=0x000004004,
            tx_ready_i=1,
        )
        await self.tick(rst_ni=1, link_up_i=1)
        self.frames = []
        self.commits = []

    async def idle(self, n=80, **kw):
        for _ in range(n):
            await self.tick(**kw)


@cocotb.test()
async def exact_three_class_init_is_driven_by_accepted_frames(d):
    b = Bench(d)
    await b.reset()
    await b.idle(35, tx_ready_i=0, peer_init1_done_i=1, peer_init2_seen_i=1)
    assert not b.v("local_init_done_o") and not b.commits and not b.v("sent_header_o")
    await b.idle(80, tx_ready_i=1)
    assert b.frames[:6] == [
        (p, c, 0 if c == 2 else 2, 0 if c == 2 else 4) for p in (0, 1) for c in range(3)
    ]
    assert b.v("local_init_done_o") and b.v("sent_header_o") == 0x000202
    assert b.commits == [(f[0], f[1]) for f in b.frames]


@cocotb.test()
async def snapshots_stalls_modular_limits_and_periodic_updates(d):
    b = Bench(d)
    await b.reset()
    await b.idle(80, peer_init1_done_i=1, peer_init2_seen_i=1)
    rng = random.Random(0xFC16)
    for header, data in ((255, 4095), (0, 0), (1, 1), (127, 2047)):
        limits_h = header | (17 << 8) | (29 << 16)
        limits_d = data | (71 << 12) | (93 << 24)
        start = len(b.frames)
        for _ in range(200):
            await b.tick(
                header_limit_i=limits_h,
                data_limit_i=limits_d,
                tx_ready_i=rng.randrange(3) != 0,
            )
        updates = b.frames[start:]
        assert (2, 0, header, data) in updates
        assert b.v("sent_header_o") == limits_h and b.v("sent_data_o") == limits_d
    assert all(c < 3 for _, c, _, _ in b.frames)


@cocotb.test()
async def training_finishes_current_frame_then_pauses_and_link_reset_reinitializes(d):
    b = Bench(d)
    await b.reset()
    await b.idle(3)
    await b.idle(50, training_i=1)
    assert len(b.frames) == 1 and not b.v("tx_valid_o") and not b.v("local_init_done_o")
    await b.idle(80, training_i=0, peer_init1_done_i=1, peer_init2_seen_i=1)
    assert b.v("local_init_done_o")
    await b.tick(link_up_i=0)
    assert (
        not b.v("local_init_done_o")
        and not b.v("sent_header_o")
        and not b.v("tx_valid_o")
    )
    before = len(b.frames)
    await b.idle(25, link_up_i=1, peer_init1_done_i=0, peer_init2_seen_i=0)
    assert all(f[0] == 0 for f in b.frames[before:])
