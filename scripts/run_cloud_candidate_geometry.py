#!/usr/bin/env python3
# SPDX-FileCopyrightText: 2026 Hasan Melih Akbulut
# SPDX-License-Identifier: Apache-2.0
"""Independent geometry/continuity/contact/antenna screen of completed routed ECO."""
import argparse,json,os,re,subprocess,sys
from pathlib import Path
from cloud_contact_release import validate_route_proof
from expanded_load_targets import validate_candidate as validate_expanded,EXTRA_FILES
from refined_load_targets import validate_candidate as validate_refined
from measured_hold_targets import validate_child,CHILD_FILES
import compare_cloud_routed_endpoints as source_reports
from route_cloud_newer_postcts import sha
ROOT=Path(__file__).resolve().parents[1];OUT=ROOT/'cloud-candidate-geometry'
PROFILES={'two_buffer':(2,'critical-load-eco','TWO_BUFFER'),'control_three_buffer':(3,'control-load-eco','THREE_BUFFER'),'measured_load_batch':(50,'measured-load-eco','MEASURED_LOAD_BATCH'),'protected_load_batch':(50,'protected-load-eco','PROTECTED_LOAD_BATCH'),'measured_hold_batch':(54,'measured-hold-eco','MEASURED_HOLD_BATCH'),'expanded_load_batch':(110,'expanded-load-eco','EXPANDED_LOAD_BATCH'),'refined_load_batch':(141,'refined-load-eco','REFINED_LOAD_BATCH')}

def main(args):
    assert os.environ.get('GITHUB_ACTIONS')=='true';OUT.mkdir(exist_ok=False);source_reports.OUT=OUT
    count,group,status=PROFILES[args.profile]
    result=dict(status='RUNNING',accepted=False,source_head=os.environ['GITHUB_SHA'],profile=args.profile,buffer_count=count,final_timing_complete=False,full_serial_phy_complete=False,
      scope='Actual completed candidateODB: native placement/antenna, all exported signal geometry, native-width/length guards, continuity and cross-net same-layer contacts. NoPG/CUT/internalmacro/spacing/ESD/transistorLVS/qualifiedRC or fullPHY acceptance. Fullendpointtiming remains separate.')
    def save():(OUT/'result.json').write_text(json.dumps(result,indent=2)+'\n')
    def run(command,label):
        env=dict(os.environ,NSSOC_ROUTE_AUDIT_OUT=str(OUT),NSSOC_GEOMETRY_ADDED_BUFFERS=str(count))
        with (OUT/(label+'.log')).open('w') as log:
            p=subprocess.Popen(command,stdout=subprocess.PIPE,stderr=subprocess.STDOUT,text=True,bufsize=1,env=env)
            for line in p.stdout:log.write(line);log.flush();print('['+label+'] '+line,end='',flush=True)
            code=p.wait()
        text=(OUT/(label+'.log')).read_text(errors='replace');assert code==0 and not re.search(r'(?m)^\[ERROR|^Error:',text),(label,code)
        result[label+'_warnings']=[l for l in text.splitlines()if '[WARNING' in l];save();return text
    save()
    try:
        selection=('routed.odb','geometry-proof.json')
        if args.profile=='protected_load_batch':selection+=('protected-route-proof.json','fixed-source-summary.json')
        if args.profile=='measured_hold_batch':selection+=CHILD_FILES
        if args.profile=='expanded_load_batch':selection+=EXTRA_FILES
        if args.profile=='refined_load_batch':selection+=EXTRA_FILES+('refined-driver-review-summary.json',)
        candidate,proof=source_reports.restore_report(group,args.run,args.summary_sha,args.parts_sha,OUT/'source',selection)
        assert candidate['status']=='COMPLETE_'+status+'_ROUTED_NOMINAL_TIMING_EXPERIMENT_NOT_SIGNOFF'
        assert candidate['source_run']==38809759501 and candidate['native_drt_drvs']==0
        assert candidate['original_routed_timing_reproduced'] and candidate['protected_source_unchanged']
        assert candidate['logic']['status']=='PASS within scope' and candidate['inversion_control']=='REJECTED'
        assert len(candidate['geometry']['added'])==len(candidate['geometry']['changes'])==count
        assert json.loads((OUT/'source/geometry-proof.json').read_text())==candidate['geometry']
        if count!=2:assert candidate['profile']==args.profile and candidate['buffer_count']==count
        if args.profile=='measured_hold_batch':validate_child(candidate,OUT/'source')
        if args.profile=='expanded_load_batch':validate_expanded(candidate,OUT/'source')
        if args.profile=='refined_load_batch':validate_refined(candidate,OUT/'source')
        if args.profile=='protected_load_batch':
            protected=json.loads((OUT/'source/protected-route-proof.json').read_text());assert protected==candidate['protected_route_proof']
            validate_route_proof(protected,candidate)
            assert sha(OUT/'source/fixed-source-summary.json')=='029d754af843cf83c4dfe6753e43ab0eec228d2d42db0e07f1a910bebcc73e75'
        result['restoration']=proof;result['routed_odb_sha256']=sha(OUT/'source/routed.odb');save()
        tcl=OUT/'placement-antenna.tcl';tcl.write_text(f'read_db {{{OUT/"source/routed.odb"}}}\nset_thread_count 2\ncheck_placement -verbose\nset n [check_antennas -verbose -report_file {{{OUT/"antenna.rpt"}}}]\nputs "NSSOC_ANTENNA_RETURN $n"\n')
        text=run([os.environ['CLOUD_APPIMAGE'],'openroad','-exit',str(tcl)],'placement-antenna')
        result['antenna_native_return']=re.findall(r'^NSSOC_ANTENNA_RETURN (.*)$',text,re.M);assert len(result['antenna_native_return'])==1
        result['antenna_report_lines']=[l for l in text.splitlines()if 'violation' in l.lower()];save()
        run([os.environ['CLOUD_APPIMAGE'],'openroad','-exit','-python',str(ROOT/'scripts/export_cloud_routed_shapes.py')],'export')
        export=json.loads((OUT/'export.json').read_text());assert export['instances']==113791+count and export['nets']==113863+count and export['exported_nets']==113556+count
        result['geometry_export']=export;save()
        run([sys.executable,str(ROOT/'scripts/check_cloud_routed_shapes.py'),'--directory',str(OUT)],'continuity')
        result['continuity']=json.loads((OUT/'continuity.json').read_text());save()
        run([sys.executable,str(ROOT/'scripts/check_cloud_signal_contacts.py'),'--directory',str(OUT)],'signal-contacts')
        result['contacts']=json.loads((OUT/'signal-contacts.json').read_text())
        assert result['continuity']['checked']==result['contacts']['net_count']==113556+count
        assert result['continuity']['total_shapes']==result['contacts']['shape_count']==export['shapes']
        assert all(sha(OUT/'source'/n)==row['sha256']for n,row in proof['restore']['selected_files'].items())
        result.update(status='COMPLETE_ROUTED_CANDIDATE_SIGNAL_GEOMETRY_AND_ANTENNA_SCREEN_NOT_SIGNOFF',source_unchanged=True)
    except BaseException as error:result.update(status='FAIL_OR_ERROR',error=repr(error));raise
    finally:
        result['outputs']={str(p.relative_to(OUT)):sha(p)for p in OUT.rglob('*')if p.is_file()and p.name!='result.json'};save()
if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--profile',choices=list(PROFILES),required=True);p.add_argument('--run',type=int,required=True);p.add_argument('--summary-sha',required=True);p.add_argument('--parts-sha',required=True);main(p.parse_args())
