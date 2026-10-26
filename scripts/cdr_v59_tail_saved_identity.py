#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0
"""Admission for one complete saved 931-member capsule; no engine or geometry work."""
import ast
import hashlib
import json
import os
from pathlib import Path,PurePosixPath
import re
import tarfile
import types
import ensure_cloud_tested_source_release as release
from cloud_chunked_results import verify_parts
from cloud_verified_parts import JoinedParts
from run_cloud_tx_layout_repair import fetch,sha

ROOT=Path(__file__).resolve().parents[1]
METHOD=ROOT/"scripts/cdr-v59-tail-saved-identity-methods.json"
PREFIX="docs/evidence/cdr-v59-tail-physical-corrected-result-20261026"
SUMMARY=PREFIX+"-summary.json"
SUMMARY_SHA="27a186a20213a7485d7f59747372e513a279d878dceb2ed1553cea36b13b5286"
PARTS=PREFIX+"-parts.json"
PARTS_SHA="7c1b16f511ceea2c87f48872e7b954863ad83ab186839545bdf4483712c53e27"
RUN=40369539200
HEAD="504c4b94ab19532e0831daf496df4a9448678290"
GROUP="cdr-v59-tail-saved-identity"
OLD_GROUP="cdr-v59-tail-access-physical"
TAG="cloud-results-40369539200-1-"+OLD_GROUP
LOCATE="docs/evidence/cdr-v59-tail-exact-wire-methods-20261026/locate01.py"
GENERATOR="scripts/generate_cdr_v59_tail_access_wire.py"
GENERATION="candidate/result.json"
EXTRACT_SOURCE="scripts/cdr_v59_binding_rc_source.py"
PUBLICATION_SOURCE="scripts/cloud_cdr_v59_binding_rc.py"
SIDES={name:{k:prefix+"/"+v for k,v in {
 "gds":"parent/layout/nssoc_cdr_pd500_resistor_v59.gds",
 "lvs":"parent/physical/lvs_flat/result.lvsdb",
 "inventory":"wire/pcell-inventory01.json","pins":"wire/source-pins.json",
 "locations":"wire/device-locations01.json","graph":"wire/native05/result.json",
 "anchors":"wire/anchors08.json"}.items()}
 for name,prefix in (("old","source-capsule/analysis-capsule"),("new","candidate"))}
FALSE_FLAGS=("native_execution_authorized","geometry_generation_authorized","physical_qualification_authorized","extraction_authorized",
 "simulation_authorized","accepted","qualified_pex","full_phy_accepted")
COMMANDS=("restore-complete-original-capsule","restore-frozen-pdk-runtime","native-additive-generation",
 "full-physical-and13-faults","fresh-native-planes","source-annotation-recovery",
 "probe01.py","locate01.py","anchors01.py","dedup01.py")

def read_json(path):
    assert path.is_file() and not path.is_symlink(),"Nonregular JSON input"
    return json.loads(path.read_text())

def write(path,value):
    assert path.parent.is_dir() and not path.parent.is_symlink()
    assert not path.is_symlink()
    path.write_text(json.dumps(value,indent=2,allow_nan=False)+"\n")

def value_hash(value):
    return hashlib.sha256(json.dumps(value,sort_keys=True,separators=(",",":"),allow_nan=False).encode()).hexdigest()

def methods():
    m=read_json(METHOD)
    assert m["schema"]=="cdr-v59-tail-saved-identity-methods-v1"
    for name,digest in m["protected_sha256"].items():
        path=ROOT/name
        assert path.is_file() and not path.is_symlink() and sha(path)==digest,name
        assert all(not p.is_symlink() for p in path.parents if p!=ROOT.parent),name
    assert all(m[k] is False for k in FALSE_FLAGS),"Engine/acceptance flag enabled"
    assert m["original_topology_comparator_unchanged"] is True
    return m

def authorize():
    m=methods()
    assert ROOT==Path("/home/runner/work/nssoc/nssoc")
    assert os.environ.get("GITHUB_ACTIONS")=="true"
    assert os.environ.get("RUNNER_ENVIRONMENT")=="github-hosted"
    assert os.environ.get("GITHUB_REPOSITORY")=="Melihakbulut221/nssoc"
    assert os.environ.get("GITHUB_RUN_ATTEMPT")=="1"
    assert m["readback_authorized"] is m["read_only_native_identity_authorized"] is True
    return m

def load_definitions(path,names,scope):
    m=read_json(METHOD)
    rel=path.relative_to(ROOT).as_posix()
    assert rel in m["protected_sha256"] and sha(path)==m["protected_sha256"][rel],rel
    text=path.read_text();tree=ast.parse(text)
    selected=[n for n in tree.body if isinstance(n,ast.FunctionDef) and n.name in names]
    assert [n.name for n in selected]==names or sorted(n.name for n in selected)==sorted(names)
    assert len(selected)==len(names)==len(set(names))
    exec(compile(ast.Module(body=selected,type_ignores=[]),str(path),"exec"),scope)
    return {n.name:scope[n.name] for n in selected}

def extraction_helpers():
    scope={"Path":Path,"PurePosixPath":PurePosixPath,"re":re,"hashlib":hashlib,
      "tarfile":tarfile,"JoinedParts":JoinedParts,"verify_parts":verify_parts,"sha":sha}
    load_definitions(ROOT/EXTRACT_SOURCE,["safe_name","exact_extract","verify_files"],scope)
    return types.SimpleNamespace(**scope)

