#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0
"""Preserve exact completed or failed postroute evidence in its tested-source release."""
import json,os
from pathlib import Path
import mainchip_saved_postroute_admission as admission
from mainchip_saved_postroute_publisher_base import publish_files
from cloud_chunked_results import pack,verify_parts
import ensure_cloud_tested_source_release as guard
GROUP='mainchip-route12-saved-postroute'
def publication_files(root,out,stem,manifest,summary):
    assert manifest['stem']==stem and manifest['source_directory']==root.name
    verify_parts(manifest,out)
    paths=[summary,out/(stem+'.parts.json'),*[out/p['name']for p in manifest['parts']]]
    assert summary.read_bytes()==(root/'result.json').read_bytes()
    assert json.loads(paths[1].read_bytes())==manifest
    assert len({p.name for p in paths})==len(paths)
    assert all(p.is_file()and not p.is_symlink()and p.stat().st_size>0 and p.parent==out for p in paths)
    return paths
def publish_evidence(root,out):
    # The always-on failure publisher must not relabel an unsupported rerun.
    assert os.environ.get('GITHUB_RUN_ATTEMPT')=='1','Only the explicitly reviewed first attempt is supported'
    root=Path(root);out=Path(out)
    assert not root.is_symlink(),'Evidence root is a symlink'
    if root.exists():assert root.is_dir(),'Evidence root is not a directory'
    tag,source=guard.context(GROUP,os.environ)
    guard.validate_release(guard.api('releases/tags/'+tag),guard.api('git/ref/tags/'+tag),tag,source)
    root.mkdir(exist_ok=True)
    assert root.is_dir()and not root.is_symlink()
    # Check the report and every descendant before any report read or write.
    for p in root.rglob('*'):
        assert not p.is_symlink(),'Unexpected evidence symlink'
        assert p.is_file()or p.is_dir(),'Unexpected nonregular evidence'
    f=root/'result.json'
    assert not f.is_symlink()and(not f.exists()or f.is_file())
    r=json.loads(f.read_bytes())if f.is_file()else dict(status='FAIL_MISSING_NATIVE_REPORT',
        source_head=source,accepted=False,final_timing_complete=False,full_phy_accepted=False)
    assert r['source_head']==source
    if r['status'].startswith('RUNNING'):r.update(status='INTERRUPTED_NATIVE_POSTROUTE_NOT_ACCEPTED',accepted=False)
    r['outputs']={str(p.relative_to(root)):admission.sha(p)for p in root.rglob('*')if p.is_file()and p!=f}
    r['run_id']=int(os.environ['GITHUB_RUN_ID']);r['run_attempt']=1
    f.write_text(json.dumps(r,indent=2)+'\n')
    out.mkdir(exist_ok=False)
    stem=GROUP+'-'+os.environ['GITHUB_RUN_ID']+'-1'
    summary=out/(stem+'.summary.json');summary.write_bytes(f.read_bytes())
    manifest=pack(root,stem,out)
    files=publication_files(root,out,stem,manifest,summary)
    report=publish_files(GROUP,files)
    return dict(status='PUBLISHED_EXACT_POSTROUTE_EVIDENCE_NOT_SIGNOFF',
        original_status=r['status'],source_head=source,publication=report,
        files=[dict(name=p.name,bytes=p.stat().st_size,sha256=admission.sha(p))for p in files])
def main():
    admission.methods()
    proof=publish_evidence(Path('cloud-mainchip-route12-postroute'),Path('publication-'+GROUP))
    print(json.dumps(proof,indent=2),flush=True)
if __name__=='__main__':main()
