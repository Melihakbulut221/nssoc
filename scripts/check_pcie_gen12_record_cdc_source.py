#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0
"""Hosted source checks only. This does not compile or qualify either new wrapper."""
import ast
import hashlib
import json
import os
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
METHOD=ROOT/'scripts/pcie-gen12-record-cdc-methods.json'
DIRECT='hw/soc/rtl/pcie/soc_pcie_gen12_record_cdc_v1.v'
COMPOSED='hw/soc/rtl/pcie/soc_pcie_gen12_recovered_records_v1.v'
TESTS={
 'soc_pcie_gen12_record_cdc_v1':[
  'all192_bits_async_wraps','held_all_fields_and_error_flags_are_payload',
  'exact_capacity_overflow_sticky_epoch','resets_held_prefetch_and_startup_stopped_clock',
  'loss_without_valid_and_buffered_prefix','mid_epoch_clock_pause_is_not_loss_detection'],
 'soc_pcie_gen12_recovered_records_v1':[
  'both_polarities_all_offsets_and_errors','first_public_word_and_startup_reset',
  'partial_raw_batch_and_complete_record_epoch_reset','polarity_change_and_known_loss_stop_epoch',
  'composed_capacity_and_common_pause']}

def sha(raw):return hashlib.sha256(raw).hexdigest()

def check():
    method=json.loads(METHOD.read_text())
    assert method['state']=='SOURCE_ONLY_REVIEW_PENDING'
    assert method['cloud_dispatch_authorized'] is False
    assert method['new_wrapper_native_proof'] is False
    for path,h in method['protected'].items():
        assert sha((ROOT/path).read_bytes())==h,path
    proposal=json.loads((ROOT/'scripts/pcie-gen12-record-cdc-proposal.json').read_text())
    for item in proposal['source_reuse']:
        raw=(ROOT/item['path']).read_bytes()
        assert len(raw)==item['bytes'] and sha(raw)==item['sha256'],item['path']
        assert hashlib.sha1(b'blob '+str(len(raw)).encode()+b'\0'+raw).hexdigest()==item['git_blob_sha']
    assert proposal['vendor']['sha256']=='339734a7984d7d540451c92f0831495837c451d170ba60dfbd59f851b28f4250'
    assert method['vendor_compile_copies']==1
    found={}
    for top,wanted in TESTS.items():
        path=ROOT/'hw/soc/tb/cocotb'/('test_'+top+'.py')
        tree=ast.parse(path.read_text())
        actual=[n.name for n in tree.body if isinstance(n,ast.AsyncFunctionDef) and n.decorator_list]
        assert actual==wanted,(top,actual)
        found[top]=actual
    ast.parse((ROOT/'hw/soc/tb/cocotb/pcie_gen12_record_cdc_harness.py').read_text())
    mutations=json.loads((ROOT/'scripts/pcie-gen12-record-cdc-mutations.json').read_text())['mutations']
    assert len(mutations)==18 and len({m['name']for m in mutations})==18
    for m in mutations:
        assert m['path'] in (DIRECT,COMPOSED)
        source=(ROOT/m['path']).read_text()
        assert source.count(m['before'])==1 and m['before']!=m['after'],m['name']
        assert source.replace(m['before'],m['after']).count(m['after'])==1,m['name']
        assert m['test'] in TESTS[Path(m['path']).stem]
    assert sum((ROOT/p).read_text().count('module soc_pcie_gen12_record_cdc_v1 ')for p in (DIRECT,COMPOSED))==1
    assert sum((ROOT/p).read_text().count('module soc_pcie_gen12_recovered_records_v1 ')for p in (DIRECT,COMPOSED))==1
    return dict(status='PASS_SOURCE_IDENTITIES_AND_DECLARED_TEST_STRUCTURE_ONLY',
                protected_count=len(method['protected']),tests=found,mutation_definitions=len(mutations),
                mutations_compiled=False,simulations_executed=False,synthesis_executed=False,
                automatic_clock_loss_detection=False,TS_accepted=False,full_PHY_accepted=False)

if __name__=='__main__':
    assert os.environ.get('GITHUB_ACTIONS')=='true','Hosted source controls only'
    assert os.environ.get('GITHUB_REPOSITORY')=='Melihakbulut221/nssoc'
    print(json.dumps(check(),indent=2))
