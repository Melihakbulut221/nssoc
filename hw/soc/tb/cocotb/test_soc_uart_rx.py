# SPDX-FileCopyrightText: 2026 Hasan Melih Akbulut
# SPDX-License-Identifier: Apache-2.0
"""RX contract driven through serial/APB pins, including malformed traffic."""
import cocotb
from cocotb.triggers import Timer, RisingEdge

from test_soc_uart import (
    setup, apb_write, apb_read, idle, val, CLK_NS, DATA, STATUS, CTRL, SCALER,
    CT_RE, CT_RI, CT_TE, ST_DR, bit_clocks,
)

OV, FE = 1 << 4, 1 << 6


async def frame(dut, byte, scaler=0, stop=1, phase_ns=0, period_ns=None):
    if phase_ns:
        await Timer(phase_ns, unit="ns")
    period = period_ns or bit_clocks(scaler) * CLK_NS
    for bit in [0] + [(byte >> n) & 1 for n in range(8)] + [stop]:
        dut.rx_i.value = bit
        await Timer(period, unit="ns")


async def enable(dut, scaler=0, interrupt=True):
    await apb_write(dut, SCALER, scaler)
    await apb_write(dut, CTRL, CT_RE | (CT_RI if interrupt else 0))
    await idle(dut, 4)


@cocotb.test()
async def bytes_phases_and_dividers(dut):
    await setup(dut)
    for scaler in [0, 1, 7]:
        await enable(dut, scaler)
        for phase in [0, 1, 5, 9]:
            for byte in [0x00, 0xff, 0xa5, 0x5a, 0x81]:
                await frame(dut, byte, scaler, phase_ns=phase)
                assert await apb_read(dut, STATUS) & (ST_DR | OV | FE) == ST_DR
                assert val(dut.irq_o) == 1
                assert await apb_read(dut, DATA) == byte
                assert not val(dut.irq_o)
                assert await apb_read(dut, DATA) == 0
    # A 12-bit maximum scaler needs a 32768-clock receive bit period.
    await enable(dut, 4095)
    await frame(dut, 0x96, 4095)
    assert await apb_read(dut, DATA) == 0x96


@cocotb.test()
async def back_to_back_overrun_and_selective_error_clear(dut):
    await setup(dut)
    await enable(dut)
    await frame(dut, 0x35)
    await frame(dut, 0xca)
    status = await apb_read(dut, STATUS)
    assert status & (ST_DR | OV | FE) == (ST_DR | OV)
    assert await apb_read(dut, DATA) == 0x35  # Preserve unread data.
    assert val(dut.irq_o) == 1  # Sticky receive error is still pending.
    await apb_write(dut, STATUS, 0xffffffff)
    assert await apb_read(dut, STATUS) & OV
    await apb_write(dut, STATUS, 0xffffffff ^ OV)
    assert not val(dut.irq_o)
    await frame(dut, 0x6c, stop=0)
    assert await apb_read(dut, STATUS) & (ST_DR | OV | FE) == FE
    assert await apb_read(dut, DATA) == 0  # Invalid frame was discarded.
    await apb_write(dut, STATUS, 0xffffffff ^ OV)
    assert await apb_read(dut, STATUS) & FE
    await apb_write(dut, STATUS, 0)
    assert not val(dut.irq_o)
    # Held-low break does not manufacture repeated bytes/errors after clear.
    await idle(dut, 100)
    assert await apb_read(dut, STATUS) & (ST_DR | OV | FE) == 0
    dut.rx_i.value = 1
    await idle(dut, 16)
    await frame(dut, 0x72)
    assert await apb_read(dut, DATA) == 0x72


@cocotb.test()
async def read_only_consumes_on_access_and_interrupt_is_gated(dut):
    await setup(dut)
    await enable(dut, interrupt=False)
    await frame(dut, 0x47)
    assert not val(dut.irq_o)
    await apb_write(dut, CTRL, CT_RE | CT_RI)
    assert val(dut.irq_o)
    await RisingEdge(dut.clk_i)
    dut.psel_i.value, dut.penable_i.value = 1, 0
    dut.pwrite_i.value, dut.paddr_i.value = 0, DATA
    await idle(dut, 3)
    assert val(dut.prdata_o) == 0x47
    dut.psel_i.value = 0
    assert await apb_read(dut, STATUS) & ST_DR
    assert await apb_read(dut, DATA) == 0x47
    assert not val(dut.irq_o)


@cocotb.test()
async def false_start_disable_abort_and_reset(dut):
    await setup(dut)
    await enable(dut, 1)
    dut.rx_i.value = 0
    await Timer(3 * CLK_NS, unit="ns")
    dut.rx_i.value = 1
    await idle(dut, 200)
    assert await apb_read(dut, STATUS) & (ST_DR | OV | FE) == 0
    sender = cocotb.start_soon(frame(dut, 0x89, 1))
    await idle(dut, 48)
    await apb_write(dut, CTRL, 0)
    await sender
    assert await apb_read(dut, STATUS) & (ST_DR | OV | FE) == 0
    await enable(dut)
    await frame(dut, 0x91)
    await apb_write(dut, CTRL, 0)
    assert await apb_read(dut, DATA) == 0x91  # Disable preserves queued byte.
    await enable(dut)
    sender = cocotb.start_soon(frame(dut, 0x12))
    await idle(dut, 24)
    dut.rst_ni.value = 0
    await idle(dut, 3)
    dut.rst_ni.value = 1
    await sender
    assert await apb_read(dut, CTRL) == 0
    assert await apb_read(dut, STATUS) & (ST_DR | OV | FE) == 0
    await enable(dut)
    await frame(dut, 0xe3)
    assert await apb_read(dut, DATA) == 0xe3


@cocotb.test()
async def scaler_write_during_frame_applies_to_next_frame(dut):
    await setup(dut)
    await enable(dut, 3)
    sender = cocotb.start_soon(frame(dut, 0x39, 3))
    await idle(dut, 70)
    await apb_write(dut, SCALER, 0)
    await sender
    assert await apb_read(dut, DATA) == 0x39
    await frame(dut, 0xc6)
    assert await apb_read(dut, DATA) == 0xc6


@cocotb.test()
async def receive_during_transmit_and_baud_error(dut):
    await setup(dut)
    await enable(dut, 7)
    await apb_write(dut, CTRL, CT_RE | CT_RI | CT_TE)
    # Independent external RX at +/- 2 percent baud error while TX shifts.
    for scale in [0.98, 1.02]:
        await apb_write(dut, DATA, 0x55)
        await frame(dut, 0xb6, 7, period_ns=bit_clocks(7) * CLK_NS * scale)
        assert await apb_read(dut, DATA) == 0xb6
        assert await apb_read(dut, STATUS) & (OV | FE) == 0


@cocotb.test()
async def pop_swept_across_receive_completion(dut):
    await setup(dut)
    kept, overflowed = 0, 0
    # Sweep DATA's APB access across the stop midpoint without observing
    # internal receiver state. A read/completion collision must keep new data.
    for delay in range(69, 85):
        await enable(dut)
        await apb_write(dut, STATUS, 0)
        await frame(dut, 0x11)
        sender = cocotb.start_soon(frame(dut, 0x22, phase_ns=1))
        await idle(dut, delay)
        assert await apb_read(dut, DATA) == 0x11
        await sender
        status = await apb_read(dut, STATUS)
        data = await apb_read(dut, DATA)
        assert not status & FE
        if status & OV:
            assert not status & ST_DR and data == 0
            overflowed += 1
        else:
            assert status & ST_DR and data == 0x22
            kept += 1
    assert kept and overflowed, (kept, overflowed)
