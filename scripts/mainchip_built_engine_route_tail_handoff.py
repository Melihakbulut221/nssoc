#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0
"""Complete route-only workspace handoff and source-bound audit restoration."""
import json
import os
from pathlib import Path
import re
import shutil
import tarfile
import mainchip_built_engine_route_tail_contract as c
from mainchip_built_engine_runtime_contract import canonical
from mainchip_witness_engine_build import fingerprint
import wait_cloud_tested_source_release as reservation

def route_records(host,inner,case,request):
    source,mode,run=request["source"],request["mode"],request["run_id"]
    c.require(request["stage"]=="route" and mode in c.MODES,"route request")
    for row in (host,case):
        c.require(row["source"]==source and row["mode"]==mode and row["stage"]=="route","route identity")
        c.require(row["physical_acceptance"] is False and not row["terminal_errors"],"route terminal errors/scope")
    c.require(host["status"]=="PASS_OWNED_ROUTE_STAGE_DIAGNOSTIC","route host completion")
    state=host["container_terminal"]["State"]
    c.require(not state["Running"] and not state["OOMKilled"] and state["ExitCode"]==0 and not state["Error"],"route container")
    c.require(inner["status"]=="PASS_BUILT_ELF_ACTUAL_ROUTE_STAGE"
        and inner["stage"]=="route" and not inner["terminal_errors"],"route inner completion")
    c.require([x["label"] for x in inner["commands"]]==["version","ldd","tcl-smoke","route-stage"]
        and all(x["returncode"]==0 and not x["timed_out"] for x in inner["commands"]),"route inner command")
    c.require(case["status"]=="PASS_ROUTE_ONLY_AWAITING_ORIGINAL_AUDITS" and case["complete_route"] is True
        and case["run_id"]==run and case["engine"]==c.ENGINE,"route body completion")
    c.require(case["prefix_source"]==c.PREFIX_SOURCE and case["prefix_run"]==c.PREFIX_RUN,"route frozen prefix")
    c.require(len(case["commands"])==1,"one actual route attempt")
    command=case["commands"][0]
    c.require(command["label"]==c.PHASES[0] and command["argv"]==c.command(c.PHASES[0])
        and command["returncode"]==0 and command["requested_timeout_seconds"]==14400,"route command")
    c.require(command["supervision_failure"] is None and command["memory_read_error"] is None
        and command["process_group_cleanup"]["remaining_live"]==[],"route owned process completion")
    c.require(command["maximum_group_rss_kib"]==c.LIMITS["max_group_rss_kib"]
        and command["minimum_available_kib"]==c.LIMITS["min_available_kib"],"route original resource guards")
    c.require(case["route_log"]["single_returned_attempt"] is True
        and case["route_log"]["sha256"]==command["stdout_sha256"]
        and case["route_log"]["bytes"]==command["stdout_bytes"],"original returned route log")
    c.require(set(case["route_outputs"])=={"routed-fixed.odb","routed-fixed.def","fixed-routing.drc"},"route output census")
    c.require(case["timing_accepted"] is False and case["full_phy_accepted"] is False,"route no acceptance")
    return True

def route_projection(files):
    # Host transport/daemon records remain in the complete handoff archive. Every
    # native input and route output consumed by the audits retains its exact path.
    return {p:row for p,row in files.items()
        if not p.startswith("out/") or p.startswith(("out/work/","out/witness/"))}

