#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0
"""Disabled fresh RC admission for exactly width-qualified saved graph inputs."""
import json
import os
from pathlib import Path
import re
import shutil
import types
import cdr_width_rc_input_evidence as evidence
import cdr_selector_width_topology_stage as graph_restore
import ensure_cloud_tested_source_release as release
from run_cloud_tx_layout_repair import sha

ROOT=Path(__file__).resolve().parents[1]
GROUP="cdr-selector-width-fresh-rc"
OUT=ROOT/("hw/soc/out/cloud-"+GROUP)
METHOD=ROOT/"scripts/cdr-selector-width-fresh-rc-methods.json"
ANALYSIS=ROOT/"hw/soc/out/cloud-cdr-v59-selector-column-width-graph/candidate"
SCOPE="WIDTH_QUALIFIED_CURRENT75_FRESH500_BINDING_WIRE_RC_SEVEN_MIM_BOTH_ORDERS"
NATIVE_FLAGS=("native_execution_authorized","binding_authorized","wire_rc_authorized",
 "mim_extraction_authorized","native_extraction_authorized")
FALSE=("geometry_generation_authorized","simulation_authorized","accepted","physical_accepted",
 "electrical_accepted","qualified_pex","full_phy_accepted","automatic_retry")
require=evidence.require
relative=evidence.graph.member
regular=evidence.graph.regular
CENSUS={"rppd":98,"cap_cmim":7,"npn13g2":124,"ptap1":221,"sg13_lv_nmos":50}


def read_json(path):
    return json.loads(Path(path).read_bytes())


def write(path,value):
    path=Path(path);path.parent.mkdir(parents=True,exist_ok=True)
    temp=path.with_suffix(path.suffix+".tmp")
    require(not path.is_symlink()and not temp.is_symlink(),"Symlink output")
    temp.write_text(json.dumps(value,sort_keys=True,indent=2,allow_nan=False)+"\n")
    temp.replace(path)


def validate_authorizations(method):
    require(method["schema"]=="cdr-selector-width-fresh-rc-v1"and method["scope"]==SCOPE,
      "Wrong fresh width RC scope")
    for name in NATIVE_FLAGS+FALSE+("source_controls_authorized","controller_readiness"):
        require(type(method[name])is bool,"Nonboolean fresh width RC authorization")
    require(len({method[n]for n in NATIVE_FLAGS})==1,"Split fresh width RC authorization")
    require(all(method[n]is False for n in FALSE),"Unsupported fresh width RC scope")
    require(not method[NATIVE_FLAGS[0]]or
      method["source_controls_authorized"]is method["controller_readiness"]is True,
      "Fresh width RC controls/controller not qualified")
    return method


def methods():
    method=validate_authorizations(read_json(METHOD))
    for name,h in method["protected_sha256"].items():
        require(type(h)is str and re.fullmatch("[0-9a-f]{64}",h)
          and sha(regular(ROOT,name))==h,"Changed fresh width RC source: "+name)
    evidence.source_guard()
    return method


def execution_context(method):
    require(ROOT==Path("/home/runner/work/nssoc/nssoc")
      and os.environ.get("GITHUB_ACTIONS")=="true"
      and os.environ.get("RUNNER_ENVIRONMENT")=="github-hosted"
      and os.environ.get("GITHUB_REPOSITORY")=="Melihakbulut221/nssoc"
      and os.environ.get("GITHUB_EVENT_NAME")=="workflow_dispatch"
      and os.environ.get("GITHUB_RUN_ATTEMPT")=="1","First hosted exact repository execution required")
    require(method["controller_readiness"]is True
      and all(method[n]is True for n in NATIVE_FLAGS),"Fresh width RC is disabled")
    return method


def authorize():
    return execution_context(methods())


def publication_authorize():
    # Preserve a failed envelope even if a source-integrity check was its cause.
    return execution_context(validate_authorizations(read_json(METHOD)))


