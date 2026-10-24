#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0
"""Cloud-only native-self and corruption controls; never starts a router or simulator."""
import ast
import base64
import copy
import hashlib
import json
import os
from pathlib import Path
import sys
import threading
import time
import traceback
import mainchip_proc_observer as obs

ROOT=Path(__file__).resolve().parents[1]
METHOD="scripts/mainchip-proc-observer-methods.json"
OUT=ROOT/"cloud-mainchip-proc-observer"

def methods():
    method=json.loads((ROOT/METHOD).read_text())
    assert method["native_route_execution_allowed"] is False
    for path,expected in method["protected"].items():
        assert hashlib.sha256((ROOT/path).read_bytes()).hexdigest()==expected,path
    code=ast.parse((ROOT/"scripts/mainchip_proc_observer.py").read_text())
    forbidden={"kill","killpg","system","fork","execve","execv","execvp","execvpe",
        "ptrace","chmod","chown","rename","remove","unlink","mkdir","makedirs",
        "popen","Popen","run","check_output","setns","unshare","pidfd_send_signal"}
    assert not any(isinstance(n,ast.Attribute) and n.attr in forbidden for n in ast.walk(code))
    opens=[n for n in ast.walk(code)if isinstance(n,ast.Call)and isinstance(n.func,ast.Attribute)
        and isinstance(n.func.value,ast.Name)and n.func.value.id=="os"and n.func.attr=="open"]
    assert len(opens)==6
    for node in opens:
        flags=ast.unparse(node.args[1])
        assert "os.O_RDONLY" in flags and not any(v in flags for v in ("O_RDWR","O_WRONLY","O_CREAT","O_TRUNC"))
    return method

def rebind(record,key,data):
    original=record["raw"][key]
    record["raw"][key]=obs.encode(data,original["monotonic_begin_ns"],original["monotonic_end_ns"])

def stat_field(record,key,number,value):
    data=obs.decode(record["raw"][key]);end=data.rfind(b")")
    fields=data[end+1:].split();fields[number-3]=str(value).encode()
    rebind(record,key,data[:end+1]+b" "+b" ".join(fields)+b"\n")

def metadata(record,key,field,value):
    data=json.loads(obs.decode(record["raw"][key]));data[field]=value
    rebind(record,key,json.dumps(data,sort_keys=True).encode())

