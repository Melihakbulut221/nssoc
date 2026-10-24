#!/usr/bin/env python3
# SPDX-FileCopyrightText: 2026 Hasan Melih Akbulut
# SPDX-License-Identifier: Apache-2.0
"""Measure three-corner slack through short-only branches before any delay ECO."""
import json,os,re,subprocess,tarfile
from pathlib import Path
import cloud_tx_input_driver as physical
import compare_cloud_routed_endpoints as reports
from route_cloud_newer_postcts import fetch,sha
from read_opensta_phase_slacks import parse_phases
from candidate_hold_conflicts import native_report_ns
ROOT=physical.ROOT;OUT=ROOT/'cloud-nine-size-branch-margins';ORIGINAL=ROOT/'cloud-routed-extraction';CANDIDATE=ROOT/'cloud-route234-sized-eco'
def pins(text):
    # full_clock_expanded contains both launch and capture trees. Only data pins
    # after the launch CLK and before the first data-arrival marker are eligible.
    assert 'data arrival time' in text
    rows=re.findall(r'(?m)^[^\n]* [\^v] (\S+) \(([^()\n]+)\)\s*$',text.split('data arrival time')[0])
    clocks=[i for i,(name,master) in enumerate(rows) if name.endswith('/CLK')]
    if clocks:
        assert len(clocks)==1, 'Multiple register launch clocks'
        result=[name for name,master in rows[clocks[0]+1:]]
    else:
        # An external input launch has no register CLK row. Require explicit
        # native input-port provenance and exact first-row identity.
        launch=re.match(r'Startpoint: (\S+) \(input port clocked by [^\n]+\)',text)
        assert launch and rows and rows[0]==(launch.group(1),'in')
        result=[name for name,master in rows]
    assert len(result)>=3 and not any(n.endswith('/CLK')for n in result)
    return result
