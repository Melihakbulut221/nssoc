#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0
"""Hosted-only unchanged static32 proof with exact optional-SHARE flow repair."""
import argparse, base64, contextlib, hashlib, json, os, signal, subprocess, sys, threading, time, traceback
from pathlib import Path
import check_pcie_gen12_training_records_static as frozen

import pcie_record_static_equivalence_prerequisite as static_eq
ROOT=Path(__file__).resolve().parents[1]
OUT=frozen.OUT
TRACE=ROOT/'hw/soc/out/cloud-pcie-gen12-training-records-noshare-telemetry'
METHOD=ROOT/'scripts/pcie-gen12-training-records-noshare-methods.json'
ORIGINAL='148c8ec7431a0ba034cc8fa71e2a1603802ab192581fd10b8750df93a8267de0'
SECONDS=1200
OUTPUT_LIMIT=16*1024*1024
PERIOD=15.0
MEMORY_PERIOD=.5
MIN_AVAILABLE_KIB=2*1024*1024
MAX_GROUP_RSS_KIB=10*1024*1024
STREAM_PERIOD=5.0
STREAM_TAIL_BYTES=4096
CONSOLE_BROKEN=False
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

def console_line(line,stream=None):
    global CONSOLE_BROKEN
    if CONSOLE_BROKEN:return
    try:
        if stream is None:stream=sys.stdout
        print(line,file=stream,flush=True)
    except BrokenPipeError:
        # Persisted evidence must survive a closed runner console. The command
        # supervisor rejects and terminates its group; a broken pipe is no PASS.
        CONSOLE_BROKEN=True

def event(kind,**extra):
    with LOCK:
        item={'event':kind,'utc':time.strftime('%Y-%m-%dT%H:%M:%SZ',time.gmtime()),
              'monotonic_seconds':time.monotonic(),'state':dict(CURRENT),**extra}
        line=json.dumps(item,sort_keys=True)
        with (TRACE/'events.jsonl').open('a') as f:f.write(line+'\n');f.flush();os.fsync(f.fileno())
        temporary=TRACE/'latest.tmp'
        temporary.write_text(json.dumps(item,indent=2)+'\n')
        os.replace(temporary,TRACE/'latest.json')
        console_line('RECORD_PROGRESS '+line)

def sample(kind='resource_sample'):
    try:event(kind,resources=resources())
    except (RunnerInterrupted,SupervisionFailure):raise
    except Exception as e:
        # Observational read failure does not substitute for a hardware verdict.
        event('resource_read_error',error=repr(e))

def heartbeat():
    while not STOP.wait(PERIOD):sample()

def group_members(pgid):
    # Linux stat fields follow the parenthesized comm; do not expose comm/argv.
    result=[]
    for path in Path('/proc').iterdir():
        if not path.name.isdecimal():continue
        value=safe_read(path/'stat')
        if value is None:continue
        fields=value.rsplit(') ',1)[-1].split()
        if len(fields)>2 and int(fields[2])==pgid:
            result.append({'pid':int(path.name),'state':fields[0]})
    return result

def live_members(pgid):
    return [x for x in group_members(pgid)if x['state']not in ('Z','X')]

def stop_process(p):
    if p is None:return {'signals':[],'remaining_live':[],'remaining_nonrunning':[]}
    signals=[]
    # The leader may already be reaped while a child still owns these streams.
    p.poll()
    for sig,grace in ((signal.SIGTERM,5.0),(signal.SIGKILL,5.0)):
        if not live_members(p.pid):break
        try:os.killpg(p.pid,sig);signals.append(signal.Signals(sig).name)
        except ProcessLookupError:break
        deadline=time.monotonic()+grace
        while time.monotonic()<deadline and live_members(p.pid):
            p.poll();time.sleep(.05)
    p.poll()
    remaining=live_members(p.pid)
    report={'signals':signals,'remaining_live':remaining,
            'remaining_nonrunning':[x for x in group_members(p.pid)if x['state']in ('Z','X')]}
    if remaining:raise SupervisionFailure('Process group remains live: '+json.dumps(report))
    # Defunct descendants cannot execute or write; expose them instead of
    # claiming that another parent or PID1 has already reaped them.
    if p.returncode is None:p.wait(timeout=5)
    return report

