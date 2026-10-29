#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0
"""Fresh full graph admission over an immutable physically verified column candidate."""
import argparse, hashlib, json, os, re, shutil, traceback
from pathlib import Path
import cdr_v59_selector_column_width_physical as previous
import cdr_v59_tail_access_topology as topology
import cdr_v59_binding_rc_source as extraction
import ensure_cloud_tested_source_release as release
from run_cloud_tx_layout_repair import fetch
ROOT=previous.ROOT
METHOD=ROOT/"scripts/cdr-v59-selector-column-width-graph-methods.json"
GROUP="cdr-v59-selector-column-width-graph"
OUT=ROOT/("hw/soc/out/cloud-"+GROUP)
VIEW="physical-input"
TOP=previous.TOP
APP_SHA=previous.APP_SHA
GDS_SHA=previous.GDS_SHA
PREFIX="docs/evidence/cdr-selector-width-fresh-physical-terminal-20261029."
SUMMARY=PREFIX+"summary.json"
PARTS=PREFIX+"parts.json"
SUMMARY_SHA="666d2464a8eab50f0367a3ef18c0c18ecf66e38f027bf2bcb2de7d735d7e2aaa"
PARTS_SHA="1c7189320abed1952470966e228ed7ad2d04f0334d82a0d79d57cc0c50b40d70"
HEAD="20e4cf92f79b9e2742373dc058a855a979f60db1"
RUN=40800207491
TAG="cloud-results-40800207491-1-cdr-v59-selector-column-width-physical"
NATIVE=("native_execution_authorized","native_graph_readback_authorized","derived_reference_projection_authorized")
FALSE=("geometry_generation_authorized","physical_qualification_authorized","extraction_authorized","simulation_authorized",
       "accepted","graph_equivalence_accepted","electrical_accepted","qualified_pex","full_phy_accepted","automatic_retry")
WIRE=("probe01.py","locate01.py","anchors01.py","dedup01.py")
WIRE_SOURCE="docs/evidence/cdr-v59-tail-exact-wire-methods-20261026"
require=previous.require
sha=previous.sha
regular=previous.regular
read=previous.read
atomic=previous.atomic

def validate_authorizations(m):
    require(m["schema"]=="cdr-v59-selector-column-width-graph-v1","Wrong graph method")
    require(m["scope"]=="FRESH_REFERENCE_PLANES_FULL_GRAPH_AND_ANCHORS_ONLY","Changed graph scope")
    for k in NATIVE+FALSE+("source_controls_authorized",):
        require(type(m[k])is bool,"Nonboolean authorization")
    require(m["source_controls_authorized"]is True and all(m[k]is False for k in FALSE),"Forbidden scope")
    require(len({m[k]for k in NATIVE})==1,"Split graph authorization")
    return m

def methods():
    m=validate_authorizations(read(METHOD));old=previous.methods()
    require(all(m["protected_sha256"].get(n)==h for n,h in old["protected_sha256"].items()),"Inherited source changed")
    for n,h in m["protected_sha256"].items():
        require(re.fullmatch("[0-9a-f]{64}",h)and sha(regular(ROOT,n))==h,"Protected source changed: "+n)
    return m

def execution_context(m):
    require(ROOT==Path("/home/runner/work/nssoc/nssoc"),"Canonical hosted root required")
    require(os.environ.get("GITHUB_ACTIONS")=="true"and os.environ.get("RUNNER_ENVIRONMENT")=="github-hosted"
      and os.environ.get("GITHUB_REPOSITORY")=="Melihakbulut221/nssoc","Hosted repository required")
    require(os.environ.get("GITHUB_RUN_ATTEMPT")=="1","First attempt only")
    require(all(m[k]is True for k in NATIVE),"Graph stage disabled")
    return m

def authorize():
    return execution_context(methods())

def publication_authorize():
    return execution_context(validate_authorizations(read(METHOD)))

