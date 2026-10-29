#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0
"""Terminal-only missing-RSS reconciliation, within the original 100 ms budget.

No fresh RSS is inferred and no PF_EXITING flag grants admission.  This module
does not authorize routing.  The returned supervisor owns one globals namespace.
"""
import ast
import copy
import hashlib
import importlib
import math
import os
import types
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
FROZEN_PATH='hw/soc/pcie-evidence/20261025-gen12-record-qualified-source/scripts/cloud_pcie_gen12_training_records_telemetry.py'
SAMPLER_PATH='scripts/pcie_live_memory_sampler.py'
LOADER_PATH='scripts/cloud_mainchip_original_clock_restoration.py'
REQUIRED={'hw/soc/pcie-evidence/20261025-gen12-record-qualified-source/scripts/cloud_pcie_gen12_training_records_telemetry.py': {'bytes': 22471, 'sha256': 'e326e548ebe11550d18a049d639bdf063f03602d4ba08299b00a5747d3281c0b'}, 'scripts/pcie_live_memory_sampler.py': {'bytes': 10879, 'sha256': '55fb9a3ba9a049c509b629e8638a688b5f827316485f9fd89cd5a8888804df07'}, 'scripts/cloud_mainchip_original_clock_restoration.py': {'bytes': 12028, 'sha256': '7700e04988a916977727b44e880f47ae8d8ae454553c8702eacae5951d743646'}, 'hw/soc/pcie-evidence/20261025-gen12-record-qualified-source/scripts/check_pcie_gen12_training_records.py': {'bytes': 28358, 'sha256': 'e1bf844ef719b4ad4230aebc58550ee577da72d88958b7724400d1c4c14c8f5a'}, 'hw/soc/pcie-evidence/20261025-gen12-record-qualified-source/scripts/check_pcie_gen12_raw32_rx.py': {'bytes': 15431, 'sha256': '451667d66bb77df193e56ed60cc82f91738d676316e4b6016f3bc9d119d7c7da'}, 'hw/soc/pcie-evidence/20261025-gen12-record-qualified-source/scripts/check_pcie_gen12_tx_raw32.py': {'bytes': 16940, 'sha256': 'b19d118fc2d2b71a8f74361a5ca315c9b137cdb1916decd9aec0d189d084a577'}}
ATTEMPTS=3
INTERVAL=.02
WINDOW=.10
TERMINAL_POLL=.005
SNAPSHOT_REPLACEMENTS=[("if attempt+1==ATTEMPTS:raise CounterError('Persistent unavailable live VmRSS')", 'if attempt+1==ATTEMPTS:raise ExhaustedMissingRSS(pgid,history,began,deadline)')]
SUPERVISED_REPLACEMENTS=[('began=time.monotonic();reason=None;p=None;memory=None;memory_error=None', 'began=time.monotonic();reason=None;p=None;memory=None;memory_error=None;memory_terminal_resolution=None'), ("                    except Exception as e:reason='memory_sample_unavailable';memory_error=repr(e)", "                    except Exception as e:\n                        reason='memory_sample_unavailable';memory_error=repr(e)\n                        if type(e) is ExhaustedMissingRSS:\n                            memory_terminal_resolution=exit_checked_terminal(p,e,min_available_kib,max_group_rss_kib)\n                            if memory_terminal_resolution['outcome']=='terminal_complete':\n                                try:\n                                    budget=exit_checked_command_deadline(began,seconds)\n                                except Exception as budget_error:\n                                    budget=dict(status='unavailable',clock='time.monotonic',\n                                                within_limit=False,error=repr(budget_error))\n                                memory_terminal_resolution['command_budget_decision']=budget\n                                if budget['status']=='checked':\n                                    reason=None if budget['within_limit'] else 'elapsed_limit'\n                            event('memory_terminal_resolution',label=label,\n                                  memory_read_error=memory_error,\n                                  resolution=memory_terminal_resolution)\n                            if memory_terminal_resolution['outcome']=='terminal_complete':\n                                break"), ("'last_memory_sentinel_sample':memory,'memory_read_error':memory_error,", "'last_memory_sentinel_sample':memory,'memory_read_error':memory_error,\n          'memory_terminal_resolution':memory_terminal_resolution,")]


class ExitCheckError(RuntimeError):
    pass


