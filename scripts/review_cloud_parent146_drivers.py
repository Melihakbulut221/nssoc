#!/usr/bin/env python3
# SPDX-FileCopyrightText: 2026 Hasan Melih Akbulut
# SPDX-License-Identifier: Apache-2.0
"""Source-bound setup load diagnosis and reported fast-hold path intersection."""
import argparse,collections,json,math,os,re
from pathlib import Path
import compare_cloud_routed_endpoints as reports
from read_opensta_phase_slacks import parse_phases
from route_cloud_newer_postcts import sha
ROOT=Path(__file__).resolve().parents[1];OUT=ROOT/'cloud-parent146-driver-review'

def stage(line):
    m=re.fullmatch(r'\s*(\d+)\s+(\S+)\s+(\S+)\s+(\S+)\s+(\S+)\s+([\^v])\s+(.+?)\s+\(([^() ]+)\)\s*',line)
    if not m:return None
    values=[float(m[i]) for i in range(2,6)]
    assert all(math.isfinite(v) for v in values) and values[0]>=0 and values[1]>=0,'Invalid native stage values'
    return dict(fanout=int(m[1]),cap_pf=values[0],slew_ns=values[1],delay_ns=values[2],arrival_ns=values[3],edge=m[6],pin=m[7],master=m[8],native_line=line)

def blocks(text,prefix):
    parsed=parse_phases(text,prefix);markers=list(re.finditer(r'^'+prefix+r'_(\w+)[ \t]*$',text,re.M));result=[]
    for index,marker in enumerate(markers):
        end=markers[index+1].start() if index+1<len(markers) else len(text);body=text[marker.end():end]
        starts=list(re.finditer(r'^Startpoint:',body,re.M));expected=parsed[marker[1]]['paths'];assert len(starts)==len(expected)
        for j,start in enumerate(starts):
            stop=starts[j+1].start() if j+1<len(starts) else len(body);raw=body[start.start():stop]
            assert 'data arrival time' in raw
            stages=[row for line in raw.split('data arrival time',1)[0].splitlines() if (row:=stage(line)) is not None]
            assert stages,'No native data stages in complete path'
            result.append(dict(phase=marker[1],path_index=j,metadata=expected[j],stages=stages))
    return parsed,result

def eligible(row):
    master=row['master']
    return master.startswith('sg13g2_') and master.endswith(('_1','_2')) and not any(k in master for k in ('df','latch','dlygate','clk')) and row['cap_pf']>=.1 and row['delay_ns']>=.5

def controls():
    line='  4  0.424000000  1.200000000  0.764000000  2.100000000 ^ input37806/X (sg13g2_buf_2)'
    r=stage(line);assert r['pin']=='input37806/X' and r['fanout']==4 and eligible(r)
    assert stage('  0.000000 data arrival time') is None
    assert not eligible(dict(r,master='sg13g2_dfrbpq_1')) and not eligible(dict(r,master='sg13g2_dlygate4sd3_1'))
    assert not eligible(dict(r,cap_pf=.099)) and not eligible(dict(r,delay_ns=.499))
    for value in ('nan','inf','-0.1'):
        try:stage(line.replace('0.424000000',value))
        except AssertionError:pass
        else:raise AssertionError('Invalid native capacitance accepted')
    assert stage(line.replace('^','v'))['edge']=='v'
    assert stage(line.replace('input37806/X','$abc$1$cell/with_path/Y'))['pin']=='$abc$1$cell/with_path/Y'
    return dict(native_columns_and_polarity_checked=True,invalid_capacitance_rejected=3,sequential_and_delay_cells_excluded_from_load_recipe=True,thresholds_are_diagnostic_selection_only=True)

