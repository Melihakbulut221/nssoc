# SPDX-License-Identifier: Apache-2.0
"""Actual frozen collectors and single shared front; independent raw-wire oracles."""
from collections import deque
import cocotb
from cocotb.triggers import Timer
from test_pcie_training_epoch_control import Commands,EW,MASK
from test_pcie_shared_serial_front import Front
from pcie_gen12_record_cdc_harness import stream_words,pack
import check_pcie_gen12_raw32_rx as table_rx

class Ingress(Commands):
    def __init__(self,d):
        super().__init__(d,fronts=False)
        self.mode=0;self.polarity=0;self.generation=0;self.generating=False
        self.ready=15;self.expected=[deque()for _ in range(4)]
        self.partial=[[]for _ in range(4)];self.pending=[deque()for _ in range(4)]
        self.oracles=[table_rx.SerialOracle(*table_rx.table())for _ in range(4)]
        self.raw=0;self.valid=0;self.reads=[0]*4;self.held=[None]*4
        self.gen3=Front(d);self.offsets=[0,1,17,31]
        self.allow_fault=False;self.lengths=[set()for _ in range(4)]
        self.field_positions=[set()for _ in range(4)]
    async def start(self):
        for n in ("lane_reset_i","lane_loss_i","raw_valid_i","raw_i","gen12_ready_i","gen3_ready_i"):
            getattr(self.d,n).value=0
        await super().start()
    def clear_generation(self,encoding,polarity):
        self.mode=encoding;self.polarity=polarity;self.generation+=1
        self.reads=[0]*4;self.held=[None]*4;self.partial=[[]for _ in range(4)]
        self.expected=[deque()for _ in range(4)];self.lengths=[set()for _ in range(4)]
        self.gen3.epoch=self.generation;self.gen3.expected=self.expected
        self.gen3.bits=[0]*4;self.gen3.count=list(self.offsets);self.gen3.index=[0]*4
        for k in range(4):
            self.oracles[k].clear();self.oracles[k].prev=(polarity>>k)&1
            self.pending[k]=deque(stream_words(self.offsets[k],(polarity>>k)&1,
                self.generation&1,count=160+self.generation,random_codes=True))
    async def issue(self,encoding=2,polarity=5,align=15,wait=True):
        e=await super().issue(encoding,polarity,align,wait=False)
        if encoding!=3:self.clear_generation(encoding,polarity);self.generating=True
        if wait and encoding!=3:
            await self.until(lambda:self.v("epoch_active_o"),label="actual fronts never reached applied epoch")
            self.applied()
        return e
    def observe(self,k,batch):
        data,ks,ce,de,co,count,*_=batch
        for slot in range(count):
            sym=((data>>(8*slot))&255,(ks>>slot)&1,(ce>>slot)&1,(de>>slot)&1,(co>>slot)&1)
            if self.partial[k]or(sym[0]==188 and sym[1]and not sym[2]and sym[4]):
                at=len(self.partial[k])
                for field in range(4):
                    if sym[field+1]:self.field_positions[field].add(at)
                self.partial[k].append(sym)
                if len(self.partial[k])==16:
                    self.expected[k].append(pack(self.partial[k]));self.partial[k]=[]
    async def lane(self,k):
        bit=1<<k
        await Timer(17+137*k,unit="ps")
        try:
            while True:
                self.clocks&=~bit;self.d.recovered_clk_i.value=self.clocks
                if self.pause[k]:
                    await Timer(100,unit="ps");continue
                live=self.generating and not self.v("front_reset_o")and bool(self.v("lane_running_o")&bit)
                valid=live and (self.mode==2 or bool(self.pending[k]))
                word=0
                if valid:
                    word=self.gen3.next_word(k)^((2**32-1)if(self.polarity>>k)&1 else 0)if self.mode==2 else self.pending[k].popleft()
                self.valid=(self.valid&~bit)|(bit if valid else 0)
                self.raw=(self.raw&~((2**32-1)<<(32*k)))|(word<<(32*k))
                self.d.raw_valid_i.value=self.valid;self.d.raw_i.value=self.raw
                await Timer(1900+31*k,unit="ps")
                if self.mode!=2 and not self.v("front_reset_o")and self.v("lane_running_o")&bit:
                    self.observe(k,self.oracles[k].step(1,1,0,(self.polarity>>k)&1,int(valid),word))
                self.clocks|=bit;self.d.recovered_clk_i.value=self.clocks
                await Timer(1999+29*k,unit="ps")
        except Exception as error:self.error=error;raise
    def item(self,k):
        if self.mode!=2:
            fields=("data","k","code_error","disparity_error","comma")
            widths=(128,16,16,16,16)
            return tuple(int(getattr(self.d,"gen12_"+f+"_o").value[w*k+w-1:w*k])for f,w in zip(fields,widths))
        return (int(self.d.gen3_block_o.value[194*k+193:194*k]),
                int(self.d.gen3_length_code_o.value[3*k+2:3*k]),
                int(self.d.gen3_skp_o.value[k]),int(self.d.gen3_eieos_o.value[k]),
                int(self.d.gen3_realign_o.value[k]))
    async def common(self):
        try:
            while True:
                d=self.d;d.common_clk_i.value=0
                if self.pause_common:
                    await Timer(100,unit="ps");continue
                self.pma()
                d.gen12_ready_i.value=self.ready;d.gen3_ready_i.value=self.ready
                await Timer(2000,unit="ps")
                active=self.v("epoch_active_o")
                v12=self.v("gen12_valid_o");v3=self.v("gen3_valid_o")
                if not active:
                    assert v12==v3==0,"record escaped common epoch barrier"
                    self.held=[None]*4
                else:
                    assert self.v("common_running_o")==15,"partial lane epoch exposed records"
                    assert not self.v("front_reset_o")
                    assert (v12==0 if self.mode==2 else v3==0),"inactive encoding leaked records"
                    assert not self.v("epoch_fault_o"),"faulted epoch exposed records"
                    self.applied()
                    valid=v3 if self.mode==2 else v12
                    ready=self.v("gen3_ready_i"if self.mode==2 else"gen12_ready_i")
                    for k in range(4):
                        bit=1<<k;item=self.item(k)if valid&bit else None
                        if self.held[k]is not None:assert item==self.held[k],"held complete typed record changed"
                        self.held[k]=item if valid&bit and not ready&bit else None
                        if valid&bit and ready&bit:
                            assert self.expected[k],"invented or duplicate typed record"
                            expected=self.expected[k].popleft()
                            assert item==expected,("typed raw-record mismatch",self.mode,self.generation,k,item,expected)
                            self.reads[k]+=1
                            if self.mode==2:self.lengths[k].add(item[1])
                if self.v("por_ni"):
                    if self.v("epoch_fault_o")and not self.allow_fault:raise AssertionError("unexpected ingress epoch fault")
                    if self.v("command_done_o"):self.done.append((self.v("epoch_o"),self.v("command_success_o")))
                d.common_clk_i.value=1;self.edge+=1
                await Timer(2000,unit="ps")
        except Exception as error:self.error=error;raise

