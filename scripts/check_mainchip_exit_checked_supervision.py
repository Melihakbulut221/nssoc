#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0
"""Hosted source/Python-process controls; no engine, archive, routing or CAD."""
import argparse
import ast
import contextlib
import copy
import hashlib
import json
import math
import os
import re
import subprocess
import sys
import tempfile
import time
import types
from pathlib import Path
from unittest import mock
import mainchip_exit_checked_supervision as candidate

STATUS='PASS_EXIT_CHECKED_SUPERVISION_SOURCE_CONTROLS'
PRIOR_REVIEW='docs/evidence/mainchip-exit-checked-supervision-source-review-20261029.json'
PRIOR_REVIEW_SHA='525fe820aaf9fde270f2960b23ff960768dd14b51c554a59ae367fb3f4e9b6d8'
PID=18001
START=67784


def require(value,reason):
    if not value:raise AssertionError(reason)


def function_text(raw,name):
    text=raw.decode()
    node=next(n for n in ast.parse(text).body if isinstance(n,ast.FunctionDef) and n.name==name)
    return ast.get_source_segment(text,node)


def refused(action,expected):
    try:action()
    except Exception as error:
        require(expected in str(error),(expected,type(error).__name__,str(error)))
        return type(error).__name__
    raise AssertionError('Expected refusal: '+expected)


def new_module(trace):
    module=candidate.supervisor()
    module.TRACE=Path(trace)
    module.OUT=Path(trace)
    module.CONSOLE_BROKEN=False
    return module


def derivation_controls():
    derived,proof=candidate.derive_sources()
    originals={key:(candidate.ROOT/path).read_bytes() for key,path in (
        ('supervisor',candidate.FROZEN_PATH),('sampler',candidate.SAMPLER_PATH))}
    preserved={}
    for key,changed in (('supervisor',{'supervised'}),('sampler',{'snapshot'})):
        old=ast.parse(originals[key]);new=ast.parse(derived[key])
        old_named={n.name:ast.dump(n,include_attributes=False) for n in old.body
                   if isinstance(n,(ast.FunctionDef,ast.ClassDef))}
        new_named={n.name:ast.dump(n,include_attributes=False) for n in new.body
                   if isinstance(n,(ast.FunctionDef,ast.ClassDef))}
        require(old_named.keys()==new_named.keys(),'derived function inventory')
        actual={name for name in old_named if old_named[name]!=new_named[name]}
        require(actual==changed,('only declared derived functions',actual))
        preserved[key]=len(old_named)-len(changed)
        replacements=(candidate.SUPERVISED_REPLACEMENTS if key=='supervisor'
                      else candidate.SNAPSHOT_REPLACEMENTS)
        reverse=derived[key].decode()
        for old_text,new_text in reversed(replacements):
            require(reverse.count(new_text)==1,'unique reverse seam')
            reverse=reverse.replace(new_text,old_text,1)
        require(reverse.encode()==originals[key],'exact reverse bytes')
    first=candidate.supervisor();second=candidate.supervisor()
    stateful=('supervised','heartbeat','stop_process','event','sample','wrap','interrupted','controls')
    for module in (first,second):
        require(all(getattr(module,name).__globals__ is module.__dict__ for name in stateful),
                'one coherent supervisor namespace')
        require(module._memory_counter.ATTEMPTS==3 and
                module._memory_counter.INTERVAL==.02 and
                module._memory_counter.RESAMPLE_WINDOW==.1,'original resampling budget')
        require((module.SECONDS,module.MIN_AVAILABLE_KIB,module.MAX_GROUP_RSS_KIB)==
                (1200,2097152,10485760),'original resource gates')
    require(first.__dict__ is not second.__dict__ and first.STOP is not second.STOP and
            first.CURRENT is not second.CURRENT and first.LOCK is not second.LOCK,
            'factories do not share telemetry state')
    require(function_text(derived['supervisor'],'controls')==
            function_text(originals['supervisor'],'controls'),'unchanged thirteen controls')
    refused(lambda:candidate.replace_exact(b'x\n',[('absent','changed')]),'old seam cardinality')
    refused(lambda:candidate.replace_exact(b'x\nx\n',[('x','changed')]),'old seam cardinality')
    return dict(positive=7,refusals=2,preserved_named_bodies=preserved,derivation=proof)


