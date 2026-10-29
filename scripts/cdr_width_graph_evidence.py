#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0
"""Read-only evidence joins for one saved graph capsule. No network or authority."""
import hashlib
import json
import re
from pathlib import Path, PurePosixPath

ROOT=Path(__file__).resolve().parents[1]
PREFIX="docs/evidence/cdr-selector-width-fresh-graph-terminal-20261029."
REQUIRED_DOCS={
  "docs/evidence/cdr-selector-width-fresh-graph-terminal-20261029.summary.json": {
    "bytes": 1764262,
    "sha256": "62825d1992f63c4475e4f73cb16e5fccaf21a6228b157eb971fd4a7808d58d74"
  },
  "docs/evidence/cdr-selector-width-fresh-graph-terminal-20261029.parts.json": {
    "bytes": 1117,
    "sha256": "2a32d90bd33b8ed354777c6383c04090da00ffa90ead113f5eb620f33acdaa99"
  },
  "docs/evidence/cdr-selector-width-fresh-graph-terminal-20261029.reference.json": {
    "bytes": 24580,
    "sha256": "851a4a6b04648ad487456572242ced064f804817429545daeac0a17f5d7747b3"
  },
  "docs/evidence/cdr-selector-width-fresh-graph-terminal-20261029.graph.json": {
    "bytes": 290711,
    "sha256": "eeddbaddc06d413309fafc7b396944ada5fb72aa79f90c8f929f3213c2101adb"
  },
  "docs/evidence/cdr-selector-width-fresh-graph-terminal-20261029.planes.json": {
    "bytes": 244802,
    "sha256": "bb10a385e76e014c17d229919728e16085f06396becdf47f15ee53bb4c6b3dfe"
  },
  "docs/evidence/cdr-selector-width-fresh-graph-terminal-20261029.anchors.json": {
    "bytes": 1650535,
    "sha256": "966b5465750b6b35cc24cd8e10dca94313061d17692c6c46e99c50bc5d4c6193"
  },
  "docs/evidence/cdr-selector-width-fresh-graph-terminal-20261029.locations.json": {
    "bytes": 686544,
    "sha256": "11be358288af996c51a18bd7396ecce699ab84c9c5d93737a52d517dd0546a4f"
  },
  "docs/evidence/cdr-selector-width-fresh-graph-terminal-20261029.source-pins.json": {
    "bytes": 39228,
    "sha256": "1d18f591616b6eba928beaca81fee3263942cf031b2ad4fbade9c1d7f35fafab"
  },
  "docs/evidence/cdr-selector-width-fresh-graph-terminal-20261029.run.json": {
    "bytes": 14436,
    "sha256": "ca4e8d9026989e1a7acf019cef3b608a3b0b47baa0e8e24849b232badb2ae6e9"
  },
  "docs/evidence/cdr-selector-width-fresh-graph-terminal-20261029.jobs.json": {
    "bytes": 7918,
    "sha256": "23b4236481a050f77786b8dbfa3e3da20dfb4035f7b7f5d5657cc34041bdaa10"
  },
  "docs/evidence/cdr-selector-width-fresh-graph-terminal-20261029.release.json": {
    "bytes": 31974,
    "sha256": "eb9c2006e774a854a60f744906c73708a5f7aeb0449eed394e72ed43426d4f84"
  },
  "docs/evidence/cdr-selector-width-fresh-graph-terminal-20261029.tag.json": {
    "bytes": 575,
    "sha256": "6ded1c5231bbd06ee1c402d95a21c60ddf22b6977daf69356065aa0f6a4ab10c"
  },
  "docs/evidence/cdr-selector-width-fresh-graph-terminal-20261029.restore.json": {
    "bytes": 922280,
    "sha256": "8a9a0f3a6fc31eb46429a5bee6f4c39047b813968210c636ac600bab1c4648fb"
  },
  "docs/evidence/cdr-selector-width-fresh-graph-terminal-20261029.runtime.json": {
    "bytes": 3557,
    "sha256": "3404e6dc1d6c0a0ecead9614b43a8131b4b1bb2b268f9dd1fd9c5c9f72a31467"
  },
  "docs/evidence/cdr-selector-width-fresh-graph-terminal-20261029.legacy-topology.json": {
    "bytes": 1603,
    "sha256": "5aae742ed599257b215dd34ec5179cd83117652fc791a70cc49b4f817b891412"
  }
}
CONTRACT="scripts/cdr-v59-selector-column-width-contract.json"
CONTRACT_SHA="cc92ad1c6368219f4df0faf4989e7b2a77a1dab92898f4c92c6a69e4ead67106"
RUN=40808550817
HEAD="97705f184239c0c522582b9d8e82c542bd902b65"
RELEASE=427412807
TAG="cloud-results-40808550817-1-cdr-v59-selector-column-width-graph"
WORKFLOW=".github/workflows/cdr-v59-selector-column-width-graph-cloud.yml"
PRODUCER_ROOT="/home/runner/work/nssoc/nssoc/hw/soc/out/cloud-cdr-v59-selector-column-width-graph/"
PRODUCER_CONTRACT="/home/runner/work/nssoc/nssoc/"+CONTRACT
OLD="physical-input/saved-input/current-mim-bundle/canonical-current-view/"
FRESH="candidate/"
STATUS="PASS_FRESH_NATIVE_PLANES_GRAPH_ANCHORS_REQUIRES_WIDTH_TOPOLOGY_AND_RC"
GDS="parent/layout/nssoc_cdr_pd500_resistor_v59.gds"
LVS="parent/physical/lvs_flat/result.lvsdb"
CHILD="parent/inputs/sampler_cd/layout/nssoc_rx_sampler_active_input_layout_v57.gds"
GDS_SHA="fb8a0aea5b44627a513db62ed10fe87c66f30697930e1212d3689c7ae981c0c3"
LVS_SHA="46f7b57763441747cacf5740887fdadd0bfbc75c40549effd86afb7a60dba276"
MAP_HASHES={
 "full":"20906a8ac076bba41a2b3265686e81c3f477087dba05f3b6c0059fa14070645b",
 "old":"82194d08d00a8bf338517c6972b407ecc02ec67caec2fbc43de80131d5e49f5f",
 "fresh":"3d456d354f9296bb4add7fd6ab974dcae48d813fc8a1ec174fd9656ea99df590"}
