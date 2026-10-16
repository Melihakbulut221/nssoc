#!/usr/bin/env python3
# SPDX-FileCopyrightText: 2026 Hasan Melih Akbulut
# SPDX-License-Identifier: Apache-2.0
"""Independently remeasure every actual-route ECO endpoint, preserving all failures."""
import argparse,copy,json,math,os,re,struct,subprocess,tarfile
from pathlib import Path
from cloud_contact_release import validate_route_proof
from expanded_load_targets import validate_candidate as validate_expanded,EXTRA_FILES
from measured_hold_targets import validate_child,CHILD_FILES,TARGETS as HOLD_TARGETS
from candidate_hold_conflicts import controls as conflict_controls,measure as measure_conflicts
from audit_cloud_route_annotation import BASE,SUMMARY_SHA,ARCHIVE_SHA
from audit_cloud_routed_endpoints import parse_table,controls as table_controls,HELPER_SHA
from cloud_verified_parts import extract_verified,controls as archive_controls
from route_cloud_newer_postcts import fetch,sha
from read_opensta_phase_slacks import parse_phases
ROOT=Path(__file__).resolve().parents[1];OUT=ROOT/'cloud-eco-endpoint-compare';SOURCE=ROOT/'cloud-routed-extraction'
CENSUS_SHA='54a23354fc53eb4811b574a1c1bbd70aa413d83463e5165f240b8925c10e00ff'
CENSUS_PARTS_SHA='c9d985717b22590d621bc12e7b3c5a9881ed214a48209587887f1c700d650ac8'
CENSUS_METHOD_SHA='7ffa4fbf12b48eb8a918199439c464e342f236f99f20f5060c8567583feea4b2'

def compare_rows(before,after):
    assert set(before)==set(after),'Endpoint/corner/delay identities changed'
    summaries={}
    for c,d,n in sorted(before):
        phase=c+'_'+d
        if phase not in summaries:
            summaries[phase]={edge:dict(improved=0,regressed=0,unchanged=0,became_unconstrained=0,became_constrained=0,new_negative=0,resolved_negative=0,negative_before=0,negative_after=0,unconstrained_before=0,unconstrained_after=0,worst_before_seconds=None,worst_after_seconds=None) for edge in ('rise','fall','worst')}
        for edge,a,b in zip(('rise','fall','worst'),before[(c,d,n)],after[(c,d,n)]):
            row=summaries[phase][edge]
            for side,value in (('before',a),('after',b)):
                if value is None:row['unconstrained_'+side]+=1
                else:
                    assert math.isfinite(value)
                    row['negative_'+side]+=value<0
                    key='worst_'+side+'_seconds';row[key]=value if row[key] is None else min(row[key],value)
            row['new_negative']+=b is not None and b<0 and a is not None and a>=0
            row['resolved_negative']+=a is not None and a<0 and b is not None and b>=0
            if a==b:row['unchanged']+=1
            elif a is None:row['became_constrained']+=1
            elif b is None:row['became_unconstrained']+=1
            else:row['improved' if b>a else 'regressed']+=1
    return summaries

def targeted_hold_changes(before,after):
    result=[]
    for target in HOLD_TARGETS:
        name=target['endpoint'];item=dict(endpoint=name,native_pin=target['native_pin'])
        for delay,key in (('min','hold_seconds'),('max','setup_seconds')):
            values={c:before[(c,delay,name)][2] for c in ('slow','typical','fast')}
            assert values==target[key],'Parent target values differ from pinned conflict trace'
            item['before_'+key]=values
            item['after_'+key]={c:after[(c,delay,name)][2] for c in ('slow','typical','fast')}
        item['hold_nonnegative_all_corners']=all(v is not None and v>=0 for v in item['after_hold_seconds'].values())
        item['setup_nonnegative_all_corners']=all(v is not None and v>=0 for v in item['after_setup_seconds'].values())
        item['target_timing_passed']=item['hold_nonnegative_all_corners'] and item['setup_nonnegative_all_corners']
        result.append(item)
    return result

