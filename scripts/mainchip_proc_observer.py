#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0
"""Identity-bound, read-only Linux process evidence. CPU movement is not routing progress."""
import argparse
import base64
import errno
import hashlib
import json
import os
import re
import stat
import sys
import time
import uuid

SCHEMA = "linux-proc-observer-v1"
LIMIT = 1024 * 1024
EXE_LIMIT = 2 * 1024**3
FLAGS = dict(route_progress_accepted=False, continuation_accepted=False,
             process_liveness_accepted=False, routing_complete=False,
             target_modified=False, atomic_snapshot=False)

def sha(data):
    return hashlib.sha256(data).hexdigest()

def encode(data, begin, end):
    return dict(kind="bytes", raw_base64=base64.b64encode(data).decode("ascii"),
                bytes=len(data), sha256=sha(data), monotonic_begin_ns=begin,
                monotonic_end_ns=end)

def decode(record, optional=False):
    if record.get("kind") == "unavailable":
        assert optional and type(record["errno"]) is int and record["errno"] > 0
        assert "raw_base64" not in record
        return None
    assert record["kind"] == "bytes"
    data = base64.b64decode(record["raw_base64"], validate=True)
    assert len(data) == record["bytes"] <= LIMIT and sha(data) == record["sha256"]
    return data

def parse_stat(raw):
    """comm may contain spaces, parentheses and newlines; numeric tail cannot contain ') '."""
    assert b"\0" not in raw and len(raw) <= LIMIT
    match = re.match(rb"([1-9][0-9]*) \(", raw)
    assert match is not None
    end = raw.rfind(b")")
    assert end >= match.end() and raw[end+1:end+2] == b" "
    tail = raw[end+1:].split()
    assert len(tail) >= 50 and tail[0] in [bytes([x]) for x in b"RSDZTtWXxKPI"]
    assert all(re.fullmatch(rb"-?[0-9]+", x) for x in tail[1:])
    def field(n):
        return int(tail[n-3])
    fields = dict(pid=int(match[1]), state=tail[0].decode("ascii"),
        comm_base64=base64.b64encode(raw[match.end():end]).decode("ascii"),
        ppid=field(4), user_ticks=field(14), system_ticks=field(15),
        waited_children_user_ticks=field(16), waited_children_system_ticks=field(17),
        threads=field(20), starttime_ticks=field(22), virtual_bytes=field(23),
        resident_pages=field(24), processor=field(39), guest_ticks=field(43))
    assert all(fields[k] >= 0 for k in ("ppid","user_ticks","system_ticks",
        "starttime_ticks","virtual_bytes","resident_pages","guest_ticks"))
    assert fields["threads"] > 0
    return fields

def key_values(raw):
    result = {}
    for line in raw.splitlines():
        key, separator, value = line.partition(b":")
        assert separator and key not in result
        result[key] = value.strip()
    return result

def parse_io(raw):
    rows = key_values(raw)
    required = {b"rchar",b"wchar",b"syscr",b"syscw",b"read_bytes",
                b"write_bytes",b"cancelled_write_bytes"}
    assert required <= set(rows)
    assert all(re.fullmatch(rb"[0-9]+", value) for value in rows.values())
    return {key.decode("ascii"):int(value) for key,value in rows.items()}

def parse_status(raw, tid, pid):
    rows = key_values(raw)
    assert int(rows[b"Pid"]) == tid and int(rows[b"Tgid"]) == pid
    memory = {}
    for key,value in rows.items():
        if key.startswith(b"Vm") or key.startswith(b"Rss"):
            parts = value.split()
            assert len(parts) == 2 and parts[1] == b"kB" and parts[0].isdigit()
            memory[key.decode("ascii")] = int(parts[0])*1024
    return dict(memory_bytes=memory,
        context_switches={k.decode("ascii"):int(rows[k]) for k in
            (b"voluntary_ctxt_switches",b"nonvoluntary_ctxt_switches") if k in rows})

def exe_identity(record):
    assert record["kind"] == "executable"
    assert record["fstat_before"] == record["fstat_after"]
    metadata = record["fstat_before"]
    assert stat.S_ISREG(metadata["mode"]) and 0 < record["bytes"] <= EXE_LIMIT
    assert record["bytes"] == metadata["size"]
    assert re.fullmatch("[0-9a-f]{64}", record["sha256"])
    base64.b64decode(record["link_base64"], validate=True)
    return {k:record[k] for k in ("sha256","bytes","fstat_before","link_base64")}

