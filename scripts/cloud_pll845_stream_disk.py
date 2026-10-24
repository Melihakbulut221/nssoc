#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0
"""Strict reversible storage migration; no native equation, probe or acceptance change."""
import copy,hashlib,json
from pathlib import Path
GIB=1024**3
OLD='scripts/cloud_pll845_native_acquisition.py'
OLD_HELPER='scripts/cloud_pll845_disk_budget.py'
CONTROLLER='scripts/cloud_pll845_streamed_acquisition.py'
SELF='scripts/cloud_pll845_stream_disk.py'
ARCHIVE='scripts/cloud_streamed_native_archive.py'
PUBLISHER='scripts/publish_pll845_streamed_checkpoint.py'
MANIFEST='scripts/pll845-stream-storage-deltas.json'
def sha(data):return hashlib.sha256(data).hexdigest()
def source_contract(root):
    m=json.loads((root/MANIFEST).read_text())
    assert sha((root/OLD).read_bytes())==m['baseline_method_hashes'][OLD]==m['baseline_sha256']
    assert m['baseline_sha256']=='6252d868f362e7e638c61c55703eeb83c2505f87f7a48759bbb57d86a2f0395f'
    assert sha((root/OLD_HELPER).read_bytes())==m['baseline_method_hashes'][OLD_HELPER]
    text=(root/CONTROLLER).read_text()
    for e in reversed(m['edits']):
        assert text.count(e['after'])==e['count']
        text=text.replace(e['after'],e['before'])
    assert sha(text.encode())==m['baseline_sha256'],'Unbound change outside storage migration'
    for p,d in m['current_files'].items():assert sha((root/p).read_bytes())==d,p
    native={p:d for p,d in m['baseline_method_hashes'].items()if p not in (OLD,OLD_HELPER)}
    assert len(native)==11
    assert all(sha((root/p).read_bytes())==d for p,d in native.items())
    current=dict(native)
    current.update({p:m['current_files'][p]for p in (CONTROLLER,SELF,ARCHIVE)})
    return m,current
def verify_resume_methods(report,current,root):
    m,expected=source_contract(root)
    assert current==expected,'Changed native, reader or streamed-storage method'
    if report['controller_sha256']==current[CONTROLLER]:
        assert report['method_hashes']==current
        return dict(mode='exact-current-streamed-methods',native_methods_unchanged=True)
    assert report['controller_sha256']==m['baseline_sha256'],'Unrecognized checkpoint controller'
    assert report['method_hashes']==m['baseline_method_hashes'],'Changed native/parser/physical source method'
    return dict(mode='explicit-reversible-streamed-storage-only-delta',baseline_sha256=m['baseline_sha256'],
        candidate_sha256=current[CONTROLLER],bounded_compressed_staging=True,native_methods_unchanged=True)
def disk_plan(root):
    # No full compressed archive is staged. Keep the original conservative minimum
    # for CRIU pages, one current part, raw growth until polling and runner activity.
    paths=list(root.rglob('*'));total=sum(p.stat().st_size for p in paths if p.is_file())
    return dict(source_tree_bytes=total,source_tree_entries=len(paths),archive_copies=0,
        archive_reserve_bytes=12*GIB,compressed_staging_limit_bytes=256*1024**2,
        checkpoint_and_poll_margin_bytes=8*GIB,all_original_native_files_retained=True)
def controls():
    root=Path(__file__).resolve().parents[1];m,current=source_contract(root)
    legacy=dict(controller_sha256=m['baseline_sha256'],method_hashes=m['baseline_method_hashes'])
    same=dict(controller_sha256=current[CONTROLLER],method_hashes=current)
    assert verify_resume_methods(legacy,current,root)['native_methods_unchanged']
    assert verify_resume_methods(same,current,root)['mode']=='exact-current-streamed-methods'
    rejected=[];native=next(p for p in m['baseline_method_hashes']if p not in (OLD,OLD_HELPER))
    for name in ('unknown-controller','changed-native','missing-native','extra-native','current-changed-native','changed-stream-helper'):
        prior=copy.deepcopy(same if name=='current-changed-native'else legacy);actual=dict(current)
        if name=='unknown-controller':prior['controller_sha256']='0'*64
        elif name in ('changed-native','current-changed-native'):prior['method_hashes'][native]='f'*64
        elif name=='missing-native':del prior['method_hashes'][native]
        elif name=='extra-native':prior['method_hashes']['unexpected']='a'*64
        else:actual[ARCHIVE]='0'*64
        try:verify_resume_methods(prior,actual,root)
        except AssertionError:rejected.append(name)
        else:raise AssertionError('Changed continuation methods accepted')
    assert len(rejected)==6
    p=disk_plan(root/'scripts')
    assert p['archive_reserve_bytes']==12*GIB and p['compressed_staging_limit_bytes']<GIB
    return dict(unchanged_native_methods=11,exact_current_and_previous_method_migration=True,
        rejection_controls=rejected,minimum_checkpoint_reserve_bytes=12*GIB,
        native_or_phy_acceptance=False)
if __name__=='__main__':print(json.dumps(controls()))