def expected_files():
    require(sha(ROOT/SUMMARY)==SUMMARY_SHA and sha(ROOT/PARTS)==PARTS_SHA,"Saved physical evidence changed")
    s=read(ROOT/SUMMARY)
    require((s["run_id"],s["source_head"],s["run_attempt"],s["status"])==
      (RUN,HEAD,1,"PASS_CANDIDATE_DRC_LVS_AND13_FAULTS_REQUIRES_FRESH_RC_ELECTRICAL"),"Wrong physical producer")
    require(s["terminal_finalization_complete"]is s["native_physical_qualification_passed"]is True,"Incomplete physical result")
    require(all(s[k]is False for k in ("fresh_RC_executed","simulation_executed","electrical_accepted","qualified_pex","full_phy_accepted","automatic_retry")),"Borrowed electrical acceptance")
    require(s["candidate"]["gds_sha256"]==s["outputs"]["layout/"+TOP+".gds"]==GDS_SHA,"Wrong physical candidate")
    return {**s["outputs"],"result.json":SUMMARY_SHA}

def validate_live(run,jobs,info,ref):
    require((run["id"],run["head_sha"],run["run_attempt"],run["event"],run["status"],run["conclusion"])==
      (RUN,HEAD,1,"workflow_dispatch","completed","success"),"Physical producer changed")
    require(run["path"]==".github/workflows/cdr-v59-selector-column-width-physical-cloud.yml","Physical workflow changed")
    wanted={123206235955:"source-controls",123206408396:"physical"}
    require(jobs["total_count"]==len(jobs["jobs"])==2 and {j["id"]for j in jobs["jobs"]}==set(wanted),"Physical jobs changed")
    for j in jobs["jobs"]:
        require(j["run_id"]==RUN and j["head_sha"]==HEAD and j["name"]==wanted[j["id"]]
          and j["status"]=="completed"and j["conclusion"]=="success","Physical job incomplete")
    proof=release.validate_release(info,ref,TAG,HEAD)
    require(info["id"]==427365885,"Physical release changed")
    original=read(ROOT/(PREFIX+"release.json"))
    projection=lambda rows:sorted([{k:r[k]for k in ("id","name","size","digest")}for r in rows],key=lambda r:r["id"])
    require(projection(info["assets"])==projection(original["assets"]),"Physical release assets changed")
    return proof

def baseline(out):
    return Path(out)/VIEW/"saved-input"/previous.inherited.VIEW

def validate_view(out):
    out=Path(out);root=out/VIEW
    proof=previous.inherited.loaded.verify_exact_files(root,expected_files())
    # Admission of exact prior physical evidence, not a new physical execution.
    p=read(root/"physical/result.json");previous.physical.validate_physical(p)
    require(sha(root/"physical/result.json")==read(ROOT/SUMMARY)["candidate"]["result_sha256"],"Physical report changed")
    previous.inherited.validate_candidate(root/"saved-input")
    require(sha(root/"layout"/(TOP+".gds"))==GDS_SHA,"Source physical GDS changed")
    return dict(complete_input=proof,physical_source_run=RUN,candidate_gds_sha256=GDS_SHA,
      prior_DRC_LVS_admitted=True,new_DRC_LVS_executed=False,electrical_acceptance_inherited=False)