def source_controls():
    checked=candidate.source_guard()
    failures=[]
    with tempfile.TemporaryDirectory(prefix='exit-checked-source-') as directory:
        root=Path(directory)
        for path in candidate.REQUIRED:
            target=root/path;target.parent.mkdir(parents=True,exist_ok=True)
            target.write_bytes((candidate.ROOT/path).read_bytes())
        require(candidate.source_guard(root)==checked,'authentic source projection')
        for path in candidate.REQUIRED:
            target=root/path;raw=target.read_bytes()
            target.write_bytes(raw+b'\n# synthetic corruption\n')
            failures.append(refused(lambda:candidate.source_guard(root),'source bytes: '+path))
            target.write_bytes(raw)
        path=next(iter(candidate.REQUIRED));target=root/path;raw=target.read_bytes()
        target.unlink()
        failures.append(refused(lambda:candidate.source_guard(root),'source missing regular file: '+path))
        sibling=target.with_name(target.name+'.synthetic')
        sibling.write_bytes(raw);target.symlink_to(sibling)
        failures.append(refused(lambda:candidate.source_guard(root),'source path symlink: '+path))
        target.unlink();sibling.unlink();target.write_bytes(raw)
        with mock.patch.object(candidate,'ROOT',root):
            target.write_bytes(raw+b'\n# synthetic corruption\n')
            with mock.patch.object(candidate.importlib,'import_module',
                    side_effect=AssertionError('bootstrap must not run before source refusal')) as imports:
                refused(candidate.supervisor,'source bytes: '+path)
                require(imports.call_count==0,'source refusal precedes bootstrap')
            target.write_bytes(raw)
    return dict(positive=2,refusals=len(failures)+1,
                authenticated_source_files=len(checked),synthetic_source_mutations=True)


class Clock:
    def __init__(self):self.value=0.;self.sleeps=[]
    def monotonic(self):return self.value
    def sleep(self,duration):
        require(duration>=0,'nonnegative synthetic sleep')
        self.sleeps.append(duration);self.value=round(self.value+duration,12)


def identity(pid=PID,start=START,state='R',pgrp=PID):
    return dict(pid=pid,starttime=start,state=state,pgrp=pgrp)


def stat_text(value,flags=4):
    fields=['0']*20
    fields[0]=value['state'];fields[1]='1';fields[2]=str(value['pgrp'])
    fields[6]=str(flags)  # Diagnostic PF_EXITING is deliberately irrelevant to admission.
    fields[19]=str(value['starttime'])
    return str(value['pid'])+' (synthetic) '+' '.join(fields)+'\n'


class Process:
    def __init__(self,clock,exit_at,code):
        self.pid=PID;self.clock=clock;self.exit_at=exit_at
        self.code=code;self.returncode=None;self.polls=[]
    def poll(self):
        self.polls.append(self.clock.value)
        if self.returncode is None and self.clock.value>=self.exit_at:self.returncode=self.code
        return self.returncode
    def wait(self,timeout=None):
        require(self.poll() is not None,'synthetic wait requires actual completion or cleanup')
        return self.returncode


