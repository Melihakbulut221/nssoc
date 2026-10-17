# SPDX-FileCopyrightText: 2026 Hasan Melih Akbulut
# SPDX-License-Identifier: Apache-2.0
from pathlib import Path
import functools,hashlib,json,os,re,resource
resource.setrlimit(resource.RLIMIT_AS,(2*1024**3,)*2);os.sched_setaffinity(0,{8})
B=Path(__file__).resolve().parent;TOP='soc_pcie_gen3_continuous_rx_integrity_v21'
@functools.lru_cache(None)
def pin(path):
 p=Path(path)
 with p.open('rb')as f:return dict(bytes=p.stat().st_size,sha256=hashlib.file_digest(f,'sha256').hexdigest())
policy=B/'continuation-policy03.json';pol=json.loads(policy.read_text())
for key in('method_pins','source_pins'):
 for p,v in pol[key].items():assert pin(p)==v
state=json.loads((B/'continuation-status03.json').read_text());assert state['status']=='COMPLETE_NATIVE_SCREEN_FINITE_REVIEW_AND_PUBLICATION_REQUIRED'and len(state['stages'])==6
for stage in state['stages']:assert stage['returncode']==0 and stage['status']=='COMPLETE'
roots={k:Path('/dev/shm/nssoc-integrity-v21-balanced-'+k+'-01')for k in('map','import','sta')}
for k in('map','import'):
 d=roots[k];j=json.loads((d/'result.json').read_text());assert j['returncode']==0
 for p,v in j['inputs'].items():assert pin(p)==v
 for p,v in j['outputs'].items():assert pin(str(d/p))==v
sta=json.loads((roots['sta']/'result.json').read_text());assert sta['status']=='COMPLETE_PREPLACEMENT_SCREEN_REVIEW_REQUIRED'
for c in sta['cases']:
 assert c['returncode']==0
 for p,v in c['source_pins'].items():assert pin(p)==v
 # all capture output names are relative to case root
 for p,v in c['outputs'].items():assert pin(str(roots['sta']/c['kind']/p))==v
A=json.loads((roots['map']/'mapped.json').read_text())['modules'][TOP]
Z=json.loads((roots['import']/'mapped.json').read_text())['modules'][TOP]
def driver_table(m):
 d={}
 for n,p in m['ports'].items():
  if p['direction']=='input':
   for i,b in enumerate(p['bits']):assert b not in d;d[b]=('port',n,i)
 for n,c in m['cells'].items():
  for p,bs in c['connections'].items():
   if c['port_directions'][p]=='output':
    for i,b in enumerate(bs):
     symbol=('1'if c['type']=='sg13g2_tiehi'else'0')if c['type']in('sg13g2_tiehi','sg13g2_tielo')else('cell',n,p,i)
     assert b not in d or d[b]==symbol;d[b]=symbol
 return d
ad,zd=driver_table(A),driver_table(Z)
ties={n for n,c in Z['cells'].items()if c['type']in('sg13g2_tiehi','sg13g2_tielo')};assert len(ties)==2 and A['cells'].keys()==Z['cells'].keys()-ties
canonical=lambda bs,d:[d[b]if isinstance(b,int)else b for b in bs]
checked=0
for n,c in A['cells'].items():
 z=Z['cells'][n];assert c['type']==z['type']and c['parameters']==z['parameters']and c['port_directions']==z['port_directions']and c['connections'].keys()==z['connections'].keys()
 for p,bs in c['connections'].items():assert canonical(bs,ad)==canonical(z['connections'][p],zd);checked+=len(bs)
assert A['ports'].keys()==Z['ports'].keys()
for n,p in A['ports'].items():assert p['direction']==Z['ports'][n]['direction']and canonical(p['bits'],ad)==canonical(Z['ports'][n]['bits'],zd)
assert checked==368023 and len(A['cells'])==101103 and len(A['ports'])==24
del Z,zd
cells=A['cells'];nets=A['netnames'];flops={n for n,c in cells.items()if 'CLK'in c['port_directions']}
assert len(flops)==9612
@functools.lru_cache(None)
def support(bit):
 if not isinstance(bit,int)or bit not in ad or ad[bit][0]!='cell':return frozenset([bit])
 n=ad[bit][1]
 if n in flops:return frozenset([bit])
 return frozenset(x for p,bs in cells[n]['connections'].items()if cells[n]['port_directions'][p]=='input'for b in bs for x in support(b))
