#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0
"""Bounded GDB supervision. OpenROAD attachment remains explicitly disabled."""
import hashlib,json,os,signal,subprocess,time
from pathlib import Path
from mainchip_userstack_identity import snapshot,module_inventory,file_sha,stat_record,check_frames,ProcessPin
ROOT=Path(__file__).resolve().parents[1]
READER=ROOT/'scripts/mainchip_userstack_gdb_reader.py'
NATIVE_ATTACHMENT_AUTHORIZED=False

def write(path,data):
    temp=path.with_suffix('.tmp')
    temp.write_text(json.dumps(data,indent=2,allow_nan=False)+'\n');temp.replace(path)

def members(group):
    found=[]
    for p in Path('/proc').iterdir():
        if not p.name.isdigit():continue
        try:x=stat_record((p/'stat').read_bytes())
        except(FileNotFoundError,ProcessLookupError,PermissionError):continue
        if x['pgrp']==group:found.append(x)
    return found

def clean_group(process):
    # Leader exit is not group completion. Never signal the observed target.
    evidence=[]
    for sig,seconds in ((signal.SIGTERM,2.),(signal.SIGKILL,2.)):
        live=[m for m in members(process.pid)if m['state']not in ('Z','X','x')]
        evidence.append(dict(signal=int(sig),members=live))
        if not live:break
        os.killpg(process.pid,sig)
        end=time.monotonic()+seconds
        while time.monotonic()<end:
            if not any(m['state']not in ('Z','X','x')for m in members(process.pid)):break
            time.sleep(.05)
    process.wait(timeout=2)
    left=members(process.pid)
    assert not any(m['state']not in ('Z','X','x')for m in left),'Live debugger descendants remain'
    return dict(attempts=evidence,zombies=[m for m in left if m['state']=='Z'],live_remaining=False)

def supervised(command,env,out,seconds,output_limit=32*1024**2):
    assert 0<output_limit<=32*1024**2
    out.mkdir(exist_ok=False)
    report=dict(command=command,deadline_s=seconds,status='RUNNING')
    process=None;failure=None
    try:
        with (out/'stdout.log').open('xb')as stdout,(out/'stderr.log').open('xb')as stderr:
            process=subprocess.Popen(command,env=env,stdout=stdout,stderr=stderr,start_new_session=True,cwd=env.get('NSSOC_STACK_FIXTURE_CWD'))
            report['debugger_pid']=process.pid;start=time.monotonic();write(out/'command.json',report)
            while process.poll()is None:
                if time.monotonic()-start>=seconds:failure='debugger_deadline';break
                if sum((out/n).stat().st_size for n in ('stdout.log','stderr.log'))>output_limit:
                    failure='debugger_output_limit';break
                time.sleep(.05)
            if failure is None and any(m['state']not in ('Z','X','x')for m in members(process.pid)):
                failure='live_debugger_descendant_after_leader'
            report['cleanup']=clean_group(process)
            report['returncode']=process.returncode
            report['elapsed_s']=time.monotonic()-start
        report['outputs']={n:dict(bytes=(out/n).stat().st_size,sha256=file_sha(out/n))for n in ('stdout.log','stderr.log')}
        if sum(v['bytes']for v in report['outputs'].values())>output_limit:failure='debugger_output_limit'
        report.update(status='REJECTED_SUPERVISION'if failure else 'COMPLETED_SUPERVISED_COMMAND',failure=failure)
    finally:
        if process is not None and (process.poll()is None or any(m['state']not in ('Z','X','x')for m in members(process.pid))):
            report['finally_cleanup']=clean_group(process)
        write(out/'command.json',report)
    return report


def emit_bounded_command_outputs(folder):
    """Print exact bounded stream slices before rejection; retain complete original files."""
    outputs={}
    for name in ('stdout.log','stderr.log'):
        path=folder/name
        if not path.exists():continue
        size=path.stat().st_size
        with path.open('rb')as f:
            if size<=8192:chunks=[(0,f.read())]
            else:
                head=f.read(4096);f.seek(size-4096);chunks=[(0,head),(size-4096,f.read(4096))]
        selected=[dict(offset=o,bytes=len(b),sha256=hashlib.sha256(b).hexdigest(),
                       text=b.decode('utf-8',errors='backslashreplace'))for o,b in chunks]
        report=dict(bytes=size,sha256=file_sha(path),selected=selected,
                    omitted_bytes=size-sum(len(b)for o,b in chunks),complete_raw_file_preserved=True)
        print('USERSTACK_COMMAND_STREAM '+json.dumps(dict(name=name,**report),ensure_ascii=True),flush=True)
        outputs[name]=report
    return dict(emitted=True,streams=outputs,per_stream_limit_bytes=8192)

def context(pid,expected,fixture,output,*,fault=None,canaries=False):
    assert NATIVE_ATTACHMENT_AUTHORIZED is False
    assert fixture['owned_pid']==pid and fixture['owner_pid']==os.getpid()
    assert expected['exe_sha256']==fixture['elf_sha256'] and expected['exe_path']==fixture['elf_path']
    assert expected['pid']==pid and fixture['purpose']=='HARMLESS_COUNTER_FIXTURE'
    assert Path(fixture['elf_path']).name=='counter'
    assert bytes.fromhex(expected['cmdline_hex'])==os.fsencode(fixture['elf_path'])+b'\x00'
    assert snapshot(pid,expected,tracer=0)['process']['ppid']==os.getpid()
    return dict(mode='OWNED_HARMLESS_FIXTURE',native_attachment_authorized=False,
        expected=expected,module_files=module_inventory(pid)['files'],output=str(output),
        fault=fault,permission_canaries=canaries)

