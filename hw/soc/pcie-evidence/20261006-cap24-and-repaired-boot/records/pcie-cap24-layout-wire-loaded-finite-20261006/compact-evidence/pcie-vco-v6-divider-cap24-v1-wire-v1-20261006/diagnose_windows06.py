# SPDX-FileCopyrightText: 2026 Hasan Melih Akbulut
# SPDX-License-Identifier: Apache-2.0
"""Descriptive windows over exact saved intrinsic terminals; no acceptance change."""
from pathlib import Path
import gzip,hashlib,json,os,resource,sys
import numpy as np
resource.setrlimit(resource.RLIMIT_AS,(2*1024**3,)*2);os.sched_setaffinity(0,{10})
R=Path.cwd();B=Path(__file__).resolve().parent;N=Path('/dev/shm/nssoc-vco-v6-divider-cap24-v1-wire-06-01')
sys.path.insert(0,str(R/'scripts'))
import characterize_pcie_vco_v6_divider_cap24_v1_wire_v1 as m

def pin(p):
 with p.open('rb')as f:return dict(bytes=p.stat().st_size,sha256=hashlib.file_digest(f,'sha256').hexdigest())
j=json.loads((N/'result.json').read_text());assert j['status']=='FAIL_NATIVE_LOADED_FEEDBACK_SCREEN'
c=json.loads((m.DIVIDER/'composition.json').read_text());b=json.loads((m.DIVIDER/'source-native-bijection.json').read_text());native={r['native_id']:r for r in c['records']};bound={r['source_name']:r for r in b['devices']}
with gzip.open(N/'wave.raw.gz','rb')as f:header,meta=m.life.tiny.parse_header(f,m.n.vectors(j['devices'],j['config']['extra_vectors']));blob=f.read()
assert hashlib.sha256(header+blob).hexdigest()==j['raw_sha256'];width=len(meta['columns'])*8;assert blob[j['rows']*width:]==str(j['rows']).encode()
a=np.frombuffer(blob[:j['rows']*width],'<f8').reshape(j['rows'],-1);assert np.isfinite(a).all();d=dict(zip(m.stream.previous.data_names(meta['columns']),a.T));t=d['time'];assert np.all(np.diff(t)>0)
witnesses={}
def probe(name,terminal):
 r=native[bound[name]['native_id']];term=next(z for z in r['terminals']if z['terminal']==terminal);label='v(xchain.xdiv.'+term['node'].lower()+')';assert label in d
 witnesses[name+'.'+terminal]=dict(native_id=r['native_id'],terminal=term,label=label);return label

def latch_pair(prefix,kind):
 return (probe(prefix+('__XCS'if kind=='clock'else'__XDN'),'B'if kind=='clock'else'C'),probe(prefix+('__XCH'if kind=='clock'else'__XDP'),'B'if kind=='clock'else'C'))
pairs={'VCO':('v(clkp)','v(clkn)'), 'FIRST_SLAVE_CLOCK':latch_pair('DIV__XFIRST__XCORE__XS','clock'),'FIRST_SLAVE_COLLECTOR':latch_pair('DIV__XFIRST__XCORE__XS','output'),'LIMITER_INPUT':(probe('DIV__XLP','B'),probe('DIV__XLN','B')),'LIMITER_COLLECTOR':(probe('DIV__XLN','C'),probe('DIV__XLP','C')),'SECOND_MASTER_CLOCK':latch_pair('DIV__XSECOND__XM','clock'),'SECOND_MASTER_COLLECTOR':latch_pair('DIV__XSECOND__XM','output'),'SECOND_SLAVE_CLOCK':latch_pair('DIV__XSECOND__XS','clock'),'SECOND_SLAVE_COLLECTOR':latch_pair('DIV__XSECOND__XS','output'),'PUBLIC_DIVIDER':('v(qp)','v(qn)')}
windows=[(4,18),(18,20),(20,22),(22,34)];out=[]
def stats(x,mask):
 v=x[mask];return dict(min=float(v.min()),max=float(v.max()),mean=float(v.mean()))
for lo,hi in windows:
 mask=(t>=lo*1e-9)&(t<hi*1e-9);rows=[]
 for name,(p,n)in pairs.items():
  diff=d[p]-d[n];edges=[e for e in m.n.common.crossings(t,diff,0)if lo*1e-9<=e<hi*1e-9]
  rows.append(dict(name=name,nodes=[p,n],differential=stats(diff,mask),common_mode=stats((d[p]+d[n])/2,mask),edges=len(edges),mean_frequency_hz=None if len(edges)<2 else (len(edges)-1)/(edges[-1]-edges[0])))
 hbts=[]
 for side in ['XM','XS']:
  for device in ['XT','XCS','XCH','XDP','XDN','XLP','XLN']:
   name='DIV__XSECOND__'+side+'__'+device;v={x:d[probe(name,x)]for x in ['C','B','E']};hbts.append(dict(name=name,VCE=stats(v['C']-v['E'],mask),VBE=stats(v['B']-v['E'],mask),VCB=stats(v['C']-v['B'],mask)))
 out.append(dict(window_ns=[lo,hi],samples=int(mask.sum()),signals=rows,second_stage_HBT=hbts))
r=dict(status='DESCRIPTIVE_SAVED_CAP24_TIME_WINDOW_DIAGNOSIS_NOT_ACCEPTANCE',native_status=j['status'],method=pin(Path(__file__)),inputs={str(p):pin(p)for p in [N/'result.json',N/'wave.raw.gz',m.DIVIDER/'composition.json',m.DIVIDER/'source-native-bijection.json']},values=int(a.size),native_raw_sha256=j['raw_sha256'],source_terminal_witnesses=witnesses,windows=out,scope='All original4-34ns acceptance retained FAIL. Short windows diagnose loss of division only, never substitute for the full-window gate. Actual intrinsic terminals selected through exact source/native graph, no ideal-net substitution, no native rerun.')
(B/'window-diagnosis06.json').write_text(json.dumps(r,indent=2)+'\n')
for window in out:
 print(window['window_ns'])
 for x in window['signals']:print(x['name'],x['mean_frequency_hz'],x['differential'],x['common_mode'])
