#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0
"""Cloud-only raw32-to-byte proof using global serial coordinates and table codes."""
import hashlib,json,os,random,subprocess
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
OUT=ROOT/'hw/soc/out/cloud-pcie-gen12-raw32-rx'
RTL=ROOT/'hw/soc/rtl/pcie/soc_pcie_gen12_raw32_rx.v'
FILES=[
 'hw/soc/rtl/pcie/vendor/benz_8b10b_decode.v',
 'hw/soc/rtl/pcie/soc_pcie_gen12_8b10b_decode.v',
 'hw/soc/rtl/pcie/soc_pcie_gen12_raw32_align.v',
 'hw/soc/rtl/pcie/soc_pcie_gen12_raw32_rx.v']
COM=(0x17c,0x283)
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def validate_receipt(item,binding):
 p=ROOT/item['receipt_path'];assert sha(p)==item['receipt_sha256']
 saved=json.loads(p.read_text())
 if item['role']=='aligner':
  assert saved['status']=='PASS'and saved['cycles']==95653 and saved['synthesis']=='PASS'
  assert saved['source_sha256']==binding['sources']['hw/soc/rtl/pcie/soc_pcie_gen12_raw32_align.v']
  c=saved['coverage']
  assert c['offsets']==list(range(64))and c['polarities']==[0,1]and c['initial_rd']==[0,1]
  assert c['all_raw10_payload_codes']==1024 and c['aligned_flush_residues']==list(range(10))
  assert set(c['search_flush_controls'])=={'reset','disable','force','polarity'}
  checks=saved['checks'];assert len(checks)==11 and checks[0]['label']=='positive'and checks[0]['returncode']==0
  assert len({x['label']for x in checks})==11 and all(x['returncode']!=0 for x in checks[1:])
  assert saved['full_phy_accepted']is False and saved['ltssm_accepted']is False and saved['low_rate_analog_accepted']is False
 else:
  assert item['role']=='codec'
  assert saved['status']=='PASS_EXACT_CODEC_NATIVE_ARTIFACT_SOURCES_TABLE_AND_ALL_GATES'
  assert saved['codec_RTL_accepted']and saved['native_conclusion']=='success'
  assert saved['native_run']==item['run']and saved['native_source']==item['head']and saved['native_attempt']==item['attempt']
  a=saved['artifact']
  assert a['all_recorded_member_hashes_verified']and a['metadata_digest']=='sha256:'+a['archive_sha256']and a['archive_bytes']>0
  r=saved['original_result']
  assert r['source_head']==item['head']and int(r['run_id'])==item['run']
  assert r['status']=='PASS_GEN12_SINGLE_LANE_CODEC_TABLE_EXHAUSTIVE_STATE_SYNTHESIS_AND9_FAULTS'
  assert len(r['negative_controls'])==9 and all(x['rejected']for x in r['negative_controls'])
  assert r['coverage']['decode_cases']==2048 and r['coverage']['all_codes_both_disparities']
  for path,h in saved['protected_sources'].items():assert sha(ROOT/path)==h,path
  assert saved['full_PHY_accepted']is False
 return item['receipt_sha256']
def proof():
 manifest=json.loads((ROOT/'scripts/pcie-gen12-raw32-rx-methods.json').read_text())
 for p,h in manifest['protected'].items():assert sha(ROOT/p)==h,p
 receipt=json.loads((ROOT/'scripts/pcie-gen12-raw32-rx-prerequisites.json').read_text())
 assert receipt['state']=='BOUND_TO_TWO_COMPLETED_NATIVE_PROOFS'
 assert len(receipt['runs'])==2 and {r['role']for r in receipt['runs']}=={'codec','aligner'}
 for p,h in receipt['sources'].items():assert sha(ROOT/p)==h,p
 live=[]
 for item in receipt['runs']:
  receipt_sha=validate_receipt(item,receipt)
  def api(tail):return json.loads(subprocess.check_output(['gh','api','repos/Melihakbulut221/nssoc/'+tail],text=True))
  run=api('actions/runs/'+str(item['run']))
  assert run['head_sha']==item['head'] and run['run_attempt']==item['attempt']
  assert run['status']=='completed' and run['conclusion']=='success'
  assert run['path']==item['workflow']
  jobs=api('actions/runs/'+str(item['run'])+'/jobs?filter=latest&per_page=100')['jobs']
  selected=[j for j in jobs if j['name']==item['job']]
  assert len(selected)==1 and selected[0]['status']=='completed' and selected[0]['conclusion']=='success'
  live.append(dict(run=item['run'],head=item['head'],attempt=item['attempt'],job=selected[0]['id'],conclusion='success',receipt_sha256=receipt_sha))
 return manifest,live
