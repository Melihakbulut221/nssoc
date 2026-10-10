# SPDX-FileCopyrightText: 2026 Hasan Melih Akbulut
# SPDX-License-Identifier: Apache-2.0
"""Real FC DLLPs must gate encoded completions and never charge replay twice."""
import random

import cocotb
from cocotb.triggers import Timer
from test_soc_pcie_packet_tx import expected_dllp
from test_soc_pcie_tlp_stream import request, response, CID
from test_soc_pcie_tlp_integrity import frame_bytes, tlp_bytes


def fc_frame(phase, cls, header, data):
    body = bytes(((0x40, 0xc0, 0x80)[phase] + cls*16,
                  header >> 2, ((header & 3) << 6) | (data >> 8), data & 255))
    value = 0xffff
    for octet in body:
        for bit in range(8):
            feedback = ((value >> 15) ^ (octet >> bit)) & 1
            value = ((value << 1) & 0xffff) ^ (0x100b if feedback else 0)
    reflected = int(f'{value:016b}'[::-1], 2)
    return body + ((~reflected) & 65535).to_bytes(2, 'little')


class Bench:
    def __init__(self, dut):
        self.d = dut
        self.frames, self.bus, self.grants = [], [], []
        self.partial, self.held = [], None
        self.original = {}

    def v(self, name):
        return int(getattr(self.d, name).value)

    async def tick(self, **values):
        self.d.clk_i.value = 0
        for name, value in values.items():
            getattr(self.d, name).value = value
        await Timer(5, unit='ns')
        accepted = self.v('rx_valid_i') and self.v('rx_ready_o')
        if self.v('rst_ni') and self.v('link_up_i'):
            beat = tuple(self.v(n) for n in ('tx_data_o','tx_sop_o','tx_eop_o','tx_dllp_o','tx_replay_o'))
            if self.held is not None:
                assert self.v('tx_valid_o') and self.held == beat
            self.held = beat if self.v('tx_valid_o') and not self.v('tx_ready_i') else None
            if self.v('tx_valid_o') and self.v('tx_ready_i'):
                data, sop, eop, kind, replay = beat
                assert bool(sop) == (not self.partial)
                if sop:
                    self.kind, self.replay = kind, replay
                assert kind == self.kind and replay == self.replay
                self.partial.append(data)
                if eop:
                    frame = bytes(self.partial)
                    self.frames.append((kind, replay, frame))
                    if kind:
                        assert frame == expected_dllp(frame[0] == 0x10, ((frame[2] & 15) << 8) | frame[3])
                    else:
                        seq = int.from_bytes(frame[:2], 'big')
                        assert frame == frame_bytes(frame[2:-4], seq)
                        if replay:
                            assert self.original[seq] == frame
                        else:
                            assert seq not in self.original
                            self.original[seq] = frame
                    self.partial = []
            if self.v('reserve_valid_o') and self.v('reserve_ready_o'):
                self.grants.append((self.v('reserve_class_o'),self.v('reserve_payload_dw_o'),self.v('reserve_replay_o')))
            if self.v('psel_o') and self.v('penable_o') and self.v('pready_i'):
                self.bus.append(tuple(self.v(n) for n in ('paddr_o','pwrite_o','pstrb_o','pwdata_o')))
        else:
            self.partial, self.held, self.original = [], None, {}
        self.d.clk_i.value = 1
        await Timer(5, unit='ns')
        return accepted

    async def reset(self):
        await self.tick(rst_ni=0,link_up_i=0,training_i=0,retrain_done_i=0,
                        local_init_done_i=0,function_id_i=CID,rx_data_i=0,rx_sop_i=0,
                        rx_eop_i=0,rx_error_i=0,rx_valid_i=0,rx_dllp_i=0,
                        tx_ready_i=1,pready_i=1,pslverr_i=0,prdata_i=0x12345678)
        await self.tick(rst_ni=1,link_up_i=1)
        self.frames, self.bus, self.grants = [], [], []

    async def idle(self, count=50, **values):
        for _ in range(count):
            await self.tick(rx_valid_i=0,rx_sop_i=0,rx_eop_i=0,**values)

    async def wire(self, frame, dllp=False, error=False):
        for index, octet in enumerate(frame):
            for _ in range(300):
                if await self.tick(rx_data_i=octet,rx_sop_i=index==0,rx_eop_i=index==len(frame)-1,
                                   rx_valid_i=1,rx_dllp_i=dllp,rx_error_i=error):
                    break
            else:
                raise AssertionError('Input blocked')
        await self.tick(rx_valid_i=0,rx_sop_i=0,rx_eop_i=0,rx_error_i=0)

    async def config_read(self, seq, tag=0):
        await self.wire(frame_bytes(tlp_bytes(request(4,CID << 16,tag=tag)),seq))

    async def initialize(self, cpl_h=1, cpl_d=1, local=True):
        for cls in range(3):
            await self.wire(fc_frame(0,cls,cpl_h if cls==2 else 4,cpl_d if cls==2 else 4),dllp=True)
        await self.wire(fc_frame(1,0,4,4),dllp=True)
        await self.tick(local_init_done_i=local)

    def completions(self):
        return [(replay, frame) for kind,replay,frame in self.frames if not kind]


