#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0
"""Hosted source/runtime/publication controls only; never imports CAD or restores an archive."""
import argparse
import ast
import copy
import hashlib
import io
import json
import os
from pathlib import Path
import shlex
import shutil
import subprocess
import sys
import tarfile
import tempfile
import threading
import types
from unittest import mock

import cloud_cdr_v59_tail_access_physical as c
from cloud_verified_parts import JoinedParts

FIXTURE="docs/evidence/cdr-v59-tail-original-wire-fixture-20261026"

def gate():
    m=c.methods()
    assert os.environ.get("GITHUB_ACTIONS")=="true"
    assert os.environ.get("RUNNER_ENVIRONMENT")=="github-hosted"
    assert m["source_controls_authorized"] is True
    return m

def refuse(rows,name,call,kind=AssertionError):
    try:call()
    except kind as error:rows.append({"case":name,"rejected":True,"error":repr(error)})
    else:raise AssertionError("Accepted source-control fault "+name)

def physical_controls():
    gate();positives=[];refusals=[]
    saved=json.loads((c.ROOT/"docs/evidence/cdr-v59-cd-shunt-first-physical-result-20261025.json").read_text())
    baseline=saved["physical"]
    assert c.validate_physical(baseline) is True
    positives.append({"case":"actual_original_full_physical_report","historical_outer_status":saved["status"],
      "historical_failure_not_overwritten":True})
    mutations=[
      ("status",lambda x:x.update(status="UNKNOWN")),
      ("missing_DRC_category",lambda x:x["steps"]["drc"]["measurement"].update(category_count=559)),
      ("nonzero_DRC_marker",lambda x:x["steps"]["drc"]["measurement"].update(markers=1)),
      ("DRC_status",lambda x:x["steps"]["drc"]["measurement"].update(status="FAIL")),
      ("missing_v59_length_fault",lambda x:x["steps"].pop("v59_old_length")),
      ("accepted_v59_length_fault",lambda x:x["steps"]["v59_old_length"].update(status="PASS")),
      ("deep_device_census",lambda x:x["steps"]["lvs"]["audit"]["circuits"][0].update(layout_devices_recursive=499)),
      ("flat_device_census",lambda x:x["steps"]["lvs_flat"]["audit"]["circuits"][0].update(schematic_devices_recursive=499)),
      ("extraction_diagnostic",lambda x:x["steps"]["lvs"]["audit"].update(extraction_diagnostics=["fixture"])),
      ("comparison_status",lambda x:x["steps"]["lvs_flat"]["audit"].update(circuit_status_counts={"Mismatch":1})),
      ("unexpected_step",lambda x:x["steps"].update(extra={"status":"REJECTED_EXPECTED_FAULT"})),
    ]
    for name,change in mutations:
        value=copy.deepcopy(baseline);change(value);refuse(refusals,name,lambda:c.validate_physical(value))
    with tempfile.TemporaryDirectory(prefix="cdr-tail-driver-") as folder:
        root=Path(folder);out=root/"out";work=out/"candidate";work.mkdir(parents=True)
        with mock.patch.object(c,"OUT",out),mock.patch.object(c,"WORK",work):
            derived=c.derive_methods()
            for name,row in derived.items():
                text=(work/"methods"/name).read_text()
                for change in reversed(row["exact_qualified_reversible_changes"]):
                    assert text.count(change["after"])==change["count"]
                    text=text.replace(change["after"],change["before"])
                assert text==(c.ROOT/row["original"]).read_text()
            positives.append({"case":"actual_four_method_derivations_reverse_exact","methods":derived})
            for filename in ("graph.json","locations.json","anchors.json"):
                old=json.loads((c.ROOT/FIXTURE/filename).read_text());fresh={"inputs":{}}
                for name,value in old["inputs"].items():
                    rel=Path(name).relative_to(c.source.ANALYSIS);path=work/rel;path.parent.mkdir(parents=True,exist_ok=True)
                    path.write_bytes(("HOSTED_PATH_ONLY_FIXTURE "+str(rel)+"\n").encode())
                    fresh["inputs"][str(path)]={"bytes":path.stat().st_size,"sha256":c.sha(path)} if isinstance(value,dict) else c.sha(path)
                assert c.wire_inputs(old,fresh)
                positives.append({"case":"actual_"+filename+"_input_path_binding","paths":len(fresh["inputs"]),"synthetic_file_bytes":True})
                if filename=="graph.json":
                    sample=copy.deepcopy(fresh);first=next(iter(sample["inputs"]))
                    sample["inputs"][first]["sha256"]="0"*64
                    refuse(refusals,"wire_wrong_digest",lambda:c.wire_inputs(old,sample))
                    sample=copy.deepcopy(fresh);sample["inputs"][first]["bytes"]+=1
                    refuse(refusals,"wire_wrong_bytes",lambda:c.wire_inputs(old,sample))
                    sample=copy.deepcopy(fresh);sample["inputs"][next(iter(old["inputs"]))]=sample["inputs"].pop(first)
                    refuse(refusals,"wire_old_capsule_path",lambda:c.wire_inputs(old,sample))
                    sample=copy.deepcopy(fresh);sample["inputs"].pop(first)
                    refuse(refusals,"wire_missing_input",lambda:c.wire_inputs(old,sample))
                    path=Path(first);original=path.read_bytes();path.unlink();target=root/"external";target.write_bytes(original);path.symlink_to(target)
                    refuse(refusals,"wire_symlink_input",lambda:c.wire_inputs(old,fresh));path.unlink();path.write_bytes(original)
            trace=root/"trace";trace.mkdir();sup=types.SimpleNamespace(TRACE=trace)
            result={"commands":[],"storage":[]};calls=[]
            def command(argv,label,seconds,cwd):
                assert cwd==c.ROOT and seconds==c.PHASE_SECONDS[label]
                assert "GH_TOKEN" not in os.environ and "GITHUB_TOKEN" not in os.environ
                calls.append(label)
                record={"returncode":0,"supervision_failure":None,"process_group_cleanup":{"remaining_live":[]}}
                for stream,raw in (("stdout",b"exact\n"),("stderr",bytes([255,0]))):
                    (trace/(label+"."+stream)).write_bytes(raw)
                    record[stream+"_bytes"]=len(raw);record[stream+"_sha256"]=hashlib.sha256(raw).hexdigest()
                c.write(trace/(label+".command.json"),record)
            sup.supervised=command
            with mock.patch.object(c,"storage",return_value={"fixture":True}),mock.patch.dict(os.environ,{"GH_TOKEN":"FIXTURE","GITHUB_TOKEN":"FIXTURE"}):
                for label in c.PHASE_SECONDS:
                    c.execute(sup,result,["EXPLICIT_FAKE_SUPERVISOR"],label,True)
                    assert os.environ["GH_TOKEN"]==os.environ["GITHUB_TOKEN"]=="FIXTURE"
                    positives.append({"case":"actual_execute_"+label,"fake_supervisor_only":True})
                before=len(calls);refuse(refusals,"unknown_command_before_launch",lambda:c.execute(sup,result,[],"unknown",True));assert len(calls)==before
                label=next(iter(c.PHASE_SECONDS))
                for name,change in [
                    ("nonzero_return",lambda q:q.update(returncode=7)),
                    ("supervision_failure",lambda q:q.update(supervision_failure="fixture")),
                    ("live_descendant",lambda q:q["process_group_cleanup"].update(remaining_live=[123])),
                    ("wrong_stdout_bytes",lambda q:q.update(stdout_bytes=1)),
                    ("wrong_stderr_digest",lambda q:q.update(stderr_sha256="0"*64)),
                ]:
                    def corrupt(argv,label,seconds,cwd,change=change):
                        command(argv,label,seconds,cwd);p=trace/(label+".command.json");q=json.loads(p.read_text());change(q);c.write(p,q)
                    sup.supervised=corrupt;refuse(refusals,name,lambda:c.execute(sup,result,[],label,True))
    # Run the actual main finally path with explicit non-native qualification failure.
    # Full capsule copying remains real; only acquisition, reservation and process creation are stubbed.
    for integrity_failure in (False,True):
        with tempfile.TemporaryDirectory(prefix="cdr-tail-finally-") as folder:
            root=Path(folder);out=root/"out";capsule=root/"capsule";transport=root/"publication"
            sup=types.SimpleNamespace(TRACE=out/"supervision",ACTIVE=None,STOP=threading.Event(),
                interrupted=lambda *a:None,heartbeat=lambda:None,stop_process=lambda p:{"remaining_live":[]})
            injected=RuntimeError("EXACT_SYNTHETIC_QUALIFICATION_FAILURE")
            def acquisition(*a):
                capsule.mkdir();(capsule/"partial.bin").write_bytes(b"actual partial evidence");raise injected
            def integrity(*a):
                if integrity_failure:raise ValueError("EXACT_SYNTHETIC_INTEGRITY_FAILURE")
                return {"fixture":True}
            observed=[]
            def publish_failure(result):
                assert (out/"source-capsule/partial.bin").read_bytes()==b"actual partial evidence"
                assert result["native_physical_qualification_passed"] is False
                assert result["error"]==repr(injected)
                assert result["status"]==("FAIL_ORIGINAL_CAPSULE_INTEGRITY" if integrity_failure else "FAIL_ADDITIVE_TAIL_WIRE_PHYSICAL")
                observed.append(copy.deepcopy(result))
            with mock.patch.multiple(c,OUT=out,WORK=out/"candidate",TRANSPORT=transport),mock.patch.object(c.source,"CAPSULE",capsule),\
                 mock.patch.object(c,"authorize",return_value={"protected_sha256":{c.runtime.SAMPLER:c.runtime.SAMPLER_SHA}}),\
                 mock.patch.object(c.frozen,"precreated",return_value={"fixture":True}),mock.patch.object(c,"storage",return_value={"fixture":True}),\
                 mock.patch.object(c.runtime,"supervisor",return_value=sup),mock.patch.object(c,"qualify",side_effect=acquisition),\
                 mock.patch.object(c.source,"verify_saved_inputs",side_effect=integrity),mock.patch.object(c,"publish",side_effect=publish_failure),\
                 mock.patch.object(sys,"argv",["explicit-main-fixture"]),mock.patch.object(c.publication,"emit"):
                refuse([], "main_failure_stays_rejected",c.main)
            assert len(observed)==1 and observed[0]["terminal_cleanup"]["remaining_live"]==[]
            positives.append({"case":"actual_main_preserves_partial_after_"+("integrity_failure" if integrity_failure else "qualification_failure"),
              "status":observed[0]["status"],"qualification_stubbed":True,"capsule_copy_real":True})
    assert len(positives)==17 and len(refusals)==22
    return {"status":"PASS_TAIL_PHYSICAL_DRIVER_SOURCE_CONTROLS_ONLY","positives":positives,"refusals":refusals,
      "positive_count":17,"refusal_count":22,"native_executed":False,"physical_accepted":False}

