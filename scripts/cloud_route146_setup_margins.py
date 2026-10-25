#!/usr/bin/env python3
# SPDX-FileCopyrightText: 2026 Hasan Melih Akbulut
# SPDX-License-Identifier: Apache-2.0
"""Measure all reachable setup and hold paths through actual overloaded drivers; no ECO."""
import json,os,re,subprocess,tarfile
from pathlib import Path
import cloud_tx_input_driver as physical
import compare_cloud_routed_endpoints as reports
from route_cloud_newer_postcts import fetch,sha
from read_opensta_phase_slacks import parse_phases
ROOT=physical.ROOT;OUT=ROOT/'cloud-route146-setup-margins';ORIGINAL=ROOT/'cloud-routed-extraction';CANDIDATE=ROOT/'cloud-refined-hold-eco'
def pins(text):
    rows=re.findall(r'(?m)^[^\n]* [\^v] (\S+) \(([^()\n]+)\)\s*$',text)
    assert len(rows)>=3
    return [name for name,master in rows if not name.endswith('/CLK')]
def main():
    assert os.environ.get('GITHUB_ACTIONS')=='true';OUT.mkdir(exist_ok=False)
    result=dict(status='RUNNING',accepted=False,source_head=os.environ['GITHUB_SHA'],final_timing_complete=False,scope='Read-only exact146ODB and original nominalRC/SDC/all cell corners. Through-output min/max paths across every constrained reachable endpoint screen setup acceleration risks; no resizing, repair or timing acceptance. Revalidate on234child when available.')
    def save():(OUT/'result.json').write_text(json.dumps(result,indent=2)+'\n')
    def run(command,label):
        with (OUT/(label+'.log')).open('w')as f:p=subprocess.run(command,stdout=f,stderr=subprocess.STDOUT)
        text=(OUT/(label+'.log')).read_text();assert p.returncode==0 and not re.search(r'(?m)^\[ERROR|^Error:',text),(label,text[-6000:]);return text
    save()
    try:
        url='https://github.com/Melihakbulut221/nssoc/releases/download/cloud-results-38911721184-1-parent146-driver-review/parent146-driver-review-38911721184-1.summary.json'
        fetch(url,'9207f1a03fa9f22564a6041a5e4c9d12c4e6fbcf4313ab2b496610a0d001c938',OUT/'driver-source.json')
        trace=json.loads((OUT/'driver-source.json').read_text())
        assert trace['status']=='COMPLETE_SOURCE_BOUND_SETUP_HOLD_DRIVER_DIAGNOSIS_NOT_REPAIR' and trace['source_unchanged']
        assert trace['reported_paths']==dict(hold_corner_paths=540,global_corner_paths=1050,negative_slow_setup_paths=239)
        requests=[dict(index=i,pin=r['pin'],master=r['master'],reported_fast_hold_targets=r['reported_fast_min_target_indices'],observations=r['observations']) for i,r in enumerate(trace['ranked_outputs'])]
        assert len(requests)==15 and len({r['pin']for r in requests})==15
        (OUT/'driver-requests.json').write_text(json.dumps(requests,indent=2)+'\n')
        result['driver_source']=dict(run=38911721184,sha256=sha(OUT/'driver-source.json'),targets=15);save()
        reports.OUT=OUT
        candidate,proof=reports.restore_report('refined-hold-eco',38880596259,'aa87fe441e4b3680c84bb0d46f50ccb3fe744a031dbc81a4d96de0efc2b59a2c','612de7f6659774b2b4d3211ae7e10a04df7d808d732f1404ce19a981b90b1586',CANDIDATE,('routed.odb','candidate.nominal.spef','fresh-routed-sta.tcl'))
        assert candidate['native_drt_drvs']==0 and candidate['logic']['status']=='PASS within scope'
        fetch(reports.BASE+'.summary.json',reports.SUMMARY_SHA,OUT/'original-summary.json');old=json.loads((OUT/'original-summary.json').read_text())
        packed=OUT/'original.tar.gz';fetch(reports.BASE+'.tar.gz.part0000',reports.ARCHIVE_SHA,packed);assert packed.stat().st_size==225682086 and not ORIGINAL.exists()
        with tarfile.open(packed)as archive:
            for m in archive:
                p=Path(m.name);assert not p.is_absolute()and'..'not in p.parts and p.parts[0]==ORIGINAL.name and(m.isfile()or m.isdir());archive.extract(m,ROOT,filter='data')
        packed.unlink();assert sha(ORIGINAL/'result.json')==reports.SUMMARY_SHA
        assert all(sha(ORIGINAL/n)==v for n,v in old['outputs'].items())and all(sha(Path(n))==v for n,v in old['protected_inputs'].items())
        expected=(ORIGINAL/'actual-routed-sta.tcl').read_text().replace(str(ORIGINAL/'source/routed.odb'),str(CANDIDATE/'routed.odb')).replace(str(ORIGINAL/'actual-route.nominal.spef'),str(CANDIDATE/'candidate.nominal.spef'))
        assert expected==(CANDIDATE/'fresh-routed-sta.tcl').read_text()
        run([os.environ['CLOUD_APPIMAGE'],'openroad','-exit','-python',str(ROOT/'scripts/resolve_route146_setup_drivers.py')],'resolve-physical-drivers')
        rows=json.loads((OUT/'drivers.json').read_text());assert len(rows)==len(requests)
        commands=[expected,'puts NSSOC_DRIVER_BEGIN'];phases_expected=set()
        for r in rows:
            name=r['pin'];assert not any(c in name for c in '{}[]*?\n\r')
            commands += ['set through [get_pins -quiet {'+name+'}]','if {[llength $through] != 1} {error "Driver pin is not unique"}']
            for corner in ('slow','typical','fast'):
                for delay in ('min','max'):
                    phase=f'driver_{r["index"]}_{corner}_{delay}';phases_expected.add(phase)
                    commands += ['puts PHASE_'+phase,f'report_checks -corner {corner} -through $through -path_delay {delay} -group_path_count 1 -endpoint_path_count 1 -fields {{slew cap fanout}} -digits 9']
        tcl=OUT/'driver-margins.tcl';tcl.write_text('\n'.join(commands)+'\n');native=run([os.environ['CLOUD_APPIMAGE'],'openroad','-exit',str(tcl)],'driver-margins')
        before,after=native.split('NSSOC_DRIVER_BEGIN\n');baseline=parse_phases(before,'CORNER')
        for phase,row in candidate['routed_timing'].items():assert baseline[phase]['groups']==row['groups']
        phases=parse_phases(after,'PHASE');assert set(phases)==phases_expected and len(phases)==90
        for r in rows:
            r['all_reachable_setup_ns']={c:phases[f'driver_{r["index"]}_{c}_max']['worst_slack_ns']for c in ('slow','typical','fast')}
            r['all_reachable_hold_ns']={c:phases[f'driver_{r["index"]}_{c}_min']['worst_slack_ns']for c in ('slow','typical','fast')}
            assert all(v is not None for k in ('all_reachable_setup_ns','all_reachable_hold_ns') for v in r[k].values()),'Unconstrained driver query'
            r['negative_hold_already_present']=any(v<0 for v in r['all_reachable_hold_ns'].values())
            r['safe_acceleration_proven']=False
            r['minimum_observed_hold_margin_ns']=min(r['all_reachable_hold_ns'].values())
        assert all(sha(CANDIDATE/n)==v['sha256']for n,v in proof['restore']['selected_files'].items())
        assert all(sha(Path(n))==v for n,v in old['protected_inputs'].items())
        result.update(status='COMPLETE_ALL_REACHABLE_DRIVER_MIN_MAX_MARGINS_NOT_REPAIR',rows=rows,phases=phases,source_unchanged=True,original_timing_reproduced=True,drivers_with_existing_negative_hold=sum(r['negative_hold_already_present']for r in rows),all_constrained_reachable_groups_queried=True)
    except BaseException as e:result.update(status='FAIL_OR_ERROR',error=repr(e));raise
    finally:
        result['outputs']={str(p.relative_to(OUT)):sha(p)for p in OUT.rglob('*')if p.is_file()and p.name!='result.json'};save()
if __name__=='__main__':main()
