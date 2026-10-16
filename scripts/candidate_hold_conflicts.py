# SPDX-FileCopyrightText: 2026 Hasan Melih Akbulut
# SPDX-License-Identifier: Apache-2.0
"""Expose all candidate hold paths and their setup conflicts without waiving endpoints."""
import copy,json,os,re,subprocess
from audit_cloud_routed_hold_conflicts import native_report_ns,rendering_controls
from read_opensta_phase_slacks import parse_phases

def select_targets(census,rows):
    names=census['endpoints'];corners=('slow','typical','fast')
    assert len(set(names))==len(names)==census['engine_endpoint_count']
    assert set(rows)=={(c,d,n) for c in corners for d in ('min','max') for n in names}
    targets=[]
    for name in names:
        hold={c:rows[(c,'min',name)][2] for c in corners}
        if any(v is not None and v<0 for v in hold.values()):
            assert not any(c in name for c in '{}\n\r')
            targets.append(dict(endpoint=name,native_pin=census['native_pin_mapping'][name],hold_seconds=hold,setup_seconds={c:rows[(c,'max',name)][2] for c in corners}))
    assert len(targets)==census['negative_endpoint_count']['min']
    return targets

def controls():
    c=dict(endpoints=['a/D','b/D'],engine_endpoint_count=2,native_pin_mapping={'a/D':['a','D'],'b/D':['b','D']},negative_endpoint_count={'min':1})
    rows={(corner,delay,name):(1e-10,1e-10,1e-10) for corner in ('slow','typical','fast') for delay in ('min','max') for name in c['endpoints']}
    rows[('fast','min','a/D')]=(-1e-10,1e-10,-1e-10)
    rows[('slow','max','a/D')]=(-2e-9,-1e-9,-2e-9)
    rows[('typical','max','a/D')]=(None,None,None)
    selected=select_targets(c,rows);assert len(selected)==1 and selected[0]['endpoint']=='a/D'
    assert selected[0]['setup_seconds']['slow']==-2e-9 and selected[0]['setup_seconds']['typical'] is None
    for mutate in ('missing_row','wrong_native_count','unsafe_name'):
        badc=copy.deepcopy(c);badr=copy.deepcopy(rows)
        if mutate=='missing_row':badr.pop(('slow','max','a/D'))
        elif mutate=='wrong_native_count':badc['negative_endpoint_count']['min']=0
        else:
            badc['endpoints'][0]='bad{pin';badc['native_pin_mapping']['bad{pin']=badc['native_pin_mapping'].pop('a/D')
            badr={(corner,delay,'bad{pin' if name=='a/D' else name):value for (corner,delay,name),value in badr.items()}
        try:select_targets(badc,badr)
        except AssertionError:pass
        else:raise AssertionError('Invalid path target accepted: '+mutate)
    return dict(all_negative_targets_selected=True,setup_conflicts_and_unconstrained_preserved=True,negative_controls=3,native_rendering=rendering_controls())

def measure(out,script,census,rows,expected_phases):
    assert os.environ.get('GITHUB_ACTIONS')=='true'
    targets=select_targets(census,rows)
    result=dict(status='RUNNING',accepted=False,controls=controls(),targets=targets,unconstrained_requests=[],requested_paths=0,scope='All candidate negative hold endpoints with original-corner max/min paths. No clock, constraint, RC or layout change; missing constraints remain visible. This identifies delay/setup conflicts, not acceptance.')
    def save():(out/'hold-conflicts.json').write_text(json.dumps(result,indent=2)+'\n')
    save()
    try:
        commands=[script,'puts NSSOC_CANDIDATE_CONFLICT_START','set pins_by_name {}','foreach pin [sta::endpoints] {dict set pins_by_name [get_property $pin full_name] $pin}'];requests={}
        for index,row in enumerate(targets):
            commands.append('set pin [dict get $pins_by_name {'+row['endpoint']+'}]')
            for corner in ('slow','typical','fast'):
                for delay,key in (('min','hold_seconds'),('max','setup_seconds')):
                    phase=f'target_{index}_{corner}_{delay}';value=row[key][corner]
                    if value is None:
                        result['unconstrained_requests'].append(dict(endpoint=row['endpoint'],corner=corner,delay=delay));continue
                    requests[phase]=value
                    commands.extend([f'puts PHASE_{phase}',f'report_checks -corner {corner} -to $pin -path_delay {delay} -group_path_count 1 -endpoint_path_count 1 -fields {{slew cap fanout}} -digits 9'])
        result['requested_paths']=len(requests);save()
        path=out/'hold-conflict-paths.tcl';path.write_text('\n'.join(commands)+'\n')
        with (out/'hold-conflict-paths.log').open('w') as stream:
            child=subprocess.Popen([os.environ['CLOUD_APPIMAGE'],'openroad','-exit',str(path)],stdout=subprocess.PIPE,stderr=subprocess.STDOUT,text=True)
            for line in child.stdout:stream.write(line);stream.flush();print(line,end='',flush=True)
            code=child.wait()
        log=(out/'hold-conflict-paths.log').read_text(errors='replace')
        assert code==0 and not re.search(r'(?m)^\[ERROR|^Error:',log)
        assert log.count('NSSOC_CANDIDATE_CONFLICT_START\n')==1
        baseline,detail=log.split('NSSOC_CANDIDATE_CONFLICT_START\n')
        before=parse_phases(baseline,'CORNER')
        for phase,row in expected_phases.items():assert before[phase]['groups']==row['groups']
        phases=parse_phases(detail,'PHASE');assert set(phases)==set(requests),'Missing or extra candidate path'
        result['all_corner_paths']=phases;save()
        for phase,value in requests.items():assert phases[phase]['worst_slack_ns']==native_report_ns(value),(phase,value,phases[phase]['worst_slack_ns'])
        result.update(status='COMPLETE_ALL_CANDIDATE_HOLD_CONFLICT_PATHS_NOT_TIMING_ACCEPTANCE',original_candidate_timing_reproduced=True)
    except BaseException as error:result.update(status='FAIL_OR_ERROR',error=repr(error));raise
    finally:save()
    return result