def validate_manifest(inv,proof,case,request):
    c.require(inv["schema"]=="mainchip-complete-route-workspace-v1","handoff schema")
    c.require(inv["source"]==request["source"] and inv["mode"]==request["mode"]
        and inv["run_id"]==request["run_id"] and inv["stage"]=="route","handoff lineage")
    c.require(inv["engine"]==c.ENGINE and inv["input"]==c.INPUT
        and inv["prefix_source"]==c.PREFIX_SOURCE and inv["prefix_run"]==c.PREFIX_RUN,"handoff original identities")
    files=inv["files"]
    c.require(type(files) is dict and bool(files),"full handoff files")
    for p,row in files.items():
        canonical(p)
        c.require(type(row["bytes"]) is int and row["bytes"]>=0
            and re.fullmatch("[0-9a-f]{64}",row["sha256"]) is not None,"handoff file receipt")
    c.require(proof["status"]=="PASS_COMPLETE_ROUTE_HANDOFF_NOT_ROUTING_ACCEPTANCE"
        and proof["files"]==len(files) and proof["unpacked_bytes"]==sum(x["bytes"] for x in files.values()),
        "complete handoff census")
    c.require(proof["physical_acceptance"] is False and proof["source"]==request["source"]
        and proof["mode"]==request["mode"] and proof["run_id"]==request["run_id"],"handoff proof scope")
    c.require(files["engine/openroad"]==c.ENGINE and files["input.odb"]==c.INPUT,"handoff ELF/input files")
    for name,row in case["route_outputs"].items():
        c.require(files["out/work/"+name]==row,"handoff route output join")
    expected_witness=case["route_witness"]
    c.require(set(expected_witness)==({"imported.jsonl","before_dr.jsonl","after_dr.jsonl","after_writer.jsonl"}
        if request["mode"]=="on" else set()),"route witness census")
    actual={p.removeprefix("out/witness/"):row for p,row in files.items() if p.startswith("out/witness/")}
    c.require(actual==expected_witness,"route witness handoff join")
    for name in ("host-result.json","inner-result.json","case-result.json","method.json","route-request.json",
                 "frozen-prefix-inventory.json"):
        c.require("out/"+name in files,"missing route handoff record")
    c.require(proof["canonical_projection_files"]==len(route_projection(files)),"canonical projection census")
    return files

def freeze(work,out,root):
    work,out,root=Path(work),Path(out),Path(root)
    c.method(root);c.previous.method(work/"source")
    request=c.decode(c.secure_file(work,"request.json").read_bytes())
    host=c.decode(c.secure_file(out,"host-result.json").read_bytes())
    inner=c.decode(c.secure_file(out,"inner-result.json").read_bytes())
    case=c.decode(c.secure_file(out,"case-result.json").read_bytes())
    route_records(host,inner,case,request)
    original=c.decode(c.secure_file(work,"frozen-manifest.json").read_bytes())
    c.frozen_unchanged(work,original)
    c.require(not any((out/name).exists() for name in
        ("route-handoff.tar.gz","route-handoff-inventory.json","route-handoff.json")),"handoff already attempted")
    shutil.copyfile(c.secure_file(work,"request.json"),out/"route-request.json")
    shutil.copyfile(c.secure_file(work,"frozen-manifest.json"),out/"frozen-prefix-inventory.json")
    roots=[x for x in original["roots"] if x!="out/work"]+["tail-source","out"]
    files={}
    for relative in roots:
        path=work/relative
        c.require(path.exists() and not path.is_symlink(),"handoff root missing")
        for p in sorted(path.rglob("*")) if path.is_dir() else [path]:
            c.require(not p.is_symlink() and (p.is_file() or p.is_dir()),"handoff special entry")
            if p.is_file():
                key=p.relative_to(work).as_posix()
                c.require(key not in files,"duplicate handoff member");files[key]=fingerprint(p)
    total=sum(row["bytes"] for row in files.values())
    c.require(total<=c.LIMITS["archive_expanded_limit"],"handoff expanded budget")
    c.require(shutil.disk_usage(work).free>=total+2*1024**3,"handoff archive disk budget")
    inv=dict(schema="mainchip-complete-route-workspace-v1",source=request["source"],
        run_id=request["run_id"],mode=request["mode"],stage="route",canonical_root="/work",roots=roots,
        files=files,engine=c.ENGINE,input=c.INPUT,prefix_run=c.PREFIX_RUN,prefix_source=c.PREFIX_SOURCE,
        original_frozen_inventory=fingerprint(work/"frozen-manifest.json"),
        native_input_projection_complete=True,physical_acceptance=False)
    c.atomic_record(out/"route-handoff-inventory.json",inv)
    archive=out/"route-handoff.tar.gz"
    with tarfile.open(archive,"x:gz") as tar:
        for p in sorted(files):tar.add(work/p,arcname=p,recursive=False)
    c.frozen_unchanged(work,dict(files=files))
    proof=dict(status="PASS_COMPLETE_ROUTE_HANDOFF_NOT_ROUTING_ACCEPTANCE",
        source=request["source"],run_id=request["run_id"],mode=request["mode"],stage="route",
        archive=fingerprint(archive),inventory=fingerprint(out/"route-handoff-inventory.json"),
        files=len(files),unpacked_bytes=total,canonical_projection_files=len(route_projection(files)),
        physical_acceptance=False,observer_equivalence_qualified=False)
    validate_manifest(inv,proof,case,request)
    c.atomic_record(out/"route-handoff.json",proof)
    return proof