def targeted_controls():
    before={}
    for t in HOLD_TARGETS:
        for d,k in (('min','hold_seconds'),('max','setup_seconds')):
            for c,v in t[k].items():before[(c,d,t['endpoint'])]=[v,v,v]
    after=copy.deepcopy(before)
    for t in HOLD_TARGETS:
        for c in ('slow','typical','fast'):after[(c,'min',t['endpoint'])]=[0.,0.,0.]
    assert all(r['target_timing_passed'] for r in targeted_hold_changes(before,after))
    name=HOLD_TARGETS[0]['endpoint']
    for key,value in [(('slow','max',name),[-1e-10]*3),(('fast','min',name),[None]*3)]:
        bad=copy.deepcopy(after);bad[key]=value
        assert not targeted_hold_changes(before,bad)[0]['target_timing_passed']
    missing=copy.deepcopy(after);missing.pop(('fast','min',name))
    try:targeted_hold_changes(before,missing)
    except KeyError:pass
    else:raise AssertionError('Missing target accepted')
    changed=copy.deepcopy(before);changed[('slow','max',name)]=[0.]*3
    try:targeted_hold_changes(changed,after)
    except AssertionError:pass
    else:raise AssertionError('Changed parent measurement accepted')
    return dict(all_four_zero_hold_pass_with_unchanged_positive_setup=True,new_setup_failure_rejected=True,unconstrained_hold_rejected=True,missing_target_rejected=True,changed_parent_rejected=True)

def controls():
    before={(c,d,n):[1e-10,2e-10,1e-10] for c in ('fast','slow','typical') for d in ('min','max') for n in ('a/D','b/D')}
    after=copy.deepcopy(before);after[('fast','min','a/D')]=[-1e-10,2e-10,-1e-10];after[('slow','max','b/D')]=[None,None,None]
    r=compare_rows(before,after);assert r['fast_min']['worst']['new_negative']==1 and r['fast_min']['fall']['unchanged']==2
    assert r['slow_max']['worst']['became_unconstrained']==1 and r['slow_max']['worst']['resolved_negative']==0
    reverse=compare_rows(after,before);assert reverse['fast_min']['worst']['resolved_negative']==1 and reverse['slow_max']['worst']['became_constrained']==1
    assert all(v['worst']['unchanged']==2 for v in compare_rows(before,before).values())
    malformed=copy.deepcopy(after);malformed.pop(('fast','min','a/D'))
    try:compare_rows(before,malformed)
    except AssertionError:pass
    else:raise AssertionError('Missing endpoint accepted')
    return dict(targeted_hold=targeted_controls(),conflict_paths=conflict_controls(),archives=archive_controls(),tables=table_controls(),comparison=dict(identity_roundtrip=True,new_violation_detected=True,resolution_detected=True,loss_of_constraint_not_passed=True,missing_identity_rejected=True))

def restore_report(group,run,summary_sha,parts_sha,destination,selected):
    for v in (summary_sha,parts_sha):assert re.fullmatch(r'[0-9a-f]{64}',v)
    assert run>0 and re.fullmatch(r'[a-z0-9-]+',group)
    stem=f'{group}-{run}-1';base=f'https://github.com/Melihakbulut221/nssoc/releases/download/cloud-results-{run}-1-{group}/'
    folder=OUT/(group+'-source');folder.mkdir()
    fetch(base+stem+'.summary.json',summary_sha,folder/'summary.json');result=json.loads((folder/'summary.json').read_text())
    fetch(base+stem+'.parts.json',parts_sha,folder/'parts.json');manifest=json.loads((folder/'parts.json').read_text())
    assert manifest['stem']==stem
    expected={n:result['outputs'][n] for n in selected};expected['result.json']=summary_sha
    for i,part in enumerate(manifest['parts']):
        assert part['index']==i and part['name']==stem+'.tar.gz.part'+str(i).zfill(4)
        fetch(base+part['name'],part['sha256'],folder/part['name'])
    proof=extract_verified(manifest,folder,destination,expected)
    for part in manifest['parts']:(folder/part['name']).unlink()
    return result,dict(run=run,summary_sha256=summary_sha,manifest_sha256=parts_sha,restore=proof)

def load_census(directory):
    record=json.loads((directory/'native-census.json').read_text());rows=parse_table((directory/'endpoint-slacks.tsv').read_text())
    names=record['endpoints'];corners=record['corners']
    assert len(set(names))==len(names)==record['engine_endpoint_count'] and set(corners)=={'slow','typical','fast'}
    assert record['value_units']=='seconds' and record['native_time_unit_seconds']==struct.unpack('!f',struct.pack('!f',1e-9))[0]
    assert set(rows)=={(c,d,n) for c in corners for d in ('min','max') for n in names}
    assert set(record['native_pin_mapping'])==set(names)
    assert len({json.dumps(v,sort_keys=True) for v in record['native_pin_mapping'].values()})==len(names)
    for d in ('min','max'):
        negative=sum(any(rows[(c,d,n)][2] is not None and rows[(c,d,n)][2]<0 for c in corners) for n in names)
        assert negative==record['negative_endpoint_count'][d]
        for c in corners:
            values=[rows[(c,d,n)][2] for n in names if rows[(c,d,n)][2] is not None];assert values
            assert min(values)==record['native_wns_seconds'][c+'_'+d]
    return record,rows