REPORT_PATHS={"summary":"result.json","reference":"reference-projection.json",
 "graph":"candidate/wire/native05/result.json","planes":"candidate/native-planes.json",
 "anchors":"candidate/wire/anchors08.json","locations":"candidate/wire/device-locations01.json",
 "source-pins":"candidate/wire/source-pins.json","restore":"restore.json",
 "runtime":"runtime-smoke/result.json","legacy-topology":"legacy-tail-topology-diagnostic.json"}
COMMANDS=("restore-complete-physical-capsule","independent-source-reference","fresh-native-planes",
 "fresh-source-pin-recovery","probe01","locate01","anchors01","dedup01")
ACTIONS=("owned_process_cleanup","stop_heartbeat","join_heartbeat","restore_signal_2","restore_signal_15",
 "terminal_resource_sample","protected_source_integrity","complete_saved_input_integrity","complete_output_inventory")
FALSE_FIELDS=("automatic_retry","electrical_accepted","fresh_RC_executed","full_phy_accepted",
 "graph_equivalence_accepted","native_DRC_executed","native_LVS_executed","physical_accepted",
 "qualified_pex","simulation_executed")
CENSUS={"npn13G2":124,"sg13_lv_nmos":50,"rppd":98,"cap_cmim":7,"ptap1":221}

def require(value,reason):
    if not value:
        raise AssertionError(reason)

def canonical(value):
    return json.dumps(value,sort_keys=True,separators=(",",":"),allow_nan=False)

def digest(value):
    return hashlib.sha256(canonical(value).encode()).hexdigest()

def sha(path):
    with Path(path).open("rb")as stream:
        return hashlib.file_digest(stream,"sha256").hexdigest()

