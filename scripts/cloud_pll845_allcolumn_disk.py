#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0
"""Explicit reader-only migration over the frozen preallocated native controller."""
import copy,hashlib,json,math,struct
from pathlib import Path
import cloud_pll845_compressed_disk as legacy
import read_pll845_all_native_transient as reader
import compare_cloud_routed_endpoints as reports
from run_cloud_tx_layout_repair import fetch,sha
allocation=legacy.allocation;btrfs=legacy.btrfs
ROOT=Path(__file__).resolve().parents[1]
OLD='scripts/cloud_pll845_compressed_acquisition.py'
OLD_HELPER='scripts/cloud_pll845_compressed_disk.py'
CONTROLLER='scripts/cloud_pll845_allcolumn_acquisition.py'
SELF='scripts/cloud_pll845_allcolumn_disk.py'
READER='scripts/read_pll845_all_native_transient.py'
MANIFEST='scripts/pll845-allcolumn-method-delta.json'
CONTRACT_SHA='ee6e0a9d309ce6de9a36ded8184381be8537100b506bd83a0515f1c57ed9e951'
def source_contract(root):
 old_manifest,old=legacy.source_contract(root)
 m=json.loads((root/MANIFEST).read_text());assert m['baseline_method_hashes']==old
 for p,h in m['current_files'].items():assert sha(root/p)==h,p
 text=(root/CONTROLLER).read_text()
 for e in reversed(m['edits']):
  assert text.count(e['after'])==e['count']
  text=text.replace(e['after'],e['before'])
 assert text==(root/OLD).read_text()and sha(root/OLD)==old[OLD]
 current={p:h for p,h in old.items()if p not in (OLD,OLD_HELPER)}
 current.update({p:sha(root/p)for p in (CONTROLLER,SELF,READER)})
 assert len(current)==17
 return m,current
def verify_resume_methods(report,current,root):
 m,expected=source_contract(root);assert current==expected,'Changed candidate methods'
 if report['controller_sha256']==current[CONTROLLER]:
  assert report['method_hashes']==current
  return dict(mode='exact-current-all-column-reader-methods',native_process_methods_unchanged=True)
 proof=legacy.verify_resume_methods(report,m['baseline_method_hashes'],root)
 return dict(mode='explicit-reader-only-migration',baseline=proof,
  native_process_methods_unchanged=True,original_native_columns_retained=True,
  original_acquisition_gates_unchanged=True,reader_contract_sha256=CONTRACT_SHA)
def load_contract(root,vectors=None):
 out=root/'cloud-pll845-allcolumn-reader-proof'
 if not out.exists():
  report,proof=reports.restore_report('pll845-native-reader',39582875018,
   '2d5d2a0acd3817c4cad40519b6d4021b6fe1953f7a638c1982c555b07deae329',
   'c61eea87ccfbdb3c5375ad60172d8d2c1318543f0f84e1e17c1780564ee69533',
   out,['reader-contract.json','header/native-header-prefix.bin'])
 else:
  report=json.loads((out/'result.json').read_text())
 assert sha(out/'result.json')=='2d5d2a0acd3817c4cad40519b6d4021b6fe1953f7a638c1982c555b07deae329'
 assert report['sources_unchanged']and not report['full_capture_accepted']
 assert report['status']=='PASS_REQUIRED1694_PROBES_AND2737_TERMINALS_PRESENT_IN_ACTUAL5106_COLUMN_TABLE_AND_READER_CONTROLS_NOT_FULL_CAPTURE'
 assert len(report['reader_controls']['controls'])==16 and report['reader_controls']['native_prefix']['all5106_columns_bit_exact']
 assert sha(out/'reader-contract.json')==CONTRACT_SHA
 contract=json.loads((out/'reader-contract.json').read_text());reader.contract_check(contract)
 if vectors is not None:assert vectors==contract['required_vectors'],'Prepared physical vector identities changed'
 return contract
def disk_plan(root):return legacy.disk_plan(root)
def raw_position(path):
 contract=load_contract(ROOT)
 with Path(path).open('rb')as f:table,meta=reader.parse(f.read(reader.MAX_HEADER))
 assert table==contract['raw_table']
 size=Path(path).stat().st_size;payload=size-meta['header_bytes'];stride=8*len(table)
 assert payload>=stride
 rows,remainder=divmod(payload,stride)
 with Path(path).open('rb')as f:
  f.seek(meta['header_bytes']+(rows-1)*stride);last=struct.unpack('<d',f.read(8))[0]
 assert math.isfinite(last)and last>=0
 return dict(complete_rows_observed=rows,partial_row_bytes=remainder,last_native_time_s=last,
  columns=len(table),reader_contract_sha256=CONTRACT_SHA,
  full_capture_or_acceptance_proven=False,all_terminal_values_audited=False)
def controls():
 m,current=source_contract(ROOT);previous=legacy.controls()
 contract=load_contract(ROOT);out=ROOT/'cloud-pll845-allcolumn-reader-proof'
 priorpath=out/'actual-prior-checkpoint-summary.json'
 fetch('https://github.com/Melihakbulut221/nssoc/releases/download/cloud-results-39502073954-1-pll845-native-acquisition-continuation/pll845-native-acquisition-continuation-39502073954-1.summary.json',
  '8e7835aa6e763d2d2d225370c4a9132be5f9687941f70176a78f746b1fce6ac1',priorpath)
 prior=json.loads(priorpath.read_text());assert prior['checkpoint_saved']and not prior['full_capture']
 migration=verify_resume_methods(prior,current,ROOT)
 same=dict(controller_sha256=current[CONTROLLER],method_hashes=current)
 assert verify_resume_methods(same,current,ROOT)['mode']=='exact-current-all-column-reader-methods'
 native=next(p for p in current if p.endswith('cloud_native_checkpoint_probe.py'))
 rejected=[]
 for label in ('unknown-controller','changed-native','missing-native','changed-reader','changed-storage','extra-method'):
  wrong=copy.deepcopy(same);actual=dict(current)
  if label=='unknown-controller':wrong['controller_sha256']='0'*64
  elif label=='changed-native':wrong['method_hashes'][native]='f'*64
  elif label=='missing-native':del wrong['method_hashes'][native]
  elif label=='changed-reader':actual[READER]='0'*64
  elif label=='changed-storage':actual['scripts/cloud_pll845_preallocated_storage.py']='0'*64
  else:wrong['method_hashes']['unexpected']='0'*64
  try:verify_resume_methods(wrong,actual,ROOT)
  except AssertionError:rejected.append(label)
  else:raise AssertionError('Accepted method corruption '+label)
 position=raw_position(out/'header/native-header-prefix.bin')
 assert position['complete_rows_observed']==46 and position['partial_row_bytes']==21605
 return dict(original_controls=previous,source_methods=current,actual_prior_migration=migration,
  prior_run=39502073954,rejected=rejected,native_prefix_position=position,
  all_current_methods_bound=True,reader_contract_sha256=CONTRACT_SHA,
  native_activation_performed=False,full_capture_accepted=False,storage_capacity_fixed=False)
