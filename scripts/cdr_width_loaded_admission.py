#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0
"""Disabled current-width RC input admission; no electrical verdict or numerical rewrite."""
import copy,hashlib,json,os,re
from pathlib import Path
import cdr_v59_tail_loaded_admission as old

ROOT=Path(__file__).resolve().parents[1]
METHOD="scripts/cdr-width-loaded-admission-methods.json"
PRIOR="scripts/cdr-selector-width-fresh-rc-execution-methods.json"
PRIOR_SHA="1545607eb965218cc7aef2491f64df4df5c23e31856c9169c8d59b7ac03f1a02"
PRIOR_COUNT=1184
PREFIX="docs/evidence/cdr-selector-width-fresh-rc-native-terminal-20261029/"
RECEIPT=PREFIX+"receipt.json"
RECEIPT_SHA="a551d56a0b1c8cad68b6305dab262cf02eddbd5fb8df5bcf96477d504568ef5c"
RUN=40830441311
HEAD="7ddf83d17a3b3fe0efb1eb31594b7d4d3e831b8f"
RELEASE=427537846
TAG="cloud-results-40830441311-1-cdr-selector-width-fresh-rc"
BRANCH="codex/cdr-width-loaded-admission"
MODEL=old.MODEL
CASES=old.CASES
SUMMARY=PREFIX+"direct/summary.json"
STAGE=PREFIX+"direct/MIM-precision-result.json"
RAW="terminal/hw/soc/out/cloud-cdr-selector-width-fresh-rc/result.json"
PUBLICATION="terminal/hw/soc/out/cloud-cdr-selector-width-fresh-rc-publication/publication.json"
RAW_SHA="9d128f021278fc2a3fa0be68db8f8c0b73824fa24939341802ba3ba6bfe1a820"
SUMMARY_SHA="c5695d1cde81f3aac997f461ba6e663eed7e5dfb827600d84e1ec768d84f6a23"
MODEL_MEMBER="mim/composition/pd500-mim-wire.spice"
MODEL_SHA="47124290075ec32734494f3d9a6307c9c9e930aafd7fe5d27a66b9c6f1e909ee"
PLANES_MEMBER="mim/precise/source/native-planes.json"
PLANES_SHA="bb10a385e76e014c17d229919728e16085f06396becdf47f15ee53bb4c6b3dfe"
PASS="PASS_FRESH_WIDTH500_BINDING_WIRE_RC_SEVEN_MIM_TWO_ORDERS_REQUIRES_ORIGINAL_ELECTRICAL_MATRIX"
COUNTS={"devices":500,"R":24356,"C":15566}
CENSUS={"npn13G2":124,"sg13_lv_nmos":50,"rppd":98,"cap_cmim":7,"ptap1":221}
PHASES=("restore-complete-graph4103-and-current75","fresh-current500-binding","fresh-current500-wire-RC","fresh-seven-MIM-both-native-orders")
FALSE=("automatic_retry","physical_geometry_regenerated","simulation_executed","physical_accepted","electrical_accepted","qualified_pex","full_phy_accepted","original_electrical_rejection_overridden")
REQUIRED={'direct/summary.json': {'path': 'docs/evidence/cdr-selector-width-fresh-rc-native-terminal-20261029/direct/summary.json', 'bytes': 3271162, 'sha256': 'c5695d1cde81f3aac997f461ba6e663eed7e5dfb827600d84e1ec768d84f6a23'}, 'direct/composition.json': {'path': 'docs/evidence/cdr-selector-width-fresh-rc-native-terminal-20261029/direct/composition.json', 'bytes': 969974, 'sha256': 'e13d954369f1a4eb4161d709a6e46524714fe8ceb98e7a7d31e978f5e817d6d3'}, 'direct/joint-admission.json': {'path': 'docs/evidence/cdr-selector-width-fresh-rc-native-terminal-20261029/direct/joint-admission.json', 'bytes': 1952278, 'sha256': '4bbfd0e7ae314a85e49912b077a30deebbb72698c48f0e4c1f2f1866d46017aa'}, 'direct/canonical-candidate.json': {'path': 'docs/evidence/cdr-selector-width-fresh-rc-native-terminal-20261029/direct/canonical-candidate.json', 'bytes': 9244, 'sha256': '2c0e68e56918bcfb01bd7393b256e3341ffcd44ab394d6479b6668fc3f9d94d1'}, 'run.json': {'path': 'docs/evidence/cdr-selector-width-fresh-rc-native-terminal-20261029/run.json', 'bytes': 14425, 'sha256': '5a417eeee03f6819962ff33db2b71643a197a282f39e1b8843a5965e209735d9'}, 'jobs.json': {'path': 'docs/evidence/cdr-selector-width-fresh-rc-native-terminal-20261029/jobs.json', 'bytes': 11967, 'sha256': '4c885675c17273d851d91414162aa6db30ab9deb7ad06829dace3dbb5b3fe5eb'}, 'release.json': {'path': 'docs/evidence/cdr-selector-width-fresh-rc-native-terminal-20261029/release.json', 'bytes': 44415, 'sha256': '2204f51d462fdf440bf8c05136852e48ea49de7c11b13efbfc6fc16485fe5ced'}, 'tag-ref.json': {'path': 'docs/evidence/cdr-selector-width-fresh-rc-native-terminal-20261029/tag-ref.json', 'bytes': 548, 'sha256': 'a8a096b0c9b602f455d3e4ab2d9b8d6f653fae099b2dfcfdbdfae943248a432e'}, 'complete-native-restore-map.json': {'path': 'docs/evidence/cdr-selector-width-fresh-rc-native-terminal-20261029/complete-native-restore-map.json', 'bytes': 1210084, 'sha256': '073e3f34e10f4f7b8d8ab039d6b084f7c7861696f23dc564abbf3aae0d8bf65a'}, 'direct/MIM-precision-result.json': {'path': 'docs/evidence/cdr-selector-width-fresh-rc-native-terminal-20261029/direct/MIM-precision-result.json', 'bytes': 25020377, 'sha256': 'a97d30fd66c020c3be36bee2e44c2f7032f09f954ead82bdc23d0a79c2aaf6c5'}, 'direct/binding-result.json': {'path': 'docs/evidence/cdr-selector-width-fresh-rc-native-terminal-20261029/direct/binding-result.json', 'bytes': 4471125, 'sha256': '519c03e1b3e14ae44dbc973773afdc10922ed7450cef3a26d032e482916e9806'}, 'direct/binding.json': {'path': 'docs/evidence/cdr-selector-width-fresh-rc-native-terminal-20261029/direct/binding.json', 'bytes': 351751, 'sha256': 'eec8d5f065b6da3d57c83c53c63d62b3fd3b1765c5c53b2d02a7b76a5ee4556a'}, 'direct/wire-RC-result.json': {'path': 'docs/evidence/cdr-selector-width-fresh-rc-native-terminal-20261029/direct/wire-RC-result.json', 'bytes': 4385753, 'sha256': 'e5cc28e2dc41f8453f2f8e8aca630e4e0c4c3b01097cc381e3ed7dd7329df8a8'}, 'direct/parts.json': {'path': 'docs/evidence/cdr-selector-width-fresh-rc-native-terminal-20261029/direct/parts.json', 'bytes': 1085, 'sha256': '137962dd65b118cc24652f9ceb4eb6a8b38a0a8232ec8144c87a3e3d9d73a9fb'}, 'direct/direct-publication-plan.json': {'path': 'docs/evidence/cdr-selector-width-fresh-rc-native-terminal-20261029/direct/direct-publication-plan.json', 'bytes': 4051, 'sha256': 'e99b5ed8a9a92c4a47ebc3df2adc9584587e826d73c3eafb78244fdae0354ec1'}, 'terminal/hw/soc/out/cloud-cdr-selector-width-fresh-rc/result.json': {'path': 'docs/evidence/cdr-selector-width-fresh-rc-native-terminal-20261029/terminal/hw/soc/out/cloud-cdr-selector-width-fresh-rc/result.json', 'bytes': 3271064, 'sha256': '9d128f021278fc2a3fa0be68db8f8c0b73824fa24939341802ba3ba6bfe1a820'}, 'terminal/hw/soc/out/cloud-cdr-selector-width-fresh-rc-publication/publication.json': {'path': 'docs/evidence/cdr-selector-width-fresh-rc-native-terminal-20261029/terminal/hw/soc/out/cloud-cdr-selector-width-fresh-rc-publication/publication.json', 'bytes': 8805, 'sha256': '4c4cf7a89b0ae6a24b07b09c2702987f6a3580fd05dd7698b9df4ed6fb0cb341'}}
require=old.require
sha=old.sha
regular=old.regular
relative=old.relative
write=old.write
fetch=old.fetch
release=old.release