def main(args):
    assert os.environ.get('GITHUB_ACTIONS')=='true';OUT.mkdir(exist_ok=False)
    result=dict(status='RUNNING',accepted=False,source_head=os.environ['GITHUB_SHA'],final_timing_complete=False,scope='Independent all22544endpoint/3cellcorner/rise-fall/min-max comparison using source-bound fresh routed nominalRC. Unconstrained endpoints and regressions stay visible. No estimate, relaxed SDC, qualified RC, geometry/LVS/antenna or fullPHY acceptance.')
    def save():(OUT/'result.json').write_text(json.dumps(result,indent=2)+'\n')
    save()
    try:
        helper=ROOT/'hw/soc/pnr/timing_hold_reproducibility.tcl';method=ROOT/'hw/soc/pnr/routed_endpoint_census.tcl'
        assert sha(helper)==HELPER_SHA and sha(method)==CENSUS_METHOD_SHA
        original,original_proof=restore_report('routed-endpoints',38819589884,CENSUS_SHA,CENSUS_PARTS_SHA,OUT/'baseline',('native-census.json','endpoint-slacks.tsv'))
        assert original['source_unchanged'] and original['original_routed_timing_reproduced']
        before,old_rows=load_census(OUT/'baseline');assert before['engine_endpoint_count']==22544
        profiles={'two_buffer':(2,'critical-load-eco','TWO_BUFFER'),'control_three_buffer':(3,'control-load-eco','THREE_BUFFER'),'measured_load_batch':(50,'measured-load-eco','MEASURED_LOAD_BATCH'),'protected_load_batch':(50,'protected-load-eco','PROTECTED_LOAD_BATCH'),'measured_hold_batch':(54,'measured-hold-eco','MEASURED_HOLD_BATCH'),'expanded_load_batch':(110,'expanded-load-eco','EXPANDED_LOAD_BATCH')}
        count,group,status_prefix=profiles[args.profile];candidate_dir=ROOT/('cloud-'+group)
        selection=('routed.odb','candidate.nominal.spef','fresh-routed-sta.tcl','fresh-routed-sta.log','geometry-proof.json')
        if args.profile=='protected_load_batch':selection+=('protected-route-proof.json','fixed-source-summary.json')
        if args.profile=='measured_hold_batch':selection+=CHILD_FILES
        if args.profile=='expanded_load_batch':selection+=EXTRA_FILES
        candidate,proof=restore_report(group,args.run,args.summary_sha,args.parts_sha,candidate_dir,selection)
        if args.profile=='protected_load_batch':
            protected=json.loads((candidate_dir/'protected-route-proof.json').read_text())
            assert protected==candidate['protected_route_proof']
            validate_route_proof(protected,candidate)
            assert sha(candidate_dir/'fixed-source-summary.json')=='029d754af843cf83c4dfe6753e43ab0eec228d2d42db0e07f1a910bebcc73e75'
            assert json.loads((candidate_dir/'fixed-source-summary.json').read_text())==candidate['fixed_conversion_receipt']
        expected_status='COMPLETE_'+status_prefix+'_ROUTED_NOMINAL_TIMING_EXPERIMENT_NOT_SIGNOFF'
        assert candidate['status']==expected_status and candidate['source_run']==38809759501
        assert candidate['protected_source_unchanged'] and candidate['original_routed_timing_reproduced'] and candidate['native_drt_drvs']==0
        assert candidate['logic']['status']=='PASS within scope' and candidate['inversion_control']=='REJECTED'
        assert candidate['spef_integrity']['inconsistent_nets']==0
        assert len(candidate['geometry']['added'])==len(candidate['geometry']['changes'])==count
        assert json.loads((candidate_dir/'geometry-proof.json').read_text())==candidate['geometry']
        # The frozen ECO summary embeds its complete logic receipt. Its output
        # inventory omits every basename result.json, including logic/result.json.
        # Do not pretend that omitted nested receipt has an external file hash.
        if count!=2:assert candidate['profile']==args.profile and candidate['buffer_count']==count
        if args.profile=='measured_hold_batch':validate_child(candidate,candidate_dir)
        if args.profile=='expanded_load_batch':validate_expanded(candidate,candidate_dir)
        result.update(candidate=proof,baseline=original_proof);save()
        fetch(BASE+'.summary.json',SUMMARY_SHA,OUT/'original-route-summary.json');source=json.loads((OUT/'original-route-summary.json').read_text())
        packed=OUT/'original-route.tar.gz';fetch(BASE+'.tar.gz.part0000',ARCHIVE_SHA,packed);assert packed.stat().st_size==225682086 and not SOURCE.exists()
        with tarfile.open(packed) as archive:
            for member in archive:
                p=Path(member.name);assert not p.is_absolute() and '..'not in p.parts and p.parts[0]=='cloud-routed-extraction'
                assert member.isfile() or member.isdir();archive.extract(member,ROOT,filter='data')
        packed.unlink();assert sha(SOURCE/'result.json')==SUMMARY_SHA
        for n,digest in source['outputs'].items():assert sha(SOURCE/n)==digest
        for n,digest in source['protected_inputs'].items():assert sha(Path(n))==digest
        baseline_script=(SOURCE/'actual-routed-sta.tcl').read_text()
        assert baseline_script.count(str(SOURCE/'source/routed.odb'))==1 and baseline_script.count(str(SOURCE/'actual-route.nominal.spef'))==3
        expected=baseline_script.replace(str(SOURCE/'source/routed.odb'),str(candidate_dir/'routed.odb')).replace(str(SOURCE/'actual-route.nominal.spef'),str(candidate_dir/'candidate.nominal.spef'))
        assert (candidate_dir/'fresh-routed-sta.tcl').read_text()==expected,'Candidate changed original STA contract'
        assert not (args.diagnose_semantics and args.verify_graph_minima)
        diagnostic_before=diagnostic_after=''
        if args.diagnose_semantics:
            diagnostic_method=ROOT/'hw/soc/pnr/native_path_semantics_diagnosis.tcl'
            diagnostic_before=f'\nsource {{{diagnostic_method}}}\n'
            diagnostic_after=f'\nnssoc_semantics_finish {{{OUT/"native-semantics.json"}}}\n'
            result.update(diagnostic_mode=True,diagnostic_method_sha256=sha(diagnostic_method),scope='Native Vertex versus PathEnd diagnosis only. Original strict guard errors retained, endpoint counts and targeted1/20path probes observed; not an accepted complete census, timing repair or signoff.')
            save()
        if args.verify_graph_minima:
            graph_method=ROOT/'hw/soc/pnr/native_graph_path_coverage.tcl'
            diagnostic_before=f'\nsource {{{graph_method}}}\n'
            diagnostic_after=f'\nnssoc_graph_finish {{{OUT/"native-graph-coverage.json"}}}\n'
            result.update(graph_minima_mode=True,graph_method_sha256=sha(graph_method))
            save()
        script=OUT/'candidate-census.tcl';script.write_text(expected+f'\nsource {{{helper}}}\n'+diagnostic_before+f'set nssoc_endpoint_out {{{OUT}}}\nsource {{{method}}}\n'+diagnostic_after)
        with (OUT/'candidate-census.log').open('w') as log:
            proc=subprocess.Popen([os.environ['CLOUD_APPIMAGE'],'openroad','-exit',str(script)],stdout=subprocess.PIPE,stderr=subprocess.STDOUT,text=True)
            for line in proc.stdout:log.write(line);log.flush();print(line,end='',flush=True)
            code=proc.wait()
        text=(OUT/'candidate-census.log').read_text(errors='replace');assert code==0 and not re.search(r'(?m)^\[ERROR|^Error:',text)
        phases=parse_phases(text,'CORNER')
        for phase,row in candidate['routed_timing'].items():assert phases[phase]['groups']==row['groups']
        if args.diagnose_semantics:
            diagnosis=json.loads((OUT/'native-semantics.json').read_text())
            assert diagnosis['status']=='COMPLETE_NATIVE_SEMANTICS_DIAGNOSIS_NOT_CENSUS_ACCEPTANCE'
            assert diagnosis['accepted'] is False and diagnosis['mismatch_count']==len(diagnosis['mismatches'])>0 and diagnosis['original_guard_failures']
            for name,pin in proof['restore']['selected_files'].items():assert sha(candidate_dir/name)==pin['sha256']
            assert all(sha(SOURCE/n)==v for n,v in source['outputs'].items()) and all(sha(Path(n))==v for n,v in source['protected_inputs'].items())
            assert sha(helper)==HELPER_SHA and sha(method)==CENSUS_METHOD_SHA
            result.update(status='COMPLETE_NATIVE_SEMANTICS_DIAGNOSIS_NOT_CENSUS_ACCEPTANCE',diagnosis=diagnosis,source_unchanged=True,candidate_routed_timing_reproduced=True)
            return
        after,new_rows=load_census(OUT);assert before['native_pin_mapping']==after['native_pin_mapping'],'Physical endpoint identities changed'
        if args.verify_graph_minima:
            from native_graph_path_coverage import verify
            result['exact_graph_coverage']=verify(OUT,after);save()
        comparison=compare_rows(old_rows,new_rows);result['comparison']=comparison
        if args.profile in ('measured_hold_batch','expanded_load_batch'):
            parent_report,parent_proof=restore_report('eco-endpoint-compare',38835900898,'ade9895f247c39b9439a169934bdf986b80be897bbd53b3259832b694ec9a450','36a4be4c1a5267a5cd971095579ac261cb39a6ef31df06ee8f70028894423fd3',OUT/'parent-census',('native-census.json','endpoint-slacks.tsv'))
            assert parent_report['source_unchanged'] and parent_report['candidate_routed_timing_reproduced']
            assert parent_report['candidate']['run']==38824521607 and parent_report['candidate']['summary_sha256']=='2567e3e86159187b5f6db0df8a1c2be663c3d66df9e20d4fc650f98fe9ad2db5'
            parent_meta,parent_rows=load_census(OUT/'parent-census');assert parent_meta['native_pin_mapping']==after['native_pin_mapping']
            result['parent_census']=parent_proof
            result['parent_endpoint_comparison']=compare_rows(parent_rows,new_rows)
            if args.profile=='measured_hold_batch':
                result['targeted_hold_changes']=targeted_hold_changes(parent_rows,new_rows)
                result['all_four_target_timing_passed']=all(r['target_timing_passed'] for r in result['targeted_hold_changes'])
            result['parent_new_violations']={phase:{edge:values['new_negative'] for edge,values in edges.items()} for phase,edges in result['parent_endpoint_comparison'].items()}
            save()

        result['all_constrained_endpoint_slacks_nonnegative']=all(v['worst']['negative_after']==0 for v in comparison.values())
        result['any_endpoint_regression']=any(v[e]['regressed'] for v in comparison.values() for e in ('rise','fall','worst'))
        result['any_loss_of_constraints']=any(v[e]['became_unconstrained'] for v in comparison.values() for e in ('rise','fall','worst'))
        result['endpoint_count']=len(after['endpoints']);result['endpoint_corner_delay_rows']=len(new_rows)
        if args.hold_paths:
            result['hold_conflict_paths']=measure_conflicts(OUT,expected,after,new_rows,candidate['routed_timing'])
        for name,pin in proof['restore']['selected_files'].items():assert sha(candidate_dir/name)==pin['sha256']
        assert all(sha(SOURCE/n)==v for n,v in source['outputs'].items()) and all(sha(Path(n))==v for n,v in source['protected_inputs'].items())
        result.update(status='COMPLETE_ALL_ENDPOINT_ROUTED_ECO_COMPARISON_NOT_SIGNOFF',source_unchanged=True,candidate_routed_timing_reproduced=True)
    except BaseException as error:result.update(status='FAIL_OR_ERROR',error=repr(error));raise
    finally:
        result['outputs']={str(p.relative_to(OUT)):sha(p) for p in OUT.rglob('*') if p.is_file() and p.name!='result.json'};save()

if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('--controls-only',action='store_true');parser.add_argument('--profile',choices=['two_buffer','control_three_buffer','measured_load_batch','protected_load_batch','measured_hold_batch','expanded_load_batch'])
    parser.add_argument('--hold-paths',action='store_true');parser.add_argument('--diagnose-semantics',action='store_true');parser.add_argument('--verify-graph-minima',action='store_true');parser.add_argument('--run',type=int);parser.add_argument('--summary-sha');parser.add_argument('--parts-sha');args=parser.parse_args()
    if args.controls_only:
        assert os.environ.get('GITHUB_ACTIONS')=='true';print(json.dumps(controls()))
    else:main(args)
