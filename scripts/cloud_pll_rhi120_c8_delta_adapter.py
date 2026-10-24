#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0
"""Separate delta publication/reader adapter; original native controller is unchanged."""
import ast,copy,hashlib,json,os,re,shutil,subprocess,sys,traceback
from pathlib import Path
import cloud_native_prefix_delta as delta
import cloud_native_sparse_prefix_store as sparse
import cloud_streamed_native_archive as archive
import cloud_pll_rhi120_c8_sparse_io as storage
import cloud_pll_rhi120_c8_sparse_resume as disk
import cloud_pll_rhi120_c8_sparse as native
import cloud_pll_rhi120_c8_completed_stream as completed
import read_pll_rhi120_c8_streamed as wave
import pll_rhi120_c8_native_columns as reference
import pll845_contiguous_columns as contiguous
import run_cloud_pll865_snapshot as pll
from publish_pll_rhi120_c8_sparse_checkpoint import ready
from migrate_outputs_to_cloud import publish
from publish_cloud_results import result_tag
from route_cloud_newer_postcts import fetch

ROOT=Path(__file__).resolve().parents[1]
METHOD='scripts/pll-rhi120-c8-delta-adapter-method.json'
GROUP='pll-rhi120-c8-native-delta'
CAPSULE='cloud-pll-rhi120-c8-native-delta'
READER='cloud-pll-rhi120-c8-delta-review'
WORKFLOW='.github/workflows/pll-rhi120-c8-delta-native-cloud.yml'
BRANCH='codex/complete-open-work'
LAST_DURABLE=dict(run=40001626503,attempt=1,stage='sparse',
 summary_sha256='1f990f8de03976caf21be8592e6584f9b4e6906306133f6b729a171e51534509',
 parts_sha256='ca9a995433ce65fba448e081a5b00e5a012ac3fd829869c553d90f83aad08974')
READY='COMPLETE_NATIVE_DELTA_PUBLISHED_REQUIRES_FULL5106_COLUMN_REVIEW'
def digest(data):return hashlib.sha256(data).hexdigest()
def api(path):return completed.api(path)
def methods():
 record=json.loads((ROOT/METHOD).read_text())
 for path,value in record['protected'].items():assert delta.sha(ROOT/path)==value,path
 current=disk.source_contract(ROOT)[1]
 assert completed.methods()==current
 # Every native completion assertion is byte-for-byte equivalent in AST.
 old=ast.parse((ROOT/'scripts/cloud_pll_rhi120_c8_completed_stream.py').read_text())
 old=next(n for n in old.body if isinstance(n,ast.FunctionDef)and n.name=='completed_gate')
 wanted=[n for n in old.body if 41<=n.lineno<=59]
 new=ast.parse(Path(__file__).read_text())
 new=next(n for n in new.body if isinstance(n,ast.FunctionDef)and n.name=='native_completed_report')
 actual=new.body[:-1]
 assert len(wanted)==len(actual)and all(ast.dump(a,include_attributes=False)==ast.dump(b,include_attributes=False)for a,b in zip(wanted,actual,strict=True))
 return current
def native_completed_report(spec,run,report,current):
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
 return dict(source=source,rows=rows)

def descriptor(spec):
 assert set(spec)=={'run','attempt','stage','transport','summary_sha256','parts_sha256'}
 assert spec['transport']==delta.FORMAT and spec['stage']=='sparse'
 delta.descriptor({k:v for k,v in spec.items()if k!='transport'})
 assert int(spec['attempt'])==1
 return True
def source_url(spec):
 descriptor(spec);stem=GROUP+'-'+str(spec['run'])+'-'+str(spec['attempt'])
 return 'https://github.com/Melihakbulut221/nssoc/releases/download/cloud-results-'+str(spec['run'])+'-'+str(spec['attempt'])+'-'+GROUP+'/',stem