def bits(v,n):return [(v>>i)&1 for i in range(n)]
def number(v):return sum(b<<i for i,b in enumerate(v))
def rx_rd(code,rd):
 # Independent, printed wire-first subblock rule, including invalid codes.
 s=''.join(str(b)for b in bits(code,10))
 for sub in (s[:6],s[6:]):
  if sub.count('1')>len(sub)//2 or sub in ('000111','0011'):rd=1
  elif sub.count('1')<len(sub)//2 or sub in ('111000','1100'):rd=0
 return rd
def table():
 t=json.loads((ROOT/'sw/tests/data/pcie_gen12_ieee8023z_codes.json').read_text())
 legal={};allowed=set()
 assert len(t['rows'])==268
 for row in t['rows']:
  for rd,key in enumerate(('minus','plus')):
   code=int(row[key][::-1],2);value=(row['data'],row['k'])
   assert code not in legal or legal[code]==value
   legal[code]=value;allowed.add((rd,code))
 assert len(legal)==464 and len(allowed)==536
 return legal,allowed
class SerialOracle:
 """Continuous input coordinates plus one pending batch; no RTL shifts/remainders."""
 def __init__(self,legal,allowed):
  self.legal=legal;self.allowed=allowed;self.prev=0;self.rd=0
  self.stream=[];self.start=None;self.emitted=0;self.pending=([],False,False,0)
  self.pairs=set();self.rd_errors=0;self.code_errors=0;self.batches4=0
  self.flushes={k:{'residues':set(),'pending_counts':set(),'search':0}for k in ('reset','disable','force','polarity')}
 def clear(self):
  self.rd=0;self.stream=[];self.start=None;self.emitted=0;self.pending=([],False,False,0)
 def step(self,r,e,f,p,v,w):
  kind='reset'if not r else 'disable'if not e else 'force'if f else 'polarity'if p!=self.prev else None
  if kind:
   evidence=self.flushes[kind]
   evidence['pending_counts'].add(len(self.pending[0]))
   if self.start is None:evidence['search']+=1
   else:evidence['residues'].add((len(self.stream)-self.start)%10)
   self.clear();self.prev=p if r else 0
   return (0,0,0,0,0,0,0,0,0)
  self.prev=p
  codes,boundary,acquired,seed=self.pending
  if acquired:self.rd=seed
  data=k=ce=de=comma=0
  for slot,code in enumerate(codes):
   self.pairs.add((self.rd,code))
   if code in self.legal:
    byte,control=self.legal[code];bad=0;wrong=int((self.rd,code)not in self.allowed)
   else:byte=control=wrong=0;bad=1
   data|=byte<<(8*slot);k|=control<<slot;ce|=bad<<slot;de|=wrong<<slot;comma|=int(code in COM)<<slot
   self.rd=rx_rd(code,self.rd);self.rd_errors+=wrong;self.code_errors+=bad
  self.batches4+=int(len(codes)==4)
  result=(data,k,ce,de,comma,len(codes),int(boundary),int(acquired),self.rd)
  next_codes=[];first=False;incoming=0
  if v:
   self.stream.extend(bits(w^(0xffffffff if p else 0),32))
   if self.start is None:
    for at in range(len(self.stream)-9):
     code=number(self.stream[at:at+10])
     if code in COM:self.start=at;first=True;incoming=int(code==COM[1]);break
   if self.start is not None:
    end=(len(self.stream)-self.start)//10
    next_codes=[number(self.stream[self.start+j*10:self.start+(j+1)*10])for j in range(self.emitted,end)]
    self.emitted=end
  assert len(next_codes)<=4
  self.pending=(next_codes,self.start is not None,first,incoming)
  return result