def restore(out):
    authorize();out=Path(out)
    live=validate_live(release.api("actions/runs/"+str(RUN)),
      release.api("actions/runs/"+str(RUN)+"/attempts/1/jobs?per_page=100"),
      release.api("releases/tags/"+TAG),release.api("git/ref/tags/"+TAG))
    transport=out/"input-transport";transport.mkdir()
    base="https://github.com/Melihakbulut221/nssoc/releases/download/"+TAG+"/"
    stem="cdr-v59-selector-column-width-physical-"+str(RUN)+"-1."
    for suffix,h in (("summary.json",SUMMARY_SHA),("parts.json",PARTS_SHA)):
        fetch(base+stem+suffix,h,transport/suffix)
        require((transport/suffix).read_bytes()==(ROOT/(PREFIX+suffix)).read_bytes(),"Direct physical bytes differ")
    manifest=read(transport/"parts.json")
    require(manifest["source_directory"]=="cloud-cdr-v59-selector-column-width-physical"
      and manifest["bytes"]==753233652
      and manifest["sha256"]=="8f5ecf9d69a2a1304df244ab0728d9c3c24f631c85469fe58038f3254d72c032","Wrong physical archive")
    for row in manifest["parts"]:fetch(base+row["name"],row["sha256"],transport/row["name"])
    extracted=extraction.exact_extract(manifest,transport,out/VIEW,expected_files())
    view=validate_view(out);removed=[]
    # Only fresh download cache is removed after complete extraction. The original
    # release and every original capsule member stay intact; failures keep cache.
    for row in manifest["parts"]:
        p=regular(transport,row["name"])
        require(p.stat().st_size==row["bytes"]and sha(p)==row["sha256"],"Verified download cache changed")
        p.unlink();removed.append(dict(name=row["name"],bytes=row["bytes"],sha256=row["sha256"]))
    atomic(out/"restore.json",dict(live=live,extracted=extracted,view=view,
      fresh_transport_cache_removed_after_complete_verification=removed,
      complete_original_capsule_retained=True,original_release_unmodified=True))

def report_inputs(report,root):
    require(type(report["inputs"])is dict and report["inputs"],"Missing fresh input bindings")
    records={}
    for n,v in report["inputs"].items():
        p=Path(n)
        require(p.is_absolute()and p.resolve()==p and p.is_relative_to(root)and p.is_file()and not any(q.is_symlink()for q in (p,*p.parents)),"Input outside fresh view")
        expected=v["sha256"]if isinstance(v,dict)else v
        require(sha(p)==expected,"Fresh input changed")
        if isinstance(v,dict):require(p.stat().st_size==v["bytes"],"Fresh input size changed")
        records[n]=expected
    return records

def legacy_topology_diagnostic(out):
    """Preserve the old tail-bus verdict; its material policy is not for column width."""
    out=Path(out);old=baseline(out)/"wire";new=out/"candidate/wire"
    names=("native05/result.json","device-locations01.json","anchors08.json")
    original=[read(old/n)for n in names];fresh=[read(new/n)for n in names]
    result=dict(legacy_material_policy_applicable=False,graph_equivalence_accepted=False,
      reason="Original comparator permits two TM2 tail-bus partitions. This candidate adds only the separately declared four selector partitions on Metal4/TopMetal1.",
      original_input_hashes={n:sha(old/n)for n in names},fresh_input_hashes={n:sha(new/n)for n in names})
    try:
        result.update(status="LEGACY_COMPARATOR_RETURNED",result=topology.compare(original,fresh,True))
    except AssertionError as error:
        result.update(status="LEGACY_COMPARATOR_REJECTED",error=repr(error),traceback=traceback.format_exc())
    return result

def derived_texts():
    oldtop="nssoc_cdr_pd500_active_input_v57"
    items=(("check_cdr_sampler_active_input_v57_parent_geometry.py","check_width_parent_geometry.py"),
      ("cloud_cdr_sampler_active_input_v57_planes.py","width_planes.py"),
      ("cloud_cdr_sampler_active_input_v57_wire_inputs.py","width_source_pins.py"))
    texts={};proof={}
    for source,name in items:
        path=ROOT/"scripts"/source;text=path.read_text();changes=[]
        require(text.count(oldtop)>0,"Missing original top substitution")
        changes.append(dict(before=oldtop,after=TOP,count=text.count(oldtop)))
        text=text.replace(oldtop,TOP)
        if name=="width_planes.py":
            old="from check_cdr_sampler_active_input_v57_parent_geometry import check"
            new="from check_width_parent_geometry import check"
            require(text.count(old)==1,"Geometry import count changed")
            text=text.replace(old,new);changes.append(dict(before=old,after=new,count=1))
        texts[name]=text
        proof[name]=dict(source=str(path.relative_to(ROOT)),source_sha256=sha(path),
          generated_sha256=hashlib.sha256(text.encode()).hexdigest(),changes=changes)
    return texts,proof

