# SPDX-License-Identifier: Apache-2.0
"""Independent serial bit-list -> complete public record queue oracle.
Clocks and raw bits are explicit testbench sources, not an analog CDR/PMA model.
No DUT classifier, LFSR, private state, hierarchy or report is used as an oracle.
"""
from collections import deque
import random
import cocotb
from cocotb.triggers import Timer

EIEOS = (int("ff00"*8,16)<<2)|1
SDS = (int.from_bytes(bytes([0xe1]+[0x55]*15),"little")<<2)|1

class Front:
    def __init__(self,d):
        self.d=d;self.periods=[3899,4001,3997,4103]
        self.clocks=self.raw=self.raw_valid=0
        self.enabled=[False]*4;self.paused=[False]*4
        self.common_paused=False;self.common_is_paused=False
        self.ready=15;self.offsets=[0,1,17,31];self.epoch=0
        self.expected=[deque()for _ in range(4)]
        self.bits=[0]*4;self.count=[0]*4;self.index=[0]*4
        self.seen=[0]*4;self.held=[None]*4
        self.lengths=[set()for _ in range(4)]
        self.realign=[0]*4;self.eieos=[0]*4
        self.allow_fault=0;self.error=None;self.tasks=[]

    async def until(self,condition,limit=12000):
        for _ in range(limit):
            if self.error:raise self.error
            if condition():return
            await Timer(1000,unit="ps")
        raise AssertionError("Bounded shared-front scenario did not complete")

    def begin(self,lanes=range(4)):
        self.epoch+=1
        for lane in lanes:
            self.bits[lane]=0;self.count[lane]=self.offsets[lane];self.index[lane]=0
            self.expected[lane].clear();self.seen[lane]=0;self.held[lane]=None
            self.lengths[lane].clear();self.realign[lane]=self.eieos[lane]=0
            self.enabled[lane]=True

    async def start(self,wait_all=True):
        for n in ("por_ni","reset_i","recovered_clk_i","common_clk_i",
                  "raw_valid_i","raw_i","align_control_i","force_realign_i","record_ready_i"):
            getattr(self.d,n).value=0
        await Timer(1,unit="ps")
        self.tasks=[cocotb.start_soon(self.writer(k))for k in range(4)]
        self.tasks.append(cocotb.start_soon(self.reader()))
        await Timer(50000,unit="ps")
        self.d.align_control_i.value=15;self.d.por_ni.value=1
        if wait_all:
            await self.until(lambda:int(self.d.lane_running_o.value)==15 and int(self.d.common_running_o.value)==15)
            self.begin()

    def next_word(self,lane):
        while self.count[lane]<32:
            i=self.index[lane]
            if i==0:
                value,width,code,skp,eieos,realign=EIEOS,130,2,0,1,1
            elif i in (1,2):
                # Opaque OS records before SDS are retained, not accepted as TS.
                payload=int.from_bytes(bytes([0x4a+i,lane,self.epoch&255]+[17+i]*13),"little")
                value,width,code,skp,eieos,realign=(payload<<2)|1,130,2,0,0,0
            elif i==3:
                value,width,code,skp,eieos,realign=SDS,130,2,0,0,0
            else:
                phase=(i-4)%6
                if phase==0:
                    payload=random.Random(0x840000+self.epoch*100000+lane*2000+i).getrandbits(128)
                    if (i//6)%3==1:payload=EIEOS>>2
                    value,width,code,skp,eieos,realign=(payload<<2)|2,130,2,0,0,0
                else:
                    code=phase-1
                    symbols=[0xaa]*(4+4*code)+[0xe1,0x4d^lane,0x80|(i&127),0xc3]
                    value=(int.from_bytes(bytes(symbols),"little")<<2)|1
                    width,skp,eieos,realign=66+32*code,1,0,0
            self.expected[lane].append((value,code,skp,eieos,realign))
            self.bits[lane]|=value<<self.count[lane]
            self.count[lane]+=width;self.index[lane]+=1
        word=self.bits[lane]&0xffffffff
        self.bits[lane]>>=32;self.count[lane]-=32
        return word

    async def writer(self,lane):
        mask=1<<lane
        await Timer(13+137*lane,unit="ps")
        try:
            while True:
                self.clocks&=~mask;self.d.recovered_clk_i.value=self.clocks
                if self.paused[lane]:
                    await Timer(100,unit="ps");continue
                valid=self.enabled[lane] and bool(int(self.d.lane_running_o.value)&mask)
                self.raw_valid=(self.raw_valid&~mask)|(mask if valid else 0)
                if valid:
                    self.raw=(self.raw&~(0xffffffff<<(32*lane)))|(self.next_word(lane)<<(32*lane))
                self.d.raw_valid_i.value=self.raw_valid;self.d.raw_i.value=self.raw
                await Timer(self.periods[lane]//2,unit="ps")
                self.clocks|=mask;self.d.recovered_clk_i.value=self.clocks
                await Timer(self.periods[lane]-self.periods[lane]//2,unit="ps")
        except Exception as error:self.error=error;raise

    def item(self,lane):
        d=self.d
        return (int(d.record_block_o.value[194*lane+193:194*lane]),
                int(d.record_length_code_o.value[3*lane+2:3*lane]),
                int(d.record_skp_o.value[lane]),
                int(d.record_eieos_o.value[lane]),
                int(d.record_realign_o.value[lane]))

    async def reader(self):
        await Timer(997,unit="ps")
        try:
            while True:
                d=self.d;d.common_clk_i.value=0;d.record_ready_i.value=self.ready
                self.common_is_paused=self.common_paused
                if self.common_paused:
                    await Timer(100,unit="ps");continue
                await Timer(2000,unit="ps")
                reset=not int(d.por_ni.value)or int(d.reset_i.value)
                valid=int(d.record_valid_o.value);fault=int(d.common_fault_o.value)
                ready=int(d.record_ready_i.value)
                if reset:
                    assert valid==0,"Reset exposed stale front record"
                    self.held=[None]*4
                else:
                    assert not(fault&~self.allow_fault),"Unexpected front fault"
                    for lane in range(4):
                        bit=1<<lane
                        if fault&bit:
                            assert not(valid&bit),"Faulted common lane exposed a record"
                            self.held[lane]=None;continue
                        item=self.item(lane)if valid&bit else None
                        if self.held[lane]is not None:
                            assert item==self.held[lane],"Held complete front record changed"
                        self.held[lane]=item if valid&bit and not(ready&bit)else None
                        if valid&bit and ready&bit:
                            assert self.expected[lane],"Invented front record"
                            expected=self.expected[lane].popleft()
                            assert item==expected,("Complete front record mismatch",lane,self.seen[lane],item,expected)
                            self.seen[lane]+=1;self.lengths[lane].add(item[1])
                            self.eieos[lane]+=item[3];self.realign[lane]+=item[4]
                d.common_clk_i.value=1
                await Timer(2000,unit="ps")
        except Exception as error:self.error=error;raise

    async def reset(self,por=False):
        self.enabled=[False]*4
        self.d.force_realign_i.value=0
        if por:self.d.por_ni.value=0
        else:self.d.reset_i.value=1
        await Timer(50000,unit="ps")
        assert int(self.d.record_valid_o.value)==int(self.d.common_fault_o.value)==0
        self.allow_fault=0;self.ready=15
        self.d.por_ni.value=1;self.d.reset_i.value=0
        await self.until(lambda:int(self.d.lane_running_o.value)==15 and int(self.d.common_running_o.value)==15)
        self.begin()

    async def close(self):
        for task in self.tasks:task.cancel()
        await Timer(1,unit="ps")
        if self.error:raise self.error

@cocotb.test()
async def raw_bits_all_offsets_complete_fields(d):
    p=Front(d)
    try:
        await p.start()
        for phase in range(8):
            p.offsets=[phase*4+k for k in range(4)]
            await p.reset(por=bool(phase&1))
            await p.until(lambda:min(p.seen)>=40)
            assert all(x==set(range(5))for x in p.lengths),"All five lengths not exercised"
            assert p.eieos==p.realign==[1]*4,"Acquisition metadata lost or invented"
            assert int(d.lane_locked_o.value)==15,"SDS local lock not retained"
    finally:await p.close()

@cocotb.test()
async def independent_lane_stalls_preserve_every_record(d):
    p=Front(d)
    try:
        await p.start();await p.until(lambda:min(p.seen)>=10)
        for lane in range(4):
            p.ready=15^(1<<lane)
            await p.until(lambda:p.held[lane]is not None)
            before=list(p.seen)
            await Timer(24000,unit="ps")
            assert p.seen[lane]==before[lane],"Unready lane retired a record"
            assert sum(p.seen[k]-before[k]for k in range(4)if k!=lane)>0,"One lane stalled other lanes"
            p.ready=15
            await p.until(lambda:p.seen[lane]>=before[lane]+5)
    finally:await p.close()

@cocotb.test()
async def loss_overflow_realign_and_reset_exclude_old_records(d):
    p=Front(d)
    try:
        await p.start();await p.until(lambda:min(p.seen)>=10)
        p.allow_fault=2;p.enabled[1]=False
        await p.until(lambda:int(d.common_fault_o.value)&2)
        assert int(d.common_fault_o.value)==2,"Loss contaminated another lane"
        await p.reset();await p.until(lambda:min(p.seen)>=10)
        p.allow_fault=4;p.ready=11
        await p.until(lambda:int(d.common_fault_o.value)&4)
        assert int(d.lane_fault_o.value)&4,"Overflow did not fault source"
        assert int(d.common_fault_o.value)==4,"Overflow contaminated another lane"
        await p.reset(por=True);await p.until(lambda:min(p.seen)>=10)
        p.allow_fault=1;d.force_realign_i.value=1
        await p.until(lambda:int(d.common_fault_o.value)&1)
        await p.reset();await p.until(lambda:min(p.seen)>=16)
    finally:await p.close()

@cocotb.test()
async def independent_startup_and_common_clock_status_ownership(d):
    p=Front(d);p.paused[3]=True
    try:
        await p.start(wait_all=False)
        await p.until(lambda:int(d.common_running_o.value)==7 and int(d.lane_running_o.value)==7)
        p.begin(range(3));await p.until(lambda:min(p.seen[:3])>=8)
        assert p.seen[3]==0 and not(int(d.record_valid_o.value)&8),"Stopped lane leaked a record"
        assert int(d.common_fault_o.value)==0,"Startup pause invented clock loss"
        p.paused[3]=False
        await p.until(lambda:int(d.common_running_o.value)==15 and int(d.lane_running_o.value)==15)
        p.begin([3]);await p.until(lambda:p.seen[3]>=8)
        p.common_paused=True
        await p.until(lambda:p.common_is_paused)
        names=("common_running_o","common_fault_o","record_valid_o","record_block_o",
               "record_length_code_o","record_skp_o","record_eieos_o","record_realign_o")
        snapshot=tuple(int(getattr(d,n).value)for n in names)
        await Timer(1200000,unit="ps")
        assert int(d.lane_fault_o.value)!=0,"Stopped common clock did not exercise source overflow"
        assert tuple(int(getattr(d,n).value)for n in names)==snapshot,"Recovered status leaked into a stopped common domain"
        p.allow_fault=15;p.common_paused=False
        await p.until(lambda:int(d.common_fault_o.value)!=0)
        await p.reset();await p.until(lambda:min(p.seen)>=12)
    finally:await p.close()
