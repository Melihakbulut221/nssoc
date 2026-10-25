#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0
"""Cloud-only complete RHI120 acquisition review; never restart native work."""
import copy,hashlib,json,os,re,shutil,subprocess,sys,traceback
from pathlib import Path
from unittest.mock import patch
import numpy as np
import cloud_pll_rhi120_c8_sparse_io as storage
import cloud_pll_rhi120_c8_sparse_resume as disk
import cloud_streamed_native_archive as archive
import cloud_native_sparse_prefix_store as sparse
import pll_rhi120_c8_native_columns as reference
import read_pll_rhi120_c8_streamed as wave
import pll845_contiguous_columns as contiguous
import run_cloud_pll865_snapshot as pll
from publish_pll_rhi120_c8_sparse_checkpoint import ready,controls as publication_controls
from route_cloud_newer_postcts import fetch
ROOT=Path(__file__).resolve().parents[1]
METHOD='scripts/pll-rhi120-c8-completed-stream-method.json'
GROUP='pll-rhi120-c8-completed-stream'
GIB=1024**3
def sha(data):return hashlib.sha256(data).hexdigest()
def api(path):
 return json.loads(subprocess.check_output(['gh','api','repos/Melihakbulut221/nssoc/'+path]))
def hosted_asset(aid,digest):
 b=subprocess.check_output(['gh','api','repos/Melihakbulut221/nssoc/releases/assets/'+str(aid),'-H','Accept: application/octet-stream'])
 assert sha(b)==digest
 return b
def methods():
 record=json.loads((ROOT/METHOD).read_text())
 for p,h in record['protected'].items():assert sha((ROOT/p).read_bytes())==h,p
 return disk.source_contract(ROOT)[1]
def completed_gate(spec,run,report,manifest,current):
 url,stem=storage.source_url(spec)
 assert spec['stage']=='sparse','Only the qualified sparse terminal publisher is supported'
 assert all(re.fullmatch('[0-9a-f]{64}',spec[k])for k in ('summary_sha256','parts_sha256'))
 assert str(run['id'])==str(spec['run'])and run['run_attempt']==int(spec['attempt'])==1
 assert run['status']=='completed'and run['conclusion']=='success','Source must be terminal and successful'
 assert run['path']=='.github/workflows/pll-rhi120-c8-native-sparse-cloud.yml'
 assert run['head_branch']=='codex/complete-open-work'and report['source_head']==run['head_sha']
 assert ready(report,spec['stage'],str(spec['run']),str(spec['attempt']),run['conclusion'])
 assert report['method_hashes']==current and report['controller_sha256']==current[disk.CONTROLLER]
 assert report['native_startup_readback']==dict(actual_native_devices=102,all_off_readbacks_one=True)
 assert report['exact_native_tables']==dict(exact_transient_table=True,exact_op_table=True,
  case_spelling_pairs=939,collision_free_identity_bijection=True,raw_columns_renamed=False,
  columns=5106,required_terminal_vectors=1694,dropped_columns=0)
 assert report['preparation']['vectors'] and len(report['preparation']['vectors'])==1694
 assert all(report['native_options'][k]==report['preparation']['expected_options'][k]for k in ('backend','numeric','method'))
 op=report['zero_source_operating_point']
 assert op['status']=='PASS_ALL_REQUIRED_TERMINALS_AND_EVERY_NATIVE_ZERO_SOURCE_OP_COLUMN'
 assert op['raw_sha256']==reference.OP_SHA and op['every_column_finite_and_checked']
 assert op['native_columns']==5105 and op['required_terminal_voltages']==1694
 assert len(report['all_native_op_controls'])==12 and all(x['rejected']is True for x in report['all_native_op_controls'])
 source=report['logical_capture'];sparse.source_contract(source)
 assert source==report['logical_storage_proof'] and source['sha256']==report['outputs'][storage.RAW]
 rows,partial=divmod(source['payload_bytes'],5106*8)
 position=report['native_position']
 assert position['columns']==5106 and position['complete_rows']==rows and rows>3000000
 assert position['partial_row_bytes']==partial==0 and abs(position['last_time_s']-1e-6)<1e-15
 archive.validate_manifest(manifest)
 assert manifest['stem']==stem and manifest['source_directory']=='cloud-pll-rhi120-c8-native'
 published=manifest['verification']['logical_members'][storage.RAW]
 assert {k:published[k]for k in storage.FIELDS}==source and published['original_payload_preserved']is True
 return dict(source=source,rows=rows,source_url=url,stem=stem)
