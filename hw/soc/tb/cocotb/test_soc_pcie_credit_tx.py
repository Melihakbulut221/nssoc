# SPDX-FileCopyrightText: 2026 Hasan Melih Akbulut
# SPDX-License-Identifier: Apache-2.0
"""Port-only credit oracle uses unbounded issued/consumed counters."""
import random

import cocotb
from cocotb.triggers import Timer


class Driver:
    def __init__(self, dut):
        self.dut = dut
        self.clear()

    def clear(self):
        self.seen = set()
        self.confirmed = False
        self.limit = [[0, 0] for _ in range(3)]
        self.used = [[0, 0] for _ in range(3)]
        self.inf = [[False, False] for _ in range(3)]

    async def tick(self, fc=None, request=None, reset=False, link=True, local=True, tlp=False):
        d = self.dut
        d.clk_i.value = 0
        d.rst_ni.value = not reset
        d.link_up_i.value = link
        d.local_init_done_i.value = local
        d.rx_tlp_seen_i.value = tlp
        d.fc_valid_i.value = fc is not None
        d.fc_phase_i.value, d.fc_class_i.value, d.fc_header_i.value, d.fc_data_i.value = fc or (0, 0, 0, 0)
        d.reserve_valid_i.value = request is not None
        cls, dw, replay = request or (0, 0, False)
        d.reserve_class_i.value = cls
        d.reserve_payload_dw_i.value = dw
        d.reserve_replay_i.value = replay
        await Timer(5, unit='ns')
        initialized = not reset and link and len(self.seen) == 3 and self.confirmed and local
        legal = cls < 3 and dw <= 1024
        fee = [1, (dw + 3) // 4]
        ready = initialized and legal and (replay or all(
            self.inf[cls][k] or self.limit[cls][k] - self.used[cls][k] >= fee[k]
            for k in range(2)))
        assert int(d.initialized_o.value) == initialized
        assert int(d.reserve_ready_o.value) == ready
        error = False
        if reset or not link:
            self.clear()
        else:
            all_seen_before = len(self.seen) == 3
            if request is not None and ready and not replay:
                for k in range(2):
                    if not self.inf[cls][k]:
                        self.used[cls][k] += fee[k]
            if all_seen_before and tlp:
                self.confirmed = True
            if fc is not None:
                phase, c, h, data = fc
                if c == 3 or phase == 3:
                    error = True
                elif not all_seen_before:
                    if phase == 2 or h > 127 or data > 2047:
                        error = True
                    else:
                        self.limit[c] = [h, data]
                        self.inf[c] = [h == 0, data == 0]
                        self.seen.add(c)
                elif phase == 1:
                    self.confirmed = True
                elif phase == 2:
                    next_limits = []
                    for k, (advertised, mod) in enumerate(((h, 256), (data, 4096))):
                        if self.inf[c][k]:
                            error |= advertised != 0
                            next_limits.append(0)
                        else:
                            advance = (advertised - self.limit[c][k]) % mod
                            new = self.limit[c][k] + advance
                            error |= advance >= mod // 2 or not 0 <= new - self.used[c][k] < mod // 2
                            next_limits.append(new)
                    if not error:
                        self.limit[c] = next_limits
                        self.confirmed = True
        d.clk_i.value = 1
        await Timer(5, unit='ns')
        assert int(d.protocol_error_o.value) == error
        for name, values, width in (
            ('header_limit_o', self.limit, 8), ('header_consumed_o', self.used, 8),
            ('data_limit_o', self.limit, 12), ('data_consumed_o', self.used, 12)):
            k = int(width == 12)
            expected = sum((values[c][k] % (1 << width)) << (c * width) for c in range(3))
            assert int(getattr(d, name).value) == expected, name
        assert int(d.infinite_o.value) == sum(int(self.inf[c][k]) << (2*c+k) for c in range(3) for k in range(2))
        return ready

    async def init(self, capacities=((4, 8), (3, 4), (8, 16)), first_phase=0):
        await self.tick(reset=True)
        await self.tick()
        for cls, (h, data) in enumerate(capacities):
            await self.tick(fc=(first_phase, cls, h, data), request=(cls, 0, False), local=False)
        await self.tick(fc=(1, 0, 255, 4095), local=False)
        await self.tick(local=True)


@cocotb.test()
async def initialization_and_finite_atomic_reservations(dut):
    driver = Driver(dut)
    await driver.init()
    # ceil(payload DWORDs/4), one header per new packet, independent pools.
    for cls in range(3):
        for dw in (0, 1, 4, 5, 8, 17, 1024, 1025):
            await driver.tick(request=(cls, dw, False))
    for _ in range(20):
        await driver.tick(request=(0, 1, False))
    # Repeated init is ignored; zero UpdateFC at counter rollover is NOT infinity.
    await driver.tick(fc=(0, 0, 0, 0))
    await driver.tick(fc=(2, 0, 6, 10), request=(0, 1, False))
    await driver.tick(request=(0, 5, False))
    await driver.tick(request=(3, 0, False))


@cocotb.test()
async def infinite_pools_replay_and_link_reset(dut):
    driver = Driver(dut)
    await driver.init(((0, 0), (4, 0), (0, 1)), first_phase=1)
    for _ in range(300):
        await driver.tick(request=(0, 1024, False))
    for _ in range(8):
        await driver.tick(request=(1, 1, False))
    await driver.tick(request=(2, 4, False))
    for _ in range(16):
        await driver.tick(request=(2, 1024, True))
    await driver.tick(fc=(2, 0, 0, 0))
    await driver.tick(fc=(2, 0, 1, 0))
    await driver.tick(fc=(2, 1, 5, 1))
    await driver.tick(link=False, request=(0, 0, True))
    await driver.tick(request=(0, 0, True))
    # An UpdateFC before collecting all capacities cannot initialize infinity.
    await driver.tick(fc=(2, 0, 0, 0))
    for c in range(3):
        await driver.tick(fc=(0, c, 2, 2))
    await driver.tick(tlp=True)
    await driver.tick(request=(0, 1, False))


@cocotb.test()
async def modulo_counters_random_credit_return_and_stalls(dut):
    driver = Driver(dut)
    await driver.init(((8, 32), (8, 32), (8, 32)))
    rng = random.Random(0xc4ed17)
    for index in range(12000):
        cls = index % 3
        request = (cls, rng.choice((0, 1, 4, 5, 8, 16, 31)), index % 19 == 0)
        fc = None
        if index % 4 != 0:
            # Return only actually consumed buffers, plus a bounded new window.
            limits = [max(driver.limit[cls][k], driver.used[cls][k] + (8 if k == 0 else 32)) for k in range(2)]
            fc = (2, cls, limits[0] % 256, limits[1] % 4096)
        await driver.tick(fc=fc, request=request)
    assert all(row[0] > 256 and row[1] > 4096 for row in driver.used)


@cocotb.test()
async def corrupt_credit_events_never_grant_or_reset_limits(dut):
    driver = Driver(dut)
    await driver.tick(reset=True)
    for fc in ((0, 3, 1, 1), (3, 0, 1, 1), (0, 0, 128, 1), (1, 0, 1, 2048)):
        await driver.tick(fc=fc)
    await driver.init(((1, 1), (1, 1), (1, 1)))
    for c in range(3):
        await driver.tick(request=(c, 4, False))
    for fc in ((2, 0, 0, 1), (2, 0, 129, 1), (2, 0, 1, 2049), (2, 0, 1, 0), (2, 0, 2, 2049)):
        await driver.tick(fc=fc, request=(0, 1, False))
    await driver.tick(fc=(2, 0, 2, 2))
    await driver.tick(request=(0, 1, False))
    await driver.tick(reset=True, fc=(2, 0, 3, 3), request=(0, 1, False))
    await driver.tick(request=(0, 1, False))


@cocotb.test()
async def same_cycle_update_debit_exhausts_exactly_once(dut):
    """A simultaneous UpdateFC must not restore the packet's consumed credit."""
    driver = Driver(dut)
    for cls in range(3):
        await driver.init(((4, 1), (4, 1), (4, 1)))
        # Returning one data credit while consuming one leaves precisely one.
        assert await driver.tick(fc=(2, cls, 5, 2), request=(cls, 4, False))
        assert await driver.tick(request=(cls, 4, False))
        assert not await driver.tick(request=(cls, 4, False))
        # Updates to another class must not overwrite this class's debit.
        other = (cls + 1) % 3
        assert await driver.tick(fc=(2, cls, 6, 3), request=(other, 4, False))
        assert not await driver.tick(request=(other, 4, False))
        assert await driver.tick(request=(cls, 4, False))
        assert not await driver.tick(request=(cls, 4, False))
    # The half-range check uses the post-debit balance: 128-1 and 2048-1
    # are legal, even though their pre-debit sign bits are both set.
    for cls in range(3):
        await driver.init(((4, 1), (4, 1), (4, 1)))
        assert await driver.tick(fc=(2, cls, 128, 2048), request=(cls, 4, False))
        # Without another debit, advancing those balances to the half-range
        # boundary is invalid and must leave both advertised limits intact.
        await driver.tick(fc=(2, cls, 129, 2049))
