#!/usr/bin/env python3
# SPDX-FileCopyrightText: 2026 Hasan Melih Akbulut
# SPDX-License-Identifier: Apache-2.0
"""Expose the preserved native global routing failure; never restart the source."""
import json,os,re
from pathlib import Path
import compare_cloud_routed_endpoints as reports
from cloud_corrpre_banked_postcts import api,sha
ROOT=Path(__file__).resolve().parents[1];OUT=ROOT/'cloud-banked-grt-failure'
def main():
    assert os.environ.get('GITHUB_ACTIONS')=='true';OUT.mkdir(exist_ok=False);reports.OUT=OUT
    r=dict(status='RUNNING',source_head=os.environ['GITHUB_SHA'],accepted=False,source_run=39031588904)
    def save():(OUT/'result.json').write_text(json.dumps(r,indent=2)+'\n')
    save()
    try:
        run=api('actions/runs/39031588904');assert run['status']=='completed'and run['conclusion']=='failure'and run['head_sha']=='d46ab620a9876b53e1c9667f34053d66f9c0929f'
        raw=__import__('subprocess').check_output(['gh','api','repos/Melihakbulut221/nssoc/releases/assets/650582444','-H','Accept: application/octet-stream'])
        assert __import__('hashlib').sha256(raw).hexdigest()=='08299ecda4f66635e3161e7bd33a1c11659f233e0af04ca0a070037ee119f326'
        prior=json.loads(raw)
        selected=list(prior['outputs'])
        original,proof=reports.restore_report('corrpre-banked-grt',39031588904,
            '08299ecda4f66635e3161e7bd33a1c11659f233e0af04ca0a070037ee119f326',
            'de42f19424c2033e34665149cb470909083e7e06fab76de0ffc34e0807c7fa67',OUT/'source',selected)
        assert original==prior
        r['source']=proof;r['native_logs']={}
        for n in selected:
            if not n.endswith('.log'):continue
            lines=(OUT/'source'/n).read_text(errors='replace').splitlines()
            positions=[i for i,l in enumerate(lines)if re.search(r'\[ERROR|^Error:|Traceback|^AssertionError|^\s*(?:Killed|Aborted)|congestion|overflow|NDR|GRT-' ,l,re.I)]
            if positions or n=='native.log':
                indexes=set(range(max(0,len(lines)-100),len(lines)))
                for i in positions:indexes.update(range(max(0,i-4),min(len(lines),i+8)))
                r['native_logs'][n]=[dict(line=i+1,text=lines[i])for i in sorted(indexes)]
        r['native_json']={n:json.loads((OUT/'source'/n).read_text())for n in selected if n.endswith(('process_stats.json','or_metrics_out.json','config.json'))}
        r['flow_errors']={n:(OUT/'source'/n).read_text(errors='replace')for n in selected if n in ('run/error.log','run/warning.log','run/flow.log')}
        r.update(status='COMPLETE_SOURCE_BOUND_NATIVE_FAILURE_INSPECTION_NOT_REPAIR',source_failure_preserved=True)
    except BaseException as e:r.update(status='FAIL_OR_ERROR',error=repr(e));raise
    finally:
        r['outputs']={str(p.relative_to(OUT)):sha(p)for p in OUT.rglob('*')if p.is_file()and p!=OUT/'result.json'};save()
if __name__=='__main__':main()