def prepare_view(out):
    out=Path(out);validate_view(out)
    parent=out/"candidate/parent";parent.mkdir(parents=True)
    old=baseline(out)/"parent";physical=out/VIEW
    shutil.copytree(old/"inputs",parent/"inputs")
    shutil.copyfile(old/"children.json",parent/"children.json")
    shutil.copytree(physical/"layout",parent/"layout")
    shutil.copytree(physical/"physical/lvs_flat",parent/"physical/lvs_flat")
    original=read(old/"layout/result.json")
    current=read(physical/"layout/result.json")
    require(original["ports"]==current["ports"],"Original public ports changed")
    meta={k:original[k]for k in ("source_plan","placements","primitive_census","ports")}
    require(len(meta["placements"])==16 and sum(meta["primitive_census"].values())==500,"Incomplete original metadata")
    meta.update(status="DERIVED_METADATA_FOR_FRESH_READBACK_NOT_NEW_PHYSICAL_ACCEPTANCE",
      inputs={str(p):sha(p)for p in (old/"layout/result.json",physical/"layout/result.json")},
      outputs={p.name:sha(p)for p in (parent/"layout").iterdir()if p.is_file()and p.name!="result.json"},
      original_metadata_retained=True,physical_accepted=False,electrical_accepted=False,qualified_pex=False)
    require(meta["outputs"][TOP+".gds"]==GDS_SHA,"Wrong projected parent GDS")
    atomic(parent/"layout/result.json",meta)
    texts,proof=derived_texts();method_dir=out/"candidate/methods";method_dir.mkdir()
    for name,text in texts.items():(method_dir/name).write_text(text)
    atomic(out/"derived-methods.json",proof)
    wire=out/"candidate/wire";wire.mkdir()
    for name in WIRE:shutil.copyfile(ROOT/WIRE_SOURCE/name,wire/name)
    return meta

def check_derived(out):
    out=Path(out);texts,proof=derived_texts()
    require(read(out/"derived-methods.json")==proof,"Derivation provenance changed")
    for name,text in texts.items():
        require(regular(out/"candidate/methods",name).read_bytes()==text.encode(),"Derived method changed")
    for name in WIRE:
        require(sha(regular(out/"candidate/wire",name))==sha(ROOT/WIRE_SOURCE/name),"Wire method changed")
    return proof