def source_gate(spec,run,report,manifest,current):
 assert spec==LAST_DURABLE,'Only the audited durable same-process source is authorized'
 native.source_gate(run,spec,report)
 assert run['head_branch']==BRANCH and report['source_head']==run['head_sha']
 assert report['run_id']==str(spec['run'])and report['run_attempt']==str(spec['attempt'])and report['stage']==spec['stage']
 disk.verify_resume_methods(report,current)
 assert report['checkpoint_saved']is True and report.get('native_complete')is not True
 source=report['checkpoint_prefix'];sparse.source_contract(source)
 assert source==report['logical_storage_proof'] and source['sha256']==report['outputs'][storage.RAW]
 assert report['native_position']==dict(last_time_s=9.9845671875031e-7,complete_rows=3196464,partial_row_bytes=38144,columns=5106)
 archive.validate_manifest(manifest);url,stem=storage.source_url(spec)
 assert manifest['stem']==stem and manifest['source_directory']=='cloud-pll-rhi120-c8-native'
 published=manifest['verification']['logical_members'][storage.RAW]
 assert {k:published[k]for k in storage.FIELDS}==source and published['original_payload_preserved']is True
 return source
def load_source(directory,current):
 directory=Path(directory);directory.mkdir(exist_ok=False)
 spec=copy.deepcopy(LAST_DURABLE);url,stem=storage.source_url(spec)
 fetch(url+stem+'.summary.json',spec['summary_sha256'],directory/'summary.json')
 fetch(url+stem+'.parts.json',spec['parts_sha256'],directory/'parts.json')
 report=json.loads((directory/'summary.json').read_text());manifest=json.loads((directory/'parts.json').read_text())
 run=api('actions/runs/'+str(spec['run']));source_gate(spec,run,report,manifest,current)
 return spec,report,manifest,url

def bind_capsule(record,report,report_hash,source_report,source_manifest):
 delta.validate(record);source=source_report['checkpoint_prefix']
 assert record['member']==storage.RAW
 assert record['source_descriptor']==report['source_checkpoint']==LAST_DURABLE
 assert record['source']==source
 assert record['plan']==sparse.plan_for(source,2*1024**2,4*1024**2)
 assert record['logical']==report['logical_capture']==report['logical_storage_proof']
 assert source_manifest['verification']['logical_members'][storage.RAW]['sha256']==source['sha256']
 assert record['original_files']['result.json']['sha256']==report_hash
 assert set(record['original_files'])==set(report['outputs'])|{'result.json'},'Missing or untracked native report output'
 for name,expected in report['outputs'].items():assert record['original_files'][name]['sha256']==expected,('Changed native output',name)
 return True

def envelope_gate(spec,run,envelope,manifest,current,source_report,source_manifest):
 descriptor(spec);url,stem=source_url(spec)
 assert run['status']=='completed'and run['conclusion']=='success','Owning native workflow must finish successfully'
 assert str(run['id'])==str(spec['run'])and int(run['run_attempt'])==int(spec['attempt'])==1
 assert run['path']==WORKFLOW and run['head_branch']==BRANCH
 assert envelope['status']==READY and envelope['source_head']==run['head_sha']
 assert envelope['run_id']==str(spec['run'])and envelope['run_attempt']==str(spec['attempt'])
 assert envelope['transport']==delta.FORMAT and envelope['native_outcome']=='success'
 assert envelope['native_controller_unchanged']is True and envelope['full_capture_accepted']is False
 report=envelope['native_report']
 assert report['source_head']==run['head_sha']
 bound=native_completed_report(spec,run,report,current)
 assert envelope['source_checkpoint']==LAST_DURABLE
 assert envelope['capsule_root']==CAPSULE
 bind_capsule(envelope['capsule_contract'],report,envelope['native_report_sha256'],source_report,source_manifest)
 assert re.fullmatch('[0-9a-f]{64}',envelope['capsule_contract_sha256'])
 archive.validate_manifest(manifest)
 assert manifest['stem']==stem and manifest['source_directory']==CAPSULE
 assert envelope['capsule_archive_sha256']==manifest['sha256']
 assert envelope['capsule_archive_bytes']==manifest['bytes']
 return dict(**bound,source_url=url,stem=stem)

