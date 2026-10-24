#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0
"""Cloud-only TX transport proof against published tables and serial bit queue."""
import hashlib,json,os,random,subprocess
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
OUT=ROOT/'hw/soc/out/cloud-pcie-gen12-tx-raw32'
RTL=ROOT/'hw/soc/rtl/pcie/soc_pcie_gen12_tx_raw32.v'
FILES=['hw/soc/rtl/pcie/vendor/benz_8b10b_encode.v',
 'hw/soc/rtl/pcie/soc_pcie_gen12_8b10b_encode.v',
 'hw/soc/rtl/pcie/soc_pcie_gen12_tx_raw32.v']
MARKER='PASS_TX_RAW32_TABLE_QUEUE_STALL_FLUSH_RD_THROUGHPUT'
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def proof():
 m=json.loads((ROOT/'scripts/pcie-gen12-tx-raw32-methods.json').read_text())
 for p,h in m['protected'].items():assert sha(ROOT/p)==h,p
 r=json.loads((ROOT/'scripts/pcie-gen12-tx-raw32-prerequisite.json').read_text())
 assert r['state']=='BOUND_TO_COMPLETED_CODEC_NATIVE_PROOF'
 assert r['codec_RTL_source']=='86dbe41b5383c29238b6a61f87783f3409e6cf3b'and r['attempt']==1
 assert type(r['run'])is int and r['run']!=40099402878  # Original proof rejected at TB reset initialization.
 assert r['workflow']=='.github/workflows/pcie-gen12-codec-cloud.yml'and r['job']=='exhaustive-native-rtl'
 p=ROOT/r['receipt_path'];assert sha(p)==r['receipt_sha256'];native=json.loads(p.read_text())
 assert native['status']=='PASS_EXACT_CODEC_NATIVE_ARTIFACT_SOURCES_TABLE_AND_ALL_GATES'
 assert native['codec_RTL_accepted']and native['native_conclusion']=='success'
 assert native['native_run']==r['run']and native['native_source']==r['head']and native['native_attempt']==1
 assert native['original_result']['status']=='PASS_GEN12_SINGLE_LANE_CODEC_TABLE_EXHAUSTIVE_STATE_SYNTHESIS_AND9_FAULTS'
 assert native['artifact']['all_recorded_member_hashes_verified']and len(native['original_result']['negative_controls'])==9
 for p,h in r['sources'].items():assert sha(ROOT/p)==h==native['protected_sources'][p],p
 def api(tail):return json.loads(subprocess.check_output(['gh','api','repos/Melihakbulut221/nssoc/'+tail],text=True))
 run=api('actions/runs/'+str(r['run']))
 assert run['head_sha']==r['head']and run['run_attempt']==1 and run['path']==r['workflow']
 assert run['status']=='completed'and run['conclusion']=='success'
 jobs=api('actions/runs/'+str(r['run'])+'/jobs?filter=latest&per_page=100')['jobs']
 selected=[j for j in jobs if j['name']==r['job']]
 assert len(selected)==1 and selected[0]['conclusion']=='success'and selected[0]['status']=='completed'
 return m,dict(run=r['run'],head=r['head'],job=selected[0]['id'],receipt_sha256=r['receipt_sha256'])
def wirebits(code):return [int(b)for b in code]
def number(bits):return sum(b<<i for i,b in enumerate(bits))
def rd_after(bits,rd):
 for part in (bits[:6],bits[6:]):
  if part.count('1')>len(part)//2 or part in ('000111','0011'):rd=1
  elif part.count('1')<len(part)//2 or part in ('111000','1100'):rd=0
 return rd
def table():
 t=json.loads((ROOT/'sw/tests/data/pcie_gen12_ieee8023z_codes.json').read_text());enc={}
 assert len(t['rows'])==268
 for row in t['rows']:
  for rd,key in enumerate(('minus','plus')):
   code=row[key];assert len(code)==10 and set(code)<={'0','1'}
   enc[rd,row['k'],row['data']]=(wirebits(code),rd_after(code,rd))
 assert len(enc)==536
 return enc