def synthetic_case(name,*,exit_at=.09,code=0,passed=True,old=False,fault=None,
                   expected_reason=None,expected_exception=None,seconds=1200,start_delay=0,pre_fix=False):
    """Real returned supervised()/snapshot; fake only clock, process and proc I/O."""
    with tempfile.TemporaryDirectory(prefix='exit-checked-'+name+'-') as directory:
        root=Path(directory);module=new_module(root);clock=Clock()
        process=Process(clock,exit_at,code)
        counts=dict(status_reads=0,missing_reads=0,meminfo_reads=0,census_reads=0,cleanup_calls=0,signals=[])
        terminal_called=[]
        module.time=types.SimpleNamespace(monotonic=clock.monotonic,sleep=clock.sleep,
                                          strftime=time.strftime,gmtime=time.gmtime)
        module.sample=lambda *args,**kwargs:None
        def start(*args,**kwargs):
            clock.value=start_delay
            return process
        module.subprocess=types.SimpleNamespace(
            Popen=start,CompletedProcess=subprocess.CompletedProcess)
        def live():
            rows=[]
            if process.poll() is None:rows.append(dict(pid=PID,state='R'))
            if fault=='live_child':rows.append(dict(pid=PID+1,state='R'))
            return rows
        module.live_members=lambda pgid:live()
        module.group_members=lambda pgid:live()
        def stop(p):
            counts['cleanup_calls']+=1
            if fault=='cleanup_first' and counts['cleanup_calls']==1:
                raise OSError('synthetic cleanup failure')
            signals=[]
            if p is not None and live():
                signals=['SIGTERM'];counts['signals']+=signals
                p.returncode=0
            return dict(signals=signals,remaining_live=[],remaining_nonrunning=[])
        module.stop_process=stop
        class Proc:
            enumeration_disappearances=[]
            def __init__(self,check):self.check=check
            def meminfo(self,path):
                self.check();counts['meminfo_reads']+=1
                if fault=='meminfo_permission':raise PermissionError('synthetic meminfo permission')
                if fault=='meminfo_malformed':return 'MemAvailable: unknown kB\n'
                return 'MemAvailable: '+str(1 if fault in ('low_available','missing_low_available') else 16*1024*1024)+' kB\n'
            def members(self,pgid):
                self.check()
                result=[identity()]
                if fault=='live_child':result.append(identity(PID+1,START+1))
                if fault=='partial_over_rss':result.insert(0,identity(PID-1,START-1))
                return result
            @contextlib.contextmanager
            def hold(self,pid):
                self.check()
                sequence=[0]
                def read(which):
                    self.check()
                    if which=='stat':
                        sequence[0]+=1
                        if fault=='stat_malformed':return 'broken proc stat\n'
                        changed=START-1 if pid==PID-1 else START
                        if fault=='sample_pid_reuse' and sequence[0]>1:changed+=1
                        return stat_text(identity(pid,changed),0 if fault=='flags_clear' else 4)
                    counts['status_reads']+=1
                    if fault=='status_permission':raise PermissionError('synthetic status permission')
                    prefix='Pid:\t'+str(pid)+'\nState:\tR (running)\n'
                    if fault=='status_malformed':return prefix+'VmRSS:\t1 MB\n'
                    if fault=='status_duplicate':return prefix+'VmRSS:\t1 kB\nVmRSS:\t2 kB\n'
                    if fault=='over_rss' or (fault=='partial_over_rss' and pid==PID-1):return prefix+'VmRSS:\t'+str(11*1024*1024)+' kB\n'
                    if fault=='prior_fresh' and counts['meminfo_reads']==1:return prefix+'VmRSS:\t1024 kB\n'
                    if fault=='low_available':return prefix+'VmRSS:\t1 kB\n'
                    counts['missing_reads']+=1
                    return prefix
                yield read
        module._memory_counter.ProcAccess=Proc
        class Terminal:
            def __init__(self,check):self.check=check
            def pids(self):
                self.check()
                if fault=='terminal_permission':raise PermissionError('synthetic terminal permission')
                if fault=='terminal_duplicate':return [PID,PID]
                if fault=='terminal_unknown':return [PID+50]
                if fault=='terminal_pid_reuse':return [PID]
                if fault=='live_child':return [PID+1]
                return []
            def identity_pair(self,pid):
                self.check();counts['census_reads']+=1
                if fault=='terminal_pid_reuse' and pid==PID:
                    value=identity(start=START+1,pgrp=1)
                    return dict(disposition='identity',before=value,after=value)
                if fault=='live_child' and pid==PID+1:
                    value=identity(PID+1,START+1)
                    return dict(disposition='identity',before=value,after=value)
                return dict(disposition='gone',error_type='ProcessLookupError',errno=3)
        module.terminal_access=Terminal
        actual_resolution=module.exit_checked_terminal
        def resolution(p,error,minimum,maximum):
            terminal_called.append(dict(at=clock.value,cleanup_calls=counts['cleanup_calls']))
            if fault=='expired_at_catch':clock.value=error.deadline+.001
            if fault=='history_mutation':error.history[-1]['disposition']='fresh_complete'
            if fault=='deadline_mutation':error.deadline+=1
            return actual_resolution(p,error,minimum,maximum)
        module.exit_checked_terminal=resolution
        actual_command_budget=module.exit_checked_command_deadline
        def command_budget(began,limit):
            if fault=='command_clock_error':raise OSError('synthetic command clock read failure')
            if fault=='command_clock_nonfinite':
                return candidate.command_budget_decision(float('nan'),began,limit)
            if fault=='command_clock_backwards':
                return candidate.command_budget_decision(began-.001,began,limit)
            return actual_command_budget(began,limit)
        module.exit_checked_command_deadline=command_budget
        original_event=module.event
        def event(kind,**kwargs):
            if fault=='snapshot_event_write' and kind=='memory_counter_resampling':
                raise OSError('synthetic snapshot event write failure')
            if fault=='event_write' and kind=='memory_terminal_resolution':
                raise OSError('synthetic terminal event write failure')
            return original_event(kind,**kwargs)
        module.event=event
        if old:
            raw=(candidate.ROOT/candidate.FROZEN_PATH).read_bytes()
            exec(compile(function_text(raw,'supervised'),str(candidate.ROOT/candidate.FROZEN_PATH),
                         'exec'),module.__dict__)
            raw=(candidate.ROOT/candidate.SAMPLER_PATH).read_bytes()
            exec(compile(function_text(raw,'snapshot'),str(candidate.ROOT/candidate.SAMPLER_PATH),
                         'exec'),module._memory_counter.__dict__)
        if pre_fix:
            proof_raw=(candidate.ROOT/PRIOR_REVIEW).read_bytes()
            require(hashlib.sha256(proof_raw).hexdigest()==PRIOR_REVIEW_SHA,'exact prior source-review bytes')
            proof=json.loads(proof_raw)['exact_derivation']['derived_supervisor']
            derived=(candidate.ROOT/candidate.FROZEN_PATH).read_text()
            for edit in proof['replacements']:
                require(derived.count(edit['old'])==1,'prior old seam cardinality')
                derived=derived.replace(edit['old'],edit['new'],1)
            require(len(derived.encode())==proof['bytes'] and
                    hashlib.sha256(derived.encode()).hexdigest()==proof['sha256'],
                    'exact actual pre-fix supervised body')
            exec(compile(function_text(derived.encode(),'supervised'),'<authenticated-pre-fix-supervised>',
                         'exec'),module.__dict__)
        error=None;result=None
        try:result=module.supervised(['synthetic-process'],name,passed,cwd=root,seconds=seconds)
        except BaseException as caught:error=caught
        record_path=root/(name+'.command.json')
        record=json.loads(record_path.read_text()) if record_path.exists() else None
        if expected_exception is not None:
            require(error is not None and expected_exception in str(error),
                    ('expected exact exceptional path',expected_exception,repr(error)))
            require(result is None,'exceptional path never returns success')
        elif expected_reason is not None:
            require(isinstance(error,module.SupervisionFailure),'supervision refusal type')
            require(record is not None and record['supervision_failure']==expected_reason,
                    ('exact supervision reason',record))
            require(result is None,'refused path never returns success')
        else:
            require(error is None,('unexpected synthetic failure',repr(error)))
            require(result.returncode==code and record['supervision_failure'] is None,
                    'actual original returncode contract')
        require(module.ACTIVE is None and module.CURRENT['child_pid'] is None,
                'actual finally restored shared telemetry state')
        if terminal_called:
            require(all(row['cleanup_calls']==0 for row in terminal_called),'terminal check precedes cleanup')
            require(counts['missing_reads']==3,'exactly three missing-RSS attempts, no fourth sample')
            require(clock.sleeps.count(.02)==2,'original two resampling sleeps')
        if record and record.get('memory_terminal_resolution'):
            diagnosis=record['memory_terminal_resolution']
            require(diagnosis['fresh_memory_sample'] is False and
                    diagnosis['PF_EXITING_used_for_acceptance'] is False,'no RSS/PF_EXITING waiver')
            if fault=='prior_fresh':
                require(record['last_memory_sentinel_sample']['group_rss_kib']==1024 and
                        record['last_memory_sentinel_sample']['sampling_attempts']==1,
                        'earlier measured sample preserved without refreshing')
            else:require(record['last_memory_sentinel_sample'] is None,'no manufactured fresh sample')
            require(record['memory_read_error'],'original error retained')
            require(diagnosis['attempts'][2]['observations'][-1]['disposition']=='missing_live_VmRSS',
                    'full original missing-counter evidence retained')
            if diagnosis['outcome']=='terminal_complete':
                require(diagnosis['finished_at']<=diagnosis['snapshot_deadline'] and not counts['signals'],
                        'resolved within original deadline without signals')
                require(diagnosis['parent_returncode']==code,'exact completed returncode retained')
                require(diagnosis['observed_resource_bounds_validated'] is True and
                        len(diagnosis['observed_resource_bounds'])==3,'all observed resource gates retained')
                if pre_fix:
                    require('command_budget_decision' not in diagnosis and
                            clock.value>=seconds and record['supervision_failure'] is None and result.returncode==0,
                            'exact pre-fix body reproduces command-deadline bypass')
                budget=diagnosis.get('command_budget_decision')
                events=[json.loads(line) for line in (root/'events.jsonl').read_text().splitlines()]
                rows=[row for row in events if row['event']=='memory_terminal_resolution']
                require(len(rows)==1 and rows[0]['resolution']==diagnosis,
                        'resolution event and command record have the same complete budget decision')
                if pre_fix:
                    require(budget is None,'pre-fix body cannot invent new budget proof')
                elif budget['status']=='checked':
                    require(budget['clock']=='time.monotonic' and budget['limit_seconds']==seconds,
                            'original caller command budget retained')
                    require(all(type(budget[key]) in (int,float) and math.isfinite(budget[key])
                                for key in ('began','observed_at','deadline','limit_seconds','elapsed_seconds')),
                            'finite same-clock command decision')
                    require(budget['began']==0 and budget['observed_at']==clock.value and
                            budget['elapsed_seconds']==budget['observed_at']-budget['began'] and
                            budget['deadline']==budget['began']+seconds,'exact command clock arithmetic')
                    if expected_reason=='elapsed_limit':
                        require(budget['within_limit'] is False and budget['observed_at']>=budget['deadline'],
                                'late or equal command completion refuses')
                    else:require(budget['within_limit'] is True,'successful command strictly before deadline')
                else:
                    require(budget['status']=='unavailable' and budget['within_limit'] is False and
                            expected_reason=='memory_sample_unavailable' and budget['error'],
                            'unavailable command clock remains fatal')
            elif fault not in ('expired_at_catch','deadline_mutation'):
                require(diagnosis['finished_at']<=diagnosis['snapshot_deadline']+.000000001,'no budget extension')
        if old:
            require(counts['status_reads']==3 and clock.value==.04 and counts['signals']==['SIGTERM'],
                    'actual old body rejects at third sample and cleanup causes rc0')
            require(record['returncode']==0 and record['supervision_failure']=='memory_sample_unavailable',
                    'old zero cleanup returncode is still failed')
        return dict(name=name,passed=True,synthetic_io=True,original_body=old,pre_fix_command_deadline_bypass=pre_fix,
                    status_reads=counts['status_reads'],terminal_called=len(terminal_called),
                    supervision_failure=record['supervision_failure'] if record else None,
                    exact_returncode=record['returncode'] if record else None)


