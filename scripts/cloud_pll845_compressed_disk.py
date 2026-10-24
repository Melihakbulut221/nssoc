#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0
"""Reversible storage-only extension of the complete native PLL continuation."""
import copy,hashlib,json,math,struct
from pathlib import Path
import cloud_pll845_stream_disk as legacy
import cloud_pll845_preallocated_storage as allocation
import cloud_native_btrfs_case as btrfs
import read_pll845_full_native_transient as full_wave
CONTROLLER='scripts/cloud_pll845_compressed_acquisition.py'
SELF='scripts/cloud_pll845_compressed_disk.py'
ARCHIVE='scripts/cloud_streamed_native_archive.py'
ALLOCATION='scripts/cloud_pll845_preallocated_storage.py'
BINDING='scripts/cloud_native_btrfs_case.py'
MANIFEST='scripts/pll845-compressed-storage-deltas.json'
def sha(data):return hashlib.sha256(data).hexdigest()
def source_contract(root):
    baseline,old=legacy.source_contract(root)
    m=json.loads((root/MANIFEST).read_text())
    assert m['baseline_method_hashes']==old
    for p,d in m['current_files'].items():assert sha((root/p).read_bytes())==d,p
    text=(root/CONTROLLER).read_text()
    for e in reversed(m['edits']):
        assert text.count(e['after'])==e['count']
        text=text.replace(e['after'],e['before'])
    assert sha(text.encode())==old[legacy.CONTROLLER]
    native={p:d for p,d in old.items()if p not in (legacy.CONTROLLER,legacy.SELF,ARCHIVE)}
    assert len(native)==11 and all(sha((root/p).read_bytes())==h for p,h in native.items())
    q=json.loads((root/m['qualification_receipt']).read_text())
    assert q['run']==m['qualification']['run']and q['summary_sha256']==m['qualification']['summary_sha256']
    assert q['parts_sha256']==m['qualification']['parts_sha256']
    r=q['report']
    assert r['status']=='PASS_NATIVE_PHYSICAL845_PREALLOCATED_BEFORE_DOWNLOAD_SHARED_BTRFS_BIT_EXACT_BOUNDED4NS_NOT_FULL_CAPACITY'
    assert r['positive']['all_native_times_and_all34_probes_bit_exact']and r['positive']['rows']==12818
    assert r['positive']['single_entrypoint']and len(r['controls'])==3 and all(c['rejected']for c in r['controls'])
    assert len(r['external_path_controls']['rejected'])==5 and r['external_superblock']['same_superblock']
    assert r['compressed_case']['before_download_mount_verified']
    assert r['final_storage_capacity']['preallocated_capacity_retained']and not r['final_storage_capacity']['checkpoint_required']
    current=dict(native)
    current.update({p:sha((root/p).read_bytes())for p in (CONTROLLER,SELF,ARCHIVE,ALLOCATION,BINDING)})
    return m,current
def verify_resume_methods(report,current,root):
    m,expected=source_contract(root);assert current==expected
    if report['controller_sha256']==current[CONTROLLER]:
        assert report['method_hashes']==current
        return dict(mode='exact-current-preallocated-compressed-methods',native_methods_unchanged=True)
    old=m['baseline_method_hashes']
    assert report['controller_sha256']==old[legacy.CONTROLLER]
    assert report['method_hashes']==old,'Unrecognized native/parser/storage source'
    assert report['run_id']=='39502073954'and report['run_attempt']=='1'and report['stage']=='continuation','Use the latest terminal-success old-storage capsule'
    return dict(mode='explicit-reversible-preallocated-storage-only-migration',
        baseline_sha256=old[legacy.CONTROLLER],candidate_sha256=current[CONTROLLER],
        complete_raw_retained=True,native_methods_unchanged=True)
def disk_plan(root):
    result=legacy.disk_plan(root)
    assert result['archive_reserve_bytes']==allocation.NATIVE_CHECKPOINT_RESERVE
    result.update(allocation.capacity(Path(__file__).resolve().parents[1]))
    return result
def raw_position(path):
    # Diagnostic only: use the frozen native header reader and read one complete
    # row's time. This cannot substitute for the full all-terminal final reader.
    names,meta=full_wave.header(path);assert len(names)==1695
    size=Path(path).stat().st_size;payload=size-meta['header_bytes'];stride=8*len(names)
    assert payload>=stride
    rows,remainder=divmod(payload,stride)
    with Path(path).open('rb')as f:
        f.seek(meta['header_bytes']+(rows-1)*stride)
        last=struct.unpack('<d',f.read(8))[0]
    assert math.isfinite(last)and last>=0
    return dict(complete_rows_observed=rows,partial_row_bytes=remainder,last_native_time_s=last,
        full_capture_or_acceptance_proven=False,all_terminal_values_audited=False)
def controls():
    root=Path(__file__).resolve().parents[1];m,current=source_contract(root)
    original=legacy.controls();allocated=allocation.controls()
    old=m['baseline_method_hashes']
    for r in (dict(controller_sha256=old[legacy.CONTROLLER],method_hashes=old,run_id='39502073954',run_attempt='1',stage='continuation'),
              dict(controller_sha256=current[CONTROLLER],method_hashes=current)):
        assert verify_resume_methods(r,current,root)['native_methods_unchanged']
    native=next(p for p in old if p not in (legacy.CONTROLLER,legacy.SELF,ARCHIVE))
    rejected=[]
    for label in ('unknown-controller','changed-native','missing-native','changed-allocation','changed-binding','extra-method'):
        r=dict(controller_sha256=old[legacy.CONTROLLER],method_hashes=copy.deepcopy(old),run_id='39502073954',run_attempt='1',stage='continuation');actual=dict(current)
        if label=='unknown-controller':r['controller_sha256']='0'*64
        elif label=='changed-native':r['method_hashes'][native]='f'*64
        elif label=='missing-native':del r['method_hashes'][native]
        elif label=='changed-allocation':actual[ALLOCATION]='0'*64
        elif label=='changed-binding':actual[BINDING]='0'*64
        else:r['method_hashes']['unexpected']='0'*64
        try:verify_resume_methods(r,actual,root)
        except AssertionError:rejected.append(label)
        else:raise AssertionError('Native/storage change accepted')
    assert len(rejected)==6
    return dict(original=original,allocation=allocated,rejected=rejected,unchanged_native_methods=11,
        full_capture_capacity_or_acquisition_proven=False)
if __name__=='__main__':print(json.dumps(controls()))