def main():
    assert os.environ.get('GITHUB_ACTIONS')=='true';OUT.mkdir(exist_ok=False)
    result=dict(status='RUNNING',accepted=False,source_head=os.environ['GITHUB_SHA'],final_timing_complete=False,scope='Read-only exact nine-size routed ODB and its fresh nominal RC with original SDC/all cell corners. Through-input setup margins identify short-path-only delay opportunities; no physical repair or full timing acceptance yet.')
    def save():(OUT/'result.json').write_text(json.dumps(result,indent=2)+'\n')
    def run(command,label):
        with (OUT/(label+'.log')).open('w')as f:p=subprocess.run(command,stdout=f,stderr=subprocess.STDOUT)
        text=(OUT/(label+'.log')).read_text();assert p.returncode==0 and not re.search(r'(?m)^\[ERROR|^Error:',text),(label,text[-6000:]);return text
    save()
    try:
        reports.OUT=OUT
        trace,traceproof=reports.restore_report('nine-size-paths',38953044374,'5b5776d2f96e7d371a9d282ca372597b133681adc241958467be1b4447665376','ab63a373e201312bf0bdfc87f06ce0f6c8dceb404b50dee7ad788822ab162afd',OUT/'trace',('selected-paths.log',))
        assert trace['status']=='COMPLETE_EXACT_ROUTED_NINE_SIZE_CRITICAL_PATH_DIAGNOSIS_NOT_TIMING_ACCEPTANCE' and trace['source_unchanged'] and trace['all_endpoint_comparison_reproduced']
        result['trace_source']=traceproof
        targets=trace['targets'];detail=trace['native_paths']
        parts=re.split(r'(?m)^NSSOC_TARGET_(\d+_(?:slow|typical|fast)_(?:min|max)_(?:rise|fall))\n',detail)
        blocks=dict(zip(parts[1::2],parts[2::2],strict=True));assert len(blocks)==len(targets)*12
        requests=[];unselected=[]
        for i,target in enumerate(targets):
            if 'negative_hold' not in target['selection_reasons']:continue
            long={n for c in ('slow','typical','fast') for e in ('rise','fall') for n in pins(blocks[f'{i}_{c}_max_{e}'])}
            selected=[]
            for edge in ('rise','fall'):
                short=pins(blocks[f'{i}_fast_min_{edge}'])
                edges=[(a,b)for a,b in zip(short,short[1:])if a not in long]
                if not edges:unselected.append(dict(index=i,edge=edge,reason='No observed short-only data edge'));continue
                selected.append(edges[-1])
            # This measured source has the same short branch for both transitions.
            # Fail explicitly if a different source needs multi-branch treatment.
            assert len(selected)==2 and selected[0]==selected[1]
            a,b=selected[0];requests.append(dict(index=i,endpoint=target['endpoint'],driver_pin=a,next_pin=b,observed_fast_hold_seconds=target['hold_seconds']['fast'],all_endpoint_setup_seconds=target['setup_seconds']))
        assert len(requests)==6 and not unselected
        result.update(requested_branches=len(requests),unselected=unselected);(OUT/'branch-requests.json').write_text(json.dumps(requests,indent=2)+'\n');save()
        reports.OUT=OUT
        candidate,proof=reports.restore_report('route234-sized-eco',38930352215,'e3ff94103fe3d99e1dcdf889c1d01d741d6fd6d0a29092b20aea488dab89bbd4','fffba7e3f8b72286b19a9c9faec5d78eb155a8884ddccbb3c2bd5fd9240f13ae',CANDIDATE,('routed.odb','candidate.nominal.spef','fresh-routed-sta.tcl'))
        assert candidate['native_drt_drvs']==0 and candidate['source_unchanged'] and candidate['source_head']=='ad487eee3895b1312d86d8ce0b97d4064fc26d08'
        assert candidate['status']=='COMPLETE_NINE_SIZED_CELLS_ROUTED_FRESH_NOMINAL_RC_ALL_ENDPOINTS_NOT_SIGNOFF'
        fetch(reports.BASE+'.summary.json',reports.SUMMARY_SHA,OUT/'original-summary.json');old=json.loads((OUT/'original-summary.json').read_text())
        packed=OUT/'original.tar.gz';fetch(reports.BASE+'.tar.gz.part0000',reports.ARCHIVE_SHA,packed);assert packed.stat().st_size==225682086 and not ORIGINAL.exists()
        with tarfile.open(packed)as archive:
            for m in archive:
                p=Path(m.name);assert not p.is_absolute()and'..'not in p.parts and p.parts[0]==ORIGINAL.name and(m.isfile()or m.isdir());archive.extract(m,ROOT,filter='data')
        packed.unlink();assert sha(ORIGINAL/'result.json')==reports.SUMMARY_SHA
        assert all(sha(ORIGINAL/n)==v for n,v in old['outputs'].items())and all(sha(Path(n))==v for n,v in old['protected_inputs'].items())
        expected=(ORIGINAL/'actual-routed-sta.tcl').read_text().replace(str(ORIGINAL/'source/routed.odb'),str(CANDIDATE/'routed.odb')).replace(str(ORIGINAL/'actual-route.nominal.spef'),str(CANDIDATE/'candidate.nominal.spef'))
        assert expected==(CANDIDATE/'fresh-routed-sta.tcl').read_text()
        run([os.environ['CLOUD_APPIMAGE'],'openroad','-exit','-python',str(ROOT/'scripts/resolve_nine_size_branches.py')],'resolve-physical-branches')
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
            # Also cover every reachable endpoint, not merely the selected hold target.
            for corner in ('slow','typical','fast'):
                phase=f'branch_{r["index"]}_{corner}_allmax';phases_expected.add(phase)
                commands += ['puts PHASE_'+phase,f'report_checks -corner {corner} -through $through -path_delay max -group_path_count 1 -endpoint_path_count 1 -fields {{slew cap fanout}} -digits 9']
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
            r['all_reachable_setup_ns']={c:phases[f'branch_{r["index"]}_{c}_allmax']['worst_slack_ns']for c in ('slow','typical','fast')}
            r['positive_setup_all_reachable_endpoints']=all(v is not None and v>0 for v in r['all_reachable_setup_ns'].values())
        assert all(sha(CANDIDATE/n)==v['sha256']for n,v in proof['restore']['selected_files'].items())
        assert all(sha(Path(n))==v for n,v in old['protected_inputs'].items())
        result.update(status='COMPLETE_SHORT_BRANCH_SETUP_HOLD_MARGINS_NOT_REPAIR_ACCEPTANCE',rows=rows,phases=phases,source_unchanged=True,original_timing_reproduced=True,positive_branch_count=sum(r.get('positive_setup_all_corners',False)for r in rows),positive_all_reachable_branch_count=sum(r.get('positive_setup_all_reachable_endpoints',False)for r in rows))
    except BaseException as e:result.update(status='FAIL_OR_ERROR',error=repr(e));raise
    finally:
        result['outputs']={str(p.relative_to(OUT)):sha(p)for p in OUT.rglob('*')if p.is_file()and p.name!='result.json'};save()
if __name__=='__main__':main()