def controls(evidence):
    bad=[]
    def reject(name,fn):
        try:
            fn()
        except (AssertionError,ValueError,KeyError,TypeError):
            bad.append(name)
        else:
            raise AssertionError("Accepted fault "+name)
    stop=threading.Event();ready=threading.Event()
    def sleeper():
        ready.set();stop.wait()
    worker=threading.Thread(target=sleeper,name="proc-test) (x")
    worker.start();assert ready.wait(5)
    samples=[]
    evidence["actual_self_samples"]=samples
    evidence["rejected_so_far"]=bad
    try:
        with obs.ProcObserver(os.getpid()) as reader:
            for unused in range(3):
                # A real hosted self-process counter exercise; not a target/router workload.
                start=time.process_time_ns()
                while time.process_time_ns()-start<50_000_000:
                    hashlib.sha256(b"native-self-observer-control").digest()
                sample=reader.snapshot()
                samples.append(sample)
                assert sample["status"]=="OBSERVED_IDENTITY_BOUND_PROCESS",sample.get("error")
        assert all(len(x["derived"]["threads"])>=2 for x in samples)
        identity=samples[0]["derived"]["identity"]
        assert identity["pid"]==os.getpid()
        with open("/proc/self/exe","rb")as executable:
            assert hashlib.file_digest(executable,"sha256").hexdigest()==identity["executable"]["sha256"]
        assert samples[-1]["derived"]["process"]["stat_after"]["user_ticks"] > samples[0]["derived"]["process"]["stat_before"]["user_ticks"]
        assert all(not x[k] for x in samples for k in obs.FLAGS)
        base=samples[0]
        leader=str(os.getpid());prefix="thread_"+leader+"_"
        def single(name,mutate):
            q=copy.deepcopy(base);mutate(q);reject(name,lambda:obs.validate(q))
        single("pid-reused-within-snapshot",lambda q:stat_field(q,"process_stat_after",22,identity["starttime_ticks"]+1))
        single("changed-numeric-pid",lambda q:q.__setitem__("pid",q["pid"]+1))
        single("cpu-counter-regression",lambda q:stat_field(q,"process_stat_before",14,base["derived"]["process"]["stat_after"]["user_ticks"]+1))
        single("thread-id-reused",lambda q:stat_field(q,prefix+"stat_after",22,base["derived"]["threads"][leader]["stat_after"]["starttime_ticks"]+1))
        single("thread-cpu-regression",lambda q:stat_field(q,prefix+"stat_before",15,base["derived"]["threads"][leader]["stat_after"]["system_ticks"]+1))
        single("boot-changed",lambda q:rebind(q,"boot_after",b"00000000-0000-4000-8000-000000000000\n"))
        single("boot-malformed",lambda q:rebind(q,"boot_before",b"not-a-boot-uuid"))
        single("thread-set-changed",lambda q:rebind(q,"task_ids_after",json.dumps([os.getpid()]).encode()))
        single("duplicate-thread",lambda q:rebind(q,"task_ids_before",json.dumps([os.getpid(),os.getpid()]).encode()))
        single("proc-directory-reused",lambda q:metadata(q,"directory_after","inode",identity["proc_directory"]["inode"]+1))
        single("thread-directory-reused",lambda q:metadata(q,prefix+"directory_after","inode",base["derived"]["threads"][leader]["directory"]["inode"]+1))
        single("executable-changed",lambda q:q["raw"]["exe_after"].__setitem__("sha256","0"*64))
        single("executable-file-modified",lambda q:q["raw"]["exe_after"]["fstat_after"].__setitem__("size",0))
        single("unreadable-required-stat",lambda q:q["raw"]["process_stat_before"].update(kind="unavailable",errno=13))
        single("raw-evidence-bit-corruption",lambda q:q["raw"]["process_stat_before"].__setitem__("sha256","0"*64))
        single("raw-evidence-size-corruption",lambda q:q["raw"]["process_stat_before"].__setitem__("bytes",1))
        single("evidence-order-reversed",lambda q:q["read_order"].reverse())
        single("evidence-order-missing",lambda q:q["read_order"].pop())
        single("monotonic-clock-reordered",lambda q:q["raw"]["boot_after"].__setitem__("monotonic_begin_ns",q["monotonic_begin_ns"]-1))
        single("noninteger-clock",lambda q:q.__setitem__("monotonic_begin_ns",float(q["monotonic_begin_ns"])))
        single("namespace-changed",lambda q:rebind(q,"pid_namespace_after",b"pid:[0]"))
        single("invented-route-acceptance",lambda q:q.__setitem__("route_progress_accepted",True))
        single("invented-liveness-acceptance",lambda q:q.__setitem__("process_liveness_accepted",True))
        single("missing-thread-evidence",lambda q:q["raw"].pop(prefix+"stat_after"))
        single("extra-unbound-evidence",lambda q:q["raw"].__setitem__("extra",copy.deepcopy(q["raw"]["boot_after"])))
        io=obs.decode(base["raw"]["process_io_before"])
        assert io is not None
        single("malformed-available-io",lambda q:rebind(q,"process_io_before",b"rchar: not-a-counter\n"))
        def lower_io(q):
            fields=obs.parse_io(obs.decode(q["raw"]["process_io_after"]))
            fields["rchar"]=obs.parse_io(io)["rchar"]-1
            assert fields["rchar"]>=0
            rebind(q,"process_io_after",b"".join(k.encode()+b": "+str(v).encode()+b"\n"for k,v in fields.items()))
        single("non-atomic-io-regression-detected",lower_io)
        single("malformed-available-memory",lambda q:rebind(q,"process_statm_before",b"1 2 bad 4 5 6 7\n"))
        q=copy.deepcopy(base)
        for key in q["raw"]:
            if "_io_" in key or "_wchan_" in key:
                old=q["raw"][key]
                q["raw"][key]=dict(kind="unavailable",errno=13,message="synthetic permission fixture",
                    monotonic_begin_ns=old["monotonic_begin_ns"],monotonic_end_ns=old["monotonic_end_ns"])
        optional=obs.validate(q)
        assert optional["process"]["io_before"] is None and optional["process"]["wchan_after"] is None
        assert optional["missing_optional_values_are_not_zero"]
        data=obs.decode(base["raw"]["process_stat_before"])
        end=data.rfind(b")");start=data.index(b"(")+1
        names=[b"space name",b"a)b(c",b") (",b"line\n) (",b"",b"all)))"]
        for name in names:
            altered=data[:start]+name+data[end:]
            parsed=obs.parse_stat(altered)
            assert parsed["pid"]==os.getpid() and parsed["comm_base64"]==base64.b64encode(name).decode()
            assert parsed["starttime_ticks"]==identity["starttime_ticks"]
        reject("stat-no-closing-parenthesis",lambda:obs.parse_stat(b"1 (missing R 0"))
        reject("stat-short-numeric-tail",lambda:obs.parse_stat(b"1 (name) R 0\n"))
        reject("stat-nonnumeric-tail",lambda:obs.parse_stat(data[:end+1]+b" R nope"+b" 0"*49))
        reject("stat-nul-in-comm",lambda:obs.parse_stat(data[:start]+b"\0"+data[end:]))
        reject("wrong-caller-identity",lambda:obs.validate(base,expected_identity={}))
        current=samples[1]
        def cross(name,mutate):
            q=copy.deepcopy(current);mutate(q);reject(name,lambda:obs.validate(q,base))
        cross("pid-reuse-between-samples",lambda q:[stat_field(q,k,22,identity["starttime_ticks"]+1)for k in ("process_stat_before","process_stat_after")])
        cross("boot-change-between-samples",lambda q:[rebind(q,k,b"00000000-0000-4000-8000-000000000000\n")for k in ("boot_before","boot_after")])
        cross("directory-reuse-between-samples",lambda q:[metadata(q,k,"inode",identity["proc_directory"]["inode"]+1)for k in ("directory_before","directory_after")])
        cross("binary-change-between-samples",lambda q:[q["raw"][k].__setitem__("sha256","0"*64)for k in ("exe_before","exe_after")])
        cross("tid-reuse-between-samples",lambda q:[stat_field(q,prefix+"stat_"+k,22,base["derived"]["threads"][leader]["stat_after"]["starttime_ticks"]+1)for k in ("before","after")])
        assert len(bad)==38,len(bad)
        return dict(status="PASS_NATIVE_SELF_AND38_PROCESS_OBSERVER_FAULTS",
            rejected=bad,actual_sample_count=len(samples),comm_parenthesis_newline_cases=len(names),
            optional_permission_fixture_verified=True,router_started=False,simulator_started=False,
            process_restart_performed=False,read_only_target=True,**obs.FLAGS)
    finally:
        stop.set();worker.join(timeout=5);assert not worker.is_alive()