class Oracle:
 """Published code strings are appended to a Python serial-bit list.
 Public handshakes, not RTL shift/mask expressions, consume exact32-bit slices."""
 def __init__(self,enc):
  self.enc=enc;self.q=[];self.rd=0;self.pairs=set();self.invalid=set()
  self.counts=set();self.fill=set();self.flush={k:set()for k in ('reset','disable','flush')}
  self.stalls=0;self.pops=0;self.pushes=0;self.rejected=0
  self.reject_with_pop=0;self.force_nonempty=0;self.force_stalled=0;self.underflows=0
 def step(self,r,e,f,valid,count,data,k,force,ready,demand):
  # Async reset has already emptied state when combinational pins are sampled.
  if not r:
   self.flush['reset'].add(len(self.q));self.q=[];self.rd=0
  active=bool(r and e and not f);out_valid=int(active and len(self.q)>=32)
  out=number(self.q[:32])if out_valid else 0;pop=bool(out_valid and ready)
  bad_count=count not in (1,2,3,4)
  bad_k=any((0,(k>>slot)&1,(data>>(8*slot))&255)not in self.enc for slot in range(min(count,4)))
  bad=bad_count or bad_k;capacity=72-len(self.q)+(32 if pop else 0)
  in_ready=int(active and (bad or capacity>=10*count))
  underflow=int(active and demand and ready and not out_valid)
  before=(in_ready,out,out_valid,underflow)
  old_q=list(self.q);old_rd=self.rd
  errors=(0,0,0)
  if not active:
   if r:self.flush['disable'if not e else'flush'].add(len(self.q))
   self.q=[];self.rd=0
  else:
   self.underflows+=underflow
   if valid and not in_ready:self.stalls+=1
   if force and valid and not in_ready and self.q:self.force_stalled+=1
   if pop:self.q=self.q[32:];self.pops+=1
   if valid and in_ready:
    self.counts.add(count)
    if bad:
     errors=(1,int(bad_count),int(not bad_count and bad_k));self.rejected+=1;self.reject_with_pop+=int(pop)
     if not bad_count:
      for slot in range(count):
       pair=(old_rd,(k>>slot)&1,(data>>(8*slot))&255)
       if pair not in self.enc:self.invalid.add(pair)
     assert self.rd==old_rd and self.q==(old_q[32:]if pop else old_q)
    else:
     self.force_nonempty+=int(force and bool(old_q));self.pushes+=1
     rd=0 if force else self.rd
     for slot in range(count):
      pair=(rd,(k>>slot)&1,(data>>(8*slot))&255);self.pairs.add(pair)
      code,rd=self.enc[pair];self.q.extend(code)
     self.rd=rd
  assert len(self.q)<=72 and set(self.q)<={0,1}
  self.fill.add(len(self.q))
  return (*before,*errors,self.rd,len(self.q))