def contract():
    methods()
    saved=evidence.validate_saved()
    require(saved["canonical_analysis_path"]==str(ANALYSIS),"Canonical analysis path changed")
    return dict(schema="fresh-width-RC-input-contract-v1",qualified_input=saved,
      transport=dict(expected_sha256=saved["complete_graph_files"]),
      canonical_candidate=dict(expected_sha256=saved["current_files"],members=75),
      historical_authority_reused=False)


def verify_saved(root,c):
    root=Path(root)
    result=evidence.validate_restored(root)
    require(result["saved"]==c["qualified_input"],"Saved graph differs from admitted width proof")
    return result


def qualify_saved(root,c):
    result=verify_saved(root,c)
    return dict(status="PASS_EXACT_WIDTH_NATIVE_PROOF_AND_COMPLETE_GRAPH_FOR_FRESH_RC",
      source_head=os.environ["GITHUB_SHA"],run_id=int(os.environ["GITHUB_RUN_ID"]),
      original_graph_source=evidence.graph.HEAD,original_graph_run=evidence.graph.RUN,
      original_topology_source=evidence.HEAD,original_topology_run=evidence.RUN,
      complete_graph_members=4103,current_members=75,original_members=605,
      original_physical_run=40800207491,physical_acceptance_borrowed_from_this_admission=False,
      restored=result,current_files=c["canonical_candidate"]["expected_sha256"],
      fresh_RC_executed=False,simulation_executed=False,physical_accepted=False,
      electrical_accepted=False,qualified_pex=False,full_phy_accepted=False)


def restore():
    authorize()
    topmeta=dict(run=release.api("actions/runs/"+str(evidence.RUN)),
      jobs=release.api("actions/runs/"+str(evidence.RUN)+"/attempts/1/jobs?per_page=100"),
      release=release.api("releases/"+str(evidence.RELEASE)),
      tag=release.api("git/ref/tags/"+evidence.TAG))
    g=evidence.graph
    graphmeta=dict(run=release.api("actions/runs/"+str(g.RUN)),
      jobs=release.api("actions/runs/"+str(g.RUN)+"/attempts/1/jobs?per_page=100"),
      release=release.api("releases/"+str(g.RELEASE)),ref=release.api("git/ref/tags/"+g.TAG))
    live=evidence.validate_live(topmeta,graphmeta)
    destination=OUT/"restore"
    require(not destination.exists()and not destination.is_symlink(),"Restore output already exists")
    destination.mkdir(parents=True)
    # Exact old transport/extraction body, replacing only historical authority.
    # Its complete4103 map and originalgraph release identity remain unchanged.
    context=dict(graph_restore.restore.__globals__,authorize=authorize)
    restored=types.FunctionType(graph_restore.restore.__code__,context,
      graph_restore.restore.__name__,graph_restore.restore.__defaults__,graph_restore.restore.__closure__)
    restored(destination)
    c=contract();pin=qualify_saved(destination/"graph-input",c)
    write(destination/"joint-admission.json",pin)
    write(destination/"live-width-and-graph.json",live)
    expected=c["canonical_candidate"]["expected_sha256"]
    require(len(expected)==75 and "result.json"not in expected,"Wrong current75 projection")
    require(not ANALYSIS.exists()and not ANALYSIS.is_symlink(),"Canonical analysis path occupied")
    for parent in ANALYSIS.parents:require(not parent.is_symlink(),"Symlink canonical analysis ancestor")
    ANALYSIS.mkdir(parents=True)
    for name,h in expected.items():
        path=regular(destination/"graph-input/candidate",name)
        require(sha(path)==h,"Changed source projection member")
        target=ANALYSIS/relative(name);target.parent.mkdir(parents=True,exist_ok=True)
        shutil.copyfile(path,target);require(sha(target)==h,"Changed copied projection member")
    actual={n:r["sha256"]for n,r in evidence.graph.tree(ANALYSIS).items()}
    require(actual==expected,"Incomplete exact canonical projection")
    write(destination/"canonical-candidate.json",dict(files=expected,complete_members=75,
      original_absolute_path=str(ANALYSIS),all_original_bytes_unchanged=True,
      current_root_result_fabricated=False,additional_outputs_initially_absent=True))
    require(qualify_saved(destination/"graph-input",c)==pin,"Original graph changed during projection")
    methods()
    return pin
