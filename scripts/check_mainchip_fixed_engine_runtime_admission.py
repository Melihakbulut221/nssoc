#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0
"""Hosted source-only admission controls; actual metadata, synthetic archive bytes."""
import argparse
import copy
import hashlib
import io
import json
from pathlib import Path
import sys
import tarfile
import tempfile
from unittest.mock import patch
sys.path.insert(0, str(Path(__file__).resolve().parent))
import mainchip_fixed_engine_runtime_admission as a


def controls():
    positives=[];refusals=[]
    def reject(name, action, reason):
        try:action()
        except (ValueError, AssertionError, KeyError, TypeError) as exc:
            assert reason in str(exc), (name,repr(exc),reason)
            refusals.append(dict(name=name,error=repr(exc)))
        else:raise AssertionError("Admission accepted changed evidence: "+name)
    guard=a.source_guard();assert guard["complete_members"]==100 and guard["direct_JSON_count"]==20
    assert guard["runtime_qualified"]is False and guard["native_assets_acquired"]is False
    positives.append("actual_source_guard_full26_reports_and920_inherited_pins")
    d=a.read_reports();expected=a.expected_engine()
    assert expected["files"]==d["complete-native-restore-map.json"] and expected["files"]["openroad"]==a.ENGINE
    assert len(expected["files"])==100 and len(expected["runtime"])==104
    assert a.engine_extract is a.frozen.engine_extract and a.runtime_match is a.frozen.runtime_match
    positives.append("actual100_member_metadata_projection_and_unchanged_helpers")
    envelope=a.engine_envelope(d["run.json"],d["jobs.json"],d["release.json"],d["tag-ref.json"],d["release.json"])
    assert envelope["source"]==a.SOURCE and envelope["original_build_conclusion"]=="success" and envelope["runtime_qualified"]is False
    positives.append("actual3_job21_asset_producer_envelope")
    assert a.runtime_match(d["direct/runtime-dependencies.json"],d["direct/runtime-dependencies.json"])["count"]==104
    positives.append("actual104_record_identity_only_not_runtime_execution")
    def changed_report(name, change, reason):
        value=copy.deepcopy(d);change(value);reject(name,lambda:a.validate_reports(value),reason)
    cases=(
      ("missing required report",lambda x:x.pop("direct/source-before.json"),"complete required"),
      ("receipt source",lambda x:x["receipt.json"].update(source="0"*40),"terminal receipt producer"),
      ("receipt runtime acceptance",lambda x:x["receipt.json"].update(actual_ODB_runtime_qualified=True),"cannot transfer runtime"),
      ("missing current member",lambda x:x["complete-native-restore-map.json"].pop("openroad"),"exact99plus1"),
      ("raw outputs binding",lambda x:x["complete-native-restore-map.json"]["outputs.json"].update(sha256="0"*64),"raw outputs.json"),
      ("output source",lambda x:x["direct/outputs.json"].update(source="0"*40),"output producer scope"),
      ("archive digest",lambda x:x["direct/parts.json"]["archive"].update(sha256="0"*64),"exact current engine archive"),
      ("library digest",lambda x:next(iter(x["direct/runtime-dependencies.json"].values())).update(sha256="0"*64),"exact104"),
      ("library count",lambda x:x["direct/runtime-dependencies.json"].pop(next(iter(x["direct/runtime-dependencies.json"]))),"exact104"),
      ("failed host",lambda x:x["direct/host-result.json"].update(status="FAIL_ENGINE_BUILD"),"actual complete build result"),
      ("failed inner",lambda x:x["direct/inner-result.json"].update(status="FAIL_ENGINE_BUILD"),"inner build failure"),
      ("wrong ELF",lambda x:x["direct/inner-result.json"]["binary"].update(sha256="0"*64),"actual complete build result"),
      ("native acceptance transfer",lambda x:x["direct/host-result.json"].update(runtime_qualified=True),"new build scope only"),
      ("command nonzero",lambda x:x["direct/inner-result.json"]["commands"][0].update(returncode=1),"actual build command failure"),
      ("command timeout",lambda x:x["direct/host-result.json"]["commands"][0].update(timed_out=True),"actual build command failure"),
      ("wrong command identity",lambda x:x["direct/inner-result.json"]["commands"][0]["argv"].append("--changed"),"exact build command identity"),
      ("earlier progress corruption",lambda x:x["direct/inner-result.json"]["available_outputs"]["host-progress.json"].update(sha256="0"*64),"partial result output inventory"),
      ("cleanup failure",lambda x:x["direct/host-result.json"]["terminal_actions"][0].update(completed=False),"actual build cleanup failure"),
      ("partial output hash",lambda x:x["direct/host-result.json"]["available_outputs"]["openroad"].update(sha256="0"*64),"partial result output inventory"),
      ("source after drift",lambda x:x["direct/source-after.json"]["src/drt/src/dr/FlexDR_init.cpp"].update(sha256="0"*64),"complete unchanged compiled source"),
      ("old upstream binding",lambda x:x["direct/source-derivation.json"].update(upstream_commit="0"*40),"exact observer plus3-line"),
      ("LTO configuration",lambda x:x["direct/build-configuration.json"]["cache_flags"].update(LINK_TIME_OPTIMIZATION=["BOOL","ON"]),"actual full engine build configuration"),
      ("controls source",lambda x:x["direct/fixed-engine-controls.json"].update(current_source="0"*40),"actual source controls producer"),
      ("controls synthetic scope",lambda x:x["direct/fixed-engine-controls.json"].update(actual_engine_compilation=True),"synthetic source controls scope"),
      ("new controls count",lambda x:x["direct/fixed-engine-controls.json"]["publication"].update(count=6),"source controls counts"),
      ("reservation release",lambda x:x["direct/release-reservation.json"].update(release_id=427111201),"producer reserved release ID"),
      ("publication source failure",lambda x:x["direct/publication-availability.json"].update(source_integrity_validated=False),"publication source/scope"),
      ("publication member",lambda x:x["direct/direct-publication-plan.json"]["files"][0].update(archive_member="other.json"),"publication plan member join"),
      ("method runtime authority",lambda x:x["direct/method.json"].update(native_probe_authorized=True),"original build method is not runtime authority"),
    )
    for name, change, reason in cases:changed_report(name,change,reason)
    changed=copy.deepcopy(d);changed["direct/outputs.json"]["files"]["openroad"]["sha256"]="0"*64
    changed["complete-native-restore-map.json"]["openroad"]["sha256"]="0"*64
    reject("coherently changed member hash",lambda:a.validate_reports(changed),"exact current engine member identities")
    old=a.frozen.expected_engine(a.ROOT)
    assert len(old["files"])==95
    reject("actual historical95 member map",lambda:a.validate_inventory(d["direct/outputs.json"],old["files"]),"exact99plus1")
    def live_case(name,change,reason):
        r,j,rel,tag=(copy.deepcopy(d[p])for p in ("run.json","jobs.json","release.json","tag-ref.json"))
        change(r,j,rel,tag)
        reject(name,lambda:a.engine_envelope(r,j,rel,tag,d["release.json"]),reason)
    live=(
      ("run source",lambda r,j,s,t:r.update(head_sha="0"*40),"actual new build run"),
      ("run ID",lambda r,j,s,t:r.update(id=40756287268),"actual new build run"),
      ("run attempt",lambda r,j,s,t:r.update(run_attempt=2),"actual new build run"),
      ("failed run",lambda r,j,s,t:r.update(conclusion="failure"),"actual new build run"),
      ("wrong workflow",lambda r,j,s,t:r.update(path=".github/workflows/mainchip-internal-witness-engine-build.yml"),"actual new build workflow"),
      ("missing job",lambda r,j,s,t:j["jobs"].pop(),"complete3"),
      ("failed job",lambda r,j,s,t:j["jobs"][0].update(conclusion="failure"),"failed build job"),
      ("failed publication step",lambda r,j,s,t:j["jobs"][2]["steps"][4].update(conclusion="failure"),"job/step identities"),
      ("missing asset",lambda r,j,s,t:s["assets"].pop(),"complete21"),
      ("asset digest",lambda r,j,s,t:s["assets"][0].update(digest="sha256:"+"0"*64),"live actual build release assets"),
      ("asset size",lambda r,j,s,t:s["assets"][0].update(size=s["assets"][0]["size"]+1),"live actual build release assets"),
      ("asset duplicate",lambda r,j,s,t:s["assets"].__setitem__(1,copy.deepcopy(s["assets"][0])),"duplicate build asset"),
    )
    for name,change,reason in live:live_case(name,change,reason)
    method=a.methods();prior=a.core.decode(a.core.secure_file(a.ROOT,a.PRIOR).read_bytes())
    env=dict(GITHUB_ACTIONS="true",RUNNER_ENVIRONMENT="github-hosted",RUNNER_OS="Linux",
        GITHUB_REPOSITORY="Melihakbulut221/nssoc",GITHUB_EVENT_NAME="workflow_dispatch",GITHUB_RUN_ATTEMPT="1",
        GITHUB_REF="refs/heads/"+a.BRANCH,GITHUB_RUN_ID="123456",GITHUB_SHA="a"*40)
    enabled=copy.deepcopy(method);enabled["source_controls_authorized"]=True
    assert a.validate_context(env,enabled,"a"*40)["native_authorized"]is False
    for key,value,reason in (
        ("GITHUB_ACTIONS","false","hosted source-only"),
        ("RUNNER_ENVIRONMENT","self-hosted","hosted source-only"),
        ("GITHUB_REPOSITORY","other/repository","hosted source-only"),
        ("GITHUB_EVENT_NAME","push","first-manual"),
        ("GITHUB_RUN_ATTEMPT","2","first-manual"),
        ("GITHUB_REF","refs/heads/main","first-manual"),
        ("GITHUB_SHA","b"*40,"exact admission source/run"),
        ("GITHUB_RUN_ID","0","exact admission source/run")):
        bad=dict(env);bad[key]=value
        reject("hosted context "+key,lambda:a.validate_context(bad,enabled,"a"*40),reason)
    disabled=copy.deepcopy(enabled);disabled["source_controls_authorized"]=False
    reject("disabled source controls",lambda:a.validate_context(env,disabled,"a"*40),"source controls enabled")
    for enabled in (False,True):
        baseline=copy.deepcopy(method);baseline["source_controls_authorized"]=enabled
        a.validate_method(baseline,prior)
        bad=copy.deepcopy(baseline);bad["source_controls_authorized"]=int(enabled)
        reject("typed source-only authority "+str(enabled),lambda:a.validate_method(bad,prior),"typed source controls")
    for flag in a.AUTH_FALSE:
        bad=copy.deepcopy(method);bad[flag]=True
        reject("forbidden authority "+flag,lambda:a.validate_method(bad,prior),"no execution or acceptance")
    for name,change,reason in (
        ("missing new source pin",lambda x:x["protected"].pop(a.NEW_FILES[0]),"required new admission source pins"),
        ("changed inherited pin",lambda x:x["protected"].update({next(iter(prior["protected"])):"0"*64}),"inherited source pin changed"),
        ("qualified old engine",lambda x:x.update(qualified_engine={"sha256":"1e79"}),"no qualified engine transfer")):
        bad=copy.deepcopy(method);change(bad);reject(name,lambda:a.validate_method(bad,prior),reason)
    with tempfile.TemporaryDirectory() as temp:
        damaged=Path(temp)/"host.json";damaged.write_bytes(a.core.secure_file(a.ROOT,a.PREFIX+"direct/host-result.json").read_bytes()+b" ")
        original=a.core.secure_file
        def files(root,path):
            return damaged if path==a.PREFIX+"direct/host-result.json" else original(root,path)
        with patch.object(a.core,"secure_file",side_effect=files):
            reject("real report-byte corruption",lambda:a.read_reports(),"immutable producer report: direct/host-result.json")
    archive=synthetic_archive_controls(reject)
    positives.append("actual_frozen_extractor_on_explicit_synthetic_bytes")
    return dict(status="PASS_FIXED_ENGINE_RUNTIME_INPUT_SOURCE_CONTROLS",positive_count=len(positives),positive_cases=positives,
                refusal_count=len(refusals),refusals=refusals,source_guard=guard,synthetic_archive=archive,
                actual_metadata_validated=True,actual_native_archive_restored=False,actual_runtime_probe_executed=False,
                new_ELF_executed=False,native_payload_acquired=False,runtime_qualified=False,
                physical_acceptance=False,original920_sources_unchanged=True)


