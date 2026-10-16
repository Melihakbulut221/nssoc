#!/usr/bin/env python3
# SPDX-FileCopyrightText: 2026 Hasan Melih Akbulut
# SPDX-License-Identifier: Apache-2.0
"""Recover original pump extraction methods from source-bound cloud records."""
import hashlib,json,os
from pathlib import Path
from route_cloud_newer_postcts import fetch,sha
ROOT=Path(__file__).resolve().parents[1];OUT=ROOT/'cloud-pll-pump-methods'
def main():
    assert os.environ.get('GITHUB_ACTIONS')=='true';OUT.mkdir(exist_ok=False)
    r=dict(status='RUNNING',source_head=os.environ['GITHUB_SHA'],accepted=False,qualified_pex=False,full_phy_accepted=False,scope='Recover archived original pump/RHI140 physical binding and extraction methods for adapting actual9um capacitor layout. Source recovery only; no new extraction or electrical pass.')
    def save():(OUT/'result.json').write_text(json.dumps(r,indent=2)+'\n')
    save()
    try:
        source=OUT/'source-recovery.json';h='e3482fbcaccf9315236b5b47451e1bb0488ca054dc5e3f9299795f03f8ff227e'
        fetch('https://github.com/Melihakbulut221/nssoc/releases/download/cloud-results-38624930704-1-pll-acquisition-review/result.json',h,source)
        assert source.stat().st_size==23052321
        old=json.loads(source.read_text());assert old['status']=='FAILED_PLL_PARENT_METHOD_RECOVERY' and old['error']=="AssertionError('No original composition recovered')"
        r['source']=dict(run=38624930704,sha256=h,bytes=source.stat().st_size,original_status=old['status'],original_failure=old['error'])
        selected={};inventory={}
        for path,row in old['recovered_sources'].items():
            if not any(word in path.lower() for word in ('pump','rhi140')):continue
            data=row['text'].encode();assert len(data)==row['bytes'] and hashlib.sha256(data).hexdigest()==row['sha256']
            inventory[path]=dict(bytes=len(data),sha256=row['sha256'])
            if path.endswith('.py'):
                assert len(data)<500000
                selected[path]=row
        assert selected,'No actual pump source methods recovered'
        r['inventory']=inventory;r['methods']=selected
        r['status']='COMPLETE_SOURCE_BOUND_PUMP_METHOD_RECOVERY_NOT_NEW_EXTRACTION'
        assert sha(source)==h
    except BaseException as e:r.update(status='FAIL_OR_ERROR',error=repr(e));raise
    finally:
        r['outputs']={p.name:sha(p) for p in OUT.iterdir() if p.is_file() and p.name!='result.json'};save()
if __name__=='__main__':main()
