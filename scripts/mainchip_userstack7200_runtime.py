#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0
"""Read-only full runtime/identity check. No ptrace, debugger or target command."""
import argparse,json,os,sys,time
from pathlib import Path
from mainchip_userstack7200_admission import methods
from mainchip_userstack_native_binding import inventory,inspect,bound,verify_live,runtime_closure,mapped_runtime
from mainchip_userstack_identity import snapshot,ProcessPin
def main():
    assert os.geteuid()==0
    m=methods();assert m['native_process_restore_authorized']is True and m['gdb_attachment_authorized']is False
    p=argparse.ArgumentParser();p.add_argument('--expect',required=True);p.add_argument('--inventory',required=True)
    a=p.parse_args();expect=json.loads(Path(a.expect).read_bytes());inv=inventory(Path(a.inventory).read_bytes())
    assert expect['mode']=='EXACT_NO_GDB_7200_RUNTIME_BINDING' and expect['route_tcl'].endswith('/cloud-mainchip-route12-drt-runtime/work/route.tcl')
    bound(inspect(expect['id']),expect)
    got=snapshot(expect['pid'],tracer=0,require_running=True);expect['identity']=got['identity']
    with ProcessPin(expect['pid'],expect['identity'])as pin:
        pin.verify();before=verify_live(expect,inv);pin.verify()
        full=runtime_closure(expect['pid'],expect['identity'],inv,time.monotonic()+300)
        modules=mapped_runtime(expect['pid'],expect['identity'],inv)
        after=verify_live(expect,inv);pin.verify()
    assert before['identity']==after['identity']
    print(json.dumps(dict(status='PASS_EXACT_RUNTIME_CLOSURE_WITHOUT_GDB',identity=after['identity'],
        runtime_closure=full,mapped_files=modules['files'],mapped_inventory_sha256=modules['inventory_sha256'],
        gdb_attached=False,target_memory_written=False,target_registers_written=False,
        target_detached=after['tracer_pid']==0,normal_continuation_preaccepted=False)))
if __name__=='__main__':main()
