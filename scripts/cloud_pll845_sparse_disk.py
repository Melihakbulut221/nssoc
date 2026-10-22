#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0
"""Explicit sparse-storage migration; native process and original gates stay pinned."""
import copy,json
from pathlib import Path
import cloud_pll845_proof_namespace_disk as previous
from run_cloud_tx_layout_repair import sha,fetch
ROOT=Path(__file__).resolve().parents[1]
OLD='scripts/cloud_pll845_proof_namespace_acquisition.py'
OLD_HELPER='scripts/cloud_pll845_proof_namespace_disk.py'
CONTROLLER='scripts/cloud_pll845_sparse_acquisition.py'
SELF='scripts/cloud_pll845_sparse_disk.py'
MANIFEST='scripts/pll845-sparse-method-delta.json'
EXTRA=(CONTROLLER,SELF,'scripts/cloud_pll845_sparse_io.py',
 'scripts/cloud_logical_native_archive.py','scripts/cloud_native_sparse_prefix_store.py',
 'scripts/publish_pll845_sparse_checkpoint.py','scripts/read_pll845_sparse_completed.py',
 'scripts/pll845-source-publication-reconciliation.json')
allocation=previous.allocation
btrfs=previous.btrfs
load_contract=previous.load_contract
disk_plan=previous.disk_plan
raw_position=previous.raw_position
def source_contract(root):
    _,old=previous.source_contract(root);m=json.loads((root/MANIFEST).read_text())
    assert m['baseline_method_hashes']==old
    for p,h in m['current_files'].items():assert sha(root/p)==h,p
    text=(root/OLD).read_text()
    for e in m['edits']:
        assert text.count(e['before'])==e['count'];text=text.replace(e['before'],e['after'])
    assert text==(root/CONTROLLER).read_text(),'Unexpected production controller change'
    current={p:h for p,h in old.items()if p not in (OLD,OLD_HELPER)}
    current.update({p:sha(root/p)for p in EXTRA})
    assert len(current)==24
    return m,current
def verify_resume_methods(report,current,root):
    m,expected=source_contract(root);assert current==expected
    if report['controller_sha256']==current[CONTROLLER]:
        assert report['method_hashes']==current
        return dict(mode='exact-sparse-ordinary-archive-methods',native_process_methods_unchanged=True)
    proof=previous.verify_resume_methods(report,m['baseline_method_hashes'],root)
    return dict(mode='explicit-qualified-sparse-working-file-and-ordinary-archive-migration',
        baseline=proof,native_process_methods_unchanged=True,original_native_columns_retained=True,
        original_solver_loads_stimuli_duration_unchanged=True,original_reader_and_acquisition_gates_retained=True,
        full_reader_deferred_to_ordinary_complete_waveform=True)
def controls():
    m,current=source_contract(ROOT);base=previous.controls()
    path=ROOT/'cloud-pll845-allcolumn-reader-proof'/'actual-sparse-source-summary.json'
    fetch('https://github.com/Melihakbulut221/nssoc/releases/download/cloud-results-39674830790-1-pll845-native-acquisition-initial/pll845-native-acquisition-initial-39674830790-1.summary.json',
        '95f6e3053f2484af8ba2eab954b6d5f3536cc20898226a8f5c95f0f81df0b243',path)
    prior=json.loads(path.read_text())
    assert prior['checkpoint_saved']and not prior['full_capture']
    migration=verify_resume_methods(prior,current,ROOT)
    same=dict(controller_sha256=current[CONTROLLER],method_hashes=current)
    assert verify_resume_methods(same,current,ROOT)['mode']=='exact-sparse-ordinary-archive-methods'
    rejected=[]
    for label in ('unknown-controller','changed-native','missing-native','changed-old-storage','changed-new-storage','extra-method'):
        bad=copy.deepcopy(same)
        if label=='unknown-controller':bad['controller_sha256']='0'*64
        elif label=='changed-native':bad['method_hashes']['scripts/cloud_native_checkpoint_probe.py']='0'*64
        elif label=='missing-native':del bad['method_hashes']['scripts/cloud_native_checkpoint_probe.py']
        elif label=='changed-old-storage':bad['method_hashes']['scripts/cloud_pll845_preallocated_storage.py']='0'*64
        elif label=='changed-new-storage':bad['method_hashes']['scripts/cloud_pll845_sparse_io.py']='0'*64
        else:bad['method_hashes']['unexpected']='0'*64
        try:verify_resume_methods(bad,current,ROOT)
        except AssertionError:rejected.append(label)
        else:raise AssertionError('Changed native resume methods accepted: '+label)
    return dict(original_controls=base,actual_prior_migration=migration,prior_run=39674830790,
        rejected=rejected,source_methods=current,native_activation_performed=False,full_capture_accepted=False)