def exact(a,b,reason):
    require(json.dumps(a,sort_keys=True,separators=(",",":"),allow_nan=False)==json.dumps(b,sort_keys=True,separators=(",",":"),allow_nan=False),reason)

def methods():
    m=json.loads(regular(ROOT,METHOD).read_bytes())
    require(m["schema"]=="cdr-width-loaded-input-admission-v1","Wrong loaded admission method")
    old.validate_authorizations(m)
    require(m["cases"]==list(CASES)and m["producer_source"]==HEAD and m["producer_run"]==RUN,"Method producer/cases changed")
    prior=regular(ROOT,PRIOR);require(sha(prior)==PRIOR_SHA,"Historical execution method changed")
    previous=json.loads(prior.read_bytes())["protected_sha256"]
    require(len(previous)==PRIOR_COUNT and all(m["protected_sha256"].get(n)==h for n,h in previous.items()),"Inherited source pins changed")
    require(m["protected_sha256"].get(PRIOR)==PRIOR_SHA and m["protected_sha256"].get(RECEIPT)==RECEIPT_SHA,"Admission proof pins omitted")
    for n in ("scripts/cdr_width_loaded_admission.py","scripts/check_cdr_width_loaded_admission.py","docs/evidence/cdr-width-loaded-admission-source-review-20261029.json"):
        require(n in m["protected_sha256"],"New admission source pin omitted")
    for n,h in m["protected_sha256"].items():
        require(type(h)is str and re.fullmatch("[0-9a-f]{64}",h)and sha(regular(ROOT,n))==h,"Protected loaded source changed: "+n)
    return m

