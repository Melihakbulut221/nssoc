# SPDX-FileCopyrightText: 2026 Hasan Melih Akbulut
# SPDX-License-Identifier: Apache-2.0
"""Independent per-lane serial-bit FIFOs; never compare only TX/RX loopback."""

from collections import deque
import random

import cocotb
from cocotb.triggers import Timer


def bits(value, width):
    return [(value >> bit) & 1 for bit in range(width)]


def peek(queue, width):
    return sum(queue[i] << i for i in range(width))


async def exercise(d, seed, cycles, stalls=True, interruptions=False):
    rng = random.Random(seed)
    tx = [deque() for _ in range(4)]
    rx = [deque() for _ in range(4)]
    pending_block = pending_word = None
    d.clk_i.value = 0
    d.rst_ni.value = 0
    d.flush_i.value = 0
    d.tx_block_valid_i.value = 0
    d.tx_header_i.value = 0
    d.tx_payload_i.value = 0
    d.tx_word_ready_i.value = 0
    d.rx_word_valid_i.value = 0
    d.rx_word_i.value = 0
    d.rx_block_ready_i.value = 0
    await Timer(5, unit="ns")
    d.clk_i.value = 1
    await Timer(5, unit="ns")
    d.rst_ni.value = 1
    accepted_blocks = accepted_words = tx_words = rx_blocks = 0
    tx_residues, rx_residues = set(), set()
    stalled_tx = stalled_rx = simultaneous_tx = simultaneous_rx = 0
    for cycle in range(cycles + 16):
        draining = cycle >= cycles
        d.clk_i.value = 0
        reset = interruptions and cycle % 239 == 113
        flush = interruptions and cycle % 181 == 71
        active = not reset and not flush
        d.rst_ni.value = int(not reset)
        d.flush_i.value = int(flush)
        if not active:
            for q in tx + rx:
                q.clear()
            pending_block = pending_word = None
        if (
            pending_block is None
            and not draining
            and (not stalls or rng.random() < 0.7)
        ):
            pending_block = (
                rng.choice((1, 2)),
                [rng.getrandbits(128) for _ in range(4)],
            )
        if pending_word is None and not draining and (not stalls or rng.random() < 0.8):
            pending_word = [rng.getrandbits(32) for _ in range(4)]
        tr = draining or not stalls or rng.random() < 0.65
        rr = draining or not stalls or rng.random() < 0.6
        d.tx_block_valid_i.value = int(pending_block is not None)
        d.tx_header_i.value = pending_block[0] if pending_block else 0
        d.tx_payload_i.value = (
            sum(v << (128 * i) for i, v in enumerate(pending_block[1]))
            if pending_block
            else 0
        )
        d.tx_word_ready_i.value = int(tr)
        d.rx_word_valid_i.value = int(pending_word is not None)
        d.rx_word_i.value = (
            sum(v << (32 * i) for i, v in enumerate(pending_word))
            if pending_word
            else 0
        )
        d.rx_block_ready_i.value = int(rr)
        await Timer(5, unit="ns")
        tv = bool(int(d.tx_word_valid_o.value))
        rv = bool(int(d.rx_block_valid_o.value))
        assert tv == (active and len(tx[0]) >= 32), (cycle, "TX valid")
        assert rv == (active and len(rx[0]) >= 130), (cycle, "RX valid")
        if not active:
            assert int(d.tx_block_ready_o.value) == int(d.rx_word_ready_o.value) == 0
        if tv:
            assert int(d.tx_word_o.value) == sum(
                peek(q, 32) << (32 * i) for i, q in enumerate(tx)
            ), (cycle, "TX bit stream")
        if rv:
            assert int(d.rx_header_o.value) == sum(
                peek(q, 2) << (2 * i) for i, q in enumerate(rx)
            ), (cycle, "RX headers")
            assert int(d.rx_payload_o.value) == sum(
                (peek(q, 130) >> 2) << (128 * i) for i, q in enumerate(rx)
            ), (cycle, "RX payloads")
        stalled_tx += tv and not tr
        stalled_rx += rv and not rr
        tp = tv and tr
        rp = rv and rr
        if tp:
            for q in tx:
                for _ in range(32):
                    q.popleft()
            tx_words += 1
        if rp:
            for q in rx:
                for _ in range(130):
                    q.popleft()
            rx_blocks += 1
        tb = bool(int(d.tx_block_ready_o.value)) and pending_block is not None
        rw = bool(int(d.rx_word_ready_o.value)) and pending_word is not None
        if tb:
            for lane, q in enumerate(tx):
                q.extend(bits(pending_block[0], 2) + bits(pending_block[1][lane], 128))
            accepted_blocks += 1
            pending_block = None
        if rw:
            for lane, q in enumerate(rx):
                q.extend(bits(pending_word[lane], 32))
            accepted_words += 1
            pending_word = None
        simultaneous_tx += tp and tb
        simultaneous_rx += rp and rw
        assert all(len(q) <= 160 for q in tx + rx)
        tx_residues.add(len(tx[0]) % 32)
        rx_residues.add(len(rx[0]) % 130)
        if not stalls and not interruptions and 1 <= cycle < cycles:
            assert tv and tr, "Saturated transmitter inserted a word bubble"
        d.clk_i.value = 1
        await Timer(5, unit="ns")
    assert pending_block is None and pending_word is None
    assert len(tx[0]) < 32 and len(rx[0]) < 130
    assert accepted_blocks > 100 and accepted_words > 300
    assert simultaneous_tx > 50 and simultaneous_rx > 50
    assert tx_residues == set(range(0, 32, 2))
    assert rx_residues == set(range(0, 130, 2))
    if stalls:
        assert stalled_tx > 100 and stalled_rx > 50
    if not interruptions:
        assert accepted_blocks * 130 == tx_words * 32 + len(tx[0])
        assert accepted_words * 32 == rx_blocks * 130 + len(rx[0])
    d._log.info(
        "source blocks=%d words=%d sink words=%d blocks=%d",
        accepted_blocks,
        accepted_words,
        tx_words,
        rx_blocks,
    )


@cocotb.test()
async def independent_random_serial_oracles(d):
    await exercise(d, 0x130032, 2400)


@cocotb.test()
async def saturated_continuous_words(d):
    await exercise(d, 0x1234, 1800, stalls=False)


@cocotb.test()
async def reset_and_flush_partial_blocks(d):
    await exercise(d, 0xC1EA, 2600, interruptions=True)