def capacity(disk_free,ram_available,source,part_limit):
 rows,partial=divmod(source['payload_bytes'],5106*8)
 assert not partial and rows>1 and part_limit>0
 cache=rows*len(contiguous.REQUIRED)*8
 required_disk=part_limit+4*GIB
 required_ram=2*cache+512*1024**2
 assert disk_free>=required_disk,'Insufficient part staging plus 4GiB reserve'
 assert ram_available>=required_ram,'Insufficient exact analyzer cache memory'
 return dict(ordinary_raw_allocated=False,cache_bytes=cache,required_disk_bytes=required_disk,
  required_ram_bytes=required_ram,free_disk_bytes=disk_free,available_ram_bytes=ram_available)
class AnalyzerCache:
 def __init__(self,names,rows):
  assert len(names)==len(set(names))and set(contiguous.REQUIRED)<=set(names)
  assert type(rows)is int and rows>1
  self.names=names;self.rows=rows;self.done=0;self.indices=[names.index(n)for n in contiguous.REQUIRED]
  self.data={n:np.empty(rows,dtype='<f8')for n in contiguous.REQUIRED}
  self.digest=hashlib.sha256();self.finished=False
 def append(self,start,values):
  assert not self.finished and start==self.done
  assert values.ndim==2 and values.shape[1]==len(self.names)and values.dtype==np.dtype('<f8')
  stop=start+len(values);assert len(values)>0 and stop<=self.rows
  block=np.take(values,self.indices,axis=1);assert np.isfinite(block).all()
  for i,n in enumerate(contiguous.REQUIRED):self.data[n][start:stop]=block[:,i]
  rebuilt=np.column_stack([self.data[n][start:stop]for n in contiguous.REQUIRED])
  assert np.array_equal(block.view('<u8'),rebuilt.view('<u8'))
  self.digest.update(block.tobytes(order='C'));self.done=stop
 def finish(self):
  assert not self.finished and self.done==self.rows
  self.finished=True
  for a in self.data.values():a.flags.writeable=False
  return self.data,dict(rows=self.rows,cached_columns=list(contiguous.REQUIRED),
   cached_bytes=sum(a.nbytes for a in self.data.values()),selected_row_major_binary64_sha256=self.digest.hexdigest(),
   all_cached_sample_bits_checked=True,samples_removed=0,resampled=False,
   scope='Analyzer cache only; full native stream validation and immutable archive retain all5106 columns.')
def qualification():
 run=api('actions/runs/40015445081')
 assert run['status']=='completed'and run['conclusion']=='success'and run['head_sha']=='6d5a834cec479d107fba06e35eaf8a2c9f288ce8'
 assert run['path']=='.github/workflows/pll-rhi120-c8-stream-reader-cloud.yml'
 b=hosted_asset(670234964,'3202871c4f3e6f82dc1c0bf5d735541c59b937ca24d0183850af2eeaa4d5c35e')
 r=json.loads(b)
 assert r['status']=='PASS_ALL5106_STREAM_READER_ORIGINAL16_CONTROLS_AND5_TRANSPORT_GATES_NOT_FULL_CAPTURE'
 assert len(r['original_controls_reproduced']['controls'])==16 and len(r['transport_controls'])==5
 assert r['all_actual_prefix_sample_bits_equal']and r['original_full_capture_assertions_ast_identical']and r['sources_unchanged']
 return dict(run=40015445081,summary_sha256=sha(b))
