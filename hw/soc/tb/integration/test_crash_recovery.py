# SPDX-FileCopyrightText: 2026 Hasan Melih Akbulut
# SPDX-License-Identifier: Apache-2.0
"""Observe the real CRASH_DUMP_DEMO CPU program, reset and APB transactions."""
import cocotb
from cocotb.triggers import FallingEdge, ReadOnly, RisingEdge


@cocotb.test(timeout_time=15, timeout_unit="ms")
async def double_fault_pc_survives_watchdog_and_apb_write(tb):
    core = tb.dut
    # The firmware provokes the double fault by trapping again inside its
    # exception handler. No crash input, stored PC or bus response is forced.
    # This is combinational CSR logic: delta-cycle transitions are not
    # synchronous faults. Observe a settled half-cycle before capture.
    while True:
        await RisingEdge(core.double_fault_seen_o)
        await FallingEdge(tb.clk)
        await ReadOnly()
        if int(core.double_fault_seen_o.value):
            fault_pc = int(core.crash_dump.value) >> 128
            break
    assert fault_pc == 0xFF9FE000, f"unexpected injected fault PC {fault_pc:#x}"
    await FallingEdge(core.rst_sys_n)
    await RisingEdge(core.rst_sys_n)

    reads = 0
    attempted_write = False
    while True:
        await RisingEdge(core.sel_bootreg)
        while int(core.sel_bootreg.value):
            await FallingEdge(tb.clk)
            if not (int(core.sel_bootreg.value) and int(core.penable.value)
                    and int(core.pready.value)):
                continue
            if int(core.paddr.value) & 0xFFF != 0x010:
                continue
            assert int(core.pslverr.value) == 0
            if int(core.pwrite.value):
                assert int(core.pwdata.value) == 0xDEADBEEF
                attempted_write = True
            else:
                assert int(core.prdata.value) == fault_pc
                reads += 1
                if reads >= 2 and attempted_write:
                    # Sample the accepting edge, not only the setup of a read.
                    await RisingEdge(tb.clk)
                    tb._log.info("Double fault PC %#x retained across watchdog reset and read-only APB write", fault_pc)
                    return
