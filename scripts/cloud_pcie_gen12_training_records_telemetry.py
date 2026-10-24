#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0
"""Hosted-only instrumentation of the unchanged complete record proof."""
import argparse, contextlib, hashlib, json, os, signal, subprocess, sys, threading, time, traceback
from pathlib import Path
import check_pcie_gen12_training_records as frozen
ROOT=Path(__file__).resolve().parents[1]
OUT=frozen.OUT
TRACE=ROOT/'hw/soc/out/cloud-pcie-gen12-training-records-telemetry'
METHOD=ROOT/'scripts/pcie-gen12-training-records-telemetry-methods.json'
ORIGINAL='e1bf844ef719b4ad4230aebc58550ee577da72d88958b7724400d1c4c14c8f5a'
SECONDS=1200
OUTPUT_LIMIT=16*1024*1024
PERIOD=15.0
LOCK=threading.RLock()
CURRENT={'phase':'not_started','child_pid':None}
STOP=threading.Event()
ACTIVE=None

class SupervisionFailure(RuntimeError):pass
class RunnerInterrupted(RuntimeError):pass

def host():
    assert os.environ.get('GITHUB_ACTIONS')=='true'
    assert os.environ.get('RUNNER_ENVIRONMENT')=='github-hosted'
    assert os.environ.get('GITHUB_REPOSITORY')=='Melihakbulut221/nssoc'

def sha(p):
    h=hashlib.sha256()
    with Path(p).open('rb') as f:
        for chunk in iter(lambda:f.read(1024*1024),b''):h.update(chunk)
    return h.hexdigest()

def pins():
    m=json.loads(METHOD.read_text())
    for p,h in m['protected'].items():assert sha(ROOT/p)==h,p
    assert sha(frozen.__file__)==ORIGINAL
    return m

def safe_read(p):
    try:return Path(p).read_text()
    except (OSError,UnicodeError):return None

def resources():
    # Numeric process/system counters only; never command lines or environments.
    rows=[]
    for p in Path('/proc').iterdir():
        if not p.name.isdecimal():continue
        status=safe_read(p/'status')
        if status is None:continue
        values={}
        for line in status.splitlines():
            k,_,v=line.partition(':')
            if k in ('Pid','PPid','VmRSS','VmHWM','VmSize','Threads'):values[k]=v.strip()
        if 'Pid' in values and 'PPid' in values:rows.append(values)
    selected={os.getpid()}
    while True:
        before=set(selected)
        selected.update(int(x['Pid']) for x in rows if int(x['PPid']) in selected)
        if before==selected:break
    process=[x for x in rows if int(x['Pid']) in selected]
    # File absence is explicit, not interpreted as a zero counter.
    counters={n:safe_read('/sys/fs/cgroup/'+n) for n in
              ('memory.current','memory.peak','memory.max','memory.events','cpu.stat','pids.current')}
    mem=safe_read('/proc/meminfo')
    mem={} if mem is None else {k:v.strip() for line in mem.splitlines()
                               for k,_,v in [line.partition(':')]
                               if k in ('MemAvailable','MemFree','SwapFree','SwapTotal')}
    disk=os.statvfs(TRACE)
    return {'processes':process,'cgroup':counters,'system_memory_kib':mem,
      'disk_available_bytes':disk.f_bavail*disk.f_frsize,
      'self_maxrss_kib_unit':'Linux proc VmRSS/VmHWM fields retain original kB units'}

def event(kind,**extra):
    with LOCK:
        item={'event':kind,'utc':time.strftime('%Y-%m-%dT%H:%M:%SZ',time.gmtime()),
              'monotonic_seconds':time.monotonic(),'state':dict(CURRENT),**extra}
        line=json.dumps(item,sort_keys=True)
        with (TRACE/'events.jsonl').open('a') as f:f.write(line+'\n');f.flush();os.fsync(f.fileno())
        temporary=TRACE/'latest.tmp'
        temporary.write_text(json.dumps(item,indent=2)+'\n')
        os.replace(temporary,TRACE/'latest.json')
        print('RECORD_PROGRESS '+line,flush=True)

def sample(kind='resource_sample'):
    try:event(kind,resources=resources())
    except (RunnerInterrupted,SupervisionFailure):raise
    except Exception as e:
        # Observational read failure does not substitute for a hardware verdict.
        event('resource_read_error',error=repr(e))

def heartbeat():
    while not STOP.wait(PERIOD):sample()

