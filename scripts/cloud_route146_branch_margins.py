#!/usr/bin/env python3
# SPDX-FileCopyrightText: 2026 Hasan Melih Akbulut
# SPDX-License-Identifier: Apache-2.0
"""Measure three-corner slack through short-only branches before any delay ECO."""
import json,os,re,subprocess,tarfile
from pathlib import Path
import cloud_tx_input_driver as physical
import compare_cloud_routed_endpoints as reports
from cloud_route146_conflict_detail import SOURCE as TRACE_SOURCE
from route_cloud_newer_postcts import fetch,sha
from read_opensta_phase_slacks import parse_phases
from candidate_hold_conflicts import native_report_ns
ROOT=physical.ROOT;OUT=ROOT/'cloud-route146-branch-margins';ORIGINAL=ROOT/'cloud-routed-extraction';CANDIDATE=ROOT/'cloud-refined-hold-eco'
def pins(text):
    rows=re.findall(r'(?m)^[^\n]* [\^v] (\S+) \(([^()\n]+)\)\s*$',text)
    assert len(rows)>=3
    return [name for name,master in rows if not name.endswith('/CLK')]
def main():
    assert os.environ.get('GITHUB_ACTIONS')=='true';OUT.mkdir(exist_ok=False)
    result=dict(status='RUNNING',accepted=False,source_head=os.environ['GITHUB_SHA'],final_timing_complete=False,scope='Read-only exact146ODB and original nominalRC/SDC/all cell corners. Through-input setup margins identify short-path-only delay opportunities; no physical repair or full timing acceptance yet.')
    def save():(OUT/'result.json').write_text(json.dumps(result,indent=2)+'\n')
    def run(command,label):
        with (OUT/(label+'.log')).open('w')as f:p=subprocess.run(command,stdout=f,stderr=subprocess.STDOUT)
        text=(OUT/(label+'.log')).read_text();assert p.returncode==0 and not re.search(r'(?m)^\[ERROR|^Error:',text),(label,text[-6000:]);return text
    save()
    try:
        physical.OUT=OUT;tracedir,trace=physical.restore(TRACE_SOURCE);targets=trace['hold_conflict_paths']['targets'];assert len(targets)==90
        log=(tracedir/'hold-conflict-paths.log').read_text();detail=log.split('NSSOC_CANDIDATE_CONFLICT_START\n')[1]
        parts=re.split(r'(?m)^PHASE_(target_\d+_(?:slow|typical|fast)_(?:min|max))\n',detail);blocks=dict(zip(parts[1::2],parts[2::2],strict=True));assert len(blocks)==540
        requests=[];unselected=[]
        for i,target in enumerate(targets):
            short=pins(blocks[f'target_{i}_fast_min']);long=set(n for corner in ('slow','typical','fast')for n in pins(blocks[f'target_{i}_{corner}_max']))
            edges=[(a,b)for a,b in zip(short,short[1:])if a not in long]
            if not edges:unselected.append(dict(index=i,reason='No observed short-only edge'));continue
            a,b=edges[-1];requests.append(dict(index=i,endpoint=target['endpoint'],driver_pin=a,next_pin=b,observed_fast_hold_seconds=target['hold_seconds']['fast'],all_endpoint_setup_seconds=target['setup_seconds']))
        result.update(requested_branches=len(requests),unselected=unselected);(OUT/'branch-requests.json').write_text(json.dumps(requests,indent=2)+'\n');save()
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
        run([os.environ['CLOUD_APPIMAGE'],'openroad','-exit','-python',str(ROOT/'scripts/resolve_route146_branches.py')],'resolve-physical-branches')
        rows=json.loads((OUT/'branches.json').read_text());assert len(rows)==len(requests)
        commands=[expected,'puts NSSOC_BRANCH_BEGIN','set endpoints_by_name {}','foreach p [sta::endpoints] {dict set endpoints_by_name [get_property $p full_name] $p}'];phases_expected=set()
        for r in rows:
            if 'branch_pin'not in r:continue
            name=r['branch_pin'];assert not any(c in name for c in '{}[]*?\n\r')
            endpoint=r['endpoint'];assert not any(c in endpoint for c in '{}\n\r')
            commands += ['set through [get_pins -quiet {'+name+'}]','if {[llength $through] != 1} {error "Branch pin is not unique"}','set endpoint [dict get $endpoints_by_name {'+endpoint+'}]']
            for corner in ('slow','typical','fast'):
                for delay in ('min','max'):
                    phase=f'branch_{r["index"]}_{corner}_{delay}';phases_expected.add(phase)
                    commands += ['puts PHASE_'+phase,f'report_checks -corner {corner} -through $through -to $endpoint -path_delay {delay} -group_path_count 1 -endpoint_path_count 1 -fields {{slew cap fanout}} -digits 9']
        tcl=OUT/'branch-margins.tcl';tcl.write_text('\n'.join(commands)+'\n');native=run([os.environ['CLOUD_APPIMAGE'],'openroad','-exit',str(tcl)],'branch-margins')
        before,after=native.split('NSSOC_BRANCH_BEGIN\n');baseline=parse_phases(before,'CORNER')
        for phase,row in candidate['routed_timing'].items():assert baseline[phase]['groups']==row['groups']
        phases=parse_phases(after,'PHASE');assert set(phases)==phases_expected
        for r in rows:
            if 'branch_pin'not in r:continue
            r['through_setup_ns']={c:phases[f'branch_{r["index"]}_{c}_max']['worst_slack_ns']for c in ('slow','typical','fast')}
            r['through_hold_ns']={c:phases[f'branch_{r["index"]}_{c}_min']['worst_slack_ns']for c in ('slow','typical','fast')}
            assert r['through_hold_ns']['fast']==native_report_ns(r['observed_fast_hold_seconds'])
            r['positive_setup_all_corners']=all(v is not None and v>0 for v in r['through_setup_ns'].values())
        assert all(sha(CANDIDATE/n)==v['sha256']for n,v in proof['restore']['selected_files'].items())
        assert all(sha(Path(n))==v for n,v in old['protected_inputs'].items())
        result.update(status='COMPLETE_SHORT_BRANCH_SETUP_HOLD_MARGINS_NOT_REPAIR_ACCEPTANCE',rows=rows,phases=phases,source_unchanged=True,original_timing_reproduced=True,positive_branch_count=sum(r.get('positive_setup_all_corners',False)for r in rows))
    except BaseException as e:result.update(status='FAIL_OR_ERROR',error=repr(e));raise
    finally:
        result['outputs']={str(p.relative_to(OUT)):sha(p)for p in OUT.rglob('*')if p.is_file()and p.name!='result.json'};save()
if __name__=='__main__':main()