def source_guard():
    m=methods();raw=regular(ROOT,RECEIPT).read_bytes()
    require(hashlib.sha256(raw).hexdigest()==RECEIPT_SHA,"Terminal receipt changed")
    receipt=json.loads(raw)
    require(receipt["run"]==RUN and receipt["source"]==HEAD and receipt["terminal"]=="success","Terminal receipt identity changed")
    # Full log bodies stay protected without copying or parsing them as model inputs.
    for n,spec in receipt["files"].items():
        require(m["protected_sha256"].get(n)==spec["sha256"],"Complete proof file unprotected")
        path=regular(ROOT,n);require(path.stat().st_size==spec["bytes"]and sha(path)==spec["sha256"],"Complete proof bytes changed")
    docs={}
    for name,spec in REQUIRED.items():
        exact(receipt["files"][spec["path"]],{"bytes":spec["bytes"],"sha256":spec["sha256"]},"Required report receipt changed")
        data=regular(ROOT,spec["path"]).read_bytes()
        require(len(data)==spec["bytes"]and hashlib.sha256(data).hexdigest()==spec["sha256"],"Required report bytes changed")
        docs[name]=json.loads(data)
    validate_reports(docs)
    return docs

def submap(full,prefix):
    return {n[len(prefix):]:h for n,h in full.items()if n.startswith(prefix)}

def nested(full,prefix,report,raw_hash,count):
    expected={**report["outputs"],"result.json":raw_hash}
    require(len(expected)==count,"Nested complete output count changed")
    exact(submap(full,prefix),expected,"Nested complete output map changed")
    return expected

