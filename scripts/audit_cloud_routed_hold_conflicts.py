#!/usr/bin/env python3
# SPDX-FileCopyrightText: 2026 Hasan Melih Akbulut
# SPDX-License-Identifier: Apache-2.0
"""Expose actual slow/fast paths for all 91 simultaneously constrained hold targets."""
import hashlib,json,os,re,subprocess,tarfile
from pathlib import Path
from audit_cloud_route_annotation import BASE,SUMMARY_SHA,ARCHIVE_SHA
from route_cloud_newer_postcts import fetch,sha
from read_opensta_phase_slacks import parse_phases
ROOT=Path(__file__).resolve().parents[1];OUT=ROOT/'cloud-routed-hold-conflicts';SOURCE=ROOT/'cloud-routed-extraction'
CENSUS='https://github.com/Melihakbulut221/nssoc/releases/download/cloud-results-38819589884-1-routed-endpoints/routed-endpoints-38819589884-1'
CENSUS_SHA='54a23354fc53eb4811b574a1c1bbd70aa413d83463e5165f240b8925c10e00ff'
CENSUS_ARCHIVE_SHA='14883e2c8766210fddfaccb1d2a121a3e9a3bb308fd795029d5897a362bb636a'

def native_report_ns(value):
    # OpenSTA857316ff liberty/Units.cc:174-185 uses float32(value/scale),
    # zeroes abs(scaled)<1e-6, then printf("%.*f",digits,scaled). This is
    # report representation only; raw SI values and acceptance stay unchanged.
    import struct
    f32=lambda x:struct.unpack('!f',struct.pack('!f',x))[0]
    scaled=f32(f32(value)/f32(1e-9))
    if abs(scaled)<1e-6:scaled=0.0
    return float(format(scaled,'.9f'))

def rendering_controls():
    assert native_report_ns(2.9761593189903124e-10)==0.297615945
    assert native_report_ns(0.0)==native_report_ns(1e-16)==native_report_ns(-1e-16)==0.0
    assert native_report_ns(-2.9761593189903124e-10)==-0.297615945
    return dict(native_observed_positive=1,sign_symmetry=1,zero_threshold_cases=3,acceptance_tolerance_changed=False)