def main():
    assert os.environ.get('GITHUB_ACTIONS')=='true';OUT.mkdir(exist_ok=False);reports.OUT=OUT
    result=dict(status='RUNNING',accepted=False,source_head=os.environ['GITHUB_SHA'],controls=controls(),full_serial_phy_complete=False,final_timing_complete=False,scope='Actual source-bound146buffer parent only; the234child is still routing. All1050 original global reported paths and all90hold-target540corner paths retained. Weak-driver prioritization does not prove min-path safety: paths can switch, other endpoints are not represented in the hold trace, and allendpoint rerouted timing/geometry must be checked after changes.')
    def save():(OUT/'result.json').write_text(json.dumps(result,indent=2)+'\n')
    save()
    try:
        trace,trace_proof=reports.restore_report('eco-endpoint-compare',38890552952,'37d829d48fa0a712cbac4ef371b17f0e8bae22e80d1e07596b5e7c2c88625344','5d88883114ffac8f845636adca0f582b491dc033edd9fe674d6c197f10d6bafe',OUT/'trace',('hold-conflict-paths.log','hold-conflicts.json'))
        assert trace['source_unchanged'] and trace['candidate_routed_timing_reproduced'] and trace['candidate']['run']==38880596259
        assert trace['graph_minima_mode'] and trace['exact_graph_coverage']['verification']['exact_minimum_equality'] and not trace['any_loss_of_constraints']
        detail=trace['hold_conflict_paths'];assert detail==json.loads((OUT/'trace/hold-conflicts.json').read_text())
        assert len(detail['targets'])==90 and detail['requested_paths']==540 and not detail['unconstrained_requests']
        log=(OUT/'trace/hold-conflict-paths.log').read_text();assert log.count('NSSOC_CANDIDATE_CONFLICT_START\n')==1
        phases,paths=blocks(log.split('NSSOC_CANDIDATE_CONFLICT_START\n')[1],'PHASE');assert phases==detail['all_corner_paths'] and len(paths)==540
        parent,parent_proof=reports.restore_report('refined-hold-eco',38880596259,'aa87fe441e4b3680c84bb0d46f50ccb3fe744a031dbc81a4d96de0efc2b59a2c','612de7f6659774b2b4d3211ae7e10a04df7d808d732f1404ce19a981b90b1586',OUT/'parent',('fresh-routed-sta.log',))
        assert parent['original_routed_timing_reproduced'] and parent['protected_source_unchanged'] and parent['native_drt_drvs']==0
        global_phases,global_paths=blocks((OUT/'parent/fresh-routed-sta.log').read_text(),'CORNER')
        assert global_phases==parent['routed_timing'] and len(global_paths)==1050
        assert parent['profile']=='refined_hold_batch' and parent['buffer_count']==146
        assert trace['endpoint_count']==22544 and trace['endpoint_corner_delay_rows']==135264
        fast_min={}
        for p in paths:
            match=re.fullmatch(r'target_(\d+)_(slow|typical|fast)_(min|max)',p['phase']);assert match
            idx=int(match[1]);assert 0<=idx<90
            if match[2]=='fast' and match[3]=='min':
                for row in p['stages']:fast_min.setdefault(row['pin'],set()).add(idx)
        candidates={};chosen=[]
        for origin,records in [('global',global_paths),('hold_targets',paths)]:
            for p in records:
                meta=p['metadata']
                if meta['corner']!='slow' or meta['path_type']!='max' or meta['slack_ns']>=0:continue
                chosen.append(dict(origin=origin,**p))
                for row in p['stages']:
                    if not eligible(row):continue
                    key=(row['pin'],row['master']);item=candidates.setdefault(key,dict(pin=row['pin'],master=row['master'],observations=[],reported_fast_min_target_indices=sorted(fast_min.get(row['pin'],set())),requires_native_odb_pin_resolution=True))
                    item['observations'].append(dict(origin=origin,phase=p['phase'],path_index=p['path_index'],endpoint=meta['endpoint'],slack_ns=meta['slack_ns'],stage=row))
        ranked=sorted(candidates.values(),key=lambda x:(-max(r['stage']['delay_ns'] for r in x['observations']),-len(x['observations']),x['pin']))
        result.update(status='COMPLETE_SOURCE_BOUND_SETUP_HOLD_DRIVER_DIAGNOSIS_NOT_REPAIR',trace_source=trace_proof,parent_source=parent_proof,reported_paths=dict(hold_corner_paths=len(paths),global_corner_paths=len(global_paths),negative_slow_setup_paths=len(chosen)),selection=dict(min_cap_pf=.1,min_stage_delay_ns=.5,weak_drive_suffixes=['_1','_2'],diagnostic_only=True),unique_weak_loaded_outputs=len(ranked),ranked_outputs=ranked,negative_slow_paths=chosen)
        result['negative_fast_setup_paths']=[p for p in global_paths if p['metadata']['corner']=='fast'and p['metadata']['path_type']=='max'and p['metadata']['slack_ns']<0]
        assert len(result['negative_fast_setup_paths'])==1, 'Exact146parent has one reported fast setup path'
        positives=[(i,r)for i,r in enumerate(detail['targets'])if all(v is not None and v>0 for v in r['setup_seconds'].values())]
        assert len(positives)==0 and len({(r['native_pin']['instance'],r['native_pin']['pin'])for _,r in positives})==0
        result['positive_setup_hold_targets']=[]
        for index,target in positives:
            relevant=[p for p in paths if p['phase'].startswith('target_'+str(index)+'_')]
            assert len(relevant)==6 and {p['metadata']['corner']for p in relevant}=={'slow','typical','fast'}
            assert target['hold_seconds']['fast']<0 and target['native_pin']['kind']=='instance'
            result['positive_setup_hold_targets'].append(dict(index=index,target=target,all_six_measured_paths=relevant,
                delay_cell_fit_proven=False,requires_physical_branch_trial=True))
        result['remaining_setup_conflicting_hold_targets']=len(detail['targets'])-len(positives)
        assert result['remaining_setup_conflicting_hold_targets']==90
        result['complete_reported_global_paths']=global_paths
        result['all_stage_delay_ranking']=sorted([dict(origin=origin,phase=p['phase'],metadata=p['metadata'],stage=row) for origin,records in [('global',global_paths),('hold_targets',paths)] for p in records if p['metadata']['path_type']=='max'and p['metadata']['slack_ns']<0 for row in p['stages']if row['delay_ns']>=.25],key=lambda r:-r['stage']['delay_ns'])
        result['not_seen_on_reported_fast_hold_paths']=[r['pin'] for r in ranked if not r['reported_fast_min_target_indices']]
        result['seen_on_reported_fast_hold_paths']=[r['pin'] for r in ranked if r['reported_fast_min_target_indices']]
        for folder,proof in [('trace',trace_proof),('parent',parent_proof)]:
            for name,pin in proof['restore']['selected_files'].items():assert sha(OUT/folder/name)==pin['sha256']
        result['source_unchanged']=True
        print(json.dumps(dict(status=result['status'],outputs=len(ranked),not_seen_on_reported_fast_hold_paths=result['not_seen_on_reported_fast_hold_paths'])),flush=True)
    except BaseException as error:result.update(status='FAIL_OR_ERROR',error=repr(error));raise
    finally:
        result['outputs']={str(p.relative_to(OUT)):sha(p) for p in OUT.rglob('*') if p.is_file() and p.name!='result.json'};save()
if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--controls-only',action='store_true');a=p.parse_args()
    if a.controls_only:print(json.dumps(controls()))
    else:main()
