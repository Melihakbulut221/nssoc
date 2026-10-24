#!/usr/bin/env python3
# SPDX-FileCopyrightText: 2026 Hasan Melih Akbulut
# SPDX-License-Identifier: Apache-2.0
"""Independent native geometry or annotation reviewer for the actual nine-size child."""
import argparse,copy,json,os,re,subprocess,sys
from pathlib import Path
import compare_cloud_routed_endpoints as reports
from route_cloud_newer_postcts import fetch,sha
ROOT=Path(__file__).resolve().parents[1]
PARENT_ODB='4a044ffdb4d92ec3e9150cb4a9696ed7dbfacc05361e64bc6b278259e6c3eeb4'
PARENT_SUMMARY='765b113220ba12b3267ee50cd1ff02bfac7eb89a336c41ba77632c7ccd401e6e'
SCREEN_SHA='d8b43beae0667c6eaa64f5cd80c9c8466eb20734bfc7d0aa6822e66d8513f751'
TARGETS={
'place29858':('sg13g2_buf_1','sg13g2_buf_2'),
'$abc$1705011$auto$blifparse.cc:397:parse_blif$1750764':('sg13g2_and4_1','sg13g2_and4_2'),
'place31700':('sg13g2_buf_1','sg13g2_buf_2'),
'place32232':('sg13g2_buf_1','sg13g2_buf_2'),
'$abc$1705011$auto$blifparse.cc:397:parse_blif$1749223':('sg13g2_nand2_1','sg13g2_nand2_2'),
'place29578':('sg13g2_buf_2','sg13g2_buf_4'),
'$abc$1705011$auto$blifparse.cc:397:parse_blif$1747241':('sg13g2_nor2_1','sg13g2_nor2_2'),
'place35278':('sg13g2_buf_2','sg13g2_buf_4'),
'place37065':('sg13g2_buf_1','sg13g2_buf_2')}
def validate_screen(s):
    assert s['status']=='COMPLETE_AVAILABLE_DRIVER_FROZEN_RC_SIZING_SCREEN_NOT_PHYSICAL_ACCEPTANCE'
    assert s['physical_source']['summary_sha256']==PARENT_SUMMARY and s['physical_source']['run']==38896397749
    assert s['baseline_all_endpoint_rows_reproduced']and s['source_unchanged']and s['endpoint_count']==22544 and s['endpoint_corner_delay_rows']==135264
    changes=s['preparation']['changes'];assert len(changes)==9
    actual={r['pin'].rsplit('/',1)[0]:(r['master'],r['replacement'])for r in changes}
    assert actual==TARGETS,'Candidate recipe differs from actual measured nine sizes'
    assert s['preparation']['requested_count']==14 and len(s['preparation']['unavailable'])==5
    assert not s['accepted']and not s['physical_candidate']and s['physical_validation_required']
def controls(directory):
    directory.mkdir(exist_ok=False)
    url='https://github.com/Melihakbulut221/nssoc/releases/download/cloud-results-38917800540-1-route234-sizing-screen/route234-sizing-screen-38917800540-1.summary.json'
    fetch(url,SCREEN_SHA,directory/'screen.json');s=json.loads((directory/'screen.json').read_text());validate_screen(s)
    faults=[]
    for kind in ('wrong_parent','missing_change','unavailable_master','false_physical_claim'):
        bad=copy.deepcopy(s)
        if kind=='wrong_parent':bad['physical_source']['run']=38880596259
        elif kind=='missing_change':bad['preparation']['changes'].pop()
        elif kind=='unavailable_master':bad['preparation']['changes'][0]['replacement']='sg13g2_nand4_2'
        else:bad['physical_candidate']=True
        try:validate_screen(bad)
        except AssertionError:faults.append(kind)
        else:raise AssertionError('Invalid sizing provenance accepted')
    return dict(actual_screen_sha256=SCREEN_SHA,exact_real_targets=9,negative_controls=faults)
