#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0
"""Read-only cloud analysis of exact saved nominal captures; no simulator command."""
import argparse,json,os,shutil,traceback
from pathlib import Path
import cdr_v59_headroom_readback_admission as a
import cdr_v59_headroom_rows as core
import cdr_v58_saved_rows as rows
import cloud_cdr_v59_binding_rc as evidence
import migrate_outputs_to_cloud as publisher
import ensure_cloud_tested_source_release as release
import wait_cloud_tested_source_release as waiter
from cloud_chunked_results import pack,verify_parts
GROUP='cdr-v59-cn-headroom-readback'
def write(p,value):
    p.write_text(json.dumps(value,indent=2,allow_nan=False)+'\n')
def run_case(case,out,m):
    assert shutil.disk_usage(out.parent).free>=8*1024**3
    saved,report,restore=a.restore(case,out,m)
    write(out/'restore-proof.json',restore)
    t,d,contract,replay=a.validate_native(saved,report)
    write(out/'original-measurements-reproduced.json',replay)
    diagnosis=core.diagnostic(t,d,report,contract)
    cache=rows.cache(out/'selected-all-native-rows.bin',t,d,diagnosis['selected_vectors'])
    frameproof=core.write_frames(out/'all-critical-native-frames.jsonl',t,d,diagnosis,report,contract)
    write(out/'diagnosis.json',diagnosis);write(out/'cache.json',cache);write(out/'frames.json',frameproof)
    # Every downloaded/extracted source still matches before disposing cloud copies.
    for p,v in restore['selected'].items():assert a.sha(saved/p)==v['sha256']
    del t,d
    # Originals remain immutable in source releases; only this disposable cloud copy.
    shutil.rmtree(saved);shutil.rmtree(out/'transport')
    return dict(case=case,original_rejection=True,targets={i:dict(minimum_VCE_v=v['minimum_VCE_v'],row=v['worst_native_row'],violating_rows=v['failing_native_rows'])for i,v in diagnosis['targets'].items()},
        restore_members=restore['all_member_hashes_verified'],frames=frameproof,cache=cache,
        accepted=False,causality_proven=False)
def publication_result(root):
    assert root.is_dir()and not root.is_symlink(),'Missing or linked evidence root'
    for p in root.rglob('*'):assert not p.is_symlink()and(p.is_file()or p.is_dir()),'Nonregular evidence'
    path=root/'result.json';assert path.is_file()and not path.is_symlink()
    r=json.loads(path.read_bytes())
    assert r['source_head']==os.environ['GITHUB_SHA']and r['run_id']==int(os.environ['GITHUB_RUN_ID'])and r['run_attempt']==1
    assert r['source_run']==a.RUN
    for k in ('new_simulation','new_extraction','geometry_changed','accepted','cdr_accepted','qualified_pex','full_phy_accepted'):assert r[k]is False
    assert r['status']in ('RUNNING','FAIL_EXISTING_CAPTURE_ANALYSIS','PASS_EXISTING_CAPTURE_HEADROOM_ANALYSIS_NOT_ACCEPTANCE')
    cases=[x['case']for x in r['cases']]
    assert cases==['nominal_early','nominal_late'][:len(cases)]
    for row in r['cases']:assert row['original_rejection']is True and row['accepted']is False and row['causality_proven']is False
    if r['status'].startswith('PASS_'):assert cases==['nominal_early','nominal_late']
    current={str(p.relative_to(root)):a.sha(p)for p in root.rglob('*')if p.is_file()and p!=path}
    assert r['outputs']==current,'Changed or incomplete saved evidence inventory'
    return r
def publish(root,m):
    a.cloud_guard(m);waiter.wait(GROUP,os.environ)
    before=publication_result(root)
    transport=a.ROOT/'hw/soc/out'/(GROUP+'-publication');transport.mkdir(parents=True,exist_ok=False)
    stem=GROUP+'-'+os.environ['GITHUB_RUN_ID']+'-1';summary=transport/(stem+'.summary.json')
    shutil.copyfile(root/'result.json',summary);assert a.sha(summary)==a.sha(root/'result.json')
    assert shutil.disk_usage(transport).free>=sum(p.stat().st_size for p in root.rglob('*')if p.is_file())+1024**3
    manifest=pack(root,stem,transport,512*1024**2);verify_parts(manifest,transport)
    assert manifest['stem']==stem and manifest['source_directory']==root.name
    assert summary.read_bytes()==(root/'result.json').read_bytes()
    assert publication_result(root)==before
    files=evidence.publication_files(transport,summary,transport/(stem+'.parts.json'),manifest)
    tag,_=release.context(GROUP,os.environ);previous=publisher.release
    publisher.release=evidence.only_reserved(GROUP,os.environ,release.api)
    proof=dict(status='RUNNING',assets=[])
    try:
        for p in files:
            before_hash=a.sha(p);proof['assets'].append(publisher.publish(p,tag));assert a.sha(p)==before_hash
        proof['status']='PASS_EXISTING_CAPTURE_EVIDENCE_PUBLISHED_NOT_ELECTRICAL_ACCEPTANCE'
    except BaseException as e:proof.update(status='FAIL_PUBLICATION',error=repr(e));raise
    finally:
        publisher.release=previous;write(transport/'publication.json',proof)
    return proof
def main():
    p=argparse.ArgumentParser();g=p.add_mutually_exclusive_group(required=True)
    g.add_argument('--readback',action='store_true');g.add_argument('--publish',action='store_true');args=p.parse_args()
    m=a.methods();a.cloud_guard(m)
    out=a.ROOT/('cloud-'+GROUP)
    if args.publish:
        print(json.dumps(publish(out,m),indent=2),flush=True);return
    waiter.wait(GROUP,os.environ);out.mkdir(exist_ok=False)
    result=dict(status='RUNNING',source_head=os.environ['GITHUB_SHA'],run_id=int(os.environ['GITHUB_RUN_ID']),
        run_attempt=1,source_run=a.RUN,cases=[],new_simulation=False,new_extraction=False,geometry_changed=False,
        accepted=False,cdr_accepted=False,qualified_pex=False,full_phy_accepted=False)
    try:
        for case in ('nominal_early','nominal_late'):result['cases'].append(run_case(case,out/case,m))
        a.methods();result['status']='PASS_EXISTING_CAPTURE_HEADROOM_ANALYSIS_NOT_ACCEPTANCE'
    except BaseException as e:
        result.update(status='FAIL_EXISTING_CAPTURE_ANALYSIS',error=repr(e),traceback=traceback.format_exc());raise
    finally:
        result['outputs']={str(p.relative_to(out)):a.sha(p)for p in out.rglob('*')if p.is_file()and p!=out/'result.json'}
        write(out/'result.json',result)
        print(json.dumps(dict(status=result['status'],result_sha256=a.sha(out/'result.json'),completed_cases=[x['case']for x in result['cases']])),flush=True)
if __name__=='__main__':main()
