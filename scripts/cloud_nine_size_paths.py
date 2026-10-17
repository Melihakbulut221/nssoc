#!/usr/bin/env python3
# SPDX-FileCopyrightText: 2026 Hasan Melih Akbulut
# SPDX-License-Identifier: Apache-2.0
"""Read-only native diagnosis of every remaining hold endpoint and worst setup paths."""
import json,os,re,subprocess,tarfile,shutil,sys
from pathlib import Path
import compare_cloud_routed_endpoints as reports
import audit_cloud_routed_endpoints as endpoints
from route_cloud_newer_postcts import fetch,sha
from read_opensta_phase_slacks import parse_phases
ROOT=Path(__file__).resolve().parents[1];OUT=ROOT/'cloud-nine-size-paths';SOURCE=ROOT/'cloud-routed-extraction'
SUMMARY='e3ff94103fe3d99e1dcdf889c1d01d741d6fd6d0a29092b20aea488dab89bbd4'
PARTS='fffba7e3f8b72286b19a9c9faec5d78eb155a8884ddccbb3c2bd5fd9240f13ae'
def native():
    endpoints.OUT=OUT;endpoints.SOURCE=OUT;endpoints.native_topology()
def main():
    assert os.environ.get('GITHUB_ACTIONS')=='true';OUT.mkdir(exist_ok=False);reports.OUT=OUT
    r=dict(status='RUNNING',source_head=os.environ['GITHUB_SHA'],source_run=38930352215,accepted=False,final_timing_complete=False,physical_candidate_modified=False,scope='All six remaining hold endpoints plus ten worst setup endpoints per cell corner from the real nine-size routed database and fresh nominal SPEF. Remeasure exact native transition slacks and capture complete clock/data paths and physical driver/fanout topology. No constraint waivers, design edits or signoff.')
    def save():(OUT/'result.json').write_text(json.dumps(r,indent=2)+'\n')
    def run(args,label):
        with (OUT/(label+'.log')).open('w')as f:code=subprocess.call(args,stdout=f,stderr=subprocess.STDOUT)
        log=(OUT/(label+'.log')).read_text(errors='replace');assert code==0 and not re.search(r'(?m)^\[ERROR|^Error:',log),(label,code,log[-6000:]);return log
    save()
    try:
        r['controls']=endpoints.controls();selected=('routed.odb','candidate.nominal.spef','fresh-routed-sta.tcl','routed-census/native-census.json','routed-census/endpoint-slacks.tsv','parent-census/native-census.json','parent-census/endpoint-slacks.tsv')
        candidate,proof=reports.restore_report('route234-sized-eco',38930352215,SUMMARY,PARTS,OUT/'source',selected);r['source']=proof
        assert candidate['status']=='COMPLETE_NINE_SIZED_CELLS_ROUTED_FRESH_NOMINAL_RC_ALL_ENDPOINTS_NOT_SIGNOFF'and candidate['source_unchanged']and candidate['native_drt_drvs']==0
        assert candidate['source_head']=='ad487eee3895b1312d86d8ce0b97d4064fc26d08'
        meta,rows=reports.load_census(OUT/'source/routed-census');before,old=reports.load_census(OUT/'source/parent-census')
        assert len(rows)==135264 and meta['engine_endpoint_count']==22544 and before['native_pin_mapping']==meta['native_pin_mapping']
        assert reports.compare_rows(old,rows)==candidate['endpoint_comparison']
        names=meta['endpoints'];corners=['slow','typical','fast'];chosen={};ranked={}
        for name in names:
            values=[rows[(c,'min',name)][2]for c in corners];finite=[v for v in values if v is not None]
            if finite and min(finite)<0:chosen[name]=['negative_hold']
        assert len(chosen)==6
        for corner in corners:
            ranked[corner]=sorted((n for n in names if rows[(corner,'max',n)][2]is not None),key=lambda n:(rows[(corner,'max',n)][2],n))[:10]
            for name in ranked[corner]:chosen.setdefault(name,[]).append('worst_setup_'+corner)
        targets=[]
        for name,reasons in sorted(chosen.items()):
            hold={c:rows[(c,'min',name)][2]for c in corners};setup={c:rows[(c,'max',name)][2]for c in corners};finite=[v for v in setup.values()if v is not None]
            targets.append(dict(endpoint=name,selection_reasons=reasons,hold_seconds=hold,setup_seconds=setup,worst_setup_seconds=min(finite)if finite else None,setup_constrained_all_corners=len(finite)==3,transition_slacks={c+'_'+d:rows[(c,d,name)]for c in corners for d in ['min','max']}))
        (OUT/'negative-hold-targets.json').write_text(json.dumps(targets,indent=2)+'\n');shutil.copyfile(OUT/'source/routed-census/native-census.json',OUT/'native-census.json')
        r.update(targets=targets,ranked_setup=ranked,all_endpoint_comparison_reproduced=True);save()
        fetch(reports.BASE+'.summary.json',reports.SUMMARY_SHA,OUT/'original-summary.json');original=json.loads((OUT/'original-summary.json').read_text());packed=OUT/'original.tar.gz';fetch(reports.BASE+'.tar.gz.part0000',reports.ARCHIVE_SHA,packed);assert packed.stat().st_size==225682086 and not SOURCE.exists()
        with tarfile.open(packed)as archive:
            for m in archive:
                p=Path(m.name);assert not p.is_absolute()and'..'not in p.parts and p.parts[0]==SOURCE.name and(m.isfile()or m.isdir());archive.extract(m,ROOT,filter='data')
        packed.unlink();assert sha(SOURCE/'result.json')==reports.SUMMARY_SHA
        assert all(sha(SOURCE/n)==v for n,v in original['outputs'].items())and all(sha(Path(n))==v for n,v in original['protected_inputs'].items())
        native_tcl=(SOURCE/'actual-routed-sta.tcl').read_text()
        sourcepath=ROOT/'cloud-route234-sized-eco'
        stored=native_tcl.replace(str(SOURCE/'source/routed.odb'),str(sourcepath/'routed.odb')).replace(str(SOURCE/'actual-route.nominal.spef'),str(sourcepath/'candidate.nominal.spef'))
        assert stored==(OUT/'source/fresh-routed-sta.tcl').read_text(),'Producer STA script differs from original constraints/libraries'
        script=stored.replace(str(sourcepath/'routed.odb'),str(OUT/'source/routed.odb')).replace(str(sourcepath/'candidate.nominal.spef'),str(OUT/'source/candidate.nominal.spef'))
        helper=ROOT/'hw/soc/pnr/timing_hold_reproducibility.tcl';assert sha(helper)==reports.HELPER_SHA
        commands=[script,f'source {{{helper}}}','set named_endpoints {}','foreach pin [sta::endpoints] {dict set named_endpoints [get_property $pin full_name] $pin}',f'set out [open {{{OUT/"selected-slacks.tsv"}}} w]','puts $out "index\tcorner\tdelay\tedge\tseconds"']
        for i,target in enumerate(targets):
            name=target['endpoint'];assert not any(ch in name for ch in '{}\n\r')
            commands += ['set pin [dict get $named_endpoints {'+name+'}]']
            for corner in corners:
                for delay in ['min','max']:
                    for edge in ['rise','fall']:
                        commands += [f'puts NSSOC_TARGET_{i}_{corner}_{delay}_{edge}',f'set paths [find_timing_paths -to $pin -corner {corner} -path_delay {delay}_{edge} -group_path_count 100 -endpoint_path_count 1]','set minimum UNCONSTRAINED','foreach path $paths {if {[$path pin] ne $pin || [$path is_unconstrained]} {error "Unexpected selected endpoint"}; set value [nssoc_hold_slack [$path slack]]; if {$value ne "UNCONSTRAINED" && ($minimum eq "UNCONSTRAINED" || $value<$minimum)} {set minimum $value}}',f'puts $out [join [list {i} {corner} {delay} {edge} $minimum] "\t"]',f'report_checks -to $pin -corner {corner} -path_delay {delay}_{edge} -group_path_count 2 -endpoint_path_count 1 -format full_clock_expanded -fields {{slew cap fanout}} -digits 9']
        commands+=['close $out','puts NSSOC_NINE_SIZE_SELECTED_PATHS_COMPLETE'];tcl=OUT/'selected-paths.tcl';tcl.write_text('\n'.join(commands)+'\n')
        log=run([os.environ['CLOUD_APPIMAGE'],'openroad','-exit',str(tcl)],'selected-paths');phases=parse_phases(log.split('NSSOC_TARGET_')[0],'CORNER')
        for k,v in candidate['routed_timing'].items():assert phases[k]['groups']==v['groups']
        observed={}
        for line in (OUT/'selected-slacks.tsv').read_text().splitlines()[1:]:
            i,c,d,e,v=line.split('\t');key=(int(i),c,d,e);assert key not in observed;value=endpoints.number(v);expected=rows[(c,d,targets[int(i)]['endpoint'])][['rise','fall'].index(e)];assert value==expected,(key,value,expected);observed[key]=value
        assert len(observed)==len(targets)*12 and log.count('NSSOC_NINE_SIZE_SELECTED_PATHS_COMPLETE')==1
        os.environ['NSSOC_NINE_SIZE_NATIVE']='1'
        run([os.environ['CLOUD_APPIMAGE'],'openroad','-exit','-python',str(Path(__file__).resolve())],'native-topology')
        del os.environ['NSSOC_NINE_SIZE_NATIVE']
        topology=json.loads((OUT/'hold-target-topology.json').read_text());assert len(topology)==len(targets);r['topology']=topology
        r['native_paths']=log[log.index('NSSOC_TARGET_'):];r['selected_transition_rows']=len(observed)
        assert all(sha(OUT/'source'/p)==candidate['outputs'][p]for p in selected)and all(sha(Path(n))==v for n,v in original['protected_inputs'].items())
        r.update(status='COMPLETE_EXACT_ROUTED_NINE_SIZE_CRITICAL_PATH_DIAGNOSIS_NOT_TIMING_ACCEPTANCE',source_unchanged=True)
    except BaseException as error:r.update(status='FAIL_OR_ERROR',error=repr(error));raise
    finally:
        r['outputs']={str(p.relative_to(OUT)):sha(p)for p in OUT.rglob('*')if p.is_file()and p!=OUT/'result.json'};save()
if __name__=='__main__':
    if os.environ.get('NSSOC_NINE_SIZE_NATIVE')=='1':native()
    else:main()