def main(args):
    assert os.environ.get('GITHUB_ACTIONS')=='true'
    if args.controls_only:print(json.dumps(controls(ROOT/'cloud-nine-size-controls')));return
    assert args.kind in ('geometry','annotation')
    out=ROOT/('cloud-nine-size-'+args.kind);out.mkdir(exist_ok=False);reports.OUT=out
    result=dict(status='RUNNING',accepted=False,source_head=os.environ['GITHUB_SHA'],kind=args.kind,source_run=args.run,final_timing_complete=False,full_serial_phy_complete=False,scope='Independent actual9size ODB/parent census and signal geometry or RC annotation. NoPG/CUT/spacing/internalmacro/transistorLVS/qualifiedRC/SRAM/ESD/fullPHY or timing acceptance.')
    def save():(out/'result.json').write_text(json.dumps(result,indent=2)+'\n')
    def run(command,label,env):
        with (out/(label+'.log')).open('w')as log:
            p=subprocess.run(command,stdout=log,stderr=subprocess.STDOUT,env=env)
        text=(out/(label+'.log')).read_text(errors='replace');print(label,text[-5000:],flush=True)
        assert p.returncode==0 and not re.search(r'(?m)^\[ERROR|^Error:',text),(label,p.returncode)
        return text
    save()
    try:
        result['controls']=controls(out/'controls');save()
        selected=('routed.odb','parent/routed.odb','geometry-proof.json','post-route-geometry.json','sizing-screen.json','candidate.nominal.spef','fresh-routed-sta.log')
        r,proof=reports.restore_report('route234-sized-eco',args.run,args.summary_sha,args.parts_sha,out/'source',selected)
        assert r['status']=='COMPLETE_NINE_SIZED_CELLS_ROUTED_FRESH_NOMINAL_RC_ALL_ENDPOINTS_NOT_SIGNOFF'
        assert r['source_run']==38896397749 and r['parent']['run']==38896397749 and r['parent']['summary_sha256']==PARENT_SUMMARY
        assert r['sized_cells']==9 and r['added_cells']==0 and r['source_unchanged']and r['parent_timing_reproduced']
        assert r['native_drt_drvs']==0 and r['logic']['status']=='PASS within scope'and r['inversion_control']=='REJECTED'
        assert r['spef_integrity']['inconsistent_nets']==0 and r['endpoint_count']==22544 and r['endpoint_corner_delay_rows']==135264
        assert not r['accepted']and not r['final_timing_complete']
        assert sha(out/'source/sizing-screen.json')==SCREEN_SHA;validate_screen(json.loads((out/'source/sizing-screen.json').read_text()))
        assert json.loads((out/'source/geometry-proof.json').read_text())==r['geometry']
        assert r['post_route_geometry']==json.loads((out/'source/post-route-geometry.json').read_text())
        assert r['post_route_geometry']['routed_odb_sha256']==sha(out/'source/routed.odb')
        result['restoration']=proof;result['routed_odb_sha256']=sha(out/'source/routed.odb');save()
        env=dict(os.environ,NSSOC_NINE_REVIEW_OUT=str(out),NSSOC_ROUTE_AUDIT_OUT=str(out),NSSOC_GEOMETRY_ADDED_BUFFERS='234',NSSOC_ANNOTATION_NATIVE='1',NSSOC_ANNOTATION_AUDIT_OUT=str(out/'source'),NSSOC_ANNOTATION_ADDED_BUFFERS='234',NSSOC_ANNOTATION_SPEF='candidate.nominal.spef',NSSOC_ANNOTATION_STA_LOG='fresh-routed-sta.log')
        run([os.environ['CLOUD_APPIMAGE'],'openroad','-exit','-python',str(ROOT/'scripts/audit_nine_size_candidate_native.py')],'native-nine-audit',env)
        result['native_census']=json.loads((out/'native-nine-audit.json').read_text());save()
        if args.kind=='geometry':
            script=out/'placement-antenna.tcl';script.write_text(f'read_db {{{out/"source/routed.odb"}}}\nset_thread_count 2\ncheck_placement -verbose\nset n [check_antennas -verbose -report_file {{{out/"antenna.rpt"}}}]\nputs "NSSOC_ANTENNA_RETURN $n"\n')
            text=run([os.environ['CLOUD_APPIMAGE'],'openroad','-exit',str(script)],'placement-antenna',env)
            result['antenna_report_lines']=[l for l in text.splitlines()if 'violation'in l.lower()]
            run([os.environ['CLOUD_APPIMAGE'],'openroad','-exit','-python',str(ROOT/'scripts/export_cloud_routed_shapes.py')],'export',env)
            export=json.loads((out/'export.json').read_text());assert export['instances']==114025 and export['nets']==114097 and export['exported_nets']==113790
            run([sys.executable,str(ROOT/'scripts/check_cloud_routed_shapes.py'),'--directory',str(out)],'continuity',env)
            run([sys.executable,str(ROOT/'scripts/check_cloud_signal_contacts.py'),'--directory',str(out)],'contacts',env)
            result['export']=export;result['continuity']=json.loads((out/'continuity.json').read_text());result['contacts']=json.loads((out/'signal-contacts.json').read_text())
            assert result['continuity']['checked']==result['contacts']['net_count']==113790
            assert result['continuity']['total_shapes']==result['contacts']['shape_count']==export['shapes']
        else:
            run([os.environ['CLOUD_APPIMAGE'],'openroad','-exit','-python',str(ROOT/'scripts/audit_cloud_route_annotation.py')],'annotation',env)
            detail=json.loads((out/'source/driver-classification.json').read_text())
            assert detail['spef_nets']==113790
            result['classification']={k:v for k,v in detail.items()if k!='drivers'}
        assert all(sha(out/'source'/n)==v['sha256']for n,v in proof['restore']['selected_files'].items())
        result.update(status='COMPLETE_INDEPENDENT_NINE_SIZE_'+args.kind.upper()+'_SCREEN_NOT_SIGNOFF',source_unchanged=True)
    except BaseException as error:result.update(status='FAIL_OR_ERROR',error=repr(error));raise
    finally:
        result['outputs']={str(p.relative_to(out)):sha(p)for p in out.rglob('*')if p.is_file()and p.name!='result.json'};save()
if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--controls-only',action='store_true');p.add_argument('--kind',choices=('geometry','annotation'));p.add_argument('--run',type=int);p.add_argument('--summary-sha');p.add_argument('--parts-sha');main(p.parse_args())
