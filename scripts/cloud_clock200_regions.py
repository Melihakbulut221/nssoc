#!/usr/bin/env python3
# SPDX-FileCopyrightText: 2026 Hasan Melih Akbulut
# SPDX-License-Identifier: Apache-2.0
"""Expose the preserved native global routing failure; never restart the source."""
import json,os,re
from pathlib import Path
import compare_cloud_routed_endpoints as reports
from cloud_corrpre_banked_postcts import api,sha
ROOT=Path(__file__).resolve().parents[1];OUT=ROOT/'cloud-clock200-regions'
def main():
    assert os.environ.get('GITHUB_ACTIONS')=='true';OUT.mkdir(exist_ok=False);reports.OUT=OUT
    r=dict(status='RUNNING',source_head=os.environ['GITHUB_SHA'],accepted=False,source_run=39041556309)
    def save():(OUT/'result.json').write_text(json.dumps(r,indent=2)+'\n')
    save()
    try:
        run=api('actions/runs/39041556309');assert run['status']=='completed'and run['conclusion']=='failure'and run['head_sha']=='e06941eefa3761b8b351be1606b7f802cde5dfed'
        raw=__import__('subprocess').check_output(['gh','api','repos/Melihakbulut221/nssoc/releases/assets/650765861','-H','Accept: application/octet-stream'])
        assert __import__('hashlib').sha256(raw).hexdigest()=='ebaad5e691a884072c624b2e5ad02108300863b5a78ee20e3dfc0464cb17c637'
        prior=json.loads(raw)
        selected=list(prior['outputs'])
        original,proof=reports.restore_report('corrpre-banked-clock200-grt',39041556309,
            'ebaad5e691a884072c624b2e5ad02108300863b5a78ee20e3dfc0464cb17c637',
            '795a8da88709f3b189d6302ca7c81cfff3508182bd0ed6a4f845b30c314c2516',OUT/'source',selected)
        assert original==prior
        r['source']=proof;r['native_logs']={}
        r['congestion_regions']={n:(OUT/'source'/n).read_text() for n in selected if n in prior['native_congestion_reports']}
        assert len(r['congestion_regions'])==3 and prior['native_ndr_screen']['preserved']
        assert all(sha(OUT/'source'/n)==v for n,v in prior['native_congestion_reports'].items())
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