def validate_reports(d):
    s=d["direct/summary.json"];raw=d[RAW];full=d["complete-native-restore-map.json"]
    require(len(full)==6647 and len(s["outputs"])==6646 and len(raw["outputs"])==6645,"Complete current RC inventory changed")
    exact(full,{**s["outputs"],"result.json":RAW_SHA},"Raw result substituted by publication summary")
    exact(s["outputs"],{**raw["outputs"],"publication-driver.log":"704f93a52832b1db4821218ee91e0d70a1c872ca4ad9f433f39db82e274b106f"},"Publication-only log delta changed")
    exact({k:v for k,v in s.items()if k!="outputs"},{k:v for k,v in raw.items()if k!="outputs"},"Raw/publication result semantics changed")
    for n,h in full.items():relative(n);require(type(h)is str and re.fullmatch("[0-9a-f]{64}",h),"Invalid full member digest")
    require(s["status"]==PASS and s["source_head"]==HEAD and type(s["run_id"])is int and s["run_id"]==RUN and type(s["run_attempt"])is int and s["run_attempt"]==1,"Current producer identity changed")
    require(all(s[k]is True for k in ("binding_executed","extraction_executed","fresh_RC_pipeline_complete","terminal_finalization_complete"))and all(s[k]is False for k in FALSE)and s["historical_authority_reused"]is False,"Current producer completion/scope changed")
    require(s["original_graph_run"]==40808550817 and s["original_graph_source"]=="97705f184239c0c522582b9d8e82c542bd902b65"and s["original_width_run"]==40815684037 and s["original_width_source"]=="214ec651fd501de7e2f49a38509b184a1fd66f8d"and(s["complete_graph_members"],s["current_members"])==(4103,75),"Width/graph lineage changed")
    require([c["label"]for c in s["commands"]]==list(PHASES)and all(c["returncode"]==0 and c["supervision_failure"]is None and not c["process_group_cleanup"]["remaining_live"]for c in s["commands"]),"Current four phases incomplete")
    require(all(x["completed"]is True for x in s["terminal_actions"])and not s.get("terminal_errors"),"Current terminal finalization failed")
    pub=d[PUBLICATION]
    require(pub["status"]=="PASS_COMPLETE_FRESH_WIDTH_RC_EVIDENCE_PUBLICATION_ONLY"and pub["source_head"]==HEAD and pub["run_id"]==RUN and pub["engineering_accepted"]is False,"Complete current publication missing")
    assets=d["release.json"]["assets"]
    exact(sorted((x["id"],x["name"],x["bytes"],x["sha256"])for x in pub["assets"]),sorted((x["id"],x["name"],x["size"],x["digest"].removeprefix("sha256:"))for x in assets),"Publication complete asset receipt changed")
    plan=d["direct/direct-publication-plan.json"]
    require(plan["summary_sha256"]==SUMMARY_SHA and plan["parts_sha256"]==REQUIRED["direct/parts.json"]["sha256"]and plan["zero_byte_files_preserved_in_archive"]is True and plan["empty_bytes_replaced"]is False,"Direct publication plan changed")
    require(len(plan["files"])==15 and len({x["member"]for x in plan["files"]})==15,"Direct publication path ambiguity")
    for row in plan["files"]:
        spec=REQUIRED.get("direct/"+row["suffix"])
        require(full.get(row["member"])==row["sha256"]and row["disposition"]=="direct_and_archive","Direct raw member differs")
        if spec:require((row["sha256"],row["bytes"])==(spec["sha256"],spec["bytes"]),"Direct report hash changed")
    b=d["direct/binding-result.json"];binding=d["direct/binding.json"];rc=d["direct/wire-RC-result.json"];mim=d["direct/MIM-precision-result.json"];co=d["direct/composition.json"]
    for prefix,name,report,count in (("binding/","binding-result.json",b,53),("wire-stage/","wire-RC-result.json",rc,5),("mim/","MIM-precision-result.json",mim,1963)):
        nested(full,prefix,report,REQUIRED["direct/"+name]["sha256"],count)
        require(report["source_head"]==HEAD and report["sources_unchanged"]is True,"Nested producer source changed")
    require(s["binding_result_sha256"]==REQUIRED["direct/binding-result.json"]["sha256"]and s["wire_RC_result_sha256"]==REQUIRED["direct/wire-RC-result.json"]["sha256"]and s["completed_pipeline"]["summary_sha256"]==REQUIRED["direct/MIM-precision-result.json"]["sha256"],"Nested terminal hash changed")
    exact(b["binding"],binding,"Binding report/file differs");exact(binding["census"],CENSUS,"Device census changed")
    require(len(binding["devices"])==len({x["native_id"]for x in binding["devices"]})==500,"Native binding identity changed")
    exact(mim["composition"]["contract"],co,"Composition report/file differs");exact(co["counts"],COUNTS,"Actual current RC counts changed")
    require(co["interface"]==binding["native_ports"]+["wire_cref"]and len(set(co["interface"]))==26,"Current native port order changed")
    require(len(co["device_records"])==500 and {x["native_id"]for x in co["device_records"]}=={x["native_id"]for x in binding["devices"]},"Composition native identities changed")
    require(co["intrinsic_mim_models_in_final_netlist"]==7 and co["all_raw_wire_tokens_preserved"]is True,"MIM versus wire composition changed")
    projected=co["native_extracted_mim_cards_projected_once"]
    require(len(projected)==len({x["native_id"]for x in projected})==7 and {x["native_id"]for x in projected}=={x["native_id"]for x in co["device_records"]if x["model"]=="cap_cmim"},"Projected intrinsic MIM identities changed")
    # Exact original validator, evaluated in the SAVED producer context, not the new job.
    old.frozen_pipeline_validator(HEAD)(mim,0)
    joint=d["direct/joint-admission.json"];canonical=d["direct/canonical-candidate.json"];saved=joint["restored"]["saved"]
    require(joint["source_head"]==HEAD and joint["run_id"]==RUN and joint["status"]=="PASS_EXACT_WIDTH_NATIVE_PROOF_AND_COMPLETE_GRAPH_FOR_FRESH_RC","Joint admission producer changed")
    require((joint["complete_graph_members"],joint["current_members"],joint["original_members"])==(4103,75,605)and joint["original_graph_run"]==40808550817 and joint["original_topology_run"]==40815684037,"Joint graph/current census changed")
    require(saved["graph_source"]==s["original_graph_source"]and saved["topology_source"]==s["original_width_source"]and saved["current_root_result_must_not_be_fabricated"]is True,"Saved historical/current separation changed")
    graph=saved["complete_graph_files"];current=saved["current_files"]
    require(len(graph)==4103 and len(current)==75 and len(saved["original_files"])==605 and "result.json"not in current,"Original/current root distinction changed")
    exact(submap(full,"restore/graph-input/"),graph,"Complete4103 graph projection changed")
    exact(joint["current_files"],current,"Joint current75 changed");exact(canonical["files"],current,"Canonical current75 changed")
    require(canonical["current_root_result_fabricated"]is False and canonical["complete_members"]==75,"Fabricated current root result")
    h=mim["current_input_restoration"]
    require(h["source_head"]==HEAD and h["run"]==RUN and h["joint_admission_sha256"]==REQUIRED["direct/joint-admission.json"]["sha256"]and h["historical763_1136_1127_counts_reused"]is False,"Same-run complete MIM handoff changed")
    exact(h["binding"]["report"],b,"Handoff binding report changed");exact(h["rc"]["report"],rc,"Handoff wire report changed")
    for key,prefix,count in (("complete_binding_files","binding/",53),("complete_RC_stage_files","wire-stage/",5),("complete_current_view_files","canonical-current-view/",496)):
        require(len(h[key])==count,"Handoff complete inventory count changed");exact(h[key],submap(full,prefix),"Handoff complete inventory changed")
    require(all(h["complete_current_view_files"].get(n)==v for n,v in current.items()),"Current75 altered during RC")
    for order in ("precise","precise_reversed"):
        exact(submap(full,"mim/"+order+"/source/"),h["complete_current_view_files"],"Native order source projection differs")
        exact(submap(full,"mim/"+order+"/model-binding/"),h["complete_binding_files"],"Native order binding projection differs")
    require(mim["current_input_integrity"]["all_fresh_source_inputs_unchanged"]is True,"MIM fresh input integrity failed")
    selected_members(full)
    return {"complete_members":6647,"raw_result_sha256":RAW_SHA,"publication_summary_sha256":SUMMARY_SHA,"current_graph":4103,"original_current_inputs":75,"current_RC_view":496,"counts":COUNTS,"electrical_accepted":False}

