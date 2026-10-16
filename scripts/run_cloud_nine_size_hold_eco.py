#!/usr/bin/env python3
# SPDX-FileCopyrightText: 2026 Hasan Melih Akbulut
# SPDX-License-Identifier: Apache-2.0
"""Nine actual cell sizes on234source, legal placement, native reroute, fresh RC and all endpoints."""
import json,os,re,subprocess,sys,tarfile
from pathlib import Path
import compare_cloud_routed_endpoints as reports
from route_cloud_newer_postcts import fetch,sha,native_ndr_screen
from run_cloud_branch_hold_eco import guide_blocks
from read_opensta_phase_slacks import parse_phases
from native_graph_path_coverage import verify
ROOT=Path(__file__).resolve().parents[1];OUT=ROOT/'cloud-nine-size-hold-eco';SOURCE=ROOT/'cloud-routed-extraction'
SUMMARY='e3ff94103fe3d99e1dcdf889c1d01d741d6fd6d0a29092b20aea488dab89bbd4';PARTS='fffba7e3f8b72286b19a9c9faec5d78eb155a8884ddccbb3c2bd5fd9240f13ae'
def main():
    assert os.environ.get('GITHUB_ACTIONS')=='true';OUT.mkdir(exist_ok=False);reports.OUT=OUT
    result=dict(status='RUNNING',accepted=False,source_head=os.environ['GITHUB_SHA'],source_run=38930352215,sized_cells=0,added_cells=6,final_timing_complete=False,full_serial_phy_complete=False,scope='Six measured short-only gate input branches on the actual nine-size routed parent. All-reachable setup margin exceeds2.7ns before insertion. Six sd3 cells are a sizing hypothesis; actual placement/routing/fresh RC/full endpoint comparison determine the result. All existing cells and all other pins, PG/NDR/top boundaries and SDC stay fixed. No PHY, antenna, qualifiedRC, SRAM or foundry acceptance.')
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
    def native(mode):run([os.environ['CLOUD_APPIMAGE'],'openroad','-exit','-python',str(ROOT/'scripts/prepare_nine_size_hold_eco.py')],mode,dict(os.environ,NSSOC_CRITICAL_ECO_MODE=mode))
    save()
    try:
        parent,proof=reports.restore_report('route234-sized-eco',38930352215,SUMMARY,PARTS,OUT/'parent',('routed.odb','candidate.nominal.spef','candidate.guide','fresh-routed-sta.tcl','geometry-proof.json','routed-census/native-census.json','routed-census/endpoint-slacks.tsv'))
        assert parent['status']=='COMPLETE_NINE_SIZED_CELLS_ROUTED_FRESH_NOMINAL_RC_ALL_ENDPOINTS_NOT_SIGNOFF' and parent['source_unchanged'] and parent['native_drt_drvs']==0
        assert parent['logic']['status']=='PASS within scope' and parent['inversion_control']=='REJECTED'
        result['parent']=proof
        root='https://github.com/Melihakbulut221/nssoc/releases/download/'
        fetch(root+'cloud-results-38956304190-1-nine-size-earlier-branches/nine-size-earlier-branches-38956304190-1.summary.json','60ac0af2e4701d9b0c614602e9323f36bce4be709f7a0987ca028641c3817cf0',OUT/'branch-margins.json')
        margins=json.loads((OUT/'branch-margins.json').read_text());assert margins['source_unchanged'] and margins['original_timing_reproduced'] and margins['positive_all_reachable_branch_count']==6
        assert len(margins['rows'])==6 and min(v for r in margins['rows']for v in r['all_reachable_setup_ns'].values())>2.7
        result['branch_measurements']=margins['rows'];result['delay_sizing_hypothesis']='Six sg13g2_dlygate4sd3_1 on measured inputs; not delay-fit or closure proof.'
        fetch(root+'cloud-results-38948570826-1-nine-size-geometry/nine-size-geometry-38948570826-1.summary.json','9e09733c49258a90364fdcc2bf1538ad7c62c7cb05f8ae004eed95a017d9c1fa',OUT/'parent-geometry-summary.json')
        geometry=json.loads((OUT/'parent-geometry-summary.json').read_text())
        assert geometry['source_unchanged']and geometry['restoration']['run']==38930352215 and geometry['routed_odb_sha256']==parent['outputs']['routed.odb']
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
        stored=original.replace(str(SOURCE/'source/routed.odb'),str(ROOT/'cloud-route234-sized-eco/routed.odb')).replace(str(SOURCE/'actual-route.nominal.spef'),str(ROOT/'cloud-route234-sized-eco/candidate.nominal.spef'))
        assert stored==(OUT/'parent/fresh-routed-sta.tcl').read_text()
        expected=stored.replace(str(ROOT/'cloud-route234-sized-eco'),str(OUT/'parent'))
        phases=parse_phases(tcl(expected,'reproduce-parent'),'CORNER')
        for k,v in parent['routed_timing'].items():assert phases[k]['groups']==v['groups']
        result['parent_timing_reproduced']=True;save()
        native('prepare')
        tcl(f'read_db {{{OUT/"proposed.odb"}}}\nset_thread_count 2\ndetailed_placement -max_displacement {{1000 200}}\ncheck_placement -verbose\nwrite_db {{{OUT/"legalized.odb"}}}\n','legalize-six-new-only')
        native('audit');result['geometry']=json.loads((OUT/'geometry-proof.json').read_text());save()
        tcl(f'read_db {{{OUT/"parent/routed.odb"}}}\nwrite_verilog {{{OUT/"before.v"}}}\n','before-netlist')
        tcl(f'read_db {{{OUT/"candidate.odb"}}}\nwrite_verilog {{{OUT/"after.v"}}}\n','after-netlist')
        libs=[Path(n)for n in old['protected_inputs']if n.endswith('_typ_1p20V_25C.lib')];standard=next(p for p in libs if 'stdcell'in str(p))
        proof_cmd=[os.environ['CLOUD_APPIMAGE'],'python3',str(ROOT/'hw/soc/flow/check_eco_logic.py'),str(OUT/'before.v'),str(OUT/'after.v'),'--liberty',str(standard),'--output',str(OUT/'logic')]
        for lib in libs:
            if lib!=standard:proof_cmd+=['--macro-liberty',str(lib)]
        run(proof_cmd,'logic-proof');logic=json.loads((OUT/'logic/result.json').read_text());assert logic['status']=='PASS within scope';result['logic']=logic
        netlist=(OUT/'after.v').read_text();m=re.search(r'sg13g2_dlygate4sd3_1\s+nssoc_nine_hold_delay_0\s*\((.*?)\);',netlist,re.S);assert m
        bad=netlist[:m.start()]+'sg13g2_inv_1 nssoc_nine_hold_delay_0 ('+re.sub(r'\.X\s*\(','.Y(',m[1])+');'+netlist[m.end():]
        (OUT/'inverted.v').write_text(bad);negative=proof_cmd.copy();negative[negative.index(str(OUT/'after.v'))]=str(OUT/'inverted.v');negative[negative.index(str(OUT/'logic'))]=str(OUT/'logic-negative')
        rc,text=run(negative,'negative-inversion',expect=False);assert rc!=0 and 'Non-buffer instance added or removed'in text
        result['inversion_control']='REJECTED';save()
        guides=guide_blocks((OUT/'parent/candidate.guide').read_text());assert len(guides)==113790
        selected=sorted({row[k]for row in result['geometry']['stage_changes']for k in ('original_net','local_net')});commands=[f'read_db {{{OUT/"candidate.odb"}}}','set_thread_count 2','set_routing_layers -signal Metal2-TopMetal2 -clock Metal2-TopMetal2','set_global_routing_layer_adjustment Metal1-TopMetal2 0.2']
        for n in selected:
            assert not any(c in n for c in '{}\n')
            commands += [f'set n [[ord::get_db_block] findNet {{{n}}}]','if {$n == "NULL"} {error "Missing resized-cell net"}','grt::add_net_to_route $n']
        commands += [f'global_route -guide_file {{{OUT/"changed.guide"}}} -congestion_iterations 50 -verbose']
        text=tcl('\n'.join(commands)+'\n','selected-guides');assert native_ndr_screen(text)['preserved']
        changed=guide_blocks((OUT/'changed.guide').read_text());assert set(changed)==set(selected)
        merged=dict(guides);merged.update(changed);assert len(merged)==113796 and all(merged[n]==v for n,v in guides.items()if n not in selected)
        (OUT/'candidate.guide').write_text(''.join(merged[n]for n in sorted(merged)))
        result['guide_provenance']=dict(selected_nets=selected,all_other_guides_byte_identical=True,global_capacity_accepted=False);save()
        text=tcl(f'read_db {{{OUT/"candidate.odb"}}}\nset_thread_count 2\nread_guides {{{OUT/"candidate.guide"}}}\ncheck_placement -verbose\ndetailed_route -output_drc {{{OUT/"drc.rpt"}}} -output_guide_coverage {{{OUT/"guide-coverage.csv"}}} -drc_report_iter_step 1 -verbose 1\nputs "NSSOC_SIZED_DRVS [detailed_route_num_drvs]"\nwrite_db {{{OUT/"routed.odb"}}}\nwrite_def {{{OUT/"routed.def"}}}\n','full-detailed-route')
        values=re.findall(r'^NSSOC_SIZED_DRVS (\d+)\s*$',text,re.M);assert len(values)==1;result['native_drt_drvs']=int(values[0]);save();assert result['native_drt_drvs']==0
        native('audit-routed');result['post_route_geometry']=json.loads((OUT/'post-route-geometry.json').read_text());save()
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
        result.update(status='COMPLETE_SIX_SHORT_BRANCH_DELAYS_ROUTED_FRESH_RC_ALL_ENDPOINTS_NOT_SIGNOFF',source_unchanged=True,independent_geometry_required=True,independent_annotation_required=True)
    except BaseException as error:result.update(status='FAIL_OR_ERROR',error=repr(error));raise
    finally:
        result['outputs']={str(p.relative_to(OUT)):sha(p)for p in OUT.rglob('*')if p.is_file()and p.name!='result.json'};save()
if __name__=='__main__':main()
