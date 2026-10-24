#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0
"""Cloud-only adapter gates and real all-column partial-row transport controls."""
import ast,copy,hashlib,json,os,shutil,tempfile,traceback
import cloud_streamed_native_archive as archive
from pathlib import Path
import numpy as np
import cloud_pll_rhi120_c8_delta_adapter as adapter
import check_pll_lossless_prefix_delta as base
import cloud_native_prefix_delta as delta
import cloud_native_sparse_prefix_store as sparse
import read_pll_rhi120_c8_streamed as wave
import pll_rhi120_c8_native_columns as reference
ROOT=Path(__file__).resolve().parents[1]
OUT=ROOT/'cloud-pll-rhi120-c8-delta-adapter-controls'
def reject(fn):
 try:fn()
 except (AssertionError,KeyError,FileNotFoundError):return
 raise AssertionError('Unsafe adapter evidence accepted')
def actual_fixture(root,old,current):
 source=base.raw_contract(old);logical=base.raw_contract(current)
 native=root/'native';(native/'case/empty').mkdir(parents=True)
 (native/'case/empty').chmod(0o750)
 (native/'case/private-empty').mkdir();(native/'case/private-empty').chmod(0o700)
 for name,mode in [('readonly.model',0o444),('native-executable',0o555),('private-helper',0o700)]:
  p=native/'case'/name;p.write_bytes(('Exact original '+name+' bytes').encode());p.chmod(mode)
 raw=native/base.MEMBER
 plan=sparse.materialize(raw,base.chunks(old),source,2*1024**2,4*1024**2)
 with raw.open('r+b')as f:
  f.write(current[:source['header_bytes']]);f.seek(len(old));f.write(current[len(old):])
 (native/'result.json').write_text('{"explicit_short_fixture":true}\n')
 capsule=root/'capsule'
 record=delta.write_capsule(native,capsule,base.MEMBER,adapter.LAST_DURABLE,
  source,plan,logical,lambda:True)
 assert record['original_directories']['case/empty']==0o750
 assert (capsule/'case/empty').is_dir()
 return capsule,record,native
def envelope_fixture(saved,current,oldmanifest):
 # Positive gate metadata is deliberately synthetic; never a native artifact or dispatch.
 report=copy.deepcopy(saved);run=dict(id=991,run_attempt=1,status='completed',conclusion='success',
  path=adapter.WORKFLOW,head_branch=adapter.BRANCH,head_sha='a'*40)
 spec=dict(run=991,attempt=1,stage='sparse',transport=delta.FORMAT,
  summary_sha256='b'*64,parts_sha256='c'*64)
 source=copy.deepcopy(saved['checkpoint_prefix']);logical=copy.deepcopy(source);rows=3201408
 logical.update(bytes=source['header_bytes']+rows*5106*8,payload_bytes=rows*5106*8,
  sha256='d'*64,payload_sha256='e'*64)
 report.update(run_id='991',run_attempt='1',source_head=run['head_sha'],source_checkpoint=adapter.LAST_DURABLE,
  status='COMPLETE_RHI120_NATIVE_REQUIRES_ALL_COLUMN_FULL_CAPTURE_REVIEW',
  native_complete=True,native_exitcode=0,full_capture=False,full_capture_reader_pending=True,
  checkpoint_saved=False,diagnostics=[],native_options=copy.deepcopy(saved['preparation']['expected_options']),
  logical_capture=logical,logical_storage_proof=copy.deepcopy(logical),
  native_position=dict(columns=5106,complete_rows=rows,partial_row_bytes=0,last_time_s=1e-6))
 report['outputs'][base.MEMBER]=logical['sha256']
 report_hash=adapter.digest(json.dumps(report,sort_keys=True).encode())
 inventory={}
 for name,value in report['outputs'].items():
  row=oldmanifest['verification']['regular_files'].get(name,{})
  inventory[name]=dict(sha256=value,bytes=logical['bytes']if name==base.MEMBER else row.get('bytes',0),mode=0o644)
 inventory['result.json']=dict(sha256=report_hash,bytes=1,mode=0o644)
 dirs={'.':0o755}
 for name in inventory:
  for parent in Path(name).parents:
   if str(parent)!='.':dirs[parent.as_posix()]=0o755
 plan=sparse.plan_for(source,2*1024**2,4*1024**2)
 record=dict(format=delta.FORMAT,member=base.MEMBER,source_descriptor=adapter.LAST_DURABLE,
  source=source,plan=plan,logical=logical,
  extents=[dict(name=delta.META+'/head.bin',start=0,stop=plan['hole_start'],bytes=plan['hole_start'],sha256='1'*64),
   dict(name=delta.META+'/tail.bin',start=plan['hole_stop'],stop=logical['bytes'],bytes=logical['bytes']-plan['hole_stop'],sha256='2'*64)],
  original_files=inventory,original_directories=dirs,transport_only=True,native_activation_qualified=False,full_capture_accepted=False)
 manifest=copy.deepcopy(oldmanifest);_,stem=adapter.source_url(spec)
 manifest.update(stem=stem,source_directory=adapter.CAPSULE)
 for p in manifest['parts']:p['name']=stem+'.tar.gz.part'+str(p['index']).zfill(4)
 envelope=dict(status=adapter.READY,source_head=run['head_sha'],run_id='991',run_attempt='1',
  transport=delta.FORMAT,native_outcome='success',native_controller_unchanged=True,
  full_capture_accepted=False,native_report=report,native_report_sha256=report_hash,
  source_checkpoint=adapter.LAST_DURABLE,capsule_root=adapter.CAPSULE,capsule_contract=record,
  capsule_contract_sha256='f'*64,capsule_archive_sha256=manifest['sha256'],capsule_archive_bytes=manifest['bytes'])
 return dict(spec=spec,run=run,envelope=envelope,manifest=manifest)