def validate(report, previous=None, expected_identity=None):
    assert report["schema"] == SCHEMA
    assert all(report[k] is value for k,value in FLAGS.items())
    assert type(report["pid"]) is int and report["pid"] > 0
    assert type(report["clock_ticks_per_second"]) is int and report["clock_ticks_per_second"] > 0
    assert type(report["page_bytes"]) is int and report["page_bytes"] > 0
    raw = report["raw"]
    begin, end = report["monotonic_begin_ns"],report["monotonic_end_ns"]
    assert type(begin) is int and type(end) is int and 0 < begin <= end
    order=report["read_order"]
    assert len(order)==len(set(order))==len(raw) and set(order)==set(raw)
    last = begin
    for key in order:
        record=raw[key]
        a,b = record["monotonic_begin_ns"],record["monotonic_end_ns"]
        assert type(a) is int and type(b) is int and last <= a <= b <= end, key
        last = b
    boot = decode(raw["boot_before"]).strip()
    assert str(uuid.UUID(boot.decode("ascii"))).encode() == boot
    assert boot == decode(raw["boot_after"]).strip()
    directory = json.loads(decode(raw["directory_before"]))
    assert directory == json.loads(decode(raw["directory_after"]))
    assert directory["inode"] > 0 and stat.S_ISDIR(directory["mode"])
    assert set(directory)=={"device","inode","mode","size","mtime_ns","ctime_ns"}
    namespaces = {}
    for suffix in ("before","after"):
        namespaces[suffix] = decode(raw["pid_namespace_"+suffix], optional=True)
    assert namespaces["before"] == namespaces["after"], "PID namespace changed or availability changed"
    first,second = (parse_stat(decode(raw["process_stat_"+x])) for x in ("before","after"))
    assert first["pid"] == second["pid"] == report["pid"]
    assert first["starttime_ticks"] == second["starttime_ticks"], "PID reused"
    assert first["ppid"] == second["ppid"], "Parent changed during observation"
    assert all(second[k] >= first[k] for k in ("user_ticks","system_ticks"))
    executable = exe_identity(raw["exe_before"])
    assert executable == exe_identity(raw["exe_after"]), "Executable changed during observation"
    ids = json.loads(decode(raw["task_ids_before"]))
    assert ids == sorted(set(ids)) and ids and report["pid"] in ids and len(ids) <= 8192
    assert all(type(tid) is int and tid > 0 for tid in ids)
    assert ids == json.loads(decode(raw["task_ids_after"])), "Thread membership changed"
    assert first["threads"] == second["threads"] == len(ids)
    required = {"boot_before","directory_before","pid_namespace_before",
        "process_stat_before","exe_before","task_ids_before","task_ids_after",
        "process_stat_after","exe_after","pid_namespace_after","directory_after","boot_after"}
    derived_threads = {}
    def observed(prefix, tid, a, b):
        out = dict(stat_before=a,stat_after=b)
        for name in ("io","status","statm","wchan"):
            pair = []
            for when in ("before","after"):
                key=prefix+name+"_"+when
                required.add(key)
                value=decode(raw[key],optional=True)
                if value is None:
                    pair.append(None)
                elif name=="io":
                    pair.append(parse_io(value))
                elif name=="status":
                    pair.append(parse_status(value,tid,report["pid"]))
                elif name=="statm":
                    numbers=value.split()
                    assert len(numbers)==7 and all(x.isdigit() for x in numbers)
                    pair.append([int(x) for x in numbers])
                else:
                    pair.append(dict(raw_base64=base64.b64encode(value).decode("ascii"),
                        zero_is_not_proof_of_running=True))
            if name=="io" and all(x is not None for x in pair):
                assert pair[0].keys()==pair[1].keys()
                assert all(pair[1][k]>=pair[0][k] for k in pair[0]), "Nonmonotonic non-atomic IO observation"
            out[name+"_before"],out[name+"_after"]=pair
        return out
    process = observed("process_",report["pid"],first,second)
    for tid in ids:
        prefix="thread_"+str(tid)+"_"
        for name in ("directory_before","directory_after","stat_before","stat_after"):
            required.add(prefix+name)
        td=json.loads(decode(raw[prefix+"directory_before"]))
        assert td == json.loads(decode(raw[prefix+"directory_after"]))
        assert stat.S_ISDIR(td["mode"]) and td["inode"]>0
        a,b=(parse_stat(decode(raw[prefix+"stat_"+x]))for x in ("before","after"))
        assert a["pid"]==b["pid"]==tid and a["starttime_ticks"]==b["starttime_ticks"], "TID reused"
        assert a["ppid"]==b["ppid"]==first["ppid"]
        assert all(b[k]>=a[k]for k in ("user_ticks","system_ticks"))
        out=observed(prefix,tid,a,b);out["directory"]=td
        derived_threads[str(tid)]=out
    assert set(raw)==required, "Missing or extra unbound evidence"
    identity=dict(pid=report["pid"],boot_id=boot.decode(),starttime_ticks=first["starttime_ticks"],
        proc_directory=directory,executable=executable,
        pid_namespace_base64=None if namespaces["before"] is None else base64.b64encode(namespaces["before"]).decode(),
        clock_ticks_per_second=report["clock_ticks_per_second"],page_bytes=report["page_bytes"])
    if expected_identity is not None:
        assert identity==expected_identity, "Does not match caller-bound process identity"
    result=dict(identity=identity,process=process,threads=derived_threads,
        cpu_ticks_include_guest_time=True,child_cpu_not_added_to_process_cpu=True,
        io_counters_non_atomic=True,memory_accounting_may_be_approximate=True,
        missing_optional_values_are_not_zero=True,all_snapshots_non_atomic=True)
    if previous is not None:
        assert previous["status"]=="OBSERVED_IDENTITY_BOUND_PROCESS"
        prior=validate(previous)
        assert {k:v for k,v in previous["derived"].items() if k!="between_samples"}==prior
        assert identity==prior["identity"], "Cross-sample process identity changed"
        assert previous["monotonic_end_ns"] <= begin, "Overlapping or reordered snapshots"
        for k in ("user_ticks","system_ticks"):
            assert first[k]>=prior["process"]["stat_after"][k], "CPU counter decreased between samples"
        old_threads=prior["threads"]
        deltas={}
        for tid,cur in derived_threads.items():
            if tid not in old_threads:
                continue
            old=old_threads[tid]
            assert cur["directory"]==old["directory"]
            assert cur["stat_before"]["starttime_ticks"]==old["stat_after"]["starttime_ticks"], "TID reused across samples"
            deltas[tid]={k:cur["stat_after"][k]-old["stat_after"][k] for k in ("user_ticks","system_ticks")}
            assert all(x>=0 for x in deltas[tid].values())
        result["between_samples"]=dict(
            midpoint_elapsed_ns=(begin+end-previous["monotonic_begin_ns"]-previous["monotonic_end_ns"])//2,
            process_cpu_tick_delta={k:second[k]-prior["process"]["stat_after"][k]for k in ("user_ticks","system_ticks")},
            surviving_thread_cpu_tick_delta=deltas,
            threads_created=sorted(set(derived_threads)-set(old_threads)),
            threads_exited=sorted(set(old_threads)-set(derived_threads)),
            process_progress_inferred=False,route_progress_inferred=False)
    return result