def memory_snapshot(pgid,meminfo_path='/proc/meminfo'):
    """Fail closed on unreadable required counters, never infer absent as zero."""
    text=Path(meminfo_path).read_text()
    rows=[line.split()for line in text.splitlines()if line.startswith('MemAvailable:')]
    if len(rows)!=1 or len(rows[0])!=3 or rows[0][2]!='kB':
        raise SupervisionFailure('Unavailable MemAvailable in kB')
    available=int(rows[0][1])
    if available<0:raise SupervisionFailure('Negative MemAvailable')
    members=[]
    for member in live_members(pgid):
        path=Path('/proc')/str(member['pid'])/'status'
        try:text=path.read_text()
        except FileNotFoundError:
            if not any(x['pid']==member['pid']for x in live_members(pgid)):continue
            raise
        fields=[line.split()for line in text.splitlines()if line.startswith('VmRSS:')]
        if len(fields)!=1 or len(fields[0])!=3 or fields[0][2]!='kB':
            if not any(x['pid']==member['pid']for x in live_members(pgid)):continue
            raise SupervisionFailure('Unavailable live process VmRSS')
        rss=int(fields[0][1])
        if rss<0:raise SupervisionFailure('Negative VmRSS')
        members.append({'pid':member['pid'],'rss_kib':rss})
    return {'available_kib':available,'group_rss_kib':sum(x['rss_kib']for x in members),
            'members':members,'group_rss_may_double_count_shared_pages':True}

def stream_tails(label,paths,positions):
    # Forward bounded exact tails during execution; full streams remain in files.
    # Skipped old ranges are explicit and never represented as logged in full.
    for stream,path in paths.items():
        size=path.stat().st_size;previous=positions[stream]
        if size<=previous:continue
        start=max(previous,size-STREAM_TAIL_BYTES)
        with path.open('rb')as f:f.seek(start);chunk=f.read(size-start)
        if len(chunk)!=size-start:raise SupervisionFailure('Raw stream changed while reading')
        event('raw_stream_tail',label=label,stream=stream,offset=start,bytes=len(chunk),
              previous_forwarded_end=previous,skipped_bytes=start-previous,
              sha256=hashlib.sha256(chunk).hexdigest(),base64=base64.b64encode(chunk).decode())
        positions[stream]=size

