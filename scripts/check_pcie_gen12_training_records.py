#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0
"""Hosted-only composed 16-symbol record proof; no LTSSM acceptance inferred."""
import hashlib,json,os,random,subprocess
from pathlib import Path
import check_pcie_gen12_raw32_rx as rxbase
import check_pcie_gen12_tx_raw32 as txbase
ROOT=Path(__file__).resolve().parents[1]
OUT=ROOT/'hw/soc/out/cloud-pcie-gen12-training-records'
RTL=ROOT/'hw/soc/rtl/pcie/soc_pcie_gen12_training_records.v'
FILES=list(dict.fromkeys(rxbase.FILES+txbase.FILES))+[str(RTL.relative_to(ROOT))]
MARKER='PASS_COMPOSED_CANDIDATE16_RECORD_TRANSPORT'
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def prerequisites():
 m=json.loads((ROOT/'scripts/pcie-gen12-training-records-methods.json').read_text())
 for p,h in m['protected'].items():assert sha(ROOT/p)==h,p
 r=json.loads((ROOT/'scripts/pcie-gen12-training-records-prerequisites.json').read_text())
 assert r['state']=='BOUND_RX_TX_NATIVE_AND_REVIEWED',r['state']
 assert r['root_review']['status']=='REVIEWED_EXACT_SOURCE'
 assert len(r['root_review']['source'])==40 and len(r['root_review']['receipt_sha256'])==64
 review=ROOT/r['root_review']['receipt_path']
 assert sha(review)==r['root_review']['receipt_sha256']
 review=json.loads(review.read_text())
 assert review['status']=='REVIEWED_EXACT_SOURCE'
 reviewed=set(m['protected'])-{'scripts/pcie-gen12-training-records-prerequisites.json'}
 assert set(review['source_sha256'])==reviewed
 for p,h in review['source_sha256'].items():assert sha(ROOT/p)==h
 assert {x['role']for x in r['runs']}=={'rx','tx'} and len(r['runs'])==2
 live=[]
 for x in r['runs']:
  assert sha(ROOT/x['result_path'])==x['result_sha256']
  d=json.loads((ROOT/x['result_path']).read_text())
  assert d['source']==x['source'] and int(d['run'])==x['run'] and d['status']==x['result_status']
  assert d['icarus']['returncode']==0 and d['verilator']=='PASS' and d['synthesis']['status']=='PASS'
  assert len(d['negative_controls'])==x['fault_count']
  assert all(c['returncode']!=0 for c in d['negative_controls'])
  assert d['full_PHY_accepted']is False and d['low_rate_PMA_accepted']is False
  if x['role']=='rx':
   assert d['coverage']['actual_code_RD_pairs']==2048 and d['ltssm_accepted']is False
  else:
   assert d['coverage']['published_encode_pairs']==536 and d['coverage']['invalid_K_RD_pairs']==488
   assert d['coverage']['continuous_output_words']==8192 and d['training_owner_implemented']is False
  def api(t):return json.loads(subprocess.check_output(['gh','api','repos/Melihakbulut221/nssoc/'+t],text=True))
  run=api('actions/runs/'+str(x['run']))
  assert run['head_sha']==x['source'] and run['run_attempt']==1 and run['path']==x['workflow']
  assert run['status']=='completed' and run['conclusion']=='success'
  js=api('actions/runs/'+str(x['run'])+'/jobs?filter=latest&per_page=100')['jobs']
  found=[j for j in js if j['name']==x['job_name']]
  assert len(found)==1 and found[0]['conclusion']=='success' and found[0]['status']=='completed'
  for p,h in x['source_sha256'].items():assert sha(ROOT/p)==h
  live.append(dict(role=x['role'],run=x['run'],source=x['source'],job=found[0]['id'],result_sha256=x['result_sha256']))
 return m,live
def packed(symbols):
 return sum(d<<(8*i) | k<<(128+i) | ce<<(144+i) | de<<(160+i) | co<<(176+i)
            for i,(d,k,ce,de,co) in enumerate(symbols))