def vectors():
 legal,allowed=table();oracle=SerialOracle(legal,allowed);rows=[];rng=random.Random(0x12dec0de)
 coverage=dict(offsets=list(range(64)),polarities=[0,1],acquisition_rd=[0,1],gaps=0,delivered_during_gap=0,pending_flushes=0)
 def add(r=1,e=1,f=0,p=0,v=1,w=0):
  pending=len(oracle.pending[0])
  out=oracle.step(r,e,f,p,v,w)
  coverage['gaps']+=int(not v)
  coverage['delivered_during_gap']+=int(not v and out[5]>0)
  coverage['pending_flushes']+=int(pending>0 and (not r or not e or f))
  rows.append((r,e,f,p,v,w,*out))
 def reset(p):
  add(r=0,v=0);add(p=p,v=0)
 def stream(offset,p,rd,codes,gaps=False):
  raw=[0]*offset+[b for c in [COM[rd]]+codes for b in bits(c,10)]
  raw += [0]*((-len(raw))%32)
  for at in range(0,len(raw),32):
   if gaps and rng.randrange(7)==0:add(p=p,v=0,w=rng.getrandbits(32))
   add(p=p,w=number(raw[at:at+32])^(0xffffffff if p else 0))
  add(p=p,v=0);add(p=p,v=0)
 # All raw acquisition phases, explicit polarities and both first-COM RDs.
 for offset in range(64):
  for p in (0,1):
   for rd in (0,1):
    reset(p);stream(offset,p,rd,list(range(1024))+[COM[rd^1]],True)
 # Each raw10 code with each actual incoming RD, independently seeded by COM.
 # COM flips RD. These directed cases cover wrong-RD legal and invalid symbols.
 for rd in (0,1):
  for code in range(1024):
   p=(code>>1)&1;reset(p);stream(code%32,p,rd^1,[code],True)
 assert oracle.pairs=={(rd,code)for rd in (0,1)for code in range(1024)}
 # Every control at every residue, with a real pending batch. Offsets0..9
 # produce all ten remainders, unlike advancing by an even32 bits alone.
 for kind in ('reset','disable','force','polarity'):
  for offset in range(10):
   reset(0)
   raw=[0]*offset+bits(COM[0],10)+[0]*(22-offset)
   add(w=number(raw))
   assert oracle.start==offset and oracle.pending[0]
   args={'reset':{'r':0},'disable':{'e':0},'force':{'f':1},'polarity':{'p':1}}[kind]
   add(w=0xffffffff,**args)
   p=int(kind=='polarity')
   for _ in range(3):add(p=p,w=0xffffffff if p else 0)
   stream(0,p,1,[0,COM[0],1023])
  # Flush while no complete COM has ever appeared.
  reset(0);add(w=0);add(v=0,w=0xffffffff);add(w=0)
  add(w=0xffffffff,**{'reset':{'r':0},'disable':{'e':0},'force':{'f':1},'polarity':{'p':1}}[kind])
  # Four symbols pending: five accepted raw words after offset0 acquisition.
  reset(0);add(w=COM[0])
  for _ in range(4):add(w=0)
  assert len(oracle.pending[0])==4
  add(w=0xffffffff,**{'reset':{'r':0},'disable':{'e':0},'force':{'f':1},'polarity':{'p':1}}[kind])
 for kind,record in oracle.flushes.items():
  assert record['residues']==set(range(10)),(kind,record)
  assert 4 in record['pending_counts']and record['search']>0
  record['residues']=sorted(record['residues']);record['pending_counts']=sorted(record['pending_counts'])
 assert oracle.rd_errors and oracle.code_errors and oracle.batches4
 assert coverage['delivered_during_gap']and coverage['pending_flushes']
 coverage.update(cycles=len(rows),actual_code_RD_pairs=len(oracle.pairs),invalid_codes_delivered=oracle.code_errors,
  wrong_RD_legal_codes_delivered=oracle.rd_errors,four_symbol_batches=oracle.batches4,flush_controls=oracle.flushes)
 path=OUT/'vectors.txt'
 path.write_text(''.join(' '.join(format(value,'x')for value in row)+'\n'for row in rows))
 return coverage,path