def vectors():
 enc=table();o=Oracle(enc);rows=[];rng=random.Random(0x8018b10b)
 def add(r=1,e=1,f=0,v=0,c=1,d=0,k=0,force=0,ready=0,demand=0):
  inputs=(r,e,f,v,c,d,k,force,ready,demand)
  out=o.step(*inputs);rows.append((*inputs,*out));return out
 def reset():add(r=0)
 def symbol(data,k=0,force=0):return add(v=1,c=1,d=data,k=k,force=force)
 legal=sorted({(k,d)for _,k,d in enc})
 # Every published symbol under each actual incoming RD.
 for rd in (0,1):
  for k,d in legal:
   reset()
   if rd:symbol(188,1)
   assert o.rd==rd
   symbol(d,k)
 # Every invalid K under each actual incoming RD; neither accepted data nor RD.
 invalid=[d for d in range(256)if (0,1,d)not in enc]
 for rd in (0,1):
  for d in invalid:
   reset()
   if rd:symbol(188,1)
   assert o.rd==rd;before=o.rd;symbol(d,1);assert o.rd==before
 assert o.pairs==set(enc)and len(o.invalid)==488
 # All illegal counts, and mixed bad-K positions in every selected slot.
 for rd in (0,1):
  for c in (0,5,6,7):
   reset()
   if rd:symbol(188,1)
   add(v=1,c=c,d=0xdeadbeef,k=15,force=1,ready=1,demand=1)
 for c in range(1,5):
  for slot in range(c):
   reset();add(v=1,c=4,d=0x12345678);add(v=1,c=c,d=0,k=1<<slot,ready=1,demand=1)
 # Poison unused slots: they must add no bits and must not reject an otherwise legal batch.
 for c in range(1,4):
  reset()
  for _ in range(24):add(v=1,c=c,d=0,k=(15<<c)&15,ready=1)
  for _ in range(4):add(ready=1,demand=1)
 # Force-negative while prior bytes remain queued, including backpressure.
 reset();add(v=1,c=4,d=0xbcbcbcbc,k=15)
 for _ in range(9):add(v=1,c=4,d=0x11223344,force=1,ready=0)
 add(v=1,c=4,d=0x11223344,force=1,ready=1)
 add(v=1,c=4,d=0xbcbcbcbc,k=15,force=1,ready=1)
 for _ in range(16):add(v=1,c=4,d=rng.getrandbits(32),force=1,ready=1)
 # Accumulate every possible even occupancy up to72, then flush under every control.
 # Byte batches contribute10 bits and a word consumes32, so odd occupancies cannot occur.
 for kind in ('reset','disable','flush'):
  for target in range(0,73,2):
   reset()
   # Breadth-first search over the public queue-length contract, independent of RTL shifts.
   frontier=[(0,[])];seen={0};plan=None
   for length,path in frontier:
    if length==target:plan=path;break
    for c in range(0,5):
     for ready in (0,1):
      n=length-(32 if ready and length>=32 else 0)+10*c
      if n<=72 and n not in seen:seen.add(n);frontier.append((n,path+[(c,ready)]))
   assert plan is not None
   for c,ready in plan:add(v=int(c>0),c=max(c,1),d=0x12345678,ready=ready)
   assert len(o.q)==target
   if target==72:
    saved_rd=o.rd
    add(v=1,c=0,force=1,ready=0)
    add(v=1,c=4,d=0,k=1,force=1,ready=0)
    add(v=0,ready=0)
    assert len(o.q)==72 and o.rd==saved_rd
   add(**{'reset':dict(r=0),'disable':dict(e=0),'flush':dict(f=1)}[kind],v=1,c=4,d=0xffffffff,ready=1,demand=1,force=1)
   assert not o.q and o.rd==0
   add(ready=1,demand=1)
 for values in o.flush.values():assert values==set(range(0,73,2))
 # Long continuous supply: no bubbles after one-word prefill, every actual32 bits compared.
 reset();add(v=1,c=4,d=0x12345678)
 continuous_words=0;continuous_inputs=0;continuous_stalls=0
 for i in range(8192):
  d=k=0
  for slot in range(4):
   ck,cd=legal[(4*continuous_inputs+slot)%len(legal)];d|=cd<<(8*slot);k|=ck<<slot
  out=add(v=1,c=4,d=d,k=k,ready=1,demand=1)
  assert out[2]==1 and out[3]==0
  continuous_words+=out[2];continuous_inputs+=out[0];continuous_stalls+=1-out[0]
 assert continuous_words==8192 and continuous_inputs and continuous_stalls
 # Random stalls, gaps, poisoned unused payload, force/reset/disable/flush and invalid counts.
 pending=None
 for i in range(12000):
  if pending is None and rng.randrange(2):
   pending=dict(c=rng.randrange(8),d=rng.getrandbits(32),k=rng.randrange(16),force=rng.randrange(2))
  r=int(i%541!=0);e=int(i%251!=0);f=int(i%193==0)
  out=add(r=r,e=e,f=f,v=int(pending is not None),**(pending or {}),
   ready=int(rng.randrange(4)!=0),demand=rng.randrange(2))
  if not r or not e or f or (pending is not None and out[0]):pending=None
 for _ in range(4):add(ready=1,demand=1)
 assert o.stalls and o.reject_with_pop and o.force_nonempty and o.force_stalled and o.underflows
 assert o.counts==set(range(8))and max(o.fill)==72
 path=OUT/'vectors.txt'
 path.write_text(''.join(' '.join(format(value,'x')for value in row)+'\n'for row in rows))
 return dict(cycles=len(rows),published_encode_pairs=len(o.pairs),invalid_K_RD_pairs=len(o.invalid),
  accepted_counts=sorted(o.counts),occupancies=sorted(o.fill),flush_occupancies={k:sorted(v)for k,v in o.flush.items()},
  input_stalls=o.stalls,output_words=o.pops,accepted_valid_batches=o.pushes,rejected_batches=o.rejected,
  rejection_with_independent_output_pop=o.reject_with_pop,forced_RD_with_queued_symbols=o.force_nonempty,
  forced_RD_during_backpressure=o.force_stalled,truthful_underflows=o.underflows,
  continuous_output_words=continuous_words,continuous_accepted_batches=continuous_inputs,
  continuous_input_stalls=continuous_stalls,all_continuous_bits_checked=True),path