def metadata_controls(saved,oldmanifest,current):
 good=envelope_fixture(saved,current,oldmanifest)
 adapter.envelope_gate(**good,current=current,source_report=saved,source_manifest=oldmanifest)
 failures=[]
 def fault(name,path,value):
  bad=copy.deepcopy(good);node=bad
  for key in path[:-1]:node=node[key]
  node[path[-1]]=value
  reject(lambda:adapter.envelope_gate(**bad,current=current,source_report=saved,source_manifest=oldmanifest));failures.append(name)
 for name,path,value in [
  ('live-workflow',('run','status'),'in_progress'),('failed-workflow',('run','conclusion'),'failure'),
  ('wrong-workflow',('run','path'),'.github/workflows/pll-rhi120-c8-native-sparse-cloud.yml'),
  ('wrong-branch',('run','head_branch'),'other'),('wrong-owner-run',('run','id'),992),
  ('rerun-attempt',('run','run_attempt'),2),('wrong-head',('envelope','source_head'),'0'*40),
  ('wrong-report-head',('envelope','native_report','source_head'),'0'*40),
  ('failed-native-step',('envelope','native_outcome'),'failure'),
  ('changed-controller-claim',('envelope','native_controller_unchanged'),False),
  ('premature-capture-claim',('envelope','full_capture_accepted'),True),
  ('changed-controller',('envelope','native_report','controller_sha256'),'0'*64),
  ('wrong-native-owner',('envelope','native_report','run_id'),'992'),
  ('saved-not-completed',('envelope','native_report','checkpoint_saved'),True),
  ('nonzero-native-exit',('envelope','native_report','native_exitcode'),1),
  ('diagnostic-present',('envelope','native_report','diagnostics'),['warning']),
  ('changed-prior-payload',('envelope','native_report','prior_payload_unchanged'),False),
  ('changed-protected-input',('envelope','native_report','protected_inputs_unchanged'),False),
  ('missing-native-column',('envelope','native_report','exact_native_tables','columns'),5105),
  ('changed-native-method',('envelope','native_report','native_options','method'),'other'),
  ('wrong-last-time',('envelope','native_report','native_position','last_time_s'),9e-7),
  ('partial-final-row',('envelope','native_report','native_position','partial_row_bytes'),8),
  ('wrong-prefix-descriptor',('envelope','source_checkpoint','run'),1),
  ('wrong-raw-member',('envelope','capsule_contract','member'),'case/other.raw'),
  ('wrong-prefix-bytes',('envelope','capsule_contract','source','sha256'),'3'*64),
  ('wrong-prefix-plan',('envelope','capsule_contract','plan','hole_start'),0),
  ('wrong-logical-capture',('envelope','capsule_contract','logical','sha256'),'4'*64),
  ('wrong-report-file-hash',('envelope','native_report_sha256'),'5'*64),
  ('wrong-auxiliary-native-hash',('envelope','capsule_contract','original_files','case/op.raw','sha256'),'6'*64),
  ('wrong-capsule-root',('envelope','capsule_root'),'cloud-other'),
  ('wrong-capsule-archive-hash',('envelope','capsule_archive_sha256'),'7'*64),
  ('wrong-capsule-archive-size',('envelope','capsule_archive_bytes'),1),
  ('wrong-transport',('spec','transport'),'ordinary-full-raw'),
 ]:fault(name,path,value)
 reject(lambda:adapter.native_completed_report(good['spec'],good['run'],saved,current))
 failures.append('actual-saved-source-rejected-as-completed')
 bad=copy.deepcopy(good)
 changed=bad['envelope']['capsule_contract'];changed['source']['sha256']='8'*64
 changed['plan']['source']['sha256']='8'*64
 delta.validate(changed)
 reject(lambda:adapter.envelope_gate(**bad,current=current,source_report=saved,source_manifest=oldmanifest))
 failures.append('internally-consistent-unrelated-prefix-rejected-by-independent-source-binding')
 assert len(failures)==35
 return dict(positive='Synthetic terminal metadata only; never native acceptance',negative_controls=failures)
