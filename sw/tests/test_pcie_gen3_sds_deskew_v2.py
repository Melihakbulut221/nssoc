# SPDX-FileCopyrightText: 2026 Hasan Melih Akbulut
# SPDX-License-Identifier: Apache-2.0
"""Four actual record ports with externally timed packet-context decisions."""
import hashlib
import json
from pathlib import Path
import random
import subprocess

import pytest

ROOT=Path(__file__).resolve().parents[2]
RTL=ROOT/'hw/soc/rtl/pcie/soc_pcie_gen3_sds_deskew_v2.v'
EIEOS=int.from_bytes(bytes([0,255]*8),'little')*4+1
SDS=int.from_bytes(bytes([0xe1]+[0x55]*15),'little')*4+1
EIOS=int.from_bytes(bytes([0x66]*16),'little')*4+1


def record(b,n=2,skp=0,eieos=0,realign=0):
    return b+(n<<194)+(skp<<197)+(eieos<<198)+(realign<<199)


def skp(n,lane):
    return record(int.from_bytes(bytes([0xaa]*(4+4*n)+[0xe1,lane,0x19,0xab]),'little')*4+1,n,skp=1)


def fixture(case):
    rng=random.Random(502610)
    data=[[rng.getrandbits(128) for _ in range(4)] for _ in range(32)]
    data[3][1]=EIEOS>>2
    eds=[int(i%2==0 or i==31) for i in range(32)]
    queues=[]
    for l in range(4):
        q=[(0,record(EIEOS,eieos=1,realign=1)),(l*4,record(SDS))]
        for i,row in enumerate(data):
            q.append((0,record(row[l]*4+2)))
            if eds[i]:
                q.append((0,record(EIEOS,eieos=1) if case=='end_eieos' and i==31 else record(EIOS) if i==31 else skp((i//2)%5,l)))
        queues.append(q)
    fault=case not in ('end_eios','end_eieos','long_skp_stall','four_cycle_cadence')
    if case=='skp_without_eds':eds[0]=0
    elif case=='data_after_eds':
        for q in queues:q.pop(3)
    elif case=='consecutive_skp':
        for l,q in enumerate(queues):q.insert(4,(0,skp(2,l)))
    elif case=='unequal_skp_length':queues[1][3]=(0,skp(1,1))
    elif case=='mixed_skp_eios':queues[1][3]=(0,record(EIOS))
    elif case=='mixed_ending_types':queues[2][-1]=(0,record(EIEOS,eieos=1))
    elif case=='unknown_os_after_eds':queues[1][3]=(0,record((int.from_bytes(bytes([0x1e]*16),'little')<<2)|1))
    elif case=='missing_os_lane':queues[3]=queues[3][:3]
    elif case=='first_block_os':queues[2][2]=queues[2][3]
    elif case=='bad_skp_padding':queues[2][3]=(0,skp(0,2)|(1<<193))
    elif case=='missing_eieos':queues[2].pop(0)
    elif case=='missing_sds':queues[3]=queues[3][:1]
    elif case not in ('end_eios','end_eieos','long_skp_stall','four_cycle_cadence','unowned_decision','upstream_abort','second_arm'):
        raise AssertionError(case)
    return queues,data,eds,fault


BENCH=r'''
module tb;
reg clk=0;always #2 clk=~clk;
reg rst=0,arm=0,uf=0,decision=0,eds=0;
reg[3:0]valid=0,sk=0,ei=0,re=0;reg[775:0]b=0;reg[11:0]lc=0;
reg dr=0,sr=0;wire[3:0]ready;wire start,active,fault,dv,sv,stop,kind;
wire[511:0]data;wire[775:0]sb;wire[11:0]sc;
soc_pcie_gen3_sds_deskew_v2 #(.MAX_SKEW_CYCLES(64)) dut
(clk,rst,arm,uf,decision,eds,stop,kind,valid,ready,b,lc,sk,ei,re,start,active,fault,dv,dr,data,sv,sr,sb,sc);
reg[199:0]mem[0:4*STRIDE-1];reg[511:0]expected[0:31];reg decisions[0:31];integer times[0:4*STRIDE-1];
integer counts[0:3],pos[0:3];integer i,l,n,seen=0,starts=0,skps=0,left=0,pending=0,last_accept=-99,min_gap=999,skstall=0;
reg held=0,sheld=0;reg[511:0]old;reg[775:0]sold;reg[11:0]slold;
initial begin
$readmemh("INPUT_FILE",mem);$readmemh("DATA_FILE",expected);$readmemh("EDS_FILE",decisions);$readmemh("TIME_FILE",times);
COUNTS
for(l=0;l<4;l=l+1)pos[l]=0;
repeat(3)@(negedge clk);rst=1;arm=1;@(negedge clk);arm=0;
for(i=0;i<4000;i=i+1)begin
valid=0;b=0;lc=0;sk=0;ei=0;re=0;
for(l=0;l<4;l=l+1)begin
n=l*STRIDE+pos[l];if(pos[l]<counts[l] && i>=times[n])begin
valid[l]=1;{re[l],ei[l],sk[l],lc[l*3+:3],b[l*194+:194]}=mem[n];end end
if(left==1)begin decision=1;eds=pending;end else begin decision=0;eds=0;end
if(INJECTION==1 && i==3)decision=1;
uf=(INJECTION==2 && i==45);arm=(INJECTION==3 && i==45);
dr=(CASE_MODE==2 || i%11>=3);sr=CASE_MODE==1 ? (i>140) : i%9>=4;
#1;
if(fault)begin
if(!EXPECT_FAULT)$fatal(1,"UNEXPECTED_STRICT_COHORT_FAULT");
if(i>1000)$fatal(1,"FAULT_DETECTED_TOO_LATE");
repeat(4)begin @(negedge clk);decision=0;uf=0;arm=0;#1;
if(!fault || dv || sv || ready || stop || active)$fatal(1,"FAULT_NOT_STICKY");end
rst=0;@(negedge clk);#1;
if(fault || dv || sv || ready || stop || active)$fatal(1,"RESET_NOT_CLEAN");
$display("PASS EXPECTED_FAULT seen=%0d",seen);$finish;
end
if(held && active && (!dv || data!==old))$fatal(1,"HELD_DATA_CHANGED");
if(sheld && active && (!sv || sb!==sold || sc!==slold))$fatal(1,"HELD_SKP_CHANGED");
held=dv&&!dr;old=data;sheld=sv&&!sr;sold=sb;slold=sc;
if(start)begin starts=starts+1;if(starts!=1 || dv || ready)$fatal(1,"BAD_START");end
if(dv)begin
if(data!==expected[seen])$fatal(1,"DATA_ORDINAL_MISMATCH");
if(left>1)$fatal(1,"DATA_BEFORE_PRIOR_DECISION");
if(dr && ready!==15)$fatal(1,"NONATOMIC_DATA");
if(!dr && ready)$fatal(1,"LOST_DATA_BACKPRESSURE");end
if(sv)begin
if(valid!==15 || sk!==15 || sb!==b || sc!==lc)$fatal(1,"CORRUPT_SKP_COHORT");
if(ready!==(sr?4'b1111:4'b0000))$fatal(1,"NONATOMIC_SKP");
if(!sr)skstall=skstall+1;end
if(stop)begin
if(seen!=32 || starts!=1 || skps!=16 || held || sheld)$fatal(1,"PREMATURE_OR_INCOMPLETE_STOP");
if(kind!==END_EIEOS)$fatal(1,"WRONG_END_KIND");
if(EXPECT_FAULT)$fatal(1,"FAULT_NOT_DETECTED");
if(CASE_MODE==2 && min_gap!=4)$fatal(1,"LOST_FOUR_CYCLE_CADENCE");
if(CASE_MODE==1 && skstall<64)$fatal(1,"NO_LONG_SKP_STALL");
@(negedge clk);decision=0;#1;
if(active || fault || ready || dv || sv || stop)$fatal(1,"ENDED_STREAM_NOT_QUIET");
$display("PASS STRICT data=%0d skp=%0d min_gap=%0d stalls=%0d",seen,skps,min_gap,skstall);$finish;
end
@(posedge clk);
if(left>0)left=left-1;
if(dv && dr)begin
if(seen>0 && i-last_accept<min_gap)min_gap=i-last_accept;
last_accept=i;left=4;pending=decisions[seen];seen=seen+1;end
if(sv && sr)skps=skps+1;
for(l=0;l<4;l=l+1)if(valid[l] && ready[l])pos[l]=pos[l]+1;
@(negedge clk);
end
$fatal(1,"BOUNDED_STRICT_COHORT_TIMEOUT");
end
endmodule
'''


def run(tmp_path,case,source=RTL):
    q,data,eds,fault=fixture(case);stride=max(map(len,q));tmp_path.mkdir(parents=True,exist_ok=True)
    values=[x for row in q for x in row+[(0,0)]*(stride-len(row))]
    inputs=tmp_path/'input.hex';inputs.write_text(''.join(f'{v:050x}\n' for _,v in values))
    times=tmp_path/'times.hex';times.write_text(''.join(f'{t:08x}\n' for t,_ in values))
    expected=tmp_path/'data.hex';expected.write_text(''.join(f'{sum(v<<(128*l) for l,v in enumerate(row)):0128x}\n' for row in data))
    decisions=tmp_path/'eds.hex';decisions.write_text(''.join(f'{v:x}\n' for v in eds))
    replacements={'STRIDE':stride,'INPUT_FILE':inputs,'TIME_FILE':times,'DATA_FILE':expected,'EDS_FILE':decisions,
     'COUNTS':'\n'.join(f'counts[{l}]={len(row)};' for l,row in enumerate(q)), 'EXPECT_FAULT':int(fault),
     'INJECTION':{'unowned_decision':1,'upstream_abort':2,'second_arm':3}.get(case,0),
     'CASE_MODE':{'long_skp_stall':1,'four_cycle_cadence':2}.get(case,0),'END_EIEOS':"1'b1" if case=='end_eieos' else "1'b0"}
    text=BENCH
    for a in sorted(replacements,key=len,reverse=True):text=text.replace(a,str(replacements[a]))
    tb=tmp_path/'tb.v';tb.write_text(text);tools=ROOT/'hw/soc/tools/oss-cad-suite/bin'
    command=[str(tools/'iverilog'),'-g2012','-s','tb','-o',str(tmp_path/'sim.vvp'),str(source),str(tb)]
    p=subprocess.run(command,capture_output=True,text=True);(tmp_path/'compile.log').write_text(p.stdout+p.stderr)
    assert p.returncode==0,p.stderr
    p=subprocess.run([str(tools/'vvp'),str(tmp_path/'sim.vvp')],capture_output=True,text=True)
    log=p.stdout+p.stderr;(tmp_path/'run.log').write_text(log)
    (tmp_path/'command.json').write_text(json.dumps({'command':command,'returncode':p.returncode,'case':case,'rtl_sha256':hashlib.sha256(source.read_bytes()).hexdigest()},indent=2)+'\n')
    return p.returncode,log


CASES=['end_eios','end_eieos','long_skp_stall','four_cycle_cadence','skp_without_eds','data_after_eds','consecutive_skp','unequal_skp_length','mixed_skp_eios','mixed_ending_types','unknown_os_after_eds','missing_os_lane','first_block_os','bad_skp_padding','missing_eieos','missing_sds','unowned_decision','upstream_abort','second_arm']


@pytest.mark.parametrize('case',CASES)
def test_real_record_ports_and_parser_decisions(tmp_path,case):
    rc,log=run(tmp_path,case)
    assert rc==0 and 'PASS ' in log,log


MUTANTS={
 'pending_bypassed':('wire slot_open=!pending_q || decision;','wire slot_open=1\'b1;','four_cycle_cadence','UNEXPECTED_STRICT_COHORT_FAULT'),
 'eds_ignored':('wire expect_os=decision ? decision_eds_i : expect_os_q;','wire expect_os=1\'b0;','end_eios','UNEXPECTED_STRICT_COHORT_FAULT'),
 'lengths_unchecked':('(&is_skp) && lengths_equal','(&is_skp)','unequal_skp_length','FAULT_NOT_DETECTED'),
 'decision_ownership_unchecked':('(decision_valid_i && !pending_q)','1\'b0','unowned_decision','FAULT_NOT_DETECTED'),
 'data_lane_reverse':('data_o[lane*128 +: 128]','data_o[(3-lane)*128 +: 128]','end_eios','DATA_ORDINAL_MISMATCH'),
 'data_backpressure_ignored':('ready_o={4{(data_valid_o && data_ready_i)', 'ready_o={4{(data_valid_o)','end_eios','LOST_DATA_BACKPRESSURE'),
 'skp_backpressure_ignored':('(skp_valid_o && skp_ready_i) || stream_stop_o', '(skp_valid_o) || stream_stop_o','long_skp_stall','NONATOMIC_SKP'),
 'skp_truncated':('assign skp_block_o = block_i;','assign skp_block_o = {64\'d0,block_i[711:0]};','end_eios','CORRUPT_SKP_COHORT'),
 'eieos_kind_lost':('assign stop_eieos_o = stream_stop_o && (&is_eieos);','assign stop_eieos_o = 1\'b0;','end_eieos','WRONG_END_KIND'),
 'cohort_timeout_removed':('if(age_q==MAX_SKEW_CYCLES) fault_o<=1;','if(1\'b0) fault_o<=1;','missing_os_lane','BOUNDED_STRICT_COHORT_TIMEOUT'),
}


@pytest.mark.parametrize('name',MUTANTS)
def test_actual_policy_faults_are_observed(tmp_path,name):
    old,new,case,diagnostic=MUTANTS[name];source=RTL.read_text()
    assert source.count(old)==1
    mutant=tmp_path/'mutant.v';mutant.write_text(source.replace(old,new))
    rc,log=run(tmp_path,case,mutant)
    assert rc!=0 and diagnostic in log,log