def terminal_controls():
    rows=[]
    rows.append(synthetic_case('old-third-attempt',old=True,
                              expected_reason='memory_sample_unavailable'))
    rows.append(synthetic_case('within-budget-zero'))
    rows.append(synthetic_case('within-budget-seven',code=7,passed=False))
    rows.append(synthetic_case('original-positive-seven',code=7,
                              expected_exception='original-positive-seven'))
    rows.append(synthetic_case('at-final-poll',exit_at=.1))
    rows.append(synthetic_case('after-budget',exit_at=.101,
                              expected_reason='memory_sample_unavailable'))
    rows.append(synthetic_case('persistent-live',exit_at=float('inf'),
                              expected_reason='memory_sample_unavailable'))
    for fault in ('live_child','terminal_pid_reuse','terminal_unknown','terminal_permission',
                  'terminal_duplicate','expired_at_catch','history_mutation','deadline_mutation'):
        rows.append(synthetic_case(fault,fault=fault,expected_reason='memory_sample_unavailable'))
    for fault in ('status_permission','status_malformed','status_duplicate','stat_malformed',
                  'sample_pid_reuse','meminfo_permission','meminfo_malformed'):
        item=synthetic_case(fault,fault=fault,expected_reason='memory_sample_unavailable')
        require(item['terminal_called']==0,'only exact exhausted MissingRSS enters resolution')
        rows.append(item)
    rows.append(synthetic_case('original-rss-limit',fault='over_rss',
                              expected_reason='maximum_group_rss'))
    rows.append(synthetic_case('original-available-limit',fault='low_available',
                              expected_reason='minimum_available_memory'))
    rows.append(synthetic_case('event_write',fault='event_write',
                              expected_exception='synthetic terminal event write failure'))
    rows.append(synthetic_case('cleanup_first',fault='cleanup_first',
                              expected_exception='synthetic cleanup failure'))
    rows.append(synthetic_case('persistent-live-no-exit-flag',exit_at=float('inf'),fault='flags_clear',
                              expected_reason='memory_sample_unavailable'))
    for fault in ('missing_low_available','partial_over_rss','snapshot_event_write'):
        rows.append(synthetic_case(fault,fault=fault,expected_reason='memory_sample_unavailable'))
    rows.append(synthetic_case('prior-fresh-is-historical',exit_at=.59,fault='prior_fresh'))
    for limit in (1200,14400):
        for relation,offset in (('before',-.01),('equal',0),('after',.01)):
            rows.append(synthetic_case('command-'+str(limit)+'-'+relation,
                seconds=limit,start_delay=limit-.06,exit_at=limit+offset,
                expected_reason=None if relation=='before' else 'elapsed_limit'))
    for fault in ('command_clock_error','command_clock_nonfinite','command_clock_backwards'):
        rows.append(synthetic_case(fault,fault=fault,expected_reason='memory_sample_unavailable'))
    rows.append(synthetic_case('authenticated-pre-fix-command-bypass',seconds=1200,
        start_delay=1199.94,exit_at=1200.01,pre_fix=True))
    require(len(rows)==41,'authored terminal control count')
    return dict(cases=len(rows),old_body_regressions=1,command_budget_boundary_cases=6,
                command_budget_error_cases=3,pre_fix_command_deadline_regressions=1,rows=rows,
                native_execution=False,synthetic_process_proc_clock_io=True)


