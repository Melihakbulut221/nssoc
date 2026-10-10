# SPDX-FileCopyrightText: 2026 Hasan Melih Akbulut
# SPDX-License-Identifier: Apache-2.0
"""Additional public-port witnesses for gathered-context ordering."""
import cocotb
import test_soc_pcie_gen3_dllp_consumer_compare_v5 as o


@cocotb.test()
async def nonadjacent_same_ids_and_zero_keep_gaps(d):
    await o.reset(d)
    packets = [o.packet(i, 1) for i in range(640)]
    p = o.Ports(d, packets)
    for i in range(0, 512, 2):
        pair = packets[i:i+2]
        a, b = [o.body_words(item) for item in pair]
        # Earlier matching owner is two lanes away, not the immediate lane.
        assert all(await p.step(pair, [a[0], b[0], a[1], b[1]]))
    empty = (0, 0, 0, 0, 0, 0, 0)
    for item in packets[512:]:
        a = o.body_words(item)
        # Inactive same-ID lanes must not overwrite either valid update.
        gap = (*empty[:6], item["owner"])
        assert all(await p.step([item], [a[0], gap, a[1], gap]))
    await p.drain()
    assert not int(d.halted_o.value) and p.accepted_events == 640


@cocotb.test()
async def latest_earlier_same_id_for_four_lane_tlp(d):
    await o.reset(d)
    # Eighteen-byte TLP requires all four first-beat updates plus the fifth
    # DWORD. Choosing the earliest matching context loses the middle updates.
    await o.run_packets(d, [o.packet(i, 0) for i in range(160)], stalls=True)


@cocotb.test()
async def prior_lane_error_survives_later_valid_same_id(d):
    await o.reset(d)
    o.drive(d, (), [(0x1234, 3, 1, 0, 0, 0, 0)])
    await o.unscored_cycle(d, {"tlp_ready_i": 1, "event_ready_i": 1})
    assert not int(d.halted_o.value)
    # First lane has illegal continuation keep=7. Later full DWORDs are
    # otherwise individually valid, so they cannot erase its sticky error.
    o.drive(d, (), [(0x123456, 7, 0, 0, 0, 0, 0)] + [(0x76543210, 15, 0, 0, 0, 0, 0)] * 3)
    await o.unscored_cycle(d)
    assert int(d.halted_o.value)
    d.epoch_i.value = 2
    o.drive(d, (), ())
    await o.unscored_cycle(d)
    await o.run_packets(d, [o.packet(i, 1) for i in range(70)])