def live_route(read,ctx,env):
    run_id=int(env["GITHUB_RUN_ID"]);mode=ctx["mode"]
    c.require(ctx["stage"]=="audit" and mode in c.MODES,"audit restore context")
    run=read("actions/runs/"+str(run_id));jobs=read("actions/runs/"+str(run_id)+"/jobs?per_page=100")
    c.require(run["id"]==run_id and run["head_sha"]==ctx["source"] and run["run_attempt"]==1,"same workflow route run")
    candidates=[j for j in jobs["jobs"] if j["name"]=="route-only ("+mode+")"]
    c.require(len(candidates)==1 and candidates[0]["status"]=="completed"
        and candidates[0]["conclusion"]=="success","complete route job required")
    tag="cloud-results-"+ctx["token"]+"-"+c.group(mode,"route")
    release=read("releases/tags/"+tag);ref=read("git/ref/tags/"+tag)
    reservation.release.validate_release(release,ref,tag,ctx["source"])
    return release,dict(run_id=run_id,source=ctx["source"],mode=mode,route_job=candidates[0],
        route_release_id=release["id"],route_tag=tag,route_assets=[
            dict(id=a["id"],name=a["name"],bytes=a["size"],digest=a["digest"]) for a in release["assets"]],
        authenticated_complete_route=False)

def part_manifest(value,assets):
    c.require(set(value)=={"archive","parts"} and type(value["parts"]) is list
        and 1<=len(value["parts"])<=32,"route parts schema")
    c.require(type(value["archive"]["bytes"]) is int and 0<value["archive"]["bytes"]<=8*1024**3
        and re.fullmatch("[0-9a-f]{64}",value["archive"]["sha256"]) is not None,"route archive receipt")
    total=0
    for i,row in enumerate(value["parts"]):
        c.require(set(row)=={"name","bytes","sha256"}
            and row["name"]=="route-tail-evidence.tar.gz.part%03d"%i,"route ordered parts")
        c.require(type(row["bytes"]) is int and 0<row["bytes"]<=512*1024**2
            and (i==len(value["parts"])-1 or row["bytes"]==512*1024**2),"route part size")
        c.require(re.fullmatch("[0-9a-f]{64}",row["sha256"]) is not None,"route part hash")
        a=assets[row["name"]]
        c.require(a["size"]==row["bytes"] and a["digest"]=="sha256:"+row["sha256"],"route part asset join")
        total+=row["bytes"]
    c.require(total==value["archive"]["bytes"],"route archive total")
    return value