TB=r"""
module tb;
 reg clk=0;always #5 clk=~clk;
 reg rst=0,en=0,force_align=0,pol=0,valid=0;reg[31:0]raw=0;
 wire[31:0]data;wire[3:0]k,ce,de,comma;wire[2:0]count;wire boundary,acquired,rd;
 soc_pcie_gen12_raw32_rx dut(clk,rst,en,force_align,pol,valid,raw,data,k,ce,de,comma,count,boundary,acquired,rd);
 reg er,ee,ef,ep,ev;reg[31:0]ew,ed;reg[3:0]ek,ece,ede,em;reg[2:0]ec;reg eb,ea,erd;
 integer fd,n,row=0;
 initial begin
  fd=$fopen("vectors.txt","r");if(!fd)$fatal(1,"missing vectors");
  while(!$feof(fd))begin
   n=$fscanf(fd,"%h %h %h %h %h %h %h %h %h %h %h %h %h %h %h\n",
    er,ee,ef,ep,ev,ew,ed,ek,ece,ede,em,ec,eb,ea,erd);
   if(n==15)begin
    @(negedge clk);rst=er;en=ee;force_align=ef;pol=ep;valid=ev;raw=ew;
    #1;if(!rst && {data,k,ce,de,comma,count,boundary,acquired,rd}!==0)$fatal(1,"asynchronous reset row %0d",row);
    @(posedge clk);#1;
    if({data,k,ce,de,comma,count,boundary,acquired,rd}!=={ed,ek,ece,ede,em,ec,eb,ea,erd})
     $fatal(1,"row %0d actual %h expected %h",row,{data,k,ce,de,comma,count,boundary,acquired,rd},{ed,ek,ece,ede,em,ec,eb,ea,erd});
    row=row+1;
   end else if(n!=-1)$fatal(1,"malformed vector");
  end
  if(row<80000)$fatal(1,"truncated vector proof");
  $display("PASS_RAW32_RX_TABLE_STREAM_PIPELINE_FLUSH %0d",row);$finish;
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
 if expected:assert p.returncode==0 and 'PASS_RAW32_RX_TABLE_STREAM_PIPELINE_FLUSH'in p.stdout,p.stdout+p.stderr
 else:assert p.returncode!=0 and 'FATAL'in p.stdout+p.stderr,(label,p.stdout,p.stderr)
 return dict(label=label,returncode=p.returncode,log_sha256=sha(OUT/(label+'.log')))
def main():
 assert os.environ.get('GITHUB_ACTIONS')=='true'
 OUT.mkdir(parents=True,exist_ok=False)
 result=dict(status='RUNNING',source=os.environ['GITHUB_SHA'],run=os.environ['GITHUB_RUN_ID'],
  ltssm_accepted=False,link_up_inferred=False,low_rate_PMA_accepted=False,full_PHY_accepted=False)
 try:
  manifest,result['prerequisites']=proof();result['coverage'],vector_path=vectors()
  result['vector_sha256']=sha(vector_path);(OUT/'tb.v').write_text(TB)
  paths=[ROOT/p for p in FILES]
  result['icarus']=simulate(paths,'positive',True)
  command(['verilator','--binary','--timing','-Wno-fatal','--top-module','tb','--Mdir',OUT/'verilator','-o','rx_test',*paths,OUT/'tb.v'],'verilator-build')
  p=command([OUT/'verilator/rx_test'],'verilator')
  assert 'PASS_RAW32_RX_TABLE_STREAM_PIPELINE_FLUSH'in p.stdout
  result['verilator']='PASS'
  net=OUT/'synthesis.json'
  command(['yosys','-p','read_verilog '+' '.join(map(str,paths))+'; synth -top soc_pcie_gen12_raw32_rx; check -assert; write_json '+str(net)],'synthesis')
  n=json.loads(net.read_text());assert n['modules']['soc_pcie_gen12_raw32_rx']['cells']
  assert all(not v.get('attributes',{}).get('blackbox')for v in n['modules'].values())
  result['synthesis']=dict(status='PASS',sha256=sha(net))
  faults={
   'drop_acquisition_seed':('aligned_acquired ? aligned_rd : rd_o','rd_o'),
   'drop_RD_chain':('.rd_i(chain_rd[g])','.rd_i(chain_rd[0])'),
   'hold_invalid_RD':('(aligned_count>g) ? next_rd[g] : chain_rd[g]','(aligned_count>g && !bad_code[g]) ? next_rd[g] : chain_rd[g]'),
   'advance_unused_slots':('(aligned_count>g) ? next_rd[g] : chain_rd[g]','next_rd[g]'),
   'ignore_force_flush':('!enable_i || force_realign_i ||','!enable_i ||'),
   'ignore_disable_flush':('!enable_i || force_realign_i ||','force_realign_i ||'),
   'ignore_polarity_flush':(' || polarity_i!=previous_polarity',''),
   'drop_pending_on_valid_gap':('if(flush)begin','if(flush || !raw_valid_i)begin'),
   'reverse_bytes':('decoded[i*8+:8]','decoded[(3-i)*8+:8]'),
   'hide_code_error':('code_error_o[i]<=bad_code[i];',"code_error_o[i]<=1'b0;"),
   'hide_disparity_error':('disparity_error_o[i]<=bad_disparity[i];',"disparity_error_o[i]<=1'b0;"),
   'drop_fourth_slot':('i<aligned_count','i<aligned_count && i<3')}
  src=RTL.read_text();controls=[]
  for label,(before,after)in faults.items():
   assert src.count(before)==1,(label,before)
   mutant=OUT/(label+'.v');mutant.write_text(src.replace(before,after))
   controls.append(simulate([mutant if p==RTL else p for p in paths],label,False))
  result['negative_controls']=controls
  assert len(controls)==12 and proof()[0]==manifest
  result['status']='PASS_RAW32_RX_EXHAUSTIVE_STREAM_RD_PIPELINE_FLUSH_AND12_FAULTS'
 except BaseException as exc:
  result.update(status='FAIL_OR_ERROR',error=repr(exc));raise
 finally:
  result['outputs']={str(p.relative_to(OUT)):sha(p)for p in OUT.rglob('*')if p.is_file()and p.name!='result.json'}
  (OUT/'result.json').write_text(json.dumps(result,indent=2)+'\n')
  print(json.dumps({k:v for k,v in result.items()if k!='outputs'},indent=2))
if __name__=='__main__':main()
