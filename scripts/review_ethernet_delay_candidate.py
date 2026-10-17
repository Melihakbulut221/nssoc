#!/usr/bin/env python3
# SPDX-FileCopyrightText: 2026 Hasan Melih Akbulut
# SPDX-License-Identifier: Apache-2.0
"""Independent native geometry or annotation reviewer for one actual Ethernet delay-master replacement."""
import argparse,copy,json,os,re,subprocess,sys
from pathlib import Path
import compare_cloud_routed_endpoints as reports
from route_cloud_newer_postcts import fetch,sha
ROOT=Path(__file__).resolve().parents[1]
def main(args):
    assert os.environ.get('GITHUB_ACTIONS')=='true'
    assert args.kind in ('geometry','annotation')
    out=ROOT/('cloud-ethernet-delay-'+args.kind);out.mkdir(exist_ok=False);reports.OUT=out
    result=dict(status='RUNNING',accepted=False,source_head=os.environ['GITHUB_SHA'],kind=args.kind,source_run=args.run,final_timing_complete=False,full_serial_phy_complete=False,scope='Independent actual Ethernet delay-master ODB/parent census and signal geometry or RC annotation. NoPG/CUT/spacing/internalmacro/transistorLVS/qualifiedRC/SRAM/ESD/fullPHY or timing acceptance.')
    def save():(out/'result.json').write_text(json.dumps(result,indent=2)+'\n')
    def run(command,label,env):
        with (out/(label+'.log')).open('w')as log:
            p=subprocess.run(command,stdout=log,stderr=subprocess.STDOUT,env=env)
        text=(out/(label+'.log')).read_text(errors='replace');print(label,text[-5000:],flush=True)
        assert p.returncode==0 and not re.search(r'(?m)^\[ERROR|^Error:',text),(label,p.returncode)
        return text
    save()
    try:
        selected=('routed.odb','parent/routed.odb','geometry-proof.json','post-route-geometry.json','candidate.nominal.spef','fresh-routed-sta.log')
        r,proof=reports.restore_report('ethernet-hold-eco',args.run,args.summary_sha,args.parts_sha,out/'source',selected)
        assert r['status']=='COMPLETE_SINGLE_ETHERNET_DELAY_ROUTED_FRESH_RC_ALL_ENDPOINTS_NOT_SIGNOFF'
        assert r['source_run']==38957249404 and r['parent']['run']==38957249404 and r['parent']['summary_sha256']=='8fa70ddcf57970bcb4b726f68ecad6ebeb0c5389e9027f1dba1773906645b67b'
        assert r['sized_cells']==1 and r['added_cells']==0 and r['source_unchanged']and r['parent_timing_reproduced']
        assert r['native_drt_drvs']==0 and r['logic']['status']=='PASS within scope'and r['inversion_control']=='REJECTED'
        assert r['spef_integrity']['inconsistent_nets']==0 and r['endpoint_count']==22544 and r['endpoint_corner_delay_rows']==135264
        assert not r['accepted']and not r['final_timing_complete']
        assert json.loads((out/'source/geometry-proof.json').read_text())==r['geometry']
        assert r['post_route_geometry']==json.loads((out/'source/post-route-geometry.json').read_text())
        assert r['outputs']['routed.odb']==sha(out/'source/routed.odb')
        result['restoration']=proof;result['routed_odb_sha256']=sha(out/'source/routed.odb');save()
        env=dict(os.environ,NSSOC_ETHERNET_CHILD_SHA=r['outputs']['routed.odb'],NSSOC_NINE_REVIEW_OUT=str(out),NSSOC_ROUTE_AUDIT_OUT=str(out),NSSOC_GEOMETRY_ADDED_BUFFERS='240',NSSOC_ANNOTATION_NATIVE='1',NSSOC_ANNOTATION_AUDIT_OUT=str(out/'source'),NSSOC_ANNOTATION_ADDED_BUFFERS='240',NSSOC_ANNOTATION_SPEF='candidate.nominal.spef',NSSOC_ANNOTATION_STA_LOG='fresh-routed-sta.log')
        run([os.environ['CLOUD_APPIMAGE'],'openroad','-exit','-python',str(ROOT/'scripts/audit_ethernet_delay_candidate_native.py')],'native-nine-audit',env)
        result['native_census']=json.loads((out/'native-nine-audit.json').read_text());save()
        if args.kind=='geometry':
            script=out/'placement-antenna.tcl';script.write_text(f'read_db {{{out/"source/routed.odb"}}}\nset_thread_count 2\ncheck_placement -verbose\nset n [check_antennas -verbose -report_file {{{out/"antenna.rpt"}}}]\nputs "NSSOC_ANTENNA_RETURN $n"\n')
            text=run([os.environ['CLOUD_APPIMAGE'],'openroad','-exit',str(script)],'placement-antenna',env)
            result['antenna_report_lines']=[l for l in text.splitlines()if 'violation'in l.lower()]
            run([os.environ['CLOUD_APPIMAGE'],'openroad','-exit','-python',str(ROOT/'scripts/export_cloud_routed_shapes.py')],'export',env)
            export=json.loads((out/'export.json').read_text());assert export['instances']==114031 and export['nets']==114103 and export['exported_nets']==113796
            run([sys.executable,str(ROOT/'scripts/check_cloud_routed_shapes.py'),'--directory',str(out)],'continuity',env)
            run([sys.executable,str(ROOT/'scripts/check_cloud_signal_contacts.py'),'--directory',str(out)],'contacts',env)
            result['export']=export;result['continuity']=json.loads((out/'continuity.json').read_text());result['contacts']=json.loads((out/'signal-contacts.json').read_text())
            assert result['continuity']['checked']==result['contacts']['net_count']==113796
            assert result['continuity']['total_shapes']==result['contacts']['shape_count']==export['shapes']
        else:
            run([os.environ['CLOUD_APPIMAGE'],'openroad','-exit','-python',str(ROOT/'scripts/audit_cloud_route_annotation.py')],'annotation',env)
            detail=json.loads((out/'source/driver-classification.json').read_text())
            assert detail['spef_nets']==113796
            result['classification']={k:v for k,v in detail.items()if k!='drivers'}
        assert all(sha(out/'source'/n)==v['sha256']for n,v in proof['restore']['selected_files'].items())
        result.update(status='COMPLETE_INDEPENDENT_ETHERNET_DELAY_'+args.kind.upper()+'_SCREEN_NOT_SIGNOFF',source_unchanged=True)
    except BaseException as error:result.update(status='FAIL_OR_ERROR',error=repr(error));raise
    finally:
        result['outputs']={str(p.relative_to(out)):sha(p)for p in out.rglob('*')if p.is_file()and p.name!='result.json'};save()
if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--kind',choices=('geometry','annotation'));p.add_argument('--run',type=int);p.add_argument('--summary-sha');p.add_argument('--parts-sha');main(p.parse_args())