def member(name):
    require(type(name)is str and name and name!="." and "\\"not in name
      and not PurePosixPath(name).is_absolute() and ".."not in PurePosixPath(name).parts
      and PurePosixPath(name).as_posix()==name,"Unsafe evidence member")
    return name

def regular(root,name):
    root=Path(root);member(name);path=root/name
    require(root.is_absolute()and root.resolve()==root and root.is_dir(),"Noncanonical evidence root")
    require(path.is_file()and not any(p.is_symlink()for p in (path,*path.parents)),
      "Nonregular evidence member")
    return path

def source_guard():
    """Exact original report bytes; intentionally fails until root imports all listed docs."""
    result={}
    for name,proof in REQUIRED_DOCS.items():
        path=regular(ROOT,name)
        raw=path.read_bytes()
        require(len(raw)==proof["bytes"]and hashlib.sha256(raw).hexdigest()==proof["sha256"],
          "Changed required evidence: "+name)
        result[name[len(PREFIX):-5]]=json.loads(raw)
    raw=regular(ROOT,CONTRACT).read_bytes()
    require(hashlib.sha256(raw).hexdigest()==CONTRACT_SHA,"Changed original width contract")
    result["contract"]=json.loads(raw)
    return result

def doc_sha(name):
    return REQUIRED_DOCS[PREFIX+name+".json"]["sha256"]

def asset_projection(info):
    rows=info["assets"]
    require(type(rows)is list and len(rows)==14,"Incomplete graph release assets")
    require(len({r["id"]for r in rows})==len({r["name"]for r in rows})==14,"Duplicate release asset")
    for r in rows:
        require(type(r["id"])is int and type(r["size"])is int and r["size"]>0
          and r["state"]=="uploaded"and re.fullmatch("sha256:[0-9a-f]{64}",r["digest"]),
          "Incomplete uploaded asset identity")
    return sorted([{k:r[k]for k in ("id","name","size","digest")}for r in rows],key=lambda r:r["id"])

def live_binding(run,jobs,release,ref,saved_release):
    require(type(run["id"])is int and type(run["run_attempt"])is int
      and type(jobs["total_count"])is int and type(release["id"])is int,
      "Untyped live graph identity")
    require((run["id"],run["head_sha"],run["run_attempt"],run["event"],run["path"],
      run["status"],run["conclusion"])==(RUN,HEAD,1,"workflow_dispatch",WORKFLOW,"completed","success"),
      "Wrong or incomplete graph run")
    wanted={123233190376:"source-controls",123233387760:"graph"}
    require(jobs["total_count"]==len(jobs["jobs"])==2
      and {j["id"]for j in jobs["jobs"]}==set(wanted),"Wrong graph jobs")
    for j in jobs["jobs"]:
        require(type(j["id"])is int and type(j["run_id"])is int,"Untyped graph job identity")
        require(j["run_id"]==RUN and j["head_sha"]==HEAD and j["name"]==wanted[j["id"]]
          and j["status"]=="completed"and j["conclusion"]=="success","Incomplete graph job")
    require(release["id"]==RELEASE and release["tag_name"]==TAG and release["target_commitish"]==HEAD
      and release["draft"]is False and release["prerelease"]is True,"Wrong graph release")
    require(ref["ref"]=="refs/tags/"+TAG and ref["object"]["type"]=="commit"
      and ref["object"]["sha"]==HEAD,"Graph tag is not exact-source lightweight tag")
    assets=asset_projection(release)
    require(assets==asset_projection(saved_release),"Graph release asset identities changed")
    return dict(run_id=RUN,source_head=HEAD,run_attempt=1,release_id=RELEASE,tag=TAG,
      source_job=123233190376,graph_job=123233387760,assets=assets,
      acquisition_performed=False,execution_authorized=False)

def validate_live(run,jobs,release,ref):
    d=source_guard()
    return live_binding(run,jobs,release,ref,d["release"])

