# SPDX-FileCopyrightText: 2026 Hasan Melih Akbulut
# SPDX-License-Identifier: Apache-2.0
"""Port-only serializer framing/capacity controls and independent wire CRC."""

import random
import cocotb
from cocotb.triggers import Timer
from test_soc_pcie_tlp_integrity import frame_bytes, tlp_bytes
from test_soc_pcie_tlp_stream import request, BAR


class Bench:
    def __init__(self, d):
        self.d = d
        self.frames = []
        self.current = []
        self.held = None
        self.bad = 0

    def v(self, n):
        return int(getattr(self.d, n).value)

    async def tick(self, **signals):
        self.d.clk_i.value = 0
        for n, v in signals.items():
            getattr(self.d, n).value = v
        await Timer(5, unit="ns")
        accepted = self.v("tlp_valid_i") and self.v("tlp_ready_o")
        if self.v("rst_ni"):
            beat = tuple(self.v(n) for n in ("tx_data_o", "tx_sop_o", "tx_eop_o"))
            if self.held is not None:
                assert self.v("tx_valid_o") and beat == self.held
            self.held = (
                beat if self.v("tx_valid_o") and not self.v("tx_ready_i") else None
            )
            if self.v("tx_valid_o") and self.v("tx_ready_i"):
                byte, sop, eop = beat
                assert bool(sop) == (not self.current)
                self.current.append(byte)
                if eop:
                    self.frames.append(bytes(self.current))
                    self.current = []
        else:
            self.held = None
            self.current = []
        self.d.clk_i.value = 1
        await Timer(5, unit="ns")
        self.bad += self.v("packet_bad_o")
        return accepted

    async def reset(self):
        await self.tick(
            rst_ni=0,
            tlp_valid_i=0,
            tlp_sop_i=0,
            tlp_eop_i=0,
            tlp_error_i=0,
            tlp_data_i=0,
            tx_ready_i=1,
        )
        await self.tick(rst_ni=1)
        self.frames = []
        self.bad = 0
        assert self.v("next_sequence_o") == 0

    async def word(self, w, sop=False, eop=False, error=False):
        for _ in range(200):
            if await self.tick(
                tlp_valid_i=1,
                tlp_data_i=w,
                tlp_sop_i=sop,
                tlp_eop_i=eop,
                tlp_error_i=error,
            ):
                return
        raise AssertionError("TX TLP input stuck")

    async def send(self, words, error_at=None):
        for i, w in enumerate(words):
            await self.word(w, i == 0, i == len(words) - 1, i == error_at)
        await self.tick(tlp_valid_i=0, tlp_sop_i=0, tlp_eop_i=0, tlp_error_i=0)

    async def idle(self, n=70, **signals):
        for _ in range(n):
            await self.tick(tlp_valid_i=0, **signals)


@cocotb.test()
async def three_four_dw_headers_max_capacity_and_random_output_stalls(dut):
    b = Bench(dut)
    await b.reset()
    rng = random.Random(45)
    vectors = [
        request(0, BAR),
        request(0x40, BAR, [0x78563412]),
        request(0x60, 0x1234567882345000, [0xDEADBEEF]),
        request(0x40, BAR, [1, 2, 3, 4, 5], length=5),
    ]
    for seq, words in enumerate(vectors):
        await b.send(words)
        for _ in range(120):
            await b.tick(tlp_valid_i=0, tx_ready_i=rng.randrange(2))
        await b.idle(tx_ready_i=1)
        assert b.frames[-1] == frame_bytes(tlp_bytes(words), seq)
    assert len(b.frames) == 4 and b.v("next_sequence_o") == 4 and not b.bad


@cocotb.test()
async def malformed_input_overflow_error_reset_and_new_sop_are_quarantined(dut):
    b = Bench(dut)
    await b.reset()
    good = request(0x40, BAR, [0x11223344])
    for words in (
        [0x40000001],
        [0x40000001, 2],
        [0x60000001, 2, 3],
        request(0x40, BAR, [1] * 6, length=6),
    ):
        before = b.bad
        await b.send(words)
        await b.idle()
        assert not b.frames and b.bad > before and b.v("next_sequence_o") == 0
    for i in range(len(good)):
        await b.send(good, error_at=i)
        await b.idle()
        assert not b.frames and b.v("next_sequence_o") == 0
    await b.word(0x40000001, sop=True)
    await b.word(0)
    await b.send(good)
    await b.idle()
    assert b.frames == [frame_bytes(tlp_bytes(good), 0)]
    await b.reset()
    await b.word(0)
    await b.word(1, eop=True)
    await b.idle()
    assert not b.frames and b.bad
    await b.send(good)
    while len(b.current) < 2:
        await b.tick(tlp_valid_i=0)
    await b.tick(tx_ready_i=0)
    await b.idle(5)
    assert b.v("next_sequence_o") == 0
    await b.reset()
    await b.idle()
    assert not b.frames and not b.v("tx_valid_o")
    await b.send(good)
    await b.idle()
    assert b.frames == [frame_bytes(tlp_bytes(good), 0)]