def stop_process(p):
    if p is None or p.poll() is not None:return
    try:os.killpg(p.pid,signal.SIGTERM)
    except ProcessLookupError:return
    try:p.wait(timeout=5)
    except subprocess.TimeoutExpired:
        try:os.killpg(p.pid,signal.SIGKILL)
        except ProcessLookupError:pass
        p.wait(timeout=5)

def supervised(args,label,passed=True,*,seconds=SECONDS,output_limit=OUTPUT_LIMIT,cwd=None):
    """Keep exact command/returncode/streams, fail closed on resource supervision."""
    global ACTIVE
    assert isinstance(label,str) and label and '/' not in label
    assert seconds>0 and output_limit>0
    cwd=OUT if cwd is None else Path(cwd)
    stdout=TRACE/(label+'.stdout');stderr=TRACE/(label+'.stderr')
    command=list(map(str,args))
    began=time.monotonic();reason=None;p=None
    with LOCK:CURRENT.update(phase='command:'+label,child_pid=None)
    event('command_start',label=label,argv=command,timeout_seconds=seconds,output_limit_per_stream_bytes=output_limit)
    try:
        with stdout.open('wb') as so,stderr.open('wb') as se:
            p=subprocess.Popen(command,cwd=cwd,stdout=so,stderr=se,start_new_session=True)
            ACTIVE=p
            with LOCK:CURRENT['child_pid']=p.pid
            sample('command_process_started')
            while p.poll() is None:
                if time.monotonic()-began>=seconds:reason='elapsed_limit';break
                if max(stdout.stat().st_size,stderr.stat().st_size)>output_limit:reason='output_limit';break
                time.sleep(.1)
            if reason:stop_process(p)
            p.wait()
            so.flush();se.flush();os.fsync(so.fileno());os.fsync(se.fileno())
        sizes=(stdout.stat().st_size,stderr.stat().st_size)
        if max(sizes)>output_limit:reason='output_limit'
        record={'label':label,'argv':command,'pid':p.pid,'returncode':p.returncode,
          'elapsed_seconds':time.monotonic()-began,'supervision_failure':reason,
          'stdout_bytes':sizes[0],'stderr_bytes':sizes[1],
          'stdout_sha256':sha(stdout),'stderr_sha256':sha(stderr)}
        (TRACE/(label+'.command.json')).write_text(json.dumps(record,indent=2)+'\n')
        event('command_end',**record)
        if reason:raise SupervisionFailure(json.dumps(record,sort_keys=True))
        # The original caller inspects both exact streams, including mutation FATAL.
        out=stdout.read_text();err=stderr.read_text()
        (cwd/(label+'.log')).write_text(out+err)
        result=subprocess.CompletedProcess(command,p.returncode,out,err)
        if passed:assert result.returncode==0,(label,out[-3000:],err[-3000:])
        return result
    finally:
        stop_process(p);ACTIVE=None
        with LOCK:CURRENT['child_pid']=None

def wrap(name,fn,seconds=SECONDS):
    def call(*args,**kwargs):
        with LOCK:CURRENT.update(phase=name,child_pid=None)
        event('phase_start',phase_name=name)
        began=time.monotonic()
        previous_handler=signal.signal(signal.SIGALRM,phase_timeout)
        previous_timer=signal.setitimer(signal.ITIMER_REAL,seconds)
        assert previous_timer==(0.0,0.0),'Unexpected nested phase watchdog'
        try:
            result=fn(*args,**kwargs)
            extra={}
            if name=='vectors':
                extra={'vector_sha256':sha(result[0]),'vector_bytes':result[0].stat().st_size,
                       'coverage':result[1]}
            event('phase_end',phase_name=name,elapsed_seconds=time.monotonic()-began,**extra)
            return result
        except BaseException as e:
            event('phase_error',phase_name=name,elapsed_seconds=time.monotonic()-began,error=repr(e))
            raise
        finally:
            signal.setitimer(signal.ITIMER_REAL,0)
            signal.signal(signal.SIGALRM,previous_handler)
    return call

def phase_timeout(signum,frame):
    raise SupervisionFailure('Phase elapsed limit; no engineering acceptance: '+str(CURRENT['phase']))

def interrupted(signum,frame):
    raise RunnerInterrupted('Received signal '+str(signum)+'; no engineering acceptance')

