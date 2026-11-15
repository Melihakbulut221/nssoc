# SPDX-License-Identifier: Apache-2.0
"""Noninvasive native PLL boundary-current diagnosis, no new transient."""
import os,json,subprocess,hashlib,zipfile,io,time,re,shutil,traceback,base64
from pathlib import Path
import numpy as np
P='repos/Melihakbulut221/nssoc/'
OUT=Path('pll-boundary-current-analysis');OUT.mkdir();NATIVE=Path('pll-boundary-current-native');NATIVE.mkdir()
def api(s):return json.loads(subprocess.check_output(['gh','api',P+s],timeout=180))
def sha(p):
 with Path(p).open('rb')as f:return hashlib.file_digest(f,'sha256').hexdigest()
def save(n,d):(OUT/n).write_text(json.dumps(d,indent=2,allow_nan=False)+'\n')
def small(aid,digest):
 m=api(f'actions/artifacts/{aid}');assert m['digest']=='sha256:'+digest and not m['expired']
 b=subprocess.check_output(['gh','api',P+f'actions/artifacts/{aid}/zip'],timeout=180);assert hashlib.sha256(b).hexdigest()==digest
 return zipfile.ZipFile(io.BytesIO(b))
def run():
 assert os.environ.get('GITHUB_ACTIONS')=='true' and os.environ.get('RUNNER_ENVIRONMENT')=='github-hosted'
 deadline=time.monotonic()+5400
 while True:
  producer=api('actions/runs/43703613123');assert producer['head_sha']=='90c1662b6d2597d85fdd171ff3e91deaf4825e7f' and producer['run_attempt']==1
  if producer['status']=='completed':break
  assert time.monotonic()<deadline,'Producer still live; no simulation restarted'
  print('Waiting for actual PLL native artifact publication',producer['status'],flush=True);time.sleep(45)
 assert producer['conclusion']=='success'
 safe=small(14159376096,'7c41c46d59205b5ea01d3536c4ce1952bb6d7216ffba699f3a5e067daa0ea49e');report=json.loads(safe.read('result.json'))
 assert report['shared_prefix_bits_identical'] and report['original_sources_unchanged'] and report['prefix_bit_mutant_rejected']
 assert report['rows']==419392 and report['variables']==5216 and report['reference']['strictly_before_130ns_rows']==416191
 incidence=json.loads(small(14156446419,'90ae28c3fc79198c1594944707f6e3f47936ff64086328732e139111cd3bf54c').read('readback.json'))
 assert incidence['unique_boundaries']==21 and len(report['passive_boundary'])==54 and len(report['substrate_boundary'])==14
 assert incidence['metal_model_sha256']=='02210e5fe8dce4c0fbda06de98d5651b5a894e6ad2d9b2f3e7bb83acf671b258'
 rebuilt=[]
 for row in incidence['terminal_incidence']:
  assert row['unique_device_with_explicit_passive_boundary'] and not row['other_device_cards']
  for branch in row['passive_branches']:
   rebuilt.append(dict(device=row['device'],terminal=row['terminal'],query='@'+branch['kind']+'.xloop.'+branch['instance'].lower()+'[i]',device_current_sign=-branch['outward_sign']))
 assert rebuilt==report['passive_boundary']
 proposal=api('contents/docs/pll-first-latch-current-instrumentation-proposal-20261024.json?ref=d05b2bf1756194d1dd5e8f8fb816044a9a1e9a14')
 pb=base64.b64decode(proposal['content']);assert hashlib.sha256(pb).hexdigest()=='0901c0d174bb1ce5c6fb7e34021fb5c948309637e8543807fdd71fed7bfcd077'
 intervals=json.loads(pb)['window']['actual_original_anomalous_intervals'];assert len(intervals)==26
 artifacts=api('actions/runs/43703613123/artifacts')['artifacts'];matches=[a for a in artifacts if a['name']=='pll-current-prefix130ns-native-43703613123' and not a['expired']];assert len(matches)==1
 meta=matches[0];assert meta['workflow_run']['head_sha']==producer['head_sha'] and meta['workflow_run']['id']==43703613123
 rawbytes=report['rows']*report['variables']*8+1048576
 assert shutil.disk_usage('/tmp').free>meta['size_in_bytes']+rawbytes+2*1024**3,'Insufficient hosted extraction space; no partial calculation'
 archive=Path('/tmp/pll-native.zip')
 with archive.open('xb')as out:subprocess.run(['gh','api',P+f"actions/artifacts/{meta['id']}/zip"],stdout=out,check=True,timeout=2400)
 assert 'sha256:'+sha(archive)==meta['digest']
 raw=Path('/tmp/current131ns.raw')
 with zipfile.ZipFile(archive)as z:
  names=[n for n in z.namelist()if n=='current131ns.raw' or n.endswith('/current131ns.raw')];assert len(names)==1
  with z.open(names[0])as inp,raw.open('xb')as out:shutil.copyfileobj(inp,out,1048576)
 archive.unlink();assert sha(raw)==report['raw_sha256']=='37ca78285805c3cbf8538c75223501cbdfcfc30013ee2d8f19892b56b8b62cf2'
 with raw.open('rb')as f:header=f.read(1048576)
 off=header.index(b'Binary:\n')+len(b'Binary:\n');header=header[:off];assert header==safe.read('header.txt')
 rows=[x.split()for x in header.decode().split('Variables:\n')[1].split('Binary:\n')[0].splitlines()];assert len(rows)==5216 and all(len(x)==3 for x in rows)
 names=[x[1].lower()for x in rows];types={x[1].lower():x[2]for x in rows};assert names[0]=='time' and len(set(names))==len(names)
 assert raw.stat().st_size-off==419392*5216*8
 m=np.memmap(raw,mode='r',dtype='<f8',offset=off,shape=(419392,5216))
 voltage={}
 for row in incidence['terminal_incidence']:voltage[(row['device'],row['terminal'])]='v(xloop.'+row['node'].lower()+')'
 queries=report['queries'];obs=['time']+list(dict.fromkeys(voltage.values()))+[q if q.endswith(('[qbe]','[qbc]'))else'i('+q+')'for q in queries]
 assert len(set(obs))==len(obs)
 for v in voltage.values():assert types[v]=='voltage'
 indices=[names.index(n)for n in obs];compact=np.empty((419392,len(obs)))
 for lo in range(0,len(m),512):
  block=np.asarray(m[lo:lo+512,:]);assert np.isfinite(block).all();compact[lo:lo+512]=block[:,indices]
 del m
 t=compact[:,0];assert t[0]==0 and t[-1]==131e-9 and np.all(np.diff(t)>0)
 def val(n):return compact[:,obs.index(n)]
 def query(n):return val(n if n.endswith(('[qbe]','[qbc]'))else'i('+n+')')
 ids=sorted(map(int,report['targets']));assert ids==[391,392,393,394,395,396,400]
 currents={}
 for device in ids:
  for term in ['C','B','E']:
   branches=[b for b in rebuilt if b['device']==device and b['terminal']==term];assert branches
   currents[(device,term)]=sum((b['device_current_sign']*query(b['query'])for b in branches),np.zeros(len(t)))
  branches=[b for b in report['substrate_boundary']if b['device']==device];assert len(branches)==2
  currents[(device,'S')]=sum((b['device_current_sign']*query(b['query'])for b in branches),np.zeros(len(t)))
 def extrema(v,lo=0,hi=None):
  hi=len(t)if hi is None else hi;chunk=v[lo:hi];assert len(chunk)
  low=lo+int(np.argmin(chunk));high=lo+int(np.argmax(chunk))
  return dict(minimum=float(v[low]),minimum_row=low,minimum_time_s=float(t[low]),maximum=float(v[high]),maximum_row=high,maximum_time_s=float(t[high]))
 diagnostics=[]
 for device in ids:
  port=[currents[(device,term)]for term in ['C','B','E','S']];residual=sum(port,np.zeros(len(t)));scale=sum((abs(x)for x in port),np.zeros(len(t)))
  model_leaf=report['targets'][str(device)]
  collector_model=query('@'+model_leaf+'[ic]')
  diagnostics.append(dict(device=device,ports_a={term:extrema(currents[(device,term)])for term in ['C','B','E','S']},kcl_residual_a=extrema(residual),maximum_normalized_kcl_residual=float(np.max(abs(residual)/np.maximum(scale,1e-9))),collector_terminal_minus_model_ic_a=extrema(port[0]-collector_model),scope='Measured physical boundary sums; KCL statistics are diagnostics, not a relaxed safety or acquisition gate.'))
 windows=[]
 for window in intervals:
  start,end=window['interval_s'];lo=int(np.searchsorted(t,start));hi=int(np.searchsorted(t,end,side='right'));assert hi>lo
  for event in window['events']:
   left,right=event['bracketing_rows'];assert t[left]<=event['time_s']<=t[right]
  windows.append(dict(index=window['index'],interval_s=window['interval_s'],native_rows=[lo,hi],devices=[dict(device=dev,currents_a={term:extrema(currents[(dev,term)],lo,hi)for term in ['C','B','E','S']},vce_v=extrema(val(voltage[(dev,'C')])-val(voltage[(dev,'E')]),lo,hi),vbe_v=extrema(val(voltage[(dev,'B')])-val(voltage[(dev,'E')]),lo,hi))for dev in ids]))
 # Retain every native queried sample and every reconstructed port sample.
 current_names=[f'{dev}:{term}'for dev in ids for term in ['C','B','E','S']]
 np.savez_compressed(NATIVE/'current-observation.npz',native_names=np.array(obs),native_values=compact,current_names=np.array(current_names),current_values=np.column_stack([currents[(dev,term)]for dev in ids for term in ['C','B','E','S']]))
 save('device-current-diagnostics.json',diagnostics);save('anomalous-window-currents.json',windows)
 result=dict(status='READ_ONLY_PHYSICAL_BOUNDARY_CURRENT_DIAGNOSIS',accepted=False,complete_terminal_currents_qualified=False,acquisition_accepted=False,full_phy_accepted=False,producer_run=43703613123,producer_head=producer['head_sha'],native_artifact_id=meta['id'],native_artifact_sha256=meta['digest'],raw_sha256=report['raw_sha256'],rows=len(t),original_saved_columns=5216,retained_native_columns=len(obs),reconstructed_ports=28,original_anomalous_windows=26,incidence_source_run=43700489696,compact_file_sha256=sha(NATIVE/'current-observation.npz'),scope='No added sources or circuit changes; actual passive branch currents from authenticated unique C/B/E boundaries and native Rsub/Csub substrate branches. Model ic is separately retained and is not substituted for terminal current. KCL and device safety require review; original acquisition rejection remains.')
 save('result.json',result);print(json.dumps(result,indent=2))
try:run()
except BaseException:
 save('failure.json',dict(traceback=traceback.format_exc(),accepted=False));raise