def selected_members(full):
    require(full[MODEL_MEMBER]==MODEL_SHA and full[PLANES_MEMBER]==PLANES_SHA and full["canonical-current-view/native-planes.json"]==PLANES_SHA and full["mim/precise_reversed/source/native-planes.json"]==PLANES_SHA,"Current model/plane exact path changed")
    return {n:full[n]for n in (MODEL_MEMBER,PLANES_MEMBER,"mim/composition/composition.json","binding/binding.json","mim/precise/source/parent/layout/result.json")}

def validate_live(run,jobs,info,ref,docs=None):
    d=source_guard()if docs is None else docs
    expected=d["run.json"]
    keys=("id","run_attempt","head_sha","head_branch","event","status","conclusion","workflow_id")
    exact({k:run[k]for k in keys},{k:expected[k]for k in keys},"Live RC run changed")
    require(run["id"]==RUN and run["head_sha"]==HEAD and run["status"]=="completed"and run["conclusion"]=="success"and type(run["run_attempt"])is int and run["run_attempt"]==1,"RC run did not succeed")
    ej={j["id"]:j for j in d["jobs.json"]["jobs"]}
    require(jobs["total_count"]==len(jobs["jobs"])==len(ej)==3 and len({j["id"]for j in jobs["jobs"]})==3,"RC job census changed")
    for j in jobs["jobs"]:
        require(j["id"]in ej,"Unexpected RC job")
        keys=("id","name","head_sha","run_id","run_attempt","status","conclusion")
        exact({k:j[k]for k in keys},{k:ej[j["id"]][k]for k in keys},"RC job identity changed")
        require(j["status"]=="completed"and j["conclusion"]=="success","RC job failed")
        sk=("number","name","status","conclusion")
        exact([{k:s[k]for k in sk}for s in j["steps"]],[{k:s[k]for k in sk}for s in ej[j["id"]]["steps"]],"RC job steps changed")
    require(type(info["id"])is int and info["id"]==RELEASE,"RC release changed")
    proof=release.validate_release(info,ref,TAG,HEAD)
    keys=("id","name","size","digest","state")
    rows=lambda value:sorted([{k:a[k]for k in keys}for a in value["assets"]],key=lambda a:a["id"])
    require(len(info["assets"])==20 and all(type(a["id"])is int and type(a["size"])is int and a["size"]>0 and a["state"]=="uploaded"for a in info["assets"]),"RC asset census/state changed")
    exact(rows(info),rows(d["release.json"]),"Complete live RC assets changed")
    parts=d["direct/parts.json"];byname={a["name"]:a for a in info["assets"]}
    require(parts["format"]=="ordered-tar-gzip-parts-v1"and parts["source_directory"]=="cloud-cdr-selector-width-fresh-rc"and parts["bytes"]==822671612 and parts["sha256"]=="07f2bb45879a0b6bb7934f88e7952d0bb3aedfa4a93337e1ff583769612728ed","Current RC archive identity changed")
    require([p["index"]for p in parts["parts"]]==[0,1]and sum(p["bytes"]for p in parts["parts"])==parts["bytes"],"Ordered archive parts changed")
    for p in parts["parts"]:
        a=byname[p["name"]];require((a["size"],a["digest"])==(p["bytes"],"sha256:"+p["sha256"]),"Archive part/release join changed")
    for name,spec in REQUIRED.items():
        if not name.startswith("direct/"):continue
        suffix=name.split("/",1)[1];matches=[a for a in info["assets"]if a["name"]==parts["stem"]+"."+suffix]
        require(len(matches)==1 and(matches[0]["size"],matches[0]["digest"])==(spec["bytes"],"sha256:"+spec["sha256"]),"Direct asset/proof bytes differ")
    return {"run":RUN,"source_head":HEAD,"reservation":proof,"assets":20,"terminal_success":True,"native_acquisition_performed":False}

