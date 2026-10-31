# SPDX-License-Identifier: Apache-2.0
"""Public-pin command oracle; no private FSM/pointers or normative PCIe timers."""
import os
import cocotb
from cocotb.triggers import Timer
EW=int(os.environ.get("EPOCH_WIDTH","2"))
MASK=(1<<EW)-1

class Commands:
    def __init__(self,d,fronts=True):
        self.d=d;self.fronts=fronts;self.pause=[False]*4;self.pause_common=False
        self.clocks=0;self.tasks=[];self.error=None;self.edge=0
        self.pma_auto=True;self.pma_delay=3;self.pma_wait=0;self.pma_seen=False
        self.pma_wrong_epoch=False;self.pma_wrong_encoding=False;self.keep_ack=False
        self.transactions=[];self.done=[];self.active_samples=0
    def v(self,name):return int(getattr(self.d,name).value)
    async def until(self,predicate,limit=6000,label="bounded public command completion"):
        for _ in range(limit):
            if self.error:raise self.error
            if predicate():return
            await Timer(1000,unit="ps")
        raise AssertionError(label)
    async def lane(self,k):
        bit=1<<k
        await Timer(17+137*k,unit="ps")
        while True:
            self.clocks&=~bit;self.d.recovered_clk_i.value=self.clocks
            if self.pause[k]:
                await Timer(100,unit="ps");continue
            await Timer(1900+31*k,unit="ps")
            self.clocks|=bit;self.d.recovered_clk_i.value=self.clocks
            await Timer(1999+29*k,unit="ps")
    def pma(self):
        d=self.d
        if not self.pma_auto:return
        request=self.v("pma_request_o")
        if request:
            self.pma_wait+=1
            if self.pma_wait>=self.pma_delay:
                d.pma_ack_epoch_i.value=(self.v("epoch_o")+int(self.pma_wrong_epoch))&MASK
                d.pma_ack_encoding_i.value=self.v("encoding_o")^int(self.pma_wrong_encoding)
                d.pma_ack_i.value=1
        elif not self.keep_ack:
            d.pma_ack_i.value=0;self.pma_wait=0
    async def common(self):
        try:
            while True:
                self.d.common_clk_i.value=0
                if self.pause_common:
                    await Timer(100,unit="ps");continue
                self.pma()
                await Timer(2000,unit="ps")
                if self.v("por_ni"):
                    if self.transactions:
                        e,c,p,a=self.transactions[-1]
                        for k in range(4):
                            if self.v("lane_ack_o")&(1<<k):
                                assert (self.v("lane_epoch_o")>>(k*EW))&MASK==e,"stale applied lane epoch"
                                assert (self.v("lane_encoding_o")>>(k*2))&3==c,"torn applied encoding"
                                assert (self.v("lane_polarity_o")>>k)&1==(p>>k)&1,"torn applied polarity"
                                assert (self.v("lane_align_o")>>k)&1==(a>>k)&1,"torn applied alignment"
                    if self.v("command_done_o"):
                        self.done.append((self.v("epoch_o"),self.v("command_success_o")))
                    if self.v("epoch_active_o"):self.active_samples+=1
                self.d.common_clk_i.value=1;self.edge+=1
                await Timer(2000,unit="ps")
        except Exception as error:self.error=error;raise
    async def start(self):
        for n in ("por_ni","common_clk_i","recovered_clk_i","reset_i","epoch_abort_i",
                  "command_valid_i","command_encoding_i","command_polarity_i","command_align_i",
                  "pma_ack_i","pma_ack_epoch_i","pma_ack_encoding_i","fronts_ready_i"):
            if hasattr(self.d,n):getattr(self.d,n).value=0
        if self.fronts:self.d.fronts_ready_i.value=1
        await Timer(1,unit="ps")
        self.tasks=[cocotb.start_soon(self.lane(k))for k in range(4)]
        self.tasks.append(cocotb.start_soon(self.common()))
        await Timer(30000,unit="ps");self.d.por_ni.value=1
    async def issue(self,encoding=2,polarity=5,align=15,wait=True):
        await self.until(lambda:self.v("command_ready_o")==1,label="ready never returned")
        # Change command while common clock low, away from the sampling edge.
        await self.until(lambda:self.v("common_clk_i")==0)
        self.d.command_encoding_i.value=encoding;self.d.command_polarity_i.value=polarity
        self.d.command_align_i.value=align
        old=self.v("epoch_o");edge=self.edge
        self.d.command_valid_i.value=1
        await self.until(lambda:self.edge>edge)
        await Timer(1,unit="ps")
        self.d.command_valid_i.value=0
        expected=(old+1)&MASK if encoding!=3 else old
        assert self.v("epoch_o")==expected,"command epoch increment mismatch"
        self.transactions.append((expected,encoding,polarity,align))
        # Deliberately poison live caller pins after acceptance. All mailboxes
        # must capture the one held transaction, not these later caller values.
        self.d.command_encoding_i.value=encoding^1
        self.d.command_polarity_i.value=polarity^15
        self.d.command_align_i.value=align^15
        if wait and encoding!=3:
            await self.until(lambda:self.v("epoch_active_o")==1,label="applied epoch never became active")
            self.applied()
        return expected
    def applied(self):
        e,c,p,a=self.transactions[-1]
        assert self.v("epoch_o")==e and self.v("encoding_o")==c,"held common command mismatch"
        assert self.v("lane_epoch_o")==sum(e<<(k*EW)for k in range(4)),"stale applied lane epoch"
        assert self.v("lane_encoding_o")==sum(c<<(2*k)for k in range(4)),"torn applied encoding"
        assert self.v("lane_polarity_o")==p,"torn applied polarity"
        assert self.v("lane_align_o")==a,"torn applied alignment"
        assert self.v("lane_ack_o")==0 and self.v("pma_request_o")==0 and self.v("pma_ack_i")==0,"ack-low barrier bypass"
    async def close(self):
        for task in self.tasks:task.cancel()
        await Timer(1,unit="ps")
        if self.error:raise self.error

