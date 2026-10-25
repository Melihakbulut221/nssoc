#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0
"""Verify lossless cloud storage against the exact archived RHI120 native prefix.

This job never starts/restores a simulator. The working sparse file is never
passed to a waveform reader. Ordinary logical bytes come from the immutable
source archive plus retained working bytes, verified in full.
"""
import hashlib,json,os,subprocess,tempfile,traceback
from pathlib import Path
import cloud_pll_rhi120_c8_sparse_io as storage
from route_cloud_newer_postcts import fetch
ROOT=Path(__file__).resolve().parents[1]
OUT=ROOT/'cloud-pll-rhi120-c8-sparse-qualification'
SPEC=dict(run=39925042125,attempt=1,stage='initial',
 summary_sha256='74033b131a40f5009565b1dd6e219f1b6748f555f750b1c715ebbc77ad93be8d',
 parts_sha256='bf1b8dcc19d1b8b31eb6934537f0efe728e7f8a6fd5060d1e1334d22627d436d')
def api(p):
 return json.loads(subprocess.check_output(['gh','api','repos/Melihakbulut221/nssoc/'+p]))
def main():
 assert os.environ.get('GITHUB_ACTIONS')=='true'
 assert os.environ['GITHUB_RUN_ATTEMPT']=='1'
 OUT.mkdir(exist_ok=False)
 r=dict(status='RUNNING',source_head=os.environ['GITHUB_SHA'],source_checkpoint=SPEC,
   native_activation_performed=False,native_resume_qualified=False,full_capture=False,
   acquisition_accepted=False,full_phy_accepted=False)
 def save():(OUT/'result.json').write_text(json.dumps(r,indent=2)+'\n')
 save()
 try:
  from check_pll_rhi120_c8_sparse_sources import check
  methods=check();r['method_hashes']=methods
  with tempfile.TemporaryDirectory(prefix='rhi120-sparse-fixture-')as temp:
   r['controls']=storage.sparse.controls(Path(temp)/'controls')
  assert len(r['controls']['negative_controls'])==16
  live=api('actions/runs/'+str(SPEC['run']))
  assert live['status']=='completed'and live['conclusion']=='failure'
  assert live['run_attempt']==1 and live['head_sha']=='ece94d479509de8fda3ac37ef4f0a4d9856aef85'
  audit=api('actions/runs/39937306316')
  assert audit['status']=='completed'and audit['conclusion']=='success'
  assert audit['head_sha']=='3096cdb182190ed6572e1705c1e0feb2bb9553bf'
  url,stem=storage.source_url(SPEC)
  fetch(url+stem+'.summary.json',SPEC['summary_sha256'],OUT/'source-summary.json')
  fetch(url+stem+'.parts.json',SPEC['parts_sha256'],OUT/'source-parts.json')
  prior=json.loads((OUT/'source-summary.json').read_text());manifest=json.loads((OUT/'source-parts.json').read_text())
  assert prior['status']=='FAIL_OR_ERROR'and prior['error']=='AssertionError()'
  assert prior['checkpoint_saved']and not prior['full_capture']
  assert prior['checkpoint_prefix']['sha256']=='2dd133ea5eb78a7a7d87a5836612bd135f20fa1da32fb7a2a6331d71ce89f166'
  assert prior['checkpoint_prefix']['bytes']==25342824379
  assert manifest['bytes']==23042563898 and manifest['sha256']=='b86cd5fab060d1e7600956defd30aaf22fb858ffc85304a4b77531fd2c6cf8e2'
  assert len(manifest['parts'])==22 and manifest['source_directory']=='cloud-pll-rhi120-c8-native'
  root=ROOT/'rhi120-sparse-source-verification';root.mkdir(exist_ok=False)
  source=root/manifest['source_directory']
  def download(part,path):fetch(url+part['name'],part['sha256'],path)
  r['status']='VERIFYING_ENTIRE_IMMUTABLE_SOURCE_AND_SPARSE_RESTORE';save()
  restored=storage.restore(manifest,root/'part-staging',root,download,prior,SPEC,url,source)
  assert restored['logical_source_stays_immutable']and restored['ordinary_full_raw_not_allocated']
  assert restored['metadata_reconciliation']['applied']is False
  r['restored_source']=restored;r['status']='VERIFYING_EVERY_LOGICAL_NATIVE_BYTE_FROM_IMMUTABLE_ARCHIVE';save()
  proof=storage.snapshot(source)
  assert {k:proof[k]for k in storage.FIELDS}==prior['checkpoint_prefix']
  assert proof['original_payload_preserved']
  raw=source/storage.RAW
  allocated=raw.stat().st_blocks*512
  assert allocated<16*1024**2 and raw.stat().st_size==25342824379
  assert storage.native_stopped()
  state=storage.state(source)
  r['verified_source_member_count']=len(prior['outputs'])
  r['logical_proof']=proof;r['physical_working_allocation_bytes']=allocated
  r['sparse_source_state']=state
  assert methods==check(),'Source methods changed during qualification'
  r.update(status='PASS_EXACT_RHI120_ARCHIVED_PREFIX_LOSSLESS_SPARSE_STORAGE_NOT_NATIVE_RESUME_OR_CAPTURE_ACCEPTANCE',
    all_recorded_source_members_verified=True,all_ordered_archive_bytes_verified=True,
    complete_logical_raw_and_payload_hashes_match=True,original_failed_source_preserved=True,
    working_sparse_file_not_waveform=True,
    next_action='Qualify an explicit production-controller/storage/publication migration against the latest completed RHI120 process, retaining exact methods/columns/runtime. Do not restart or migrate the currently live process. Never give sparse working bytes to the complete waveform reader.')
 except BaseException as error:
  r.update(status='FAIL_RHI120_SPARSE_STORAGE_QUALIFICATION',error=repr(error),traceback=traceback.format_exc());raise
 finally:
  save();print(json.dumps({k:r[k]for k in ('status','native_activation_performed','full_capture','full_phy_accepted')}),flush=True)
if __name__=='__main__':main()