@cocotb.test()
async def actual_gen12_full_records_all_offsets_polarities_and_errors(d):
    p=Ingress(d)
    try:
        await p.start()
        for phase in range(8):
            p.offsets=[phase*4+k for k in range(4)]
            await p.issue(phase%2,(phase*5)&15,15)
            await p.until(lambda:min(p.reads)>=30,label="gen12 complete record oracle did not retire")
        assert set(range(1,16))<=p.field_positions[1],"code-error positions not covered"
        assert set(range(1,16))<=p.field_positions[2],"RD-error positions not covered"
        assert {0,7}<=p.field_positions[3],"comma metadata coverage missing"
    finally:await p.close()

@cocotb.test()
async def actual_gen3_all_offsets_opaque_os_and_194_bit_metadata(d):
    p=Ingress(d)
    try:
        await p.start()
        for phase in range(8):
            p.offsets=[phase*4+k for k in range(4)]
            await p.issue(2,(phase*5)&15,15)
            await p.until(lambda:min(p.reads)>=35,label="gen3 complete record oracle did not retire")
            assert all(s==set(range(5))for s in p.lengths),"variable SKP lengths missing"
            assert p.v("gen3_locked_o")==15,"actual SDS acquisition did not lock all lanes"
    finally:await p.close()

@cocotb.test()
async def independent_ready_and_cross_encoding_epoch_flush_wrap(d):
    p=Ingress(d)
    try:
        await p.start()
        for index in range(3*(MASK+1)+1):
            await p.issue(index%3,(index*3)&15,15)
            await p.until(lambda:min(p.reads)>=8)
            for k in range(4):
                p.ready=15^(1<<k)
                await p.until(lambda:p.held[k]is not None)
                before=list(p.reads);await Timer(16000,unit="ps")
                assert p.reads[k]==before[k],"unready lane retired"
                p.ready=15
                await p.until(lambda:p.reads[k]>=before[k]+2)
            # Queue a real, undrained old-epoch prefix before reset/reuse.
            p.ready=0
            await p.until(lambda:any(x is not None for x in p.held))
            # The next command closes the epoch before disabling the old source.
            p.ready=15
        assert {x[0]for x in p.transactions}==set(range(MASK+1))
    finally:await p.close()

@cocotb.test()
async def asymmetric_reset_stopped_lane_overflow_and_no_stale_ack(d):
    p=Ingress(d)
    try:
        await p.start();p.pause[3]=True
        await p.issue(2,10,15,wait=False)
        await Timer(200000,unit="ps")
        assert p.v("gen12_valid_o")==p.v("gen3_valid_o")==0 and not p.v("epoch_active_o")
        p.pause[3]=False
        await p.until(lambda:p.v("epoch_active_o"));await p.until(lambda:min(p.reads)>=10)
        p.allow_fault=True;p.pause[1]=True;d.lane_reset_i.value=2
        await Timer(137,unit="ps");d.lane_reset_i.value=0
        await p.until(lambda:p.v("epoch_fault_o")and not p.v("epoch_active_o"))
        await p.until(lambda:p.v("command_ready_o"))
        await p.issue(1,3,15,wait=False)
        await Timer(100000,unit="ps")
        assert not p.v("epoch_active_o"),"reset/stopped lane stale acknowledgement escaped"
        p.pause[1]=False
        await p.until(lambda:p.v("epoch_active_o"));p.allow_fault=False
        await p.until(lambda:min(p.reads)>=10)
        p.allow_fault=True;p.ready=0
        await p.until(lambda:p.v("epoch_fault_o"),label="actual full FIFO did not abort epoch")
        assert not p.v("epoch_active_o")and p.v("gen12_valid_o")==p.v("gen3_valid_o")==0
        p.ready=15
        await p.issue(2,12,15);p.allow_fault=False
        await p.until(lambda:min(p.reads)>=20)
    finally:await p.close()
