# SPDX-FileCopyrightText: 2026 Hasan Melih Akbulut
# SPDX-License-Identifier: Apache-2.0
"""Independent bit-cell recurrence and port queue, with published state anchors."""

import random
from collections import deque

import cocotb
from cocotb.triggers import Timer

SEEDS = (0x1DBFBC, 0x0607BB, 0x1EC760, 0x18C0DB)
# PCI-SIG Base4 draft AppendixC.2 first eight lane0 byte-boundary states.
# Facts used as recurrence anchors; output bytes are computed, not copied code.
ANCHORS = (
    0x1DBFBC,
    0x498C2E,
    0x1186E9,
    0x0FC5AD,
    0x7CB75D,
    0x3D8DA2,
    0x0ECC8F,
    0x379717,
)


def cells(value):
    return [(value >> bit) & 1 for bit in range(23)]


def shift(old):
    # Explicit independent flip-flop equations, no integer feedback mask.
    return [
        (old[i - 1] if i else 0) ^ (old[22] if i in (0, 2, 5, 8, 16, 21) else 0)
        for i in range(23)
    ]


def transform(states, data, advance, scramble, reseed):
    result = data
    for lane in range(4):
        for bit in range(32):
            byte = lane * 4 + bit // 8
            if (scramble >> byte) & 1:
                result ^= states[lane][22] << (lane * 32 + bit)
            if (advance >> byte) & 1:
                states[lane] = shift(states[lane])
        if (reseed >> lane) & 1:
            states[lane] = cells(SEEDS[lane])
    return result


async def exercise(d, seed, saturated=False, interrupts=False):
    state = cells(SEEDS[0])
    for anchor in ANCHORS:
        assert sum(v << i for i, v in enumerate(state)) == anchor
        for _ in range(8):
            state = shift(state)
    states = [cells(s) for s in SEEDS]
    rng = random.Random(seed)
    queue = deque()
    pending = None
    d.clk_i.value = 0
    d.rst_ni.value = 0
    d.flush_i.value = 0
    d.valid_i.value = 0
    d.ready_i.value = 0
    d.data_i.value = 0
    d.advance_i.value = 0
    d.scramble_i.value = 0
    d.reseed_after_i.value = 0
    await Timer(2, unit="ns")
    d.clk_i.value = 1
    await Timer(2, unit="ns")
    accepted = consumed = stalls = 0
    advance_masks = [set() for _ in range(4)]
    reseed_events = [0] * 4
    for cycle in range(2010):
        drain = cycle >= 2000
        d.clk_i.value = 0
        reset = interrupts and cycle % 173 == 79
        flush = interrupts and cycle % 211 == 51
        active = not reset and not flush
        d.rst_ni.value = int(not reset)
        d.flush_i.value = int(flush)
        if not active:
            states = [cells(s) for s in SEEDS]
            queue.clear()
            pending = None
        if pending is None and not drain and (saturated or rng.random() < 0.8):
            advance = rng.getrandbits(16)
            scramble = advance & rng.getrandbits(16)
            # Periodically emulate fully scrambled payload words, hold-only
            # SKP payload words and bypassed-but-advancing ordered-set words.
            if cycle % 7 == 0:
                advance = scramble = 0xFFFF
            elif cycle % 7 == 1:
                advance = scramble = 0
            elif cycle % 7 == 2:
                advance, scramble = 0xFFFF, 0
            pending = (
                rng.getrandbits(128),
                advance,
                scramble,
                rng.getrandbits(4) if cycle % 11 == 0 else 0,
            )
            if cycle == 0:
                pending = (0, 0xFFFF, 0xFFFF, 0)
        ready = drain or saturated or rng.random() < 0.65
        d.ready_i.value = int(ready)
        d.valid_i.value = int(pending is not None)
        for port, value in zip(
            (d.data_i, d.advance_i, d.scramble_i, d.reseed_after_i),
            pending or (0, 0, 0, 0),
        ):
            port.value = value
        await Timer(2, unit="ns")
        valid = bool(int(d.valid_o.value))
        assert valid == (active and bool(queue)), (cycle, "valid")
        assert bool(int(d.ready_o.value)) == (active and (not queue or ready))
        if valid:
            assert int(d.data_o.value) == queue[0], (cycle, "scrambled stream")
            if cycle == 1:
                assert (int(d.data_o.value) & 0xFFFFFFFF) == 0x9894BD6C
            if ready:
                queue.popleft()
                consumed += 1
            else:
                stalls += 1
        if pending is not None and int(d.ready_o.value):
            for lane in range(4):
                advance_masks[lane].add((pending[1] >> (4 * lane)) & 15)
                reseed_events[lane] += (pending[3] >> lane) & 1
            queue.append(transform(states, *pending))
            pending = None
            accepted += 1
        if saturated and 1 <= cycle < 2000:
            assert valid and ready
        d.clk_i.value = 1
        await Timer(2, unit="ns")
    assert not queue and pending is None
    assert accepted > 700 and consumed > 700
    assert all(s == set(range(16)) for s in advance_masks)
    assert all(n > 10 for n in reseed_events)
    if not saturated:
        assert stalls > 150
    if not interrupts:
        assert accepted == consumed
    d._log.info("accepted=%d consumed=%d stalled=%d", accepted, consumed, stalls)


@cocotb.test()
async def seeded_independent_cells_and_byte_controls(d):
    await exercise(d, 0x23B170)


@cocotb.test()
async def consecutive_words_without_bubbles(d):
    await exercise(d, 0xAB23, saturated=True)


@cocotb.test()
async def flush_reset_and_stalled_reseed(d):
    await exercise(d, 0x1DBFBC, interrupts=True)