def main():
 assert os.environ.get('GITHUB_ACTIONS')=='true'
 OUT.mkdir(exist_ok=False);result=dict(status='RUNNING',source_head=os.environ['GITHUB_SHA'],
  native_activation_performed=False,full_capture_accepted=False,full_phy_accepted=False)
 def save():(OUT/'result.json').write_text(json.dumps(result,indent=2)+'\n')
 save()
 try:
  current=adapter.methods()
  scratch=Path(tempfile.mkdtemp(prefix='nssoc-delta-adapter-',dir=os.environ['RUNNER_TEMP']))
  spec,saved,manifest,_=adapter.load_source(scratch/'source',current)
  result['metadata_controls']=metadata_controls(saved,manifest,current)
  fixture=scratch/'fixture-input';fixture.mkdir()
  old,current_raw,provenance=base.actual_native_fixture(fixture)
  # Match the real durable source's38144byte incomplete row without truncating
  # the completed512row current fixture; all sample bytes remain native.
  old=old+current_raw[len(old):len(old)+38144]
  assert (len(old)-base.raw_contract(old)['header_bytes'])%(5106*8)==38144
  actual=scratch/'actual';actual.mkdir();capsule,record,native=actual_fixture(actual,old,current_raw)
  pack=actual/'packed';pack.mkdir();hosted={}
  def send(path):
   target=actual/('hosted-'+path.name);shutil.copyfile(path,target);hosted[path.name]=target
   return dict(name=path.name,bytes=target.stat().st_size,sha256=delta.sha(target))
  packed=archive.stream_pack(capsule,'adapter-mode-roundtrip',pack,send,part_bytes=2*1024**2)
  def download(row,path):shutil.copyfile(hosted[row['name']],path)
  restored=actual/'restored';archive.extract_verified(packed,actual/'parts',restored,download)
  roundcapsule=restored/'capsule'
  reject(lambda:delta.verify_capsule(roundcapsule))
  before_modes={n:p.stat().st_mode for n,p in delta.files(roundcapsule).items()}
  badfile=roundcapsule/'case/readonly.model';original=badfile.read_bytes();badfile.write_bytes(original+b'corrupt')
  reject(lambda:delta.restore_capsule_modes(roundcapsule,record))
  assert {n:p.stat().st_mode for n,p in delta.files(roundcapsule).items()}==before_modes
  badfile.write_bytes(original)
  wrong=copy.deepcopy(record);wrong['original_directories']['case/empty']=0o777
  reject(lambda:delta.restore_capsule_modes(roundcapsule,wrong))
  modes=delta.restore_capsule_modes(roundcapsule,record)
  assert {'case/empty','case/private-empty'}<=set(modes['restored_directory_modes'])
  assert {'case/readonly.model','case/native-executable'}<=set(modes['restored_file_modes'])
  assert modes['exact_native_modes_restored']
  result['production_archive_mode_roundtrip']=dict(mode_restoration=modes,
   rejected_unrestored_modes=True,rejected_corrupted_contents_before_any_chmod=True,
   rejected_unbound_contract=True,original_private_and_empty_dirs_preserved=True,
   original_readonly_and_executable_modes_preserved=True)
  capsule=roundcapsule
  refdir=scratch/'reference';refdir.mkdir();ref=reference.load_reference(refdir)
  proof={};received=[]
  names,meta=wave.read_chunks(delta.capture_chunks(capsule,base.chunks(old),proof,spec),
   ref['contract'],record['logical'],lambda start,block:received.append(block.copy()))
  expected=np.frombuffer(current_raw[record['logical']['header_bytes']:],dtype='<u8').reshape(512,5106)
  rebuilt=np.concatenate(received).view('<u8')
  assert proof['complete']and np.array_equal(expected,rebuilt)
  assert meta['all_recorded_columns_checked']==5106 and meta['rows']==512
  reject(lambda:wave.full_capture(meta))
  result['partial_row_and_header_update']=dict(prior_partial_row_bytes=38144,rows=512,columns=5106,
   binary64_samples=512*5106,all_native_bits_equal=True,transport=proof,
   full_duration_gate_rejected_short_capture=True,provenance=provenance)
  faults=[]
  original_contract=(capsule/delta.CONTRACT).read_bytes()
  head_path=capsule/record['extents'][0]['name'];head=head_path.read_bytes()
  def header_fault(label,change):
   changed=change(current_raw)
   assert len(changed)==len(current_raw)and changed!=current_raw
   bad=copy.deepcopy(record);bad['logical']=base.raw_contract(changed)
   bad['original_files'][base.MEMBER]['sha256']=bad['logical']['sha256']
   newhead=changed[:len(head)];head_path.write_bytes(newhead)
   bad['extents'][0]['sha256']=base.sha(newhead)
   (capsule/delta.CONTRACT).write_text(json.dumps(bad))
   # Transport must accept a self-consistent same-length header update; the
   # unchanged native semantic reader must reject its flags/table/point lie.
   check={};assert b''.join(delta.capture_chunks(capsule,base.chunks(old),check,spec))==changed and check['complete']
   try:
    p={}
    reject(lambda:wave.read_chunks(delta.capture_chunks(capsule,base.chunks(old),p,spec),ref['contract'],bad['logical']))
    faults.append(label)
   finally:head_path.write_bytes(head);(capsule/delta.CONTRACT).write_bytes(original_contract)
  header_fault('changed-real-flags',lambda b:b.replace(b'Flags: real',b'Flags: comp',1))
  table,_=wave.original.parse(current_raw[:wave.original.MAX_HEADER])
  variable=table[1][1].encode();replacement=(b'z'if variable[:1]!=b'z'else b'q')+variable[1:]
  header_fault('changed-native-column-identity',lambda b:b.replace(variable,replacement,1))
  def wrong_points(b):
   import re
   m=re.search(rb'(?m)^(No. Points:)([^\n]*)$',b[:record['logical']['header_bytes']]);assert m
   replacement=m[1]+b' '+b'511'.rjust(len(m[2])-1,b'0')
   return b[:m.start()]+replacement+b[m.end():]
  header_fault('wrong-header-point-count',wrong_points)
  empty=capsule/'case/empty';empty.chmod(0o700)
  try:reject(lambda:delta.verify_capsule(capsule));faults.append('changed-empty-directory-mode')
  finally:empty.chmod(0o750)
  empty.rmdir()
  try:reject(lambda:delta.verify_capsule(capsule));faults.append('missing-empty-directory')
  finally:empty.mkdir();empty.chmod(0o750)
  link=native/'case/native-link';link.symlink_to('empty')
  try:
   reject(lambda:delta.write_capsule(native,actual/'symlink-reject',base.MEMBER,spec,
    record['source'],record['plan'],record['logical'],lambda:True));faults.append('native-symlink-fails-closed')
  finally:link.unlink()
  assert len(faults)==6
  result['semantic_and_directory_controls']=faults
  # Existing unchanged analyzer source is the compatibility proof, not a new
  # replacement algorithm. The original assertion body is checked by methods().
  assert adapter.methods()==current
  result.update(status='PASS_DELTA_ADAPTER_ORIGINAL_NATIVE_GATES_PARTIAL_ROW_ALL5106_COLUMNS_AND44_REJECTIONS_NOT_NATIVE_ACCEPTANCE',
   original_native_assertions_ast_identical=True,protected_controller_reader_analyzer_unchanged=True,
   source_bindings_verified=True,native_workflow_dispatched=False,sources_unchanged=True)
 except BaseException as error:
  result.update(status='FAIL_DELTA_ADAPTER_CONTROLS',error=repr(error),traceback=traceback.format_exc());raise
 finally:save();print(result['status'],flush=True)
if __name__=='__main__':main()
