# SPDX-FileCopyrightText: 2026 Hasan Melih Akbulut
# SPDX-License-Identifier: Apache-2.0
"""Read saved Cap24 tail currents before defining the new bias prototype."""
from pathlib import Path
import gzip,hashlib,json,os,resource,sys
import numpy as np
resource.setrlimit(resource.RLIMIT_AS,(2*1024**3,)*2);os.sched_setaffinity(0,{10});R=Path.cwd();B=Path(__file__).resolve().parent;N=Path('/dev/shm/nssoc-vco-v6-divider-cap24-v1-wire-06-01')
sys.path.insert(0,str(R/'scripts'))
import characterize_pcie_vco_v6_divider_cap24_v1_wire_v1 as m

def pin(p):
 with p.open('rb')as f:return dict(bytes=p.stat().st_size,sha256=hashlib.file_digest(f,'sha256').hexdigest())
r=json.loads((N/'result.json').read_text());comp=json.loads((m.DIVIDER/'composition.json').read_text());bind=json.loads((m.DIVIDER/'source-native-bijection.json').read_text());rows={q['native_id']:q for q in comp['records']};by={q['source_name']:q for q in bind['devices']}
with gzip.open(N/'wave.raw.gz','rb')as f:h,meta=m.life.tiny.parse_header(f,m.n.vectors(r['devices'],r['config']['extra_vectors']));raw=f.read()
assert hashlib.sha256(h+raw).hexdigest()==r['raw_sha256'];n=len(meta['columns']);assert raw[r['rows']*n*8:]==str(r['rows']).encode();a=np.frombuffer(raw[:r['rows']*n*8],'<f8').reshape(r['rows'],n);assert np.isfinite(a).all();d=dict(zip(m.stream.previous.data_names(meta['columns']),a.T));out=[]
for stage in ['DIV__XFIRST__XCORE','DIV__XSECOND']:
 for latch in ['XM','XS']:
  name=stage+'__'+latch+'__XT';record=rows[by[name]['native_id']];assert record['model']=='npn13G2';node=record['line'].split()[0].lower();key='i(@q.xchain.xdiv.'+node+'.qnpn13g2[ic])';assert key in d
  result=dict(source_device=name,native_device=record['native_id'],actual_native_current_vector=key,windows=[])
  for lo,hi in [(4,18),(18,20),(20,22),(22,34)]:
   mask=(d['time']>=lo*1e-9)&(d['time']<hi*1e-9);x=d[key][mask];result['windows'].append(dict(window_ns=[lo,hi],samples=int(mask.sum()),min_A=float(x.min()),max_A=float(x.max()),mean_A=float(x.mean())))
  out.append(result)
j=dict(status='DESCRIPTIVE_ACTUAL_SAVED_TAIL_CURRENTS_NO_NATIVE_RERUN',inputs={str(p):pin(p)for p in [N/'result.json',N/'wave.raw.gz',m.DIVIDER/'composition.json',m.DIVIDER/'source-native-bijection.json']},method=pin(Path(__file__)),full_raw_sha256=r['raw_sha256'],native_status=r['status'],values=int(a.size),tails=out,scope='Measured ngspice HBT collector-current vectors, not voltage/resistance estimates. No acceptance changes; no new geometry or simulator run.')
(B/'parent-tail-current-diagnosis01.json').write_text(json.dumps(j,indent=2)+'\n')
for x in out:print(x['source_device'],[(q['window_ns'],q['mean_A'])for q in x['windows']])
