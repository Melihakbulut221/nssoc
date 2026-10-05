# SPDX-FileCopyrightText: 2026 Hasan Melih Akbulut
# SPDX-License-Identifier: Apache-2.0
"""Real serial records to CRC-qualified packet bytes, only public-port oracles."""
from collections import deque
import zlib

import cocotb
from cocotb.triggers import Timer
from test_soc_pcie_gen3_recovered_x4_v3 import Link as RawLink, EIEOS, SDS, SEEDS, transform
from test_soc_pcie_gen3_continuous_rx_integrity_v4 import tlp, wire_tlp, dllp, wire_dllp

EDS=bytes.fromhex('1f809000')
EIOS=int.from_bytes(bytes([0x66]*16),'little')*4+1


class Link(RawLink):
    def __init__(self,d,case='clean'):
        super().__init__(d)
        self.case=case
        self.expected_packets=deque();self.expected_skps=deque();self.partial=bytearray()
        self.completed=self.good=self.bad=self.nullified=self.ends=self.stops=0
        self.seen_parity=self.seen_lfsr=0
        self.output_ready=1;self.stall=False
        self.records=[deque() for _ in range(4)]
        self.record_count=0;self.cycles=0;self.skp_count=0
        self.allow_fault=case in ('missing_eds','consecutive_skp','unequal_length','bad_crc_token','data_after_eds','mixed_end')

    async def start(self,auto_arm=True):
        d=self.d
        for n in ('por_ni','reset_i','recovered_clk_i','common_clk_i','arm_i','raw_valid_i','raw_i','align_control_i','force_realign_i','ready_i'):
            getattr(d,n).value=0
        await Timer(1,unit='ps')
        self.tasks=[cocotb.start_soon(self.writer(k)) for k in range(4)]
        self.tasks.append(cocotb.start_soon(self.reader()))
        await Timer(50000,unit='ps');d.align_control_i.value=15;d.por_ni.value=1
        if auto_arm:await self.arm()

    def begin_words(self):
        for l in range(4):
            self.bits[l]=0;self.count[l]=self.offsets[l];self.index[l]=0
            self.records[l].clear()
            for _ in range(l+1):self.records[l].append((EIEOS,130))
            self.records[l].append((SDS,130))
            self.lfsr[l],_=transform(SEEDS[l]);self.parity[l]=0
        for group in range(12):
            big=tlp(group*4+1,payload=128 if group%3==0 else 0)
            if group%3==0:
                # Bytes60..63 on the wire equal EDS inside a valid TLP. This
                # must not pause/end the Data Stream or reset LFSR state.
                b=bytearray(big);b[58:62]=EDS;b[-4:]=zlib.crc32(b[:-4]).to_bytes(4,'little');big=bytes(b)
            small=tlp(group*4+2)
            control=dllp(bytes([0x00,group,0x19,0x27]))
            raw=wire_tlp(big)+wire_dllp(control)+(bytes(12) if self.case=='end_drain' and group==11 else b'')+wire_tlp(small)
            self.expected_packets.extend([(big,False),(control,True),(small,False)])
            if self.case=='integrity' and group%3==1:
                bad=tlp(0x500+group);bad=bad[:-1]+bytes([bad[-1]^1])
                raw+=wire_tlp(bad)
                raw+=wire_tlp(tlp(0x600+group),nullify=True)
            raw+=bytes((60-len(raw))%64)
            raw+=bytes(4) if self.case=='missing_eds' and group==2 else EDS
            if self.case=='bad_crc_token' and group==2:raw=bytes([raw[0]^0x10])+raw[1:]
            for block in range(len(raw)//64):
                for l in range(4):
                    plain=int.from_bytes(raw[block*64+l:(block+1)*64:4],'little')
                    self.lfsr[l],encoded=transform(self.lfsr[l],plain)
                    self.parity[l]^=encoded.bit_count()&1
                    self.records[l].append((encoded*4+2,130))
            if group==11:
                for l in range(4):
                    end=EIEOS if self.case=='end_eieos' or (self.case=='mixed_end' and l==2) else EIOS
                    self.records[l].append((end,130))
            else:
                expected=[]
                for l in range(4):
                    code=(group+(1 if self.case=='unequal_length' and group==2 and l==1 else 0))%5
                    s=self.lfsr[l];parity=self.parity[l]
                    if self.case=='parity' and group==2 and l==1:parity^=1
                    trailer=[(s>>16&127)|(parity<<7),(s>>8)&255,s&255]
                    if self.case=='lfsr' and group==2 and l==3:trailer[2]^=1
                    value=int.from_bytes(bytes([0xaa]*(4+4*code)+[0xe1]+trailer),'little')*4+1
                    self.records[l].append((value,66+32*code));expected.append((value,code));self.parity[l]=0
                    if self.case=='consecutive_skp' and group==2:self.records[l].append((value,66+32*code))
                    if self.case=='data_after_eds' and group==2:self.records[l].pop()
                self.expected_skps.append(expected)
        self.enabled=[True]*4

    def next_word(self,lane):
        while self.count[lane]<32:
            value,nbits=self.records[lane].popleft() if self.records[lane] else (EIOS,130)
            self.bits[lane]|=value<<self.count[lane];self.count[lane]+=nbits
        word=self.bits[lane]&0xffffffff;self.bits[lane]>>=32;self.count[lane]-=32
        return word

    async def reader(self):
        d=self.d
        await Timer(997,unit='ps')
        try:
            while True:
                d.common_clk_i.value=0
                ready=self.output_ready and (not self.stall or self.cycles%31>=7)
                d.ready_i.value=int(ready)
                await Timer(2000,unit='ps')
                reset=not int(d.por_ni.value) or int(d.reset_i.value)
                fault=int(d.fault_o.value)
                if not reset:
                    if not self.allow_fault:assert not fault,'Unexpected raw-to-packet epoch fault'
                    self.starts+=int(d.stream_start_o.value);self.ends+=int(d.stream_end_o.value);self.stops+=int(d.stream_stop_o.value)
                    if self.case=='end_drain' and int(d.stream_stop_o.value):self.output_ready=0
                    self.good+=int(d.packet_good_o.value).bit_count();self.bad+=int(d.packet_crc_bad_o.value).bit_count();self.nullified+=int(d.packet_nullified_o.value).bit_count()
                    self.seen_parity|=int(d.lane_error_o.value);self.seen_lfsr|=int(d.lfsr_mismatch_o.value)
                    if not self.allow_fault:
                        if self.case!='parity':assert self.seen_parity==0,'Unexpected SKP parity diagnostic'
                        if self.case!='lfsr':assert self.seen_lfsr==0,'Unexpected SKP LFSR diagnostic'
                    if int(d.skp_valid_o.value):
                        assert self.expected_skps,'Invented SKP cohort'
                        expected=self.expected_skps.popleft()
                        actual=[(int(d.skp_block_o.value)>>(l*194)&((1<<194)-1),int(d.skp_length_code_o.value)>>(l*3)&7) for l in range(4)]
                        assert actual==expected,'Changed raw SKP cohort'
                        self.skp_count+=1
                    if int(d.valid_o.value) and not fault:
                        beat=tuple(int(getattr(d,n).value) for n in ('data_o','keep_o','sop_o','eop_o','dllp_o','sequence_o'))
                        if self.held is not None:assert beat==self.held,'Held packet beat changed'
                        self.held=None if ready else beat
                        data,keep,sop,eop,kind,seq=beat
                        assert keep and not ((sop|eop|kind)&~keep),'Invalid packet byte masks'
                        if ready:
                            for i in range(16):
                                if not (keep>>i)&1:continue
                                assert self.expected_packets,'Unexpected packet escaped quarantine'
                                expected,dllp_kind=self.expected_packets[0]
                                assert bool((sop>>i)&1)==(not self.partial),'SOP byte position'
                                assert bool((kind>>i)&1)==dllp_kind,'Wrong packet type'
                                assert (seq>>(12*(i//4))&4095)==(0 if dllp_kind else int.from_bytes(expected[:2],'big')),'Wrong packet sequence'
                                self.partial.append((data>>(i*8))&255)
                                assert len(self.partial)<=len(expected),'Packet too long'
                                assert bool((eop>>i)&1)==(len(self.partial)==len(expected)),'EOP byte position'
                                if len(self.partial)==len(expected):
                                    assert self.partial==expected,'Raw-to-packet byte mismatch'
                                    self.expected_packets.popleft();self.partial.clear();self.completed+=1
                    elif self.held is not None:
                        assert fault,'Held packet vanished without fault';self.held=None
                d.common_clk_i.value=1;self.cycles+=1
                await Timer(2000,unit='ps')
        except Exception as error:
            self.error=error
            raise


async def run(d,case,offsets=None):
    p=Link(d,case);p.stall=case=='stalls'
    if offsets is not None:p.offsets=offsets
    try:
        await p.start()
        if p.allow_fault:
            await p.until(lambda:int(d.fault_o.value))
            assert int(d.halted_o.value) or int(d.fault_o.value)
        else:
            if case=='end_drain':
                await p.until(lambda:p.stops==1)
                await Timer(2000000,unit='ps')
                assert int(d.lane_fault_o.value)!=0,'Post-end transport overflow was not exercised'
                assert int(d.fault_o.value)==0 and p.ends==0,'Completed stream drain was aborted or skipped'
                p.output_ready=1
            await p.until(lambda:p.ends==1)
            assert p.starts==p.stops==p.ends==1,'SKP restarted or ended stream'
            assert p.completed==p.good==36 and not p.expected_packets and not p.partial,'Incomplete packet retirement'
            assert p.skp_count==11 and not p.expected_skps,'Incomplete SKP cohorts'
            assert p.bad==(4 if case=='integrity' else 0)
            assert p.nullified==(4 if case=='integrity' else 0)
            assert p.seen_parity==(2 if case=='parity' else 0)
            assert p.seen_lfsr==(8 if case=='lfsr' else 0)
    finally:await p.close()


@cocotb.test()
async def actual_packet_context_skp_resume_and_payload_eds(d):await run(d,'clean')
@cocotb.test()
async def packet_output_stalls_and_independent_lane_skew(d):await run(d,'stalls')
@cocotb.test()
async def eieos_ends_only_after_packet_drain(d):await run(d,'end_eieos')
@cocotb.test()
async def crc_bad_and_nullified_packets_do_not_escape(d):await run(d,'integrity')
@cocotb.test()
async def parity_reports_without_packet_retrain(d):await run(d,'parity')
@cocotb.test()
async def lfsr_diagnostic_never_changes_packet_state(d):await run(d,'lfsr')
@cocotb.test()
async def skp_without_real_eds_faults(d):await run(d,'missing_eds')
@cocotb.test()
async def consecutive_skp_faults(d):await run(d,'consecutive_skp')
@cocotb.test()
async def unequal_skp_lengths_fault(d):await run(d,'unequal_length')
@cocotb.test()
async def bad_framing_token_aborts_raw_epoch(d):await run(d,'bad_crc_token')
@cocotb.test()
async def data_after_eds_without_os_faults(d):await run(d,'data_after_eds')
@cocotb.test()
async def mixed_eios_eieos_cohort_faults(d):await run(d,'mixed_end')


@cocotb.test()
async def all_32_raw_bit_phases_preserve_packet_bytes(d):
    for phase in range(8):
        await run(d,'clean',offsets=[phase*4+k for k in range(4)])


@cocotb.test()
async def coordinated_reset_recovers_after_framing_abort(d):
    p=Link(d,'missing_eds')
    try:
        await p.start();await p.until(lambda:int(d.fault_o.value))
        # Let the public framing-abort state sample before asserting reset.
        await Timer(20000,unit='ps')
        assert int(d.halted_o.value)==1,'Framing fault did not halt parser'
        p.enabled=[False]*4;d.reset_i.value=1;d.arm_i.value=0
        await Timer(50000,unit='ps')
        assert int(d.fault_o.value)==int(d.valid_o.value)==0
        assert int(d.halted_o.value)==int(d.active_o.value)==0,'Coordinated reset did not clear parser state'
        p.case='clean';p.allow_fault=False;p.expected_packets.clear();p.expected_skps.clear();p.partial.clear();p.held=None
        p.completed=p.good=p.bad=p.nullified=p.ends=p.stops=p.starts=p.skp_count=0
        p.seen_parity=p.seen_lfsr=0
        d.reset_i.value=0;await p.arm();await p.until(lambda:p.ends==1)
        assert p.completed==p.good==36 and p.starts==p.stops==p.ends==1
        assert not p.expected_packets and not p.partial
    finally:await p.close()


@cocotb.test()
async def normal_end_drain_survives_later_transport_fault(d):await run(d,'end_drain')
