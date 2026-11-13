# SPDX-License-Identifier: Apache-2.0
"""Cloud-only sampled diagnosis; does not replace frozen full-wave acceptance."""
import hashlib,io,json,pathlib,zipfile
import numpy as np
out=pathlib.Path('out');out.mkdir(exist_ok=True)
def authenticate(path,digest):
 h=hashlib.sha256()
 with open(path,'rb') as f:
  for block in iter(lambda:f.read(1024*1024),b''):h.update(block)
 assert h.hexdigest()==digest,(path,h.hexdigest())
 return zipfile.ZipFile(path)
native=authenticate('native.zip','df95a0280336f6876e0308a4e7231e71f9d000f271398dcdad3d8eb89ae2f86a')
ns=[n for n in native.namelist() if n.endswith('/loaded-n1-nominal_late.json') or n=='loaded-n1-nominal_late.json'];assert len(ns)==1
meta_raw=native.read(ns[0]);meta=json.loads(meta_raw);bits=np.asarray(meta['source_bits'],dtype=int)
assert len(bits)==256 and set(bits)=={0,1} and hashlib.sha256(bytes(bits.tolist())).hexdigest()==meta['source_bits_sha256']
assert meta['data_offset_s']>0,'this diagnosis binds the nominal late case'
cap=authenticate('capture.zip','fde50c43560df485df21d64b3a05405680c3ad5a7774b6f8a54e501bde0b0bb0')
rs=[n for n in cap.namelist() if pathlib.PurePosixPath(n).name=='result.json'];assert len(rs)==1
record=json.loads(cap.read(rs[0]));assert record['variant']=='bd10_slave_parallel2_lowz8' and record['returncode']==0 and not record['passed']
ns=[n for n in cap.namelist() if n.endswith('bit-phase-samples.npz')];assert len(ns)==1
capture=cap.read(ns[0]);data=np.load(io.BytesIO(capture),allow_pickle=False)
names=[str(x).lower() for x in data['names']];assert len(set(names))==len(names)
samples=data['samples'].astype(float);grid=data['grid'];assert samples.shape==(len(names),258*16) and grid.shape==(258*16,)
assert np.isfinite(samples).all() and np.all(np.diff(grid)>0)
UI=125e-12;START=2e-9;assert np.allclose(grid,START+np.arange(258*16)*UI/16,rtol=0,atol=1e-20)
lookup={n:i for i,n in enumerate(names)};aliases=meta['binding']['aliases']
def vector(node):
 node=aliases.get(node,node).lower();key='v('+node+')'
 assert key in lookup,(node,'voltage not captured')
 return samples[lookup[key]],key
pairs={
 'sampler_a':('xpd.aqp','xpd.aqn','current','rising'),
 'sampler_b':('xpd.bqp','xpd.bqn','edge','falling'),
 'sampler_c':('xpd.cqp','xpd.cqn','previous','rising'),
 'sampler_d':('xpd.dqp','xpd.dqn','edge','rising'),
 'buffer_a_input':('xpd.w_t273_b','xpd.w_t275_b','current','rising'),
 'buffer_a_output':('xpd.w_t275_c','xpd.w_t273_c','current','rising'),
 'buffer_c_input':('xpd.w_t278_b','xpd.w_t280_b','previous','rising'),
 'buffer_c_output':('xpd.w_t280_c','xpd.w_t278_c','previous','rising'),
 'select0_input':('xpd.w_t281_b','xpd.w_t282_b','edge','rising'),
 'select0_output':('xpd.w_t282_c','xpd.w_t281_c','edge','rising'),
 'select1_input':('xpd.w_t299_b','xpd.w_t300_b','edge','rising'),
 'select1_output':('xpd.w_t300_c','xpd.w_t299_c','edge','rising'),
 'xor_x':('xp','xn','x','rising'),'xor_y':('yp','yn','y','rising')}
idx=np.arange(1,255);current=bits[idx];previous=bits[idx-1];following=bits[idx+1];edge=previous
expect={'current':current,'previous':previous,'edge':edge,'x':current^edge,'y':previous^edge}
phases=sorted(set([k/16 for k in range(16)]+[.3,.6,.75,.9]));patterns=[''.join(map(str,v)) for v in zip(previous,current,following)]
def stats(v):
 return dict(samples=int(len(v)),minimum_signed_v=float(v.min()),median_signed_v=float(np.median(v)),p05_signed_v=float(np.quantile(v,.05)),wrong_sign=int(np.count_nonzero(v<=0)),below_100mv=int(np.count_nonzero(v<.1)))
stages={}
for name,(p,n,expectation,clockedge) in pairs.items():
 vp,pn=vector(p);vn,nn=vector(n);delta=vp-vn;edges=START+(idx+(.5 if clockedge=='rising' else 0))*UI;rows=[]
 for phase in phases:
  signed=np.interp(edges+phase*UI,grid,delta)*(2*expect[expectation]-1)
  grouped={pattern:stats(signed[np.array([q==pattern for q in patterns])]) for pattern in sorted(set(patterns))}
  rows.append(dict(phase_ui=phase,all_patterns=stats(signed),patterns_previous_current_next=grouped))
 stages[name]=dict(nodes=[pn,nn],expected=expectation,clock_edge=clockedge,phases=rows)
r=dict(status='SAMPLED_PHASE_PATTERN_DIAGNOSIS',source_run=43497945915,source_native_artifact=14078587671,source_capture_artifact=14078352603,source_metadata_sha256=hashlib.sha256(meta_raw).hexdigest(),source_bits_sha256=meta['source_bits_sha256'],capture_sha256=hashlib.sha256(capture).hexdigest(),data_offset_s=meta['data_offset_s'],bit_indices=[1,254],grid_step_s=UI/16,stages=stages,scope='Diagnostic interpolation from 16 samples/UI; not continuous extrema, actual clock-to-valid timing, causal delay proof or new acceptance. Original full-wave verdict remains rejected. Stage input/output expectations are diagnostic hypotheses; analog polarity and delays must be interpreted before changes.',accepted=False,new_simulation=False,new_layout=False)
(out/'phase-pattern.json').write_text(json.dumps(r,indent=2));print(json.dumps({'stages':len(stages),'phases':len(phases),'source_bits_sha256':r['source_bits_sha256'],'accepted':False}))