class ExhaustedMissingRSS(RuntimeError):
    """Only the third exhausted, otherwise valid MissingRSS observation."""
    def __init__(self,pgid,history,began,deadline):
        super().__init__('Persistent unavailable live VmRSS')
        self.pgid=pgid
        self.history=copy.deepcopy(history)
        self.began=began
        self.deadline=deadline
        self.original_error="CounterError('Persistent unavailable live VmRSS')"


def source_guard(root=None):
    root=ROOT if root is None else Path(root)
    result={}
    for relative,expected in REQUIRED.items():
        path=root/relative
        current=root
        if root.is_symlink():raise ExitCheckError('source root symlink')
        for part in Path(relative).parts:
            current=current/part
            if current.is_symlink():raise ExitCheckError('source path symlink: '+relative)
        if not path.is_file():raise ExitCheckError('source missing regular file: '+relative)
        raw=path.read_bytes()
        actual=dict(bytes=len(raw),sha256=hashlib.sha256(raw).hexdigest())
        if actual!=expected:raise ExitCheckError('source bytes: '+relative)
        result[relative]=actual
    return result


def replace_exact(raw,replacements):
    text=raw.decode('utf-8')
    for old,new in replacements:
        if text.count(old)!=1:raise ExitCheckError('derivation old seam cardinality')
        text=text.replace(old,new,1)
    reverse=text
    for old,new in reversed(replacements):
        if reverse.count(new)!=1:raise ExitCheckError('derivation new seam cardinality')
        reverse=reverse.replace(new,old,1)
    if reverse.encode()!=raw:raise ExitCheckError('derivation reverse bytes')
    return text.encode()


def derive_sources(root=None):
    root=ROOT if root is None else Path(root)
    checked=source_guard(root)
    frozen=(root/FROZEN_PATH).read_bytes()
    sampler=(root/SAMPLER_PATH).read_bytes()
    result=dict(
        supervisor=replace_exact(frozen,SUPERVISED_REPLACEMENTS),
        sampler=replace_exact(sampler,SNAPSHOT_REPLACEMENTS))
    for key,value in result.items():ast.parse(value,filename=key)
    return result,dict(original=checked,derived={
        key:dict(bytes=len(value),sha256=hashlib.sha256(value).hexdigest())
        for key,value in result.items()},supervisor_seams=3,snapshot_seams=1,
        historical_files_changed=False)


class TerminalAccess:
    """Held /proc identity reads; unknown/unreadable entries cannot resolve."""
    def __init__(self,counter,check):
        self.counter=counter
        self.check=check
        self.access=counter.ProcAccess(check=check)

    def pids(self):
        result=[]
        for path in Path('/proc').iterdir():
            self.check()
            if path.name.isdecimal():result.append(int(path.name))
        self.check()
        return sorted(result)

    def identity_pair(self,pid):
        self.check()
        try:
            with self.access.hold(pid) as read:
                before=self.counter.identity(read('stat'));self.check()
                after=self.counter.identity(read('stat'));self.check()
        except (FileNotFoundError,ProcessLookupError) as error:
            return dict(disposition='gone',error_type=type(error).__name__,errno=error.errno)
        if before['pid']!=pid or after['pid']!=pid:
            raise ExitCheckError('terminal proc path PID mismatch')
        if not self.counter.same(before,after):
            raise ExitCheckError('terminal identity changed during held read')
        return dict(disposition='identity',before=before,after=after)


def known_identities(error,counter):
    if type(error) is not ExhaustedMissingRSS:
        raise ExitCheckError('terminal exception type')
    if type(error.pgid) is not int or error.pgid<=0:
        raise ExitCheckError('terminal process group')
    if len(error.history)!=ATTEMPTS:
        raise ExitCheckError('terminal requires exactly three attempts')
    if error.deadline!=error.began+WINDOW:
        raise ExitCheckError('terminal original deadline')
    known={}
    for number,item in enumerate(error.history,1):
        if item['attempt']!=number or item['disposition']!='retry_missing_live_counter':
            raise ExitCheckError('terminal attempt history')
        if item.get('enumeration_disappearances'):
            raise ExitCheckError('terminal unknown resampling identities')
        if not item['observations'] or item['observations'][-1].get('disposition') not in (
                'missing_live_status_file','missing_live_VmRSS'):
            raise ExitCheckError('terminal requires missing counter evidence')
        for identity in item['enumerated']:
            if identity['pgrp']!=error.pgid:
                raise ExitCheckError('terminal historical process group')
            pid=identity['pid']
            if pid in known and not counter.same(known[pid],identity):
                raise ExitCheckError('terminal historical PID reuse')
            known[pid]=identity
    if error.pgid not in known:
        raise ExitCheckError('terminal leader identity absent')
    return known