def controls():
    host();m=pins();TRACE.mkdir(parents=True,exist_ok=False)
    results={}
    try:
        # These are subprocess supervision fixtures, not project RTL simulation.
        r=supervised([sys.executable,'-c','import sys;print("positive");print("stderr",file=sys.stderr)'],
                     'fixture-positive',cwd=TRACE)
        assert r.stdout=='positive\n'and r.stderr=='stderr\n'
        results['positive_exact_streams']=True
        r=supervised([sys.executable,'-c','import sys;print("FATAL fixture");sys.exit(7)'],
                     'fixture-negative',False,cwd=TRACE)
        assert r.returncode==7 and r.stdout=='FATAL fixture\n'
        results['negative_exact_returncode']=True
        for name,args,kw,reason in (
          ('timeout',[sys.executable,'-c','import time;time.sleep(60)'],{'seconds':.2},'elapsed_limit'),
          ('oversize',[sys.executable,'-c','print("x"*8192)'],{'output_limit':1024},'output_limit')):
            try:supervised(args,'fixture-'+name,False,cwd=TRACE,**kw)
            except SupervisionFailure:
                d=json.loads((TRACE/('fixture-'+name+'.command.json')).read_text())
                assert d['supervision_failure']==reason
                assert ACTIVE is None
                results[name+'_fails_before_mutant_acceptance']=True
            else:raise AssertionError('Supervision failure accepted as mutation '+name)
        # A normal nonzero tool must still reject at the original passed=True gate.
        try:supervised([sys.executable,'-c','raise SystemExit(9)'],'fixture-bad-positive',cwd=TRACE)
        except AssertionError:results['positive_nonzero_rejected']=True
        else:raise AssertionError('Nonzero positive accepted')
        try:wrap('fixture-phase-timeout',lambda:time.sleep(60),seconds=.2)()
        except SupervisionFailure:results['python_phase_watchdog_fails_closed']=True
        else:raise AssertionError('Unbounded Python phase')
        pins()
        result={'status':'PASS_RECORD_TELEMETRY_SOURCE_AND_SUPERVISION_CONTROLS_NO_RTL',
          'controls':results,'source_pins':m,'engineering_accepted':False}
        assert len(results)==6
        (TRACE/'controls.json').write_text(json.dumps(result,indent=2)+'\n')
        print(json.dumps(result),flush=True)
    finally:stop_process(ACTIVE)

def main():
    host();m=pins();TRACE.mkdir(parents=True,exist_ok=False);assert not OUT.exists()
    old={name:getattr(frozen,name)for name in ('command','prerequisites','vectors','testbench')}
    old_signals={s:signal.signal(s,interrupted)for s in (signal.SIGTERM,signal.SIGINT)}
    frozen.command=supervised
    for name in ('prerequisites','vectors','testbench'):setattr(frozen,name,wrap(name,old[name]))
    worker=threading.Thread(target=heartbeat,daemon=True);worker.start()
    result={'status':'RUNNING','run':os.environ['GITHUB_RUN_ID'],'source':os.environ['GITHUB_SHA'],
            'original_checker_sha256':ORIGINAL,'original_gate_and_RTL_changed':False,
            'engineering_accepted':False,'source_pins':m}
    try:
        event('start',source=result['source'],run=result['run']);sample()
        frozen.main()
        native=json.loads((OUT/'result.json').read_text())
        assert native['status']=='PASS_COMPOSED_CANDIDATE16_TRANSPORT_AND24_COMPILED_FAULTS'
        assert len(native['negative_controls'])==24 and all(x['returncode']!=0 for x in native['negative_controls'])
        assert native['icarus']['returncode']==0 and native['verilator']=='PASS'and native['synthesis']['status']=='PASS'
        pins()
        result.update(status='PASS_INSTRUMENTED_UNCHANGED_COMPLETE_RECORD_PROOF',
                      original_result_sha256=sha(OUT/'result.json'),engineering_accepted=True)
    except BaseException as e:
        result.update(status='FAIL_OR_INTERRUPTED',error=repr(e),traceback=traceback.format_exc())
        raise
    finally:
        stop_process(ACTIVE);STOP.set();worker.join(timeout=2)
        for name,fn in old.items():setattr(frozen,name,fn)
        for s,fn in old_signals.items():signal.signal(s,fn)
        sample('final_resource_sample')
        result['original_result_present']=(OUT/'result.json').exists()
        if result['original_result_present']:result['original_result_sha256']=sha(OUT/'result.json')
        (TRACE/'result.json').write_text(json.dumps(result,indent=2)+'\n')
        event('terminal',status=result['status'],engineering_accepted=result['engineering_accepted'])

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--controls',action='store_true');args=p.parse_args()
    if args.controls:controls()
    else:main()
