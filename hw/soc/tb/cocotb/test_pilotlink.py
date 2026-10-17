# SPDX-FileCopyrightText: 2026 Hasan Melih Akbulut
# SPDX-License-Identifier: Apache-2.0
"""Public driver exercised on the unchanged submitted pilot and actual TT pins."""
import random

import cocotb
from cocotb.clock import Clock
from cocotb.triggers import RisingEdge, Timer
from golden.lif_core import LIFConfig, LIFCore
from golden.regmap_gen import ADDR, RESET
from pilotlink import PilotLink, encode_frame
from pilotlink.cocotb_transport import CocotbTransport


@cocotb.test()
async def public_driver_matches_golden_at_pins(dut):
    cocotb.start_soon(Clock(dut.clk, 10, unit='ns').start())
    dut.ena.value = 1
    dut.ui_in.value = 2  # deselected; no parallel AER request
    dut.uio_in.value = 0
    dut.rst_n.value = 0
    for _ in range(6): await RisingEdge(dut.clk)
    dut.rst_n.value = 1
    for _ in range(6): await RisingEdge(dut.clk)
    p = PilotLink(CocotbTransport(dut), neurons=8, axons=8)
    assert await p.read(ADDR['ID']) == RESET['ID']
    assert await p.geometry() == (8, 8)
    for value in (0, 0xffffffff, 0xa5a51234, 0x89abcdef):
        await p.write(ADDR['SCRATCH'], value)
        assert await p.read(ADDR['SCRATCH']) == value
    await p.state_clear()
    cfg = LIFConfig(thresh=4, v_reset=-2, leak_shift=3, syn_shift=0, refr_period=1)
    await p.configure(threshold=4, v_reset=-2, leak_shift=3, refractory=1)
    rng = random.Random(29)
    weights = [[7] * 8] + [[rng.randrange(-8, 8) for _ in range(8)] for _ in range(7)]
    await p.load_weights(weights, 8)
    await p.enable()
    frames = [[0], [0, 1], [], [2], [7, 0], [1, 1]]
    core = LIFCore(8, 8, weights, cfg)
    expected = core.run_frames(frames)
    actual = await p.run_frames(frames)
    assert actual == expected
    assert actual[0] == list(range(8))  # exceeds the five-event buffered path
    for n in range(8):
        await p.write(ADDR['N_ADDR'], n)
        value = await p.read(ADDR['N_DATA'])
        v, refractory = core.get_state(n)
        assert value == (v & 65535) | (refractory << 16)
    assert await p.read(ADDR['CNT_SEC']) == 0
    assert await p.read(ADDR['CNT_DED']) == 0


@cocotb.test()
async def cancelled_partial_write_releases_select_without_committing(dut):
    cocotb.start_soon(Clock(dut.clk, 10, unit='ns').start())
    dut.ena.value = 1
    dut.ui_in.value = 2
    dut.uio_in.value = 0
    dut.rst_n.value = 0
    for _ in range(6): await RisingEdge(dut.clk)
    dut.rst_n.value = 1
    for _ in range(6): await RisingEdge(dut.clk)
    transport = CocotbTransport(dut)
    task = cocotb.start_soon(transport.send_frame(encode_frame(True, ADDR['SCRATCH'], 0xffffffff)))
    await Timer(300, unit='ns')  # abort before eight command bits, much less forty
    task.cancel()
    await Timer(1, unit='ns')
    assert int(dut.ui_in.value) & 3 == 2
    assert not transport.active and transport.pending is None
    await Timer(160, unit='ns')  # explicitly restore the deselect-gap contract
    p = PilotLink(transport, neurons=8, axons=8)
    assert await p.read(ADDR['SCRATCH']) == RESET['SCRATCH']
