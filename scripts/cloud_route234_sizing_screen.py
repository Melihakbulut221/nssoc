#!/usr/bin/env python3
# SPDX-FileCopyrightText: 2026 Hasan Melih Akbulut
# SPDX-License-Identifier: Apache-2.0
"""Measure a concrete14-driver sizing hypothesis on actual234 source; never sign off frozen RC."""
import json,os,re,subprocess,tarfile
from pathlib import Path
import compare_cloud_routed_endpoints as reports
from branch_hold_targets import validate_child,CHILD_FILES
from route_cloud_newer_postcts import fetch,sha
from read_opensta_phase_slacks import parse_phases
from native_graph_path_coverage import verify
ROOT=Path(__file__).resolve().parents[1];OUT=ROOT/'cloud-route234-sizing-screen';SOURCE=ROOT/'cloud-routed-extraction';CHILD=ROOT/'cloud-branch-hold-eco'
SUMMARY='765b113220ba12b3267ee50cd1ff02bfac7eb89a336c41ba77632c7ccd401e6e'
PARTS='ed0fa830af18e5703c36e509ff3230ffe4522b106aaf764482709d5c9f2dc178'
def main():
    assert os.environ.get('GITHUB_ACTIONS')=='true';OUT.mkdir(exist_ok=False);reports.OUT=OUT
    result=dict(status='RUNNING',accepted=False,source_head=os.environ['GITHUB_SHA'],physical_candidate=False,final_timing_complete=False,scope='Concrete14-driver doubling hypothesis on actual234ODB using unchanged original constraints/libraries and frozen234SPEF. Full22544endpoint comparison and restricted logic proof; route/pin geometry is invalid after resizing. This ranks a possible future physical ECO only. No legalization/freshRC/DRC/LVS/PHY acceptance.')
    def save():(OUT/'result.json').write_text(json.dumps(result,indent=2)+'\n')
    def run(command,label,expect=True):
        with (OUT/(label+'.log')).open('w')as log:
            p=subprocess.run(command,stdout=log,stderr=subprocess.STDOUT)
        text=(OUT/(label+'.log')).read_text(errors='replace')
        if expect:assert p.returncode==0 and not re.search(r'(?m)^\[ERROR|^Error:',text),(label,p.returncode,text[-5000:])
        print(label,p.returncode,text[-1200:],flush=True)
        return p.returncode,text
    def tcl(text,label):
        f=OUT/(label+'.tcl');f.write_text(text)
        return run([os.environ['CLOUD_APPIMAGE'],'openroad','-exit',str(f)],label)[1]
    save()
    try:
        candidate,proof=reports.restore_report('branch-hold-eco',38896397749,SUMMARY,PARTS,CHILD,('routed.odb','candidate.nominal.spef','fresh-routed-sta.tcl','geometry-proof.json')+CHILD_FILES)
        validate_child(candidate,CHILD)
        assert candidate['native_drt_drvs']==0 and candidate['protected_source_unchanged'] and candidate['logic']['status']=='PASS within scope'
        result['physical_source']=proof
        census,census_proof=reports.restore_report('eco-endpoint-compare',38914920637,'7b4cebace5eb8e52071fb3a19eafcf5a10ea4b63cd0d032d34d99af66050940b','131c0f60e5a5b801a25585e3783487f8225eddf68736b23da8665fd800d009ca',OUT/'published-census',('native-census.json','endpoint-slacks.tsv'))
        assert census['source_unchanged'] and census['candidate']['run']==38896397749 and census['candidate']['summary_sha256']==SUMMARY
        baseline_meta,baseline_rows=reports.load_census(OUT/'published-census')
        assert len(baseline_rows)==135264 and baseline_meta['engine_endpoint_count']==22544
        result['published_census']=census_proof
        url='https://github.com/Melihakbulut221/nssoc/releases/download/cloud-results-38911721184-1-parent146-driver-review/parent146-driver-review-38911721184-1.summary.json'
        fetch(url,'9207f1a03fa9f22564a6041a5e4c9d12c4e6fbcf4313ab2b496610a0d001c938',OUT/'driver-source.json')
        trace=json.loads((OUT/'driver-source.json').read_text());assert trace['source_unchanged']
        requests=[dict(index=i,pin=r['pin'],master=r['master'])for i,r in enumerate(trace['ranked_outputs'])]
        assert len(requests)==15 and requests[14]['pin']=='place27767/X'
        (OUT/'driver-requests.json').write_text(json.dumps(requests,indent=2)+'\n')
        fetch(reports.BASE+'.summary.json',reports.SUMMARY_SHA,OUT/'original-summary.json');old=json.loads((OUT/'original-summary.json').read_text())
        packed=OUT/'original.tar.gz';fetch(reports.BASE+'.tar.gz.part0000',reports.ARCHIVE_SHA,packed);assert packed.stat().st_size==225682086 and not SOURCE.exists()
        with tarfile.open(packed)as archive:
            for m in archive:
                p=Path(m.name);assert not p.is_absolute()and'..'not in p.parts and p.parts[0]==SOURCE.name and(m.isfile()or m.isdir());archive.extract(m,ROOT,filter='data')
        packed.unlink();assert sha(SOURCE/'result.json')==reports.SUMMARY_SHA
        assert all(sha(SOURCE/n)==v for n,v in old['outputs'].items())and all(sha(Path(n))==v for n,v in old['protected_inputs'].items())
        expected=(SOURCE/'actual-routed-sta.tcl').read_text().replace(str(SOURCE/'source/routed.odb'),str(CHILD/'routed.odb')).replace(str(SOURCE/'actual-route.nominal.spef'),str(CHILD/'candidate.nominal.spef'))
        assert expected==(CHILD/'fresh-routed-sta.tcl').read_text()
        helper=ROOT/'hw/soc/pnr/timing_hold_reproducibility.tcl';method=ROOT/'hw/soc/pnr/routed_endpoint_census.tcl';graph=ROOT/'hw/soc/pnr/native_graph_path_coverage.tcl'
        assert sha(helper)==reports.HELPER_SHA and sha(method)==reports.CENSUS_METHOD_SHA
        def census_run(script,label):
            directory=OUT/label;directory.mkdir()
            suffix=f'\nsource {{{helper}}}\nsource {{{graph}}}\nset nssoc_endpoint_out {{{directory}}}\nsource {{{method}}}\nnssoc_graph_finish {{{directory/"native-graph-coverage.json"}}}\n'
            log=tcl(script+suffix,label)
            meta,rows=reports.load_census(directory);assert meta['native_pin_mapping']==baseline_meta['native_pin_mapping']and len(rows)==135264
            coverage=verify(directory,meta)
            return meta,rows,coverage,log
        meta,before,coverage,log=census_run(expected,'baseline')
        assert before==baseline_rows,'Actual234 does not reproduce every published endpoint'
        phases=parse_phases(log,'CORNER')
        for k,v in candidate['routed_timing'].items():assert phases[k]['groups']==v['groups']
        result.update(baseline_all_endpoint_rows_reproduced=True,baseline_graph_coverage=coverage);save()
        commands=[expected,'puts NSSOC_DRIVER_BEGIN'];phase_names=set()
        for r in requests:
            name=r['pin'];assert not any(c in name for c in '{}[]*?\n\r')
            commands+=['set through [get_pins -quiet {'+name+'}]','if {[llength $through] != 1} {error "Driver pin is not unique"}']
            for c in ('slow','typical','fast'):
                for d in ('min','max'):
                    phase=f'driver_{r["index"]}_{c}_{d}';phase_names.add(phase)
                    commands+=['puts PHASE_'+phase,f'report_checks -corner {c} -through $through -path_delay {d} -group_path_count 1 -endpoint_path_count 1 -fields {{slew cap fanout}} -digits 9']
        margin_log=tcl('\n'.join(commands)+'\n','source-driver-margins');phases=parse_phases(margin_log.split('NSSOC_DRIVER_BEGIN\n')[1],'PHASE')
        assert set(phases)==phase_names
        for r in requests:
            r['source234_hold_ns']={c:phases[f'driver_{r["index"]}_{c}_min']['worst_slack_ns']for c in ('slow','typical','fast')}
            r['source234_setup_ns']={c:phases[f'driver_{r["index"]}_{c}_max']['worst_slack_ns']for c in ('slow','typical','fast')}
            assert all(v is not None for key in ('source234_hold_ns','source234_setup_ns')for v in r[key].values())
        result['remeasured_source_drivers']=requests;save()
        assert all(v>0 for r in requests[:14]for v in r['source234_hold_ns'].values()),'Selected driver already has negative hold on actual234; revise hypothesis before resizing'
        run([os.environ['CLOUD_APPIMAGE'],'openroad','-exit','-python',str(ROOT/'scripts/prepare_route234_sizing_screen.py')],'prepare-sizing')
        preparation=json.loads((OUT/'native-sizing.json').read_text());assert 0<len(preparation['changes'])<=14 and len(preparation['changes'])+len(preparation['unavailable'])==14 and preparation['source_unchanged']
        result['preparation']=preparation;save()
        tcl(f'read_db {{{CHILD/"routed.odb"}}}\nwrite_verilog {{{OUT/"before.v"}}}\n','before-netlist')
        tcl(f'read_db {{{OUT/"unlegalized-frozen-wire.odb"}}}\nwrite_verilog {{{OUT/"after.v"}}}\n','after-netlist')
        libs=[Path(n)for n in old['protected_inputs']if n.endswith('_typ_1p20V_25C.lib')];standard=next(p for p in libs if 'stdcell'in str(p))
        proof_cmd=[os.environ['CLOUD_APPIMAGE'],'python3',str(ROOT/'hw/soc/flow/check_eco_logic.py'),str(OUT/'before.v'),str(OUT/'after.v'),'--liberty',str(standard),'--output',str(OUT/'logic')]
        for lib in libs:
            if lib!=standard:proof_cmd+=['--macro-liberty',str(lib)]
        run(proof_cmd,'logic-proof');logic=json.loads((OUT/'logic/result.json').read_text());assert logic['status']=='PASS within scope'
        # A real transistor-library-compatible buffer inversion must be rejected.
        netlist=(OUT/'after.v').read_text();pattern=r'sg13g2_buf_2\s+place29858\s*\((.*?)\);';m=re.search(pattern,netlist,re.S);assert m
        bad=netlist[:m.start()]+'sg13g2_inv_2 place29858 ('+re.sub(r'\.X\s*\(','.Y(',m[1])+');'+netlist[m.end():]
        (OUT/'inverted.v').write_text(bad);negative=proof_cmd.copy();negative[negative.index(str(OUT/'after.v'))]=str(OUT/'inverted.v');negative[negative.index(str(OUT/'logic'))]=str(OUT/'logic-negative')
        rc,text=run(negative,'negative-inversion',False);assert rc!=0 and 'Non-buffer instance added or removed'in text
        result.update(logic=logic,inversion_control='REJECTED');save()
        assert expected.count(str(CHILD/'routed.odb'))==1
        estimate=expected.replace(str(CHILD/'routed.odb'),str(OUT/'unlegalized-frozen-wire.odb'))
        meta,after,coverage,log=census_run(estimate,'sized-estimate')
        comparison=reports.compare_rows(before,after)
        result.update(frozen_spef_comparison=comparison,sized_graph_coverage=coverage,endpoint_count=22544,endpoint_corner_delay_rows=len(after),any_loss_of_constraints=any(v[e]['became_unconstrained']for v in comparison.values()for e in ('rise','fall','worst')),physical_validation_required=True)
        assert not result['any_loss_of_constraints']
        changed=[dict(corner=c,delay=d,endpoint=n,before=before[(c,d,n)],after=after[(c,d,n)])for c,d,n in sorted(before)if before[(c,d,n)]!=after[(c,d,n)]]
        (OUT/'changed-endpoints.json').write_text(json.dumps(changed,indent=2)+'\n')
        assert all(sha(CHILD/n)==v['sha256']for n,v in proof['restore']['selected_files'].items())
        assert all(sha(Path(n))==v for n,v in old['protected_inputs'].items())
        assert sha(helper)==reports.HELPER_SHA and sha(method)==reports.CENSUS_METHOD_SHA
        result.update(status='COMPLETE_AVAILABLE_DRIVER_FROZEN_RC_SIZING_SCREEN_NOT_PHYSICAL_ACCEPTANCE',source_unchanged=True)
    except BaseException as error:result.update(status='FAIL_OR_ERROR',error=repr(error));raise
    finally:
        result['outputs']={str(p.relative_to(OUT)):sha(p)for p in OUT.rglob('*')if p.is_file()and p.name!='result.json'};save()
if __name__=='__main__':main()