def publish_complete():
 assert os.environ.get('GITHUB_ACTIONS')=='true'and os.environ['GITHUB_REF_NAME']==BRANCH
 assert os.environ['GITHUB_RUN_ATTEMPT']=='1'
 current=methods();out=ROOT/'cloud-pll-rhi120-c8-native'
 publication=ROOT/'cloud-pll-rhi120-c8-delta-publication';publication.mkdir(exist_ok=False)
 result=dict(status='RUNNING',source_head=os.environ['GITHUB_SHA'],run_id=os.environ['GITHUB_RUN_ID'],
  run_attempt=os.environ['GITHUB_RUN_ATTEMPT'],transport=delta.FORMAT,
  full_capture_accepted=False,full_phy_accepted=False,native_activation_performed=False)
 tag=result_tag(GROUP,os.environ);stem=GROUP+'-'+result['run_id']+'-'+result['run_attempt']
 def save():(publication/'result.json').write_text(json.dumps(result,indent=2)+'\n')
 save()
 try:
  assert os.environ['NATIVE_OUTCOME']=='success','Failed native execution cannot produce reader readiness'
  raw=(out/'result.json').read_bytes();report=json.loads(raw)
  spec=dict(run=int(result['run_id']),attempt=1,stage='sparse',transport=delta.FORMAT,
   summary_sha256='0'*64,parts_sha256='0'*64)
  native_completed_report(spec,dict(conclusion='success'),report,current)
  assert report['source_head']==result['source_head']
  assert report['source_checkpoint']==LAST_DURABLE
  source_spec,source_report,source_manifest,_=load_source(publication/'immutable-source',current)
  state=storage.state(out)
  assert state['checkpoint']==source_spec and state['source']==source_report['checkpoint_prefix']
  assert state['manifest']==source_manifest
  assert state['plan']==sparse.plan_for(state['source'],2*1024**2,4*1024**2)
  assert storage.native_stopped()
  # The unchanged controller already computed the logical hash. Do not read
  # or republish its 130GB immutable prefix here. Readiness is not acceptance;
  # the completed reader independently verifies every original byte afterward.
  capsule=ROOT/CAPSULE
  record=delta.write_capsule(out,capsule,storage.RAW,source_spec,state['source'],
   state['plan'],report['logical_capture'],storage.native_stopped)
  bind_capsule(record,report,digest(raw),source_report,source_manifest)
  result.update(native_report=report,native_report_sha256=digest(raw),
   native_outcome='success',native_controller_unchanged=True,source_checkpoint=source_spec,
   capsule_root=CAPSULE,capsule_contract=record,capsule_contract_sha256=delta.sha(capsule/delta.CONTRACT))
  save()
  manifest=archive.stream_pack(capsule,stem,ROOT,lambda p:publish(p,tag))
  assert storage.native_stopped()and delta.verify_capsule(capsule)==record
  result.update(status=READY,capsule_archive_sha256=manifest['sha256'],capsule_archive_bytes=manifest['bytes'])
  save()
  summary=ROOT/(stem+'.summary.json');summary.write_bytes((publication/'result.json').read_bytes())
  sr=publish(summary,tag);pr=publish(ROOT/(stem+'.parts.json'),tag)
  assert sr['sha256']==delta.sha(summary)and pr['sha256']==delta.sha(ROOT/(stem+'.parts.json'))
  dispatch=dict(run=int(result['run_id']),attempt=1,stage='sparse',transport=delta.FORMAT,
   summary_sha256=sr['sha256'],parts_sha256=pr['sha256'])
  with open(os.environ['GITHUB_OUTPUT'],'a')as f:
   f.write('reader_ready=true\ncheckpoint='+json.dumps(dispatch,separators=(',',':'))+'\n')
  print(json.dumps(dict(status=result['status'],checkpoint=dispatch,full_capture_accepted=False)),flush=True)
 except BaseException as error:
  result.update(status='FAIL_NATIVE_DELTA_PUBLICATION',error=repr(error),traceback=traceback.format_exc());save()
  failure=ROOT/(stem+'.publication-failure.json');failure.write_bytes((publication/'result.json').read_bytes())
  publish(failure,tag)
  raise

