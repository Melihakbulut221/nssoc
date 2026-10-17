#!/usr/bin/env python3
# SPDX-FileCopyrightText: 2026 Hasan Melih Akbulut
# SPDX-License-Identifier: Apache-2.0
"""Advance exact one-hot placement to fresh all-corner native post-CTS repair."""
import argparse,json,os,subprocess,sys,time
from pathlib import Path
from cloud_corrpre_banked_handoff import api,get_asset,wait_success
ROOT=Path(__file__).resolve().parents[1]
OUT=ROOT/'cloud-replay-onehot-repair-source'
RUN=39059854681
HEAD='1a48e41127d8485ebcf382fd99482b6d8b1bef76'
def main():
    p=argparse.ArgumentParser();p.add_argument('--wait',action='store_true');a=p.parse_args()
    assert os.environ.get('GITHUB_ACTIONS')=='true';OUT.mkdir(exist_ok=False)
    r=dict(status='WAITING_FOR_EXACT_NEW_CTS',source_head=os.environ['GITHUB_SHA'],accepted=False,final_timing_complete=False)
    def save():(OUT/'result.json').write_text(json.dumps(r,indent=2)+'\n')
    save()
    try:
        run=wait_success(RUN,'.github/workflows/replay-onehot-placement-cloud.yml',time.monotonic()+18000,r,save)
        assert run['head_sha']==HEAD and run['event']=='push'and run['run_attempt']==1
        if a.wait:r['status']='EXACT_NEW_CTS_COMPLETED_READY_FOR_INDEPENDENT_REVALIDATION';return
        group='replay-onehot-placement';release=api(f'releases/tags/cloud-results-{RUN}-1-{group}');pins={}
        for kind in ('summary','parts'):
            matches=[x for x in release['assets']if x['name']==f'{group}-{RUN}-1.{kind}.json'];assert len(matches)==1
            raw,digest=get_asset(matches[0]);pins[kind]=dict(asset=matches[0]['id'],sha256=digest)
            (OUT/(kind+'.json')).write_bytes(raw)
        original=json.loads((OUT/'summary.json').read_text())
        assert original['source_head']==HEAD and original['sources_unchanged']and original['returncode']==0
        r.update(status='RUNNING_INDEPENDENT_NEW_CTS_REPAIR',pins=pins);save()
        subprocess.run([sys.executable,str(ROOT/'scripts/cloud_replay_onehot_postcts.py'),'--placement-run',str(RUN),'--summary-sha256',pins['summary']['sha256'],'--parts-sha256',pins['parts']['sha256']],check=True,cwd=ROOT)
        r['status']='NEW_NATIVE_REPAIR_COMPLETED_NOT_ROUTED_TIMING_OR_LOGIC_SIGNOFF'
    except BaseException as error:r.update(status='FAIL_OR_ERROR_NO_SOURCE_RESTART',error=repr(error));raise
    finally:save()
if __name__=='__main__':main()
