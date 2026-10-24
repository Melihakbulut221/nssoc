# SPDX-FileCopyrightText: 2026 Hasan Melih Akbulut
# SPDX-License-Identifier: Apache-2.0
"""Read completed RX14 GRT captures only; rank measured endpoint alternatives."""
from pathlib import Path
import datetime,hashlib,json,re
S=Path(__file__).resolve().parent
pin=lambda p:dict(bytes=Path(p).stat().st_size,sha256=hashlib.sha256(Path(p).read_bytes()).hexdigest())
variants={}
for version in ['14a','14b']:
 root=Path('/dev/shm/nssoc-rx-prefetch-v2-postroute-repair-'+version+'-targeted-01')
 result=json.loads((root/'result.json').read_text())
 assert result['status']=='COMPLETE_CANDIDATE_REQUIRES_EQUIVALENCE_ROUTE_RC' and result['returncode']==0
 assert result['inputs']=={p:pin(p) for p in result['inputs']}
 assert result['outputs']=={n:pin(root/n) for n in result['outputs']}
 original=Path('/dev/shm/nssoc-rx-prefetch-v2-postroute-repair-'+version)
 assert (root/'repaired.v').read_bytes()==(original/'repaired.v').read_bytes(), 'Targeted report rerun changed logical candidate'
 text=(root/'native.log').read_text()
 tags=['CANDIDATE13_GRT_BEFORE_EXPLICIT_LOAD_ISOLATION','CANDIDATE_GLOBAL_ROUTE_ESTIMATES_ONLY']
 parsed={}
 all_labels=re.findall(r'^(CANDIDATE\S+)\s*$',text,re.M)
 for tag in tags:
  block={}
  for endpoint in ['_26191_','_26187_','_26189_']:
   block[endpoint]={}
   for corner in ['slow','typical','fast']:
    block[endpoint][corner]={}
    for direction in ['max','min']:
     label=f'{tag}_TARGET_{endpoint}_{corner}_{direction}'
     assert all_labels.count(label)==1
     start=text.index('\n'+label+'\n')+len(label)+2
     match=re.search(r'^CANDIDATE\S+\s*$|^NATIVE_POSTROUTE_REPAIR_CANDIDATE_COMPLETE$',text[start:],re.M)
     body=text[start:start+match.start()] if match else text[start:]
     values=re.findall(r'([+-]?[\d.]+)\s+slack \((MET|VIOLATED)\)',body)
     assert len(values)==1,(label,values)
     # The last before-report is followed by router diagnostics; keep only
     # the actual complete timing report through its unique slack line.
     end=re.search(r'([+-]?[\d.]+)\s+slack \((MET|VIOLATED)\)',body).end()
     body=body[:end]+'\n'
     assert 'Endpoint: '+endpoint+' ' in body
     block[endpoint][corner]['setup' if direction=='max' else 'hold']=dict(slack_ns=float(values[0][0]),classification=values[0][1],raw_report=body)
  parsed['before' if tag==tags[0] else 'after']=block
 delta={ep:{corner:{check:round(parsed['after'][ep][corner][check]['slack_ns']-parsed['before'][ep][corner][check]['slack_ns'],6) for check in ['setup','hold']} for corner in ['slow','typical','fast']} for ep in parsed['before']}
 variants[version]=dict(result=dict(path=str(root/'result.json'),**pin(root/'result.json')),repaired_netlist=pin(root/'repaired.v'),original_netlist=pin(original/'repaired.v'),source_unchanged=True,parsed=parsed,delta_ns=delta,minimum_targeted_slow_setup_ns=min(v['slow']['setup']['slack_ns'] for v in parsed['after'].values()),minimum_targeted_hold_ns=min(c['hold']['slack_ns'] for ep in parsed['after'].values() for c in ep.values()))
# Full initial path reports must agree exactly, not just rounded slacks.
assert variants['14a']['parsed']['before']==variants['14b']['parsed']['before']
eligible=[v for v in variants if variants[v]['minimum_targeted_hold_ns']>0]
ranked=sorted(eligible,key=lambda v:variants[v]['minimum_targeted_slow_setup_ns'],reverse=True)
r=dict(status='COMPLETED_GRT_TARGETED_ALTERNATIVE_COMPARISON_NOT_FINAL_TIMING',utc=datetime.datetime.now(datetime.UTC).isoformat(),method=pin(__file__),variants=variants,ranked_by_worst_targeted_slow_setup=ranked,suggested_candidate=ranked[0] if ranked else None,baseline_targeted_reports_byte_equal=True,physical_acceptance=False,qualified_rc=False,scope='Same4ns/IO/propagatedclock and placement/GRT algorithms. Three actual RX13 RC-critical endpoints only. Candidate source/netlist unchanged by added reports. Ranking is a GRT estimate, not final route/RC or whole-chip timing; require exact newproof,tenfaults,sixports before newDRT/actualnominalRC. Keep originalRX13 route/RC immutable and allrejected alternatives.')
p=S/'targeted-comparison.json';assert not p.exists();p.write_text(json.dumps(r,indent=2)+'\n');print(json.dumps(dict(status=r['status'],suggested=r['suggested_candidate'],minimum_setup={v:variants[v]['minimum_targeted_slow_setup_ns'] for v in variants},minimum_hold={v:variants[v]['minimum_targeted_hold_ns'] for v in variants},output=pin(p))))
