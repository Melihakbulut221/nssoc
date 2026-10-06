# SPDX-FileCopyrightText: 2026 Hasan Melih Akbulut
# SPDX-License-Identifier: Apache-2.0
"""Actual bounded saved-data/finite-stream controls, never a570 simulation."""
from pathlib import Path
import copy,gzip,hashlib,io,json,resource,sys
import numpy as np
B=Path(__file__).resolve().parent;sys.path.insert(0,str(B))
import characterize_clamped570_02 as m
D=B/'finite-controls05'
N=Path('/dev/shm/nssoc-vco-v6-divider-tail115-v1-sixteenthstep-06-01')

def main():
 resource.setrlimit(resource.RLIMIT_AS,(2*1024**3,2*1024**3));resource.setrlimit(resource.RLIMIT_CORE,(0,0))
 assert not D.exists();D.mkdir();outcomes=[]
 c,rows,texts=m.config(.6);expected=m.n.vectors(rows,c['extra_vectors']);columns=['time']+expected;names=m.stream.previous.data_names(columns)
 prior=json.loads((N/'result.json').read_text());assert m.pin(N/'result.json')==dict(bytes=426434,sha256='1428ee18fc41a19ff5b5a92c3cce2803f1c2fbbe29ce08c6a8c95c9610cf2ded')
 assert m.pin(N/'wave.raw.gz')==prior['outputs']['wave.raw.gz']
 oldexpected=m.n.vectors(prior['devices'],prior['config']['extra_vectors']);oldobs=m.previous.OBS
 selected=[];sample=None;whole=hashlib.sha256();payload=hashlib.sha256();count=0;size=0
 with gzip.open(N/'wave.raw.gz','rb')as src:
  header,meta=m.life.tiny.parse_header(src,oldexpected);whole.update(header);size+=len(header)
  oldnames=m.stream.previous.data_names(meta['columns']);indices=[oldnames.index(x)for x in oldobs];width=len(oldnames)*8;pending=bytearray()
  while block:=src.read(1024**2):
   whole.update(block);size+=len(block);pending.extend(block);take=len(pending)//width
   if take:
    body=bytes(pending[:take*width]);payload.update(body);a=np.frombuffer(body,'<f8').reshape(take,-1)
    selected.append(a[:,indices].copy());count+=take
    if sample is None and (a[:,0]>=4e-9).any():sample=a[np.flatnonzero(a[:,0]>=4e-9)[0]].copy()
    del pending[:take*width]
 assert bytes(pending)==str(count).encode()and count==prior['rows']
 assert whole.hexdigest()==prior['raw_sha256']and payload.hexdigest()==prior['payload_sha256']and size==prior['raw_bytes']
 data=dict(zip([x.replace('v(xchain.','v(xloop.xchain.')for x in oldobs],np.concatenate(selected).T));del selected
 t=data['time'];data.update({'v(vctrl)':np.full(len(t),.6),'i(vctrl)':np.full(len(t),2e-6),'v(up)':np.zeros(len(t)),'v(down)':np.zeros(len(t)),'v(reset)':np.full(len(t),2.5),'v(reference)':np.zeros(len(t))})
 result=m.measurement(data,c);assert result['passed']and result['checks']==prior['measurement']['checks']and len(result['checks'])==13
 assert all(abs(x['clamp_mean_a']-2e-6)<1e-18 for x in result['windows'])
 outcomes.append(dict(case='actual_saved13_predicates_with_declared_synthetic_idle_clamp_columns',passed=True,checks=result['checks'],clamp_windows=result['windows']))
 for vector,value,key in [('v(up)',.251,'pfd_up_idle'),('v(down)',.251,'pfd_down_idle'),('v(reset)',2.249,'external_reset_asserted'),('v(vctrl)',.600001,'actual_clamp_level')]:
  bad=dict(data);bad[vector]=np.full(len(t),value);r=m.measurement(bad,c)
  assert r['division_passed']and not r['passed']and not r['tuning_checks'][key]
  outcomes.append(dict(case='reject_'+key,passed=True,diagnostic=key))
 del data
 base=np.zeros(len(names))
 for i,name in enumerate(names):
  old=name.replace('xloop.xchain.','xchain.')
  if old in oldnames:base[i]=sample[oldnames.index(old)]
 base[names.index('v(reset)')]=2.5;base[names.index('v(up)')]=0;base[names.index('v(down)')]=0
 short=copy.deepcopy(c);short.update(stop_s=3*c['step_s'],window_s=[0,3*c['step_s']])
 a=np.tile(base,(4,1));a[:,0]=np.arange(4)*c['step_s']
 meter=m.Meter(columns,rows,short);meter.push(a);safe,_,grid=meter.finish()
 assert safe['passed']and len(safe['all_device_bounds'])==570
 outcomes.append(dict(case='all570_safety_rules_on_four_static_saved_operating_rows',passed=True,bounds=safe['all_device_bounds'],scope='Synthetic short safety fixture, not startup, physical dynamics or native result'))
 new_hv=next(x for x in rows if x['path'].startswith('xloop.xdet.')and x['model']=='sg13_hv_nmos')
 bad=a.copy();target=next(x for x in new_hv['nets']if x.startswith('xloop.xdet.'));bad[:,names.index('v('+target+')')]=3.301
 meter=m.Meter(columns,rows,short);meter.push(bad);s,_,_=meter.finish();assert not s['passed']and not next(x for x in s['all_device_bounds']if x['path']==new_hv['path'])['passed']
 outcomes.append(dict(case='actual_added_pfd_device_terminal_overvoltage',passed=True,device=new_hv['path']))
 contact=next(x for x in rows if x['model']=='ptap1');bad=a.copy();bad[:,names.index('v('+contact['nets'][0]+')')]+=3.4
 meter=m.Meter(columns,rows,short);meter.push(bad);s,_,_=meter.finish();assert not s['passed']and not next(x for x in s['all_device_bounds']if x['path']==contact['path'])['passed']
 outcomes.append(dict(case='retained_finite_contact_voltage_rejection',passed=True,device=contact['path']))
 # Exact native parser/capture over actual bytes. Measurement is independently
 # tested above; these four-row fixtures deliberately do not assert division.
 native_root=m.NATIVE_ROOT;callback=m.measurement;m.NATIVE_ROOT=D/'native';m.NATIVE_ROOT.mkdir()
 def short_measurement(data,config):return dict(passed=False,synthetic_four_row_transport_only=True)
 m.measurement=short_measurement
 def raw(array,trailer=b'4'):
  h=f'Title: Explicit synthetic570 finite control\nDate: fixed\nPlotname: Transient Analysis\nFlags: real\nNo. Variables: {len(columns)}\nNo. Points: 0\nVariables:\n'
  for i,name in enumerate(names):h+=f'{i}\t{name}\t'+('time'if i==0 else'current'if name.startswith('i(')else'voltage')+'\n'
  return h.encode()+b'Binary:\n'+array.astype('<f8').tobytes()+trailer
 try:
  for label,array,limit,diagnostic in [('positive',a,m.MAX_ROWS,None),('nonfinite',a.copy(),m.MAX_ROWS,'All native observations finite'),('row_budget',a,3,'Bounded120000 native rows including adaptive extras')]:
   if label=='nonfinite':array[2,1]=np.nan
   folder=m.NATIVE_ROOT/label;folder.mkdir();body=raw(array);fixture=D/(label+'.raw');fixture.write_bytes(body)
   old_limit=m.MAX_ROWS;m.MAX_ROWS=limit
   try:
    try:r=m.capture(io.BytesIO(body),folder,rows,short)
    except BaseException as error:
     assert diagnostic and diagnostic in str(error),(label,repr(error));failure=json.loads((folder/'capture-failure.json').read_text())
     assert failure['received_raw_bytes']==len(body)and failure['received_raw_sha256']==hashlib.sha256(body).hexdigest()
    else:assert diagnostic is None and r['safety']['passed']and r['rows']==4
   finally:m.MAX_ROWS=old_limit
   assert gzip.decompress((folder/'wave.raw.gz').read_bytes())==body
   outcomes.append(dict(case='finite_capture_'+label,passed=True,fixture=m.pin(fixture),captured=m.pin(folder/'wave.raw.gz'),expected_diagnostic=diagnostic,not_native=True))
 finally:m.measurement=callback;m.NATIVE_ROOT=native_root
 assert m.pin(N/'wave.raw.gz')==prior['outputs']['wave.raw.gz']
 report=dict(status='PASS_SAVED570_SAFETY_MEASUREMENT_AND_FAILED_PREFIX_CONTROLS',source=m.pin(Path(m.__file__)),method=m.pin(__file__),old_native_result=m.pin(N/'result.json'),old_raw=m.pin(N/'wave.raw.gz'),outcomes=outcomes,cases=len(outcomes),native_or_solver_executed=False,scope='Full prior455 raw was streamed once; actual13 reductions retained.570 safety uses explicit short synthetic steady rows plus zero-current new PFD nodes, never simulation. Transport positives and negatives call actual new FIFO parser/Meter/gzip/fsync code on finite bytes with measurement separately exercised over original full34ns timing. No physical570 PASS, tuning direction/range or polarity selection.')
 (D/'result.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(dict(result=m.pin(D/'result.json'),cases=len(outcomes))))

if __name__=='__main__':main()
