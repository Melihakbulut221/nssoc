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
def main():
    admission.methods()
    tag,source=guard.context(GROUP,os.environ)
    guard.validate_release(guard.api('releases/tags/'+tag),guard.api('git/ref/tags/'+tag),tag,source)
    root=Path('cloud-mainchip-route12-postroute');root.mkdir(exist_ok=True)
    f=root/'result.json'
    r=json.loads(f.read_bytes())if f.is_file()else dict(status='FAIL_MISSING_NATIVE_REPORT',
        source_head=source,accepted=False,final_timing_complete=False,full_phy_accepted=False)
    assert r['source_head']==source
    if r['status'].startswith('RUNNING'):r.update(status='INTERRUPTED_NATIVE_POSTROUTE_NOT_ACCEPTED',accepted=False)
    for p in root.rglob('*'):assert not p.is_symlink(),'Unexpected evidence symlink'
    r['outputs']={str(p.relative_to(root)):admission.sha(p)for p in root.rglob('*')if p.is_file()and p!=f}
    r['run_id']=int(os.environ['GITHUB_RUN_ID']);r['run_attempt']=1
    f.write_text(json.dumps(r,indent=2)+'\n')
    out=Path('publication-'+GROUP);out.mkdir(exist_ok=False)
    stem=GROUP+'-'+os.environ['GITHUB_RUN_ID']+'-1'
    summary=out/(stem+'.summary.json');summary.write_bytes(f.read_bytes())
    manifest=pack(root,stem,out);verify_parts(manifest,out)
    files=[summary,out/(stem+'.parts.json'),*[out/p['name']for p in manifest['parts']]]
    assert summary.read_bytes()==f.read_bytes()
    assert all(p.is_file()and not p.is_symlink()and p.parent==out for p in files)
    report=publish_files(GROUP,files)
    print(json.dumps(dict(status='PUBLISHED_EXACT_POSTROUTE_EVIDENCE_NOT_SIGNOFF',
        original_status=r['status'],source_head=source,publication=report),indent=2),flush=True)
if __name__=='__main__':main()