def direct_snapshot_controls():
    """Typed error must carry all original attempts and the original deadline."""
    clock=Clock();counter=candidate.supervisor()._memory_counter
    class Access:
        enumeration_disappearances=[]
        def meminfo(self,path):return 'MemAvailable: 16777216 kB\n'
        def members(self,pgid):return [identity()]
        @contextlib.contextmanager
        def hold(self,pid):
            def read(name):
                return stat_text(identity()) if name=='stat' else 'Pid: '+str(PID)+'\nState: R (running)\n'
            yield read
    events=[]
    try:
        counter.snapshot(PID,access=Access(),clock=clock.monotonic,pause=clock.sleep,
                         emit=lambda kind,**kwargs:events.append(dict(kind=kind,**kwargs)))
    except candidate.ExhaustedMissingRSS as error:
        require(error.began==0 and error.deadline==.1 and clock.value==.04,
                'exact original snapshot clock')
        require(len(error.history)==3 and [r['attempt'] for r in error.history]==[1,2,3],
                'complete ordered attempt history')
        require(len(events)==4 and events[-1]['outcome']=='rejected',
                'original rejected event remains explicit')
        require(error.original_error=="CounterError('Persistent unavailable live VmRSS')",
                'original exhaustion meaning retained')
        terminal=candidate.supervisor()
        terminal.time=types.SimpleNamespace(monotonic=lambda:.100001,sleep=clock.sleep)
        p=types.SimpleNamespace(pid=PID,poll=lambda:0)
        result=candidate.resolve_terminal(terminal,p,error)
        require(result['outcome']=='rejected' and not result['polls'],'expired budget never polls')
    else:raise AssertionError('Exhausted missing RSS accepted')
    return dict(positive=5,native_execution=False,synthetic_proc_clock=True)


