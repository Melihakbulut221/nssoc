#!/usr/bin/env python3
# SPDX-FileCopyrightText: 2026 Hasan Melih Akbulut
# SPDX-License-Identifier: Apache-2.0
"""Independent exact ODB/SPEF review after changed-pin-compatible fresh extraction."""
import argparse,json,os,re,subprocess
from pathlib import Path
import compare_cloud_routed_endpoints as reports
from route_cloud_newer_postcts import sha
ROOT=Path(__file__).resolve().parents[1]
def main(args):
    assert os.environ.get('GITHUB_ACTIONS')=='true'and args.kind=='annotation'
    out=ROOT/'cloud-ethernet-compatible-annotation';out.mkdir(exist_ok=False);reports.OUT=out
    r=dict(status='RUNNING',accepted=False,source_head=os.environ['GITHUB_SHA'],kind=args.kind,source_run=args.run,final_timing_complete=False,full_serial_phy_complete=False,scope='Independent exact native one-master census and actual SPEF/driver annotation. Scoped three-corner measured hold0 is not final timing acceptance: setup, unconstrained endpoints, qualifiedRC, foundryDRC/LVS, fullPHY remain open.')
    def save():(out/'result.json').write_text(json.dumps(r,indent=2)+'\n')
    def run(cmd,name,env):
        with(out/(name+'.log')).open('w')as f:p=subprocess.run(cmd,stdout=f,stderr=subprocess.STDOUT,env=env)
        text=(out/(name+'.log')).read_text(errors='replace');print(name,text[-4000:],flush=True)
        assert p.returncode==0 and not re.search(r'(?m)^\[ERROR|^Error:',text),(name,p.returncode)
    save()
    try:
        selected=('routed.odb','parent/routed.odb','candidate.nominal.spef','fresh-routed-sta.log','geometry-source/native-nine-audit.json','geometry-source/pin-compatibility.json')
        source,proof=reports.restore_report('ethernet-compatible-rc',args.run,args.summary_sha,args.parts_sha,out/'source',selected)
        assert source['status']=='COMPLETE_PIN_COMPATIBLE_ETHERNET_ROUTES_FRESH_RC_ALL_ENDPOINTS_NOT_SIGNOFF'
        assert source['source_head']=='b857ac77a30d76646d02ca245168d79dfe77c059'and source['source_unchanged']and source['no_routing_performed']
        assert source['source_run']==38957249404 and source['geometry_run']==38992292456 and source['parent_timing_reproduced']
        assert source['sized_cells']==1 and source['added_cells']==0 and source['endpoint_count']==22544 and source['endpoint_corner_delay_rows']==135264
        assert source['spef_integrity']['inconsistent_nets']==0 and not source['accepted']and not source['final_timing_complete']
        assert source['candidate_odb_sha256']==source['outputs']['routed.odb']==sha(out/'source/routed.odb')=='49a805c66e904b534dd846bcca58070feaeac77dfe1427f7937e89427b0085e8'
        assert source['original_geometry_equality_gate']=='FAILED_RETAINED'
        compatibility=json.loads((out/'source/geometry-source/pin-compatibility.json').read_text());assert compatibility==source['actual_pin_route_compatibility']
        assert compatibility['status']=='COMPLETE_ACTUAL_PIN_ROUTE_COMPATIBILITY_SCREEN_NOT_SIGNOFF'and not compatibility['candidate_route_failures']and not compatibility['candidate_power_errors']
        prior=json.loads((out/'source/geometry-source/native-nine-audit.json').read_text());assert prior==source['native_geometry']['native_census']
        assert prior['status']=='PASS_INDEPENDENT_SINGLE_ETHERNET_DELAY_NATIVE_CENSUS_NOT_SIGNOFF'and prior['changed_masters']==1 and prior['added']==0
        assert len(prior['changes'])==1;change=prior['changes'][0]
        displacement=[b-a for a,b in zip(change['before']['location'],change['after']['location'],strict=True)];assert displacement==[0,0]
        # The native auditor accepts this explicit metadata projection of the
        # already source-hashed earlier native receipt. It still independently
        # reloads both original ODBs and applies the real disconnection/master
        # faults. No new geometric measurement is fabricated by this projection.
        receipt=dict(changes=[dict(change,displacement_dbu=displacement)])
        (out/'source/geometry-proof.json').write_text(json.dumps(receipt,indent=2)+'\n')
        r['projected_receipt_source']=dict(path='geometry-source/native-nine-audit.json',sha256=sha(out/'source/geometry-source/native-nine-audit.json'),derived_sha256=sha(out/'source/geometry-proof.json'))
        r.update(restoration=proof,routed_odb_sha256=source['candidate_odb_sha256'],producer_timing={k:v['worst']for k,v in source['endpoint_comparison'].items()},original_geometry_equality_gate='FAILED_RETAINED')
        env=dict(os.environ,NSSOC_ETHERNET_CHILD_SHA=source['candidate_odb_sha256'],NSSOC_NINE_REVIEW_OUT=str(out),NSSOC_ANNOTATION_NATIVE='1',NSSOC_ANNOTATION_AUDIT_OUT=str(out/'source'),NSSOC_ANNOTATION_ADDED_BUFFERS='240',NSSOC_ANNOTATION_SPEF='candidate.nominal.spef',NSSOC_ANNOTATION_STA_LOG='fresh-routed-sta.log')
        run([os.environ['CLOUD_APPIMAGE'],'openroad','-exit','-python',str(ROOT/'scripts/audit_ethernet_delay_candidate_native.py')],'native-census',env)
        r['native_census']=json.loads((out/'native-nine-audit.json').read_text());save()
        run([os.environ['CLOUD_APPIMAGE'],'openroad','-exit','-python',str(ROOT/'scripts/audit_cloud_route_annotation.py')],'annotation',env)
        detail=json.loads((out/'source/driver-classification.json').read_text());assert detail['spef_nets']==113796
        r['classification']={k:v for k,v in detail.items()if k!='drivers'}
        assert all(sha(out/'source'/n)==v['sha256']for n,v in proof['restore']['selected_files'].items())
        r.update(status='COMPLETE_INDEPENDENT_ETHERNET_COMPATIBLE_ANNOTATION_SCREEN_NOT_SIGNOFF',source_unchanged=True)
    except BaseException as e:r.update(status='FAIL_OR_ERROR',error=repr(e));raise
    finally:
        r['outputs']={str(p.relative_to(out)):sha(p)for p in out.rglob('*')if p.is_file()and p!=out/'result.json'};save()
if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--kind',choices=('annotation',),required=True);p.add_argument('--run',type=int,required=True);p.add_argument('--summary-sha',required=True);p.add_argument('--parts-sha',required=True);main(p.parse_args())