def normalized_inputs(report):
    require(type(report["inputs"])is dict and report["inputs"],"Missing report inputs")
    result={}
    for path,value in report["inputs"].items():
        require(type(path)is str and PurePosixPath(path).is_absolute()
          and PurePosixPath(path).as_posix()==path,"Noncanonical producer input path")
        if type(value)is dict:
            require(set(value)=={"bytes","sha256"}and type(value["bytes"])is int and value["bytes"]>=0,
              "Malformed sized input binding")
            h=value["sha256"]
        else:
            h=value
        require(type(h)is str and re.fullmatch("[0-9a-f]{64}",h),"Malformed input digest")
        result[path]=h
    return result

def maps(d):
    s=d["summary"]
    require((s["run_id"],s["source_head"],s["run_attempt"],s["status"])==(RUN,HEAD,1,STATUS),
      "Wrong saved graph summary")
    require(s["terminal_finalization_complete"]is s["native_graph_readback_passed"]is s["graph_started"]is True,
      "Incomplete saved graph terminal")
    require(all(s[k]is False for k in FALSE_FIELDS)and s["original_failure_preserved"]is True,
      "Borrowed graph/physical/electrical acceptance")
    require(s["source_physical_run"]==40800207491
      and s["source_physical_head"]=="20e4cf92f79b9e2742373dc058a855a979f60db1"
      and s["complete_input_members"]==3992 and s["consumed_view"]=="physical-input",
      "Wrong prior physical lineage")
    require([r["label"]for r in s["commands"]]==list(COMMANDS),"Incomplete command sequence")
    for r in s["commands"]:
        require(r["returncode"]==0 and r["supervision_failure"]is None and r["memory_read_error"]is None
          and r["maximum_group_rss_kib"]==10485760 and r["minimum_available_kib"]==2097152
          and r["process_group_cleanup"]["remaining_live"]==[],"Incomplete graph command")
    require([r["action"]for r in s["terminal_actions"]]==list(ACTIONS)
      and all(r["completed"]is True for r in s["terminal_actions"]),"Incomplete terminal actions")
    require(s["terminal_evidence"]["owned_process_cleanup"]["remaining_live"]==[],
      "Graph process still live")
    require(s["terminal_evidence"]["protected_source_integrity"]["protected_files"]==1040,
      "Wrong tested source census")
    require(s["terminal_evidence"]["complete_saved_input_integrity"]["complete_input"]==
      dict(all_hashes_unchanged=True,exact_inventory=True,files=3992),"Incomplete prior capsule")
    reservation=s["reservation"]
    require(reservation["release_id"]==RELEASE and reservation["tag"]==TAG
      and reservation["tested_source"]==HEAD and reservation["target_verified"]is True
      and reservation["externally_reserved"]is True and reservation["assets_overwritten"]is False,
      "Wrong original reservation")
    outputs=s["outputs"];require(type(outputs)is dict and len(outputs)==4102 and "result.json"not in outputs,
      "Incomplete full output map")
    for n,h in outputs.items():
        member(n);require(type(h)is str and re.fullmatch("[0-9a-f]{64}",h),"Malformed saved member hash")
    full={**outputs,"result.json":doc_sha("summary")}
    roots={"old":{n[len(OLD):]:h for n,h in outputs.items()if n.startswith(OLD)},
      "fresh":{n[len(FRESH):]:h for n,h in outputs.items()if n.startswith(FRESH)}}
    require(len(full)==4103 and len(roots["old"])==605 and len(roots["fresh"])==75,
      "Wrong complete root projections")
    require(digest(full)==MAP_HASHES["full"]and all(digest(roots[k])==MAP_HASHES[k]for k in roots),
      "Changed inventory projection")
    require(roots["old"]==d["contract"]["baseline_inventory"],"Original605 differs from contract")
    require(s["candidate_gds_sha256"]==roots["fresh"][GDS]==GDS_SHA
      and roots["fresh"][LVS]==LVS_SHA,"Wrong physically verified GDS/LVS")
    for name,path in REPORT_PATHS.items():
        require(full[path]==doc_sha(name),"Report not joined to complete output map")
    parts=d["parts"]
    require(parts["format"]=="ordered-tar-gzip-parts-v1"
      and parts["source_directory"]=="cloud-cdr-v59-selector-column-width-graph"
      and parts["stem"]=="cdr-v59-selector-column-width-graph-40808550817-1"
      and parts["bytes"]==756084331
      and parts["sha256"]=="65d2de3995696fac34df3119396024d5c52b2c33cd09d43a9c892f33cef34d61",
      "Wrong complete graph archive manifest")
    require([r["index"]for r in parts["parts"]]==[0,1]
      and [r["bytes"]for r in parts["parts"]]==[536870912,219213419],"Incomplete ordered archive parts")
    assets={r["name"]:r for r in d["release"]["assets"]}
    for r in parts["parts"]:
        require(r["name"]in assets and assets[r["name"]]["size"]==r["bytes"]
          and assets[r["name"]]["digest"]=="sha256:"+r["sha256"],"Archive part/release mismatch")
    for name in ("summary","parts","reference","graph","planes","anchors","locations","source-pins","restore","runtime","legacy-topology"):
        a=assets[parts["stem"]+"."+name+".json"];proof=REQUIRED_DOCS[PREFIX+name+".json"]
        require(a["size"]==proof["bytes"]and a["digest"]=="sha256:"+proof["sha256"],
          "Direct report/release mismatch")
    live_binding(d["run"],d["jobs"],d["release"],d["tag"],d["release"])
    return full,roots