def publication_helpers():
    scope={"Path":Path,"json":json,"release":release,"verify_parts":verify_parts}
    load_definitions(ROOT/PUBLICATION_SOURCE,["only_reserved","publication_files"],scope)
    return types.SimpleNamespace(**scope)

def validate_summary(summary):
    assert summary["status"]=="FAIL_ADDITIVE_TAIL_WIRE_PHYSICAL"
    assert summary["source_head"]==HEAD and summary["run_id"]==RUN and summary["run_attempt"]==1
    assert summary["error"]=="AssertionError()"
    assert 'old_graph["native_ports"]==new_graph["native_ports"]' in summary["traceback"]
    assert [(r["label"],r["returncode"]) for r in summary["commands"]]==[(n,0) for n in COMMANDS]
    for r in summary["commands"]:
        assert r["supervision_failure"] is None and not r["process_group_cleanup"]["remaining_live"]
    for k in ("native_physical_qualification_passed","automatic_retry","accepted","electrical_accepted",
              "qualified_pex","full_phy_accepted","wire_rc_extracted","simulation_executed"):
        assert summary[k] is False,k
    assert len(summary["outputs"])==930
    assert summary["generation_result_sha256"]=="1c614b4863940a1b161640caecb1577ff0c399cbbb083866ccc1523fbd370514"
    assert summary["physical_result_sha256"]=="4462c427ddbb82352d9e3b08c365606dc8848dd0df4032eed19f7111ea42f9f2"
    assert summary["saved_capsule_integrity"]=={"files":706,"all_hashes_unchanged":True}
    for name,digest in summary["outputs"].items():
        p=PurePosixPath(name)
        assert p.as_posix()==name and not p.is_absolute() and ".." not in p.parts and chr(92) not in name
        assert re.fullmatch("[0-9a-f]{64}",digest)
    return summary

def expected_files():
    assert sha(ROOT/SUMMARY)==SUMMARY_SHA
    summary=validate_summary(read_json(ROOT/SUMMARY))
    expected={**summary["outputs"],"result.json":SUMMARY_SHA}
    assert len(expected)==931
    assert all(n in expected for files in SIDES.values() for n in files.values())
    return expected

def validate_live(run,jobs,info,ref):
    assert (run["id"],run["head_sha"],run["run_attempt"],run["event"],run["status"],run["conclusion"])==(
      RUN,HEAD,1,"workflow_dispatch","completed","failure")
    assert run["path"]==".github/workflows/cdr-v59-tail-access-physical-cloud.yml"
    wanted={121736255584:("source-controls","success"),121736653973:("physical","failure")}
    assert jobs["total_count"]==len(jobs["jobs"])==2
    assert {j["id"] for j in jobs["jobs"]}==set(wanted)
    for j in jobs["jobs"]:
        assert j["run_id"]==RUN and j["head_sha"]==HEAD and j["status"]=="completed"
        assert (j["name"],j["conclusion"])==wanted[j["id"]]
    result=release.validate_release(info,ref,TAG,HEAD)
    assert info["id"]==424559937
    original=read_json(ROOT/(PREFIX+"-release.json"))
    fields=("id","name","size","digest")
    project=lambda rows:sorted([{k:r[k] for k in fields} for r in rows],key=lambda r:r["id"])
    assert project(info["assets"])==project(original["assets"]) and len(info["assets"])==9
    return result

def validate_parts(manifest):
    assert sha(ROOT/PARTS)==PARTS_SHA and manifest==read_json(ROOT/PARTS)
    assert manifest["bytes"]==32043537 and manifest["source_directory"]=="cloud-cdr-v59-tail-access-physical"
    assert manifest["sha256"]=="891a8cc633af7475d3c8679a37efaad32e996ff9f8f42027499c81ab0ba66d40"
    return manifest

def verify_inputs(root,expected):
    proof=extraction_helpers().verify_files(root,expected)
    actual=set()
    for p in root.rglob("*"):
        assert not p.is_symlink() and (p.is_dir() or p.is_file()),"Nonregular restored member"
        if p.is_file():actual.add(p.relative_to(root).as_posix())
    assert actual==set(expected),"Changed complete restored member inventory"
    return proof

def restore(out):
    authorize()
    proof=validate_live(release.api("actions/runs/"+str(RUN)),
      release.api("actions/runs/"+str(RUN)+"/attempts/1/jobs?per_page=100"),
      release.api("releases/tags/"+TAG),release.api("git/ref/tags/"+TAG))
    transport=out/"transport";transport.mkdir()
    base="https://github.com/Melihakbulut221/nssoc/releases/download/"+TAG+"/"
    stem=OLD_GROUP+"-"+str(RUN)+"-1"
    fetch(base+stem+".summary.json",SUMMARY_SHA,transport/"summary.json")
    assert (transport/"summary.json").read_bytes()==(ROOT/SUMMARY).read_bytes()
    fetch(base+stem+".parts.json",PARTS_SHA,transport/"parts.json")
    manifest=validate_parts(read_json(transport/"parts.json"))
    for p in manifest["parts"]:fetch(base+p["name"],p["sha256"],transport/p["name"])
    result=extraction_helpers().exact_extract(manifest,transport,out/"restored",expected_files())
    assert result["regular_members"]==931
    verify_inputs(out/"restored",expected_files())
    write(out/"archive-verification.json",{"release":proof,"archive":result,
      "original_failure_preserved":True,"input_archive_only":True})
    return result