def supervised(args,label,passed=True,*,seconds=SECONDS,output_limit=OUTPUT_LIMIT,cwd=None,
               min_available_kib=MIN_AVAILABLE_KIB,max_group_rss_kib=MAX_GROUP_RSS_KIB,
               meminfo_path='/proc/meminfo'):
    """Keep exact command/returncode/streams, fail closed on resource supervision."""
    global ACTIVE
    assert isinstance(label,str) and label and '/' not in label
    assert seconds>0 and output_limit>0 and min_available_kib>0 and max_group_rss_kib>0
    cwd=OUT if cwd is None else Path(cwd)
    stdout=TRACE/(label+'.stdout');stderr=TRACE/(label+'.stderr')
    command=list(map(str,args))
    began=time.monotonic();reason=None;p=None;memory=None;memory_error=None
    next_memory=0.0;next_stream=0.0;positions={'stdout':0,'stderr':0}
    paths={'stdout':stdout,'stderr':stderr}
    with LOCK:CURRENT.update(phase='command:'+label,child_pid=None)
    event('command_start',label=label,argv=command,timeout_seconds=seconds,output_limit_per_stream_bytes=output_limit,
          minimum_available_kib=min_available_kib,maximum_group_rss_kib=max_group_rss_kib,
          memory_period_seconds=MEMORY_PERIOD,stream_tail_bytes=STREAM_TAIL_BYTES)
    try:
        with stdout.open('wb') as so,stderr.open('wb') as se:
            p=subprocess.Popen(command,cwd=cwd,stdout=so,stderr=se,start_new_session=True)
            ACTIVE=p
            with LOCK:CURRENT['child_pid']=p.pid
            sample('command_process_started')
            while p.poll() is None:
                now=time.monotonic()
                if CONSOLE_BROKEN:reason='console_pipe_broken';break
                if now>=next_memory:
                    try:
                        memory=memory_snapshot(p.pid,meminfo_path)
                        if memory['available_kib']<min_available_kib:reason='minimum_available_memory'
                        elif memory['group_rss_kib']>max_group_rss_kib:reason='maximum_group_rss'
                    except Exception as e:reason='memory_sample_unavailable';memory_error=repr(e)
                    next_memory=now+MEMORY_PERIOD
                    if reason:
                        event('memory_sentinel_rejection',label=label,reason=reason,
                              memory=memory,memory_error=memory_error)
                        break
                if now>=next_stream:
                    stream_tails(label,paths,positions);next_stream=now+STREAM_PERIOD
                if now-began>=seconds:reason='elapsed_limit';break
                if max(stdout.stat().st_size,stderr.stat().st_size)>output_limit:reason='output_limit';break
                time.sleep(.1)
            if not reason and live_members(p.pid):reason='orphan_descendant_after_leader_exit'
            cleanup=stop_process(p)
            p.wait()
            so.flush();se.flush();os.fsync(so.fileno());os.fsync(se.fileno())
        stream_tails(label,paths,positions)
        if CONSOLE_BROKEN:reason='console_pipe_broken'
        sizes=(stdout.stat().st_size,stderr.stat().st_size)
        if max(sizes)>output_limit:reason='output_limit'
        record={'label':label,'argv':command,'pid':p.pid,'returncode':p.returncode,
          'elapsed_seconds':time.monotonic()-began,'supervision_failure':reason,
          'last_memory_sentinel_sample':memory,'memory_read_error':memory_error,
          'minimum_available_kib':min_available_kib,'maximum_group_rss_kib':max_group_rss_kib,
          'stdout_bytes':sizes[0],'stderr_bytes':sizes[1],
          'stdout_sha256':sha(stdout),'stderr_sha256':sha(stderr),'process_group_cleanup':cleanup}
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
    global CONSOLE_BROKEN
    host();m=pins();TRACE.mkdir(parents=True,exist_ok=False)
    results={}
    try:
        # These are subprocess supervision fixtures, not project RTL simulation.
        r=supervised([sys.executable,'-c','import sys;print("positive");print("stderr",file=sys.stderr)'],
                     'fixture-positive',cwd=TRACE)
        assert r.stdout=='positive\n'and r.stderr=='stderr\n'
        results['positive_exact_streams']=True
        tails=[json.loads(x)for x in (TRACE/'events.jsonl').read_text().splitlines()
               if json.loads(x).get('event')=='raw_stream_tail'and json.loads(x).get('label')=='fixture-positive']
        assert len(tails)==2 and {x['stream']for x in tails}=={'stdout','stderr'}
        for item in tails:
            expected=('positive\n'if item['stream']=='stdout'else'stderr\n').encode()
            assert base64.b64decode(item['base64'])==expected and item['offset']==0 and item['skipped_bytes']==0
            assert item['sha256']==hashlib.sha256(expected).hexdigest()
        results['exact_bounded_stream_chunks_forwarded']=True
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
        # Low fixture limits avoid intentionally stressing the runner.
        for name,code,kw,reason in (
          ('rss','import time;block=bytearray(32*1024*1024);print("allocated-32MiB",flush=True);time.sleep(60)',
             {'max_group_rss_kib':16*1024},'maximum_group_rss'),
          ('available','import time;time.sleep(60)',{'min_available_kib':1<<60},'minimum_available_memory'),
          ('memory-unreadable','import time;time.sleep(60)',
             {'meminfo_path':str(TRACE/'deliberately-absent-meminfo')},'memory_sample_unavailable')):
            try:supervised([sys.executable,'-c',code],'fixture-'+name,False,cwd=TRACE,**kw)
            except SupervisionFailure:
                q=json.loads((TRACE/('fixture-'+name+'.command.json')).read_text())
                assert q['supervision_failure']==reason and q['process_group_cleanup']['remaining_live']==[]
                assert ACTIVE is None
                results[name+'_fails_before_mutant_acceptance']=True
            else:raise AssertionError('Memory sentinel accepted as mutation '+name)
        class ClosedConsole:
            def write(self,text):raise BrokenPipeError('deliberately closed fixture console')
            def flush(self):pass
        console_line('fixture closed pipe',ClosedConsole())
        assert CONSOLE_BROKEN is True
        try:
            try:supervised([sys.executable,'-c','import time;time.sleep(60)'],'fixture-console',False,cwd=TRACE)
            except SupervisionFailure:
                q=json.loads((TRACE/'fixture-console.command.json').read_text())
                assert q['supervision_failure']=='console_pipe_broken'and q['process_group_cleanup']['remaining_live']==[]
                results['closed_console_persisted_and_rejected']=True
            else:raise AssertionError('Closed console accepted')
        finally:CONSOLE_BROKEN=False
        # A normal nonzero tool must still reject at the original passed=True gate.
        try:supervised([sys.executable,'-c','raise SystemExit(9)'],'fixture-bad-positive',cwd=TRACE)
        except AssertionError:results['positive_nonzero_rejected']=True
        else:raise AssertionError('Nonzero positive accepted')
        child='import time;print("descendant-writer",flush=True);time.sleep(60)'
        leader='import subprocess,sys,time;subprocess.Popen([sys.executable,"-c",'+repr(child)+']);time.sleep(.2)'
        try:supervised([sys.executable,'-c',leader],'fixture-orphan',False,cwd=TRACE)
        except SupervisionFailure:
            q=json.loads((TRACE/'fixture-orphan.command.json').read_text())
            assert q['supervision_failure']=='orphan_descendant_after_leader_exit'
            assert q['process_group_cleanup']['remaining_live']==[]
            assert 'descendant-writer' in (TRACE/'fixture-orphan.stdout').read_text()
            results['exited_leader_descendant_rejected_and_stopped']=True
        else:raise AssertionError('Live descendant accepted')
        child='import signal,time;signal.signal(signal.SIGTERM,signal.SIG_IGN);print("TERM-ignored",flush=True);time.sleep(60)'
        try:supervised([sys.executable,'-c',child],'fixture-resistant',False,cwd=TRACE,seconds=.5)
        except SupervisionFailure:
            q=json.loads((TRACE/'fixture-resistant.command.json').read_text())
            assert q['supervision_failure']=='elapsed_limit'
            assert q['process_group_cleanup']['signals']==['SIGTERM','SIGKILL']
            assert q['process_group_cleanup']['remaining_live']==[]
            results['term_resistant_group_killed_and_rejected']=True
        else:raise AssertionError('Resistant child accepted')
        try:wrap('fixture-phase-timeout',lambda:time.sleep(60),seconds=.2)()
        except SupervisionFailure:results['python_phase_watchdog_fails_closed']=True
        else:raise AssertionError('Unbounded Python phase')
        pins()
        result={'status':'PASS_RECORD_TELEMETRY_SOURCE_AND_SUPERVISION_CONTROLS_NO_RTL',
          'controls':results,'source_pins':m,'engineering_accepted':False}
        assert len(results)==13
        (TRACE/'controls.json').write_text(json.dumps(result,indent=2)+'\n')
        print(json.dumps(result),flush=True)
    finally:stop_process(ACTIVE)

