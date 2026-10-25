#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0
"""Exact restored OpenROAD reader; no permission canaries or target writes."""
import copy,json,os,time,traceback
from pathlib import Path
import gdb
from mainchip_userstack_native_binding import inventory,mapped_runtime,loaded_native_executable,verify_live,MODE
from mainchip_userstack_identity import snapshot,check_frames,module_inventory,frame_binding,ProcessPin,loaded_executable_identity
OFF=('may-write-registers','may-write-memory','may-insert-breakpoints',
     'may-insert-tracepoints','may-insert-fast-tracepoints','may-call-functions')

def write(path,report):
    temp=path.with_suffix('.tmp');temp.write_text(json.dumps(report,indent=2,allow_nan=False)+'\n');temp.replace(path)

def run():
    ctx=json.loads(Path(os.environ['NSSOC_STACK_CONTEXT']).read_text())
    assert os.environ.get('GITHUB_ACTIONS')=='true'
    assert ctx['mode']==MODE and ctx['native_attachment_authorized']is True
    assert ctx['permission_canaries']is False and ctx['fault']is None
    inv=inventory(Path(ctx['inventory_path']).read_bytes())
    verify_live(ctx['container'],inv)
    pid=ctx['expected']['pid'];out=Path(ctx['output'])
    result=dict(status='RUNNING',identity=ctx['expected'],native_attachment_authorized=True,
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
        result['gdb_programspace_filename']=gdb.current_progspace().filename
        write(out,result)
        result['loaded_executable_identity']=loaded_native_executable(pid,ctx['expected'],result['gdb_programspace_filename'])
        pin.verify(tracer=0,require_running=True)
        verify_live(ctx['container'],inv)
        started=time.monotonic_ns()
        gdb.execute('attach '+str(pid));attached=True
        during=pin.verify(tracer=os.getpid(),require_running=False)
        assert all(t['state']in ('T','t')for t in during['tasks'])
        verify_live(ctx['container'],inv,tracer=os.getpid(),require_running=False)
        result['stopped_identity']=during
        write(out,result)
        # No injected fixture faults or permission-write canaries are allowed on the native target.
        modules=mapped_runtime(pid,ctx['expected'],inv)
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
        verify_live(ctx['container'],inv,tracer=os.getpid(),require_running=False)
        result['stopped_read_finished_ns']=time.monotonic_ns()
        result['stop_read_duration_ns']=result['stopped_read_finished_ns']-started
        result['status']='ACQUIRED_BOUNDED_NATIVE_STACKS'
    except BaseException as e:
        result.update(status='REJECTED_NATIVE_STACK_READER',error=repr(e),traceback=traceback.format_exc())
    finally:
        # An attach may partly succeed before raising. Inspect actual inferior state.
        try:
            inferior=gdb.selected_inferior()
            if attached or inferior.pid:
                assert inferior.pid==pid
                result['detach_attempted']=True
                result['detach_acknowledgment']=gdb.execute('detach',to_string=True)
                assert gdb.selected_inferior().pid==0
                verify_live(ctx['container'],inv)
                result['detached']=True
            else:result['detached']=False
        except BaseException as e:
            result.update(status='REJECTED_NATIVE_STACK_DETACH',detach_error=repr(e))
        if pin is not None:pin.close()
        result['finished_monotonic_ns']=time.monotonic_ns()
        write(out,result)
    if result['status']!='ACQUIRED_BOUNDED_NATIVE_STACKS':raise gdb.GdbError(result['status'])

run()