TB=r"""
module tb;
 reg clk=0;always #5 clk=~clk;
 reg rst=0,en=0,flush=0,bv=0;wire br;
 reg[2:0]count=1;reg[31:0]data=0;reg[3:0]k=0;reg force_rd=0;
 wire[31:0]raw;wire rv;reg rr=0,demand=0;wire uf,be,ce,ke,rd;wire[6:0]fill;
 soc_pcie_gen12_tx_raw32 dut(clk,rst,en,flush,bv,br,count,data,k,force_rd,
  raw,rv,rr,demand,uf,be,ce,ke,rd,fill);
 reg er,ee,ef,ev;reg[2:0]ec;reg[31:0]ed;reg[3:0]ek;reg eforce,eready,edemand;
 reg ebr;reg[31:0]eraw;reg erv,euf,ebe,ece,eke,erd;reg[6:0]efill;
 integer fd,n,row=0;
 initial begin
  rst=1;#1;rst=0;#1; // Explicit real asynchronous assertion before any check.
  fd=$fopen("vectors.txt","r");if(!fd)$fatal(1,"missing vectors");
  while(!$feof(fd))begin
   n=$fscanf(fd,"%h %h %h %h %h %h %h %h %h %h %h %h %h %h %h %h %h %h %h\n",
    er,ee,ef,ev,ec,ed,ek,eforce,eready,edemand,ebr,eraw,erv,euf,ebe,ece,eke,erd,efill);
   if(n==19)begin
    @(negedge clk);rst=er;en=ee;flush=ef;bv=ev;count=ec;data=ed;k=ek;force_rd=eforce;rr=eready;demand=edemand;
    #1;
    if({br,raw,rv,uf}!=={ebr,eraw,erv,euf})$fatal(1,"comb row%0d actual%h expected%h",row,{br,raw,rv,uf},{ebr,eraw,erv,euf});
    if(!rst && {fill,rd,be,ce,ke}!==0)$fatal(1,"async reset row%0d",row);
    @(posedge clk);#1;
    if({be,ce,ke,rd,fill}!=={ebe,ece,eke,erd,efill})$fatal(1,"state row%0d actual%h expected%h",row,{be,ce,ke,rd,fill},{ebe,ece,eke,erd,efill});
    if(fill>72 || (dut.fifo_q>>fill)!==0)$fatal(1,"unused stored bits or occupancy row%0d",row);
    row=row+1;
   end else if(n!=-1)$fatal(1,"malformed vector");
  end
  if(row<22000)$fatal(1,"truncated proof");
  $display("PASS_TX_RAW32_TABLE_QUEUE_STALL_FLUSH_RD_THROUGHPUT %0d",row);$finish;
 end
endmodule
"""
def command(args,label,must_pass=True):
 p=subprocess.run(list(map(str,args)),cwd=OUT,capture_output=True,text=True)
 (OUT/(label+'.log')).write_text(p.stdout+p.stderr)
 if must_pass:assert p.returncode==0,(label,p.stdout[-4000:],p.stderr[-4000:])
 return p
def simulate(paths,label,expected):
 exe=OUT/(label+'.vvp')
 command(['iverilog','-g2012','-s','tb','-o',exe,*paths,OUT/'tb.v'],label+'-compile')
 p=command(['vvp',exe],label,False)
 if expected:assert p.returncode==0 and MARKER in p.stdout,p.stdout+p.stderr
 else:assert p.returncode!=0 and 'FATAL'in p.stdout+p.stderr,(label,p.stdout,p.stderr)
 return dict(label=label,returncode=p.returncode,log_sha256=sha(OUT/(label+'.log')))
