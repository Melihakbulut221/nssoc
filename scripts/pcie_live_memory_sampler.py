#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0
"""Bounded fresh-RSS resampling; no resource limit or acceptance change."""
import ast, contextlib, hashlib, inspect, os, time
from pathlib import Path

FROZEN_SHA='e326e548ebe11550d18a049d639bdf063f03602d4ba08299b00a5747d3281c0b'
ATTEMPTS=3
INTERVAL=.02
RESAMPLE_WINDOW=.10
NONRUNNING=('Z','X','x')
STATES=frozenset('RSDZTtWXxKPI')

class CounterError(RuntimeError):pass
class MissingRSS(CounterError):
    def __init__(self,evidence):
        super().__init__('Live VmRSS temporarily absent')
        self.evidence=evidence

def identity(text):
    prefix,sep,tail=text.rpartition(') ')
    if not sep or ' ('not in prefix:raise CounterError('Malformed proc stat')
    pid=int(prefix.split(' (',1)[0]);f=tail.split()
    if len(f)<20 or f[0]not in STATES:raise CounterError('Incomplete proc stat')
    result=dict(pid=pid,state=f[0],pgrp=int(f[2]),starttime=int(f[19]))
    if min(result['pid'],result['pgrp'],result['starttime'])<0:
        raise CounterError('Negative process identity')
    return result

def same(a,b):
    return all(a[k]==b[k]for k in ('pid','pgrp','starttime'))

def counter(text,key):
    rows=[x.split()for x in text.splitlines()if x.startswith(key+':')]
    if len(rows)!=1 or len(rows[0])!=3 or rows[0][2]!='kB':
        raise CounterError('Malformed '+key+' counter or units')
    token=rows[0][1]
    if not token.isdecimal():raise CounterError('Nonnegative integer required for '+key)
    return int(token)

def one_field(text,key):
    rows=[x.split(':',1)[1].strip()for x in text.splitlines()if x.startswith(key+':')]
    if len(rows)!=1:raise CounterError('Missing or duplicate '+key)
    return rows[0]

class ProcAccess:
    def meminfo(self,path):return Path(path).read_text()
    def members(self,pgid):
        result=[]
        for path in Path('/proc').iterdir():
            if not path.name.isdecimal():continue
            try:value=identity((path/'stat').read_text())
            except FileNotFoundError:continue
            if value['pid']!=int(path.name):raise CounterError('Proc path PID mismatch')
            if value['pgrp']==pgid and value['state']not in NONRUNNING:result.append(value)
        return sorted(result,key=lambda x:x['pid'])
    @contextlib.contextmanager
    def hold(self,pid):
        fd=os.open('/proc/'+str(pid),os.O_RDONLY|os.O_DIRECTORY|os.O_NOFOLLOW|os.O_CLOEXEC)
        try:
            def read(name):
                assert name in ('stat','status')
                child=os.open(name,os.O_RDONLY|os.O_NOFOLLOW|os.O_CLOEXEC,dir_fd=fd)
                try:
                    chunks=[];size=0
                    while True:
                        b=os.read(child,16384)
                        if not b:break
                        size+=len(b)
                        if size>1024*1024:raise CounterError('Oversized proc counter file')
                        chunks.append(b)
                    return b''.join(chunks).decode('ascii')
                finally:os.close(child)
            yield read
        finally:os.close(fd)

def member_observation(access,expected):
    observed=dict(expected=expected)
    try:
        with access.hold(expected['pid'])as read:
            try:before=identity(read('stat'))
            except FileNotFoundError:
                return dict(**observed,disposition='exited_before_first_held_stat')
            observed['before']=before
            if not same(expected,before):raise CounterError('Process identity changed before counter')
            if before['state']in NONRUNNING:return dict(**observed,disposition='nonrunning_before_counter')
            try:
                text=read('status')
                observed['status_sha256']=hashlib.sha256(text.encode()).hexdigest()
                missing_file=False
            except FileNotFoundError:text=None;missing_file=True
            try:after=identity(read('stat'))
            except FileNotFoundError:return dict(**observed,disposition='exited_after_counter_read')
            observed['after']=after
            if not same(before,after):raise CounterError('Process identity changed after counter')
            if after['state']in NONRUNNING:return dict(**observed,disposition='nonrunning_after_counter')
            if missing_file:
                observed.update(disposition='missing_live_status_file')
                raise MissingRSS(observed)
            if one_field(text,'Pid')!=str(expected['pid']):raise CounterError('Status PID mismatch')
            state=one_field(text,'State').split()[0]
            if state not in STATES or state in NONRUNNING:raise CounterError('Status/stat live-state inconsistency')
            rows=[x for x in text.splitlines()if x.startswith('VmRSS:')]
            if not rows:
                observed.update(disposition='missing_live_VmRSS')
                raise MissingRSS(observed)
            observed.update(disposition='measured_fresh',rss_kib=counter(text,'VmRSS'))
            return observed
    except CounterError as error:
        error.evidence=observed
        raise
    except FileNotFoundError:
        # No numeric-path rebinding: opening the originally enumerated proc
        # directory failed. No zero or stale RSS is substituted.
        return dict(**observed,disposition='gone_before_held_directory')

