# SPDX-FileCopyrightText: 2026 Hasan Melih Akbulut
# SPDX-License-Identifier: Apache-2.0
"""APB port assertions, including the CPU bridge's parked timeout request."""

import cocotb
from cocotb.triggers import Timer


class Bench:
    def __init__(self, d):
        self.d = d
        self.transfers = []
        self.responses = []
        self.setups = []
        self.active = None
        self.was_access = False

    def v(self, n):
        return int(getattr(self.d, n).value)

    @staticmethod
    def master(index, sel=1, enable=0, address=None, data=None, write=1, strobe=15):
        return {
            f"m{index}_{key}_i": value
            for key, value in {
                "psel": sel,
                "penable": enable,
                "paddr": address
                if address is not None
                else (index + 1) * 0x10000 + 0x24,
                "pwdata": data if data is not None else 0xCA000000 + index,
                "pwrite": write,
                "pstrb": strobe,
            }.items()
        }

    async def tick(self, **kw):
        self.d.clk_i.value = 0
        for n, v in kw.items():
            getattr(self.d, n).value = v
        await Timer(5, unit="ns")
        replies = (self.v("m0_pready_o"), self.v("m1_pready_o"))
        if self.v("rst_ni"):
            selected = self.v("psel_o")
            enabled = self.v("penable_o")
            beat = tuple(
                self.v(n) for n in ("paddr_o", "pwrite_o", "pwdata_o", "pstrb_o")
            )
            assert not (enabled and not selected)
            assert not all(replies)
            if selected:
                owner_from_payload = (beat[0] >> 16) - 1
                assert owner_from_payload in (0, 1)
                assert self.v(f"m{owner_from_payload}_psel_i"), (
                    "Withdrawn owner still selected downstream"
                )
                if not enabled:
                    if self.active is None:
                        self.active = beat
                        self.setups.append(beat)
                    else:
                        assert beat == self.active
                else:
                    assert self.active is not None, "ACCESS without a fresh SETUP"
                    assert beat == self.active, (
                        "Captured request changed before completion"
                    )
                    if self.v("pready_i"):
                        owner = (beat[0] >> 16) - 1
                        assert owner in (0, 1)
                        assert replies[owner] == 1 and replies[1 - owner] == 0
                        self.transfers.append(beat)
                        self.responses.append(
                            (
                                owner,
                                self.v(f"m{owner}_pslverr_o"),
                                self.v(f"m{owner}_prdata_o"),
                            )
                        )
                        self.active = None
            else:
                self.active = None
            for m in range(2):
                if not replies[m]:
                    assert not self.v(f"m{m}_pslverr_o") and not self.v(
                        f"m{m}_prdata_o"
                    )
            assert bool(any(replies)) == bool(
                selected and enabled and self.v("pready_i")
            )
        else:
            assert not self.v("psel_o") and not self.v("penable_o") and not any(replies)
            self.active = None
        self.d.clk_i.value = 1
        await Timer(5, unit="ns")
        return replies

    async def reset(self):
        await self.tick(
            rst_ni=0,
            pready_i=0,
            pslverr_i=0,
            prdata_i=0,
            **self.master(0, 0),
            **self.master(1, 0),
        )
        await self.tick(rst_ni=1)

    async def idle(self, count=3, **kw):
        for _ in range(count):
            await self.tick(**kw)


@cocotb.test()
async def simultaneous_requests_lock_wait_state_payload_and_route_error(d):
    b = Bench(d)
    await b.reset()
    await b.tick(**b.master(0), **b.master(1))
    await b.tick(**b.master(0, enable=1), **b.master(1, enable=1))
    await b.idle(12)
    assert not b.transfers and b.v("paddr_o") == 0x10024
    replies = await b.tick(pready_i=1, pslverr_i=1, prdata_i=0xF00DBAAD)
    assert replies == (1, 0)
    await b.tick(**b.master(0, 0), pready_i=0)
    await b.idle(8)
    assert len(b.transfers) == 1 and b.v("paddr_o") == 0x20024
    await b.tick(pready_i=1, pslverr_i=0, prdata_i=0x12345678)
    await b.tick(**b.master(1, 0))
    assert b.responses == [(0, 1, 0xF00DBAAD), (1, 0, 0x12345678)]
    assert len(b.setups) == 2


