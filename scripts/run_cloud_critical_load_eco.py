#!/usr/bin/env python3
# SPDX-FileCopyrightText: 2026 Hasan Melih Akbulut
# SPDX-License-Identifier: Apache-2.0
"""Measured critical-load repair with real rerouting, fresh extraction and STA."""
import hashlib,json,os,re,subprocess,sys,tarfile
from pathlib import Path
from route_cloud_newer_postcts import fetch,sha,native_ndr_screen
from read_opensta_phase_slacks import parse_phases
from run_cloud_failed_guide_drt import guide_index
from critical_load_targets import COUNT,DIRECTORY,PROFILE,COMPLETE_STATUS,MAX_DISPLACEMENT_UM,SELECTION,validate_measurements
ROOT=Path(__file__).resolve().parents[1];OUT=ROOT/DIRECTORY;SOURCE=ROOT/'cloud-routed-extraction'
BASE='https://github.com/Melihakbulut221/nssoc/releases/download/cloud-results-38809759501-1-routed-extraction/'
STEM='routed-extraction-38809759501-1'
SUMMARY_SHA='aa721c7ccd04c30ed97af33dac632eb0cfdd99fd27232a46819299d12f62e583'
ARCHIVE_SHA='131bc44b4dc4d26f9ba1fa6a34b17742aa0ccf65e8c3075dca91dfe5dc5c1d4a'

def guide_blocks(text):
    guide_index(text);result={};lines=text.splitlines(keepends=True);i=0
    while i<len(lines):
        if not lines[i].strip():i+=1;continue
        start=i;name=lines[i].strip();i+=1;assert lines[i].strip()=='(';i+=1
        while lines[i].strip()!=')':i+=1
        i+=1;result[name]=''.join(lines[start:i])
    return result