def synthetic_archive_controls(reject):
    # These are invented fixture bytes, never the engine/native archive.
    payloads={"openroad":b"synthetic-not-an-ELF", "empty.stderr":b"", "note.json":b"{}"}
    expected={n:dict(bytes=len(b),sha256=hashlib.sha256(b).hexdigest())for n,b in payloads.items()}
    def packed(mode):
        stream=io.BytesIO()
        with tarfile.open(fileobj=stream,mode="w:gz")as archive:
            for name,raw in payloads.items():
                if mode=="missing"and name=="note.json":continue
                selected="../escape"if mode=="path"and name=="note.json"else name
                data=b"X"*len(raw)if mode=="hash"and name=="openroad"else raw
                info=tarfile.TarInfo(selected);info.size=len(data)
                if mode=="link"and name=="note.json":info.type=tarfile.SYMTYPE;info.linkname="openroad";info.size=0
                archive.addfile(info,io.BytesIO(data))
                if mode=="duplicate"and name=="note.json":archive.addfile(info,io.BytesIO(data))
        return stream.getvalue()
    with tempfile.TemporaryDirectory()as temp:
        root=Path(temp);result=a.engine_extract(io.BytesIO(packed("valid")),root/"valid",expected)
        assert result["all_files"]==expected and result["all_regular_members_verified"]is True
        assert (root/"valid/openroad").read_bytes()==payloads["openroad"]
        assert not(root/"valid/empty.stderr").exists()and not(root/"valid/note.json").exists()
        for mode,reason in (("missing","missing archive member"),("hash","changed archive member"),
                            ("path","archive path"),("link","nonregular archive member"),("duplicate","duplicate archive member")):
            reject("synthetic archive "+mode,lambda mode=mode:a.engine_extract(io.BytesIO(packed(mode)),root/mode,expected),reason)
        reject("synthetic occupied destination",lambda:a.engine_extract(io.BytesIO(packed("valid")),root/"valid",expected),"fresh extraction destination")
    return dict(synthetic_only=True,actual_engine_archive_acquired=False,fixture_regular_members=3,
                selected_fixture_members=["openroad"],empty_fixture_member_verified=True,refusal_count=6)


def main():
    p=argparse.ArgumentParser();p.add_argument("--output",type=Path);args=p.parse_args()
    authority=a.authorize();result=controls();result["current_context"]=authority;raw=json.dumps(result,sort_keys=True,indent=2)+"\n"
    if args.output:
        args.output.parent.mkdir(parents=True,exist_ok=True);args.output.write_text(raw)
    else:print(raw,end="")
    return 0

if __name__=="__main__":raise SystemExit(main())