def controls(current,out):
 # Actual saved source must reject. Positive metadata below is deliberately a
 # synthetic terminal fixture, never a source descriptor authorizing execution.
 spec=dict(run=39967627133,attempt=1,stage='sparse',
  summary_sha256='3ff36c73fdcc52aa4096090d8d156e52e6173da3a837fa38ff5de81a6b0406bb',
  parts_sha256='7bbe164c01ec4680d551aea120807503c137c03a7daf3cccd52130d6afe04b15')
 raw=hosted_asset(669929123,spec['summary_sha256']);part=hosted_asset(669929250,spec['parts_sha256'])
 (out/'actual-saved-summary.json').write_bytes(raw);(out/'actual-saved-parts.json').write_bytes(part)
 saved=json.loads(raw);manifest=json.loads(part)
 run=dict(id=spec['run'],run_attempt=1,status='completed',conclusion='success',
  head_sha=saved['source_head'],head_branch='codex/complete-open-work',
  path='.github/workflows/pll-rhi120-c8-native-sparse-cloud.yml')
 rejected=[]
 try:completed_gate(spec,run,saved,manifest,current)
 except AssertionError:rejected.append('actual486ns-saved-source')
 else:raise AssertionError('Saved source accepted as completed')
 r=copy.deepcopy(saved);m=copy.deepcopy(manifest)
 r.update(status='COMPLETE_RHI120_NATIVE_REQUIRES_ALL_COLUMN_FULL_CAPTURE_REVIEW',native_complete=True,
  native_exitcode=0,full_capture=False,full_capture_reader_pending=True,checkpoint_saved=False,diagnostics=[],
  native_options=copy.deepcopy(r['preparation']['expected_options']))
 n=3200001;source=copy.deepcopy(r['logical_storage_proof'])
 source['payload_bytes']=n*5106*8;source['bytes']=source['header_bytes']+source['payload_bytes']
 r.update(logical_capture=source,logical_storage_proof=copy.deepcopy(source),
  native_position=dict(last_time_s=1e-6,complete_rows=n,partial_row_bytes=0,columns=5106))
 m['verification']['logical_members'][storage.RAW].update(source)
 assert completed_gate(spec,run,r,m,current)['rows']==n
 faults=[
  ('live-run',('run','status'),'in_progress'),('failed-run',('run','conclusion'),'failure'),
  ('wrong-run',('run','id'),1),('wrong-attempt',('run','run_attempt'),2),
  ('wrong-path',('run','path'),'.github/workflows/unqualified.yml'),
  ('wrong-head',('report','source_head'),'0'*40),
  ('wrong-controller',('report','controller_sha256'),'0'*64),
  ('native-exit',('report','native_exitcode'),1),
  ('saved',('report','checkpoint_saved'),True),
  ('prior-changed',('report','prior_payload_unchanged'),False),
  ('input-changed',('report','protected_inputs_unchanged'),False),
  ('warning',('report','diagnostics'),['warning']),
  ('off-readback',('report','native_startup_readback','all_off_readbacks_one'),False),
  ('renamed-table',('report','exact_native_tables','raw_columns_renamed'),True),
  ('solver',('report','native_options','method'),'GEAR'),
  ('op-identity',('report','zero_source_operating_point','raw_sha256'),'0'*64),
  ('short-time',('report','native_position','last_time_s'),9e-7),
  ('partial-row',('report','native_position','partial_row_bytes'),1),
  ('raw-hash',('report','outputs',storage.RAW),'0'*64),
  ('wrong-root',('manifest','source_directory'),'other'),
  ('lost-prefix',('manifest','verification','logical_members',storage.RAW,'original_payload_preserved'),False),
 ]
 for label,path,value in faults:
  x=copy.deepcopy(dict(run=run,report=r,manifest=m));target=x
  for key in path[:-1]:target=target[key]
  target[path[-1]]=value
  try:completed_gate(spec,x['run'],x['report'],x['manifest'],current)
  except AssertionError:rejected.append(label)
  else:raise AssertionError('Accepted terminal-source fault '+label)
 analyze=pll.acquisition_analyzer()
 contiguous.analyzer_inputs(ROOT/'scripts/review_pcie_pll_acquisition_v1.py',pll.acquisition_cycle_diagnosis)
 def cached(names,values,progress=None):
  c=AnalyzerCache(names,len(values))
  for start in range(0,len(values),257):c.append(start,values[start:start+257])
  selected,receipt=c.finish()
  return dict({n:values[:,i]for i,n in enumerate(names)},**selected),receipt
 with patch.object(contiguous,'columns',cached):
  equivalent=contiguous.controls(analyze,pll.acquisition_cycle_diagnosis)
 c=AnalyzerCache(list(contiguous.REQUIRED),3);v=np.zeros((3,8),dtype='<f8')
 cache_faults=[]
 for label,action in [
  ('out-of-order',lambda:c.append(1,v[:1])),
  ('overrun',lambda:c.append(0,np.zeros((4,8),dtype='<f8'))),
  ('incomplete',lambda:c.finish())]:
  try:action()
  except AssertionError:cache_faults.append(label)
  else:raise AssertionError(label)
 c.append(0,v);c.finish()
 try:c.append(3,v[:1])
 except AssertionError:cache_faults.append('append-after-finish')
 else:raise AssertionError('Reused final cache')
 cap=capacity(6*GIB,2*GIB,source,256*1024**2)
 for label,args in [('disk',(4*GIB,2*GIB)),('ram',(6*GIB,512*1024**2))]:
  try:capacity(*args,source,256*1024**2)
  except AssertionError:cache_faults.append('insufficient-'+label)
  else:raise AssertionError(label)
 return dict(source_rejections=rejected,positive_gate='Synthetic terminal metadata only; no native waveform or dispatch',
  original_publication_controls=publication_controls(),analyzer_equivalence=equivalent,
  cache_capacity_controls=cache_faults,capacity=cap,native_started=False,full_capture_accepted=False)