def real_python_controls():
    with tempfile.TemporaryDirectory(prefix='exit-checked-real-python-') as directory:
        root=Path(directory);module=new_module(root)
        zero=module.supervised([sys.executable,'-c','import sys;print("zero");print("stderr",file=sys.stderr)'],
                              'real-zero',cwd=root)
        require(zero.returncode==0 and zero.stdout=='zero\n' and zero.stderr=='stderr\n',
                'real Python zero exact streams')
        seven=module.supervised([sys.executable,'-c','print("seven");raise SystemExit(7)'],
                               'real-seven',False,cwd=root)
        require(seven.returncode==7 and seven.stdout=='seven\n','real Python seven exact result')
        refused(lambda:module.supervised([sys.executable,'-c','raise SystemExit(7)'],
                'real-seven-positive',cwd=root),'real-seven-positive')
        require(module.ACTIVE is None,'actual Python children cleaned')
    return dict(positive=2,refusals=1,real_short_python_children=3,
                engine_or_native_archive_execution=False)


def original_controls():
    """Execute the unchanged thirteen-control body on the actual returned module."""
    with tempfile.TemporaryDirectory(prefix='exit-checked-original-') as directory:
        module=new_module(Path(directory)/'controls')
        guard=candidate.source_guard()
        # The historical controls' pins() names their old application run.
        # Replace only that source provenance lookup after authenticating all
        # declared inputs; preserve controls(), all helpers and process bodies.
        module.pins=lambda:dict(exit_checked_sources=guard,
                                synthetic_application_provenance_adapter=True)
        module.controls()
        result=json.loads((module.TRACE/'controls.json').read_text())
        require(result['status']=='PASS_RECORD_TELEMETRY_SOURCE_AND_SUPERVISION_CONTROLS_NO_RTL',
                'original result status')
        require(len(result['controls'])==13 and all(value is True for value in result['controls'].values()),
                'all thirteen original controls actually executed')
        require(result['engineering_accepted'] is False,'original no-engineering-acceptance scope')
        candidate.source_guard()
    return result


