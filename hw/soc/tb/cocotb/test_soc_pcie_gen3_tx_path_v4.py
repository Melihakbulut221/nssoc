# SPDX-FileCopyrightText: 2026 Hasan Melih Akbulut
# SPDX-License-Identifier: Apache-2.0
"""Compare actual scrambled/framed TX words with independent per-lane bit queues."""

import random
from collections import deque

import cocotb
from cocotb.triggers import Timer

SEEDS = (0x1DBFBC, 0x0607BB, 0x1EC760, 0x18C0DB)


def cells(value):
    return [(value >> bit) & 1 for bit in range(23)]


def append_block(queues, states, header, payload, advance, scramble, reseed):
    for lane in range(4):
        # Headers bypass the LFSR and never advance it.
        queues[lane].extend([(header >> bit) & 1 for bit in range(2)])
        for bit in range(128):
            byte = lane * 16 + bit // 8
            value = (payload >> (lane * 128 + bit)) & 1
            if (scramble >> byte) & 1:
                value ^= states[lane][22]
            queues[lane].append(value)
            if (advance >> byte) & 1:
                old = states[lane]
                states[lane] = [
                    (old[i - 1] if i else 0)
                    ^ (old[22] if i in (0, 2, 5, 8, 16, 21) else 0)
                    for i in range(23)
                ]
        if (reseed >> lane) & 1:
            states[lane] = cells(SEEDS[lane])


async def exercise(d, seed, saturated=False, interrupts=False):
    states = [cells(s) for s in SEEDS]
    queues = [deque() for _ in range(4)]
    rng = random.Random(seed)
    pending = stalled = None
    d.clk_i.value = d.rst_ni.value = d.flush_i.value = 0
    d.block_valid_i.value = d.word_ready_i.value = 0
    d.header_i.value = d.payload_i.value = 0
    d.advance_i.value = d.scramble_i.value = d.reseed_after_i.value = 0
    await Timer(2, unit="ns")
    d.clk_i.value = 1
    await Timer(2, unit="ns")
    accepted = words = output_stalls = input_stalls = resets = reseeds = 0
    masks_seen = set()
    for cycle in range(2040):
        drain = cycle >= 2000
        reset = interrupts and cycle % 173 == 79
        flush = interrupts and cycle % 211 == 51
        active = not (reset or flush)
        d.clk_i.value = 0
        d.rst_ni.value = int(not reset)
        d.flush_i.value = int(flush)
        if not active:
            states = [cells(s) for s in SEEDS]
            queues = [deque() for _ in range(4)]
            pending = stalled = None
            resets += 1
        if pending is None and not drain and (saturated or rng.random() < 0.8):
            kind = cycle % 5
            if kind == 0:
                advance = scramble = (1 << 64) - 1
            elif kind == 1:
                advance, scramble = (1 << 64) - 1, 0
            elif kind == 2:
                advance = scramble = 0
            else:
                advance = rng.getrandbits(64)
                scramble = rng.getrandbits(64)
            pending = (
                1 if cycle % 2 else 2,
                rng.getrandbits(512),
                advance,
                scramble,
                rng.getrandbits(4) if cycle % 7 == 0 else 0,
            )
        ready = drain or saturated or rng.random() < 0.63
        d.word_ready_i.value = int(ready)
        d.block_valid_i.value = int(pending is not None)
        for port, value in zip(
            (d.header_i, d.payload_i, d.advance_i, d.scramble_i, d.reseed_after_i),
            pending or (0,) * 5,
        ):
            port.value = value
        await Timer(2, unit="ns")
        valid = bool(int(d.word_valid_o.value))
        in_ready = bool(int(d.block_ready_o.value))
        if not active:
            assert not valid and not in_ready
        if stalled is not None:
            assert valid and int(d.word_o.value) == stalled, (
                cycle,
                "stalled word changed",
            )
        if valid:
            assert all(len(q) >= 32 for q in queues), (cycle, "unsolicited output")
            expected = sum(
                q[bit] << (lane * 32 + bit)
                for lane, q in enumerate(queues)
                for bit in range(32)
            )
            assert int(d.word_o.value) == expected, (cycle, "serial stream differs")
            if ready:
                for q in queues:
                    for _ in range(32):
                        q.popleft()
                words += 1
            else:
                output_stalls += 1
        stalled = int(d.word_o.value) if valid and not ready else None
        if pending is not None and in_ready:
            masks_seen.add((pending[2] == 0, pending[3] == 0))
            reseeds += bool(pending[4])
            append_block(queues, states, *pending)
            accepted += 1
            pending = None
        elif pending is not None and active:
            input_stalls += 1
        if saturated and 3 <= cycle < 2000:
            assert valid and ready, (cycle, "bubble under continuous demand")
        d.clk_i.value = 1
        await Timer(2, unit="ns")
    assert pending is None and all(len(q) < 32 for q in queues)
    assert accepted > 200 and words > 850 and input_stalls > 500
    assert len(masks_seen) >= 3 and reseeds > 10
    if not saturated:
        assert output_stalls > 400
    if not interrupts:
        assert words * 32 + len(queues[0]) == accepted * 130
    else:
        assert resets > 10
    d._log.info("blocks=%d words=%d stalls=%d", accepted, words, output_stalls)


@cocotb.test()
async def masks_headers_and_backpressure(d):
    await exercise(d, 0x13023)


@cocotb.test()
async def sustained_word_rate(d):
    await exercise(d, 0x80432, saturated=True)


@cocotb.test()
async def flushes_clear_partial_blocks_and_lfsrs(d):
    await exercise(d, 0x98742, interrupts=True)
