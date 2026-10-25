# SPDX-FileCopyrightText: 2026 Hasan Melih Akbulut
# SPDX-License-Identifier: Apache-2.0
"""Public raw bits to exact owned events and TLP bytes; no internal state oracle."""
from collections import deque
import zlib

import cocotb
from cocotb.triggers import Timer
from test_soc_pcie_gen3_recovered_x4_v3 import Link as RawLink, EIEOS, SDS, SEEDS, transform
from test_soc_pcie_gen3_dllp_consumer_v6 import packet, expected, EVENTS
from test_soc_pcie_gen3_continuous_rx_integrity_v4 import tlp, wire_tlp, wire_dllp

EDS=bytes.fromhex('1f809000')
EIOS=(int.from_bytes(bytes([0x66]*16),'little')<<2)|1


class Link(RawLink):
    def __init__(self,d,case='mixed',count=300,batch=20):
        super().__init__(d)
        self.case=case;self.count_packets=count;self.batch=batch
        self.records=[deque() for _ in range(4)]
        self.events=deque();self.tlps=deque();self.skps=deque()
        self.partial=bytearray();self.event_held=None;self.body_held=None
        self.ends=self.stops=self.event_count=self.tlp_count=self.skp_count=self.cycles=self.maximum=0
        self.event_ready=self.body_ready=1
        self.allow_fault=case in ('overflow','bad_token','missing_eds')
        self.epoch=None

    async def start(self,auto_arm=True):
        d=self.d
        for n in ('por_ni','reset_i','abort_i','recovered_clk_i','common_clk_i','arm_i','raw_valid_i','raw_i','align_control_i','force_realign_i','tlp_ready_i','event_ready_i'):
            getattr(d,n).value=0
        await Timer(1,unit='ps')
        self.tasks=[cocotb.start_soon(self.writer(k)) for k in range(4)]
        self.tasks.append(cocotb.start_soon(self.reader()))
        await Timer(50000,unit='ps');d.align_control_i.value=15;d.por_ni.value=1
        if auto_arm:await self.arm()

    def begin_words(self):
        self.events.clear();self.tlps.clear();self.skps.clear();self.partial.clear()
        self.event_held=self.body_held=None
        self.ends=self.stops=self.event_count=self.tlp_count=self.skp_count=self.starts=self.maximum=0
        self.epoch=None
        packets=[]
        for i in range(self.count_packets):
            is_dllp=(self.case=='dllps' or i%5!=0) and not (self.case in ('end_drain','end_events') and i==self.count_packets-1)
            status=1 if i%11==4 else 2 if not is_dllp and i%7==0 else 0
            p=packet(i,int(is_dllp),status=status)
            if not is_dllp and i%3==1:
                data=bytearray(tlp(p['seq'],payload=128));data[58:62]=EDS
                data[-4:]=zlib.crc32(data[:-4]).to_bytes(4,'little');p['data']=bytes(data)
            packets.append(p);self.events.append(expected(p))
            if not is_dllp and not status:self.tlps.append(p)
        for lane in range(4):
            self.bits[lane]=0;self.count[lane]=self.offsets[lane];self.index[lane]=0;self.records[lane].clear()
            for _ in range(lane+1):self.records[lane].append((EIEOS,130))
            self.records[lane].append((SDS,130));self.lfsr[lane],_=transform(SEEDS[lane]);self.parity[lane]=0
        groups=[packets[i:i+self.batch] for i in range(0,len(packets),self.batch)]
        for group,subset in enumerate(groups):
            raw=bytearray()
            for p in subset:
                # End the final TLP immediately before EDS so the normal-stop
                # edge arrives while its owned output still needs retirement.
                # Earlier over-capacity pre-stop stalls are a separate fault case.
                if self.case in ('end_drain','end_events') and p is packets[-1]:raw+=bytes((40-len(raw))%64)
                data=p['data']
                if p['status']==1:data=data[:-1]+bytes([data[-1]^1])
                raw+=wire_dllp(data) if p['dllp'] else wire_tlp(data,nullify=p['status']==2)
            raw+=bytes((60-len(raw))%64)
            raw+=bytes(4) if self.case=='missing_eds' and group==1 else EDS
            if self.case=='bad_token' and group==1:raw[0]^=0x10
            for block in range(len(raw)//64):
                for lane in range(4):
                    plain=int.from_bytes(raw[block*64+lane:(block+1)*64:4],'little')
                    self.lfsr[lane],encoded=transform(self.lfsr[lane],plain)
                    self.parity[lane]^=encoded.bit_count()&1
                    self.records[lane].append(((encoded<<2)|2,130))
            if group==len(groups)-1:
                for lane in range(4):self.records[lane].append((EIEOS if self.case=='end_eieos' else EIOS,130))
            else:
                cohort=[]
                for lane in range(4):
                    code=group%5;state=self.lfsr[lane]
                    trailer=[((state>>16)&127)|(self.parity[lane]<<7),(state>>8)&255,state&255]
                    value=(int.from_bytes(bytes([0xaa]*(4+4*code)+[0xe1]+trailer),'little')<<2)|1
                    self.records[lane].append((value,66+32*code));cohort.append((value,code));self.parity[lane]=0
                self.skps.append(cohort)
        self.enabled=[True]*4

    def next_word(self,lane):
        while self.count[lane]<32:
            value,width=self.records[lane].popleft() if self.records[lane] else (EIOS,130)
            self.bits[lane]|=value<<self.count[lane];self.count[lane]+=width
        word=self.bits[lane]&0xffffffff;self.bits[lane]>>=32;self.count[lane]-=32
        return word

    async def reader(self):
        d=self.d
        await Timer(997,unit='ps')
        try:
            while True:
                d.common_clk_i.value=0
                er=self.event_ready and (self.case!='stalls' or self.cycles%41>=3)
                br=self.body_ready and (self.case!='stalls' or self.cycles%47>=4)
                d.event_ready_i.value=int(er);d.tlp_ready_i.value=int(br)
                await Timer(2000,unit='ps')
                reset=not int(d.por_ni.value) or int(d.reset_i.value)
                fault=int(d.fault_o.value)
                if not reset:
                    if not self.allow_fault:assert not fault,('Unexpected raw-owned-event epoch fault', {n:int(getattr(d,n).value) for n in ('overflow_o','framing_error_o','lane_fault_o','halted_o','stream_stop_o')})
                    self.starts+=int(d.stream_start_o.value);self.stops+=int(d.stream_stop_o.value)
                    if int(d.stream_end_o.value):
                        assert not self.events and not self.tlps and not self.partial,'Stream end preceded ordered event retirement'
                        self.ends+=1
                    if int(d.stream_start_o.value):self.epoch=None
                    elif int(d.active_o.value) and not fault:
                        ep=int(d.epoch_o.value)
                        if self.epoch is not None:assert ep==self.epoch,'SKP changed ownership epoch'
                        self.epoch=ep
                    if int(d.skp_valid_o.value):
                        got=[(int(d.skp_block_o.value)>>(194*l)&((1<<194)-1),int(d.skp_length_code_o.value)>>(3*l)&7) for l in range(4)]
                        assert self.skps and got==self.skps.popleft(),'Raw SKP cohort changed'
                        self.skp_count+=1
                    if self.case in ('end_drain','end_events') and int(d.stream_stop_o.value):
                        self.event_ready=0
                        if self.case=='end_drain':self.body_ready=0
                    mask=int(d.event_valid_o.value)
                    bundle=(mask,)+tuple(int(getattr(d,n).value) for n,_ in EVENTS)
                    if not fault:
                        if self.event_held is not None:assert bundle==self.event_held,'Held ordered event changed'
                        self.event_held=bundle if mask and not er else None
                        if mask and er:
                            assert mask in (1,3,7,15),'Sparse descriptor/event mask'
                            self.maximum=max(self.maximum,mask.bit_count())
                            for j in range(mask.bit_count()):
                                got=tuple((int(getattr(d,n).value)>>(w*j))&((1<<w)-1) for n,w in EVENTS)
                                assert self.events and got==self.events.popleft(),('Raw owned event mismatch',self.event_count,got)
                                self.event_count+=1
                        valid=int(d.tlp_valid_o.value)
                        body=tuple(int(getattr(d,n).value) for n in ('tlp_data_o','tlp_keep_o','tlp_sop_o','tlp_eop_o','tlp_sequence_o','tlp_owner_o'))
                        if self.body_held is not None:assert valid and body==self.body_held,'Held owned TLP changed'
                        self.body_held=body if valid and not br else None
                        if valid and br:
                            data,keep,sop,eop,seq,owner=body
                            assert keep and not ((sop|eop)&~keep),'TLP mask outside kept bytes'
                            for b in range(16):
                                if not ((keep>>b)&1):continue
                                assert self.tlps,'Bad/null/DLLP body escaped as TLP'
                                p=self.tlps[0]
                                assert owner>>(6*(b//4))&63==p['owner'],'Wrong TLP owner generation'
                                assert seq>>(12*(b//4))&4095==p['seq'],'Wrong TLP sequence'
                                assert bool(sop>>b&1)==(not self.partial),'TLP SOP location'
                                self.partial.append(data>>(8*b)&255)
                                assert len(self.partial)<=len(p['data']),'TLP body too long'
                                assert bool(eop>>b&1)==(len(self.partial)==len(p['data'])),'TLP EOP location'
                                if len(self.partial)==len(p['data']):
                                    assert bytes(self.partial)==p['data'],'TLP data changed'
                                    self.partial.clear();self.tlps.popleft();self.tlp_count+=1
                    else:self.event_held=self.body_held=None
                d.common_clk_i.value=1;self.cycles+=1
                await Timer(2000,unit='ps')
        except Exception as error:self.error=error;raise


async def run(d,case='mixed',count=300,batch=20,offsets=None):
    p=Link(d,case,count,batch)
    if offsets is not None:p.offsets=offsets
    if case=='overflow':p.event_ready=p.body_ready=0
    try:
        await p.start()
        if p.allow_fault:
            await p.until(lambda:int(d.fault_o.value))
            await Timer(20000,unit='ps')
            assert int(d.halted_o.value),'Transport fault did not halt ownership'
            assert int(d.event_valid_o.value)==int(d.tlp_valid_o.value)==0,'Fault left stale output visible'
            if case=='overflow':assert int(d.overflow_o.value),'Bounded ownership exhaustion did not report overflow'
        else:
            if case in ('end_drain','end_events'):
                await p.until(lambda:p.stops==1);await Timer(2000000,unit='ps')
                assert p.ends==0 and int(d.active_o.value),'Consumer events were omitted from end/drain accounting'
                assert int(d.lane_fault_o.value)!=0,'Later transport fault not exercised'
                p.event_ready=p.body_ready=1
            await p.until(lambda:p.ends==1)
            assert p.event_count==count and not p.events and not p.tlps and not p.partial
            assert p.starts==p.stops==p.ends==1
            assert not p.skps and p.skp_count==(count+batch-1)//batch-1
            assert int(d.halted_o.value)==int(d.fault_o.value)==0
        return p
    finally:await p.close()


@cocotb.test()
async def crc_bad_nullified_ack_nak_fc_and_owner_wrap(d):await run(d)
@cocotb.test()
async def complete_dllp_density_exceeds_every_owner_buffer(d):
    p=await run(d,'dllps',1200,64)
    assert p.maximum>=2,'No simultaneous ordered event retirement exercised'
@cocotb.test()
async def independent_tlp_and_event_backpressure(d):await run(d,'stalls')
@cocotb.test()
async def all_32_raw_phases_preserve_owners_and_events(d):
    for phase in range(8):await run(d,count=36,batch=12,offsets=[4*phase+k for k in range(4)])
@cocotb.test()
async def eieos_drains_all_owned_outputs(d):await run(d,'end_eieos')
@cocotb.test()
async def normal_end_keeps_held_events_during_later_lane_fault(d):await run(d,'end_drain',24,8)
@cocotb.test()
async def normal_end_waits_for_events_after_body_drains(d):await run(d,'end_events',24,8)
@cocotb.test()
async def finite_owner_exhaustion_aborts_without_stale_events(d):await run(d,'overflow')
@cocotb.test()
async def bad_token_aborts_owned_epoch(d):await run(d,'bad_token')
@cocotb.test()
async def missing_eds_aborts_owned_epoch(d):await run(d,'missing_eds')


@cocotb.test()
async def explicit_abort_suppresses_held_event_before_edge_and_reset_recovers(d):
    p=Link(d,count=48,batch=8);p.event_ready=0
    try:
        await p.start();await p.until(lambda:int(d.event_valid_o.value)!=0)
        p.allow_fault=True
        await p.until(lambda:not int(d.common_clk_i.value))
        d.abort_i.value=1;d.event_ready_i.value=1;d.tlp_ready_i.value=1
        await Timer(10,unit='ps')
        assert int(d.event_valid_o.value)==int(d.tlp_valid_o.value)==0,'Old event can handshake on explicit abort edge'
        await Timer(20000,unit='ps')
        assert int(d.halted_o.value),'Explicit abort did not halt owned epoch'
        p.enabled=[False]*4;d.reset_i.value=1;d.arm_i.value=0;d.abort_i.value=0
        await Timer(50000,unit='ps')
        assert int(d.halted_o.value)==int(d.active_o.value)==0,'Reset did not clear owned/consumer state'
        p.allow_fault=False;p.event_ready=p.body_ready=1
        d.reset_i.value=0;await p.arm();await p.until(lambda:p.ends==1)
        assert p.event_count==48 and p.starts==p.stops==p.ends==1
    finally:await p.close()