def terminal_census(counter,access,pgid,known,check):
    """Two complete scans: no live, unknown, reused or unanchored group member."""
    scans=[]
    for _ in range(2):
        check()
        listed=access.pids();check()
        if len(listed)!=len(set(listed)) or any(type(pid) is not int or pid<=0 for pid in listed):
            raise ExitCheckError('terminal invalid PID census')
        group=[];gone=[];live=[];unknown=[]
        for pid in sorted(set(listed)|set(known)):
            check()
            item=access.identity_pair(pid);check()
            if item['disposition']=='gone':
                if pid in known:gone.append(pid)
                else:unknown.append(dict(pid=pid,reason='unidentified disappearance'))
                continue
            if item['disposition']!='identity':
                raise ExitCheckError('terminal unknown identity disposition')
            before=item['before'];after=item['after']
            if before['pid']!=pid or after['pid']!=pid or not counter.same(before,after):
                raise ExitCheckError('terminal held identity mismatch')
            if pid in known and not counter.same(known[pid],after):
                raise ExitCheckError('terminal known PID reused or changed group')
            if after['pgrp']==pgid:
                group.append(dict(pid=pid,before=before,after=after))
                if pid not in known:
                    unknown.append(dict(pid=pid,reason='unanchored group identity'))
                if before['state'] not in counter.NONRUNNING or after['state'] not in counter.NONRUNNING:
                    live.append(pid)
        scans.append(dict(enumerated_count=len(listed),group=group,
                          known_gone=gone,live=live,unknown=unknown))
        if live or unknown:
            return dict(complete=False,scans=scans)
    check()
    return dict(complete=True,scans=scans)


def resolve_terminal(module,p,error,min_available_kib=None,max_group_rss_kib=None):
    """No signals, counters, PIDs, resource limits or deadlines are substituted."""
    clock=module.time.monotonic
    min_available_kib=module.MIN_AVAILABLE_KIB if min_available_kib is None else min_available_kib
    max_group_rss_kib=module.MAX_GROUP_RSS_KIB if max_group_rss_kib is None else max_group_rss_kib
    report=dict(outcome='rejected',original_error=error.original_error,
        original_memory_error=repr(error),attempts=copy.deepcopy(error.history),
        snapshot_began=error.began,snapshot_deadline=error.deadline,
        total_budget_seconds=WINDOW,fresh_memory_sample=False,
        minimum_available_kib=min_available_kib,maximum_group_rss_kib=max_group_rss_kib,
        PF_EXITING_used_for_acceptance=False,cleanup_started=False,polls=[])
    def bound():
        now=clock()
        if now<error.began or now>error.deadline:
            raise ExitCheckError('terminal original snapshot deadline exhausted')
    try:
        known=known_identities(error,module._memory_counter)
        observed=[]
        for attempt in error.history:
            available=attempt['available_kib']
            partial=[row['rss_kib'] for row in attempt['observations']
                     if row.get('disposition')=='measured_fresh']
            if type(available) is not int or available<0 or any(type(x) is not int or x<0 for x in partial):
                raise ExitCheckError('terminal malformed observed resource counter')
            lower_bound=sum(partial)
            observed.append(dict(attempt=attempt['attempt'],available_kib=available,
                                 partial_group_rss_lower_bound_kib=lower_bound,
                                 full_group_rss_measured=False))
            report['observed_resource_bounds']=observed
            if available<min_available_kib:
                raise ExitCheckError('terminal observed minimum_available_memory')
            if lower_bound>max_group_rss_kib:
                raise ExitCheckError('terminal observed maximum_group_rss lower bound')
        report['observed_resource_bounds_validated']=True
        if p is None or p.pid!=error.pgid:
            raise ExitCheckError('terminal owned parent mismatch')
        access=module.terminal_access(bound)
        while True:
            bound()
            code=p.poll()
            entry=dict(at=clock(),parent_returncode=code)
            report['polls'].append(entry)
            bound()
            if code is not None:
                census=terminal_census(module._memory_counter,access,p.pid,known,bound)
                entry['census']=census
                final_code=p.poll();bound()
                if final_code!=code:
                    raise ExitCheckError('terminal parent returncode changed')
                if census['complete']:
                    report.update(outcome='terminal_complete',parent_returncode=code,
                                  completed_before_cleanup=True)
                    break
            remaining=error.deadline-clock()
            if remaining<=0:
                raise ExitCheckError('terminal original snapshot deadline exhausted')
            module.time.sleep(min(TERMINAL_POLL,remaining))
    except Exception as failure:
        report['resolution_error']=repr(failure)
    report['finished_at']=clock()
    report['elapsed_from_snapshot_start_seconds']=report['finished_at']-error.began
    if report['outcome']=='terminal_complete' and not error.began<=report['finished_at']<=error.deadline:
        report['outcome']='rejected'
        report['resolution_error']='terminal final original snapshot deadline exhausted'
        report.pop('completed_before_cleanup',None)
    return report


