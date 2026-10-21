#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0
"""Preserve inherited storage evidence and allocate a distinct current-run proof."""
import os,re,tempfile
from pathlib import Path
import cloud_pll845_preallocated_storage as previous
prepare_workspace=previous.prepare_workspace
capacity=previous.capacity
def proof_parent(out,run_id,attempt):
    assert re.fullmatch(r'[1-9][0-9]*',str(run_id))
    assert re.fullmatch(r'[1-9][0-9]*',str(attempt))
    root=Path(out)/'storage-evidence'
    root.mkdir(exist_ok=True)
    assert not root.is_symlink()
    current=root/('run-'+str(run_id)+'-attempt-'+str(attempt))
    current.mkdir(exist_ok=False)
    return current
def capture_ready(case,out,run,prepared):
    parent=proof_parent(out,os.environ['GITHUB_RUN_ID'],os.environ['GITHUB_RUN_ATTEMPT'])
    result=previous.capture_ready(case,parent,run,prepared)
    result['current_proof_directory']=str(parent/'preallocated-storage-proof')
    result['prior_storage_proofs_retained']=True
    return result
def controls():
    baseline=previous.controls()
    with tempfile.TemporaryDirectory()as tmp:
        out=Path(tmp);old=out/'preallocated-storage-proof';old.mkdir()
        sentinel=old/'immutable-prior-proof';sentinel.write_bytes(b'prior evidence')
        first=proof_parent(out,'101','1')
        assert first!=old and sentinel.read_bytes()==b'prior evidence'
        (first/'preallocated-storage-proof').mkdir()
        second=proof_parent(out,'102','1')
        assert second!=first and first.is_dir()and old.is_dir()
        rejects=[]
        for label,run,attempt in [('duplicate','101','1'),('path-traversal','../x','1'),('invalid-attempt','103','0')]:
            try:proof_parent(out,run,attempt)
            except (AssertionError,FileExistsError):rejects.append(label)
            else:raise AssertionError('Unsafe storage-proof namespace accepted')
        assert sentinel.read_bytes()==b'prior evidence'
    return dict(status='PASS_STORAGE_PROOF_NAMESPACE_ONLY',original_storage_controls=baseline,
        rejected=rejects,prior_proofs_preserved=True,native_capacity_or_phy_acceptance=False)