FLOW={}
UPSTREAM=ROOT/'docs/evidence/pcie-gen12-record-yosys033-share-source-20261025.json'
def original_synthesis_command():
    paths=[ROOT/p for p in frozen.FILES]
    return ['yosys','-p','read_verilog '+' '.join(map(str,paths))+
      '; synth -top soc_pcie_gen12_training_records; check -assert; write_json '+str(OUT/'synthesis.json')]

def rewrite_synthesis_command(args,passed=True):
    original=original_synthesis_command()
    assert passed is True and list(map(str,args))==original
    before='; synth -top soc_pcie_gen12_training_records; check -assert;'
    after='; synth -noshare -top soc_pcie_gen12_training_records; check -assert;'
    assert original[2].count(before)==1
    suffix='; write_verilog -noattr '+str(OUT/'mapped.v')
    changed=[original[0],original[1],original[2].replace(before,after)+suffix]
    assert changed[2].count(' -noshare ')==1
    assert changed[2][:-len(suffix)].replace(after,before)==original[2]
    return changed

def check_mapped_fault(p):
    assert p.returncode>0 and 'FATAL' in p.stdout+p.stderr
    return True

def mapped_fault(mapped,label,force):
    source=(OUT/'tb.v').read_text()
    assert source.count('initial begin\n')==1
    fault=OUT/(label+'-tb.v')
    fault.write_text(source.replace('initial begin\n','initial begin\n'+force+'\n',1))
    exe=OUT/(label+'.vvp')
    supervised(['iverilog','-g2012','-s','tb','-o',exe,mapped,fault],label+'-compile')
    p=supervised(['vvp',exe],label,False)
    check_mapped_fault(p)
    return {'label':label,'returncode':p.returncode,'netlist_sha256':sha(mapped),
            'fault_testbench_sha256':sha(fault),'log_sha256':sha(OUT/(label+'.log'))}

