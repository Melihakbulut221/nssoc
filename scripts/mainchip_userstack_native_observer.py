#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0
"""20 bounded read-only attachments to the exact saved process; scheduling is perturbed."""
import argparse,hashlib,json,os,signal,subprocess,sys,time,traceback
from pathlib import Path
from mainchip_userstack_identity import ProcessPin,file_sha,check_frames,snapshot
from mainchip_userstack_observer import supervised,write,emit_bounded_command_outputs
from mainchip_userstack_native_binding import inventory,verify_live,mapped_runtime,runtime_closure,MODE
ROOT=Path(__file__).resolve().parents[1]
READER=ROOT/'scripts/mainchip_userstack_native_reader.py'
GDB_SHA='3832cc070ae1716e322105d3b39fb398695e5f031c9d39224cf227a8c2b889f6'
FLAGS=dict(scheduling_perturbed=True,target_memory_or_register_writes_permitted=False,
    route_progress_proven=False,normal_continuation_accepted=False,routing_complete=False)
def stopped(signum,frame):raise RuntimeError('Outer observer requested bounded cleanup: '+str(signum))
def method_gate():
    m=json.loads((ROOT/'scripts/mainchip-userstack-native-methods.json').read_text())
    for p,h in m['protected'].items():assert file_sha(ROOT/p)==h,p
    assert m['native_process_restore_authorized']is True and m['native_attachment_authorized']is True
    assert m['sample_count']==20 and m['interval_s']==5 and m['observer_envelope_s']==500 and m['route_segment_s']==600
    return m
def accepted_reader(r):
    assert r['status']=='ACQUIRED_BOUNDED_NATIVE_STACKS'and r['detached']is True and r['detach_attempted']is True
    assert all(v is False for v in r['permissions'].values())and all(v is False for v in r['auto_load'].values())
    check_frames(r,r['stopped_identity']);return True
def attach(expect,inv,inv_path,gdb,out,deadline):
    pid=expect['pid'];expected=expect['identity'];out.mkdir(exist_ok=False)
    report=dict(status='RUNNING',index=None,**FLAGS)
    with ProcessPin(pid,expected)as pin:
        try:
            pin.verify();report['before']=verify_live(expect,inv)
            modules=mapped_runtime(pid,expected,inv)
            ctx=dict(mode=MODE,native_attachment_authorized=True,expected=expected,container=expect,
                module_files=modules['files'],inventory_path=str(inv_path),output=str(out/'reader-result.json'),
                fault=None,permission_canaries=False)
            write(out/'context.json',ctx)
            launch=out/'reader.gdb'
            launch.write_text('python\nimport sys\nsys.path.insert(0,'+repr(str(READER.parent))+')\nexec(compile(open('+repr(str(READER))+').read(),'+repr(str(READER))+',"exec"))\nend\n')
            env={k:v for k,v in os.environ.items()if k not in ('GH_TOKEN','GITHUB_TOKEN','LD_PRELOAD','PYTHONPATH','PYTHONHOME')}
            env.update(DEBUGINFOD_URLS='',NSSOC_STACK_CONTEXT=str(out/'context.json'),HOME=str(out),NSSOC_STACK_FIXTURE_CWD=str(out))
            assert file_sha(gdb)==GDB_SHA
            args=[gdb,'--nx','--nh','--quiet','--batch','-iex','set auto-load off','-iex','set debuginfod enabled off','-x',str(launch)]
            seconds=min(10.,deadline-time.monotonic());assert seconds>0
            command=supervised(args,env,out/'command',seconds)
            report['command']=command
            pin.verify();report['after']=verify_live(expect,inv)
            assert command['status']=='COMPLETED_SUPERVISED_COMMAND'and command['returncode']==0
            r=json.loads((out/'reader-result.json').read_text());accepted_reader(r);report['reader']=r
            assert file_sha(gdb)==GDB_SHA
            report['status']='PASS_BOUNDED_EXACT_NATIVE_ATTACHMENT'
            return report
        except BaseException as e:
            report.update(status='REJECTED_BOUNDED_NATIVE_ATTACHMENT',error=repr(e),traceback=traceback.format_exc())
            try:report['failure_console']=emit_bounded_command_outputs(out/'command')
            except BaseException as other:report['console_error']=repr(other)
            raise
        finally:
            # Even timeout/error must leave every target LWP detached and running.
            try:pin.verify();report['detached_after']=verify_live(expect,inv)
            except BaseException as e:
                report.update(status='REJECTED_NATIVE_DETACH_OR_IDENTITY',cleanup_unproved=repr(e))
                write(out/'result.json',report);raise
            write(out/'result.json',report)
def main():
    assert os.environ.get('GITHUB_ACTIONS')=='true'
    a=argparse.ArgumentParser();a.add_argument('--expect',required=True);a.add_argument('--inventory',required=True);a.add_argument('--out',required=True);a.add_argument('--gdb',required=True);args=a.parse_args()
    method_gate();out=Path(args.out);assert out.is_dir()
    expect=json.loads(Path(args.expect).read_text());inv_path=Path(args.inventory);inv=inventory(inv_path.read_bytes())
    assert 'identity'not in expect,'Bootstrap identity must be measured in the privileged observer'
    expect['identity']=snapshot(expect['pid'],tracer=0,require_running=True)['identity']
    assert file_sha(args.gdb)==GDB_SHA
    signal.signal(signal.SIGTERM,stopped);signal.signal(signal.SIGINT,stopped)
    start=time.monotonic();deadline=start+480;samples=[];report=dict(status='RUNNING',**FLAGS)
    try:
        with ProcessPin(expect['pid'],expect['identity'])as pin:
            pin.verify();first=verify_live(expect,inv)
            # Signal ready immediately after actual container/process binding; closure and samples remain inside 500 s envelope.
            write(out/'ready.json',dict(status='BOUND_EXACT_NATIVE_PROCESS',identity=first['identity'],**FLAGS))
            report['runtime_closure']=runtime_closure(expect['pid'],expect['identity'],inv,deadline)
            pin.verify();verify_live(expect,inv)
            for i in range(20):
                assert not(out/'stop').exists()and time.monotonic()<deadline,'Collection stopped before all20 samples'
                row=attach(expect,inv,inv_path,args.gdb,out/('sample-'+str(i).zfill(2)),deadline)
                row['index']=i;samples.append(row)
                write(out/'progress.json',dict(completed=len(samples),expected=20,**FLAGS))
                if i<19:time.sleep(5.)
            pin.verify();verify_live(expect,inv)
            assert len(samples)==20 and time.monotonic()<deadline
            report.update(status='PASS_20_EXACT_SAVED_NATIVE_STACK_SAMPLES',samples=samples,
                elapsed_s=time.monotonic()-start,one_pidfd_held_for_full_collection=True,identity=expect['identity'])
    except BaseException as e:
        report.update(status='REJECTED_EXACT_NATIVE_STACK_COLLECTION',error=repr(e),traceback=traceback.format_exc(),samples=samples)
        raise
    finally:
        write(out/'result.json',report)
        if not(out/'ready.json').exists():write(out/'ready.json',report)
if __name__=='__main__':main()
