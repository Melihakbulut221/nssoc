#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0
"""Require unchanged bounded physical circuit, native oracle and existing gates."""
import ast,hashlib,json,re
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
def sha(b):return hashlib.sha256(b).hexdigest()
def check():
    manifest=json.loads((ROOT/'scripts/native-sparse-prefix-checkpoint-delta.json').read_text())
    before=(ROOT/manifest['baseline_path']).read_bytes()
    after=(ROOT/manifest['candidate_path']).read_bytes()
    assert sha(before)==manifest['baseline_sha256']
    expected=before.decode()
    for e in manifest['edits']:
        assert expected.count(e['before'])==e['count']
        expected=expected.replace(e['before'],e['after'])
    assert expected.encode()==after and sha(after)==manifest['candidate_sha256']
    assert re.findall(r'[0-9a-f]{64}',before.decode())==re.findall(r'[0-9a-f]{64}',after.decode())
    for name in ('prepare','inspect_capture','verify'):
        a=[n for n in ast.parse(before).body if isinstance(n,ast.FunctionDef)and n.name==name]
        b=[n for n in ast.parse(after).body if isinstance(n,ast.FunctionDef)and n.name==name]
        assert len(a)==len(b)==1 and ast.dump(a[0])==ast.dump(b[0]),name
    for p,digest in manifest['pins'].items():assert sha((ROOT/p).read_bytes())==digest,p
    receipt=json.loads((ROOT/'docs/evidence/native-sparse-prefix-fixtures-pass-20261022.json').read_text())
    assert receipt['run']==39712609867 and receipt['source_head']=='7b1080abc155958b956939c163bb29f1777b4319'
    assert set(receipt['filesystems'])=={'ext4','btrfs'}
    for fs,item in receipt['filesystems'].items():
        r=item['report']
        assert r['status']=='PASS_LOSSLESS_SPARSE_PREFIX_FIXTURE_AND16_CORRUPTIONS_NOT_NATIVE_QUALIFICATION'
        assert len(r['negative_controls'])==16 and r['immutable_source_unchanged']and r['complete_logical_bytes_equal_oracle']
        assert json.loads(r['filesystem'])['filesystems'][0]['fstype']==fs
        assert r['source_sha256']==manifest['pins']['scripts/cloud_native_sparse_prefix_store.py']
    print('PASS_FROZEN_NATIVE845_BOUNDED_ORACLE_AND_SPARSE_FIXTURE_BINDING_NOT_RUNTIME_ACCEPTANCE')
if __name__=='__main__':check()