bound=json.loads((B/'native-registered-boundary.json').read_text());assert bound['mapped_source']['sha256']==pin(str(roots['map']/'mapped.json'))['sha256']
ring={bit for name,net in nets.items()if name.startswith(tuple('framer.'+n+'['for n in('slot_data','slot_keep','slot_sop','slot_eop','slot_dllp','slot_sequence','slot_tag','slot_verdict','verdict')))for bit in net['bits']if isinstance(bit,int)and bit in ad and ad[bit][0]=='cell'and ad[bit][1]in flops};assert len(ring)==3840
payload={b for f in('data','keep','sop','eop','dllp','sequence')for b in nets['framer.retire_'+f]['bits']if isinstance(b,int)}
desc=set();count=0
for field in bound['fields']:
 for row in field['rows']:
  q=row['descriptor_q'];o=row['output_d'];name=row['descriptor_cell'];assert ad[q]==('cell',name,'Q',0)and name in flops
  assert cells[name]['connections']['D']==[row['descriptor_d']]
  on=row['output_cell'];assert on in flops and cells[on]['connections']['D']==[o]
  assert q in support(o)and not(support(o)&ring);desc.add(name);count+=1
assert count==216 and len(desc)==200
for row in bound['availability_consumer_flop_d']:
 q=nets['framer.'+row['group']]['bits'][row['bit']];assert q==row['q']and ad[q]==('cell',row['cell'],'Q',0)
 assert cells[row['cell']]['connections']['D']==[row['d']]
 ss=support(row['d']);assert len(ss)==row['support_size']and not ss&(ring|payload)
assert len(bound['availability_consumer_flop_d'])==8
log=roots['sta']/'rx/native.log';text=log.read_text();sections=re.split(r'^((?:BASELINE_CELL_ONLY|PREPLACEMENT_REPAIRED)_(?:slow|typical|fast)_(?:min|max))\n',text,flags=re.M);timing=[]
for marker,chunk in zip(sections[1::2],sections[2::2]):
 values=[float(v)for v in re.findall(r'(-?\d+\.\d+)\s+slack \((?:MET|VIOLATED)\)',chunk)];assert len(values)==2
 stage,corner,direction=marker.rsplit('_',2);timing.append(dict(stage=stage,corner=corner,direction=direction,all_group_slacks_ns=values,worst_slack_ns=min(values)))
reported=json.loads((B/'timing-comparison.json').read_text());assert timing==reported['groups']and reported['acceptance']is False
actual={x['corner']+'_'+x['direction']:x['worst_slack_ns']for x in timing if x['stage']=='PREPLACEMENT_REPAIRED'}
assert actual['slow_max']==-3.564723 and actual['typical_max']==-.758974 and actual['fast_max']==.847446
r=dict(status='PASS_SAVED_V21_FINITE_NATIVE_RECOUNT_TIMING_REJECTED',findings=[],method=pin(str(Path(__file__))),policy=pin(str(policy)),source_receipts={str(B/n):pin(str(B/n))for n in('continuation-status03.json','native-registered-boundary.json','balanced-import-graph-proof.json','timing-comparison.json','critical-path-attribution.json','native-recovery-basis03.json')},closed_stage_count=6,actual_native_cells=101103,actual_native_FFs=9612,complete_import_pin_bits=checked,publicports=24,added_ties=2,independently_recomputed_descriptor_Q_to_output_D_bits=count,distinct_descriptor_payload_FFs=len(desc),original_ring_Q_count=len(ring),actual_availability_D_cuts=8,all24raw_STA_group_values_reparsed=timing,repaired_slacks_ns=actual,scope='Independent saved graph/FFsupport/import and rawSTA reader only; no EDA or completed tests rerun. Temporaryalias KeyError retained and mapped native never rerun. Same4ns preplacement SS/TT setup stillnegative; no routed/extracted timing, allmapped-functional replay, mainchip or fullPHY acceptance.')
(B/'native-saved-peer-rx03.json').write_text(json.dumps(r,indent=2)+'\n');print(json.dumps(r,indent=2))