@cocotb.test()
async def held_payload_and_four_phase_ack_barrier(d):
    p=Commands(d)
    try:
        await p.start();p.pause[3]=True
        e=await p.issue(2,9,6,wait=False)
        await Timer(150000,unit="ps")
        assert not p.v("command_ready_o") and not p.v("epoch_active_o"),"stopped lane bypassed command barrier"
        assert p.v("pma_request_o") and (p.v("lane_ack_o")&7)==7,"missing applied lane acknowledgement"
        p.keep_ack=True;p.pause[3]=False
        await p.until(lambda:not p.v("pma_request_o"))
        await Timer(60000,unit="ps")
        assert not p.v("epoch_active_o") and not p.v("command_ready_o"),"held PMA ack bypassed low phase"
        p.keep_ack=False
        await p.until(lambda:p.v("epoch_active_o"))
        p.applied()
        await Timer(12000,unit="ps")
        assert p.done==[(e,1)],"success must occur once after actual applied barrier"
    finally:await p.close()

@cocotb.test()
async def modulo_wrap_stopped_clock_reset_and_fresh_ack(d):
    p=Commands(d)
    try:
        await p.start()
        for index in range(3*(MASK+1)+1):
            lane=index%4;p.pause[lane]=True
            e=await p.issue(index%3,index%16,(index*7)%16,wait=False)
            await Timer(50000,unit="ps")
            assert not p.v("epoch_active_o"),"stale ack admitted a reused epoch"
            assert p.v("epoch_o")==((index+1)&MASK)
            if index%3==1:
                d.epoch_abort_i.value=1
                await Timer(133,unit="ps");d.epoch_abort_i.value=0
                assert p.v("front_reset_o"),"short clean reset pulse was lost"
            p.pause[lane]=False
            if index%3==1:
                await p.until(lambda:p.v("command_ready_o"))
                assert not p.v("epoch_active_o") and p.v("epoch_fault_o"),"aborted transaction falsely succeeded"
            else:
                await p.until(lambda:p.v("epoch_active_o"));p.applied()
        assert {x[0]for x in p.transactions}==set(range(MASK+1))
    finally:await p.close()

@cocotb.test()
async def pma_wrong_epoch_encoding_and_lost_ack_are_not_success(d):
    p=Commands(d)
    try:
        await p.start()
        for field in ("pma_wrong_epoch","pma_wrong_encoding"):
            setattr(p,field,True);e=await p.issue(wait=False)
            await p.until(lambda:p.v("command_ready_o"))
            assert p.v("epoch_fault_o") and not p.v("epoch_active_o"),"wrong PMA witness accepted"
            await Timer(8000,unit="ps")
            assert (e,0)in p.done and (e,1)not in p.done
            setattr(p,field,False)
        p.pma_auto=False;await p.issue(wait=False)
        await Timer(150000,unit="ps")
        assert not p.v("epoch_active_o") and p.v("pma_request_o"),"missing PMA ack became success"
        # Recovery waits for the same held transaction; no invented timeout/retry.
        p.pma_auto=True;await p.until(lambda:p.v("epoch_active_o"));p.applied()
    finally:await p.close()

@cocotb.test()
async def common_pause_abort_startup_and_illegal_encoding(d):
    p=Commands(d)
    try:
        await p.start();d.fronts_ready_i.value=0
        await p.issue(wait=False);await p.until(lambda:not p.v("pma_request_o")and not p.v("lane_ack_o"))
        await Timer(80000,unit="ps")
        assert not p.v("epoch_active_o") and not p.v("command_ready_o"),"frontend startup bypassed"
        p.pause_common=True
        await Timer(10000,unit="ps")
        d.reset_i.value=1;await Timer(151,unit="ps");d.reset_i.value=0
        assert p.v("front_reset_o"),"stopped common domain lost reset pulse"
        p.pause_common=False
        await p.until(lambda:p.v("command_ready_o"))
        d.fronts_ready_i.value=1
        await p.issue(0,3,5)
        e=p.v("epoch_o");await p.issue(3,wait=False)
        await Timer(12000,unit="ps")
        assert p.v("epoch_o")==e and p.v("epoch_fault_o")and not p.v("pma_request_o")
        assert not p.v("epoch_active_o"),"illegal encoding retained active admission"
        await p.issue(1,12,10);p.applied()
    finally:await p.close()