def restore(work,out,root,ctx,env,read=None,fetch=None):
    if read is None:read=reservation.release.api
    if fetch is None:
        from route_cloud_newer_postcts import fetch
    work,out,root=Path(work),Path(out),Path(root)
    release,lineage=live_route(read,ctx,env)
    c.atomic_record(out/"route-source-envelope.json",lineage)
    assets={a["name"]:a for a in release["assets"]}
    transport=work/"route-transport";transport.mkdir()
    records_dir=transport/"records";records_dir.mkdir()
    records={}
    required=("host-result.json","inner-result.json","case-result.json","outputs.json","parts.json",
              "method.json","route-handoff.json","route-handoff-inventory.json")
    for name in required:
        a=assets[name]
        c.require(type(a["size"]) is int and 0<a["size"]<=32*1024**2
            and re.fullmatch("sha256:[0-9a-f]{64}",a["digest"]) is not None,"route direct record bound")
        p=records_dir/name;fetch(a["browser_download_url"],a["digest"][7:],p)
        c.require(fingerprint(p)==dict(bytes=a["size"],sha256=a["digest"][7:]),"route direct record identity")
        records[name]=c.decode(p.read_bytes())
    request=dict(source=ctx["source"],mode=ctx["mode"],stage="route",run_id=int(env["GITHUB_RUN_ID"]))
    route_records(records["host-result.json"],records["inner-result.json"],records["case-result.json"],request)
    c.require((records_dir/"method.json").read_bytes()==c.secure_file(root,c.METHOD).read_bytes(),"route/audit exact method")
    inv,proof=records["route-handoff-inventory.json"],records["route-handoff.json"]
    expected_nested=validate_manifest(inv,proof,records["case-result.json"],request)
    c.require(fingerprint(records_dir/"route-handoff-inventory.json")==proof["inventory"],"handoff inventory bytes")
    outputs=records["outputs.json"]
    c.require(outputs["source"]==ctx["source"] and outputs["mode"]==ctx["mode"] and outputs["stage"]=="route",
        "route output inventory lineage")
    for name in required:
        if name not in ("outputs.json","parts.json"):
            c.require(outputs["files"][name]==fingerprint(records_dir/name),"route record output join")
    c.require(outputs["files"]["route-handoff.tar.gz"]==proof["archive"],"handoff archive output join")
    manifest=part_manifest(records["parts.json"],assets)
    for row in manifest["parts"]:
        fetch(assets[row["name"]]["browser_download_url"],row["sha256"],transport/row["name"])
        c.require(fingerprint(transport/row["name"])=={k:row[k] for k in ("bytes","sha256")},"route part bytes")
    archive=transport/"route-outer.tar.gz"
    with archive.open("xb") as stream:
        for row in manifest["parts"]:
            with (transport/row["name"]).open("rb") as source:shutil.copyfileobj(source,stream,4*1024**2)
    c.require(fingerprint(archive)==manifest["archive"],"whole route outer archive")
    expected_outer=dict(outputs["files"]);expected_outer["outputs.json"]=fingerprint(records_dir/"outputs.json")
    outer=transport/"outer"
    with archive.open("rb") as stream:
        outer_proof=c.engine_extract(stream,outer,expected_outer,tuple(expected_outer),c.LIMITS["archive_expanded_limit"])
    c.require(fingerprint(outer/"route-handoff.tar.gz")==proof["archive"],"whole nested route archive")
    restored=work/"route-restored"
    with (outer/"route-handoff.tar.gz").open("rb") as stream:
        nested_proof=c.engine_extract(stream,restored,expected_nested,tuple(expected_nested),c.LIMITS["archive_expanded_limit"])
    # Authenticate every old input against the independent successful-prefix map,
    # and every current source blob against this exact workflow checkout.
    original=c.prefix_contract(root)
    for p,row in original["files"].items():
        c.require(expected_nested.get(p)==row,"route changed original frozen input: "+p)
    c.require(fingerprint(restored/"out/frozen-prefix-inventory.json")==inv["original_frozen_inventory"],
        "original frozen inventory handoff")
    c.require(c.decode((restored/"out/frozen-prefix-inventory.json").read_bytes())==original,"original frozen map equality")
    m=c.method(root)
    for p in [*m["protected"],c.METHOD]:
        c.require(fingerprint(c.secure_file(restored,"tail-source/"+p))==fingerprint(c.secure_file(root,p)),
            "route/audit source projection")
    projection=route_projection(expected_nested)
    for p,row in projection.items():
        target=work/p;c.require(not target.exists() and not target.is_symlink(),"audit projection collision")
        target.parent.mkdir(parents=True,exist_ok=True)
        shutil.copyfile(c.secure_file(restored,p),target)
    c.frozen_unchanged(work,dict(files=projection))
    (work/"engine/openroad").chmod(0o500)
    shutil.copyfile(restored/"out/frozen-prefix-inventory.json",work/"frozen-manifest.json")
    c.atomic_record(work/"route-projection.json",dict(files=projection))
    lineage.update(authenticated_complete_route=True,handoff=proof,
        handoff_inventory=fingerprint(records_dir/"route-handoff-inventory.json"),
        canonical_projection_files=len(projection),complete_extracted_handoff_retained=True)
    c.atomic_record(work/"route-lineage.json",lineage)
    for name in required:
        shutil.copyfile(records_dir/name,out/("route-"+name))
    c.atomic_record(out/"route-restoration.json",dict(outer=outer_proof,nested=nested_proof,
        lineage=lineage,canonical_projection=projection,physical_acceptance=False))
    return lineage
