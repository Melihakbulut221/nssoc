#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0
"""Bind actual saved PLL raw table to every prepared physical terminal in cloud."""
import json,os,re
from pathlib import Path
import compare_cloud_routed_endpoints as reports
import read_pll845_all_native_transient as reader
from run_cloud_tx_layout_repair import sha
ROOT=Path(__file__).resolve().parents[1];OUT=ROOT/'cloud-pll845-native-reader'
def main():
 assert os.environ.get('GITHUB_ACTIONS')=='true'
 OUT.mkdir();reports.OUT=OUT
 r=dict(status='RUNNING',source_head=os.environ['GITHUB_SHA'],full_capture_accepted=False,full_phy_accepted=False,live_native_process_changed=False)
 def save():(OUT/'result.json').write_text(json.dumps(r,indent=2)+'\n')
 save()
 try:
  observed,headerproof=reports.restore_report('pll845-header-review',39580323368,
   '3a7216a9e65f5ef330395a61cc198ace08f30f8949d2bff09dcc0c0495f500d9',
   '863c7b65a2fd41aabc6dcd8d738edec87ee79290cba9056b9605505c5acc5477',
   OUT/'header',['native-header.txt','native-header-prefix.bin'])
  assert observed['status']=='COMPLETE_ACTUAL_PLL_HEADER_OBSERVATION_ORIGINAL_REJECTION_REPRODUCED'
  prep,prepproof=reports.restore_report('pll845-loaded-preparation',39360285698,
   '858c5f3bf1dd567f137c7397966b34edcc3185edf06ccb1d76f99359b6e6387f',
   '607b2be43604c11ef09c865f0be144dda3bd827ee98d9a31c7bd8713ce3b2979',
   OUT/'prepared',['candidate-circuit.cir','terminal-instrumentation.json','composition/composition.json'])
  assert prep['status']=='PASS_WHOLE_PLL_LOADED_DECK_AND2737_TERMINAL_INSTRUMENTATION_REQUIRES_NATIVE_EXECUTION'and prep['sources_unchanged']
  cov=json.loads((OUT/'prepared/terminal-instrumentation.json').read_text())
  native=json.loads((OUT/'prepared/composition/composition.json').read_text())
  assert native['counts']==dict(devices=845,auxiliary_contacts=4,total_model_instances=849,R=3381,C=5105,MIM=26)
  assert cov['full_native_terminal_coverage']and len(cov['native_terminal_probes'])==2737
  assert len(cov['auxiliary_contact_probes'])==4 and cov['all_original_stimuli_loads_solver_duration_unchanged']
  vectors=cov['vectors'];assert len(vectors)==len(set(vectors))==1694
  deck=(OUT/'prepared/candidate-circuit.cir').read_text()
  assert [s[5:].split()for s in deck.splitlines()if s.startswith('save ')]==[vectors]
  assert deck.count('.tran 3.125e-13 1e-06 0 3.125e-13')==1 and '.options reltol=1e-4 abstol=1e-12 klu'in deck
  assert re.findall(r'(?m)^alter .*\[off\] = 1$',deck)==cov['native_hbt_off_targets']
  header=(OUT/'header/native-header.txt').read_bytes();assert sha(OUT/'header/native-header.txt')=='44cef9ce591b2c6bb87ba9416e78a4da9f233666e0169d2bcb3bd0e469084577'
  table,meta=reader.parse(header);assert meta['columns']==5106
  lookup={x[1]:(int(x[0]),x[2])for x in table}
  r['coverage']={'missing_required_vectors':[v for v in vectors if v not in lookup],
   'wrong_units':[v for v in vectors if v in lookup and lookup[v][1]!='voltage'],
   'required_vectors':1694,'recorded_columns':5106,'additional_recorded_columns':3411,'native_terminal_probes':2737}
  r['header_source']=headerproof;r['prepared_source']=prepproof;save()
  assert not r['coverage']['missing_required_vectors']and not r['coverage']['wrong_units']
  assert all(t['explicit_zero_reference']or t['vector']in vectors for t in cov['native_terminal_probes'])
  contract=dict(source_preparation_run=39360285698,source_preparation_sha256='858c5f3bf1dd567f137c7397966b34edcc3185edf06ccb1d76f99359b6e6387f',
   source_header_run=39580323368,source_header_sha256=sha(OUT/'header/native-header.txt'),
   raw_table=table,raw_table_sha256=reader.digest(table),required_vectors=vectors,required_vectors_sha256=reader.digest(vectors),
   required_vector_indices={v:lookup[v][0]for v in vectors},native_terminal_probes=2737,all_native_terminal_probes_covered=True,
   full_capture_accepted=False,live_native_process_changed=False)
  (OUT/'reader-contract.json').write_text(json.dumps(contract,indent=2)+'\n')
  r['reader_controls']=reader.controls(contract,(OUT/'header/native-header-prefix.bin').read_bytes(),OUT/'controls');save()
  assert all(sha(OUT/'header'/p)==observed['outputs'][p]for p in ['native-header.txt','native-header-prefix.bin'])
  assert all(sha(OUT/'prepared'/p)==prep['outputs'][p]for p in ['candidate-circuit.cir','terminal-instrumentation.json','composition/composition.json'])
  r['status']='PASS_REQUIRED1694_PROBES_AND2737_TERMINALS_PRESENT_IN_ACTUAL5106_COLUMN_TABLE_AND_READER_CONTROLS_NOT_FULL_CAPTURE'
  r['sources_unchanged']=True
 except BaseException as e:r.update(status='FAIL_OR_ERROR',error=repr(e));raise
 finally:
  r['outputs']={str(p.relative_to(OUT)):sha(p)for p in OUT.rglob('*')if p.is_file()and p!=OUT/'result.json'};save()
if __name__=='__main__':main()