def review_complete():
 assert os.environ.get('GITHUB_ACTIONS')=='true'
 out=ROOT/READER;out.mkdir(exist_ok=False)
 result=dict(status='RUNNING',source_head=os.environ['GITHUB_SHA'],native_activation_performed=False,
  full_capture=False,acquisition_accepted=False,full_device_safety_accepted=False,full_phy_accepted=False,qualified_pex=False)
 def save():(out/'result.json').write_text(json.dumps(result,indent=2)+'\n')
 save()
 try:
  current=methods();result['reader_qualification']=completed.qualification()
  spec=json.loads(os.environ['SOURCE_CHECKPOINT']);descriptor(spec)
  run=api('actions/runs/'+str(spec['run']))
  assert run['status']=='completed'and run['conclusion']=='success','Do not download a live/failed native source'
  inputs=out/'inputs';inputs.mkdir()
  url,stem=source_url(spec)
  fetch(url+stem+'.summary.json',spec['summary_sha256'],inputs/'summary.json')
  fetch(url+stem+'.parts.json',spec['parts_sha256'],inputs/'parts.json')
  envelope=json.loads((inputs/'summary.json').read_text());manifest=json.loads((inputs/'parts.json').read_text())
  oldspec,oldreport,oldmanifest,oldurl=load_source(inputs/'immutable-source',current)
  bound=envelope_gate(spec,run,envelope,manifest,current,oldreport,oldmanifest)
  result.update(source_checkpoint=spec,completed_source_gate=bound)
  def download(row,path):fetch(url+row['name'],row['sha256'],path)
  archive.extract_verified(manifest,inputs/'capsule-parts',inputs/'restored',download)
  capsule=inputs/'restored'/CAPSULE
  assert delta.sha(capsule/delta.CONTRACT)==envelope['capsule_contract_sha256']
  result['restored_native_modes']=delta.restore_capsule_modes(capsule,envelope['capsule_contract'])
  record=delta.verify_capsule(capsule,envelope['capsule_contract'])
  raw=(capsule/'result.json').read_bytes()
  assert digest(raw)==envelope['native_report_sha256']and json.loads(raw)==envelope['native_report']
  bind_capsule(record,envelope['native_report'],digest(raw),oldreport,oldmanifest)
  mem={k:int(v.split()[0])*1024 for k,v in (line.split(':',1)for line in Path('/proc/meminfo').read_text().splitlines())}
  result['capacity']=completed.capacity(shutil.disk_usage(inputs).free,mem['MemAvailable'],bound['source'],oldmanifest['part_limit_bytes'])
  refdir=inputs/'reference';refdir.mkdir();ref=reference.load_reference(refdir)
  assert ref['contract']['required_vectors']==envelope['native_report']['preparation']['vectors']
  names=[row[1]for row in ref['contract']['raw_table']]
  cache=completed.AnalyzerCache(names,bound['rows']);save()
  def olddownload(row,path):fetch(oldurl+row['name'],row['sha256'],path)
  oldchunks=storage.source_member_chunks(oldmanifest,inputs/'original-parts',olddownload,storage.RAW,oldreport['checkpoint_prefix']['bytes'])
  proof={}
  chunks=delta.capture_chunks(capsule,oldchunks,proof,oldspec)
  def consume(start,block):
   cache.append(start,block)
   if start%(wave.original.CHUNK_ROWS*1024)==0:print(json.dumps(dict(provisional_rows=cache.done,full_stream_verified=False)),flush=True)
  got,capture=wave.capture_chunks(chunks,ref['contract'],bound['source'],consume)
  assert proof['complete']and proof['source_iterator_exhausted']and proof['original_payload_preserved']
  assert got==names and capture['rows']==bound['rows']and capture['source_iterator_exhausted']
  data,cache_proof=cache.finish()
  result.update(full_capture=True,capture=capture,analyzer_cache=cache_proof,delta_transport=proof,
   all_original_native_bytes_retained=True,all5106_columns_verified=True)
  save()
  contiguous.analyzer_inputs(ROOT/'scripts/review_pcie_pll_acquisition_v1.py',pll.acquisition_cycle_diagnosis)
  analysis=pll.acquisition_analyzer()(data)
  result['independent_acquisition']=analysis
  result['cycle_diagnosis']=pll.acquisition_cycle_diagnosis(data,analysis)
  result['acquisition_accepted']=bool(analysis['passed'])
  result['status']='PASS_FULL_RHI120_DELTA_CAPTURE_AND_ORIGINAL_ACQUISITION_REQUIRES_DEVICE_PVT_PHY_SIGNOFF'if analysis['passed']else'REJECTED_ORIGINAL_FULL_RHI120_ACQUISITION_GATES'
  assert methods()==current
  assert analysis['passed'],'Original full-duration acquisition gates failed'
 except BaseException as error:
  if result['status']=='RUNNING':result['status']='FAIL_COMPLETED_DELTA_REVIEW'
  result.update(error=repr(error),traceback=traceback.format_exc());raise
 finally:save();print(result['status'],flush=True)

if __name__=='__main__':
 if sys.argv[1:] == ['--publish']:publish_complete()
 elif sys.argv[1:] == ['--review']:review_complete()
 else:raise SystemExit('Choose --publish or --review; no native process is launched by this adapter')
