#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0
"""Exact current physical-to-graph contract. This does not qualify RC or a PHY."""
from collections import Counter
from pathlib import PurePosixPath
import copy,re
TOP="nssoc_cdr_pd500_resistor_v59"
BASE="native/current-mim-bundle/canonical-current-view/"
TARGETS=(3,4,5,6,32,33,34,35)
LAYERS=(8,10,30,50,67,126,134,19,29,49,66,125,133)
FLAGS=dict(physical_acceptance=False,electrical_acceptance=False,full_phy_accepted=False,
 timing_accepted=False,qualified_pex=False,new_simulation=False)
PASS="PASS_FRESH_EIGHT_DRAIN_GRAPH_IDENTITIES_FULL_PARTITION_UNIONS_REQUIRES_RC"
def require(ok,message):
    if not ok:raise AssertionError(message)
def safe_name(name):
    p=PurePosixPath(name)
    require(isinstance(name,str)and not p.is_absolute()and str(p)==name and ".."not in p.parts and "\\"not in name,"exact relative member")
    return name
def contract(c):
    require(c["schema"]=="cdr-current-eight-drain-graph-inputs-v1","graph input schema")
    require(c["source_controls_authorized"]is True and c["native_graph_authorized"]is True,"graph execution authority")
    require(c["candidate_generation_authorized"]is False and c["fresh_rc_authorized"]is False and c["electrical_simulation_authorized"]is False,"graph scope only")
    require(all(c[k]is False for k in FLAGS),"no final acceptance in graph contract")
    require(len(c["selected"])==64 and all(n.startswith(BASE)for n in c["selected"]),"all64 current reference members")
    for n,d in c["selected"].items():
        safe_name(n);require(re.fullmatch("[0-9a-f]{64}",d)is not None,"selected reference digest")
    require(c["old_producer_run"]==41017290646 and c["old_archive_complete_members"]==2797,"actual current reference producer")
    p=c["physical"];producer=p["producer"]
    require(producer==dict(id=41203881385,head_sha="39496d034c4c1f2c9bcc3a9fe70cb3d82823fb53",
      head_branch="codex/cdr-drain-m1-loaded-electrical",run_attempt=1,event="workflow_dispatch",workflow_id=401118236),"exact qualified physical producer")
    require(p["release_id"]==429942553 and p["tag"]=="cloud-results-41203881385-1-cdr-current-eight-drain-straps","physical release identity")
    require(len(p["full"])==339 and len(p["selected"])==len(set(p["selected"]))==39 and set(p["selected"])<=set(p["full"]),"complete physical member map and selected set")
    for n,d in p["full"].items():safe_name(n);require(re.fullmatch("[0-9a-f]{64}",d)is not None,"physical member digest")
    require(p["gds"]==dict(bytes=997620,sha256="9d8984fd4852a04618146732c0d473ca80c6bb1d2f441d0da27854ed7ca69bff"),"exact admitted candidate GDS")
    require(p["lvs"]==dict(bytes=2720487,sha256="6b75a97dd6c1791622efd4676322a8f694efabec83b540e369d61b6a6270ee34"),"exact admitted flat LVS")
    require(p["full"]["native/layout/"+TOP+".gds"]==p["gds"]["sha256"]and p["full"]["native/physical/lvs_flat/result.lvsdb"]==p["lvs"]["sha256"],"candidate map join")
    parts=p["parts"]
    require(parts["format"]=="ordered-tar-gzip-parts-v1"and parts["source_directory"]=="cdr-current-eight-drain-straps-41203881385-1","physical archive namespace")
    require(parts["bytes"]==15074161 and parts["sha256"]=="19ceeaad24eaabbd223e507eecf27397b2c34a82ef18ea0b56fff1b807f67451","physical combined archive")
    require(len(parts["parts"])==1 and parts["parts"][0]["index"]==0 and sum(x["bytes"]for x in parts["parts"])==parts["bytes"],"complete ordered physical parts")
    for row in parts["parts"]:
        require({k:p["assets"][row["name"]][k]for k in("bytes","sha256")}=={k:row[k]for k in("bytes","sha256")},"physical asset part join")
    return c
def input_names(c,outputs,entry):
    contract(c);names=sorted(set(c["selected"])|{entry["report_member"],"result.json"})
    require(len(names)==66 and set(names)<=set(outputs),"all66 selected original members")
    require(all(outputs[n]==d for n,d in c["selected"].items()),"exact current reference view")
    return names
def physical_live(c,run,jobs,release,ref):
    contract(c);p=c["physical"];producer=p["producer"]
    require(all(run.get(k)==v for k,v in producer.items()),"physical source/run/attempt/workflow")
    require(run["status"]=="completed"and run["conclusion"]=="success","actual successful physical run")
    rows=jobs["jobs"];require(len(rows)==4 and {j["name"]for j in rows}=={"source-controls","preserve-job-log","physical","preserve-physical-job-logs"},"complete physical jobs")
    require(all(j["status"]=="completed"and j["conclusion"]=="success"and j["head_sha"]==producer["head_sha"]and j["run_id"]==producer["id"]for j in rows),"physical job provenance and success")
    require(release["id"]==p["release_id"]and release["tag_name"]==p["tag"]and release["target_commitish"]==producer["head_sha"]and release["draft"]is False and release["prerelease"]is True,"physical release binding")
    require(ref["object"]["type"]=="commit"and ref["object"]["sha"]==producer["head_sha"],"physical tag binding")
    assets={x["name"]:x for x in release["assets"]};require(len(assets)==len(release["assets"])and set(assets)==set(p["assets"]),"complete unique physical assets")
    for name,pin in p["assets"].items():
        a=assets[name];require(a["state"]=="uploaded"and a["id"]==pin["id"]and a["size"]==pin["bytes"]and a["digest"]=="sha256:"+pin["sha256"],"physical asset live fingerprint")
    return dict(run_id=producer["id"],source=producer["head_sha"],release_id=p["release_id"],complete_assets=True,**FLAGS)
def declarations(d):
    require(d["device_count"]==8 and d["all_original_raw_records_preserved"]is True,"actual additive geometry provenance")
    require(all(d[k]is False for k in FLAGS),"declared geometry is not full acceptance")
    rows=d["records"];require(len(rows)==574,"all574 declared raw additions")
    require({r["device"]for r in rows}==set(TARGETS),"all eight physical drains")
    require(Counter(r["layer"]for r in rows)==Counter({8:6,10:8,19:560}),"sixM1/eightM2/560Via1 additions")
    seen=set()
    for r in rows:
        require(set(r)=={"device","cluster","layer","datatype","box_dbu"},"exact declared record fields")
        require(type(r["device"])is int and type(r["cluster"])is int and r["datatype"]==0 and type(r["datatype"])is int,"typed declared owner and layer")
        b=r["box_dbu"];require(len(b)==4 and all(type(v)is int and v%5==0 for v in b)and b[0]<b[2]and b[1]<b[3],"nondegenerate5nmgrid rectangle")
        key=(r["layer"],tuple(b));require(key not in seen,"unique raw addition");seen.add(key)
    for device in TARGETS:
        owned=[r for r in rows if r["device"]==device]
        require(len({r["cluster"]for r in owned})==1,"single actual drain owner")
        require(Counter(r["layer"]for r in owned)==Counter({10:1,19:70,**({8:1}if device not in(3,32)else{})}),"exact per-device physical additions")
    require(len({r["cluster"]for r in rows})==2,"two actual tail partitions")
    return rows