@cocotb.test()
async def crc_checked_fc_and_local_completion_gate_actual_transmission(dut):
    b = Bench(dut)
    await b.reset()
    await b.config_read(0)
    await b.idle(100)
    assert b.frames == [(1,0,expected_dllp(0,0))]
    assert not b.grants and not b.v('initialized_o')
    await b.initialize(local=False)
    await b.idle(50)
    assert not b.completions() and not b.grants
    await b.tick(local_init_done_i=1)
    await b.idle(100)
    assert b.completions() == [(0,frame_bytes(tlp_bytes(response(data=0xffff,tag=0)),0))]
    assert b.grants == [(2,1,0)] and not b.bus
    assert b.v('credit_header_consumed_o') == 1 << 16
    assert b.v('credit_data_consumed_o') == 1 << 24


@cocotb.test()
async def exhausted_credits_block_new_packet_but_nak_replay_does_not_debit(dut):
    b = Bench(dut)
    await b.reset()
    await b.initialize()
    await b.config_read(0,tag=1)
    await b.idle(100)
    first = b.completions()[0][1]
    await b.config_read(1,tag=2)
    await b.idle(100)
    assert len(b.completions()) == 1 and b.grants == [(2,1,0)]
    await b.wire(expected_dllp(1,4095),dllp=True)
    await b.idle(100)
    assert b.completions() == [(0,first),(1,first)]
    assert b.grants == [(2,1,0)]
    await b.wire(expected_dllp(0,0),dllp=True)
    await b.idle(40)
    assert b.v('outstanding_o') == 0 and b.v('buffered_o') == 1
    bad = bytearray(fc_frame(2,2,2,2));bad[-1] ^= 1
    await b.wire(bad,dllp=True)
    await b.idle(60)
    assert len(b.completions()) == 2 and len(b.grants) == 1
    await b.wire(fc_frame(2,2,2,2),dllp=True)
    await b.idle(100)
    assert b.completions()[-1] == (0,frame_bytes(tlp_bytes(response(data=0xffff,tag=2)),1))
    assert b.grants == [(2,1,0),(2,1,0)]
    assert b.v('credit_header_consumed_o') == 2 << 16


@cocotb.test()
async def stalled_frame_reset_and_infinite_credit_initialization(dut):
    b = Bench(dut)
    await b.reset()
    await b.initialize(0,0)
    await b.tick(tx_ready_i=0)
    await b.config_read(0)
    await b.idle(70)
    rng = random.Random(0xc0ff)
    for _ in range(160):
        await b.tick(tx_ready_i=rng.randrange(3)!=0)
    assert len(b.completions()) == 1 and b.grants == [(2,1,0)]
    assert b.v('credit_header_consumed_o') == b.v('credit_data_consumed_o') == 0
    await b.tick(link_up_i=0,tx_ready_i=0)
    assert not b.v('initialized_o') and b.v('buffered_o') == 0
    await b.tick(link_up_i=1,tx_ready_i=1)
    await b.config_read(0)
    await b.idle(100)
    assert len(b.completions()) == 1
    assert len(b.grants) == 1 and not b.v('initialized_o')
