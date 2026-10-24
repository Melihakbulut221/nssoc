#!/usr/bin/env python3
# SPDX-FileCopyrightText: 2026 Hasan Melih Akbulut
# SPDX-License-Identifier: Apache-2.0
"""Expose exact saved routed native timing paths without changing source or constraints."""
import json,os,re
from collections import Counter
from pathlib import Path
import compare_cloud_routed_endpoints as reports
from run_cloud_tx_layout_repair import sha
ROOT=Path(__file__).resolve().parents[1]
OUT=ROOT/'hw/soc/out/cloud-onehot-round4-path-diagnosis'
def main():
    assert os.environ.get('GITHUB_ACTIONS')=='true'
    OUT.mkdir(parents=True,exist_ok=False);reports.OUT=OUT
    r=dict(status='RUNNING',source_head=os.environ['GITHUB_SHA'],accepted=False,final_timing_complete=False,full_phy_accepted=False,scope='Read-only diagnosis of saved native routed reports; no ECO or new STA claim.')
    def save():(OUT/'result.json').write_text(json.dumps(r,indent=2)+'\n')
    save()
    try:
        pin=json.loads((ROOT/'docs/evidence/replay-onehot-round4-routed-sta-result-20261018.json').read_text())
        assert pin['run']==39117700521
        selected=[n for n in pin['outputs']if n.startswith('run/2-nssoc-onehotroutedsta/')and n.endswith(('.rpt','.log','.tcl','.json'))]
        assert selected
        prior,proof=reports.restore_report('replay-onehot-round4-routed-extraction',pin['run'],pin['summary_sha256'],pin['parts_sha256'],OUT/'source',selected)
        assert prior['source_head']==pin['source_head']and prior['status']==pin['status']and prior['sources_unchanged']
        assert prior['outputs']==pin['outputs']and not prior['all_reported_timing_and_electrical_gates_met']
        r['source']=proof;r['measurements']=prior['measurements'];r['reports']={}
        for corner,row in prior['measurements'].items():
            results={}
            for name in ('max.rpt','min.rpt','ws.max.rpt','ws.min.rpt','checks.rpt','violator_list.rpt','clock.rpt'):
                rel=row['directory']+'/'+name;assert rel in selected
                text=(OUT/'source'/rel).read_text();parts=re.split(r'(?m)(?=^Startpoint:)',text)
                paths=[p for p in parts if p.startswith('Startpoint:')]
                groups=Counter();starts=Counter();ends=Counter();slacks=[]
                for p in paths:
                    for prefix,counter in [('Startpoint:',starts),('Endpoint:',ends),('Path Group:',groups)]:
                        m=re.search(r'(?m)^'+prefix+r'\s*(.+)',p)
                        if m:counter[m[1].strip()]+=1
                    m=re.search(r'(?m)^\s*([-+]?\d+(?:\.\d+)?)\s+slack\s+\((?:VIOLATED|MET)\)',p)
                    if m:slacks.append(float(m[1]))
                results[name]=dict(sha256=sha(OUT/'source'/rel),bytes=len(text.encode()),reported_path_count=len(paths),path_groups=dict(groups),startpoint_counts=starts.most_common(30),endpoint_counts=ends.most_common(30),parsed_slack_count=len(slacks),minimum_reported_slack=min(slacks)if slacks else None,first_paths=paths[:8],excerpt=text[:24000]if not paths else '',tail=text[-4000:]if name=='checks.rpt'else '')
                if name in ('max.rpt','min.rpt'):assert paths,'No native path text found'
            r['reports'][corner]=results
        assert all(sha(OUT/'source'/n)==prior['outputs'][n]for n in selected)
        r.update(status='COMPLETE_EXACT_SAVED_ROUTED_PATH_DIAGNOSIS_NOT_REPAIR',sources_unchanged=True)
    except BaseException as e:r.update(status='FAIL_OR_ERROR',error=repr(e));raise
    finally:
        r['outputs']={str(p.relative_to(OUT)):sha(p)for p in OUT.rglob('*')if p.is_file()and p!=OUT/'result.json'};save()
if __name__=='__main__':main()