def validate_candidate(out):
    out=Path(out);view=out/"candidate";wire=view/"wire"
    build=read(out/"reference-projection.json")
    require(build["status"]=="PASS_INDEPENDENT26BOX_SOURCE_REFERENCE_AND_SERIALIZED_REREAD","Reference projection incomplete")
    require(build["original_parent_gds_sha256"]==GDS_SHA and sha(view/"parent/layout"/(TOP+".gds"))==GDS_SHA,"Parent GDS changed")
    require(build["added_raw_record_count"]==26 and build["original_source_child_drawings_matched_parent"]is True
      and build["all_original_source_raw_text_properties_hierarchy_preserved"]is True,"Reference delta incomplete")
    require(build["source_child_after_sha256"]==sha(view/build["source_child_relative"]),"Reference child changed")
    source_files={p.relative_to(baseline(out)/"parent").as_posix():sha(p)
      for p in (baseline(out)/"parent/inputs").rglob("*")if p.is_file()}
    derived_files={p.relative_to(view/"parent").as_posix():sha(p)
      for p in (view/"parent/inputs").rglob("*")if p.is_file()}
    require(source_files==build["original_input_hashes"]and derived_files==build["derived_input_hashes"],"Reference source files changed")
    child=Path(build["source_child_relative"]).relative_to("parent").as_posix()
    require(set(source_files)==set(derived_files)and {n for n in source_files if source_files[n]!=derived_files[n]}=={child},"Unapproved source drawing change")
    require(source_files[child]==build["source_child_before_sha256"],"Wrong original source child")
    planes=read(view/"native-planes.json")
    require(planes["status"]=="PASS_PD500_NATIVE160_PLANES_51_NETS_19_FAULTS"
      and len(planes["anchors"])==160 and len(planes["controls"])==19
      and len(planes["parent_geometry"]["controls"])==5,"Native plane gates incomplete")
    require(len(planes["parent_geometry"]["actual_placements"])==16
      and len(planes["parent_geometry"]["checked_layers_by_kind"])==9,"Complete placement/leaf comparison missing")
    recovered=read(wire/"source-pins.json")
    require(recovered["status"]=="PASS_RECOVERED_SOURCE_PIN_BOXES_ON_IDENTICAL_PRIMITIVE_DRAWING"
      and recovered["target_gds_sha256"]==GDS_SHA and recovered["target_geometry_edited"]is False
      and recovered["missing_referenced_primitive_rejected"]is True,"Fresh source pins unqualified")
    graph=read(wire/"native05/result.json");locations=read(wire/"device-locations01.json");anchors=read(wire/"anchors08.json")
    require(graph["status"]=="PASS_GEOMETRIC_PUMP_WIRE_COMPONENT_BINDING_NO_RC"
      and graph["native_device_count"]==500 and graph["native_terminal_count"]==1446
      and graph["wire_component_count"]==113 and len(graph["native_ports"])==25,"Fresh graph incomplete")
    require(locations["status"]=="PASS_ALL_500_DEVICES_HAVE_UNIQUE_PHYSICAL_PCELL_ENCLOSURE"
      and len(locations["devices"])==500 and locations["native_terminal_count"]==1446,"Fresh devices incomplete")
    require(anchors["status"]=="PASS_EXACT_PHYSICAL_POINTS_FOR_ALL_LOGICAL_REFERENCES"
      and anchors["logical_anchor_count"]==anchors["physical_anchor_count"]==978
      and anchors["dispositions"]==dict(ACTUAL_TERMINAL_METAL_POINT_REFERENCE=953,RETAINED_INTRINSIC_BODY_NO_SUBSTRATE_RESISTANCE=493),
      "Fresh anchors incomplete")
    bindings={n:report_inputs(r,view)for n,r in [("parent-geometry",planes["parent_geometry"]),("planes",planes),("source-pins",recovered),("graph",graph),("locations",locations),("anchors",anchors)]}
    require(bindings["graph"][str(view/"parent/layout"/(TOP+".gds"))]==GDS_SHA,"Graph uses stale GDS")
    require(bindings["graph"][str(view/"parent/physical/lvs_flat/result.lvsdb")]==
      read(ROOT/SUMMARY)["outputs"]["physical/lvs_flat/result.lvsdb"],"Graph uses stale LVS")
    diagnostic=legacy_topology_diagnostic(out)
    require(diagnostic==read(out/"legacy-tail-topology-diagnostic.json"),"Legacy verdict changed")
    require(diagnostic["graph_equivalence_accepted"]is False,"Premature graph equivalence")
    methods();validate_view(out)
    check_derived(out)
    return dict(status="PASS_FRESH_NATIVE_PLANES_GRAPH_ANCHORS_REQUIRES_WIDTH_TOPOLOGY_AND_RC",
      native_graph_readback_passed=True,graph_equivalence_accepted=False,parent_gds_sha256=GDS_SHA,
      graph_sha256=sha(wire/"native05/result.json"),locations_sha256=sha(wire/"device-locations01.json"),
      anchors_sha256=sha(wire/"anchors08.json"),reference_sha256=sha(out/"reference-projection.json"),
      planes_sha256=sha(view/"native-planes.json"),full_input_bindings=bindings,
      legacy_topology_diagnostic_sha256=sha(out/"legacy-tail-topology-diagnostic.json"),
      fresh_RC_executed=False,electrical_accepted=False,qualified_pex=False,full_phy_accepted=False)

def main():
    p=argparse.ArgumentParser();p.add_argument("mode",choices=("restore",))
    p.parse_args();restore(OUT)

if __name__=="__main__":main()