def main():
    assert os.environ.get("GITHUB_ACTIONS")=="true" and sys.argv[1:]==["--controls"]
    OUT.mkdir(exist_ok=False)
    result=dict(status="RUNNING",source=os.environ["GITHUB_SHA"],run=os.environ["GITHUB_RUN_ID"],**obs.FLAGS)
    try:
        result["methods"]=methods()
        result["observation_evidence"]={}
        result["controls"]=controls(result["observation_evidence"])
        methods()
        result["status"]="PASS_MAINCHIP_READ_ONLY_PROC_OBSERVER_CONTROLS"
    except BaseException as exc:
        result.update(status="FAIL_MAINCHIP_PROC_OBSERVER_CONTROLS",error=repr(exc),traceback=traceback.format_exc())
        raise
    finally:
        data=(json.dumps(result,indent=2)+"\n").encode()
        (OUT/"result.json").write_bytes(data)
        print("PROC_OBSERVER_RESULT_BYTES",len(data),"SHA256",hashlib.sha256(data).hexdigest(),flush=True)
        encoded=base64.b64encode(data).decode()
        for i in range(0,len(encoded),4096):
            print("PROC_OBSERVER_RESULT_BASE64",i//4096,encoded[i:i+4096],flush=True)

if __name__=="__main__":
    main()