def snapshot(pgid,meminfo_path='/proc/meminfo',*,access=None,emit=None,
             clock=time.monotonic,pause=time.sleep):
    access=ProcAccess()if access is None else access
    emit=(lambda *a,**kw:None)if emit is None else emit
    history=[];identities={};resampling_began=None
    try:
        for attempt in range(ATTEMPTS):
            current=dict(attempt=attempt+1,observations=[])
            history.append(current)
            available=counter(access.meminfo(meminfo_path),'MemAvailable')
            current['available_kib']=available
            pending=None;members=[]
            enumerated=access.members(pgid);current['enumerated']=enumerated
            for expected in enumerated:
                if expected['pgrp']!=pgid:raise CounterError('Wrong enumerated process group')
                key=expected['pid']
                if key in identities and not same(identities[key],expected):
                    raise CounterError('PID identity changed across resamples')
                identities[key]=expected
                try:entry=member_observation(access,expected)
                except MissingRSS as error:
                    current['observations'].append(error.evidence);pending=error;break
                except CounterError as error:
                    current['observations'].append(getattr(error,'evidence',dict(expected=expected)))
                    raise
                current['observations'].append(entry)
                if entry['disposition']=='measured_fresh':
                    members.append(dict(pid=key,starttime=expected['starttime'],
                      pgrp=pgid,rss_kib=entry['rss_kib']))
            if pending is None:
                if resampling_began is not None and clock()-resampling_began>RESAMPLE_WINDOW:
                    raise CounterError('Fresh resample exceeded bounded window')
                current['disposition']='fresh_complete'
                result=dict(available_kib=available,group_rss_kib=sum(x['rss_kib']for x in members),
                  members=members,group_rss_may_double_count_shared_pages=True,
                  sampling_attempts=len(history),resampling_evidence=history if len(history)>1 else [],
                  excluded_nonrunning=[x for x in current['observations']if x['disposition']!='measured_fresh'])
                if len(history)>1:emit('memory_counter_resampling',outcome='fresh_complete',attempts=history)
                return result
            current['disposition']='retry_missing_live_counter'
            if resampling_began is None:resampling_began=clock()
            emit('memory_counter_resample_attempt',attempt=current,
                 maximum_attempts=ATTEMPTS,window_seconds=RESAMPLE_WINDOW)
            if attempt+1==ATTEMPTS:raise CounterError('Persistent unavailable live VmRSS')
            if clock()-resampling_began+INTERVAL>RESAMPLE_WINDOW:
                raise CounterError('Missing-counter resampling window exhausted')
            pause(INTERVAL)
    except Exception as error:
        emit('memory_counter_resampling',outcome='rejected',error=repr(error),attempts=history)
        raise

def install(supervisor):
    raw=Path(supervisor.__file__).read_bytes()
    if hashlib.sha256(raw).hexdigest()!=FROZEN_SHA:raise CounterError('Frozen supervisor changed')
    old=supervisor.memory_snapshot
    if getattr(old,'bounded_fresh_rss_adapter',False):return
    module=ast.parse(raw)
    node=next(n for n in module.body if isinstance(n,ast.FunctionDef)and n.name=='memory_snapshot')
    expected=ast.get_source_segment(raw.decode(),node)
    if inspect.getsource(old).strip()!=expected.strip():raise CounterError('Unexpected sampler seam')
    def measured(pgid,meminfo_path='/proc/meminfo'):
        try:return snapshot(pgid,meminfo_path,emit=supervisor.event)
        except Exception as error:raise supervisor.SupervisionFailure(repr(error))from error
    measured.bounded_fresh_rss_adapter=True
    measured.original_source_sha256=hashlib.sha256(expected.encode()).hexdigest()
    supervisor.memory_snapshot=measured