def main():
 assert os.environ.get('GITHUB_ACTIONS')=='true'
 OUT.mkdir(parents=True,exist_ok=False)
 result=dict(status='RUNNING',source=os.environ['GITHUB_SHA'],run=os.environ['GITHUB_RUN_ID'],
  low_rate_PMA_accepted=False,training_owner_implemented=False,serializer_connected=False,full_PHY_accepted=False)
 try:
  manifest,result['prerequisite']=proof();result['coverage'],path=vectors()
  result['vector_sha256']=sha(path);(OUT/'tb.v').write_text(TB)
  paths=[ROOT/p for p in FILES]
  result['icarus']=simulate(paths,'positive',True)
  command(['verilator','--binary','--timing','-Wno-fatal','--top-module','tb','--Mdir',OUT/'verilator','-o','tx_test',*paths,OUT/'tb.v'],'verilator-build')
  p=command([OUT/'verilator/tx_test'],'verilator');assert MARKER in p.stdout
  result['verilator']='PASS'
  net=OUT/'synthesis.json'
  command(['yosys','-p','read_verilog '+' '.join(map(str,paths))+'; synth -top soc_pcie_gen12_tx_raw32; check -assert; write_json '+str(net)],'synthesis')
  n=json.loads(net.read_text());cells=n['modules']['soc_pcie_gen12_tx_raw32']['cells'];assert len(cells)>0
  assert all(not v.get('attributes',{}).get('blackbox')for v in n['modules'].values())
  result['synthesis']=dict(status='PASS',cell_count=len(cells),cell_types=sorted({x['type']for x in cells.values()}),sha256=sha(net))
  faults={
   'break_RD_chain':('.rd_i(chain_rd[g])','.rd_i(chain_rd[0])'),
   'ignore_force_negative':("force_negative_rd_i ? 1'b0 : rd_o","rd_o"),
   'accept_invalid_K':('wire bad=bad_count || bad_k;','wire bad=bad_count;'),
   'accept_invalid_count':('wire bad_count=(count_i<1 || count_i>4);',"wire bad_count=1'b0;"),
   'accept_unready_batch':('if(push)begin','if(batch_valid_i && !bad)begin'),
   'ignore_output_backpressure':('wire pop=raw_valid_o && raw_ready_i;','wire pop=raw_valid_o;'),
   'overflow_capacity':("wire [6:0] free_bits=7'd72-after_pop;","wire [6:0] free_bits=7'd80-after_pop;"),
   'reverse_byte_slots':('.data_i(data_i[g*8+:8])','.data_i(data_i[(3-g)*8+:8])'),
   'hide_underflow':('assign underflow_o=active && stream_active_i && raw_ready_i && !raw_valid_o;', "assign underflow_o=1'b0;"),
   'fabricate_partial_word':("count_q>=7'd32","count_q!=0"),
   'ignore_flush_clear':('if(!enable_i || flush_i)begin','if(!enable_i)begin'),
   'ignore_disable_clear':('if(!enable_i || flush_i)begin','if(flush_i)begin'),
   'sticky_error_strobes':('end else begin\n   batch_error_o<=0;count_error_o<=0;k_error_o<=0;','end else begin'),
   'wrong_symbol_bit_count':("{4'b0,count_i}*7'd10","{4'b0,count_i}*7'd9"),
   'append_unused_slots':("(count_i>g) ? encoded[g*10+:10] : 10'b0",'encoded[g*10+:10]'),
   'wrong_pop_length':('(fifo_q>>32)','(fifo_q>>31)'),
   'reset_RD_positive':('fifo_q<=0;count_q<=0;rd_o<=0;',"fifo_q<=0;count_q<=0;rd_o<=1;"),
   'hide_rejection':('batch_error_o<=1;',"batch_error_o<=0;")}
  src=RTL.read_text();controls=[]
  for label,(before,after)in faults.items():
   expected_occurrences=2 if label=='reset_RD_positive'else 1
   assert src.count(before)==expected_occurrences,(label,before)
   mutant=OUT/(label+'.v');mutant.write_text(src.replace(before,after))
   controls.append(simulate([mutant if p==RTL else p for p in paths],label,False))
  result['negative_controls']=controls
  assert len(controls)==18 and proof()[0]==manifest
  result['status']='PASS_TX_RAW32_TABLE_QUEUE_RD_STALL_FLUSH_THROUGHPUT_SYNTHESIS_AND18_FAULTS'
 except BaseException as exc:result.update(status='FAIL_OR_ERROR',error=repr(exc));raise
 finally:
  result['outputs']={str(p.relative_to(OUT)):sha(p)for p in OUT.rglob('*')if p.is_file()and p.name!='result.json'}
  (OUT/'result.json').write_text(json.dumps(result,indent=2)+'\n')
  print(json.dumps({k:v for k,v in result.items()if k!='outputs'},indent=2))
if __name__=='__main__':main()
