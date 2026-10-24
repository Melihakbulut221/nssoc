#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0
"""Cloud-only native RTL verification against independent published code tables."""
import hashlib,json,os,random,re,subprocess,sys,urllib.request
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
OUT=ROOT/'hw/soc/out/cloud-pcie-gen12-codec'
MANIFEST=ROOT/'scripts/pcie-gen12-codec-methods.json'
TABLE=ROOT/'sw/tests/data/pcie_gen12_ieee8023z_codes.json'
MARKER='PASS_GEN12_CODEC_1024_ENCODE_2048_DECODE_2048_CHAIN_4096_LANE'
RTL=[
 'hw/soc/rtl/pcie/vendor/benz_8b10b_encode.v',
 'hw/soc/rtl/pcie/vendor/benz_8b10b_decode.v',
 'hw/soc/rtl/pcie/soc_pcie_gen12_8b10b_encode.v',
 'hw/soc/rtl/pcie/soc_pcie_gen12_8b10b_decode.v',
 'hw/soc/rtl/pcie/soc_pcie_gen12_codec_lane.v']
TB='sw/tests/rtl/tb_pcie_gen12_codec.v'
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def check():
 d=json.loads(MANIFEST.read_text())
 for p,h in d['protected'].items():assert sha(ROOT/p)==h,p
 provenance=json.loads((ROOT/'third_party/chuck_benz_8b10b/provenance.json').read_text())
 for row in provenance['derivatives']:
  text=(ROOT/row['original_path']).read_text()
  for edit in row['edits']:
   assert text.count(edit['before'])==edit['count']
   text=text.replace(edit['before'],edit['after'])
  assert text==(ROOT/row['path']).read_text()
 return d
def parse_primary(text):
 rows=[]
 for line in text.splitlines():
  d=re.match(r'^\s*D(\d+)\.(\d)\s+([01]{3})\s+([01]{5})\s+([01]{6})\s+([01]{4})\s+\d+\s+([01]{6})\s+([01]{4})\s',line)
  k=re.match(r'^\s*K(\d+)\.(\d)\s+([01]{6})\s+([01]{4})\s+([01]{6})\s+([01]{4})\s',line)
  if d:
   x,y,h,l,m6,m4,p6,p4=d.groups();assert int(h+l,2)==int(x)+32*int(y)
   rows.append(dict(k=0,data=int(x)+32*int(y),minus=m6+m4,plus=p6+p4))
  elif k:
   x,y,m6,m4,p6,p4=k.groups();rows.append(dict(k=1,data=int(x)+32*int(y),minus=m6+m4,plus=p6+p4))
 assert len(rows)==268 and len({(r['k'],r['data'])for r in rows})==268
 return sorted(rows,key=lambda r:(r['k'],r['data']))
def primary(table):
 source=table['source']
 raw=subprocess.run(['curl','-4','--http1.1','-A','Mozilla/5.0','--fail','--location','--retry','4','--max-time','60',source['url']],capture_output=True,check=True).stdout
 assert len(raw)==source['bytes'] and hashlib.sha256(raw).hexdigest()==source['sha256']
 text=subprocess.run(['pdftotext','-layout','-','-'],input=raw,capture_output=True,check=True).stdout.decode()
 assert parse_primary(text)==table['rows']
 return dict(url=source['url'],sha256=source['sha256'],rows=268,independent_published_table_exact=True)
def rd_after(bits,rd):
 # Printed abcdei then fghj. Special balanced cases must not be ignored.
 for part in (bits[:6],bits[6:]):
  if part.count('1')>len(part)//2 or part in ('000111','0011'):rd=1
  elif part.count('1')<len(part)//2 or part in ('111000','1100'):rd=0
 return rd
def tables(table):
 enc={};legal={};allowed=set()
 for r in table['rows']:
  for rd,name in enumerate(('minus','plus')):
   bits=r[name];code=int(bits[::-1],2)
   enc[rd,r['k'],r['data']]=(code,rd_after(bits,rd),0)
   value=r['data'],r['k']
   assert code not in legal or legal[code]==value
   legal[code]=value;allowed.add((rd,code))
 assert len(enc)==536 and len(legal)==464 and len(allowed)==536
 # Exact standard A7 cases; no reverse-only encoder-derived decode oracle.
 alt=[]
 for rd,xs,tail in ((0,(17,18,20),'0111'),(1,(11,13,14),'1000')):
  for x in xs:
   r=next(r for r in table['rows']if not r['k']and r['data']==224+x)
   assert r[('minus','plus')[rd]][6:]==tail
   alt.append(dict(rd=rd,data=r['data'],code=r[('minus','plus')[rd]]))
 assert enc[0,1,188][0]==int('0011111010'[::-1],2)
 assert enc[1,1,188][0]==int('1100000101'[::-1],2)
 return enc,legal,allowed,alt