def main():
    assert os.environ.get('GITHUB_ACTIONS')=='true';OUT.mkdir(exist_ok=False)
    result=dict(status='RUNNING',accepted=False,profile=PROFILE,buffer_count=COUNT,new_buffer_placement_search_um=list(MAX_DISPLACEMENT_UM),target_selection=SELECTION,source_run=38809759501,source_head=os.environ['GITHUB_SHA'],full_serial_phy_complete=False,final_timing_complete=False,
        scope='Explicit positive buffer16 insertions on independently measured high-load PCIe combinational outputs. Preserve original cells/geometry/SDC/libraries/NDR and all protected hold repairs. Native selected-net global guides merged with all unchanged original guides; full-chip detailed reroute and fresh nominalRC/all-cell-corner STA required. Original global132overflow,651antenna, new-candidate annotation qualification, RCcorners/SRAM/LVS remain open.')
    def save():(OUT/'result.json').write_text(json.dumps(result,indent=2)+'\n')
    def run(args,label,env=None,expect=True):
        with (OUT/(label+'.log')).open('w') as log:
            p=subprocess.Popen(args,stdout=subprocess.PIPE,stderr=subprocess.STDOUT,text=True,bufsize=1,env=env)
            for line in p.stdout:log.write(line);log.flush();print('['+label+'] '+line,end='',flush=True)
            code=p.wait()
        text=(OUT/(label+'.log')).read_text(errors='replace')
        if expect:assert code==0 and not re.search(r'(?m)^\[ERROR|^Error:',text),(label,code)
        return code,text
    def tcl(text,label):
        path=OUT/(label+'.tcl');path.write_text(text);return run([os.environ['CLOUD_APPIMAGE'],'openroad','-exit',str(path)],label)[1]
    def native(mode):run([os.environ['CLOUD_APPIMAGE'],'openroad','-exit','-python',str(ROOT/'scripts/prepare_cloud_critical_load_eco.py')],mode,dict(os.environ,NSSOC_CRITICAL_ECO_MODE=mode))
    save()
    try:
        fetch(BASE+STEM+'.summary.json',SUMMARY_SHA,OUT/'original-summary.json');old=json.loads((OUT/'original-summary.json').read_text())
        assert old['protected_inputs_unchanged'] and old['spef_integrity']['inconsistent_nets']==0
        assert old['nominal_rc_cell_corner_phases']['slow_max']['worst_slack_ns']==-11.940513
        packed=OUT/'source.tar.gz';fetch(BASE+STEM+'.tar.gz.part0000',ARCHIVE_SHA,packed);assert packed.stat().st_size==225682086
        assert not SOURCE.exists()
        with tarfile.open(packed) as archive:
            for member in archive:
                p=Path(member.name);assert not p.is_absolute() and '..'not in p.parts and p.parts[0]=='cloud-routed-extraction'
                assert member.isfile() or member.isdir();archive.extract(member,ROOT,filter='data')
        packed.unlink();assert sha(SOURCE/'result.json')==SUMMARY_SHA
        for n,digest in old['outputs'].items():assert sha(SOURCE/n)==digest,n
        for n,digest in old['protected_inputs'].items():assert sha(Path(n))==digest,n
        validate_measurements((SOURCE/'actual-routed-sta.log').read_text())
        if PROFILE in ('expanded_load_batch','refined_load_batch'):
            from expanded_load_targets import REVIEW_URL,REVIEW_SHA,verify_review
            fetch(REVIEW_URL,REVIEW_SHA,OUT/'driver-review-summary.json')
            result['driver_review_source']=verify_review((OUT/'driver-review-summary.json').read_bytes());save()

        if PROFILE=='refined_load_batch':
            import refined_load_targets as refined
            fetch(refined.REVIEW_URL,refined.REVIEW_SHA,OUT/'refined-driver-review-summary.json')
            result['refined_review_source']=refined.verify_review((OUT/'refined-driver-review-summary.json').read_bytes());save()
        original_script=(SOURCE/'actual-routed-sta.tcl').read_text();measured=parse_phases(tcl(original_script,'reproduce-routed-baseline'),'CORNER')
        for phase,row in old['nominal_rc_cell_corner_phases'].items():
            assert set(measured[phase]['groups'])==set(row['groups'])
            for group,v in row['groups'].items():assert abs(measured[phase]['groups'][group]['worst_slack_ns']-v['worst_slack_ns'])<=1e-6
        result['original_routed_timing_reproduced']=True;save()
        baseline=SOURCE/'source/routed.odb'
        tcl(f'read_db {{{baseline}}}\nwrite_verilog {{{OUT/"before.v"}}}\n','baseline-netlist')
        native('prepare')
        dpl_limits=' '.join(map(str,MAX_DISPLACEMENT_UM))
        tcl(f'read_db {{{OUT/"proposed.odb"}}}\nset_thread_count 2\ndetailed_placement -max_displacement {{{dpl_limits}}}\ncheck_placement -verbose\nwrite_db {{{OUT/"legalized.odb"}}}\n','legalize-only-new-buffers')
        native('audit');geometry=json.loads((OUT/'geometry-proof.json').read_text());result['geometry']=geometry
        tcl(f'read_db {{{OUT/"candidate.odb"}}}\nwrite_verilog {{{OUT/"after.v"}}}\n','candidate-netlist')
        libs=[Path(n) for n in old['protected_inputs'] if n.endswith('_typ_1p20V_25C.lib')];standard=next(p for p in libs if 'stdcell' in str(p))
        proof=[os.environ['CLOUD_APPIMAGE'],'python3',str(ROOT/'hw/soc/flow/check_eco_logic.py'),str(OUT/'before.v'),str(OUT/'after.v'),'--liberty',str(standard),'--output',str(OUT/'logic')]
        for lib in libs:
            if lib!=standard:proof+=['--macro-liberty',str(lib)]
        run(proof,'logic-proof');logic=json.loads((OUT/'logic/result.json').read_text());assert logic['status']=='PASS within scope';result['logic']=logic
        netlist=(OUT/'after.v').read_text();pattern=r'sg13g2_buf_16\s+nssoc_critical_load_buffer_0\s*\((.*?)\);';m=re.search(pattern,netlist,re.S);assert m
        bad=netlist[:m.start()]+'sg13g2_inv_1 nssoc_critical_load_buffer_0 ('+re.sub(r'\.X\s*\(','.Y(',m[1])+');'+netlist[m.end():]
        (OUT/'inverted.v').write_text(bad);negative=proof.copy();negative[negative.index(str(OUT/'after.v'))]=str(OUT/'inverted.v');negative[negative.index(str(OUT/'logic'))]=str(OUT/'logic-negative')
        rc,log=run(negative,'negative-inversion-proof',expect=False);assert rc!=0 and 'Non-buffer instance added or removed' in log;result['inversion_control']='REJECTED';save()
        guide_base='https://github.com/Melihakbulut221/nssoc/releases/download/cloud-results-38788529905-1-failed-guide-drt/failed-guide-drt-38788529905-1.tar.gz'
        packed=OUT/'guides-source.tar.gz';fetch(guide_base,'ce430c94dd6da745f2a15420eb5f8031842e9ddd78b6ad70aa0bb56634c0b964',packed)
        with tarfile.open(packed) as archive:raw=archive.extractfile('cloud-failed-guide-drt/inputs/failed-route.guide').read()
        assert hashlib.sha256(raw).hexdigest()=='fc6efcd026c6b2040fdb636376c2ab0a38f959d0ae4ee3acdbe381bcf3412e1b';packed.unlink();(OUT/'original.guide').write_bytes(raw)
        original=guide_blocks(raw.decode());assert len(original)==113556
        selected=[r[k] for r in geometry['changes'] for k in ('original_net','local_net')];assert len(set(selected))==2*COUNT
        commands=[f'read_db {{{OUT/"candidate.odb"}}}','set_thread_count 2','set_routing_layers -signal Metal2-TopMetal2 -clock Metal2-TopMetal2','set_global_routing_layer_adjustment Metal1-TopMetal2 0.2']
        for n in selected:
            assert not any(c in n for c in '{}\n')
            commands += [f'set n [[ord::get_db_block] findNet {{{n}}}]','if {$n == "NULL"} {error "Missing selected ECO net"}','grt::add_net_to_route $n']
        commands += [f'global_route -guide_file {{{OUT/"changed.guide"}}} -congestion_iterations 50 -verbose']
        log=tcl('\n'.join(commands)+'\n','selected-net-native-guides');assert native_ndr_screen(log)['preserved']
        changed=guide_blocks((OUT/'changed.guide').read_text());assert set(changed)==set(selected)
        merged=dict(original);merged.update(changed);assert len(merged)==113556+COUNT
        assert all(merged[n]==b for n,b in original.items() if n not in selected)
        (OUT/'candidate.guide').write_text(''.join(merged[n] for n in sorted(merged)))
        result['guide_provenance']=dict(original_guided_nets=len(original),selected_native_nets=selected,merged_guided_nets=len(merged),all_unmodified_guides_byte_identical=True,global_capacity_accepted=False);save()
        log=tcl(f'read_db {{{OUT/"candidate.odb"}}}\nset_thread_count 2\nread_guides {{{OUT/"candidate.guide"}}}\ncheck_placement -verbose\ndetailed_route -output_drc {{{OUT/"drc.rpt"}}} -output_guide_coverage {{{OUT/"guide-coverage.csv"}}} -drc_report_iter_step 1 -verbose 1\nputs "NSSOC_ECO_DRVS [detailed_route_num_drvs]"\nwrite_db {{{OUT/"routed.odb"}}}\nwrite_def {{{OUT/"routed.def"}}}\n','full-detailed-route')
        matches=re.findall(r'^NSSOC_ECO_DRVS (\d+)\s*$',log,re.M);assert len(matches)==1;result['native_drt_drvs']=int(matches[0]);save()
        assert result['native_drt_drvs']==0,'Failed physical route retained; no STA adoption'
        if PROFILE in ('expanded_load_batch','refined_load_batch'):
            native('audit_routed');result['post_route_geometry']=json.loads((OUT/'post-route-geometry.json').read_text());save()
        rules=SOURCE/'source/IHP_rcx_patterns.rules';spef=OUT/'candidate.nominal.spef'
        tcl(f'read_db {{{OUT/"routed.odb"}}}\nset_thread_count 2\ndefine_process_corner -ext_model_index 0 nominal\nextract_parasitics -ext_model_file {{{rules}}} -lef_res\nwrite_spef {{{spef}}}\n','fresh-nominal-extraction')
        sys.path.insert(0,str(ROOT/'hw/soc/flow'));from audit_estimated_spef import audit
        result['spef_integrity']=audit(spef,allow_coupling=True);assert result['spef_integrity']['inconsistent_nets']==0;save()
        assert original_script.count(str(baseline))==1 and original_script.count(str(SOURCE/'actual-route.nominal.spef'))==3
        script=original_script.replace(str(baseline),str(OUT/'routed.odb')).replace(str(SOURCE/'actual-route.nominal.spef'),str(spef))
        candidate=parse_phases(tcl(script,'fresh-routed-sta'),'CORNER');result['routed_timing']=candidate
        result['group_deltas']={p:{g:dict(before_ns=v['worst_slack_ns'],after_ns=candidate[p]['groups'][g]['worst_slack_ns'],delta_ns=candidate[p]['groups'][g]['worst_slack_ns']-v['worst_slack_ns']) for g,v in row['groups'].items()} for p,row in old['nominal_rc_cell_corner_phases'].items()}
        result['status']=COMPLETE_STATUS
        assert all(sha(Path(n))==v for n,v in old['protected_inputs'].items());result['protected_source_unchanged']=True
        if PROFILE in ('expanded_load_batch','refined_load_batch'):
            if PROFILE=='refined_load_batch':
                from refined_load_targets import validate_candidate
            else:
                from expanded_load_targets import validate_candidate
            validate_candidate(result,OUT)
    except BaseException as error:result.update(status='FAIL_OR_ERROR',error=repr(error));raise
    finally:
        result['outputs']={str(p.relative_to(OUT)):sha(p) for p in OUT.rglob('*') if p.is_file() and p.name!='result.json'};save()
if __name__=='__main__':main()
