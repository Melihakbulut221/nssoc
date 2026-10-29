#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0
"""Separate cloud admission for immutable fresh-graph width topology comparison."""
import argparse,json,os,re
from pathlib import Path
import cdr_v59_selector_column_width_graph as previous
import cdr_v59_binding_rc_source as extraction
import cdr_width_graph_evidence as evidence
import ensure_cloud_tested_source_release as release
from run_cloud_tx_layout_repair import fetch

ROOT=previous.ROOT
GROUP="cdr-selector-width-topology"
OUT=ROOT/("hw/soc/out/cloud-"+GROUP)
VIEW="graph-input"
METHOD=ROOT/"scripts/cdr-selector-width-topology-methods.json"
APP_SHA=previous.APP_SHA
GDS_SHA=previous.GDS_SHA
TOP=previous.TOP
RUN=40808550817
HEAD="97705f184239c0c522582b9d8e82c542bd902b65"
TAG="cloud-results-40808550817-1-cdr-v59-selector-column-width-graph"
PREFIX="docs/evidence/cdr-selector-width-fresh-graph-terminal-20261029."
SUMMARY=PREFIX+"summary.json"
PARTS=PREFIX+"parts.json"
SUMMARY_SHA="62825d1992f63c4475e4f73cb16e5fccaf21a6228b157eb971fd4a7808d58d74"
PARTS_SHA="2a32d90bd33b8ed354777c6383c04090da00ffa90ead113f5eb620f33acdaa99"
OLD="physical-input/saved-input/current-mim-bundle/canonical-current-view"
FRESH="candidate"
NATIVE=("native_execution_authorized","native_width_comparison_authorized")
FALSE=("geometry_generation_authorized","physical_qualification_authorized","extraction_authorized",
 "simulation_authorized","accepted","graph_equivalence_accepted","electrical_accepted",
 "qualified_pex","full_phy_accepted","automatic_retry")
require=previous.require
sha=previous.sha
read=previous.read
regular=previous.regular
atomic=previous.atomic

def validate_authorizations(m):
    require(m["schema"]=="cdr-selector-width-topology-v1","Wrong width comparison method")
    require(m["scope"]=="READ_ONLY_EXACT_WIDTH_TOPOLOGY_AND_NATIVE_CONTROLS","Changed comparison scope")
    for key in NATIVE+FALSE+("source_controls_authorized",):
        require(type(m[key])is bool,"Nonboolean authorization")
    require(m["source_controls_authorized"]is True and all(m[k]is False for k in FALSE),"Forbidden scope")
    require(len({m[k]for k in NATIVE})==1,"Split comparison authorization")
    return m

def methods():
    m=validate_authorizations(read(METHOD));old=previous.methods()
    require(all(m["protected_sha256"].get(n)==h for n,h in old["protected_sha256"].items()),
      "Inherited source changed")
    for n,h in m["protected_sha256"].items():
        require(re.fullmatch("[0-9a-f]{64}",h)and sha(regular(ROOT,n))==h,"Protected source changed: "+n)
    evidence.source_guard()
    return m

def execution_context(m):
    require(ROOT==Path("/home/runner/work/nssoc/nssoc"),"Canonical hosted root required")
    require(os.environ.get("GITHUB_ACTIONS")=="true" and os.environ.get("RUNNER_ENVIRONMENT")=="github-hosted"
      and os.environ.get("GITHUB_REPOSITORY")=="Melihakbulut221/nssoc","Hosted repository required")
    require(os.environ.get("GITHUB_RUN_ATTEMPT")=="1","First attempt only")
    require(all(m[k]is True for k in NATIVE),"Width comparison disabled")
    return m

def authorize():
    return execution_context(methods())

def publication_authorize():
    return execution_context(validate_authorizations(read(METHOD)))

def expected_files():
    return evidence.expected_files()

def validate_view(out):
    return evidence.validate_restored(Path(out)/VIEW)

def expected_roots():
    return evidence.expected_roots()

