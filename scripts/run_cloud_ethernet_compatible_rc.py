#!/usr/bin/env python3
# SPDX-FileCopyrightText: 2026 Hasan Melih Akbulut
# SPDX-License-Identifier: Apache-2.0
"""Fresh extraction after actual changed-pin compatibility screens; strict equality failure retained."""
import argparse,json,os,re,shutil,subprocess,sys,tarfile
from pathlib import Path
import compare_cloud_routed_endpoints as reports
from route_cloud_newer_postcts import fetch,sha,native_ndr_screen
from run_cloud_branch_hold_eco import guide_blocks
from read_opensta_phase_slacks import parse_phases
from native_graph_path_coverage import verify
ROOT=Path(__file__).resolve().parents[1];OUT=ROOT/'cloud-ethernet-compatible-rc';SOURCE=ROOT/'cloud-routed-extraction'
SUMMARY='8fa70ddcf57970bcb4b726f68ecad6ebeb0c5389e9027f1dba1773906645b67b';PARTS='d41a2ecf54bb782b439d8c9e46f005ff964d682602167910672d81fb6a09e290'
def main():
    p=argparse.ArgumentParser();p.add_argument('--geometry-run',type=int,required=True);p.add_argument('--geometry-summary',required=True);p.add_argument('--geometry-parts',required=True);args=p.parse_args()
    assert os.environ.get('GITHUB_ACTIONS')=='true';OUT.mkdir(exist_ok=False);reports.OUT=OUT
    result=dict(status='RUNNING',accepted=False,source_head=os.environ['GITHUB_SHA'],source_run=38957249404,sized_cells=1,added_cells=0,final_timing_complete=False,full_serial_phy_complete=False,scope='Exact pre-reroute sd1->sd2 ODB after actual planar pin/PG contacts, route/obstruction default-spacing and all-signal continuity/contact screens. Original identical-shape gate remains FAILED; no foundry DRC acceptance inferred. No new routing or sizing. Fresh nominalRC and all22544endpoint comparison under original constraints/corners. Source geometry is mandatory; independent annotation, fullLVS/DRC/qualifiedRC/fullPHY remain required, no signoff inferred')
    def save():(OUT/'result.json').write_text(json.dumps(result,indent=2)+'\n')
    def run(args,label,env=None,expect=True):
        with (OUT/(label+'.log')).open('w')as log:
            proc=subprocess.Popen(args,stdout=subprocess.PIPE,stderr=subprocess.STDOUT,text=True,bufsize=1,env=env)
            for line in proc.stdout:log.write(line);log.flush();print('['+label+'] '+line,end='',flush=True)
            code=proc.wait()
        text=(OUT/(label+'.log')).read_text(errors='replace')
        if expect:assert code==0 and not re.search(r'(?m)^\[ERROR|^Error:',text),(label,code,text[-3000:])
        return code,text
    def tcl(text,label):
        path=OUT/(label+'.tcl');path.write_text(text)
        return run([os.environ['CLOUD_APPIMAGE'],'openroad','-exit',str(path)],label)[1]
    save()
    try:
        parent,proof=reports.restore_report('nine-size-hold-eco',38957249404,SUMMARY,PARTS,OUT/'parent',('routed.odb','candidate.nominal.spef','candidate.guide','fresh-routed-sta.tcl','geometry-proof.json','routed-census/native-census.json','routed-census/endpoint-slacks.tsv'))
        assert parent['status']=='COMPLETE_SIX_SHORT_BRANCH_DELAYS_ROUTED_FRESH_RC_ALL_ENDPOINTS_NOT_SIGNOFF'and parent['source_unchanged']and parent['native_drt_drvs']==0
        assert parent['logic']['status']=='PASS within scope'and parent['inversion_control']=='REJECTED'
        result['parent']=proof
        root='https://github.com/Melihakbulut221/nssoc/releases/download/'
        fetch(root+'cloud-results-38976347463-1-ethernet-hold-screen/ethernet-hold-screen-38976347463-1.summary.json','21f1283f2939110cfed3df86e172e6208237b0491b2f6c253e022b7ac8ea3736',OUT/'sizing-screen.json')
        screen=json.loads((OUT/'sizing-screen.json').read_text())
        assert screen['source_unchanged']and screen['baseline_all_endpoint_rows_reproduced']
        assert screen['preparation']['source_odb_sha256']==parent['outputs']['routed.odb']
        variant=next(r for r in screen['variants']if r['replacement']=='sg13g2_dlygate4sd2_1')
        assert variant['logic']['status']=='PASS within scope'and variant['inversion_control']=='REJECTED'
        assert variant['viable_frozen_rc_screen']and variant['endpoint_count']==22544 and variant['endpoint_corner_delay_rows']==135264
        result['frozen_screen']=dict(run=38976347463,summary_sha256=sha(OUT/'sizing-screen.json'),variant=variant)
        fetch(root+'cloud-results-38977048618-1-six-hold-geometry/six-hold-geometry-38977048618-1.summary.json','7f5d12e12325a49e48c22de427e9e59fb28a4ff53fc6120407450d82b70b0741',OUT/'parent-geometry-summary.json')
        geometry=json.loads((OUT/'parent-geometry-summary.json').read_text())
        assert geometry['source_unchanged']and geometry['restoration']['run']==38957249404 and geometry['routed_odb_sha256']==parent['outputs']['routed.odb']
        assert geometry['continuity']['failed']==0 and geometry['contacts']['no_cross_net_contacts']
        result['parent_antenna']=geometry['antenna_report_lines'];save()
        before,old_rows=reports.load_census(OUT/'parent/routed-census')
        fetch(reports.BASE+'.summary.json',reports.SUMMARY_SHA,OUT/'original-summary.json');old=json.loads((OUT/'original-summary.json').read_text())
        packed=OUT/'original.tar.gz';fetch(reports.BASE+'.tar.gz.part0000',reports.ARCHIVE_SHA,packed);assert packed.stat().st_size==225682086 and not SOURCE.exists()
        with tarfile.open(packed)as archive:
            for m in archive:
                p=Path(m.name);assert not p.is_absolute()and'..'not in p.parts and p.parts[0]==SOURCE.name and(m.isfile()or m.isdir());archive.extract(m,ROOT,filter='data')
        packed.unlink();assert sha(SOURCE/'result.json')==reports.SUMMARY_SHA
        assert all(sha(SOURCE/n)==v for n,v in old['outputs'].items())and all(sha(Path(n))==v for n,v in old['protected_inputs'].items())
        original=(SOURCE/'actual-routed-sta.tcl').read_text()
        stored=original.replace(str(SOURCE/'source/routed.odb'),str(ROOT/'cloud-nine-size-hold-eco/routed.odb')).replace(str(SOURCE/'actual-route.nominal.spef'),str(ROOT/'cloud-nine-size-hold-eco/candidate.nominal.spef'))
        assert stored==(OUT/'parent/fresh-routed-sta.tcl').read_text()
        expected=stored.replace(str(ROOT/'cloud-nine-size-hold-eco'),str(OUT/'parent'))
        phases=parse_phases(tcl(expected,'reproduce-parent'),'CORNER')
        for k,v in parent['routed_timing'].items():assert phases[k]['groups']==v['groups']
        result['parent_timing_reproduced']=True;save()
        geometry,geometry_proof=reports.restore_report('ethernet-pin-compatible',args.geometry_run,args.geometry_summary,args.geometry_parts,OUT/'geometry-source',('source/routed.odb','source/parent/routed.odb','native-nine-audit.json','unchanged-wire-native.json','continuity.json','signal-contacts.json','export.json','pin-compatibility-native.json','pin-compatibility.json'))
        assert geometry['status']=='COMPLETE_ACTUAL_PIN_COMPATIBILITY_AND_SIGNAL_GEOMETRY_REQUIRES_FRESH_RC'and geometry['source_unchanged']
        assert geometry['source_head']=='03585c2a79da83ae66ebde1d586f978c530e3b47'and geometry['source_run']==38978702458
        assert not geometry['accepted']and not geometry['final_timing_complete']
        assert geometry['candidate_odb_sha256']=='49a805c66e904b534dd846bcca58070feaeac77dfe1427f7937e89427b0085e8'
        for name,key in [('native-nine-audit.json','native_census'),('unchanged-wire-native.json','wire_census'),('continuity.json','continuity'),('signal-contacts.json','contacts'),('export.json','export'),('pin-compatibility.json','pin_compatibility')]:
            assert json.loads((OUT/'geometry-source'/name).read_text())==geometry[key]
        wire=geometry['wire_census'];native_proof=geometry['native_census']
        assert wire['status']=='DIAGNOSTIC_RECORDED_ACCEPTANCE_CHECKS_PENDING'
        assert geometry['original_geometry_equality_gate']=='FAILED_RETAINED'
        assert not wire['master_obstructions_equal']and not wire['power_pins_equal']
        assert wire['all114103net_wire_records_equal']and wire['routed_nets']==113796 and wire['wire_detachment_control']['rejected']
        compat=geometry['pin_compatibility']
        assert compat['status']=='COMPLETE_ACTUAL_PIN_ROUTE_COMPATIBILITY_SCREEN_NOT_SIGNOFF'
        assert not compat['accepted']and not compat['original_pin_and_obstruction_equality_gate_passed']
        assert compat['source_unchanged']and compat['candidate_sha256']==geometry['candidate_odb_sha256']
        assert not compat['candidate_power_errors']and not compat['parent_power_errors']and not compat['candidate_route_failures']
        assert compat['nets_checked']==113796 and compat['shapes_checked']==geometry['export']['shapes']
        assert compat['controls']['actual_geometry_faults_rejected']==['actual_local_VDD_grid_removed','actual_VDD_connected_to_wrong_rail','route_at_actual_power_pin','route_at_actual_obstruction']
        physical=json.loads((OUT/'geometry-source/pin-compatibility-native.json').read_text())
        assert sha(OUT/'geometry-source/pin-compatibility-native.json')==geometry['outputs']['pin-compatibility-native.json']
        assert physical['source_unchanged']and physical['candidate_sha256']==geometry['candidate_odb_sha256']
        # Validate the diagnostic's spatial acceleration window against native
        # shape bounds and spacing, so no relevant route could be filtered out.
        spacing=physical['minimum_spacing_dbu']['Metal1'];assert 0<spacing<=1000
        for inst in physical['instances'].values():
            assert inst['orientation_control_rejected']and inst['native_transform_verified_all_pins']
            for rows in [*inst['pins'].values(),inst['obstructions']]:
                for layer,x1,y1,x2,y2 in rows:
                    assert layer=='Metal1'and 2769080<=x1-spacing and x2+spacing<=2774920 and 1945480<=y1-spacing and y2+spacing<=1951700
        for method,digest in geometry['method_hashes'].items():assert sha(ROOT/'scripts'/method)==digest
        result['original_geometry_equality_gate']='FAILED_RETAINED'
        result['actual_pin_route_compatibility']=compat
        assert native_proof['changed_masters']==1 and native_proof['added']==0 and native_proof['negative_control']['rejected']and native_proof['master_control']['rejected']
        assert native_proof['source_parent_sha256']==parent['outputs']['routed.odb']
        assert geometry['continuity']['failed']==0 and geometry['contacts']['no_cross_net_contacts']
        assert geometry['continuity']['checked']==geometry['contacts']['net_count']==geometry['export']['exported_nets']==113796
        assert sha(OUT/'geometry-source/source/parent/routed.odb')==sha(OUT/'parent/routed.odb')
        shutil.copy2(OUT/'geometry-source/source/routed.odb',OUT/'routed.odb')
        assert sha(OUT/'routed.odb')==geometry['candidate_odb_sha256']==wire['candidate_odb_sha256']==native_proof['routed_odb_sha256']
        result.update(geometry_restoration=geometry_proof,geometry_summary_sha256=args.geometry_summary,geometry_run=args.geometry_run,candidate_odb_sha256=sha(OUT/'routed.odb'),native_geometry=geometry,no_routing_performed=True)
        save()
        rules=SOURCE/'source/IHP_rcx_patterns.rules';spef=OUT/'candidate.nominal.spef'
        tcl(f'read_db {{{OUT/"routed.odb"}}}\nset_thread_count 2\ndefine_process_corner -ext_model_index 0 nominal\nextract_parasitics -ext_model_file {{{rules}}} -lef_res\nwrite_spef {{{spef}}}\n','fresh-extraction')
        sys.path.insert(0,str(ROOT/'hw/soc/flow'));from audit_estimated_spef import audit
        result['spef_integrity']=audit(spef,allow_coupling=True);assert result['spef_integrity']['inconsistent_nets']==0
        actual=original.replace(str(SOURCE/'source/routed.odb'),str(OUT/'routed.odb')).replace(str(SOURCE/'actual-route.nominal.spef'),str(spef))
        result['routed_timing']=parse_phases(tcl(actual,'fresh-routed-sta'),'CORNER');save()
        helper=ROOT/'hw/soc/pnr/timing_hold_reproducibility.tcl';method=ROOT/'hw/soc/pnr/routed_endpoint_census.tcl';graph=ROOT/'hw/soc/pnr/native_graph_path_coverage.tcl'
        assert sha(helper)==reports.HELPER_SHA and sha(method)==reports.CENSUS_METHOD_SHA
        directory=OUT/'routed-census';directory.mkdir()
        tcl(actual+f'\nsource {{{helper}}}\nsource {{{graph}}}\nset nssoc_endpoint_out {{{directory}}}\nsource {{{method}}}\nnssoc_graph_finish {{{directory/"native-graph-coverage.json"}}}\n','routed-census')
        after,new_rows=reports.load_census(directory);assert before['native_pin_mapping']==after['native_pin_mapping']and len(new_rows)==135264
        result['graph_coverage']=verify(directory,after);result['endpoint_comparison']=reports.compare_rows(old_rows,new_rows)
        result['endpoint_count']=22544;result['endpoint_corner_delay_rows']=len(new_rows)
        text=tcl(f'read_db {{{OUT/"routed.odb"}}}\ncheck_placement -verbose\nset n [check_antennas -verbose -report_file {{{OUT/"antenna.rpt"}}}]\nputs "NSSOC_ANTENNA_RETURN $n"\n','placement-antenna')
        result['antenna_report_lines']=[l for l in text.splitlines()if 'violation'in l.lower()]
        assert all(sha(OUT/'parent'/n)==v['sha256']for n,v in proof['restore']['selected_files'].items())
        assert all(sha(Path(n))==v for n,v in old['protected_inputs'].items())
        assert all(sha(OUT/'geometry-source'/n)==v['sha256']for n,v in geometry_proof['restore']['selected_files'].items())
        assert sha(OUT/'routed.odb')==geometry['candidate_odb_sha256']
        result.update(status='COMPLETE_PIN_COMPATIBLE_ETHERNET_ROUTES_FRESH_RC_ALL_ENDPOINTS_NOT_SIGNOFF',source_unchanged=True,independent_geometry_required=False,independent_annotation_required=True)
    except BaseException as error:result.update(status='FAIL_OR_ERROR',error=repr(error));raise
    finally:
        result['outputs']={str(p.relative_to(OUT)):sha(p)for p in OUT.rglob('*')if p.is_file()and p.name!='result.json'};save()
if __name__=='__main__':main()