def expected_files():
    d=source_guard()
    return maps(d)[0]

def expected_roots():
    d=source_guard()
    return maps(d)[1]

def tree(root):
    root=Path(root)
    require(root.is_absolute()and root.resolve()==root and root.is_dir()
      and not any(p.is_symlink()for p in (root,*root.parents)),"Noncanonical restored root")
    result={}
    for path in sorted(root.rglob("*")):
        require(not path.is_symlink(),"Symlink restored member")
        if path.is_dir():
            continue
        require(path.is_file(),"Nonregular restored member")
        name=member(path.relative_to(root).as_posix())
        result[name]=dict(bytes=path.stat().st_size,sha256=sha(path))
    return result

def map_binding(root,full,path,value,allow_contract=False):
    h=value["sha256"]if type(value)is dict else value
    require(type(path)is str and PurePosixPath(path).as_posix()==path,"Noncanonical original path")
    if path.startswith(PRODUCER_ROOT):
        relative=member(path[len(PRODUCER_ROOT):])
        require(relative in full and full[relative]==h,"Original path/hash not in authentic capsule")
        actual=regular(root,relative)
        require(sha(actual)==h,"Relocated bound input changed")
        if type(value)is dict:
            require(actual.stat().st_size==value["bytes"],"Relocated bound input size changed")
        return dict(original_path=path,member=relative,sha256=h,bytes=actual.stat().st_size,
          original_report_rewritten=False)
    require(allow_contract and path==PRODUCER_CONTRACT and h==CONTRACT_SHA,
      "Unapproved external report input")
    actual=regular(ROOT,CONTRACT);require(sha(actual)==h,"Original contract input changed")
    return dict(original_path=path,repository_path=CONTRACT,sha256=h,bytes=actual.stat().st_size,
      original_report_rewritten=False)