class Records:
 """FIFO lists and complete symbol tuples, independent of DUT shifts/pointers."""
 def __init__(self):
  legal,allowed=rxbase.table();self.rx=rxbase.SerialOracle(legal,allowed)
  self.tx=txbase.Oracle(txbase.table());self.batch=(0,)*9;self.prev=0
  self.partial=[];self.queue=[];self.overflow=0;self.pending=None;self.group=0
  self.rx_completed=0;self.rx_delivered=0;self.overflows=0;self.simultaneous_full_pop_push=0
  self.complete_slots=set();self.starts=set();self.internal_com=0;self.trailing_start=0
  self.rx_ce_positions=set();self.rx_de_positions=set();self.rx_k_positions=set()
  self.partial_flush={k:set()for k in ('reset','disable','force','polarity')}
  self.queued_flush={k:set()for k in ('reset','disable','force','polarity')}
  self.tx_accepted=0;self.tx_rejected=0;self.tx_queued=0;self.tx_stalls=0
  self.bad_k_positions=set();self.tx_flush_groups={k:set()for k in ('reset','disable','flush')}
  self.tx_force_stalls=0;self.tx_force_changes=0;self.loopback_words=0
 def rx_step(self,r,e,f,p,v,w,ready):
  flush='reset'if not r else'disable'if not e else'force'if f else'polarity'if p!=self.prev else None
  flush_partial=len(self.partial);flush_queue=len(self.queue)
  if not r:self.queue=[];self.partial=[];self.overflow=0
  active=bool(r and not flush);pre=(int(active and bool(self.queue)),packed(self.queue[0])if active and self.queue else 0,self.overflow)
  old_fill=len(self.queue);pop=bool(pre[0]and ready)
  if flush:
   self.partial_flush[flush].add(flush_partial);self.queued_flush[flush].add(flush_queue)
   self.partial=[];self.queue=[];self.overflow=0;self.batch=(0,)*9
  else:
   if pop:self.queue.pop(0);self.rx_delivered+=1
   if not self.overflow:
    data,k,ce,de,co,n,_,_,_=self.batch;completed=False
    for slot in range(n):
     item=((data>>(8*slot))&255,(k>>slot)&1,(ce>>slot)&1,(de>>slot)&1,(co>>slot)&1)
     if not self.partial:
      if not(item[0]==188 and item[1]and not item[2]and item[4]):continue
      self.starts.add(slot);self.trailing_start+=int(completed)
     elif item[4]:self.internal_com+=1
     self.partial.append(item)
     if len(self.partial)==16:
      frame=self.partial;self.partial=[];completed=True;self.complete_slots.add(slot)
      self.rx_completed+=1
      for i,(_,kk,cc,dd,_)in enumerate(frame):
       if kk:self.rx_k_positions.add(i)
       if cc:self.rx_ce_positions.add(i)
       if dd:self.rx_de_positions.add(i)
      if len(self.queue)==2:self.overflow=1;self.overflows+=1;break
      self.queue.append(frame)
      self.simultaneous_full_pop_push+=int(old_fill==2 and pop)
  self.prev=p if r else 0
  self.batch=self.rx.step(r,e,f,p,v,w)
  after=(int(bool(self.queue)),packed(self.queue[0])if self.queue else 0,
         self.overflow,self.batch[6],self.batch[8],len(self.queue),len(self.partial))
  return pre,after
 def tx_step(self,r,e,f,v,data,k,force,ready,demand):
  old=self.pending;old_group=self.group
  active=bool(r and e and not f);record_ready=int(active and old is None)
  if old is None:chunk=flags=initial=0
  else:
   word,mask,initial=old;chunk=(word>>(32*old_group))&0xffffffff;flags=(mask>>(4*old_group))&15
  prior_rd=self.tx.rd
  out=self.tx.step(r,e,f,int(old is not None),4,chunk,flags,int(initial and old_group==0),ready,demand)
  error=queued=0
  if not active:
   kind='reset'if not r else'disable'if not e else'flush'
   if old is not None:self.tx_flush_groups[kind].add(old_group)
   self.pending=None;self.group=0
  else:
   if old is not None:
    self.tx_stalls+=int(not out[0]);self.tx_force_stalls+=int(initial and old_group==0 and not out[0])
    if out[0]:
     self.tx_force_changes+=int(initial and old_group==0 and prior_rd==1)
     assert not any(out[4:7])
     if old_group==3:self.pending=None;self.group=0;queued=1;self.tx_queued+=1
     else:self.group+=1
   if v and record_ready:
    bad=[i for i in range(16)if (0,(k>>i)&1,(data>>(8*i))&255)not in self.tx.enc]
    if bad:error=1;self.tx_rejected+=1;self.bad_k_positions.update(bad)
    else:self.pending=(data,k,force);self.group=0;self.tx_accepted+=1
  pre=(record_ready,out[1],out[2],out[3])
  after=(error,queued,out[7],out[8],int(self.pending is not None),self.group,int(any(out[4:7])))
  return pre,after
 def step(self,rrst,ren,rflush,rpol,rvalid,rraw,rready,trst,ten,tflush,tvalid,tdata,tk,tforce,tready,tdemand,loopback):
  tp,ta=self.tx_step(trst,ten,tflush,tvalid,tdata,tk,tforce,tready,tdemand)
  if loopback:rvalid=int(tp[2]and tready);rraw=tp[1];self.loopback_words+=rvalid
  rp,ra=self.rx_step(rrst,ren,rflush,rpol,rvalid,rraw,rready)
  return (*rp,*tp,*ra,*ta)
