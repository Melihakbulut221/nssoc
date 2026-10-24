# SPDX-FileCopyrightText: 2026 Hasan Melih Akbulut
# SPDX-License-Identifier: Apache-2.0
"""Independent serial queues cover every variable block length and bit offset."""

from collections import deque
import random

import cocotb
from cocotb.triggers import Timer

LENGTHS = (66, 98, 130, 162, 194)


async def exercise(d, seed, saturated=False, interrupts=False):
    rng = random.Random(seed)
    queues = [deque() for _ in range(4)]
    pending = None
    d.clk_i.value = d.rst_ni.value = d.flush_i.value = 0
    d.block_valid_i.value = d.word_ready_i.value = 0
    d.header_i.value = d.payload_i.value = d.length_code_i.value = 0
    await Timer(2, unit="ns")
    d.clk_i.value = 1
    await Timer(2, unit="ns")
    accepted = emitted = rejected = in_stalls = out_stalls = 0
    lengths_seen, offsets, pairs = set(), set(), set()
    previous_length = None
    for cycle in range(3040):
        drain = cycle >= 3000
        reset = interrupts and cycle % 179 == 71
        flush = interrupts and cycle % 211 == 52
        active = not (reset or flush)
        d.clk_i.value = 0
        d.rst_ni.value = int(not reset)
        d.flush_i.value = int(flush)
        if not active:
            queues = [deque() for _ in range(4)]
            pending = None
        if pending is None and not drain and (saturated or rng.random() < 0.8):
            code = rng.randrange(5)
            if not saturated and cycle % 13 == 0:
                code = 5 + cycle % 3
            # Unused high payload bits are deliberately nonzero; they must not
            # poison a following short block appended into the same reservoir.
            data = rng.getrandbits(768) | sum(
                1 << (192 * lane + 191) for lane in range(4)
            )
            pending = (code, 1 + cycle % 2, data)
        ready = drain or saturated or rng.random() < 0.6
        d.word_ready_i.value = int(ready)
        d.block_valid_i.value = int(pending is not None)
        for port, value in zip(
            (d.length_code_i, d.header_i, d.payload_i), pending or (2, 0, 0)
        ):
            port.value = value
        await Timer(2, unit="ns")
        code, header, data = pending or (2, 0, 0)
        count = len(queues[0])
        valid = bool(int(d.word_valid_o.value))
        assert valid == (active and count >= 32), (cycle, "valid/count")
        error = active and pending is not None and code > 4
        assert bool(int(d.length_error_o.value)) == error
        left = count - (32 if valid and ready else 0)
        want_ready = active and code <= 4 and left + LENGTHS[code] <= 256
        assert bool(int(d.block_ready_o.value)) == want_ready, (cycle, "capacity")
        if valid:
            expected = sum(
                q[bit] << (32 * lane + bit)
                for lane, q in enumerate(queues)
                for bit in range(32)
            )
            assert int(d.word_o.value) == expected, (cycle, "serialized bits")
            if ready:
                for q in queues:
                    for _ in range(32):
                        q.popleft()
                emitted += 32
            else:
                out_stalls += 1
        if pending is not None and want_ready:
            length = LENGTHS[code]
            lengths_seen.add(length)
            offsets.add(len(queues[0]) % 32)
            if previous_length is not None:
                pairs.add((previous_length, length))
            previous_length = length
            for lane, q in enumerate(queues):
                bits = ((data >> (lane * 192)) << 2) | header
                q.extend((bits >> bit) & 1 for bit in range(length))
            accepted += length
            pending = None
        elif error:
            rejected += 1
            pending = None  # Explicit rejection permits caller to correct it.
        elif pending is not None and active:
            in_stalls += 1
        if saturated and 1 <= cycle < 3000:
            assert valid and ready, (cycle, "continuous demand bubble")
        d.clk_i.value = 1
        await Timer(2, unit="ns")
    assert pending is None and all(len(q) < 32 for q in queues)
    assert lengths_seen == set(LENGTHS) and offsets == set(range(0, 32, 2))
    assert len(pairs) == 25 and accepted > 35000 and emitted > 30000 and in_stalls > 500
    if not saturated:
        assert rejected > 10 and out_stalls > 500
    if not interrupts:
        assert accepted == emitted + len(queues[0])
    d._log.info(
        "acceptedbits=%d emittedbits=%d rejected=%d", accepted, emitted, rejected
    )


@cocotb.test()
async def mixed_lengths_and_invalid_codes(d):
    await exercise(d, 0x6698194)


@cocotb.test()
async def sustained_variable_block_stream(d):
    await exercise(d, 0x130194, saturated=True)


@cocotb.test()
async def flush_discards_partial_reservoir(d):
    await exercise(d, 0x16232, interrupts=True)


@cocotb.test()
async def drain_all_even_remainders(d):
    # A continuous random stream rarely drains to a particular residue. Prove
    # the not-yet-a-word boundary for every reachable even residue explicitly.
    d.flush_i.value = 0
    d.word_ready_i.value = 1
    d.length_code_i.value = 0
    d.header_i.value = 2
    data = sum((lane + 1) << (192 * lane) for lane in range(4))
    d.payload_i.value = data
    for blocks in range(1, 17):
        d.clk_i.value = 0
        d.rst_ni.value = 0
        d.block_valid_i.value = 0
        await Timer(2, unit="ns")
        d.clk_i.value = 1
        await Timer(2, unit="ns")
        queues = [deque() for _ in range(4)]
        sent = words = 0
        for cycle in range(4 * blocks + 16):
            d.clk_i.value = 0
            d.rst_ni.value = 1
            d.block_valid_i.value = int(sent < blocks)
            await Timer(2, unit="ns")
            count = len(queues[0])
            valid = bool(int(d.word_valid_o.value))
            assert valid == (count >= 32), (blocks, cycle, count)
            if valid:
                expected = sum(
                    q[bit] << (32 * lane + bit)
                    for lane, q in enumerate(queues)
                    for bit in range(32)
                )
                assert int(d.word_o.value) == expected
                for q in queues:
                    for _ in range(32):
                        q.popleft()
                words += 1
            if sent < blocks and int(d.block_ready_o.value):
                for lane, q in enumerate(queues):
                    bits = ((lane + 1) << 2) | 2
                    q.extend((bits >> bit) & 1 for bit in range(66))
                sent += 1
            d.clk_i.value = 1
            await Timer(2, unit="ns")
        assert sent == blocks and words == blocks * 66 // 32
        assert all(len(q) == blocks * 66 % 32 for q in queues)
