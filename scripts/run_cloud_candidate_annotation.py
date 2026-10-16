#!/usr/bin/env python3
# SPDX-FileCopyrightText: 2026 Hasan Melih Akbulut
# SPDX-License-Identifier: Apache-2.0
"""Source-bound native RC annotation diagnosis for completed physical candidates."""
import argparse,json,os,re,subprocess
from pathlib import Path
from refined_hold_targets import validate_child as validate_refined_hold,CHILD_FILES as REFINED_HOLD_FILES,TARGETS as REFINED_HOLD_TARGETS
from cloud_contact_release import validate_route_proof
from expanded_load_targets import validate_candidate as validate_expanded,EXTRA_FILES
from refined_load_targets import validate_candidate as validate_refined
from measured_hold_targets import validate_child,CHILD_FILES
import compare_cloud_routed_endpoints as source_reports
from run_cloud_candidate_geometry import PROFILES
from route_cloud_newer_postcts import sha
ROOT=Path(__file__).resolve().parents[1];OUT=ROOT/'cloud-candidate-annotation'
def main(args):
    assert os.environ.get('GITHUB_ACTIONS')=='true';OUT.mkdir(exist_ok=False);source_reports.OUT=OUT
    count,group,status=PROFILES[args.profile]
    result=dict(status='RUNNING',accepted=False,source_head=os.environ['GITHUB_SHA'],profile=args.profile,buffer_count=count,final_timing_complete=False,full_serial_phy_complete=False,
      scope='Classify every unannotated native driver in pinned completed fresh routed STA using exact candidateODB/SPEF and nativeODB netID plus exact OpenRCX writer names. Diagnostic only: not complete functional-interface coverage, qualifiedRC, SRAM characterization, allcorner finalSTA, geometry/LVS or fullPHY acceptance.')
    def save():(OUT/'result.json').write_text(json.dumps(result,indent=2)+'\n')
    save()
    try:
        selected=('routed.odb','candidate.nominal.spef','fresh-routed-sta.log','geometry-proof.json')
        if args.profile=='protected_load_batch':selected+=('protected-route-proof.json','fixed-source-summary.json')
        if args.profile=='measured_hold_batch':selected+=CHILD_FILES
        if args.profile=='refined_hold_batch':selected+=REFINED_HOLD_FILES
        if args.profile=='expanded_load_batch':selected+=EXTRA_FILES
        if args.profile=='refined_load_batch':selected+=EXTRA_FILES+('refined-driver-review-summary.json',)
        candidate,proof=source_reports.restore_report(group,args.run,args.summary_sha,args.parts_sha,OUT/'source',selected)
        assert candidate['status']=='COMPLETE_'+status+'_ROUTED_NOMINAL_TIMING_EXPERIMENT_NOT_SIGNOFF'
        assert candidate['source_run']==38809759501 and candidate['native_drt_drvs']==0
        assert candidate['original_routed_timing_reproduced'] and candidate['protected_source_unchanged']
        assert candidate['logic']['status']=='PASS within scope' and candidate['inversion_control']=='REJECTED'
        assert candidate['spef_integrity']['inconsistent_nets']==0
        assert len(candidate['geometry']['added'])==len(candidate['geometry']['changes'])==count
        assert json.loads((OUT/'source/geometry-proof.json').read_text())==candidate['geometry']
        if count!=2:assert candidate['profile']==args.profile and candidate['buffer_count']==count
        if args.profile=='measured_hold_batch':validate_child(candidate,OUT/'source')
        if args.profile=='refined_hold_batch':validate_refined_hold(candidate,OUT/'source')
        if args.profile=='expanded_load_batch':validate_expanded(candidate,OUT/'source')
        if args.profile=='refined_load_batch':validate_refined(candidate,OUT/'source')
        if args.profile=='protected_load_batch':
            protected=json.loads((OUT/'source/protected-route-proof.json').read_text());assert protected==candidate['protected_route_proof']
            validate_route_proof(protected,candidate)
            assert sha(OUT/'source/fixed-source-summary.json')=='029d754af843cf83c4dfe6753e43ab0eec228d2d42db0e07f1a910bebcc73e75'
        result['restoration']=proof;save()
        env=dict(os.environ,NSSOC_ANNOTATION_NATIVE='1',NSSOC_ANNOTATION_AUDIT_OUT=str(OUT/'source'),NSSOC_ANNOTATION_ADDED_BUFFERS=str(count),NSSOC_ANNOTATION_SPEF='candidate.nominal.spef',NSSOC_ANNOTATION_STA_LOG='fresh-routed-sta.log')
        with (OUT/'native-classification.log').open('w') as log:
            process=subprocess.run([os.environ['CLOUD_APPIMAGE'],'openroad','-exit','-python',str(ROOT/'scripts/audit_cloud_route_annotation.py')],stdout=log,stderr=subprocess.STDOUT,env=env)
        text=(OUT/'native-classification.log').read_text(errors='replace');print(text,flush=True)
        assert process.returncode==0 and not re.search(r'(?m)^\[ERROR|^Error:',text),'Native annotation classification failed'
        detail=json.loads((OUT/'source/driver-classification.json').read_text());assert detail['status']=='COMPLETE_SOURCE_BOUND_ANNOTATION_DIAGNOSIS_NOT_COVERAGE_ACCEPTANCE' and detail['spef_nets']==113556+count
        result['classification']={k:v for k,v in detail.items()if k!='drivers'}
        assert all(sha(OUT/'source'/n)==row['sha256']for n,row in proof['restore']['selected_files'].items())
        result.update(status='COMPLETE_CANDIDATE_NATIVE_RC_ANNOTATION_DIAGNOSIS_NOT_COVERAGE_ACCEPTANCE',source_unchanged=True)
    except BaseException as error:result.update(status='FAIL_OR_ERROR',error=repr(error));raise
    finally:
        result['outputs']={str(p.relative_to(OUT)):sha(p)for p in OUT.rglob('*')if p.is_file()and p.name!='result.json'};save()
if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--profile',choices=list(PROFILES),required=True);p.add_argument('--run',type=int,required=True);p.add_argument('--summary-sha',required=True);p.add_argument('--parts-sha',required=True);main(p.parse_args())
