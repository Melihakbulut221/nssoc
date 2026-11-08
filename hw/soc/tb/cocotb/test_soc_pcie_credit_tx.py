# SPDX-FileCopyrightText: 2026 Hasan Melih Akbulut
# SPDX-License-Identifier: Apache-2.0
"""Port-only credit oracle uses unbounded issued/consumed counters.

The module grants from a registered verdict and applies an UpdateFC one
cycle after it is presented. The oracle models both: a request is granted
only if it was presented unchanged in the previous cycle, was affordable
and initialized then, and nothing was consumed in that cycle; an UpdateFC presented in one
cycle is checked and applied in the next, after that cycle's debit.
"""
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
        self.pending = None
        self.verdict = False
        self.last_request = None
        self.consumed = False

    async def tick(self, fc=None, request=None, reset=False, link=True, local=True, tlp=False, idle_request=None):
        d = self.dut
        d.clk_i.value = 0
        d.rst_ni.value = not reset
        d.link_up_i.value = link
        d.local_init_done_i.value = local
        d.rx_tlp_seen_i.value = tlp
        d.fc_valid_i.value = fc is not None
        d.fc_phase_i.value, d.fc_class_i.value, d.fc_header_i.value, d.fc_data_i.value = fc or (0, 0, 0, 0)
        d.reserve_valid_i.value = request is not None
        cls, dw, replay = request or idle_request or (0, 0, False)
        d.reserve_class_i.value = cls
        d.reserve_payload_dw_i.value = dw
        d.reserve_replay_i.value = replay
        await Timer(5, unit='ns')
        initialized = not reset and link and len(self.seen) == 3 and self.confirmed and local
        legal = cls < 3 and dw <= 1024
        fee = [1, (dw + 3) // 4]
        key = (cls, dw, replay)
        # Registered verdict: the same request in the previous cycle, affordable
        # then, and no consume in that cycle.
        ready = (not reset and link and self.verdict and key == self.last_request
                 and not self.consumed)
        # This cycle's verdict, against this cycle's credit and initialization,
        # grants next cycle.
        verdict = initialized and legal and (replay or all(
            self.inf[cls][k] or self.limit[cls][k] - self.used[cls][k] >= fee[k]
            for k in range(2)))
        assert int(d.initialized_o.value) == initialized
        assert int(d.reserve_ready_o.value) == ready
        error = False
        if reset or not link:
            self.clear()
        else:
            all_seen_before = len(self.seen) == 3
            consumed = request is not None and ready and not replay
            if consumed:
                for k in range(2):
                    if not self.inf[cls][k]:
                        self.used[cls][k] += fee[k]
            if all_seen_before and tlp:
                self.confirmed = True
            # The UpdateFC presented last cycle is checked and applied now,
            # after this cycle's debit; this cycle's one waits a cycle.
            pending, self.pending = self.pending, fc
            self.verdict, self.last_request, self.consumed = verdict, key, consumed
            if pending is not None:
                phase, c, h, data = pending
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

    async def grant(self, request):
        """Present a request with valid low for a cycle, then with valid high.

        The registered verdict grants a request one cycle after it first
        appears; the first cycle is the one in which its affordability is
        judged."""
        await self.tick(idle_request=request)
        return await self.tick(request=request)


@cocotb.test()
async def initialization_and_finite_atomic_reservations(dut):
    driver = Driver(dut)
    await driver.init()
    # ceil(payload DWORDs/4), one header per new packet, independent pools.
    for cls in range(3):
        for dw in (0, 1, 4, 5, 8, 17, 1024, 1025):
            await driver.grant((cls, dw, False))
    for _ in range(20):
        await driver.tick(request=(0, 1, False))
    # Repeated init is ignored; zero UpdateFC at counter rollover is NOT infinity.
    await driver.tick(fc=(0, 0, 0, 0))
    await driver.tick(fc=(2, 0, 6, 10), request=(0, 1, False))
    await driver.tick(request=(0, 1, False))
    await driver.grant((0, 5, False))
    await driver.grant((3, 0, False))


@cocotb.test()
async def infinite_pools_replay_and_link_reset(dut):
    driver = Driver(dut)
    await driver.init(((0, 0), (4, 0), (0, 1)), first_phase=1)
    for _ in range(300):
        await driver.tick(request=(0, 1024, False))
    for _ in range(8):
        await driver.tick(request=(1, 1, False))
    await driver.grant((2, 4, False))
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
    await driver.tick()
    await driver.tick(tlp=True)
    await driver.grant((0, 1, False))


@cocotb.test()
async def modulo_counters_random_credit_return_and_stalls(dut):
    driver = Driver(dut)
    await driver.init(((8, 32), (8, 32), (8, 32)))
    rng = random.Random(0xc4ed17)
    # Each request is held for two cycles: one to judge it, one to grant it.
    for index in range(24000):
        cls = (index // 2) % 3
        if index % 2 == 0:
            request = (cls, rng.choice((0, 1, 4, 5, 8, 16, 31)), (index // 2) % 19 == 0)
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
        await driver.grant((c, 4, False))
    for fc in ((2, 0, 0, 1), (2, 0, 129, 1), (2, 0, 1, 2049), (2, 0, 1, 0), (2, 0, 2, 2049)):
        await driver.tick(fc=fc, request=(0, 1, False))
    await driver.tick(fc=(2, 0, 2, 2))
    await driver.tick()
    await driver.grant((0, 1, False))
    await driver.tick(reset=True, fc=(2, 0, 3, 3), request=(0, 1, False))
    await driver.tick(request=(0, 1, False))


@cocotb.test()
async def same_cycle_update_debit_exhausts_exactly_once(dut):
    """A simultaneous UpdateFC must not restore the packet's consumed credit."""
    driver = Driver(dut)
    for cls in range(3):
        await driver.init(((4, 1), (4, 1), (4, 1)))
        # Returning one data credit while consuming one leaves precisely one.
        # The update is presented a cycle before the debit, so that it is
        # applied in the debit's cycle.
        await driver.tick(fc=(2, cls, 5, 2), idle_request=(cls, 4, False))
        assert await driver.tick(request=(cls, 4, False))
        assert not await driver.tick(request=(cls, 4, False))  # cycle after a consume
        assert await driver.tick(request=(cls, 4, False))
        assert not await driver.tick(request=(cls, 4, False))
        assert not await driver.tick(request=(cls, 4, False))  # exhausted
        # Updates to another class must not overwrite this class's debit.
        other = (cls + 1) % 3
        await driver.tick(fc=(2, cls, 6, 3), idle_request=(other, 4, False))
        assert await driver.tick(request=(other, 4, False))
        assert not await driver.tick(request=(other, 4, False))
        assert not await driver.tick(request=(other, 4, False))  # exhausted
        assert await driver.grant((cls, 4, False))
        assert not await driver.tick(request=(cls, 4, False))
        assert not await driver.tick(request=(cls, 4, False))  # exhausted
    # The half-range check uses the post-debit balance: 128-1 and 2048-1
    # are legal, even though their pre-debit sign bits are both set.
    for cls in range(3):
        await driver.init(((4, 1), (4, 1), (4, 1)))
        await driver.tick(fc=(2, cls, 128, 2048), idle_request=(cls, 4, False))
        assert await driver.tick(request=(cls, 4, False))
        # Without another debit, advancing those balances to the half-range
        # boundary is invalid and must leave both advertised limits intact.
        await driver.tick(fc=(2, cls, 129, 2049))
        await driver.tick()
    # Isolate data exhaustion from header exhaustion. A multi-credit payload
    # must debit ceil(DWORDs/4), while a zero-length payload debits no data.
    for cls in range(3):
        await driver.init(((0, 3), (0, 3), (0, 3)))
        assert await driver.grant((cls, 0, False))
        assert await driver.grant((cls, 8, False))
        assert not await driver.grant((cls, 8, False))
        assert await driver.grant((cls, 4, False))
        assert not await driver.grant((cls, 1, False))
        assert await driver.grant((cls, 0, False))
        # Restoring two credits permits one five-DWORD packet, exactly once.
        # The update is applied a cycle after it is presented, and judged
        # affordable in the cycle after that.
        await driver.tick(fc=(2, cls, 0, 5))
        await driver.tick()
        assert await driver.grant((cls, 5, False))
        assert not await driver.grant((cls, 1, False))

    # An idle bus may carry a legal request while valid is low. Neither its
    # header nor payload may rescue an otherwise invalid half-range UpdateFC.
    for cls in range(3):
        await driver.init(((4, 1), (4, 1), (4, 1)))
        await driver.tick(fc=(2, cls, 128, 2048), idle_request=(cls, 4, False))
        await driver.tick(idle_request=(cls, 4, False))
        assert driver.used[cls] == [0, 0]
        assert driver.limit[cls] == [4, 1]
        # The identical advertised boundary is legal with a real debit.
        await driver.tick(fc=(2, cls, 128, 2048), idle_request=(cls, 4, False))
        assert await driver.tick(request=(cls, 4, False))
        assert driver.used[cls] == [1, 1]
        assert driver.limit[cls] == [128, 2048]