def expected_files():
    return source_guard()["complete-native-restore-map.json"]

def verify_restored(out):
    return old.verify_exact_files(Path(out)/"current-mim-bundle",expected_files())

def authorize(prepare_only):
    require(type(prepare_only)is bool,"Preparation mode must be boolean")
    m=methods()
    require(os.environ.get("GITHUB_ACTIONS")=="true"and os.environ.get("RUNNER_ENVIRONMENT")=="github-hosted"and os.environ.get("GITHUB_REPOSITORY")=="Melihakbulut221/nssoc"and os.environ.get("GITHUB_EVENT_NAME")=="workflow_dispatch"and os.environ.get("GITHUB_RUN_ATTEMPT")=="1"and os.environ.get("GITHUB_REF")=="refs/heads/"+BRANCH,"New hosted loaded context required")
    require(re.fullmatch("[0-9a-f]{40}",os.environ.get("GITHUB_SHA",""))and re.fullmatch("[1-9][0-9]*",os.environ.get("GITHUB_RUN_ID","")),"Invalid new hosted source/run")
    require(m["preparation_authorized"if prepare_only else"simulation_authorized"]is True and m["controller_readiness"]is True,"Current loaded execution disabled")
    return m

def acquire_and_extract(out,d,info):
    transport=Path(out)/"current-mim-transport";transport.mkdir(exist_ok=False)
    for a in info["assets"]:
        relative(a["name"]);require("/"not in a["name"],"Invalid producer asset basename")
        target=transport/a["name"];digest=a["digest"].removeprefix("sha256:")
        fetch(a["browser_download_url"],digest,target)
        require(target.stat().st_size==a["size"]and sha(target)==digest,"Downloaded current RC asset changed")
    for name,spec in REQUIRED.items():
        if name.startswith("direct/"):
            p=transport/(d["direct/parts.json"]["stem"]+"."+name.split("/",1)[1])
            require(p.read_bytes()==regular(ROOT,spec["path"]).read_bytes(),"Direct snapshot transport changed")
    bundle=Path(out)/"current-mim-bundle"
    return old.saved.exact_extract(d["direct/parts.json"],transport,bundle,d["complete-native-restore-map.json"])

