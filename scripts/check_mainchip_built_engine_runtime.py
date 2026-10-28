#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0
"""Cloud source controls for archive admission, native cleanup and immutable scope."""
import copy
import io
import json
from pathlib import Path
import tarfile
import tempfile
from types import SimpleNamespace
from unittest.mock import patch
import mainchip_built_engine_runtime_contract as c
import mainchip_built_engine_runtime_native as native
ROOT=Path(__file__).resolve().parent.parent

def main():
    m=c.method(ROOT);positive=[];refused=[];lifecycle=[]
    def accept(label,fn):
        fn();positive.append(label)
    def reject(label,fn,reason):
        try:fn()
        except (AssertionError,ValueError)as exc:
            assert reason in str(exc),(label,str(exc),reason)
            refused.append(dict(label=label,reason=str(exc)))
        else:raise AssertionError("unexpected acceptance: "+label)
    env=dict(GITHUB_ACTIONS="true",RUNNER_OS="Linux",GITHUB_REPOSITORY=c.REPOSITORY,
        GITHUB_RUN_ID="123",GITHUB_RUN_ATTEMPT="1",GITHUB_SHA="a"*40,GITHUB_REF="refs/heads/"+c.BRANCH)
    accept("hosted exact source context",lambda:c.context(env))
    for key,value,reason in [
        ("GITHUB_ACTIONS","false","hosted"),("RUNNER_OS","Windows","hosted"),
        ("GITHUB_REPOSITORY","foreign/project","repository"),("GITHUB_RUN_ID","0","run identity"),
        ("GITHUB_RUN_ATTEMPT","2","no retry"),("GITHUB_SHA","main","source identity"),
        ("GITHUB_REF","refs/heads/codex/mainchip-internal-witness-engine-build","runtime probe branch")]:
        reject("context "+key,lambda key=key,value=value:c.context({**env,key:value}),reason)
    expected=c.expected_engine(ROOT)
    run=c.decode(c.secure_file(ROOT,c.PREFIX+"run.json").read_bytes())
    jobs=c.decode(c.secure_file(ROOT,c.PREFIX+"jobs.json").read_bytes())
    release=expected["release"];tag=c.decode(c.secure_file(ROOT,c.PREFIX+"tag.json").read_bytes())
    accept("actual prior build envelope",lambda:c.engine_envelope(run,jobs,release,tag,release))
    changed=copy.deepcopy(run);changed["head_sha"]="b"*40
    reject("wrong engine source",lambda:c.engine_envelope(changed,jobs,release,tag,release),"original build run")
    changed_jobs=copy.deepcopy(jobs);changed_jobs["jobs"][1]["conclusion"]="failure"
    reject("failed engine build",lambda:c.engine_envelope(run,changed_jobs,release,tag,release),"original build jobs")
    changed_release=copy.deepcopy(release);changed_release["assets"][0]["digest"]="sha256:"+"0"*64
    reject("changed engine asset",lambda:c.engine_envelope(run,jobs,changed_release,tag,release),"asset census")
    def capsule(entries):
        buffer=io.BytesIO()
        with tarfile.open(fileobj=buffer,mode="w:gz")as archive:
            for name,raw,kind in entries:
                info=tarfile.TarInfo(name);info.type=kind;info.size=len(raw)if kind==tarfile.REGTYPE else 0
                if kind==tarfile.SYMTYPE:info.linkname="/etc/passwd"
                archive.addfile(info,io.BytesIO(raw)if info.size else None)
        buffer.seek(0);return buffer
    expected_small={"openroad":dict(bytes=3,sha256=c.digest(b"elf")),
                    "trace.json":dict(bytes=2,sha256=c.digest(b"{}"))}
    complete=[("openroad",b"elf",tarfile.REGTYPE),("trace.json",b"{}",tarfile.REGTYPE)]
    with tempfile.TemporaryDirectory()as temp:
        counter=[0]
        def extract(entries,limit=1024):
            counter[0]+=1
            return c.engine_extract(capsule(entries),Path(temp)/str(counter[0]),expected_small,limit=limit)
        accept("complete inventory selected extraction",lambda:extract(complete))
        for label,entries,reason in [
            ("traversal",[("../openroad",b"elf",tarfile.REGTYPE)],"archive path"),
            ("absolute",[("/openroad",b"elf",tarfile.REGTYPE)],"archive path"),
            ("symlink",[("openroad",b"",tarfile.SYMTYPE)],"nonregular"),
            ("duplicate",complete+[complete[0]],"duplicate"),
            ("unknown",complete+[("extra",b"x",tarfile.REGTYPE)],"identity/size"),
            ("missing",complete[:1],"missing"),
            ("changed bytes",[("openroad",b"bad",tarfile.REGTYPE),complete[1]],"changed archive"),
            ("wrong size",[("openroad",b"elf!",tarfile.REGTYPE),complete[1]],"identity/size"),
            ("unrecorded directory",[("extra",b"",tarfile.DIRTYPE)]+complete,"unrecorded")]:
            reject(label,lambda entries=entries:extract(entries),reason)
        reject("expanded bound",lambda:extract(complete,limit=4),"expanded size")
    runtime={str(i):dict(bytes=i,sha256=str(i))for i in range(104)}
    accept("exact 104 runtime records",lambda:c.runtime_match(runtime,copy.deepcopy(runtime)))
    for label,actual in [("missing",dict(list(runtime.items())[:-1])),("extra",{**runtime,"extra":{}}),("changed",{**runtime,"1":{}})]:
        reject("runtime "+label,lambda actual=actual:c.runtime_match(runtime,actual),"runtime dependency identities")
    def exercise(failure=None):
        events=[]
        block=object()
        class Database:
            def getChip(self):
                events.append("chip")
                if failure=="chip":raise RuntimeError("chip sentinel")
                return SimpleNamespace(getBlock=lambda:block)
        db=Database()
        def create():
            events.append("create")
            if failure=="create":raise RuntimeError("create sentinel")
            return db
        def read(actual,path):
            assert actual is db;events.append("read")
            if failure=="read":raise RuntimeError("read sentinel")
        def destroy(actual):
            assert actual is db;events.append("destroy")
            if failure=="destroy":raise RuntimeError("destroy sentinel")
        def census(odb,actual,actual_block,partial):
            assert actual is db and actual_block is block
            events.append("census");partial["prefix"]="retained"
            if failure=="census":raise RuntimeError("census sentinel")
            return dict(all_net_count=143820,all_instance_count=153130)
        report=dict(terminal_errors=[],complete_census=False,database_destroyed=False)
        caught=None
        with patch.object(native,"fingerprint",return_value=c.INPUT):
            try:native.inspect_database(SimpleNamespace(dbDatabase=SimpleNamespace(create=create,destroy=destroy),read_db=read),Path("/fixture.odb"),report,census)
            except RuntimeError as exc:caught=str(exc)
        assert events.count("destroy")==(0 if failure=="create"else 1)
        if failure in ("create","read","chip","census"):assert caught==failure+" sentinel"
        else:assert caught is None
        if failure=="destroy":assert report["terminal_errors"] and not report["database_destroyed"]
        elif failure!="create":assert report["database_destroyed"]
        if failure=="census":assert report["partial_census"]=={"prefix":"retained"}
        lifecycle.append(dict(case=failure or "complete",events=events,primary=caught,
            cleanup_errors=report["terminal_errors"],complete_census=report["complete_census"]))
    for failure in (None,"create","read","chip","census","destroy"):exercise(failure)
    assert len(positive)==4 and len(refused)==23 and len(lifecycle)==6
    print(json.dumps(dict(status="PASS_BUILT_ENGINE_RUNTIME_SOURCE_CONTROLS",positive_count=len(positive),
        refusal_count=len(refused),lifecycle_count=len(lifecycle),positive=positive,refusals=refused,
        lifecycle=lifecycle,protected_count=len(m["protected"]),native_objects_executed=False,
        physical_acceptance=False,observer_equivalence_qualified=False),sort_keys=True,indent=2))
if __name__=="__main__":main()
