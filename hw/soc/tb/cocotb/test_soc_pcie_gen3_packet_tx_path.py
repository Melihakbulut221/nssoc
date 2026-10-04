# SPDX-FileCopyrightText: 2026 Hasan Melih Akbulut
# SPDX-License-Identifier: Apache-2.0
import cocotb
from pcie_gen3_framer_support import Port, tlp


@cocotb.test()
async def packet_to_native_serial_words(d):
    p = Port(d, wrapped=True)
    await p.reset()
    await p.send(tlp(0x12A, 128, True), bubbles=True)
    await p.send(bytes.fromhex("00123456789a"), dllp=True)
    await p.send(tlp(0xFFF, 44), nullify=True, bubbles=True)
    await p.drain(150)
    assert p.good == 3 and p.frames == 3 and p.words > 300


@cocotb.test()
async def held_serial_words_and_restart_preserve_packet_boundaries(d):
    p = Port(d, wrapped=True)
    await p.reset()
    await p.send(tlp(0x777, 128, True), ready_pattern=lambda i, w: i % 3 != 1 or w > 3)
    await p.drain(100)
    assert p.frames == 1 and p.stalls > 20
    # Drain first, then interrupt an incomplete input transaction and reset LFSRs.
    packet = tlp(0x222, 64)
    for i, byte in enumerate(packet[:22]):
        p.input(byte, 1, i == 0, 0)
        assert await p.tick()
    p.input()
    await p.tick(flush=True)
    await p.tick()
    await p.send(packet)
    await p.drain(100)
    assert p.frames == 2