def verify_bundle(bundle,d):
    full=d["complete-native-restore-map.json"]
    proof=old.verify_exact_files(bundle,full)
    require(regular(bundle,"result.json").read_bytes()==regular(ROOT,REQUIRED[RAW]["path"]).read_bytes(),"Restored raw terminal differs")
    for row in d["direct/direct-publication-plan.json"]["files"]:
        name="direct/"+row["suffix"]
        if name in REQUIRED:require(regular(bundle,row["member"]).read_bytes()==regular(ROOT,REQUIRED[name]["path"]).read_bytes(),"Restored direct report differs")
    planes=json.loads(regular(bundle,PLANES_MEMBER).read_bytes())
    require(sha(regular(bundle,PLANES_MEMBER))==PLANES_SHA and sha(regular(bundle,MODEL_MEMBER))==MODEL_SHA,"Current exact model/planes missing")
    require(planes["status"]=="PASS_PD500_NATIVE160_PLANES_51_NETS_19_FAULTS"and len(planes["anchors"])==160 and len({a["logical_net"]for a in planes["anchors"]})==51,"Current native plane qualification changed")
    layouts=[h for n,h in planes["inputs"].items()if n.endswith("/layout/result.json")]
    require(layouts==[full["mim/precise/source/parent/layout/result.json"]],"Current planes/layout join changed")
    require(regular(bundle,"mim/precise/model-binding/binding.json").read_bytes()==regular(bundle,"binding/binding.json").read_bytes(),"Current plane binding differs")
    for order in ("precise","precise_reversed"):
        require(regular(bundle,"mim/"+order+"/source/native-planes.json").read_bytes()==regular(bundle,PLANES_MEMBER).read_bytes(),"Two-order native planes differ")
    return planes,proof

def loaded_view(bundle,d,archive,remote,planes):
    require(archive["regular_members"]==6647 and archive["full_inventory_verified"]is True,"Complete restored archive missing")
    exact({n:r["sha256"]for n,r in archive["complete_member_hashes"].items()},d["complete-native-restore-map.json"],"Restored archive full map differs")
    proof={"run":RUN,"source_head":HEAD,"reservation":remote["reservation"],"live_producer":remote,"full_archive":archive,
      "summary_sha256":SUMMARY_SHA,"raw_result_sha256":RAW_SHA,"stage_sha256":REQUIRED["direct/MIM-precision-result.json"]["sha256"],
      "original_graph_run":40808550817,"original_width_run":40815684037,"complete_graph_members":4103,"current_members":75,
      "historical_failed_geometry_and_electrical_reports_retained":True,"geometry_regenerated":False,"extraction_rerun":False,"simulation_preaccepted":False}
    plane_proof={"current_mim_source":proof["stage_sha256"],"native_planes_sha256":PLANES_SHA,
      "fresh_layout_sha256":d["complete-native-restore-map.json"]["mim/precise/source/parent/layout/result.json"],
      "native_binding_sha256":REQUIRED["direct/binding.json"]["sha256"]}
    return d["direct/MIM-precision-result.json"],proof,Path(bundle)/MODEL_MEMBER,d["direct/composition.json"],planes,plane_proof

def restore(out,prepare_only):
    authorize(prepare_only);d=source_guard();out=Path(out)
    require(out.is_dir()and not out.is_symlink(),"Invalid loaded output root")
    require(all(not(out/n).exists()and not(out/n).is_symlink()for n in ("current-mim-transport","current-mim-bundle")),"Loaded restore destination occupied")
    run=release.api("actions/runs/"+str(RUN));jobs=release.api("actions/runs/"+str(RUN)+"/attempts/1/jobs?per_page=100")
    info=release.api("releases/"+str(RELEASE));ref=release.api("git/ref/tags/"+TAG)
    remote=validate_live(run,jobs,info,ref,d)
    archive=acquire_and_extract(out,d,info)
    planes,_=verify_bundle(out/"current-mim-bundle",d)
    methods()
    return loaded_view(out/"current-mim-bundle",d,archive,remote,planes)
