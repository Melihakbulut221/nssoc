# SPDX-FileCopyrightText: 2026 Hasan Melih Akbulut
# SPDX-License-Identifier: Apache-2.0
"""TLP descriptors reach the unmodified SoC GPIO RTL, not a bus stub."""
import cocotb
from test_soc_pcie_tlp_regs import Bench, packet, completion, BAR


class GpioBench(Bench):
    async def tick(self, **signals):
        for field in ['pready_i', 'pslverr_i', 'prdata_i']:
            signals.pop(field, None)  # These are outputs of the real GPIO.
        if signals.get('rst_ni') == 0:
            signals['gpio_i'] = 0
        return await super().tick(**signals)


@cocotb.test()
async def host_register_reads_writes_drive_real_gpio(dut):
    b = GpioBench(dut); await b.reset(); await b.enable()
    assert await b.transact(packet(0x40, BAR+8, 0xffff)) == []
    assert b.v('gpio_oe_o') == 0xffff
    for value in [0, 0xffff, 0xa55a, 0x8001]:
        assert await b.transact(packet(0x40, BAR+4, value)) == []
        assert b.v('gpio_o') == value
        assert await b.transact(packet(0, BAR+4)) == [completion(data=value, lower=4)]
    assert await b.transact(packet(0x40, BAR+0x74, 1)) == []
    assert b.v('gpio_o') == 0x8000
    assert await b.transact(packet(0, BAR+4)) == [completion(data=0x8000, lower=4)]
    for _ in range(4): await b.tick(gpio_i=0x1234)
    assert await b.transact(packet(0, BAR)) == [completion(data=0x1234)]
    assert b.errors == 0


@cocotb.test()
async def apb3_partial_writes_and_unmapped_requests_cannot_mutate_gpio(dut):
    b = GpioBench(dut); await b.reset(); await b.enable()
    await b.transact(packet(0x40, BAR+8, 0xffff))
    await b.transact(packet(0x40, BAR+4, 0x5aa5))
    for be in range(15):
        assert await b.transact(packet(0x40, BAR+4, 0xffff, be=be)) == []
        assert b.v('gpio_o') == 0x5aa5
    assert b.errors == 14  # BE=0 is a legal no-op, not an APB3 write.
    await b.cfg(0x10, BAR+0x1000)
    assert await b.transact(packet(0x40, BAR+4, 0)) == []
    assert b.v('gpio_o') == 0x5aa5
    assert await b.transact(packet(0, BAR+4)) == [completion(status=1, count=0)]
    assert await b.transact(packet(0, BAR+0x1004)) == [completion(data=0x5aa5, lower=4)]