def main():
 assert os.environ.get('GITHUB_ACTIONS')=='true'
 out=ROOT/('cloud-'+GROUP);out.mkdir(exist_ok=False)
 result=dict(status='RUNNING',source_head=os.environ['GITHUB_SHA'],native_activation_performed=False,
  full_capture=False,acquisition_accepted=False,full_device_safety_accepted=False,full_phy_accepted=False,qualified_pex=False)
 def save():(out/'result.json').write_text(json.dumps(result,indent=2)+'\n')
 save()
 try:
  current=methods();result['reader_qualification']=qualification()
  if '--controls'in sys.argv:
   result['controls']=controls(current,out);result['status']='PASS_COMPLETED_SOURCE_AND_EXACT_ANALYZER_CACHE_CONTROLS_NOT_NATIVE_ACCEPTANCE'
   return
  spec=json.loads(os.environ['SOURCE_CHECKPOINT'])
  run=api('actions/runs/'+str(spec['run']))
  assert run['status']=='completed'and run['conclusion']=='success','No archive download for a live or failed source'
  inputs=ROOT/('cloud-'+GROUP+'-input');inputs.mkdir(exist_ok=False)
  url,stem=storage.source_url(spec)
  fetch(url+stem+'.summary.json',spec['summary_sha256'],inputs/'source-summary.json')
  fetch(url+stem+'.parts.json',spec['parts_sha256'],inputs/'source-parts.json')
  report=json.loads((inputs/'source-summary.json').read_text());manifest=json.loads((inputs/'source-parts.json').read_text())
  bound=completed_gate(spec,run,report,manifest,current)
  result.update(source_checkpoint=spec,completed_source_gate=bound)
  mem={k:int(v.split()[0])*1024 for k,v in (line.split(':',1)for line in Path('/proc/meminfo').read_text().splitlines())}
  result['capacity']=capacity(shutil.disk_usage(inputs).free,mem['MemAvailable'],bound['source'],manifest['part_limit_bytes'])
  refdir=inputs/'reference';refdir.mkdir();ref=reference.load_reference(refdir)
  assert ref['contract']['required_vectors']==report['preparation']['vectors']
  names=[row[1]for row in ref['contract']['raw_table']]
  cache=AnalyzerCache(names,bound['rows']);save()
  def download(row,path):fetch(url+row['name'],row['sha256'],path)
  def consume(start,block):
   cache.append(start,block)
   if start%(wave.original.CHUNK_ROWS*1024)==0:print(json.dumps(dict(provisional_rows=cache.done,full_stream_verified=False)),flush=True)
  chunks=storage.source_member_chunks(manifest,inputs/'part-staging',download,storage.RAW,bound['source']['bytes'])
  got,capture=wave.capture_chunks(chunks,ref['contract'],bound['source'],consume)
  assert got==names and capture['rows']==bound['rows']and capture['source_iterator_exhausted']
  data,cache_proof=cache.finish()
  result.update(full_capture=True,capture=capture,analyzer_cache=cache_proof,
   original_release_retains_all_native_bytes=True,all5106_columns_verified=True)
  save()
  contiguous.analyzer_inputs(ROOT/'scripts/review_pcie_pll_acquisition_v1.py',pll.acquisition_cycle_diagnosis)
  analysis=pll.acquisition_analyzer()(data)
  result['independent_acquisition']=analysis
  result['cycle_diagnosis']=pll.acquisition_cycle_diagnosis(data,analysis)
  result['acquisition_accepted']=bool(analysis['passed'])
  result['status']='PASS_FULL_RHI120_CAPTURE_AND_ORIGINAL_ACQUISITION_REQUIRES_DEVICE_PVT_PHY_SIGNOFF'if analysis['passed']else'REJECTED_ORIGINAL_FULL_RHI120_ACQUISITION_GATES'
  assert methods()==current
  assert analysis['passed'],'Original full-duration acquisition gates failed'
 except BaseException as error:
  if result['status']=='RUNNING':result['status']='FAIL_COMPLETED_STREAM_REVIEW'
  result.update(error=repr(error),traceback=traceback.format_exc());raise
 finally:
  save();print(result['status'],flush=True)
if __name__=='__main__':main()