def runtime_controls():
    m=gate()
    with tempfile.TemporaryDirectory(prefix="cdr-tail-runtime-") as folder:
        root=Path(folder)
        owned=c.runtime.supervisor(c.ROOT,root/"out",root/"supervision",gate,m["protected_sha256"][c.runtime.SAMPLER])
        owned.controls()
        supervisor=json.loads((owned.TRACE/"controls.json").read_text())
        assert len(supervisor["controls"])==13
        probe=c.runtime.launcher(c.ROOT,gate,m["protected_sha256"][c.runtime.PROBE])
        actual_write=probe.admission.write;records=[]
        def persisted(path,value):
            actual_write(path,value)
            assert json.loads(path.read_text())==value and not path.with_suffix(path.suffix+".tmp").exists()
            records.append({"accepted":value["accepted"],"status":value["status"],"sha256":c.sha(path),
              "terminal_before_collection":value["terminal_group_verified_before_stream_collection"]})
        probe.admission.write=persisted
        launcher=probe.controls()
        assert len(records)==11 and sum(r["accepted"] for r in records)==2 and all(r["terminal_before_collection"] for r in records)
        # Reproduce the exact draft missing dependency by removing only its writer.
        app=root/"old-namespace";app.write_text("#!/bin/sh\nexit 127\n");app.chmod(0o700)
        del probe.admission.write
        try:probe.probe(app,probe.digest(app),root/"old-missing-write")
        except AttributeError as error:
            assert str(error)=="'types.SimpleNamespace' object has no attribute 'write'"
            old={"error":repr(error),"stdout_saved":(root/"old-missing-write/stdout.bin").is_file(),
                 "stderr_saved":(root/"old-missing-write/stderr.bin").is_file(),"result_missing":not (root/"old-missing-write/result.json").exists()}
            assert old["stdout_saved"] and old["stderr_saved"] and old["result_missing"]
        else:raise AssertionError("Original missing writer was accepted")
        finally:probe.admission.write=actual_write
        fixed=probe.probe(app,probe.digest(app),root/"fixed-exit127")
        assert fixed["accepted"] is False and fixed["returncode"]==127
        assert json.loads((root/"fixed-exit127/result.json").read_text())==fixed
    return {"status":"PASS_QUALIFIED_RUNTIME_AND_WRITER_DEPENDENCY_CONTROLS","supervisor":supervisor,
       "launcher":launcher,"all11_launcher_results_saved":records,"original_missing_writer_reproduced":old,
       "corrected_exit127_saved":fixed,"actual_appimage_executed":False,"native_executed":False}

