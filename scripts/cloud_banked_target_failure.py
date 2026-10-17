#!/usr/bin/env python3
# SPDX-FileCopyrightText: 2026 Hasan Melih Akbulut
# SPDX-License-Identifier: Apache-2.0
"""Expose the preserved native targeted repair failure; never restart the source."""
import json,os,re
from pathlib import Path
import compare_cloud_routed_endpoints as reports
from cloud_corrpre_banked_postcts import api,sha
ROOT=Path(__file__).resolve().parents[1];OUT=ROOT/'cloud-banked-target-failure'
def main():
    assert os.environ.get('GITHUB_ACTIONS')=='true';OUT.mkdir(exist_ok=False);reports.OUT=OUT
    r=dict(status='RUNNING',source_head=os.environ['GITHUB_SHA'],accepted=False,source_run=39034766244)
    def save():(OUT/'result.json').write_text(json.dumps(r,indent=2)+'\n')
    save()
    try:
        run=api('actions/runs/39034766244');assert run['status']=='completed'and run['conclusion']=='failure'and run['head_sha']=='012337031d9855b7fd4bb1fcd3ebf47b67b70786'
        raw=__import__('subprocess').check_output(['gh','api','repos/Melihakbulut221/nssoc/releases/assets/650499763','-H','Accept: application/octet-stream'])
        assert __import__('hashlib').sha256(raw).hexdigest()=='8dfdbf144501bb5a337cdf2759605bff2c2448e129eeef70841c677bede52c30'
        prior=json.loads(raw)
        selected=[n for n in prior['outputs']if n.endswith(('.log','.tcl'))]
        original,proof=reports.restore_report('corrpre-banked-targeted',39034766244,
            '8dfdbf144501bb5a337cdf2759605bff2c2448e129eeef70841c677bede52c30',
            '7dadacfdb09a6124345796a494c44e0296dbfdb5a1921540a8e2617bff11fec2',OUT/'source',selected)
        assert original==prior
        r['source']=proof;r['native_logs']={}
        for n in selected:
            if not n.endswith('.log'):continue
            lines=(OUT/'source'/n).read_text(errors='replace').splitlines()
            positions=[i for i,l in enumerate(lines)if re.search(r'error|traceback|failed|NSSOC_TARGETED',l,re.I)]
            if positions or n=='native.log':
                indexes=set(range(max(0,len(lines)-15),len(lines)))
                for i in positions:indexes.update(range(max(0,i-4),min(len(lines),i+8)))
                r['native_logs'][n]=[dict(line=i+1,text=lines[i])for i in sorted(indexes)]
        r.update(status='COMPLETE_SOURCE_BOUND_NATIVE_FAILURE_INSPECTION_NOT_REPAIR',source_failure_preserved=True)
    except BaseException as e:r.update(status='FAIL_OR_ERROR',error=repr(e));raise
    finally:
        r['outputs']={str(p.relative_to(OUT)):sha(p)for p in OUT.rglob('*')if p.is_file()and p!=OUT/'result.json'};save()
if __name__=='__main__':main()
