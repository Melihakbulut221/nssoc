# SPDX-FileCopyrightText: 2026 Hasan Melih Akbulut
# SPDX-License-Identifier: Apache-2.0
"""Public RX/APB/merged-output integration checks, with independent CRC oracles."""

import random
import cocotb
from cocotb.triggers import Timer

# Import only undecorated helpers/classes; imported test functions are not exposed.
from test_soc_pcie_packet_tx import expected_dllp
from test_soc_pcie_packet_endpoint import Bench as EndpointBench
from test_soc_pcie_tlp_stream import Bench as StreamBench, request, response, CID, BAR
from test_soc_pcie_tlp_integrity import frame_bytes, tlp_bytes


class Bench(EndpointBench):
    def __init__(self, d):
        super().__init__(d)
        self.kind = None
        self.dllps = []

    async def tick(self, **signals):
        self.d.clk_i.value = 0
        for name, value in signals.items():
            getattr(self.d, name).value = value
        await Timer(5, unit="ns")
        accepted = self.v("rx_valid_i") and self.v("rx_ready_o")
        if self.v("rst_ni"):
            beat = tuple(
                self.v(n) for n in ("tx_data_o", "tx_sop_o", "tx_eop_o", "tx_dllp_o")
            )
            if self.held is not None:
                assert self.v("tx_valid_o") and beat == self.held, (
                    "Stalled merged packet changed"
                )
            self.held = (
                beat if self.v("tx_valid_o") and not self.v("tx_ready_i") else None
            )
            if self.v("tx_valid_o") and self.v("tx_ready_i"):
                data, sop, eop, kind = beat
                assert bool(sop) == (not self.current)
                if sop:
                    self.kind = kind
                assert self.kind == kind, "DLLP/TLP interleaving"
                self.current.append(data)
                if eop:
                    frame = bytes(self.current)
                    self.frames.append((kind, frame))
                    self.current = []
                    if kind:
                        assert len(frame) == 6 and frame[0] in (0, 0x10)
                        assert frame == expected_dllp(
                            frame[0] == 0x10, ((frame[2] & 15) << 8) | frame[3]
                        )
                        self.dllps.append(frame)
                    else:
                        assert frame == frame_bytes(frame[2:-4], self.tx_sequence)
                        header = 4 if frame[2] & 0x20 else 3
                        words = [
                            int.from_bytes(
                                frame[i : i + 4],
                                "big" if (i - 2) // 4 < header else "little",
                            )
                            for i in range(2, len(frame) - 4, 4)
                        ]
                        self.packets.append(words)
                        self.tx_sequence = (self.tx_sequence + 1) & 4095
            if self.v("psel_o") and self.v("penable_o") and self.v("pready_i"):
                self.bus.append(
                    tuple(
                        self.v(n)
                        for n in ("paddr_o", "pwrite_o", "pstrb_o", "pwdata_o")
                    )
                )
        else:
            self.held = None
            self.current = []
            self.kind = None
            self.tx_sequence = 0
        self.d.clk_i.value = 1
        await Timer(5, unit="ns")
        self.errors += self.v("error_o")
        self.events.append(
            tuple(
                self.v(n)
                for n in (
                    "packet_accepted_o",
                    "packet_duplicate_o",
                    "packet_rejected_o",
                )
            )
        )
        return accepted

    async def reset(self):
        await StreamBench.reset(self)
        self.frames = []
        self.dllps = []
        self.events = []
        assert self.v("rx_expected_sequence_o") == self.v("tx_next_sequence_o") == 0


@cocotb.test()
async def good_request_emits_actual_ack_then_prefixed_completion(dut):
    b = Bench(dut)
    await b.reset()
    assert await b.transact(request(4, CID << 16), gap=True) == [response(data=0xFFFF)]
    assert b.frames == [
        (1, expected_dllp(0, 0)),
        (0, frame_bytes(tlp_bytes(response(data=0xFFFF)), 0)),
    ]
    assert not b.bus and not b.errors
    await b.enable()
    sequence = b.v("rx_expected_sequence_o")
    await b.send(request(0x40, BAR + 0x24, [0x12345678]))
    await b.idle()
    assert b.bus == [(0x24, 1, 15, 0x12345678)] and b.dllps[-1] == expected_dllp(
        0, sequence
    )


@cocotb.test()
async def bad_future_and_duplicate_are_serialized_without_repeated_apb(dut):
    b = Bench(dut)
    await b.reset()
    await b.enable()
    seq = b.v("rx_expected_sequence_o")
    words = request(0x40, BAR + 0x30, [0x78563412])
    packet = bytearray(frame_bytes(tlp_bytes(words), seq))
    packet[-1] ^= 1
    old = len(b.dllps)
    await b.wire(packet)
    await b.idle()
    assert not b.bus and not b.packets and b.dllps[old:] == [expected_dllp(1, seq - 1)]
    await b.send(words, sequence=seq + 1)
    await b.idle()
    assert not b.bus and len(b.dllps) == old + 1  # outstanding NAK suppression
    await b.send(words, sequence=seq)
    await b.idle()
    assert b.bus == [(0x30, 1, 15, 0x78563412)] and b.dllps[-1] == expected_dllp(0, seq)
    await b.send(words, sequence=seq)
    await b.idle()
    assert len(b.bus) == 1 and b.dllps[-1] == expected_dllp(0, seq)
    await b.send(words, sequence=seq + 2)
    await b.idle()
    assert len(b.bus) == 1 and b.dllps[-1] == expected_dllp(1, seq)
    assert b.v("rx_expected_sequence_o") == seq + 1


@cocotb.test()
async def simultaneous_queued_frames_stalls_and_reset_never_mix_packet_types(dut):
    b = Bench(dut)
    await b.reset()
    await b.enable()
    b.frames.clear()
    b.dllps.clear()
    await b.tick(tx_ready_i=0, pready_i=0)
    await b.send(request(0, BAR + 4, tag=1))
    await b.idle(35)
    assert b.v("tx_valid_o") and b.v("tx_dllp_o") and not b.bus
    await b.idle(30, pready_i=1)
    await b.send(request(0, BAR + 8, tag=2))
    await b.idle(45)
    await b.idle(20)
    rng = random.Random(0xACC)
    for _ in range(220):
        await b.tick(rx_valid_i=0, tx_ready_i=rng.randrange(2))
    await b.idle(tx_ready_i=1)
    assert b.dllps == [expected_dllp(0, 2), expected_dllp(0, 3)]
    assert b.packets == [response(data=0xD3C2B1A0, tag=t, lower=4 * t) for t in (1, 2)]
    assert len(b.bus) == 2 and not b.current
    # Reset with both a stalled generated DLLP and a pending completion.
    await b.tick(tx_ready_i=0)
    await b.send(request(4, CID << 16))
    await b.idle(60)
    assert b.v("tx_valid_o")
    await b.reset()
    await b.idle(20)
    assert not b.v("tx_valid_o") and not b.v("psel_o") and not b.frames
    assert await b.transact(request(4, CID << 16)) == [response(data=0xFFFF)]
    assert b.frames[0] == (1, expected_dllp(0, 0)) and b.frames[1][0] == 0