def fstat_record(fd):
    s=os.fstat(fd)
    return dict(device=s.st_dev,inode=s.st_ino,mode=s.st_mode,size=s.st_size,
                mtime_ns=s.st_mtime_ns,ctime_ns=s.st_ctime_ns)

class ProcObserver:
    """Hold proc-directory descriptors; never re-open the numeric PID between samples."""
    def __init__(self,pid):
        assert os.environ.get("GITHUB_ACTIONS")=="true", "Cloud-only observer"
        assert sys.platform=="linux" and type(pid) is int and pid>0
        self.pid=pid
        self.root=os.open("/proc",os.O_RDONLY|os.O_DIRECTORY|os.O_CLOEXEC)
        try:
            self.directory=os.open(str(pid),os.O_RDONLY|os.O_DIRECTORY|os.O_CLOEXEC|os.O_NOFOLLOW,dir_fd=self.root)
        except BaseException:
            os.close(self.root)
            raise
        self.previous=None
    def close(self):
        os.close(self.directory);os.close(self.root)
    def __enter__(self):
        return self
    def __exit__(self,*unused):
        self.close()
    def snapshot(self,expected_identity=None):
        r=dict(schema=SCHEMA,pid=self.pid,raw={},read_order=[],monotonic_begin_ns=time.monotonic_ns(),
            clock_ticks_per_second=os.sysconf("SC_CLK_TCK"),page_bytes=os.sysconf("SC_PAGE_SIZE"),
            status="COLLECTING",**FLAGS)
        def capture(key,fn):
            assert key not in r["read_order"]
            r["read_order"].append(key)
            start=time.monotonic_ns()
            try:
                data=fn()
            except OSError as exc:
                r["raw"][key]=dict(kind="unavailable",errno=exc.errno,
                    message=str(exc),monotonic_begin_ns=start,monotonic_end_ns=time.monotonic_ns())
            else:
                r["raw"][key]=encode(data,start,time.monotonic_ns())
                assert len(data)<=LIMIT, "Oversize evidence (raw prefix retained)"
        def read_at(fd,name):
            file=os.open(name,os.O_RDONLY|os.O_CLOEXEC|os.O_NOFOLLOW,dir_fd=fd)
            try:
                with os.fdopen(file,"rb",closefd=False) as stream:
                    return stream.read(LIMIT+1)
            finally:
                os.close(file)
        def read(key,fd,name):
            capture(key,lambda:read_at(fd,name))
        def directory(key,fd):
            capture(key,lambda:json.dumps(fstat_record(fd),sort_keys=True).encode())
        def exe(key):
            assert key not in r["read_order"]
            r["read_order"].append(key)
            start=time.monotonic_ns()
            link=os.fsencode(os.readlink("exe",dir_fd=self.directory))
            fd=os.open("exe",os.O_RDONLY|os.O_CLOEXEC,dir_fd=self.directory)
            try:
                before=fstat_record(fd);h=hashlib.sha256();count=0
                while True:
                    chunk=os.read(fd,1024*1024)
                    if not chunk:break
                    count+=len(chunk);assert count<=EXE_LIMIT
                    h.update(chunk)
                after=fstat_record(fd)
            finally:
                os.close(fd)
            r["raw"][key]=dict(kind="executable",link_base64=base64.b64encode(link).decode(),
                bytes=count,sha256=h.hexdigest(),fstat_before=before,fstat_after=after,
                monotonic_begin_ns=start,monotonic_end_ns=time.monotonic_ns())
        def extras(prefix,fd,when):
            for name in ("io","status","statm","wchan"):
                read(prefix+name+"_"+when,fd,name)
        task=None
        try:
            read("boot_before",self.root,"sys/kernel/random/boot_id")
            directory("directory_before",self.directory)
            capture("pid_namespace_before",lambda:os.fsencode(os.readlink("ns/pid",dir_fd=self.directory)))
            read("process_stat_before",self.directory,"stat")
            exe("exe_before")
            task=os.open("task",os.O_RDONLY|os.O_DIRECTORY|os.O_CLOEXEC|os.O_NOFOLLOW,dir_fd=self.directory)
            def list_tasks():
                names=os.listdir(task)
                assert names and all(re.fullmatch("[1-9][0-9]*",n)for n in names)
                ids=sorted(int(n)for n in names);assert len(ids)<=8192
                return json.dumps(ids).encode()
            capture("task_ids_before",list_tasks)
            ids=json.loads(decode(r["raw"]["task_ids_before"]))
            extras("process_",self.directory,"before")
            for tid in ids:
                fd=os.open(str(tid),os.O_RDONLY|os.O_DIRECTORY|os.O_CLOEXEC|os.O_NOFOLLOW,dir_fd=task)
                try:
                    prefix="thread_"+str(tid)+"_"
                    directory(prefix+"directory_before",fd)
                    read(prefix+"stat_before",fd,"stat")
                    extras(prefix,fd,"before")
                    extras(prefix,fd,"after")
                    read(prefix+"stat_after",fd,"stat")
                    directory(prefix+"directory_after",fd)
                finally:
                    os.close(fd)
            extras("process_",self.directory,"after")
            capture("task_ids_after",list_tasks)
            read("process_stat_after",self.directory,"stat")
            exe("exe_after")
            capture("pid_namespace_after",lambda:os.fsencode(os.readlink("ns/pid",dir_fd=self.directory)))
            directory("directory_after",self.directory)
            read("boot_after",self.root,"sys/kernel/random/boot_id")
            r["monotonic_end_ns"]=time.monotonic_ns()
            r["derived"]=validate(r,self.previous,expected_identity)
            r["status"]="OBSERVED_IDENTITY_BOUND_PROCESS"
            self.previous=r
        except (OSError,AssertionError,ValueError,KeyError) as exc:
            r["monotonic_end_ns"]=time.monotonic_ns()
            r["status"]="REJECTED_PROCESS_OBSERVATION"
            r["error"]=dict(type=type(exc).__name__,message=str(exc))
        finally:
            if task is not None:os.close(task)
        return r

def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--pid",type=int,required=True)
    parser.add_argument("--samples",type=int,default=1)
    parser.add_argument("--interval",type=float,default=10.)
    args=parser.parse_args()
    assert 1<=args.samples<=60 and 0<=args.interval<=60
    try:
        with ProcObserver(args.pid) as observer:
            for i in range(args.samples):
                if i:time.sleep(args.interval)
                report=observer.snapshot()
                print(json.dumps(report,sort_keys=False),flush=True)
                if report["status"]!="OBSERVED_IDENTITY_BOUND_PROCESS":
                    raise SystemExit(1)
    except (OSError,AssertionError) as exc:
        print(json.dumps(dict(schema=SCHEMA,pid=args.pid,status="REJECTED_OBSERVER_OPEN",
            monotonic_ns=time.monotonic_ns(),error=dict(type=type(exc).__name__,message=str(exc)),**FLAGS)),flush=True)
        raise SystemExit(1)

if __name__=="__main__":
    main()
