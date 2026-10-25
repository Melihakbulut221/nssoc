#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0
"""Hosted-only deterministic sampler controls and harmless real process churn."""
import contextlib, copy, json, os, subprocess, sys, time
from pathlib import Path
from unittest import mock
import pcie_live_memory_sampler as a

def stat(pid=71,group=71,start=123,state='R'):
    tail=[state,'1',str(group)]+['0']*16+[str(start)]
    return str(pid)+' (fixture) '+' '.join(tail)+'\n'

def status(rss='41',unit='kB',state='R',pid=71):
    text='Pid: '+str(pid)+'\nState: '+state+' (fixture)\n'
    return text if rss is None else text+'VmRSS: '+rss+' '+unit+'\n'

def sample_record(**changes):
    result=dict(before=stat(),after=stat(),status=status())
    result.update(changes);return result

class FakeAccess:
    def __init__(self,attempts,meminfo=None,enumerated=None):
        self.attempts=attempts;self.step=-1;self.reads=[]
        self.infos=meminfo or ['MemAvailable: 10000000 kB\n']*len(attempts)
        self.enumerated=enumerated
    def meminfo(self,path):
        self.step+=1
        value=self.infos[min(self.step,len(self.infos)-1)]
        if isinstance(value,Exception):raise value
        return value
    def members(self,pgid):
        if self.enumerated is not None:return self.enumerated[min(self.step,len(self.enumerated)-1)]
        return [a.identity(stat())]
    @contextlib.contextmanager
    def hold(self,pid):
        r=self.attempts[min(self.step,len(self.attempts)-1)]
        if isinstance(r,Exception):raise r
        n=0
        def read(name):
            nonlocal n
            key='status'if name=='status'else('before'if n==0 else'after')
            if name=='stat':n+=1
            self.reads.append((self.step,key))
            value=r[key]
            if isinstance(value,Exception):raise value
            return value
        yield read

class Clock:
    def __init__(self):self.value=0.;self.pauses=[]
    def now(self):return self.value
    def pause(self,dt):self.pauses.append(dt);self.value+=dt

def exercise(access,clock=None):
    clock=clock or Clock();events=[]
    value=a.snapshot(71,access=access,clock=clock.now,pause=clock.pause,
                     emit=lambda name,**kw:events.append(dict(event=name,**kw)))
    return value,events,clock