def publication_fixture(root,status,remote_fault=None,path_fault=None):
    out=root/"out";work=out/"candidate";transport=root/"publication";work.mkdir(parents=True)
    report={"status":status,"native_physical_qualification_passed":False,"accepted":False,"fixture":True}
    if status=="OVERSIZED_SYNTHETIC":report["retained_full_text"]="x"*(4*1024**2+1)
    c.write(out/"result.json",report);(out/".hidden").write_bytes(b"hidden");(out/"empty").touch()
    extra=[work/"result.json",work/"parent/physical/result.json",work/"native-planes.json",out/"full-topology-comparison.json",
       work/"wire/native05/result.json",work/"wire/device-locations01.json",work/"wire/anchors08.json"]
    for i,p in enumerate(extra):p.parent.mkdir(parents=True,exist_ok=True);c.write(p,{"fixture":True,"index":i,"accepted":False})
    original={str(p.relative_to(out)):{"bytes":p.stat().st_size,"sha256":c.sha(p)} for p in out.rglob("*") if p.is_file()}
    if path_fault=="root_link":
        other=root/"real";out.rename(other);out.symlink_to(other,target_is_directory=True)
    elif path_fault=="root_file":
        shutil.rmtree(out);out.write_text("not directory")
    elif path_fault=="result_link":
        p=out/"result.json";body=p.read_bytes();p.unlink();target=root/"outside";target.write_bytes(body);p.symlink_to(target)
    elif path_fault=="descendant_link":(out/"link").symlink_to(out/".hidden")
    elif path_fault=="missing_result":(out/"result.json").unlink()
    env={"GITHUB_ACTIONS":"true","GITHUB_REPOSITORY":"Melihakbulut221/nssoc","GITHUB_RUN_ID":"123456","GITHUB_RUN_ATTEMPT":"1","GITHUB_SHA":"a"*40}
    tag,head=c.release.context(c.GROUP,env)
    info={"id":1,"tag_name":tag,"target_commitish":head,"draft":False,"prerelease":True,"assets":[]}
    ref={"ref":"refs/tags/"+tag,"object":{"type":"commit","sha":head}}
    if remote_fault=="draft":info["draft"]=True
    elif remote_fault=="prerelease":info["prerelease"]=False
    elif remote_fault=="target":info["target_commitish"]="b"*40
    elif remote_fault=="tag":ref["object"]["sha"]="b"*40
    elif remote_fault=="annotated_tag":ref["object"]["type"]="tag"
    elif remote_fault=="ref":ref["ref"]="refs/heads/wrong"
    calls=[];injected=ValueError("EXACT_INJECTED_PUBLISHER_TRANSPORT_FAILURE")
    def read(path,missing=False):
        assert path in ("releases/tags/"+tag,"git/ref/tags/"+tag)
        if path.startswith("releases/"):return None if remote_fault=="absent" else info
        return ref
    def upload(argv,*args,**kwargs):
        assert argv[:4]==["gh","release","upload",tag] and argv[5:]==["-R","Melihakbulut221/nssoc"]
        p=Path(argv[4]);assert p.parent==transport and p.is_file()
        calls.append(argv)
        if remote_fault=="exception":raise injected
        entry={"name":p.name,"id":len(info["assets"])+1,"size":p.stat().st_size,
          "digest":"sha256:"+c.sha(p),"browser_download_url":"https://example.invalid/"+p.name}
        if remote_fault=="uploaded_size":entry["size"]+=1
        if remote_fault=="uploaded_digest":entry["digest"]="sha256:"+"0"*64
        info["assets"].append(entry)
        return subprocess.CompletedProcess(argv,0)
    previous=c.publisher.release
    with mock.patch.multiple(c,OUT=out,WORK=work,TRANSPORT=transport),mock.patch.dict(os.environ,env),\
         mock.patch.object(c.shutil,"disk_usage",return_value=types.SimpleNamespace(free=100*1024**3)),\
         mock.patch.object(c.release,"api",side_effect=read),mock.patch.object(c.publisher.subprocess,"run",side_effect=upload):
        try:proof=c.publish(report)
        except BaseException as error:
            assert c.publisher.release is previous
            if remote_fault=="exception":assert error is injected and len(calls)==1
            raise
        assert c.publisher.release is previous
        assert proof["status"]=="PASS_FULL_PHYSICAL_EVIDENCE_PUBLISHED"
        assert json.loads((out/"result.json").read_text())==report
        manifest=next(transport.glob("*.parts.json"));packed=json.loads(manifest.read_text())
        parts=[transport/row["name"] for row in packed["parts"]]
        restored={}
        with io.BufferedReader(JoinedParts(parts)) as stream,tarfile.open(fileobj=stream,mode="r|gz") as archive:
            for member in archive:
                if member.isdir():continue
                assert member.isfile()
                relative=Path(member.name).relative_to(out.name).as_posix()
                body=archive.extractfile(member).read()
                assert relative not in restored
                restored[relative]={"bytes":len(body),"sha256":hashlib.sha256(body).hexdigest()}
        assert restored==original
        assert len(calls)==len(proof["assets"])==len(parts)+9
        before=len(calls)
        # Real qualified publisher must reuse a verified identical remote asset.
        c.publisher.release=c.publication.only_reserved(c.GROUP,os.environ,c.release.api)
        try:again=c.publisher.publish(transport/proof["assets"][0]["name"],tag)
        finally:c.publisher.release=previous
        assert again==proof["assets"][0] and len(calls)==before
        return {"status":status,"complete_original_files":len(original),"parts":len(parts),"assets":len(proof["assets"]),
          "complete_tar_roundtrip":True,"existing_identical_asset_reused":True,"original_result_sha256":original["result.json"]["sha256"]}

