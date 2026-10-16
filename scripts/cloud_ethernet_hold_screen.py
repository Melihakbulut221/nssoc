#!/usr/bin/env python3
# SPDX-FileCopyrightText: 2026 Hasan Melih Akbulut
# SPDX-License-Identifier: Apache-2.0
"""Price smallest existing delay-cell alternatives on the exact routed Ethernet hold branch."""
import json,os,re,subprocess,tarfile
from pathlib import Path
import compare_cloud_routed_endpoints as reports
from route_cloud_newer_postcts import fetch,sha
from read_opensta_phase_slacks import parse_phases
from native_graph_path_coverage import verify
ROOT=Path(__file__).resolve().parents[1];OUT=ROOT/'cloud-ethernet-hold-screen';SOURCE=ROOT/'cloud-routed-extraction'
SUMMARY='8fa70ddcf57970bcb4b726f68ecad6ebeb0c5389e9027f1dba1773906645b67b'
PARTS='d41a2ecf54bb782b439d8c9e46f005ff964d682602167910672d81fb6a09e290'
TARGET='u_eth.u_mac.rx_fifo.fifo_inst.u_sram.g_bank[6].u_mem/A_MEN'
def main():
    assert os.environ.get('GITHUB_ACTIONS')=='true';OUT.mkdir(exist_ok=False);reports.OUT=OUT
    result=dict(status='RUNNING',source_head=os.environ['GITHUB_SHA'],accepted=False,physical_candidate=False,final_timing_complete=False,physical_validation_required=True,
        scope='Exact six-hold routed parent, remaining Ethernet SRAM A_MEN hold violation. Actual existing sd1 delay is replaced by each available sd2/sd3 at same anchor. All22544 endpoints/135264 corner-delay rows and restricted logic proof. Frozen wireRC estimates only; changed pin geometry invalidates physical route acceptance.')
    def save():(OUT/'result.json').write_text(json.dumps(result,indent=2)+'\n')
    def run(command,label,expect=True):
        with (OUT/(label+'.log')).open('w')as log:p=subprocess.run(command,stdout=log,stderr=subprocess.STDOUT)
        text=(OUT/(label+'.log')).read_text(errors='replace')
        print(label,p.returncode,text[-1600:],flush=True)
        if expect:assert p.returncode==0 and not re.search(r'(?m)^\[ERROR|^Error:',text),(label,p.returncode,text[-6000:])
        return p.returncode,text
    def tcl(text,label):
        f=OUT/(label+'.tcl');f.write_text(text);return run([os.environ['CLOUD_APPIMAGE'],'openroad','-exit',str(f)],label)[1]
    save()
    try:
        selected=('routed.odb','candidate.nominal.spef','fresh-routed-sta.tcl','routed-census/native-census.json','routed-census/endpoint-slacks.tsv')
        candidate,proof=reports.restore_report('nine-size-hold-eco',38957249404,SUMMARY,PARTS,OUT/'source',selected)
        assert candidate['status']=='COMPLETE_SIX_SHORT_BRANCH_DELAYS_ROUTED_FRESH_RC_ALL_ENDPOINTS_NOT_SIGNOFF'and candidate['source_unchanged']and candidate['native_drt_drvs']==0
        assert candidate['source_head']=='2a3f6a2cac51640809c2e40aba8d685927229520'
        assert candidate['logic']['status']=='PASS within scope'and candidate['inversion_control']=='REJECTED'
        result['source']=proof;baseline_meta,baseline_rows=reports.load_census(OUT/'source/routed-census')
        assert len(baseline_rows)==135264 and baseline_meta['engine_endpoint_count']==22544
        assert baseline_rows[('fast','min',TARGET)][2]==-7.90811860440499e-13
        fetch(reports.BASE+'.summary.json',reports.SUMMARY_SHA,OUT/'original-summary.json');old=json.loads((OUT/'original-summary.json').read_text())
        packed=OUT/'original.tar.gz';fetch(reports.BASE+'.tar.gz.part0000',reports.ARCHIVE_SHA,packed);assert packed.stat().st_size==225682086 and not SOURCE.exists()
        with tarfile.open(packed)as archive:
            for m in archive:
                p=Path(m.name);assert not p.is_absolute()and'..'not in p.parts and p.parts[0]==SOURCE.name and(m.isfile()or m.isdir());archive.extract(m,ROOT,filter='data')
        packed.unlink();assert sha(SOURCE/'result.json')==reports.SUMMARY_SHA
        assert all(sha(SOURCE/n)==v for n,v in old['outputs'].items())and all(sha(Path(n))==v for n,v in old['protected_inputs'].items())
        native=(SOURCE/'actual-routed-sta.tcl').read_text();parent=ROOT/'cloud-nine-size-hold-eco'
        stored=native.replace(str(SOURCE/'source/routed.odb'),str(parent/'routed.odb')).replace(str(SOURCE/'actual-route.nominal.spef'),str(parent/'candidate.nominal.spef'))
        assert stored==(OUT/'source/fresh-routed-sta.tcl').read_text()
        expected=stored.replace(str(parent/'routed.odb'),str(OUT/'source/routed.odb')).replace(str(parent/'candidate.nominal.spef'),str(OUT/'source/candidate.nominal.spef'))
        helper=ROOT/'hw/soc/pnr/timing_hold_reproducibility.tcl';method=ROOT/'hw/soc/pnr/routed_endpoint_census.tcl';graph=ROOT/'hw/soc/pnr/native_graph_path_coverage.tcl'
        assert sha(helper)==reports.HELPER_SHA and sha(method)==reports.CENSUS_METHOD_SHA
        def census_run(script,label):
            directory=OUT/label;directory.mkdir()
            suffix=f'\nsource {{{helper}}}\nsource {{{graph}}}\nset nssoc_endpoint_out {{{directory}}}\nsource {{{method}}}\nnssoc_graph_finish {{{directory/"native-graph-coverage.json"}}}\n'
            log=tcl(script+suffix,label);meta,rows=reports.load_census(directory)
            assert meta['native_pin_mapping']==baseline_meta['native_pin_mapping']and len(rows)==135264
            return rows,verify(directory,meta),log
        before,coverage,log=census_run(expected,'baseline');assert before==baseline_rows
        phases=parse_phases(log,'CORNER')
        for k,v in candidate['routed_timing'].items():assert phases[k]['groups']==v['groups']
        result.update(baseline_all_endpoint_rows_reproduced=True,baseline_graph_coverage=coverage);save()
        run([os.environ['CLOUD_APPIMAGE'],'openroad','-exit','-python',str(ROOT/'scripts/prepare_ethernet_hold_screen.py')],'prepare')
        preparation=json.loads((OUT/'native-sizing.json').read_text());assert preparation['source_unchanged']and preparation['status']=='COMPLETE_EXACT_SINGLE_SINK_DELAY_MASTER_SUBSTITUTIONS_NOT_PHYSICAL_ECO'
        result['preparation']=preparation;result['variants']=[];save()
        tcl(f'read_db {{{OUT/"source/routed.odb"}}}\nwrite_verilog {{{OUT/"before.v"}}}\n','before-netlist')
        libs=[Path(n)for n in old['protected_inputs']if n.endswith('_typ_1p20V_25C.lib')];standard=next(p for p in libs if 'stdcell'in str(p))
        for variant in preparation['variants']:
            if not variant['available']:continue
            label=variant['replacement'];v=dict(replacement=label,physical_candidate=False);result['variants'].append(v)
            odb=OUT/variant['odb'];assert sha(odb)==variant['odb_sha256']
            after_v=OUT/(label+'.v');logic_dir=OUT/('logic-'+label)
            tcl(f'read_db {{{odb}}}\nwrite_verilog {{{after_v}}}\n','netlist-'+label)
            cmd=[os.environ['CLOUD_APPIMAGE'],'python3',str(ROOT/'hw/soc/flow/check_eco_logic.py'),str(OUT/'before.v'),str(after_v),'--liberty',str(standard),'--output',str(logic_dir)]
            for lib in libs:
                if lib!=standard:cmd+=['--macro-liberty',str(lib)]
            run(cmd,'logic-'+label);v['logic']=json.loads((logic_dir/'result.json').read_text());assert v['logic']['status']=='PASS within scope'
            text=after_v.read_text();pattern=re.escape(label)+r'\s+nssoc_refined_hold_delay_2\s*\((.*?)\);';m=re.search(pattern,text,re.S);assert m
            bad=text[:m.start()]+'sg13g2_inv_1 nssoc_refined_hold_delay_2 ('+re.sub(r'\.X\s*\(','.Y(',m[1])+');'+text[m.end():]
            bad_path=OUT/(label+'-inverted.v');bad_path.write_text(bad);negative=cmd.copy()
            negative[negative.index(str(after_v))]=str(bad_path);negative[negative.index(str(logic_dir))]=str(OUT/('negative-'+label))
            rc,log=run(negative,'negative-'+label,False);assert rc!=0 and 'Non-buffer instance added or removed'in log;v['inversion_control']='REJECTED';save()
            assert expected.count(str(OUT/'source/routed.odb'))==1
            estimate=expected.replace(str(OUT/'source/routed.odb'),str(odb))
            after,coverage,log=census_run(estimate,'estimate-'+label);comparison=reports.compare_rows(before,after)
            assert not any(v[e]['became_unconstrained']for v in comparison.values()for e in ('rise','fall','worst'))
            v.update(frozen_spef_comparison=comparison,graph_coverage=coverage,endpoint_count=22544,endpoint_corner_delay_rows=len(after),
                target={c+'_'+d:after[(c,d,TARGET)]for c in ('slow','typical','fast')for d in ('min','max')},
                viable_frozen_rc_screen=all(comparison[c+'_min']['worst']['negative_after']==0 and comparison[c+'_max']['worst']['new_negative']==0 for c in ('slow','typical','fast')))
            (OUT/(label+'-changed-endpoints.json')).write_text(json.dumps([dict(corner=c,delay=d,endpoint=n,before=before[(c,d,n)],after=after[(c,d,n)])for c,d,n in sorted(before)if before[(c,d,n)]!=after[(c,d,n)]],indent=2)+'\n')
            assert sha(odb)==variant['odb_sha256'];save()
        assert len(result['variants'])==sum(v['available']for v in preparation['variants'])
        assert all(sha(OUT/'source'/n)==candidate['outputs'][n]for n in selected)and all(sha(Path(n))==v for n,v in old['protected_inputs'].items())
        result.update(status='COMPLETE_ETHERNET_SINGLE_HOLD_DELAY_SCREEN_ALL_ENDPOINTS_NOT_ROUTED_ACCEPTANCE',source_unchanged=True)
    except BaseException as error:result.update(status='FAIL_OR_ERROR',error=repr(error));raise
    finally:
        result['outputs']={str(p.relative_to(OUT)):sha(p)for p in OUT.rglob('*')if p.is_file()and p!=OUT/'result.json'};save()
if __name__=='__main__':main()
