# SPDX-License-Identifier: Apache-2.0
"""Cloud-only conditional signal statistics; never an acceptance replacement."""
import json,hashlib,zipfile,io,pathlib
import numpy as np
P=pathlib.Path
P('out').mkdir()
def archive(path,expected):
 with open(path,'rb') as f:actual=hashlib.file_digest(f,'sha256').hexdigest()
 assert actual==expected,(path,actual)
 return zipfile.ZipFile(path)
native=archive('native.zip','df95a0280336f6876e0308a4e7231e71f9d000f271398dcdad3d8eb89ae2f86a')
names=[n for n in native.namelist() if n.endswith('/loaded-n1-nominal_late.json') or n=='loaded-n1-nominal_late.json'];assert len(names)==1
meta_raw=native.read(names[0]);meta=json.loads(meta_raw);bits=np.asarray(meta['source_bits'],dtype=int)
assert len(bits)==256 and set(bits)=={0,1} and hashlib.sha256(bytes(bits.tolist())).hexdigest()==meta['source_bits_sha256'] and meta['data_offset_s']>0
aliases=meta['binding']['aliases'];UI=125e-12;START=2e-9
rows=[]
for variant,aid,digest in [('bd10_lowz8_xor2',14096157243,'cf6cbe5a8bdf71efdc612262083bb4cab937d2bf7bf4f4da010b708d23fdc769'),('bd10_lowz8_xor2_acbuf15',14103722468,'db6cb7f43236c307230a92222b9a05d3dd96ea8ee8db991f21a042c68a192b3e'),('bd10_lowz8_xor2_acbuf20',14104256551,'36800a0c924470105e0ed7857541c3b8b3e989969ed85597c29e1faa38b568cd')]:
 z=archive(variant+'.zip',digest)
 def one(suffix):
  matches=[n for n in z.namelist() if P(n).name==suffix];assert len(matches)==1;return z.read(matches[0])
 result=json.loads(one('result.json'));assert result['variant']==variant and result['returncode']==0 and not result['passed']
 capture=one('bit-phase-samples.npz');data=np.load(io.BytesIO(capture),allow_pickle=False);grid=data['grid'];values=data['samples'].astype(float);names=[str(n).lower() for n in data['names']]
 assert len(set(names))==len(names) and values.shape==(len(names),258*16) and np.isfinite(values).all()
 assert np.allclose(grid,START+np.arange(258*16)*UI/16,rtol=0,atol=1e-20)
 lookup={n:i for i,n in enumerate(names)}
 def v(node):
  node=aliases.get(node,node).lower();key='v('+node+')';assert key in lookup,(node,key);return values[lookup[key]]
 pairs={t:('xpd.'+t+'qp','xpd.'+t+'qn') for t in 'abcd'}
 pairs.update(x=('xp','xn'),y=('yp','yn'),buffer_a=('xpd.w_t275_c','xpd.w_t273_c'),buffer_c=('xpd.w_t280_c','xpd.w_t278_c'))
 diff={k:v(p)-v(n) for k,(p,n) in pairs.items()}
 indices=np.arange(2,254);current=bits[indices];previous=bits[indices-1]
 expected={'a':current,'b':current,'c':previous,'d':previous,'buffer_a':current,'buffer_c':previous,'x':current^previous,'y':previous^previous}
 # All selected phases are after the next falling edge: B now expects bits[k].
 # The original B gate samples from falling[k], a different window; unchanged.
 groups=[]
 phases=np.arange(16)/16
 # Exact preserved grid samples: rising[k] is at grid index16*k+8.
 slots=(indices[:,None]*16+8+np.arange(16)[None,:]).astype(int)
 assert np.allclose(grid[slots],START+(indices[:,None]+.5+phases[None,:])*UI,rtol=0,atol=1e-20)
 all_signals={k:signal[slots] for k,signal in diff.items() if k in ['a','buffer_a','c','buffer_c']}
 for prev in [0,1]:
  for cur in [0,1]:
   sel=(previous==prev)&(current==cur);assert sel.any()
   group={'previous_bit':prev,'current_bit':cur,'bit_count':int(sel.sum()),'signals':{}}
   for k,sampled in all_signals.items():
    target=current if k in ['a','buffer_a'] else previous
    signed=sampled*(2*target[:,None]-1)
    selected=signed[sel];ok=selected>=.1
    stable=np.logical_and.accumulate(ok[:,::-1],axis=1)[:,::-1]
    any_stable=stable.any(axis=1);first=np.argmax(stable,axis=1)
    settle=phases[first[any_stable]]*UI
    group['signals'][k]={'never_stable_100mv_by_last_phase':int((~any_stable).sum()),'stable_count':int(any_stable.sum()),'first_stable_delay_ps_percentiles':{str(q):float(np.percentile(settle,q)*1e12) for q in [0,50,90,100]} if len(settle) else None,'phase_signed_margin': [{'phase_ui':float(ph),'min_v':float(selected[:,j].min()),'median_v':float(np.median(selected[:,j])),'max_v':float(selected[:,j].max()),'wrong_sign':int((selected[:,j]<=0).sum()),'below_100mv':int((selected[:,j]<.1).sum())} for j,ph in enumerate(phases)]}
   groups.append(group)
 rows.append({'variant':variant,'artifact_id':aid,'artifact_sha256':digest,'capture_sha256':hashlib.sha256(capture).hexdigest(),'original_result_passed':result['passed'],'clock_vector_names':[n for n in names if 'clk' in n or 'clock' in n],'groups':groups})
r={'status':'EXACT_GRID_BUFFER_SETTLING_DIAGNOSIS_ONLY','source_runs':[43542889935,43562981217],'metadata_sha256':hashlib.sha256(meta_raw).hexdigest(),'source_bits_sha256':meta['source_bits_sha256'],'sample_step_s':UI/16,'b_expected_at_this_window':'bits[k], because rising[k]+0.6..0.9UI follows falling[k+1]; original falling-edge B acceptance is unchanged','prior_diagnostic_run':43562679420,'excluded_edge_bits':[0,1,254,255],'scope':'Exact preserved UI/16 grid, phase0..15/16 after rising[k]. Stable means signed margin>=100mV through last sampled phase, not continuous-time proof. A/buffer_A expected current bit and C/buffer_C previous bit as prior topology diagnosis; no new polarity proof. No waveform realignment, acceptance edits, new simulation or layout. Inspect transition-direction settling before a new circuit candidate; this is not a PHY pass.','accepted':False,'variants':rows}
P('out/buffer-settling.json').write_text(json.dumps(r,indent=2));print(r['status'])