def publication_controls():
    gate();positives=[];refusals=[]
    for status in ("FAIL_ADDITIVE_TAIL_WIRE_PHYSICAL","RUNNING_ADDITIVE_TAIL_WIRE_PHYSICAL","OVERSIZED_SYNTHETIC"):
        with tempfile.TemporaryDirectory(prefix="cdr-tail-publication-") as folder:positives.append(publication_fixture(Path(folder),status))
    for name in ("draft","prerelease","target","tag","annotated_tag","ref","absent","uploaded_size","uploaded_digest","exception"):
        with tempfile.TemporaryDirectory(prefix="cdr-tail-publication-fault-") as folder:
            kind=ValueError if name=="exception" else RuntimeError if name.startswith("uploaded_") else AssertionError
            refuse(refusals,name,lambda:publication_fixture(Path(folder),"FAIL_FIXTURE",remote_fault=name),kind)
    for name in ("root_link","root_file","result_link","descendant_link","missing_result"):
        with tempfile.TemporaryDirectory(prefix="cdr-tail-publication-path-") as folder:
            refuse(refusals,name,lambda:publication_fixture(Path(folder),"FAIL_FIXTURE",path_fault=name),
                FileNotFoundError if name=="missing_result" else AssertionError)
    assert len(positives)==3 and len(refusals)==15
    return {"status":"PASS_ACTUAL_TAIL_PUBLISHER_AND_PACK_CONTROLS","positives":positives,"refusals":refusals,
      "positive_count":3,"refusal_count":15,"real_qualified_publisher":True,"remote_transport_explicitly_mocked":True,
      "network_accessed":False,"native_executed":False,"inherited_publication_controls":c.publication.publication_controls()}

def main():
    parser=argparse.ArgumentParser();parser.add_argument("--section",choices=("physical","runtime","publication"),required=True)
    parser.add_argument("--output",type=Path,required=True);args=parser.parse_args()
    args.output.parent.mkdir(parents=True,exist_ok=True)
    result={"status":"RUNNING_TAIL_SOURCE_CONTROLS","section":args.section,"native_executed":False}
    c.write(args.output,result)
    try:result={"physical":physical_controls,"runtime":runtime_controls,"publication":publication_controls}[args.section]()
    except BaseException as error:
        result.update(status="FAIL_TAIL_SOURCE_CONTROLS",error=repr(error));c.write(args.output,result);raise
    c.write(args.output,result);c.publication.emit(args.output,"CDR_TAIL_"+args.section.upper()+"_CONTROLS")

if __name__=="__main__":main()