def report_joins(root,d,full,roots):
    """Only named current-producer reports are mapped; historic nested reports stay original."""
    s=d["summary"];candidate=s["candidate"]
    require(candidate["status"]==STATUS and candidate["native_graph_readback_passed"]is True
      and all(candidate[k]is False for k in ("electrical_accepted","fresh_RC_executed","full_phy_accepted",
        "graph_equivalence_accepted","qualified_pex")),"Incomplete or overclaiming candidate")
    for name,field in (("graph","graph_sha256"),("locations","locations_sha256"),("anchors","anchors_sha256"),
      ("planes","planes_sha256"),("reference","reference_sha256"),("legacy-topology","legacy_topology_diagnostic_sha256")):
        require(candidate[field]==doc_sha(name),"Candidate/report digest mismatch")
    require(candidate["parent_gds_sha256"]==GDS_SHA,"Candidate parent digest mismatch")
    planes=d["planes"];parent_geometry=planes["parent_geometry"]
    require(planes["status"]=="PASS_PD500_NATIVE160_PLANES_51_NETS_19_FAULTS"
      and len(planes["anchors"])==160 and len(planes["controls"])==19
      and planes["qualified_pex"]is planes["closed_loop"]is planes["full_phy_accepted"]is False,
      "Incomplete original native plane proof")
    require(parent_geometry["status"]=="PASS_ALL16_ACTUAL_PLACEMENTS_AND_NINE_NATIVE_LEAF_DRAWINGS"
      and len(parent_geometry["actual_placements"])==16 and len(parent_geometry["checked_layers_by_kind"])==9
      and len(parent_geometry["controls"])==5 and parent_geometry["full_phy_accepted"]is False,
      "Incomplete independent parent geometry proof")
    graph=d["graph"];locations=d["locations"];anchors=d["anchors"];pins=d["source-pins"]
    require(graph["status"]=="PASS_GEOMETRIC_PUMP_WIRE_COMPONENT_BINDING_NO_RC"
      and graph["native_devices"]==CENSUS,"Wrong saved graph scope")
    for k,n in (("native_device_count",500),("native_terminal_count",1446),("wire_component_count",113),
      ("native_net_count",238),("native_electrical_net_count",114)):
        require(type(graph[k])is int and graph[k]==n,"Wrong graph census: "+k)
    require(len(graph["wire_components"])==113 and len(graph["native_net_coverage"])==238
      and len(graph["native_ports"])==len(set(graph["native_ports"]))==25,
      "Incomplete graph rows/ports")
    require(graph["no_wire_geometry_change"]is graph["no_component_union_by_native_label"]is True
      and graph["wire_rc_extracted"]is graph["full_pex_qualified"]is graph["substrate_r_modeled"]is False,
      "Wrong graph qualification flags")
    require(locations["status"]=="PASS_ALL_500_DEVICES_HAVE_UNIQUE_PHYSICAL_PCELL_ENCLOSURE"
      and len(locations["devices"])==500 and locations["model_census"]==CENSUS
      and locations["native_terminal_count"]==1446 and locations["qualified_pex"]is False,
      "Incomplete saved locations")
    require(anchors["status"]=="PASS_EXACT_PHYSICAL_POINTS_FOR_ALL_LOGICAL_REFERENCES"
      and anchors["logical_anchor_count"]==anchors["physical_anchor_count"]==len(anchors["anchors"])==978
      and len(anchors["rows"])==1446 and anchors["public_ports"]==25
      and anchors["dispositions"]==dict(ACTUAL_TERMINAL_METAL_POINT_REFERENCE=953,
        RETAINED_INTRINSIC_BODY_NO_SUBSTRATE_RESISTANCE=493)
      and all(anchors[k]is False for k in ("point_quantization_used_to_merge","wire_rc_extracted",
        "full_pex_qualified","distributed_intrinsic_terminal_model")),"Incomplete saved anchor proof")
    require(pins["status"]=="PASS_RECOVERED_SOURCE_PIN_BOXES_ON_IDENTICAL_PRIMITIVE_DRAWING"
      and pins["target_gds_sha256"]==GDS_SHA and pins["target_geometry_edited"]is False
      and pins["missing_referenced_primitive_rejected"]is True,"Incomplete source-pin proof")
    reports={"parent-geometry":parent_geometry,"planes":planes,"source-pins":pins,
      "graph":graph,"locations":locations,"anchors":anchors}
    require(set(candidate["full_input_bindings"])==set(reports),"Incomplete report binding groups")
    sizes={"parent-geometry":13,"planes":6,"source-pins":13,"graph":3,"locations":4,"anchors":9}
    bindings={}
    for name,report in reports.items():
        require(normalized_inputs(report)==candidate["full_input_bindings"][name]
          and len(report["inputs"])==sizes[name],"Saved full input bindings differ: "+name)
        bindings[name]=[map_binding(root,full,path,value)for path,value in report["inputs"].items()]
    unique={r["original_path"]for rows in bindings.values()for r in rows}
    require(sum(map(len,bindings.values()))==48 and len(unique)==30,"Wrong full report binding census")
    cell_sources=[v["source"]for v in pins["cells"].values()if "source"in v]
    require(len(cell_sources)==59 and all(p in pins["inputs"]for p in cell_sources),
      "Source-cell pointer is not an authenticated recovered input")
    require(set(graph["outputs"])=={"wires.gds","wires.l2n"},"Incomplete wire output binding")
    for name,value in graph["outputs"].items():
        path=regular(root,FRESH+"wire/native05/"+member(name))
        require(full[FRESH+"wire/native05/"+name]==value["sha256"]==sha(path)
          and path.stat().st_size==value["bytes"],"Wire output size/hash mismatch")
    reference=d["reference"]
    require(reference["status"]=="PASS_INDEPENDENT26BOX_SOURCE_REFERENCE_AND_SERIALIZED_REREAD"
      and reference["added_raw_record_count"]==len(reference["added_raw_records"])==26
      and reference["proposal"]==d["contract"]["declared_rectangles"],"Incomplete independent26 reference")
    require(all(reference[k]is True for k in ("all_original_source_raw_text_properties_hierarchy_preserved",
      "independent_source_used","original_capsule_unmodified","original_source_child_drawings_matched_parent"))
      and all(reference[k]is False for k in ("electrical_accepted","engineering_parent_geometry_edited",
        "full_phy_accepted","graph_equivalence_accepted","new_physical_qualification",
        "parent_as_own_reference_used","qualified_pex")),"Wrong independent-reference scope")
    require(reference["source_child_relative"]==CHILD and reference["original_parent_gds_sha256"]==GDS_SHA,
      "Wrong reference child/physical-parent role")
    original={n[len("parent/"):]:h for n,h in roots["old"].items()if n.startswith("parent/inputs/")}
    fresh={n[len("parent/"):]:h for n,h in roots["fresh"].items()if n.startswith("parent/inputs/")}
    require(len(original)==len(fresh)==48 and original==reference["original_input_hashes"]
      and fresh==reference["derived_input_hashes"]and set(original)==set(fresh),"Incomplete reference input maps")
    relative=CHILD[len("parent/"):]
    require({n for n in original if original[n]!=fresh[n]}=={relative}
      and original[relative]==reference["source_child_before_sha256"]
      and fresh[relative]==reference["source_child_after_sha256"],"Unapproved reference source-file change")
    normalized_inputs(reference)
    require(len(reference["inputs"])==5,"Wrong reference binding census")
    bindings["reference"]=[map_binding(root,full,p,v,True)for p,v in reference["inputs"].items()]
    all_bound=[r for rows in bindings.values()for r in rows]
    require(len({r["original_path"]for r in all_bound if "member"in r})==33
      and sum("repository_path"in r for r in all_bound)==1,"Wrong complete external/path policy")
    legacy=d["legacy-topology"]
    require(legacy["status"]=="LEGACY_COMPARATOR_REJECTED"
      and legacy["legacy_material_policy_applicable"]is legacy["graph_equivalence_accepted"]is False,
      "Legacy diagnostic converted to acceptance")
    for name,h in legacy["original_input_hashes"].items():
        require(roots["old"]["wire/"+member(name)]==h,"Old legacy input changed")
    for name,h in legacy["fresh_input_hashes"].items():
        require(roots["fresh"]["wire/"+member(name)]==h,"Fresh legacy input changed")
    return bindings