def controls():
    report=dict(status=STATUS,native_executed=False,engine_executed=False,
                routing_accepted=False,physical_acceptance=False,
                actual_failed_prefix_reclassified=False)
    report['source']=source_controls()
    report['derivation']=derivation_controls()
    report['snapshot']=direct_snapshot_controls()
    report['terminal']=terminal_controls()
    report['real_python']=real_python_controls()
    report['original_supervisor']=original_controls()
    return report


def main():
    parser=argparse.ArgumentParser()
    parser.add_argument('--output',required=True)
    args=parser.parse_args()
    require(os.environ.get('GITHUB_ACTIONS')=='true','GitHub actions only')
    require(os.environ.get('RUNNER_ENVIRONMENT')=='github-hosted','hosted runner only')
    require(os.environ.get('GITHUB_REPOSITORY')=='Melihakbulut221/nssoc','exact repository')
    require(os.environ.get('GITHUB_EVENT_NAME')=='workflow_dispatch','manual source controls only')
    require(os.environ.get('GITHUB_RUN_ATTEMPT')=='1','first attempt only')
    source=os.environ['GITHUB_SHA'];run=os.environ['GITHUB_RUN_ID']
    require(re.fullmatch('[0-9a-f]{40}',source) is not None and run.isdecimal(),'source/run context')
    report=controls()
    report['current_context']=dict(source=source,run_id=int(run),attempt=1,
        source_controls_only=True,native_executed=False)
    Path(args.output).write_text(json.dumps(report,sort_keys=True,indent=2)+'\n')
    print(json.dumps(report,sort_keys=True),flush=True)


if __name__=='__main__':
    main()
