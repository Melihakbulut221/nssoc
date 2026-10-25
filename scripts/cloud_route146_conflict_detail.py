#!/usr/bin/env python3
# SPDX-FileCopyrightText: 2026 Hasan Melih Akbulut
# SPDX-License-Identifier: Apache-2.0
"""Expose immutable full cell paths for simultaneous setup/hold repair, cloud only."""
import json,os,re
from pathlib import Path
import cloud_tx_input_driver as physical
from run_cloud_tx_layout_repair import sha
from read_opensta_phase_slacks import parse_phases
ROOT=physical.ROOT;OUT=ROOT/'cloud-route146-conflict-detail'
SOURCE=dict(run=38890552952,group='eco-endpoint-compare',root='cloud-eco-endpoint-compare',bytes=29334237,sha='aae74a0639b4fea97af0617b25a51087e7535154a6a1649b24872add289ec0a8',summary='37d829d48fa0a712cbac4ef371b17f0e8bae22e80d1e07596b5e7c2c88625344')
def main():
    assert os.environ.get('GITHUB_ACTIONS')=='true';OUT.mkdir(exist_ok=False)
    result=dict(status='RUNNING',accepted=False,source_head=os.environ['GITHUB_SHA'],source=SOURCE,scope='Exact existing146candidate timing reports; identifies cells for repair, does not change or waive constraints. Worst setup selection is within the90hold-conflicting endpoints, not all chip endpoints.')
    try:
        physical.OUT=OUT;source,prior=physical.restore(SOURCE)
        assert prior['candidate']['run']==38880596259 and prior['candidate_routed_timing_reproduced'] and prior['source_unchanged']
        trace=prior['hold_conflict_paths'];targets=trace['targets'];assert len(targets)==90 and trace['requested_paths']==540 and not trace['unconstrained_requests']
        log=(source/'hold-conflict-paths.log').read_text();assert sha(source/'hold-conflict-paths.log')=='7cd79a1bd50ce1dc101e8ea5878fa3f7b4b18b6d149f388f5b67e4269645545a'
        _,detail=log.split('NSSOC_CANDIDATE_CONFLICT_START\n');parts=re.split(r'(?m)^PHASE_(target_\d+_(?:slow|typical|fast)_(?:min|max))\n',detail)
        assert len(parts)==1081 and not parts[0].strip();blocks=dict(zip(parts[1::2],parts[2::2],strict=True));assert len(blocks)==540
        assert parse_phases(detail,'PHASE')==trace['all_corner_paths']
        indices=sorted(set(sorted(range(90),key=lambda i:targets[i]['hold_seconds']['fast'])[:3]+sorted(range(90),key=lambda i:targets[i]['setup_seconds']['slow'])[:3]))
        selected=[]
        for i in indices:
            reports={c+'_'+d:blocks[f'target_{i}_{c}_{d}']for c in ('slow','typical','fast')for d in ('min','max')}
            selected.append(dict(index=i,target=targets[i],reports=reports))
        groups={}
        for i,t in enumerate(targets):
            lo=trace['all_corner_paths'][f'target_{i}_fast_min']['paths'][0]
            hi=trace['all_corner_paths'][f'target_{i}_slow_max']['paths'][0]
            group=lo['group'];g=groups.setdefault(group,dict(count=0,self_feedback_min=0,same_min_max_start=0,setup_conflicts=0))
            g['count']+=1;g['self_feedback_min']+=lo['startpoint']==lo['endpoint'];g['same_min_max_start']+=lo['startpoint']==hi['startpoint'];g['setup_conflicts']+=any(v<0 for v in t['setup_seconds'].values())
        result.update(status='COMPLETE_EXACT_ROUTE146_CELL_PATHS_NOT_TIMING_ACCEPTANCE',targets=targets,groups=groups,selected=selected,all540_native_reports_verified=True,original_log_sha256=sha(source/'hold-conflict-paths.log'))
    except BaseException as e:result.update(status='FAIL_OR_ERROR',error=repr(e));raise
    finally:(OUT/'result.json').write_text(json.dumps(result,indent=2)+'\n')
if __name__=='__main__':main()