def encode(enc,rd,k,data):return enc.get((rd,k,data),(0,rd,1))
def decode(legal,allowed,rd,code):
 bits=format(code,'010b')[::-1];nrd=rd_after(bits,rd)
 if code not in legal:return 0,0,nrd,1,0
 data,k=legal[code]
 return data,k,nrd,0,int((rd,code)not in allowed)
def pack(fields):
 value=0;width=0
 for number,bits in fields:
  assert 0<=number<2**bits
  value=(value<<bits)|number;width+=bits
 return format(value,'0'+str((width+3)//4)+'x')
def write_vectors(table):
 enc,legal,allowed,alt=tables(table);e=[];d=[];c=[];l=[]
 for rd in (0,1):
  for k in (0,1):
   for data in range(256):
    code,nrd,err=encode(enc,rd,k,data)
    e.append(pack(zip((rd,k,data,code,nrd,err),(1,1,8,10,1,1))))
  for code in range(1024):
   data,k,nrd,ce,de=decode(legal,allowed,rd,code)
   d.append(pack(zip((rd,code,data,k,nrd,ce,de),(1,10,8,1,1,1,1))))
 rng=random.Random(0x8b10b);symbols=sorted({(k,data)for _,k,data in enc})
 for i in range(2048):
  start=i&1;rd=start;dataword=kword=codeword=0
  for j in range(4):
   k,data=symbols[(i*4+j)%268]if i<268 else rng.choice(symbols)
   code,rd,err=encode(enc,rd,k,data);assert not err
   dataword|=data<<(j*8);kword|=k<<j;codeword|=code<<(j*10)
  c.append(pack(zip((start,kword,dataword,codeword,rd),(1,4,32,40,1))))
 txrd=rxrd=txcode=rxdata=rxk=0
 stats=dict(tx_disabled=0,rx_disabled=0,tx_invalid_k=0,rx_invalid_code=0,rx_wrong_disparity=0,independent_resets=0)
 for i in range(4096):
  trst=int(i%137!=0);rrst=int(i%113!=0);ten=rng.randrange(2);ren=rng.randrange(2)
  tk=rng.randrange(2);td=rng.randrange(256);rc=rng.randrange(1024)
  tv=te=rv=rce=rde=0
  if not trst:txrd=txcode=0
  elif ten:
   code,nrd,te=encode(enc,txrd,tk,td);tv=1-te
   if tv:txrd=nrd;txcode=code
  if not rrst:rxrd=rxdata=rxk=0
  elif ren:rxdata,rxk,rxrd,rce,rde=decode(legal,allowed,rxrd,rc);rv=1
  stats['tx_disabled']+=int(not ten);stats['rx_disabled']+=int(not ren)
  stats['tx_invalid_k']+=te;stats['rx_invalid_code']+=rce;stats['rx_wrong_disparity']+=rde
  stats['independent_resets']+=int(trst!=rrst)
  values=(trst,rrst,ten,ren,tk,td,rc,txcode,txrd,tv,te,rxdata,rxk,rxrd,rv,rce,rde)
  l.append(pack(zip(values,(1,1,1,1,1,8,10,10,1,1,1,8,1,1,1,1,1))))
 for name,rows in [('encode',e),('decode',d),('chain',c),('lane',l)]:
  (OUT/(name+'.mem')).write_text('\n'.join(rows)+'\n')
 assert min(stats.values())>0
 return dict(encode_cases=len(e),valid_encode=536,invalid_K_cases=488,decode_cases=len(d),all_codes_both_disparities=True,
  legal_code_patterns=len(legal),allowed_code_RD_pairs=len(allowed),four_symbol_chain_cases=len(c),lane_cycles=len(l),lane_coverage=stats,
  alternate_D7_cases=alt,all_RX_RD_updates_from_received_subblocks=True)
def command(args,label,cwd=OUT,expect_pass=True):
 p=subprocess.run(list(map(str,args)),cwd=cwd,capture_output=True,text=True)
 (OUT/(label+'.log')).write_text(p.stdout+p.stderr)
 if expect_pass:assert p.returncode==0,(label,p.returncode,(p.stdout+p.stderr)[-6000:])
 return p
def simulate(paths,label):
 exe=OUT/(label+'.vvp')
 command(['iverilog','-g2012','-s','tb_pcie_gen12_codec','-o',exe,*paths,ROOT/TB],label+'-compile')
 p=command(['vvp',exe],label,expect_pass=False)
 return p.returncode==0 and MARKER in p.stdout,p
def main():
 assert os.environ.get('GITHUB_ACTIONS')=='true'
 methods=check();OUT.mkdir(parents=True,exist_ok=False)
 result=dict(status='RUNNING',source_head=os.environ['GITHUB_SHA'],run_id=os.environ['GITHUB_RUN_ID'],
  LTSSM_implemented=False,comma_alignment_implemented=False,low_rate_PMA_qualified=False,full_PHY_accepted=False)
 def save():(OUT/'result.json').write_text(json.dumps(result,indent=2)+'\n')
 save()
 try:
  table=json.loads(TABLE.read_text());result['primary_oracle']=primary(table);result['coverage']=write_vectors(table)
  paths=[ROOT/p for p in RTL]
  good,p=simulate(paths,'icarus');assert good,p.stdout[-6000:]+p.stderr[-6000:]
  result['icarus']='PASS_INDEPENDENT_TABLE_AND_STATE_TESTS'
  command(['verilator','--binary','--timing','-Wno-fatal','--top-module','tb_pcie_gen12_codec','--Mdir',OUT/'verilator','-o','codec_test',*paths,ROOT/TB],'verilator-build')
  p=command([OUT/'verilator/codec_test'],'verilator');assert MARKER in p.stdout
  result['verilator']='PASS_SAME_INDEPENDENT_VECTORS'
  synth={}
  for top in ('soc_pcie_gen12_8b10b_encode','soc_pcie_gen12_8b10b_decode','soc_pcie_gen12_codec_lane'):
   target=OUT/(top+'.json')
   command(['yosys','-p','read_verilog '+' '.join(map(str,paths))+'; synth -top '+top+'; check -assert; write_json '+str(target)],'yosys-'+top)
   net=json.loads(target.read_text());cells=net['modules'][top]['cells'];assert cells
   assert all(not v.get('attributes',{}).get('blackbox')for v in net['modules'].values())
   synth[top]=dict(cells=len(cells),yosys_check_assert=True,netlist_sha256=sha(target))
  result['synthesis']=synth
  faults=[
   ('tx_bit_order',RTL[2],'10\'b0 : encoded','10\'b0 : {encoded[0],encoded[1],encoded[2],encoded[3],encoded[4],encoded[5],encoded[6],encoded[7],encoded[8],encoded[9]}'),
   ('tx_invalid_K',RTL[2],'assign k_error_o=k_i && !legal_k;','assign k_error_o=1\'b0;'),
   ('tx_RD_constant',RTL[2],'assign rd_o=k_error_o ? rd_i : next_rd;','assign rd_o=rd_i;'),
   ('rx_code_error_hidden',RTL[3],'assign code_error_o=bad_code;','assign code_error_o=1\'b0;'),
   ('rx_disparity_hidden',RTL[3],'assign disparity_error_o=!bad_code && bad_disparity;','assign disparity_error_o=1\'b0;'),
   ('rx_RD_invalid_hold',RTL[3],"assign rd_o=(ones4>3'd2","assign rd_o=bad_code ? rd_i : (ones4>3'd2"),
   ('rx_alternate7_reject',RTL[3],'assign code_error_o=bad_code;',"assign code_error_o=bad_code || code_i==10'b1110110001;"),
   ('lane_enable_ignored',RTL[4],'if(tx_enable_i && !tx_bad) begin','if(!tx_bad) begin'),
   ('lane_reset_positive',RTL[4],'tx_code_o<=0;tx_rd_o<=0;','tx_code_o<=0;tx_rd_o<=1;')]
  results=[]
  for name,path,before,after in faults:
   source=(ROOT/path).read_text();assert source.count(before)==1,(name,before)
   changed=OUT/(name+'.v');changed.write_text(source.replace(before,after))
   variant=[changed if p==ROOT/path else p for p in paths]
   passed,p=simulate(variant,'fault-'+name)
   assert not passed and p.returncode!=0 and 'FATAL' in p.stdout+p.stderr,(name,p.stdout,p.stderr)
   results.append(dict(name=name,rejected=True,mutant_sha256=sha(changed)))
  result['negative_controls']=results
  assert len(results)==9 and check()==methods
  result.update(status='PASS_GEN12_SINGLE_LANE_CODEC_TABLE_EXHAUSTIVE_STATE_SYNTHESIS_AND9_FAULTS',sources_unchanged=True)
 except BaseException as exc:
  result.update(status='FAIL_OR_ERROR',error=repr(exc));raise
 finally:
  result['outputs']={str(p.relative_to(OUT)):sha(p)for p in OUT.rglob('*')if p.is_file()and p!=OUT/'result.json'}
  save()
  print(json.dumps(dict(result_sha256=sha(OUT/'result.json'),result={k:v for k,v in result.items()if k!='outputs'}),indent=2))
if __name__=='__main__':main()
