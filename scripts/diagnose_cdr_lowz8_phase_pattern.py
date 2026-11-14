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

UI=125e-12;START=2e-9
# Crossing classification retains left-censoring, missing and ambiguous events.
def crossing(t,y,threshold):
 assert len(t)==len(y) and len(t)>2 and np.all(np.diff(t)>0) and np.isfinite(y).all()
 hits=np.flatnonzero((y[:-1]<threshold)&(y[1:]>=threshold))
 times=[float(t[i]+(threshold-y[i])*(t[i+1]-t[i])/(y[i+1]-y[i])) for i in hits]
 if y[0]>=threshold:status='left_censored'
 elif len(times)==0:status='missing'
 elif len(times)>1:status='ambiguous'
 else:status='unique'
 return {'status':status,'crossings_s':times,'left_boundary_v':float(y[0]),'right_boundary_v':float(y[-1])}
# Known offset, never-crossing and nonunique cases must remain distinct.
t=np.array([0.,1.,2.,3.]);assert crossing(t,t-1.,0.)['crossings_s']==[1.]
assert crossing(t,np.ones(4),0.)['status']=='left_censored'
assert crossing(t,-np.ones(4),0.)['status']=='missing'
assert crossing(np.arange(5.),np.array([-1.,1.,-1.,1.,1.]),0.)['status']=='ambiguous'
rows=[]
for label,ip,inn,op,on,lag in [
 ('buffer_a','xpd.w_t273_b','xpd.w_t275_b','xpd.w_t275_c','xpd.w_t273_c',0),
 ('buffer_c','xpd.w_t278_b','xpd.w_t280_b','xpd.w_t280_c','xpd.w_t278_c',1)]:
 vi=vector(ip)[0]-vector(inn)[0];vo=vector(op)[0]-vector(on)[0]
 stage=[]
 for k in range(2,254):
  # Restrict response measurements to an actual transition in expected data.
  if bits[k-lag]==bits[k-lag-1]:continue
  edge=START+(k+.5)*UI;left=edge-.25*UI;right=edge+.95*UI
  times=np.concatenate(([left],grid[(grid>left)&(grid<right)],[right]));sign=2*int(bits[k-lag])-1
  values={'input':np.interp(times,grid,vi)*sign,'output':np.interp(times,grid,vo)*sign}
  thresholds={}
  for threshold in (0.,.1):
   result={key:crossing(times,value,threshold) for key,value in values.items()}
   delay=None
   if all(v['status']=='unique' for v in result.values()):delay=result['output']['crossings_s'][0]-result['input']['crossings_s'][0]
   thresholds[str(threshold)]={'signals':result,'output_minus_input_s':delay}
  stage.append({'bit_index':k,'history_previous2_current_next':''.join(map(str,bits[k-2:k+2])),'expected_bit':int(bits[k-lag]),'original_rising_edge_s':edge,'thresholds':thresholds})
 summaries={}
 for threshold in ('0.0','0.1'):
  delays=[x['thresholds'][threshold]['output_minus_input_s'] for x in stage if x['thresholds'][threshold]['output_minus_input_s'] is not None]
  summaries[threshold]={'unique_input_output_pairs':len(delays),'all_transition_bits':len(stage),'status_counts':{side:{status:sum(x['thresholds'][threshold]['signals'][side]['status']==status for x in stage) for status in ['unique','missing','ambiguous','left_censored']} for side in ['input','output']},'delay_ps':{'min':float(min(delays)*1e12),'median':float(np.median(delays)*1e12),'max':float(max(delays)*1e12)} if delays else None}
 rows.append({'stage':label,'nodes':[ip,inn,op,on],'summaries':summaries,'transition_rows':stage})
r={'status':'SAMPLED_BUFFER_RESPONSE_DIAGNOSIS','source_run':43497945915,'metadata_sha256':hashlib.sha256(meta_raw).hexdigest(),'capture_sha256':hashlib.sha256(capture).hexdigest(),'source_bits_sha256':meta['source_bits_sha256'],'sample_step_s':UI/16,'original_edge_window_ui':[-.25,.95],'stages':rows,'controls':'known crossing, left-censored, missing and ambiguous classifications checked','scope':'Diagnostic interpolation only, not continuous waveform proof or causal transistor-delay attribution. Original 0.3/0.6/0.9 UI gates unchanged. Out-of-window and ambiguous crossings remain unresolved; no ideal input replacement or signal realignment. Analog polarity expectations require original topology interpretation.','accepted':False,'new_simulation':False,'new_layout':False}
(out/'buffer-response.json').write_text(json.dumps(r,indent=2));print(json.dumps({x['stage']:x['summaries'] for x in rows}))
