# SPDX-FileCopyrightText: 2026 Hasan Melih Akbulut
# SPDX-License-Identifier: Apache-2.0
import os
from collections import deque
import cocotb
from pcie_gen3_framer_support import Port, framed, tlp

CAP = int(os.environ.get("PCIE_FRAMER_CAPACITY", "150"))


@cocotb.test()
async def complete_packets_crc_fields_striping_and_idle(d):
    p = Port(d)
    await p.reset()
    cases = [
        (tlp(0), False, False),
        (tlp(0xFFF, 4), False, False),
        (bytes.fromhex("00000fff1234"), True, False),
        (tlp(0xABC, 44), False, True),
        (tlp(0x555, 128, True), False, False),
        (tlp(0x321, 128, False, True), False, False),
        (tlp(0x123, 0, True, True, read_length=1023), False, False),
    ]
    for packet, dllp, nullify in cases:
        await p.send(packet, dllp, nullify, bubbles=True)
        await p.drain(15)
    assert p.frames == len(cases) and p.good == len(cases) and p.errors == 0
    assert p.blocks > 200


@cocotb.test()
async def invalid_packets_never_emit_and_recover(d):
    p = Port(d)
    await p.reset()
    valid = tlp(0x241, 4)
    wrong_prefix = bytes([0x12]) + valid[1:]
    wrong_fmt = valid[:2] + bytes([valid[2] | 0x80]) + valid[3:]
    wrong_length = valid[:5] + bytes([7]) + valid[6:]
    bad = [
        (valid[:-1], False, None, None),
        (valid + bytes(4), False, None, None),
        (valid[:6], False, None, None),
        (wrong_prefix, False, None, None),
        (wrong_fmt, False, None, None),
        (wrong_length, False, None, None),
        (valid, False, len(valid) - 1, None),
        (valid, False, None, 8),
        (bytes(5), True, None, None),
        (bytes(7), True, None, None),
        (bytes(CAP + 1), False, None, None),
    ]
    for packet, dllp, error, type_at in bad:
        old = p.errors
        await p.send(packet, dllp, good=False, error_at=error, type_at=type_at)
        await p.drain(8)
        assert p.errors > old and p.good == 0 and p.frames == 0
    old = p.errors
    await p.send(bytes(6), dllp=True, nullify=True, good=False)
    await p.drain(8)
    assert p.errors > old and p.good == 0
    # Orphaned tail is rejected; a new SOP abandons an old partial frame.
    p.input(0x99, 1, 0, 1)
    await p.tick()
    p.input()
    for i, byte in enumerate(valid[:9]):
        p.input(byte, 1, i == 0, 0)
        assert await p.tick()
    await p.send(valid)
    await p.drain()
    assert p.frames == 1 and p.good == 1


@cocotb.test()
async def stalls_back_to_back_flush_reset_and_nullification(d):
    p = Port(d)
    await p.reset()
    a = tlp(0xABC, 128, True)
    b = tlp(0xDDD, 44)
    await p.send(a, ready_pattern=lambda i, w: i % 7 != 2 or w > 2)
    # A second packet waits while the first's complete output is stalled.
    await p.send(b, nullify=True, ready_pattern=lambda i, w: w >= 9 if i == 0 else True)
    await p.drain()
    assert p.frames == 2 and p.stalls >= 9
    # Reset after complete receipt but before the first packet block is accepted.
    await p.send(a, ready_pattern=lambda i, w: False)
    await p.tick(ready=True)  # Load a real first packet block after old IDL.
    await p.tick(ready=False)
    assert int(d.payload_o.value) != 0
    await p.tick(ready=False, reset=True)
    await p.tick()
    p.input()
    await p.drain()
    # A flush after one accepted data block cancels all remaining buffered blocks.
    await p.send(a, ready_pattern=lambda i, w: False)
    await p.tick(ready=True)
    await p.tick(ready=True)
    assert p.in_frame
    await p.tick(flush=True)
    await p.tick()
    await p.drain()
    # Flush in partial input prevents an incomplete packet leaking after recovery.
    for i, byte in enumerate(a[:40]):
        p.input(byte, 1, i == 0, 0)
        assert await p.tick()
    p.input()
    await p.tick(flush=True)
    await p.tick()
    await p.send(tlp(0x123))
    await p.drain()
    assert p.frames == 3


@cocotb.test()
async def exact_capacity_and_one_byte_overflow(d):
    p = Port(d)
    await p.reset()
    payload = ((CAP - 22) // 4) * 4
    exact = tlp(0xFFE, payload, True)
    assert len(exact) <= CAP and len(exact) > CAP - 4
    await p.send(exact, bubbles=True)
    await p.drain(100)
    assert p.good == 1 and p.frames == 1
    over = exact + bytes(CAP - len(exact) + 1)
    await p.send(over, good=False)
    await p.drain(20)
    assert p.errors >= 1 and p.good == 1 and p.frames == 1