def parent_and_derivation(root,full,roots):
    meta_path=regular(root,FRESH+"parent/layout/result.json")
    meta=json.loads(meta_path.read_text())
    original=json.loads(regular(root,OLD+"parent/layout/result.json").read_text())
    require(meta["status"]=="DERIVED_METADATA_FOR_FRESH_READBACK_NOT_NEW_PHYSICAL_ACCEPTANCE"
      and meta["original_metadata_retained"]is True
      and meta["physical_accepted"]is meta["electrical_accepted"]is meta["qualified_pex"]is False,
      "Wrong current metadata scope")
    for field in ("source_plan","placements","primitive_census","ports"):
        require(meta[field]==original[field],"Original metadata field changed: "+field)
    require(len(meta["placements"])==16 and len(meta["ports"])==25
      and sum(meta["primitive_census"].values())==500,"Incomplete parent metadata")
    normalized_inputs(meta)
    require(set(meta["inputs"])=={PRODUCER_ROOT+OLD+"parent/layout/result.json",
      PRODUCER_ROOT+"physical-input/layout/result.json"},"Wrong current metadata input paths")
    mapped=[map_binding(root,full,p,v)for p,v in meta["inputs"].items()]
    layout={n[len(FRESH+"parent/layout/"):]:h for n,h in full.items()
      if n.startswith(FRESH+"parent/layout/")and n!=FRESH+"parent/layout/result.json"}
    require(meta["outputs"]==layout,"Current metadata layout output mismatch")
    derivation=json.loads(regular(root,"derived-methods.json").read_text())
    require(set(derivation)=={"check_width_parent_geometry.py","width_planes.py","width_source_pins.py"},
      "Incomplete exact reader derivation")
    for name,row in derivation.items():
        require(sha(regular(ROOT,member(row["source"])))==row["source_sha256"]
          and full[FRESH+"methods/"+name]==row["generated_sha256"],"Reader derivation source/output mismatch")
    wire_sources={}
    for name in ("probe01.py","locate01.py","anchors01.py","dedup01.py"):
        path="docs/evidence/cdr-v59-tail-exact-wire-methods-20261026/"+name
        require(sha(regular(ROOT,path))==full[FRESH+"wire/"+name],"Original copied wire reader changed")
        wire_sources[path]=full[FRESH+"wire/"+name]
    return dict(parent_metadata_inputs=mapped,derived_reader_records=derivation,
      unchanged_wire_reader_sha256=wire_sources)

