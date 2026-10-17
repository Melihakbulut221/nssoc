#!/usr/bin/env python3
# SPDX-FileCopyrightText: 2026 Hasan Melih Akbulut
# SPDX-License-Identifier: Apache-2.0
"""One fresh, detached CPU10 probe; native ownership stays inside the driver."""
import datetime
import hashlib
import json
import os
import signal
from pathlib import Path
import subprocess
import sys

R=Path.cwd()
B=Path(__file__).resolve().parent
OUT=Path('/dev/shm/nssoc-vco-v6-divider-power-v2-wire-06-01')
sys.path.insert(0,str(R/'scripts'))
import characterize_pcie_vco_v6_divider_power_v2_wire_v1 as m


def pin(p):
    p=Path(p)
    return {'bytes':p.stat().st_size,'sha256':hashlib.sha256(p.read_bytes()).hexdigest()}


def verify():
    freeze=json.loads((B/'source-freeze01.json').read_text())
    for path,p in freeze['pins'].items():
        assert pin(path)==p,path
    peer=json.loads((B/'source-only-peer01-rx.json').read_text())
    assert peer['status']=='PASS_SOURCE_ONLY_LOADED455_WIRE_MODEL' and peer['findings']==[]
    assert peer['freeze']==pin(B/'source-freeze01.json')
    assert os.sched_getaffinity(0)=={10}
    assert not OUT.exists()
    c,rows,_=m.config(.6,'')
    assert len(rows)==455 and len(m.n.vectors(rows,c['extra_vectors']))==956
    free,used=m._scope['guard'](OUT)
    assert free>=1024**3 and used+24*1024**2<m.OWN_LIMIT
    return {'freeze':pin(B/'source-freeze01.json'),'peer':pin(B/'source-only-peer01-rx.json'),'free':free,'own':used,'utc':datetime.datetime.now(datetime.UTC).isoformat()}


def run_with_boundary_signals():
    # Outside the native owner there are no owned children. Fail immediately
    # so cancellation cannot remain trapped in an inactive outer owner's flag.
    # The inner ProcessOwner temporarily installs its graceful native handler
    # and restores this one, covering both entry and exit handoff boundaries.
    def stop(signum, frame):
        raise RuntimeError("Controller received " + signal.Signals(signum).name)
    previous={sig:signal.getsignal(sig) for sig in (signal.SIGINT,signal.SIGTERM)}
    try:
        for sig in previous:signal.signal(sig,stop)
        return m.run(OUT,.6,'')
    finally:
        for sig,handler in previous.items():signal.signal(sig,handler)


def controller():
    preflight=verify()
    result={'status':'RUNNING','preflight':preflight,'out':str(OUT),'controller_pid':os.getpid(),'boot_id':Path('/proc/sys/kernel/random/boot_id').read_text().strip()}
    m.n.common.atomic(B/'native06-controller.json',result)
    try:
        native=run_with_boundary_signals()
        m._scope['guard'](OUT)
        result.update(status='CLOSED_FINITE_NATIVE_RESULT',native_status=native['status'],outputs={str(p.relative_to(OUT)):pin(p) for p in OUT.rglob('*') if p.is_file()})
        m.n.common.atomic(B/'native06-controller.json',result)
        return 0 if native['status']=='PASS_NATIVE_LOADED_FEEDBACK_SCREEN' else 1
    except BaseException as error:
        result.update(status='FAILED_RETAINED',error=repr(error),outputs={str(p.relative_to(OUT)):pin(p) for p in OUT.rglob('*') if p.is_file()} if OUT.exists() else {})
        m.n.common.atomic(B/'native06-controller.json',result)
        raise


def launch():
    preflight=verify()
    with (B/'launch-once.json').open('x') as f:json.dump(preflight,f,indent=2)
    command=['taskset','-c','10',str(R/'hw/soc/tools/cocotb-venv/bin/python'),str(Path(__file__).resolve()),'--controller']
    env={k:v for k,v in os.environ.items() if k not in ('PYTHONPATH','PYTHONHOME','PYTHONEXECUTABLE','GH_TOKEN','GITHUB_TOKEN','LD_PRELOAD')}
    env.update(PYTHONDONTWRITEBYTECODE='1',OPENBLAS_NUM_THREADS='1',OMP_NUM_THREADS='1')
    with (B/'native-06-01.log').open('x') as log:
        process=subprocess.Popen(command,cwd=R,stdin=subprocess.DEVNULL,stdout=log,stderr=subprocess.STDOUT,start_new_session=True,close_fds=True,env=env)
        fields=(Path('/proc')/str(process.pid)/'stat').read_text().rsplit(') ',1)[1].split()
    receipt={'status':'DETACHED_CONTROLLER_STARTED_NATIVE_PROGRESS_REQUIRED','controller':{'pid':process.pid,'start_ticks':fields[19],'process_group':int(fields[2])},'boot_id':Path('/proc/sys/kernel/random/boot_id').read_text().strip(),'command':command,'preflight':preflight,'launcher':pin(Path(__file__))}
    m.n.common.atomic(B/'detached-launch.json',receipt)
    print(json.dumps(receipt))


if __name__=='__main__':
    if sys.argv[1:]==['--controller']:raise SystemExit(controller())
    assert not sys.argv[1:]
    launch()
