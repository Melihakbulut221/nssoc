#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0
"""Trusted GDB-side bounded reader. Invoked only by fixture supervisor for now."""
import copy,json,os,time,traceback
from pathlib import Path
import gdb
from mainchip_userstack_identity import snapshot,check_frames,module_inventory,frame_binding,ProcessPin
OFF=('may-write-registers','may-write-memory','may-insert-breakpoints',
     'may-insert-tracepoints','may-insert-fast-tracepoints','may-call-functions')

def write(path,report):
    temp=path.with_suffix('.tmp');temp.write_text(json.dumps(report,indent=2,allow_nan=False)+'\n');temp.replace(path)

def run():
    ctx=json.loads(Path(os.environ['NSSOC_STACK_CONTEXT']).read_text())
    assert os.environ.get('GITHUB_ACTIONS')=='true'
    assert ctx['mode']=='OWNED_HARMLESS_FIXTURE' and ctx['native_attachment_authorized']is False
    pid=ctx['expected']['pid'];out=Path(ctx['output'])
    result=dict(status='RUNNING',identity=ctx['expected'],native_attachment_authorized=False,
        scheduling_perturbed=True,native_memory_writes_permitted=False,threads=[],detach_attempted=False)
    attached=False;pin=None
    try:
        pin=ProcessPin(pid,ctx['expected'])
        pin.verify(tracer=0,require_running=True)
        gdb.execute('set auto-load off')
        gdb.execute('set debuginfod enabled off')
        gdb.execute('set pagination off')
        gdb.execute('set confirm off')
        gdb.execute('set non-stop off')
        for name in OFF:gdb.execute('set '+name+' off')
        result['permissions']={name:gdb.parameter(name)for name in OFF}
        result['auto_load']={name:gdb.parameter('auto-load '+name)for name in ('python-scripts','gdb-scripts','local-gdbinit','libthread-db')}
        assert all(v is False for v in result['auto_load'].values())
        assert all(v is False for v in result['permissions'].values())
        assert gdb.parameter('debuginfod enabled')=='off'
        # Numeric PID comes only from the validated owned fixture context.
        gdb.execute('set sysroot /proc/'+str(pid)+'/root')
        gdb.execute('file /proc/'+str(pid)+'/exe')
        assert gdb.current_progspace().filename=='/proc/'+str(pid)+'/exe'
        started=time.monotonic_ns()
        gdb.execute('attach '+str(pid));attached=True
        during=pin.verify(tracer=os.getpid(),require_running=False)
        assert all(t['state']in ('T','t')for t in during['tasks'])
        result['stopped_identity']=during
        write(out,result)
        if ctx.get('fault')=='error-after-attach':raise RuntimeError('Actual fixture injected reader error')
        if ctx.get('fault')=='identity-after-attach':
            bad=copy.deepcopy(ctx['expected']);bad['starttime']+=1
            snapshot(pid,bad,tracer=os.getpid())
        if ctx.get('fault')=='timeout-after-attach':time.sleep(60)
        if ctx.get('permission_canaries'):
            assert gdb.lookup_global_symbol('fixture_counter') is not None
            assert gdb.lookup_global_symbol('fixture_noop') is not None
            commands=[('set variable fixture_counter = 0',('memory','not allowed')),
                      ('set $rax = 0',('register','not allowed')),
                      ('call fixture_noop()',('may-call-functions',))]
            failures=[]
            for command,required in commands:
                try:gdb.execute(command,to_string=True)
                except gdb.error as e:
                    assert all(word in str(e).lower()for word in required),('Wrong rejection',command,str(e))
                    failures.append(dict(command=command,error=str(e)))
                else:raise AssertionError('Readonly permission allowed '+command)
            result['permission_canaries']=failures
            assert len(failures)==len(commands)
        modules=module_inventory(pid)
        assert modules['files']==ctx['module_files'],'Mapped target modules changed'
        result['native_modules']=modules
        native={x['pid']:x for x in during['tasks']}
        threads=gdb.selected_inferior().threads()
        assert len(threads)==len(native)<=64
        for thread in sorted(threads,key=lambda x:x.ptid[1]):
            host_tid=int(thread.ptid[1]);assert host_tid in native
            thread.switch();frames=[];errors=[]
            frame=gdb.newest_frame()
            for level in range(16):
                if frame is None:break
                try:
                    pc=int(frame.pc())
                    obj=gdb.solib_name(pc)
                    frames.append(dict(level=level,pc=pc,name=frame.name(),type=int(frame.type()),object_path=obj,
                        binding=frame_binding(pc,modules)))
                    frame=frame.older()
                except gdb.error as e:
                    errors.append(str(e));break
            assert frames,'No actual frame acquired'
            result['threads'].append(dict(host_tid=host_tid,native_starttime=native[host_tid]['starttime'],
                frames=frames,truncated=frame is not None,unwind_errors=errors))
        check_frames(result,during)
        result['maps']=(Path('/proc')/str(pid)/'maps').read_text()
        result['stopped_read_finished_ns']=time.monotonic_ns()
        result['stop_read_duration_ns']=result['stopped_read_finished_ns']-started
        result['status']='ACQUIRED_BOUNDED_FIXTURE_STACKS'
    except BaseException as e:
        result.update(status='REJECTED_FIXTURE_STACK_READER',error=repr(e),traceback=traceback.format_exc())
    finally:
        # An attach may partly succeed before raising. Inspect actual inferior state.
        try:
            inferior=gdb.selected_inferior()
            if attached or inferior.pid:
                assert inferior.pid==pid
                result['detach_attempted']=True
                result['detach_acknowledgment']=gdb.execute('detach',to_string=True)
                assert gdb.selected_inferior().pid==0
                result['detached']=True
            else:result['detached']=False
        except BaseException as e:
            result.update(status='REJECTED_FIXTURE_STACK_DETACH',detach_error=repr(e))
        if pin is not None:pin.close()
        result['finished_monotonic_ns']=time.monotonic_ns()
        write(out,result)
    if result['status']!='ACQUIRED_BOUNDED_FIXTURE_STACKS':raise gdb.GdbError(result['status'])

run()