def main():
    assert os.environ.get('GITHUB_ACTIONS')=='true';OUT.mkdir(exist_ok=False)
    result=dict(status='RUNNING',accepted=False,source_head=os.environ['GITHUB_SHA'],source_run=38809759501,census_run=38819589884,final_timing_complete=False,scope='All91 actual-route negative hold endpoints, with min/max reports at each original cell corner. Identify shared slow/fast path causes before delay insertion;90endpoints already fail setup. No constraints/RC/layout changed; not timing acceptance.')
    def save():(OUT/'result.json').write_text(json.dumps(result,indent=2)+'\n')
    save()
    try:
        result['rendering_controls']=rendering_controls()
        fetch(CENSUS+'.summary.json',CENSUS_SHA,OUT/'census-summary.json');census=json.loads((OUT/'census-summary.json').read_text())
        assert census['status']=='COMPLETE_ACTUAL_ROUTED_ENDPOINT_CENSUS_NOT_TIMING_ACCEPTANCE'
        assert census['source_unchanged'] and census['original_routed_timing_reproduced'] and census['negative_hold_endpoints']==91
        packed=OUT/'census.tar.gz';fetch(CENSUS+'.tar.gz.part0000',CENSUS_ARCHIVE_SHA,packed);assert packed.stat().st_size==3562754
        with tarfile.open(packed) as archive:
            name='hold-target-topology.json';member=archive.getmember('cloud-routed-endpoints/'+name);assert member.isfile()
            data=archive.extractfile(member).read();assert hashlib.sha256(data).hexdigest()==census['outputs'][name]
            (OUT/name).write_bytes(data)
        packed.unlink();targets=json.loads(data);assert len(targets)==91 and len({r['endpoint'] for r in targets})==91
        fetch(BASE+'.summary.json',SUMMARY_SHA,OUT/'original-summary.json');old=json.loads((OUT/'original-summary.json').read_text())
        packed=OUT/'source.tar.gz';fetch(BASE+'.tar.gz.part0000',ARCHIVE_SHA,packed);assert packed.stat().st_size==225682086 and not SOURCE.exists()
        with tarfile.open(packed) as archive:
            for member in archive:
                p=Path(member.name);assert not p.is_absolute() and '..'not in p.parts and p.parts[0]=='cloud-routed-extraction'
                assert member.isfile() or member.isdir();archive.extract(member,ROOT,filter='data')
        packed.unlink();assert sha(SOURCE/'result.json')==SUMMARY_SHA
        for n,digest in old['outputs'].items():assert sha(SOURCE/n)==digest,n
        for n,digest in old['protected_inputs'].items():assert sha(Path(n))==digest,n
        original=(SOURCE/'actual-routed-sta.tcl').read_text()
        commands=[original,'puts NSSOC_CONFLICT_START','set pins_by_name {}','foreach pin [sta::endpoints] {dict set pins_by_name [get_property $pin full_name] $pin}']
        for index,row in enumerate(targets):
            name=row['endpoint'];assert not any(c in name for c in '{}\n\r')
            commands.append('set pin [dict get $pins_by_name {'+name+'}]')
            for c in ('slow','typical','fast'):
                for d in ('max','min'):
                    commands += [f'puts PHASE_target_{index}_{c}_{d}',f'report_checks -corner {c} -to $pin -path_delay {d} -group_path_count 1 -endpoint_path_count 1 -fields {{slew cap fanout}} -digits 9']
        path=OUT/'all-conflict-paths.tcl';path.write_text('\n'.join(commands)+'\n')
        with (OUT/'all-conflict-paths.log').open('w') as stream:
            child=subprocess.Popen([os.environ['CLOUD_APPIMAGE'],'openroad','-exit',str(path)],stdout=subprocess.PIPE,stderr=subprocess.STDOUT,text=True)
            for line in child.stdout:stream.write(line);stream.flush();print(line,end='',flush=True)
            code=child.wait()
        log=(OUT/'all-conflict-paths.log').read_text(errors='replace')
        assert code==0 and not re.search(r'(?m)^\[ERROR|^Error:',log);assert log.count('NSSOC_CONFLICT_START\n')==1
        baseline,detail=log.split('NSSOC_CONFLICT_START\n');phases=parse_phases(baseline,'CORNER')
        for p,row in old['nominal_rc_cell_corner_phases'].items():assert phases[p]['groups']==row['groups']
        phases=parse_phases(detail,'PHASE');assert len(phases)==6*len(targets)
        result.update(hold_targets=targets,all_corner_paths=phases);save()
        for i,row in enumerate(targets):
            for c in ('slow','typical','fast'):
                for d,k in (('min','hold_seconds'),('max','setup_seconds')):
                    value=row[k][c];assert value is not None
                    observed=phases[f'target_{i}_{c}_{d}']['worst_slack_ns']
                    assert native_report_ns(value)==observed,(i,c,d,value,native_report_ns(value),observed)
        result.update(status='COMPLETE_SOURCE_BOUND_CONFLICT_PATHS_NOT_TIMING_ACCEPTANCE',hold_targets=targets,all_corner_paths=phases,original_routed_timing_reproduced=True)
        assert all(sha(SOURCE/n)==v for n,v in old['outputs'].items())
        assert all(sha(Path(n))==v for n,v in old['protected_inputs'].items());result['source_unchanged']=True
    except BaseException as error:result.update(status='FAIL_OR_ERROR',error=repr(error));raise
    finally:
        result['outputs']={str(p.relative_to(OUT)):sha(p) for p in OUT.rglob('*') if p.is_file() and p.name!='result.json'};save()
if __name__=='__main__':main()