INPUTS=[('rrst',1),('ren',1),('rflush',1),('rpol',1),('rvalid',1),('rraw',32),('rready',1),
 ('trst',1),('ten',1),('tflush',1),('tvalid',1),('tdata',128),('tk',16),('tforce',1),('tready',1),('tdemand',1),('loopback',1)]
PRE=[('rpvalid',1),('rppacket',192),('rpoverflow',1),('tpready',1),('tpraw',32),('tpvalid',1),('tpunderflow',1)]
POST=[('ravalid',1),('rapacket',192),('raoverflow',1),('raboundary',1),('rard',1),('rafill',2),('rapartial',5),
 ('taerror',1),('taqueued',1),('tard',1),('tafill',7),('tapending',1),('tagroup',2),('tatransport',1)]
def vectors():
 o=Records();rows=[];rng=random.Random(0x16c0de)
 default=dict(rrst=1,ren=1,rflush=0,rpol=0,rvalid=0,rraw=0,rready=1,trst=1,ten=1,tflush=0,tvalid=0,tdata=0,tk=0,tforce=0,tready=1,tdemand=0,loopback=0)
 def add(**kw):
  args=default|kw;values=tuple(args[n]for n,_ in INPUTS);out=o.step(*values);rows.append((*values,*out));return out
 def reset_rx(p=0):add(rrst=0);add(rpol=p)
 def reset_tx():add(trst=0)
 def code(byte,k,rd):bits,n=o.tx.enc[rd,k,byte];return txbase.number(bits),n
 def neutral(rd):
  return next(txbase.number(bits)for (incoming,k,d),(bits,n)in o.tx.enc.items()if incoming==rd and k==0 and n==rd)
 def feed(codes,offset=0,p=0,gaps=False,ready=1,finish=True):
  bitstream=[0]*offset+[b for c in codes for b in rxbase.bits(c,10)]
  bitstream += [0]*((-len(bitstream))%32)
  for at in range(0,len(bitstream),32):
   if gaps and rng.randrange(5)==0:add(rpol=p,rready=ready,rraw=rng.getrandbits(32))
   add(rpol=p,rready=ready,rvalid=1,rraw=txbase.number(bitstream[at:at+32])^(0xffffffff if p else 0))
  if finish:
   for _ in range(3):add(rpol=p,rready=ready)
 def frame(rd,changed=None):
  codes=[rxbase.COM[rd^1]]+[neutral(rd)]*15
  if changed:
   pos,c=changed;codes[pos]=c
  return codes
 # Complete candidates from every raw offset and explicit polarity, including
 # standard-looking and arbitrary EQ-like symbol6 contents, without classification.
 for offset in range(32):
  for p in (0,1):
   reset_rx(p);feed(frame(0)+frame(1,(6,code(0xf4,0,1)[0]))+frame(0),offset,p,True)
 # Every actual incoming raw10/RD pair appears inside a preserved record.
 for rd in (0,1):
  for raw in range(1024):
   reset_rx();pos=1+(raw%15);feed(frame(rd,(pos,raw)),raw%32,0,raw%7==0)
 assert o.rx.pairs=={(rd,c)for rd in (0,1)for c in range(1024)}
 # Inner COM, arbitrary K and every error position. A wrong-RD start COM is
 # preceded by an already collected record, so it is not silently reseeded.
 for pos in range(1,16):
  for raw in (rxbase.COM[0],rxbase.COM[1],0,1023):
   reset_rx();feed(frame(0,(pos,raw))+frame(1,(pos,raw)),pos%10,0,True)
 reset_rx();feed(frame(0)+frame(0)+frame(0))  # First COM leaves RD+, following forced sign is retained as an error.
 # Noise outside records must be ignored, including legal D28.5 (not K28.5).
 reset_rx();noise=code(188,0,0)[0];feed(frame(0)+[noise]*7+frame(1))
 # Two queued frames: popping at the same edge as the third completion must
 # make room; blocking that edge must instead halt without discarding old frames.
 for pop_final in (0,1):
  reset_rx();codes=frame(0)+frame(0)+frame(0)+frame(1)
  bits=[b for c in codes for b in rxbase.bits(c,10)]
  for at in range(0,len(bits),32):
   last=o.batch;will_complete=len(o.partial)+last[5]>=16
   allow=int(pop_final and len(o.queue)==2 and will_complete)
   add(rvalid=1,rraw=txbase.number(bits[at:at+32]),rready=allow)
  for _ in range(3):
   will_complete=len(o.partial)+o.batch[5]>=16
   add(rready=int(pop_final and len(o.queue)==2 and will_complete))
  if not pop_final:
   assert o.overflow and len(o.queue)==2
   for _ in range(8):add()
   assert not o.queue and o.overflow
   count=o.rx_completed;feed(frame(0)+frame(1));assert o.rx_completed==count
 # Flush every partial count including a pending complete-RX batch; search
 # automatically for a bit offset allowing each count in the public stream.
 for kind in ('reset','disable','force','polarity'):
  for target in range(16):
   reached=False
   for offset in range(32):
    reset_rx();bits=[0]*offset+[b for c in frame(0)+frame(1)for b in rxbase.bits(c,10)]
    bits += [0]*((-len(bits))%32)
    for at in range(0,len(bits),32):
     if len(o.partial)==target and (target or at>0):reached=True;break
     add(rvalid=1,rraw=txbase.number(bits[at:at+32]),rready=0)
    if reached:break
   assert reached,(kind,target)
   controls={'reset':{'rrst':0},'disable':{'ren':0},'force':{'rflush':1},'polarity':{'rpol':1}}[kind]
   add(rvalid=1,rraw=0xffffffff,rready=0,**controls)
   assert not o.partial and not o.queue and not o.overflow
   add(rpol=int(kind=='polarity'))
  for fill in (1,2):
   reset_rx();feed(frame(0)*fill,ready=0);assert len(o.queue)==fill
   add(rready=0,**{'reset':{'rrst':0},'disable':{'ren':0},'force':{'rflush':1},'polarity':{'rpol':1}}[kind])
   assert not o.queue
 # TX holds one whole request until acceptance; rejected late-K records never
 # submit their preceding otherwise valid chunks to the raw32 FIFO.
 reset_rx()
 def submit(data,k=0,force=0,stalls=False,loop=False):
  accepted=False
  for retry in range(64):
   ready=int(not stalls or retry%5==4)
   out=add(tvalid=1,tdata=data,tk=k,tforce=force,tready=ready,loopback=int(loop))
   if out[3]:accepted=True;break
  assert accepted
 def drain(loop=False):
  for _ in range(24):
   if o.pending is None and not o.tx.q:break
   add(tready=1,loopback=int(loop))
  assert o.pending is None and not o.tx.q
  for _ in range(2):add(tready=1,loopback=int(loop))
 for pos in range(16):
  for byte in range(256):
   for k in (0,1):
    reset_tx();data=(0x11*sum(1<<(8*i)for i in range(16)))&~(255<<(8*pos));data|=byte<<(8*pos)
    submit(data,k<<pos,force=byte%2);drain()
 # Real repeated RD continuity and forced-negative while earlier raw words
 # remain queued. This is caller-owned, not an automatic per-record reset.
 reset_tx()
 for i in range(48):
  data=sum((188 if j%4==0 else rng.randrange(256))<<(8*j)for j in range(16));mask=sum(1<<j for j in range(0,16,4))
  submit(data,mask,force=i%3==0,stalls=True)
 drain()
 # Flush every pending group for all three TX controls and check independent
 # RX state remains unaffected when only the TX domain is reset/disabled.
 for kind in ('reset','disable','flush'):
  for target in range(4):
   reset_tx();submit(0xbcbcbcbcbcbcbcbcbcbcbcbcbcbcbcbc,65535,force=1)
   for _ in range(12):
    if o.pending is not None and o.group==target:break
    add()
   assert o.pending is not None and o.group==target
   add(tvalid=1,tdata=0xdead,tk=0,tforce=1,**{'reset':{'trst':0},'disable':{'ten':0},'flush':{'tflush':1}}[kind])
   assert o.pending is None and not o.tx.q and o.tx.rd==0
 # Actual composed DUT wiring: raw32 TX transfers feed the real RX ports.
 # Independent expected serial bits still come from the printed table oracle.
 reset_rx();reset_tx();loop_records=256;loop_before=o.rx_completed
 for i in range(loop_records):
  payload=[188]+[rng.randrange(256)for _ in range(15)]
  payload[6]=0x80|(i&127)  # Preserve EQ-like contents without a training verdict.
  submit(sum(b<<(8*j)for j,b in enumerate(payload)),1,loop=True,stalls=i%7==0)
 drain(True)
 assert o.loopback_words==loop_records*5
 assert o.rx_completed-loop_before==loop_records and not o.overflow
 # Random held TX requests and independent RX gaps/errors/reset, not DUT-feedback oracle.
 pending=None
 for i in range(6000):
  if pending is None and rng.randrange(3)==0:
   pending=dict(tdata=rng.getrandbits(128),tk=rng.getrandbits(16),tforce=rng.randrange(2))
  controls=dict(rrst=int(i%307!=0),ren=int(i%197!=0),rflush=int(i%151==0),rpol=(i//541)%2,
   rvalid=int(rng.randrange(4)!=0),rraw=rng.getrandbits(32),rready=int(rng.randrange(3)!=0),
   trst=int(i%331!=0),ten=int(i%211!=0),tflush=int(i%179==0),tready=int(rng.randrange(3)!=0))
  out=add(**controls,tvalid=int(pending is not None),**(pending or {}))
  if not controls['trst']or not controls['ten']or controls['tflush']or out[3]:pending=None
 assert o.complete_slots==set(range(4))and o.starts==set(range(4))and o.trailing_start
 assert o.internal_com and o.simultaneous_full_pop_push and o.overflows
 assert o.rx_ce_positions.issuperset(range(1,16))and o.rx_de_positions.issuperset(range(1,16))
 assert o.rx_k_positions==set(range(16))and o.bad_k_positions==set(range(16))
 assert all(v==set(range(16))for v in o.partial_flush.values())
 assert all(v.issuperset({0,1,2})for v in o.queued_flush.values())
 assert all(v==set(range(4))for v in o.tx_flush_groups.values())
 assert o.tx_stalls and o.tx_force_stalls and o.tx_force_changes
 path=OUT/'vectors.txt';path.write_text(''.join(' '.join(format(v,'x')for v in row)+'\n'for row in rows))
 coverage=dict(cycles=len(rows),raw_offsets=list(range(32)),polarities=[0,1],actual_raw_code_RD_pairs=len(o.rx.pairs),
  completed_records=o.rx_completed,delivered_records=o.rx_delivered,completion_slots=sorted(o.complete_slots),start_slots=sorted(o.starts),
  internal_COM_symbols_preserved=o.internal_com,trailing_same_batch_starts=o.trailing_start,
  code_error_positions=sorted(o.rx_ce_positions),disparity_error_positions=sorted(o.rx_de_positions),K_positions=sorted(o.rx_k_positions),
  full_fifo_pop_and_completion=o.simultaneous_full_pop_push,overflow_halts=o.overflows,
  partial_flush={k:sorted(v)for k,v in o.partial_flush.items()},queued_flush={k:sorted(v)for k,v in o.queued_flush.items()},
  tx_accepted=o.tx_accepted,tx_rejected=o.tx_rejected,tx_queued=o.tx_queued,invalid_K_positions=sorted(o.bad_k_positions),
  tx_backpressure_cycles=o.tx_stalls,forced_first_batch_stalls=o.tx_force_stalls,forced_first_batch_RD_changes=o.tx_force_changes,
  tx_flush_groups={k:sorted(v)for k,v in o.tx_flush_groups.items()},actual_composed_loopback_words=o.loopback_words,
  actual_composed_loopback_records=loop_records,protocol_TS_acceptance=False)
 return path,coverage

def testbench():
 def decl(kind,name,width):return kind+(' 'if width==1 else'['+str(width-1)+':0] ')+name+';'
 all_fields=INPUTS+PRE+POST
 lines=['module tb;','reg clk=0;always #5 clk=~clk;']
 lines += [decl('reg','i_'+n,w)for n,w in INPUTS]
 lines += [decl('reg','e_'+n,w)for n,w in all_fields]
 lines += [
 'wire rv,overflow,boundary,rrd,tr,te,tq,tv,tu,trd,terr;',
 'wire[127:0]rd;wire[15:0]rk,rce,rde,rm;wire[31:0]tw;',
 'wire[191:0]packet={rm,rde,rce,rk,rd};',
 'wire incoming_valid=i_loopback ? (tv && i_tready) : i_rvalid;',
 'wire[31:0]incoming_word=i_loopback ? tw : i_rraw;',
 'soc_pcie_gen12_training_records dut(',
 '.rx_clk_i(clk),.rx_rst_ni(i_rrst),.rx_enable_i(i_ren),.rx_force_realign_i(i_rflush),.rx_polarity_i(i_rpol),',
 '.rx_raw_valid_i(incoming_valid),.rx_raw_i(incoming_word),.rx_record_valid_o(rv),.rx_record_ready_i(i_rready),',
 '.rx_record_data_o(rd),.rx_record_k_o(rk),.rx_record_code_error_o(rce),.rx_record_disparity_error_o(rde),.rx_record_comma_o(rm),',
 '.rx_overflow_o(overflow),.rx_boundary_valid_o(boundary),.rx_rd_o(rrd),',
 '.tx_clk_i(clk),.tx_rst_ni(i_trst),.tx_enable_i(i_ten),.tx_flush_i(i_tflush),',
 '.tx_record_valid_i(i_tvalid),.tx_record_ready_o(tr),.tx_record_data_i(i_tdata),.tx_record_k_i(i_tk),',
 '.tx_record_force_negative_rd_i(i_tforce),.tx_record_error_o(te),.tx_record_queued_o(tq),',
 '.tx_raw_o(tw),.tx_raw_valid_o(tv),.tx_raw_ready_i(i_tready),.tx_stream_active_i(i_tdemand),',
 '.tx_underflow_o(tu),.tx_rd_o(trd),.tx_transport_error_o(terr));',
 'integer fd,n,row=0;',
 'initial begin']
 lines += ['i_'+n+'=0;'for n,_ in INPUTS]
 lines += ['i_rrst=1;i_trst=1;#1;i_rrst=0;i_trst=0;#1;',
  'fd=$fopen("vectors.txt","r");if(!fd)$fatal(1,"missing vectors");',
  'while(!$feof(fd))begin',
  'n=$fscanf(fd,"'+' '.join('%h'for _ in all_fields)+'\\n",'+','.join('e_'+n for n,_ in all_fields)+');',
  'if(n=='+str(len(all_fields))+')begin','@(negedge clk);']
 lines += ['i_'+n+'=e_'+n+';'for n,_ in INPUTS]
 lines += ['#1;',
  'if({rv,packet,overflow,tr,tw,tv,tu}!=={'+','.join('e_'+n for n,_ in PRE)+'})$fatal(1,"comb row%0d",row);',
  'if(!i_rrst && {dut.rx_fill,dut.rx_partial_count,overflow}!==0)$fatal(1,"RX async reset row%0d",row);',
  'if(!i_trst && {dut.tx_pending,dut.tx_fill,trd,te,tq,terr}!==0)$fatal(1,"TX async reset row%0d",row);',
  '@(posedge clk);#1;',
  'if({rv,packet,overflow,boundary,rrd,dut.rx_fill,dut.rx_partial_count,te,tq,trd,dut.tx_fill,dut.tx_pending,dut.tx_group,terr}!=={'+','.join('e_'+n for n,_ in POST)+'})',
  '$fatal(1,"state row%0d actual%h expected%h",row,{rv,packet,overflow,boundary,rrd,dut.rx_fill,dut.rx_partial_count,te,tq,trd,dut.tx_fill,dut.tx_pending,dut.tx_group,terr},{'+','.join('e_'+n for n,_ in POST)+'});',
  'if(dut.rx_fill>2 || dut.rx_partial_count>15 || dut.tx_fill>72)$fatal(1,"bounds row%0d",row);',
  'row=row+1;end else if(n!=-1)$fatal(1,"malformed vector");end',
  'if(row<30000)$fatal(1,"truncated proof");',
  '$display("'+MARKER+' %0d",row);$finish;end','endmodule']
 return '\n'.join(lines)+'\n'
def command(args,label,passed=True):
 p=subprocess.run(list(map(str,args)),cwd=OUT,capture_output=True,text=True)
 (OUT/(label+'.log')).write_text(p.stdout+p.stderr)
 if passed:assert p.returncode==0,(label,p.stdout[-3000:],p.stderr[-3000:])
 return p
def simulate(paths,label,good):
 exe=OUT/(label+'.vvp')
 command(['iverilog','-g2012','-s','tb','-o',exe,*paths,OUT/'tb.v'],label+'-compile')
 p=command(['vvp',exe],label,False)
 if good:assert p.returncode==0 and MARKER in p.stdout,(label,p.stdout,p.stderr)
 else:assert p.returncode!=0 and 'FATAL'in p.stdout+p.stderr,(label,p.stdout,p.stderr)
 return dict(label=label,returncode=p.returncode,compile_sha256=sha(OUT/(label+'-compile.log')),log_sha256=sha(OUT/(label+'.log')))
def mutations():
 return {
 'collect_any_symbol':[("if(rx_next_count!=0 ||","if(rx_next_count==0 ||")],
 'restart_at_internal_COM':[("rx_next_partial[rx_next_count*8+:8]=rx_batch_data[s*8+:8];",
  "if(rx_batch_comma[s])begin rx_next_count=0;rx_next_partial=0;end\n      rx_next_partial[rx_next_count*8+:8]=rx_batch_data[s*8+:8];")],
 'discard_byte':[("rx_next_partial[rx_next_count*8+:8]=rx_batch_data[s*8+:8];","rx_next_partial[rx_next_count*8+:8]=0;")],
 'discard_K':[("rx_next_partial[128+rx_next_count]=rx_batch_k[s];","rx_next_partial[128+rx_next_count]=0;")],
 'discard_code_error':[("rx_next_partial[144+rx_next_count]=rx_batch_ce[s];","rx_next_partial[144+rx_next_count]=0;")],
 'discard_disparity_error':[("rx_next_partial[160+rx_next_count]=rx_batch_de[s];","rx_next_partial[160+rx_next_count]=0;")],
 'discard_internal_COM_flag':[("rx_next_partial[176+rx_next_count]=rx_batch_comma[s];","rx_next_partial[176+rx_next_count]=(rx_next_count==0);")],
 'complete_early':[("if(rx_next_count==15)begin","if(rx_next_count==14)begin")],
 'discard_trailing_batch_slots':[("if(s<rx_batch_count)begin","if(s<rx_batch_count && !rx_complete_valid)begin")],
 'ignore_simultaneous_pop_capacity':[("rx_complete_valid && rx_after_pop<2","rx_complete_valid && rx_fill<2")],
 'hide_overflow':[("rx_overflow_o<=1;rx_partial_count<=0;","rx_overflow_o<=0;rx_partial_count<=0;")],
 'ignore_RX_flush':[("if(rx_flush)begin","if(1'b0)begin")],
 'ignore_RX_polarity_flush':[(" || rx_polarity_i!=rx_previous_polarity","")],
 'validate_only_first_TX_chunk':[("for(k=0;k<16;k=k+1)","for(k=0;k<4;k=k+1)")],
 'accept_illegal_TX_K':[("if(tx_bad_k)tx_record_error_o<=1;","if(1'b0)tx_record_error_o<=1;")],
 'advance_TX_during_stall':[("if(tx_pending && tx_batch_ready)begin","if(tx_pending)begin")],
 'force_RD_every_chunk':[(".force_negative_rd_i(tx_force && tx_group==0)",".force_negative_rd_i(tx_force)")],
 'ignore_explicit_force_RD':[(".force_negative_rd_i(tx_force && tx_group==0)",".force_negative_rd_i(1'b0)")],
 'reverse_TX_chunks':[(".data_i(tx_data[tx_group*32+:32])",".data_i(tx_data[(3-tx_group)*32+:32])")],
 'read_unlatched_TX_input':[(".data_i(tx_data[tx_group*32+:32])",".data_i(tx_record_data_i[tx_group*32+:32])")],
 'ignore_TX_flush':[("if(!tx_enable_i || tx_flush_i)begin","if(!tx_enable_i)begin")],
 'discard_last_TX_chunk':[("if(tx_group==3)begin","if(tx_group==2)begin")]
 }
def main():
 assert os.environ.get('GITHUB_ACTIONS')=='true'
 OUT.mkdir(parents=True,exist_ok=False)
 result=dict(status='RUNNING',source=os.environ['GITHUB_SHA'],run=os.environ['GITHUB_RUN_ID'],
  protocol_TS_acceptance=False,training_owner_implemented=False,lane_negotiation_implemented=False,
  low_rate_PMA_accepted=False,gen3_transition_accepted=False,mainchip_connected=False,full_PHY_accepted=False)
 try:
  m,result['prerequisites']=prerequisites()
  path,result['coverage']=vectors();result['vector_sha256']=sha(path)
  (OUT/'tb.v').write_text(testbench());paths=[ROOT/p for p in FILES]
  result['icarus']=simulate(paths,'positive',True)
  command(['verilator','--binary','--timing','-Wno-fatal','--top-module','tb','--Mdir',OUT/'verilator','-o','record_test',*paths,OUT/'tb.v'],'verilator-build')
  p=command([OUT/'verilator/record_test'],'verilator');assert MARKER in p.stdout
  result['verilator']='PASS'
  net=OUT/'synthesis.json'
  command(['yosys','-p','read_verilog '+' '.join(map(str,paths))+'; synth -top soc_pcie_gen12_training_records; check -assert; write_json '+str(net)],'synthesis')
  n=json.loads(net.read_text());assert n['modules']['soc_pcie_gen12_training_records']['cells']
  assert all(not v.get('attributes',{}).get('blackbox')for v in n['modules'].values())
  result['synthesis']=dict(status='PASS',sha256=sha(net))
  controls=[];source=RTL.read_text()
  for label,edits in mutations().items():
   changed=source
   for before,after in edits:
    assert changed.count(before)==1,(label,before)
    changed=changed.replace(before,after)
   mutant=OUT/(label+'.v');mutant.write_text(changed)
   controls.append(simulate([mutant if p==RTL else p for p in paths],label,False))
  result['negative_controls']=controls
  assert len(controls)==22 and prerequisites()[0]==m
  result['status']='PASS_COMPOSED_CANDIDATE16_TRANSPORT_AND22_COMPILED_FAULTS'
 except BaseException as exc:
  result.update(status='FAIL_OR_ERROR',error=repr(exc));raise
 finally:
  result['outputs']={str(p.relative_to(OUT)):sha(p)for p in OUT.rglob('*')if p.is_file()and p.name!='result.json'}
  (OUT/'result.json').write_text(json.dumps(result,indent=2)+'\n')
  print(json.dumps({k:v for k,v in result.items()if k!='outputs'},indent=2))
if __name__=='__main__':main()