def controls(supervisor):
    supervisor.host()
    passed={};rejected={}
    transient=FakeAccess([sample_record(status=status(None)),sample_record(status=status('99'))],
      meminfo=['MemAvailable: 111 kB\n','MemAvailable: 222 kB\n'])
    r,e,c=exercise(transient)
    assert r['group_rss_kib']==99 and r['available_kib']==222 and r['sampling_attempts']==2
    assert r['members'][0]['starttime']==123 and c.pauses==[a.INTERVAL]
    assert len(e)==2 and e[0]['attempt']['observations'][0]['disposition']=='missing_live_VmRSS'
    passed['transient_missing_then_fresh_RSS_and_MemAvailable']=True
    r,e,c=exercise(FakeAccess([sample_record()]))
    assert r['group_rss_kib']==41 and r['sampling_attempts']==1 and not e and not c.pauses
    passed['stable_single_fresh_measurement']=True
    r,e,c=exercise(FakeAccess([sample_record(status=status(None)),sample_record(status=status(None)),sample_record(status=status('87'))]))
    assert r['group_rss_kib']==87 and r['sampling_attempts']==3 and c.pauses==[a.INTERVAL]*2
    passed['last_bounded_attempt_fresh']=True
    for name,record in [
      ('gone_before_open',FileNotFoundError('fixture gone')),
      ('gone_before_first_stat',sample_record(before=FileNotFoundError('fixture gone'))),
      ('gone_after_status',sample_record(after=FileNotFoundError('fixture gone'))),
      ('zombie_after_status',sample_record(after=stat(state='Z')))]:
        r,e,c=exercise(FakeAccess([record]))
        assert r['members']==[] and r['group_rss_kib']==0
        assert len(r['excluded_nonrunning'])==1 and not c.pauses
        passed[name+'_excluded_with_observed_exit']=True
    r,e,c=exercise(FakeAccess([sample_record(status=FileNotFoundError('fixture status')),sample_record(status=status('43'))]))
    assert r['group_rss_kib']==43 and r['sampling_attempts']==2
    passed['held_live_missing_status_then_fresh']=True

    def reject(name,access,expected,pauses=None,clock=None):
        events=[];clock=clock or Clock()
        try:a.snapshot(71,access=access,clock=clock.now,pause=clock.pause,
          emit=lambda kind,**kw:events.append(dict(event=kind,**kw)))
        except (a.CounterError,PermissionError,UnicodeError)as error:
            assert expected in str(error),(name,repr(error))
            assert events[-1]['outcome']=='rejected'
            if pauses is not None:assert len(clock.pauses)==pauses
            rejected[name]=dict(rejected=True,error_type=type(error).__name__,events=events)
        else:raise AssertionError('Sampler control survived: '+name)
    reject('persistent_missing_RSS',FakeAccess([sample_record(status=status(None))]),'Persistent',2)
    for name,text in [
      ('negative',status('-1')),('wrong_units',status('4','MB')),
      ('noninteger',status('1.5')),('nonnumeric',status('nan')),
      ('duplicate',status()+'VmRSS: 5 kB\n'),('wrong_PID',status(pid=72)),
      ('missing_PID','State: R\nVmRSS: 41 kB\n'),
      ('terminal_status_live_stat',status(state='Z'))]:
        reject('RSS_'+name,FakeAccess([sample_record(status=text)]),
               'Status'if name in ('wrong_PID','terminal_status_live_stat')else
               'Pid'if name=='missing_PID'else 'VmRSS',0)
    reject('status_permission',FakeAccess([sample_record(status=PermissionError('denied-status'))]),'denied-status',0)
    reject('stat_permission',FakeAccess([sample_record(before=PermissionError('denied-stat'))]),'denied-stat',0)
    reject('proc_directory_permission',FakeAccess([PermissionError('denied-directory')]),'denied-directory',0)
    reject('malformed_stat',FakeAccess([sample_record(before='bad')]),'Malformed proc stat',0)
    reject('identity_before',FakeAccess([sample_record(before=stat(start=999))]),'identity changed before',0)
    reject('identity_after',FakeAccess([sample_record(after=stat(start=999))]),'identity changed after',0)
    reject('group_transition',FakeAccess([sample_record(after=stat(group=72))]),'identity changed after',0)
    first=a.identity(stat());second=a.identity(stat(start=999))
    reject('PID_reuse_between_attempts',FakeAccess([sample_record(status=status(None)),sample_record()],
          enumerated=[[first],[second]]),'identity changed across',1)
    for name,info in [
      ('missing','MemFree: 42 kB\n'),('units','MemAvailable: 42 MB\n'),
      ('negative','MemAvailable: -1 kB\n'),
      ('permission',PermissionError('denied-meminfo'))]:
        reject('MemAvailable_'+name,FakeAccess([sample_record()],meminfo=[info]),
               'denied-meminfo'if name=='permission'else'MemAvailable',0)
    class SlowClock(Clock):
        def pause(self,dt):super().pause(dt);self.value+=1
    reject('finite_window',FakeAccess([sample_record(status=status(None)),sample_record()]),
           'bounded window',1,SlowClock())

    # The real production enumeration loop shares the same total-call budget.
    class GrowingEntry:
        def __init__(self,index,clock):self.name=str(100+index);self.clock=clock
        def __truediv__(self,name):assert name=='stat';return self
        def read_text(self):
            self.clock.value+=.011
            return stat(pid=int(self.name))
    class GrowingProc:
        def __init__(self,clock):self.clock=clock;self.read_count=0
        def iterdir(self):
            for i in range(1000):
                self.read_count+=1;yield GrowingEntry(i,self.clock)
    clk=Clock();directory=GrowingProc(clk)
    class GrowingAccess(a.ProcAccess):
        def meminfo(self,path):return 'MemAvailable: 1000 kB\n'
    production=GrowingAccess()
    def guard():
        if clk.now()>a.RESAMPLE_WINDOW:raise a.CounterError('total enumeration bounded window')
    production.check=guard
    with mock.patch.object(a,'Path',lambda path:directory):
        reject('growing_group_total_budget',production,'bounded window',0,clk)
    assert 1<directory.read_count<1000
    clk=Clock()
    class SlowReadAccess(FakeAccess):
        @contextlib.contextmanager
        def hold(self,pid):
            with super().hold(pid)as read:
                def slow(name):
                    if name=='status':clk.value+=1
                    return read(name)
                yield slow
    reject('held_member_read_total_budget',SlowReadAccess([sample_record()]),
           'bounded window',0,clk)

    # Real Linux /proc identities under harmless short-lived process churn.
    # No resource stress, compiler, RTL, network or archive operation.
    code=("import subprocess,sys,time\n"
          "for i in range(48):\n"
          " subprocess.run([sys.executable,'-c','pass'],check=True)\n"
          " time.sleep(.005)\n"
          "time.sleep(.15)\n")
    proc=subprocess.Popen([sys.executable,'-c',code],stdout=subprocess.PIPE,stderr=subprocess.PIPE,
                           start_new_session=True)
    samples=[];events=[];deadline=time.monotonic()+10
    try:
        while proc.poll()is None:
            assert time.monotonic()<deadline,'bounded harmless churn timeout'
            samples.append(a.snapshot(proc.pid,emit=lambda kind,**kw:events.append(dict(event=kind,**kw))))
            time.sleep(.003)
        stdout,stderr=proc.communicate(timeout=2)
        assert proc.returncode==0 and not stdout and not stderr
    finally:cleanup=supervisor.stop_process(proc)
    assert len(samples)>=3 and not cleanup['remaining_live']
    assert all(x['available_kib']>=0 and x['group_rss_kib']>=0 for x in samples)
    assert any(len(x['members'])>=2 for x in samples),'actual child membership never observed'
    passed['real_short_lived_churn_held_proc_identity']=True
    assert len(passed)==9 and len(rejected)==24
    return dict(status='PASS_BOUNDED_FRESH_MEMORY_SAMPLER_CONTROLS_NO_RTL',
      positives=passed,rejected=rejected,real_churn=dict(samples=len(samples),
      maximum_observed_members=max(len(x['members'])for x in samples),
      resampling_events=events,cleanup=cleanup),limits_changed=False,
      stale_or_zero_counter_substitution=False,native_CDC_executed=False)
