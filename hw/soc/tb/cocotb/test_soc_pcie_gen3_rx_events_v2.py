# SPDX-FileCopyrightText: 2026 Hasan Melih Akbulut
# SPDX-License-Identifier: Apache-2.0
"""Actual raw x4 transport through frozen CRC ownership and wide event consumer."""

from collections import deque
import cocotb
from cocotb.triggers import Timer
from test_soc_pcie_gen3_dllp_consumer_v2 import packet, expected, EVENTS

# This serial reference is independently authored and frozen with the upstream
# public-port suite, not imported from RTL/CRC generator/transmitter code.
from test_soc_pcie_gen3_continuous_rx_owned_v2 import serial_words, wire_dllp, wire_tlp


class Stream:
    def __init__(self, d, packets):
        self.d = d
        self.events = deque(expected(p) for p in packets)
        self.tlps = deque(p for p in packets if not p["dllp"] and not p["status"])
        self.partial = bytearray()
        self.held = None
        self.maximum = 0

    async def step(self, word=0, ready=1, bodyready=1):
        d = self.d
        d.clk_i.value = 0
        d.word_i.value = word
        d.event_ready_i.value = ready
        d.tlp_ready_i.value = bodyready
        await Timer(2, unit="ns")
        assert (
            not int(d.halted_o.value)
            and not int(d.overflow_o.value)
            and not int(d.framing_error_o.value)
        ), "Frontend fault"
        mask = int(d.event_valid_o.value)
        bundle = (mask,) + tuple(int(getattr(d, n).value) for n, _ in EVENTS)
        if self.held is not None:
            assert bundle == self.held
        self.held = bundle if mask and not ready else None
        if mask and ready:
            self.maximum = max(self.maximum, mask.bit_count())
            for i in range(mask.bit_count()):
                got = tuple(
                    (int(getattr(d, n).value) >> (w * i)) & ((1 << w) - 1)
                    for n, w in EVENTS
                )
                assert self.events and got == self.events.popleft(), (
                    "Actual upstream CRC/decode mismatch",
                    got,
                )
        if int(d.tlp_valid_o.value) and bodyready:
            keep = int(d.tlp_keep_o.value)
            data = int(d.tlp_data_o.value)
            sop = int(d.tlp_sop_o.value)
            eop = int(d.tlp_eop_o.value)
            owner = int(d.tlp_owner_o.value)
            seq = int(d.tlp_sequence_o.value)
            for b in range(16):
                if (keep >> b) & 1:
                    p = self.tlps[0]
                    assert ((owner >> (6 * (b // 4))) & 63) == p["owner"] and (
                        (seq >> (12 * (b // 4))) & 4095
                    ) == p["seq"]
                    assert bool((sop >> b) & 1) == (not self.partial)
                    self.partial.append((data >> (8 * b)) & 255)
                    if (eop >> b) & 1:
                        assert bytes(self.partial) == p["data"]
                        self.partial.clear()
                        self.tlps.popleft()
        d.clk_i.value = 1
        await Timer(2, unit="ns")


async def reset(d):
    d.rst_ni.value = 0
    d.flush_i.value = 0
    d.stream_start_i.value = 0
    d.stream_abort_i.value = 0
    s = Stream(d, [])
    for _ in range(3):
        await s.step()
    d.rst_ni.value = 1
    await s.step()
    d.stream_start_i.value = 1
    await s.step()
    d.stream_start_i.value = 0


async def run(d, packets, stalls=False):
    data = bytearray()
    for p in packets:
        raw = p["data"]
        if p["status"] == 1:
            raw = raw[:-1] + bytes([raw[-1] ^ 1])
        data += wire_dllp(raw) if p["dllp"] else wire_tlp(raw, p["status"] == 2)
    data += bytes(4096)
    words = serial_words(bytes(data))
    s = Stream(d, packets)
    for i, w in enumerate(words):
        await s.step(
            w,
            not stalls or i % 101 not in (30, 31),
            not stalls or i % 113 not in (40, 41),
        )
    assert not s.events and not s.tlps and not s.partial, "Raw stream failed to drain"
    return s


@cocotb.test()
async def actual_raw_x4_crc_discard_and_ordered_fields(d):
    await reset(d)
    packets = [
        packet(
            i,
            0 if i % 7 == 0 else 1,
            status=2 if i % 49 == 0 else 1 if i % 11 == 0 else 0,
        )
        for i in range(600)
    ]
    s = await run(d, packets, True)
    assert s.maximum >= 2


@cocotb.test()
async def actual_raw_x4_no_idle_dllps_exceed_every_buffer(d):
    await reset(d)
    s = await run(d, [packet(i, 1) for i in range(1200)])
    assert s.maximum >= 2


@cocotb.test()
async def held_event_abort_ready_same_edge_discards_old_epoch(d):
    await reset(d)
    stale = packet(0, 1, body=bytes.fromhex("00000003"))
    s = Stream(d, [stale])
    for word in serial_words(wire_dllp(stale["data"]) + bytes(1024)):
        await s.step(word, ready=0)
        if int(d.event_valid_o.value):
            break
    else:
        raise AssertionError("No held event to abort")
    prior_epoch = int(d.epoch_o.value)
    d.clk_i.value = 0
    d.stream_abort_i.value = 1
    d.event_ready_i.value = 1
    await Timer(2, unit="ns")
    assert int(d.event_valid_o.value) == 0, (
        "Old DLLP event can handshake on explicit abort edge"
    )
    assert int(d.tlp_valid_o.value) == 0
    d.clk_i.value = 1
    await Timer(2, unit="ns")
    assert int(d.epoch_o.value) != prior_epoch
    assert int(d.halted_o.value), "Explicit abort must halt the upstream epoch"
    d.stream_abort_i.value = 0
    d.stream_start_i.value = 1
    d.clk_i.value = 0
    d.word_i.value = 0
    await Timer(2, unit="ns")
    assert int(d.event_valid_o.value) == 0
    d.clk_i.value = 1
    await Timer(2, unit="ns")
    assert not int(d.halted_o.value), "Start edge did not clear prior abort"
    d.stream_start_i.value = 0
    await run(d, [packet(i, 1) for i in range(30)])