def validate_restored(root):
    d=source_guard();full,roots=maps(d);root=Path(root)
    before=tree(root)
    require({n:r["sha256"]for n,r in before.items()}==full,"Restored full4103 inventory differs")
    for name,path in REPORT_PATHS.items():
        require(regular(root,path).read_bytes()==regular(ROOT,PREFIX+name+".json").read_bytes(),
          "Restored direct report bytes differ: "+name)
    bindings=report_joins(root,d,full,roots)
    metadata=parent_and_derivation(root,full,roots)
    restored_physical={n[len("physical-input/"):]:h for n,h in full.items()if n.startswith("physical-input/")}
    prior=d["restore"]["extracted"]
    require(len(restored_physical)==3992 and prior["regular_members"]==3992
      and prior["full_inventory_verified"]is True
      and {n:r["sha256"]for n,r in prior["complete_member_hashes"].items()}==restored_physical,
      "Nested prior physical map mismatch")
    require(d["summary"]["restore"]==d["restore"]
      and d["summary"]["runtime_smoke"]==d["runtime"],"Embedded original proof differs")
    runtime=d["runtime"]
    require(runtime["status"]=="PASS_PINNED_APPIMAGE_INTERPRETER_AND_PYA_IMPORT"
      and runtime["accepted"]is True and runtime["returncode"]==0 and runtime["timed_out"]is False
      and runtime["cleanup"]["remaining_live"]==[]
      and runtime["appimage_before_sha256"]==runtime["appimage_after_sha256"]==
        runtime["expected_appimage_sha256"]=="d6a349ec65be11456e96c4981d35f63ca34d3c85daf79a51e1ccb907bb5d7466",
      "Incomplete original runtime evidence")
    require(tree(root)==before,"Restored input changed during validation")
    source_guard()
    return dict(status="PASS_EXACT_SAVED_GRAPH_EVIDENCE_JOINS_ONLY",run_id=RUN,source_head=HEAD,
      complete_members=4103,complete_member_hashes=before,inventory_sha256=digest(full),
      expected_roots={k:dict(members=len(v),inventory_sha256=digest(v))for k,v in roots.items()},
      mapped_report_inputs=bindings,parent_metadata_and_derivation=metadata,
      original_report_bytes_unchanged=True,native_comparison_executed=False,
      archive_acquisition_performed=False,execution_authorized=False,
      graph_equivalence_accepted=False,physical_accepted=False,qualified_pex=False,
      electrical_accepted=False,full_phy_accepted=False)