@cocotb.test()
async def repeated_contention_is_fair_and_each_transfer_has_new_setup(d):
    b = Bench(d)
    await b.reset()
    enable = [0, 0]
    counter = [0, 0]
    for _ in range(160):
        kw = {}
        for m in range(2):
            kw.update(
                b.master(
                    m,
                    enable=enable[m],
                    address=((m + 1) << 16) + 4 * counter[m],
                    data=counter[m],
                )
            )
        replies = await b.tick(pready_i=1, **kw)
        for m in range(2):
            if replies[m]:
                counter[m] += 1
                enable[m] = 0
            else:
                enable[m] = 1
    owners = [x[0] for x in b.responses]
    assert len(owners) >= 30 and owners == [i % 2 for i in range(len(owners))]
    assert abs(counter[0] - counter[1]) <= 1 and len(b.setups) >= len(b.transfers)
    for m in range(2):
        assert [x[2] for x in b.transfers if (x[0] >> 16) == m + 1] == list(
            range(counter[m])
        )


@cocotb.test()
async def withdrawn_owner_and_reset_never_acknowledge_or_reuse_stale_payload(d):
    b = Bench(d)
    await b.reset()
    await b.tick(**b.master(1))
    await b.tick(**b.master(1, enable=1))
    await b.idle(4)
    await b.tick(**b.master(1, 0), pready_i=1)
    assert not b.transfers
    await b.tick(**b.master(0))
    await b.tick(**b.master(0, enable=1), pready_i=0)
    await b.idle(4)
    await b.tick(rst_ni=0, pready_i=1)
    assert not b.transfers
    await b.tick(rst_ni=1, **b.master(0, 0), **b.master(1, 0))
    await b.tick(**b.master(1, address=0x20080, data=0x778899AA))
    await b.tick(**b.master(1, enable=1, address=0x20080, data=0x778899AA))
    await b.tick()
    await b.tick(**b.master(1, 0))
    await b.idle()
    assert b.transfers == [(0x20080, 1, 0x778899AA, 15)]


@cocotb.test()
async def parked_timed_out_cpu_request_cannot_retrigger_after_late_ready(d):
    b = Bench(d)
    await b.reset()
    await b.tick(**b.master(0))
    await b.tick(**b.master(0, enable=1))
    await b.idle(15)
    # Matches frozen soc_apb_bridge to_fired behavior: master remains in ACCESS
    # after the fabric timeout and ignores any later ready until system reset.
    await b.tick(pready_i=1)
    await b.idle(18)
    assert len(b.transfers) == 1 and len(b.responses) == 1, (
        "Parked CPU request replayed"
    )
    # A parked completed master must not block the other master's fresh request.
    await b.tick(**b.master(1))
    await b.tick(**b.master(1, enable=1))
    for _ in range(8):
        replies = await b.tick()
        if replies[1]:
            break
    else:
        raise AssertionError("Parked completed CPU starved PCIe")
    await b.tick(**b.master(1, 0))
    await b.idle(8)
    assert [r[0] for r in b.responses] == [0, 1]
    # A genuine new SETUP rearms the CPU request even with PSEL continuously 1.
    await b.tick(**b.master(0, enable=0, address=0x10088, data=0x55))
    await b.tick(**b.master(0, enable=1, address=0x10088, data=0x55))
    for _ in range(6):
        replies = await b.tick()
        if replies[0]:
            break
    else:
        raise AssertionError("New CPU SETUP did not rearm")
    assert b.transfers[-1] == (0x10088, 1, 0x55, 15)


@cocotb.test()
async def completed_pcie_access_is_also_single_shot_until_a_fresh_setup(d):
    b = Bench(d)
    await b.reset()
    await b.tick(**b.master(1))
    await b.tick(**b.master(1, enable=1))
    await b.idle(4)
    await b.tick(pready_i=1)
    await b.idle(20)
    assert len(b.transfers) == 1 and b.responses[0][0] == 1
    await b.tick(**b.master(0))
    await b.tick(**b.master(0, enable=1))
    for _ in range(8):
        replies = await b.tick()
        if replies[0]:
            break
    else:
        raise AssertionError("Completed PCIe request starved CPU")
    await b.tick(**b.master(0, 0))
    await b.idle(5)
    assert [r[0] for r in b.responses] == [1, 0]


@cocotb.test()
async def round_robin_preference_survives_idle_before_next_simultaneous_tie(d):
    b = Bench(d)
    await b.reset()
    await b.tick(**b.master(0))
    await b.tick(**b.master(0, enable=1), pready_i=1)
    await b.tick()
    await b.tick(**b.master(0, 0))
    await b.idle(5)
    assert [r[0] for r in b.responses] == [0]
    await b.tick(**b.master(0), **b.master(1), pready_i=0)
    await b.tick(**b.master(0, enable=1), **b.master(1, enable=1))
    await b.idle(4)
    assert b.v("paddr_o") == 0x20024
    await b.tick(pready_i=1, pslverr_i=1, prdata_i=0x55AA)
    assert b.responses[-1] == (1, 1, 0x55AA)