def flow_command(args,label,passed=True,**kwargs):
    if label!='synthesis':return supervised(args,label,passed,**kwargs)
    assert not FLOW,'Synthesis may execute exactly once'
    changed=rewrite_synthesis_command(args,passed)
    version=supervised(['yosys','-V'],'synthesis-tool-version')
    assert version.stdout.strip()=='Yosys 0.33 (git sha1 2584903a060)',version.stdout
    FLOW.update(status='RUNNING',original_argv=list(map(str,args)),executed_argv=changed,
                yosys_version=version.stdout.strip(),RTL_changed=False,
                full_synth_check_preserved=True,SAT_resource_sharing_disabled=True,
                original24_mutations_required=True)
    p=supervised(changed,label,passed,**kwargs)
    mapped=OUT/'mapped.v';assert mapped.is_file()and mapped.stat().st_size>0
    FLOW['mapped_netlist_sha256']=sha(mapped)
    FLOW['post_synthesis_icarus']=frozen.simulate([mapped],'post-synthesis',True)
    FLOW['mapped_negative_controls']=[
       mapped_fault(mapped,'mapped-force-TX-valid-zero',"force dut.tx_raw_valid_o=1'b0;"),
       mapped_fault(mapped,'mapped-force-RX-code-error-zero',"force dut.rx_record_code_error_o=16'h0000;")]
    assert len(FLOW['mapped_negative_controls'])==2
    FLOW['status']='PASS_NOSHARE_MAPPED_NETLIST_SAME_ORACLE_AND2_FAULTS'
    return p

def flow_controls():
    host();m=pins();original=original_synthesis_command();changed=rewrite_synthesis_command(original)
    assert ' -noshare 'in changed[2]and '; check -assert;'in changed[2]
    faults={}
    variants={
      'missing_tool':[],
      'wrong_tool':['false']+original[1:],
      'extra_argument':original+['--help'],
      'wrong_mode':[original[0],'-Q',original[2]],
      'remove_check':[original[0],original[1],original[2].replace('; check -assert;',';')],
      'disable_abc':[original[0],original[1],original[2].replace('synth -top','synth -noabc -top')],
      'disable_fsm':[original[0],original[1],original[2].replace('synth -top','synth -nofsm -top')],
      'partial_synthesis':[original[0],original[1],original[2].replace('synth -top','synth -run coarse -top')],
      'wrong_top':[original[0],original[1],original[2].replace(' -top soc_pcie_gen12_training_records',' -top soc_pcie_gen12_raw32_rx')],
      'missing_DUT_source':[original[0],original[1],original[2].replace(str(ROOT/frozen.FILES[-1]),'')],
      'already_disabled_share':[original[0],original[1],original[2].replace('synth -top','synth -noshare -top')],
      'wrong_output':[original[0],original[1],original[2].replace('synthesis.json','other.json')],
      'appended_pass':[original[0],original[1],original[2]+'; delete'],
      'mapped_output_in_input':[original[0],original[1],changed[2]]}
    for name,args in variants.items():
        try:rewrite_synthesis_command(args)
        except AssertionError:faults[name]=True
        else:raise AssertionError('Unreviewed synthesis command accepted '+name)
    try:rewrite_synthesis_command(original,False)
    except AssertionError:faults['negative_synthesis_never_accepted']=True
    else:raise AssertionError('Synthesis cannot be a negative control')
    assert check_mapped_fault(subprocess.CompletedProcess([],1,'FATAL: fixture',''))
    for name,p in (
      ('mapped_zero_exit',subprocess.CompletedProcess([],0,'FATAL: fixture','')),
      ('mapped_signal_exit',subprocess.CompletedProcess([],-15,'FATAL: fixture','')),
      ('mapped_missing_FATAL',subprocess.CompletedProcess([],1,'','different error'))):
        try:check_mapped_fault(p)
        except AssertionError:faults[name]=True
        else:raise AssertionError('Invalid mapped rejection accepted '+name)
    upstream=json.loads(UPSTREAM.read_text());verified={}
    assert upstream['commit']=='2584903a0605cc7ffdfc1996254ccc1f548403f2'
    for path,h in upstream['source_sha256'].items():
        data=json.loads(subprocess.check_output(['gh','api','repos/YosysHQ/yosys/contents/'+path+'?ref='+upstream['commit']],timeout=30))
        b=base64.b64decode(data['content']);assert hashlib.sha256(b).hexdigest()==h
        verified[path]=h
    assert len(faults)==18 and all(faults.values())and pins()==m
    result={'status':'PASS_EXACT_NOSHARE_ADAPTER_AND18_FAULTS_NO_RTL',
      'negative_controls':faults,'original_argv':original,'executed_argv':changed,
      'primary_sources_verified':verified,'native_DUT_executed':False}
    TRACE.mkdir(parents=True,exist_ok=True)
    (TRACE/'flow-controls.json').write_text(json.dumps(result,indent=2)+'\n')
    print(json.dumps(result,indent=2),flush=True)

