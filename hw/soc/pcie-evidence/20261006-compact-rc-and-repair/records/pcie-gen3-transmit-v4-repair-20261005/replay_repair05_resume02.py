# SPDX-FileCopyrightText: 2026 Hasan Melih Akbulut
# SPDX-License-Identifier: Apache-2.0
"""Replay unchanged three-case TX oracle against exact bound candidate05."""
import ast
import gzip
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import resource
import shutil
import signal
import subprocess
import sys
import time

from owned_lifecycle05 import owned_popen, stop_failed_group

assert sys.version_info[:2]==(3,12)
R=Path.cwd();B=Path(__file__).resolve().parent
OUT=Path('/dev/shm/nssoc-tx-path-v4-repair05-physical-replay-02')
NET=Path('/dev/shm/nssoc-tx-path-v4-postroute-repair-05/repaired.v')
E=Path('/dev/shm/nssoc-tx-path-v4-repair05-equivalence')
MODEL=Path('/home/hasanmelih/.ciel/ciel/ihp-sg13g2/versions/c4b8b4e5e7a05f375cca3815d51b3a37721fbf5c/ihp-sg13g2/libs.ref/sg13g2_stdcell/verilog/sg13g2_stdcell.v')
sys.path.insert(0,str(R/'scripts'))
from check_pcie_integrity import tool_environment
from check_pcie_integrity_native import MODEL_SHA
from cocotb_results import count_results

def pin(p):
    with p.open('rb') as f:return {'bytes':p.stat().st_size,'sha256':hashlib.file_digest(f,'sha256').hexdigest()}

def interrupted(n,f):raise InterruptedError(f'Parent signal{n}')
for s in (signal.SIGTERM,signal.SIGINT):signal.signal(s,interrupted)
spec=importlib.util.spec_from_file_location('tx05_bound_proof',B/'proof_gate_repair05.py');gate=importlib.util.module_from_spec(spec);spec.loader.exec_module(gate)
binding=gate.verify_binding();assert pin(MODEL)['sha256']==MODEL_SHA
bench=R/'hw/soc/tb/cocotb/test_soc_pcie_gen3_tx_path_v4.py';make=bench.with_name('Makefile.soc_pcie_gen3_tx_path_v4');runtime=R/'hw/soc/tools/oss-cad-suite'
files=[Path(__file__),B/'owned_lifecycle05.py',B/'proof_gate_repair05.py',E/'proof-execution-binding.json',*gate.input_paths(),B/'normalize_repair05.py',NET,MODEL,bench,make,R/'scripts/check_pcie_integrity.py',R/'scripts/check_pcie_integrity_native.py',R/'scripts/cocotb_results.py']
files += [runtime/d/n for d,names in [('bin',['iverilog','vvp']),('libexec',['iverilog','vvp'])] for n in names]
before={str(p):pin(p) for p in files}
while shutil.disk_usage('/dev/shm').free<1024**3:time.sleep(5)
OUT.mkdir()
command=['make','-f',str(make),'--no-print-directory','VERILOG_SOURCES='+str(NET)+' '+str(MODEL),'SIM_BUILD='+str(OUT/'sim'),'COCOTB_RESULTS_FILE='+str(OUT/'results.xml'),'PCIE_NATIVE=1']
record={'status':'RUNNING_EXACT_BOUND_TX05_NATIVE_PORTS','inputs':before,'command':command,'allowed_cpu_affinity':sorted(os.sched_getaffinity(0)),'address_space_limit_bytes':2*1024**3,'elapsed_watchdog_seconds':None,'scope':'Original3 independent TX serial-word port cases; exact repaired native cell netlist, specify models,4ns clock; no SDF/parasitic or fullPHY timing acceptance.'}
def save():(OUT/'result.json').write_text(json.dumps(record,indent=2)+'\n')
def limits():
    resource.setrlimit(resource.RLIMIT_AS,(2*1024**3,)*2);resource.setrlimit(resource.RLIMIT_CORE,(0,0));os.sched_setaffinity(0,{min(os.sched_getaffinity(0))});signal.pthread_sigmask(signal.SIG_UNBLOCK,{signal.SIGTERM,signal.SIGINT})
ns={'stop_failed_group':stop_failed_group}
process=None;complete=False;save()
try:
    with (OUT/'simulation.log').open('x') as log:
        try:
            old=signal.pthread_sigmask(signal.SIG_BLOCK,{signal.SIGTERM,signal.SIGINT})
            try:process=owned_popen(command,cwd=OUT,env=tool_environment(runtime/'bin'),stdout=log,stderr=subprocess.STDOUT,start_new_session=True,preexec_fn=limits)
            finally:signal.pthread_sigmask(signal.SIG_SETMASK,old)
            record['pid']=process.pid;save()
            while process.poll() is None:
                if shutil.disk_usage('/dev/shm').free<528*1024**2:raise RuntimeError('Shared scratch floor')
                time.sleep(.25)
            record['returncode']=process.wait();assert record['returncode']==0;complete=True
        finally:
            if process is not None and not complete:ns['stop_failed_group'](process)
    counts=count_results([OUT/'results.xml']);record['tests']=dict(zip(('passed','failed','skipped'),counts));assert counts==(3,0,0)
    assert before=={str(p):pin(p) for p in files};assert gate.verify_binding()==binding
    raw=OUT/'sim/sim.vvp';original=pin(raw);zipped=raw.with_name(raw.name+'.gz')
    with raw.open('rb') as source,gzip.open(zipped,'xb',compresslevel=1) as dest:shutil.copyfileobj(source,dest)
    digest=hashlib.sha256();size=0
    with gzip.open(zipped,'rb') as f:
        while data:=f.read(1024**2):digest.update(data);size+=len(data)
    assert {'bytes':size,'sha256':digest.hexdigest()}==original==pin(raw)
    record['lossless_closed_program']={'raw':original,'gzip':pin(zipped),'full_readback':True};raw.unlink()
    record['status']='PASS_EXACT_BOUND_TX05_PHYSICAL_NETLIST_PORT_REPLAY'
except BaseException as error:record.update(status='FAIL_RETAINED',error=repr(error));raise
finally:
    record['outputs']={str(p.relative_to(OUT)):pin(p) for p in OUT.rglob('*') if p.is_file() and p.name!='result.json'};save()
print(record['status'],record['tests'])
