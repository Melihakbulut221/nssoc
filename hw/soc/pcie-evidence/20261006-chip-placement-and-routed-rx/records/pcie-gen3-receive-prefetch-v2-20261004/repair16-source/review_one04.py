# SPDX-FileCopyrightText: 2026 Hasan Melih Akbulut
# SPDX-License-Identifier: Apache-2.0
"""Read closed mixed-RC debug-only replay; preserve an adverse selection result."""
from pathlib import Path
import hashlib,json,re
B=Path(__file__).resolve().parent
D=Path('/dev/shm/nssoc-rx-prefetch-v2-postroute-repair-16-one-repair-04')
def pin(p):
 p=Path(p)
 with p.open('rb') as f:return dict(bytes=p.stat().st_size,sha256=hashlib.file_digest(f,'sha256').hexdigest())
j=json.loads((D/'result.json').read_text());assert j['status']=='COMPLETE_CANDIDATE_REQUIRES_EQUIVALENCE_ROUTE_RC' and j['returncode']==0
assert j['inputs']=={p:pin(p) for p in j['inputs']};assert j['outputs']=={p:pin(D/p) for p in j['outputs']}
assert pin(D/'before_final_grt.v')==pin(D/'repaired.v')
text=(D/'native.log').read_text();final=text.split('RX16ONE04_FRESH_FULL_GRT_FINAL\n',1)[1]
assert not any(x in final for x in ('Missing route to pin','Fail to restore routing segments'))
sec=re.split(r'^((?:UNCHANGED_RX14A_ACTUAL_RC|RX16ONE04_GRT_BEFORE_BROAD_REPAIR|RX16ONE04_RELOADED_ACTUAL_RC_BEFORE_REPAIR|RX16ONE04_GRT_AFTER_BROAD_REPAIR_ESTIMATES_ONLY)_(?:slow|typical|fast)_(?:min|max))\n',text,flags=re.M)
summary={};count=0
for marker,body in zip(sec[1::2],sec[2::2]):
 rows=[]
 for raw in body.split('Startpoint:')[1:]:
  sl=re.findall(r'(-?\d+\.\d+)\s+slack \((MET|VIOLATED)\)',raw);assert len(sl)==1
  kind='recovery' if 'recovery check' in raw else 'removal' if 'removal check' in raw else 'hold' if 'Path Type: min' in raw else 'setup'
  val=float(sl[0][0]);assert (val<0)==(sl[0][1]=='VIOLATED');rows.append((kind,val));count+=1
 summary[marker]={k:dict(reported=sum(t==k for t,v in rows),worst_ns=min(v for t,v in rows if t==k),negative=sum(v<0 for t,v in rows if t==k)) for k in {t for t,v in rows}}
assert count==2640
before=summary['RX16ONE04_GRT_BEFORE_BROAD_REPAIR_slow_max']['setup']['worst_ns'];after=summary['RX16ONE04_GRT_AFTER_BROAD_REPAIR_ESTIMATES_ONLY_slow_max']['setup']['worst_ns'];assert after<before
r=dict(status='REJECTED_FOR_NEW_DRT_WORSE_GRT_SETUP_THAN_UNCHANGED_BASELINE',method=pin(__file__),result=pin(D/'result.json'),summary=summary,actual_path_records=count,setup_estimate_gain_ns=round(after-before,6),final_route_context_clean=True,fullGRT_netlist_unchanged=True,native_not_reexecuted=True,scope='Same original4ns/hold0.05; actual-SPEF-first original clone/sizeup/buffer/split with debuglevel3 and max_repairs_per_pass1 produced worse final cleanGRT setup than the original baseline GRT. Finite experiment retained; no new proof/ports/DRT/RC or closure claim.')
(B/'one04-rejection-review.json').write_text(json.dumps(r,indent=2)+'\n');print(json.dumps(r,indent=2))