def accepted_reader(reader):
    assert reader['status']=='ACQUIRED_BOUNDED_FIXTURE_STACKS'
    assert reader['detached']is True and reader['detach_attempted']is True
    check_frames(reader,reader['stopped_identity'])
    return True

def accepted_collection(samples):
    assert len(samples)==20
    assert [s['index']for s in samples]==list(range(20))
    assert all(s['status']=='PASS_BOUNDED_OWNED_FIXTURE_ATTACHMENT'for s in samples)
    return True

def _attach_once(pid,expected,fixture,gdb,out,*,fault=None,canaries=False,seconds=10):
    assert os.environ.get('GITHUB_ACTIONS')=='true'
    before=snapshot(pid,expected,tracer=0,require_running=True)
    out.mkdir(exist_ok=False);path=out/'context.json';target=out/'gdb-result.json'
    ctx=context(pid,expected,fixture,target,fault=fault,canaries=canaries);write(path,ctx)
    reader_sha=file_sha(READER)
    launch=out/'reader.gdb'
    launch.write_text('python\nimport sys\nsys.path.insert(0,'+repr(str(READER.parent))+')\nexec(compile(open('+repr(str(READER))+').read(),'+repr(str(READER))+',"exec"))\nend\n')
    env=dict(os.environ,DEBUGINFOD_URLS='',NSSOC_STACK_CONTEXT=str(path),HOME=fixture['fixture_home'],NSSOC_STACK_FIXTURE_CWD=fixture['fixture_cwd'])
    args=[gdb,'--nx','--nh','--quiet','--batch','-iex','set auto-load off',
          '-iex','set debuginfod enabled off','-x',str(launch)]
    result=dict(status='RUNNING',before=before,reader_sha256=reader_sha,scheduling_perturbed=True,
        target_memory_or_register_writes_permitted=False,native_attachment_authorized=False)
    try:
        command=supervised(args,env,out/'command',seconds);result['command']=command
        # Cleanup is required even when command timed out or its trusted reader rejected.
        after=snapshot(pid,expected,tracer=0,require_running=True);result['after']=after
        assert file_sha(READER)==reader_sha
        if target.exists():result['reader']=json.loads(target.read_text())
        assert command['status']=='COMPLETED_SUPERVISED_COMMAND' and command['returncode']==0,command
        reader=result['reader'];accepted_reader(reader)
        result['status']='PASS_BOUNDED_OWNED_FIXTURE_ATTACHMENT'
    except BaseException as e:
        result.update(status='REJECTED_OWNED_FIXTURE_ATTACHMENT',error=repr(e))
        try:result['failure_console']=emit_bounded_command_outputs(out/'command')
        except BaseException as console_error:result['failure_console_error']=repr(console_error)
        try:result['after_rejection']=snapshot(pid,expected,tracer=0,require_running=True)
        except BaseException as cleanup:
            result['cleanup_unproved']=repr(cleanup)
        raise
    finally:write(out/'result.json',result)
    return result

def _collect(pid,expected,fixture,gdb,out,interval=5.,count=20):
    assert count==20 and interval==5.,'Fixed acquisition contract'
    out.mkdir(exist_ok=False);start=time.monotonic();samples=[]
    try:
        for i in range(20):
            assert time.monotonic()-start<480
            sample=attach_once(pid,expected,fixture,gdb,out/('sample-'+str(i).zfill(2)),canaries=i==0)
            sample['index']=i;samples.append(sample)
            write(out/'progress.json',dict(completed=len(samples),expected=20,scheduling_perturbed=True))
            if i<19:time.sleep(interval)
        assert time.monotonic()-start<=480
        accepted_collection(samples)
        result=dict(status='PASS_20_HARMLESS_FIXTURE_STACK_ACQUISITIONS',samples=samples,
            scheduling_perturbed=True,new_native_route=False,native_attachment_authorized=False,
            normal_continuation_accepted=False,route_progress_proven=False)
        write(out/'result.json',result)
        return result
    except BaseException as e:
        write(out/'result.json',dict(status='REJECTED_FIXTURE_ACQUISITION',error=repr(e),samples=samples,
            native_attachment_authorized=False,normal_continuation_accepted=False,route_progress_proven=False))
        raise

def attach_once(pid,expected,fixture,gdb,out,*,fault=None,canaries=False,seconds=10):
    with ProcessPin(pid,expected)as pin:
        before=pin.verify()
        try:
            result=_attach_once(pid,expected,fixture,gdb,out,fault=fault,canaries=canaries,seconds=seconds)
            after=pin.verify()
            result['held_proc_and_pidfd']=dict(before=before['identity'],after=after['identity'],exit_not_observed=True)
            write(out/'result.json',result)
            return result
        except BaseException:
            if (out/'result.json').exists():
                result=json.loads((out/'result.json').read_text())
                result['status_before_final_binding_rejection']=result['status']
                result['status']='REJECTED_OWNED_FIXTURE_ATTACHMENT'
                try:
                    after=pin.verify()
                    result['held_pin_after_rejection']=dict(identity=after['identity'],exit_not_observed=True)
                except BaseException as e:result['held_pin_rejection']=repr(e)
                write(out/'result.json',result)
            raise

def collect(pid,expected,fixture,gdb,out,interval=5.,count=20):
    with ProcessPin(pid,expected)as pin:
        pin.verify()
        try:
            result=_collect(pid,expected,fixture,gdb,out,interval=interval,count=count)
            pin.verify()
            result['one_pidfd_held_for_full_collection']=True
            write(out/'result.json',result)
            return result
        except BaseException as e:
            if (out/'result.json').exists():
                result=json.loads((out/'result.json').read_text())
                result.update(status='REJECTED_FIXTURE_ACQUISITION',final_binding_error=repr(e))
                write(out/'result.json',result)
            raise