def command_budget_decision(now,began,seconds):
    """Fresh same-clock deadline decision; equality and unavailable clocks fail."""
    values=(now,began,seconds)
    if any(type(value) not in (int,float) or not math.isfinite(value) for value in values):
        raise ExitCheckError('nonfinite or invalid command clock/budget')
    if seconds<=0 or now<began:
        raise ExitCheckError('invalid command clock ordering or budget')
    deadline=began+seconds;elapsed=now-began
    if not math.isfinite(deadline) or not math.isfinite(elapsed):
        raise ExitCheckError('nonfinite command deadline arithmetic')
    return dict(status='checked',clock='time.monotonic',began=began,
        observed_at=now,deadline=deadline,limit_seconds=seconds,elapsed_seconds=elapsed,
        within_limit=now<deadline and elapsed<seconds)


def supervisor():
    """Fresh isolated module, with every telemetry stateful function co-located."""
    derived,proof=derive_sources()
    legacy=importlib.import_module('cloud_mainchip_original_clock_restoration')
    if Path(legacy.__file__).resolve()!=ROOT/LOADER_PATH:
        raise ExitCheckError('legacy loader origin')
    bootstrap=legacy.supervisor()
    for name in ('check_pcie_gen12_training_records','check_pcie_gen12_raw32_rx','check_pcie_gen12_tx_raw32'):
        dependency=importlib.import_module(name)
        expected=ROOT/Path(FROZEN_PATH).parent/(name+'.py')
        if Path(dependency.__file__).resolve()!=expected:
            raise ExitCheckError('bootstrap dependency origin: '+name)
    source_guard()
    module=types.ModuleType('_mainchip_exit_checked_telemetry')
    module.__file__=str(ROOT/FROZEN_PATH)
    module.ExhaustedMissingRSS=ExhaustedMissingRSS
    exec(compile(derived['supervisor'],module.__file__,'exec'),module.__dict__)
    counter=types.ModuleType('_mainchip_exit_checked_memory')
    counter.__file__=str(ROOT/SAMPLER_PATH)
    counter.ExhaustedMissingRSS=ExhaustedMissingRSS
    exec(compile(derived['sampler'],counter.__file__,'exec'),counter.__dict__)
    if (counter.ATTEMPTS,counter.INTERVAL,counter.RESAMPLE_WINDOW)!=(ATTEMPTS,INTERVAL,WINDOW):
        raise ExitCheckError('original counter budget changed')
    module._memory_counter=counter
    module.terminal_access=lambda check:TerminalAccess(counter,check)
    module.exit_checked_terminal=lambda p,error,minimum,maximum:resolve_terminal(module,p,error,minimum,maximum)
    module.exit_checked_command_deadline=lambda began,seconds:command_budget_decision(module.time.monotonic(),began,seconds)
    def measured(pgid,meminfo_path='/proc/meminfo'):
        try:
            return counter.snapshot(pgid,meminfo_path,emit=module.event,
                                    clock=module.time.monotonic,pause=module.time.sleep)
        except ExhaustedMissingRSS:
            raise
        except Exception as error:
            raise module.SupervisionFailure(repr(error)) from error
    measured.bounded_fresh_rss_adapter=True
    measured.exit_checked_adapter=True
    module.memory_snapshot=measured
    module.OUT=bootstrap.OUT
    module.TRACE=bootstrap.TRACE
    module.exit_checked_derivation=proof
    if (module.SECONDS,module.MIN_AVAILABLE_KIB,module.MAX_GROUP_RSS_KIB)!=(1200,2097152,10485760):
        raise ExitCheckError('original supervisor limits changed')
    for name in ('supervised','heartbeat','stop_process','event','sample','wrap','interrupted'):
        if getattr(module,name).__globals__ is not module.__dict__:
            raise ExitCheckError('split supervisor globals: '+name)
    return module
