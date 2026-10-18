#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0
"""Read preserved interrupted native route logs; no reroute or timing claim."""
import json,os,re
from pathlib import Path
import compare_cloud_routed_endpoints as reports
from run_cloud_tx_layout_repair import sha
ROOT=Path(__file__).resolve().parents[1];OUT=ROOT/'hw/soc/out/cloud-onehot-load-route-review'
def main():
    assert os.environ.get('GITHUB_ACTIONS')=='true'
    OUT.mkdir(parents=True,exist_ok=False);reports.OUT=OUT
    r=dict(status='RUNNING',source_head=os.environ['GITHUB_SHA'],accepted=False,final_timing_complete=False)
    def save():(OUT/'result.json').write_text(json.dumps(r,indent=2)+'\n')
    save()
    try:
        pin=json.loads((ROOT/'docs/evidence/onehot-load-route-interrupted-20261018.json').read_text())
        prior,proof=reports.restore_report('onehot-load-route',pin['run'],pin['summary_sha256'],pin['parts_sha256'],OUT/'source',pin['selected'])
        assert prior['status']==pin['status'] and prior['source_head']==pin['source_head'] and not prior['accepted']
        r['interrupted_source']=proof;r['logs']={};r['states']={};r['configs']={}
        for n in pin['selected']:
            p=OUT/'source'/n;assert sha(p)==pin['selected_sha256'][n]==prior['outputs'][n]
            if n.endswith(('.log','.rpt')):
                lines=p.read_text(errors='replace').splitlines()
                milestones=[l for l in lines if re.search(r'iter|violation|elapsed|memory|error|warning|rout|congest|percent|repair',l,re.I)]
                r['logs'][n]=dict(line_count=len(lines),tail=lines[-100:],milestones=milestones[-150:])
            elif n.endswith('state_out.json') or n.endswith('state_in.json'):
                state=json.loads(p.read_text());r['states'][n]={k:v for k,v in state.items() if k!='metrics'};r['states'][n]['metric_count']=len(state.get('metrics',{}))
            elif n.endswith('config.json'):
                cfg=json.loads(p.read_text());r['configs'][n]={k:v for k,v in cfg.items()if any(t in k for t in ['THREAD','CORE','DRT','GRT','CLOCK','ROUT','DERAT'])}
        assert any(n.endswith('1-openroad-globalrouting/state_out.json')for n in r['states'])
        assert not any(n.endswith('2-openroad-detailedrouting/state_out.json')for n in pin['selected'])
        r.update(status='PASS_PRESERVED_INTERRUPTED_ROUTE_REVIEW_NOT_ROUTING_OR_TIMING_ACCEPTANCE',sources_unchanged=True)
    except BaseException as e:r.update(status='FAIL_OR_ERROR',error=repr(e));raise
    finally:
        r['outputs']={str(p.relative_to(OUT)):sha(p)for p in OUT.rglob('*')if p.is_file()and p!=OUT/'result.json'};save()
if __name__=='__main__':main()