def main():
    host();m=pins();TRACE.mkdir(parents=True,exist_ok=False);assert not OUT.exists()
    old={name:getattr(frozen,name)for name in ('command','prerequisites','vectors','testbench')}
    old_signals={s:signal.signal(s,interrupted)for s in (signal.SIGTERM,signal.SIGINT)}
    frozen.command=flow_command
    def prerequisites_with_equivalence():
        proof=static_eq.require()
        event('actual_static32_equivalence_prerequisite',proof=proof)
        return old['prerequisites']()
    frozen.prerequisites=wrap('prerequisites',prerequisites_with_equivalence)
    for name in ('vectors','testbench'):setattr(frozen,name,wrap(name,old[name]))
    worker=threading.Thread(target=heartbeat,daemon=True);worker.start()
    result={'status':'RUNNING','run':os.environ['GITHUB_RUN_ID'],'source':os.environ['GITHUB_SHA'],
            'executed_checker_sha256':ORIGINAL,'behavioral_oracle_and_acceptance_gates_changed':False,
            'candidate_static_RTL_rewrite':True,
            'engineering_accepted':False,'source_pins':m,'synthesis_flow':FLOW}
    try:
        event('start',source=result['source'],run=result['run']);sample()
        frozen.main()
        native=json.loads((OUT/'result.json').read_text())
        assert native['status']=='PASS_COMPOSED_CANDIDATE16_TRANSPORT_AND24_COMPILED_FAULTS'
        assert len(native['negative_controls'])==24 and all(x['returncode']!=0 for x in native['negative_controls'])
        assert native['icarus']['returncode']==0 and native['verilator']=='PASS'and native['synthesis']['status']=='PASS'
        assert FLOW['status']=='PASS_NOSHARE_MAPPED_NETLIST_SAME_ORACLE_AND2_FAULTS'
        assert FLOW['post_synthesis_icarus']['returncode']==0
        assert len(FLOW['mapped_negative_controls'])==2 and all(x['returncode']>0 for x in FLOW['mapped_negative_controls'])
        pins()
        result.update(status='PASS_INSTRUMENTED_STATIC32_NOSHARE_POSTMAP_COMPLETE_RECORD_PROOF',
                      candidate_result_sha256=sha(OUT/'result.json'),engineering_accepted=True)
    except BaseException as e:
        result.update(status='FAIL_OR_INTERRUPTED',error=repr(e),traceback=traceback.format_exc())
        raise
    finally:
        stop_process(ACTIVE);STOP.set();worker.join(timeout=2)
        for name,fn in old.items():setattr(frozen,name,fn)
        for s,fn in old_signals.items():signal.signal(s,fn)
        sample('final_resource_sample')
        result['candidate_result_present']=(OUT/'result.json').exists()
        if result['candidate_result_present']:result['candidate_result_sha256']=sha(OUT/'result.json')
        (TRACE/'result.json').write_text(json.dumps(result,indent=2)+'\n')
        event('terminal',status=result['status'],engineering_accepted=result['engineering_accepted'])

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--controls',action='store_true');p.add_argument('--flow-controls',action='store_true');args=p.parse_args()
    if args.controls:controls()
    elif args.flow_controls:flow_controls()
    else:main()
