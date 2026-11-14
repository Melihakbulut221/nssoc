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
for variant,aid,digest in [('bd10_lowz8_xor2',14096157243,'cf6cbe5a8bdf71efdc612262083bb4cab937d2bf7bf4f4da010b708d23fdc769'),('bd10_lowz8_xor3',14096586409,'7ee65c2f95e548590b1b5416c5b4bc6b47b8a291a628bed353fa917edbc89816')]:
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
 for phase in [.6,.75,.9]:
  times=START+(indices+.5+phase)*UI
  sampled={k:np.interp(times,grid,signal) for k,signal in diff.items()}
  for prev in [0,1]:
   for cur in [0,1]:
    sel=(previous==prev)&(current==cur);assert sel.any()
    group={'phase_after_rising_ui':phase,'previous_bit':prev,'current_bit':cur,'bit_count':int(sel.sum()),'signals':{}}
    for k,values_k in sampled.items():
     x=values_k[sel];signed=x*(2*expected[k][sel]-1)
     group['signals'][k]={'differential_min_v':float(x.min()),'median_v':float(np.median(x)),'max_v':float(x.max()),'wrong_sign':int((signed<=0).sum()),'below_100mv':int((signed<.1).sum()),'signed_min_v':float(signed.min())}
    group['measured_input_parity_diagnostics']={}
    for name,left,right,out in [('a_b_vs_x_instantaneous_only','a','b','x'),('buffer_a_b_vs_x_instantaneous_only','buffer_a','b','x'),('y_sampler','c','d','y'),('y_buffer','buffer_c','d','y')]:
     valid=sel&(abs(sampled[left])>=.1)&(abs(sampled[right])>=.1)&(abs(sampled[out])>=.1)
     parity=(sampled[left]>0)^(sampled[right]>0);observed=sampled[out]>0
     group['measured_input_parity_diagnostics'][name]={'all_group_samples':int(sel.sum()),'three_signals_over_100mv':int(valid.sum()),'xor_agree':int((valid&(parity==observed)).sum()),'xnor_agree':int((valid&(parity!=observed)).sum()),'uncertain_excluded_from_parity_only':int((sel&~valid).sum())}
    groups.append(group)
 rows.append({'variant':variant,'artifact_id':aid,'artifact_sha256':digest,'capture_sha256':hashlib.sha256(capture).hexdigest(),'original_result_passed':result['passed'],'groups':groups})
r={'status':'CONDITIONAL_SAMPLED_DIAGNOSIS_ONLY','source_run':43542889935,'metadata_sha256':hashlib.sha256(meta_raw).hexdigest(),'source_bits_sha256':meta['source_bits_sha256'],'sample_step_s':UI/16,'b_expected_at_this_window':'bits[k], because rising[k]+0.6..0.9UI follows falling[k+1]; original falling-edge B acceptance is unchanged','supersedes_diagnostic_run':43554431443,'excluded_edge_bits':[0,1,254,255],'scope':'Interpolated preserved sample grid; conditional summaries do not replace continuous native waveform checks. No gate changes, signal realignment, inversion, circuit patch, new simulation or new layout. Measured input parity is diagnostic only and excludes low-margin triples explicitly. Buffer polarity follows prior topology diagnosis and is not independently proven by this report.','accepted':False,'variants':rows}
P('out/conditional-signals.json').write_text(json.dumps(r,indent=2));print(r['status'])