def restore(out):
    authorize();out=Path(out)
    live=evidence.validate_live(release.api("actions/runs/"+str(RUN)),
      release.api("actions/runs/"+str(RUN)+"/attempts/1/jobs?per_page=100"),
      release.api("releases/tags/"+TAG),release.api("git/ref/tags/"+TAG))
    transport=out/"input-transport";transport.mkdir()
    base="https://github.com/Melihakbulut221/nssoc/releases/download/"+TAG+"/"
    stem="cdr-v59-selector-column-width-graph-"+str(RUN)+"-1."
    for suffix,h in (("summary.json",SUMMARY_SHA),("parts.json",PARTS_SHA)):
        fetch(base+stem+suffix,h,transport/suffix)
        require((transport/suffix).read_bytes()==(ROOT/(PREFIX+suffix)).read_bytes(),"Direct graph bytes differ")
    manifest=read(transport/"parts.json")
    require(manifest["source_directory"]=="cloud-cdr-v59-selector-column-width-graph"
      and manifest["bytes"]==756084331 and manifest["sha256"]==
      "65d2de3995696fac34df3119396024d5c52b2c33cd09d43a9c892f33cef34d61","Wrong graph archive")
    require([r["bytes"]for r in manifest["parts"]]==[536870912,219213419],"Wrong ordered graph parts")
    for row in manifest["parts"]:
        fetch(base+row["name"],row["sha256"],transport/row["name"])
    extracted=extraction.exact_extract(manifest,transport,out/VIEW,expected_files())
    view=validate_view(out);removed=[]
    for row in manifest["parts"]:
        p=regular(transport,row["name"])
        require(p.stat().st_size==row["bytes"]and sha(p)==row["sha256"],"Verified download cache changed")
        p.unlink();removed.append(dict(name=row["name"],bytes=row["bytes"],sha256=row["sha256"]))
    atomic(out/"expected-roots.json",expected_roots())
    atomic(out/"restore.json",dict(live=live,extracted=extracted,view=view,
      fresh_transport_cache_removed_after_complete_verification=removed,
      complete_original_capsule_retained=True,original_release_unmodified=True))

def validate_candidate(out):
    out=Path(out)
    require(read(regular(out,"expected-roots.json"))==expected_roots(),"Authenticated root maps changed")
    view=validate_view(out)
    synthetic=read(regular(out,"native-synthetic.json"))
    native=read(regular(out,"native-controls.json"))
    require((synthetic["status"],synthetic["positive_cases"],synthetic["rejected_cases"])==
      ("PASS_WIDTH_TOPOLOGY_SYNTHETIC_CONTROLS",3,20),"Native synthetic controls incomplete")
    require(synthetic["actual_pya_geometry_functions_exercised"]is True
      and synthetic["actual_saved_candidate_read"]is False,"Synthetic scope changed")
    require(native["status"]=="PASS_ACTUAL_WIDTH_NATIVE_FAULT_CONTROLS"
      and native["positive_complete_comparisons"]==2 and len(native["native_refusals"])==9
      and native["native_original_inputs_unchanged"]is True,"Actual native controls incomplete")
    identity=native["identity_controls"]
    require(identity["status"]=="PASS_COMPLETE_ACQUIRED_WITNESS_MUTATION_CONTROLS"
      and identity["positive_copies"]==12 and len(identity["refusals"])==12
      and identity["saved_native_inputs_mutated"]is False,"Acquired witness controls incomplete")
    comparison=native["comparison"]
    require(comparison["status"]=="PASS_WIDTH_SPECIFIC_NATIVE_IDENTITY_EXACT_UNION_AND_OWNERSHIP"
      and comparison["scope"]=="READ_ONLY_WIDTH_COMPARISON_ONLY","Comparison incomplete")
    require(comparison["contract_sha256"]=="cc92ad1c6368219f4df0faf4989e7b2a77a1dab92898f4c92c6a69e4ead67106",
      "Width contract changed")
    require(comparison["original_topology_comparator_modified"]is False
      and comparison["old_tail_bus_policy_used_for_acceptance"]is False
      and comparison["native_device_ids_not_remapped"]is True
      and comparison["raw_public_pin_order_retained"]is True,"Identity policy changed")
    for side,files in expected_roots().items():
        row=comparison["inputs"][side]
        digest=__import__("hashlib").sha256(json.dumps(files,sort_keys=True,separators=(",",":"),allow_nan=False).encode()).hexdigest()
        require(row==dict(member_count=len(files),inventory_sha256=digest,files=files),"Comparison root binding changed")
    require(len(comparison["geometry"]["typed_additions"])==26
      and len(comparison["geometry"]["placed_additions"])==52,"Geometry proof incomplete")
    owned=comparison["owned_union"]
    require(owned["component_count"]==113 and owned["checked_component_layers"]==1469
      and len(owned["rows"])==1469 and len(owned["changed"])==8,"Complete material ownership proof missing")
    for report in (synthetic,native,comparison):
        require(all(report[k]is False for k in ("physical_accepted","electrical_accepted","qualified_pex",
          "full_phy_accepted","simulation_executed","automatic_retry")),"Unexpected acceptance")
    return dict(status="PASS_SAVED_GRAPH_WIDTH_SPECIFIC_TOPOLOGY_ONLY",view=view,
      synthetic_sha256=sha(out/"native-synthetic.json"),native_controls_sha256=sha(out/"native-controls.json"),
      original_members=605,fresh_members=75,components=113,component_layers=1469,
      declared_child_rectangles=26,placed_rectangles=52,changed_owner_layers=8,
      original_native_inputs_unchanged=True,graph_equivalence_accepted=False,
      fresh_RC_executed=False,electrical_accepted=False,qualified_pex=False,full_phy_accepted=False)

def main():
    p=argparse.ArgumentParser();p.add_argument("mode",choices=("restore",));p.parse_args()
    restore(OUT)

if __name__=="__main__":main()
