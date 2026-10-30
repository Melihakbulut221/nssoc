#!/usr/bin/env python3
"""Separate exact-source RC authority over the newly qualified two-M1 current graph."""
import hashlib,json,os,re,shutil
from pathlib import Path,PurePosixPath
import cloud_cdr_drain_m1_fresh_graph as graph
import cdr_selector_width_fresh_rc_execution as qualified
import ensure_cloud_tested_source_release as release
from wait_cloud_tested_source_release import wait
from run_cloud_tx_layout_repair import sha
ROOT=Path(__file__).resolve().parents[1]
BRANCH="codex/cdr-drain-m1-fresh-rc"
GROUP="cdr-drain-m1-fresh-rc"
OUT=ROOT/("hw/soc/out/cloud-"+GROUP)
METHOD=ROOT/"scripts/cdr-drain-m1-fresh-rc-methods.json"
CONFIG=ROOT/"scripts/cdr-drain-m1-fresh-rc-inputs.json"
ANALYSIS=ROOT/"hw/soc/out/cloud-cdr-drain-m1-fresh-graph/candidate"
GRAPH_RUN=41003747027
GRAPH_HEAD="474045b9821069cbe42a71752c3c53267e5493fd"
PHYSICAL_RUN=41000358737
PHYSICAL_HEAD="37b5b75738b5bbe5eafcfb5e94101c08503c995a"
GRAPH_MANIFEST_SHA="667a795dc4ad5ce07055c23fc8da15dbeb3fb2e1c7ecaac1a69cb03866f89ccd"
GRAPH_MEMBERS=138
NATIVE=("native_execution_authorized","binding_authorized","wire_rc_authorized","mim_extraction_authorized","native_extraction_authorized")
FALSE=("geometry_generation_authorized","simulation_authorized","accepted","physical_accepted","electrical_accepted","qualified_pex","full_phy_accepted","automatic_retry")
SCOPE="FRESH_TWO_M1_GRAPH_CURRENT75_FRESH500_BINDING_WIRE_RC_SEVEN_MIM_BOTH_ORDERS"
RESERVATION=ROOT/"hw/soc/out/cdr-drain-m1-fresh-rc-preflight/reservation.json"
RESERVATION_ENV="CDR_DRAIN_M1_RC_RESERVATION_SHA256"
CONTROLS=ROOT/"hw/soc/out/cdr-drain-m1-fresh-rc-controls/current.json"
BINDING_FILES=("wire/device-locations01.json","parent/layout/result.json","parent/layout/schematic.cir",
 "parent/physical/lvs_flat/extracted.cir","parent/physical/lvs_flat/audit.json","parent/physical/lvs_flat/result.lvsdb")
ENTRIES={"binding":"scripts/cloud_cdr_drain_m1_fresh_binding.py","rc":"scripts/cloud_cdr_drain_m1_fresh_wire_rc.py",
 "capture":"scripts/cloud_cdr_drain_m1_fresh_mim_capture.py","audit":"scripts/cloud_cdr_drain_m1_fresh_mim_audit.py",
 "precision":"scripts/cloud_cdr_drain_m1_fresh_mim_precision.py"}
require=graph.require
regular=graph.frozen.regular
atomic=qualified.atomic
write=atomic

def relative(value):
    p=PurePosixPath(value)
    require(type(value)is str and not p.is_absolute()and p.as_posix()==value and all(v not in ("",".","..")for v in p.parts),"unsafe relative member")
    return p

def read_json(path):
    return json.loads(Path(path).read_bytes())

def validate_authorizations(method):
    require(method["schema"]=="cdr-drain-m1-fresh-rc-v1"and method["scope"]==SCOPE,"fresh two-M1 RC scope")
    for name in NATIVE+FALSE+("source_controls_authorized","controller_readiness"):
        require(type(method[name])is bool,"typed RC authority: "+name)
    require(len({method[k]for k in NATIVE})==1,"split native authority")
    require(all(method[k]is False for k in FALSE),"unsupported acceptance")
    require(not method[NATIVE[0]]or method["source_controls_authorized"]is method["controller_readiness"]is True,"RC source/controller qualification")
    return method

def methods():
    require(METHOD.is_file()and not METHOD.is_symlink(),"regular current method")
    m=validate_authorizations(read_json(METHOD))
    for name,digest in m["protected_sha256"].items():
        require(sha(regular(ROOT,name))==digest,"changed current RC source: "+name)
    graph.source_guard(GRAPH_MANIFEST_SHA,ROOT)
    prior=qualified.methods()
    require(all(m["protected_sha256"].get(n)==v for n,v in prior["protected_sha256"].items()),"all1184 prior RC sources retained")
    require(len(prior["protected_sha256"])==1184,"qualified RC protection census")
    return m

def context(method):
    validate_authorizations(method)
    require(ROOT==Path("/home/runner/work/nssoc/nssoc")and os.environ.get("GITHUB_ACTIONS")=="true"
      and os.environ.get("RUNNER_ENVIRONMENT")=="github-hosted"and os.environ.get("GITHUB_REPOSITORY")=="Melihakbulut221/nssoc"
      and os.environ.get("GITHUB_EVENT_NAME")=="workflow_dispatch"and os.environ.get("GITHUB_RUN_ATTEMPT")=="1"
      and os.environ.get("GITHUB_REF")=="refs/heads/"+BRANCH,"exact hosted RC branch/attempt")
    release.context(GROUP,os.environ)
    require(method["controller_readiness"]is True and all(method[k]is True for k in NATIVE),"current RC disabled")
    return method

def controls_binding():
    r=read_json(regular(CONTROLS.parent,CONTROLS.name))
    require(r["status"]=="PASS_DRAIN_M1_FRESH_RC_SOURCE_CONTROLS"and r["passed"]is True,"current RC controls")
    require(r["current_context"]==dict(source=os.environ["GITHUB_SHA"],run_id=int(os.environ["GITHUB_RUN_ID"]),attempt=1,
      source_controls_only=True,native_executed=False),"same source RC controls")
    require((r["positive"],r["refusal"])==(8,110),"complete current controls")
    require(r["native_executed"]is False and r["electrical_acceptance"]is False,"source-only RC evidence")
    return dict(bytes=CONTROLS.stat().st_size,sha256=sha(CONTROLS))

def validate_reservation(value,method):
    tag,head=release.context(GROUP,os.environ)
    require(value["schema"]=="two-M1-fresh-rc-reservation-v1"and value["source_head"]==head
      and type(value["run_id"])is int and value["run_id"]==int(os.environ["GITHUB_RUN_ID"])
      and type(value["run_attempt"])is int and value["run_attempt"]==1,"reservation context")
    require(value["method_sha256"]==sha(METHOD)and value["graph_manifest_sha256"]==GRAPH_MANIFEST_SHA,"reservation source")
    controls=value["current_source_controls"]
    require(type(controls["bytes"])is int and controls["bytes"]>0 and re.fullmatch("[0-9a-f]{64}",controls["sha256"]),"reservation controls fingerprint")
    proof=release.validate_release(value["release"],value["ref"],tag,head)
    require(proof["existing_assets"]==[]and value["empty_before_dependencies"]is True and value["creation_attempted"]is False,"independent empty reservation")
    return proof

def reservation(method):
    require(sha(regular(ROOT,str(RESERVATION.relative_to(ROOT))))==os.environ.get(RESERVATION_ENV),"receipt hash")
    value=read_json(RESERVATION)
    return dict(receipt_sha256=sha(RESERVATION),receipt=value,validated=validate_reservation(value,method))

def authorize():
    method=context(methods());proof=reservation(method)
    require(proof["receipt"]["current_source_controls"]==controls_binding(),"unchanged current source controls")
    return method

def preflight():
    method=context(methods());controls=controls_binding()
    require(not RESERVATION.exists()and not RESERVATION.is_symlink(),"reservation no overwrite")
    wait(GROUP,os.environ)
    tag,head=release.context(GROUP,os.environ)
    value=dict(schema="two-M1-fresh-rc-reservation-v1",source_head=head,run_id=int(os.environ["GITHUB_RUN_ID"]),run_attempt=1,
      method_sha256=sha(METHOD),graph_manifest_sha256=GRAPH_MANIFEST_SHA,current_source_controls=controls,
      release=release.api("releases/tags/"+tag),ref=release.api("git/ref/tags/"+tag),empty_before_dependencies=True,creation_attempted=False)
    validate_reservation(value,method);atomic(RESERVATION,value)
    return dict(receipt=str(RESERVATION),sha256=sha(RESERVATION),reservation=value)

def publication_authorize():
    method=context(validate_authorizations(read_json(METHOD)));reservation(method)
    tag,head=release.context(GROUP,os.environ)
    return release.validate_release(release.api("releases/tags/"+tag),release.api("git/ref/tags/"+tag),tag,head)

def contract():
    methods();c=read_json(CONFIG);q=c["fresh_graph_qualification"]
    require(c["producer"]["id"]==GRAPH_RUN and c["producer"]["head_sha"]==GRAPH_HEAD
      and len(c["full"])==GRAPH_MEMBERS,"actual graph producer")
    require(q["status"]=="PASS_FRESH_TWO_M1_GRAPH_IDENTITIES_FULL_PARTITION_UNIONS_REQUIRES_RC"
      and q["current_files"]==c["current_files"]and len(c["current_files"])==75 and "result.json"not in c["current_files"],"actual current75")
    require(q["candidate_gds"]["sha256"]=="34f06505f3ff2fdb06257d6202931aa12d2d0176d482a2a7916561eeb9646034"
      and q["candidate_lvs"]["sha256"]=="db740e4439e43e67bb9ddce5e69d784e1adb1b18b07cac893fe0db3128a1ec43","actual widened input hashes")
    prefix=c["proof_prefix"]
    require(sha(regular(ROOT,prefix+"receipt.json"))==c["receipt_sha256"],"actual graph receipt")
    require(read_json(regular(ROOT,prefix+"readback/"+c["report_prefix"]+"graph-qualification.json"))==q,"raw graph qualification")
    diagnosis=read_json(regular(ROOT,prefix+"diagnosis.json"))
    require(c["terminal_join"]==diagnosis["actual_terminal_join"]and c["physical_producer"]==diagnosis["physical_producer"],"actual terminal and physical provenance")
    invpath=prefix+"readback/"+c["report_prefix"]+"permanent-output-inventory.json"
    full={n:v["sha256"]for n,v in read_json(regular(ROOT,invpath))["complete_available_derived_files"].items()}
    full[c["report_prefix"]+"permanent-output-inventory.json"]=sha(regular(ROOT,invpath))
    require(c["full"]==full,"complete archived native graph member map")
    for n,v in c["current_files"].items():require(c["full"][c["view_prefix"]+n]==v["sha256"],"current/full inventory join")
    return dict(schema="fresh-two-M1-RC-input-contract-v1",qualified_input=c,
      transport=dict(expected_sha256=c["full"]),
      canonical_candidate=dict(expected_sha256={n:v["sha256"]for n,v in c["current_files"].items()},members=75),
      historical_authority_reused=False)

def verify_saved(root,c):
    expected=c["transport"]["expected_sha256"]
    actual={}
    require(root.is_dir()and not root.is_symlink(),"saved graph root")
    for p in root.rglob("*"):
        require(not p.is_symlink()and (p.is_dir()or p.is_file()),"saved graph nonregular")
        if p.is_file():actual[p.relative_to(root).as_posix()]=sha(p)
    require(actual==expected,"complete actual graph138 inventory")
    q=c["qualified_input"];report=read_json(regular(root,q["report_prefix"]+"graph-qualification.json"))
    require(report==q["fresh_graph_qualification"],"saved raw graph qualification")
    return dict(files=len(actual),full_sha256=actual,all_original_bytes_unchanged=True,
      graph_source=GRAPH_HEAD,graph_run=GRAPH_RUN,physical_run=PHYSICAL_RUN)

def qualify_saved(root,c):
    saved=verify_saved(root,c)
    return dict(status="PASS_EXACT_NEW_TWO_M1_GRAPH_AND_CURRENT75_FOR_FRESH_RC",
      source_head=os.environ["GITHUB_SHA"],run_id=int(os.environ["GITHUB_RUN_ID"]),
      graph_source=GRAPH_HEAD,graph_run=GRAPH_RUN,physical_source=PHYSICAL_HEAD,physical_run=PHYSICAL_RUN,
      complete_graph_members=GRAPH_MEMBERS,current_members=75,
      restored=saved,current_files=c["canonical_candidate"]["expected_sha256"],
      actual_terminal_identity_join=c["qualified_input"]["terminal_join"],
      fresh_RC_executed=False,electrical_accepted=False,qualified_pex=False,full_phy_accepted=False)

def restore():
    authorize();c=contract();q=c["qualified_input"]
    live=graph.frozen.validate_live(q,release.api("actions/runs/"+str(GRAPH_RUN)),
      release.api("actions/runs/"+str(GRAPH_RUN)+"/attempts/1/jobs?per_page=100"),
      release.api("releases/"+str(q["release_id"])),release.api("git/ref/tags/"+q["tag"]))
    require(live.pop("successful_RC_production_only")is True,"shared live proof")
    live["successful_fresh_graph_only"]=True
    out=OUT/"restore";require(not out.exists()and not out.is_symlink(),"new restore destination");out.mkdir(parents=True)
    asset=q["assets"]["cdr-drain-m1-fresh-graph-evidence.tar.gz"];archive=out/"graph-native-input.tar.gz"
    graph.frozen.download(asset,archive)
    saved=out/"graph-input"
    census=graph.frozen.select_archive(archive,q["full"],list(q["full"]),q["source_directory"],saved)
    write(out/"restore.json",dict(complete_graph_census=census,live=live))
    pin=qualify_saved(saved,c);write(out/"joint-admission.json",pin);write(out/"live-graph-and-physical.json",live)
    expected=c["canonical_candidate"]["expected_sha256"]
    require(not ANALYSIS.exists()and not ANALYSIS.is_symlink(),"canonical fresh analysis exists")
    for parent in ANALYSIS.parents:require(not parent.is_symlink(),"canonical path symlink")
    ANALYSIS.mkdir(parents=True)
    for name,digest in expected.items():
        original=regular(saved,q["view_prefix"]+name);target=ANALYSIS/relative(name);target.parent.mkdir(parents=True,exist_ok=True)
        shutil.copyfile(original,target);require(sha(target)==digest,"current projection hash")
    require({p.relative_to(ANALYSIS).as_posix():sha(p)for p in ANALYSIS.rglob("*")if p.is_file()}==expected,"complete current projection")
    # Reports retain the exact authenticated original absolute paths. Map only by the canonical path.
    for bindings in q["fresh_graph_qualification"]["fresh_report_bindings"].values():
        for name,digest in bindings.items():
            path=Path(name);require(path.is_relative_to(ANALYSIS)and str(path)==name
              and sha(regular(ANALYSIS,path.relative_to(ANALYSIS).as_posix()))==digest,"original fresh absolute report binding")
    write(out/"canonical-candidate.json",dict(files=expected,complete_members=75,
      original_absolute_path=str(ANALYSIS),all_original_bytes_unchanged=True,current_root_result_fabricated=False))
    require(qualify_saved(saved,c)==pin,"saved graph changed during projection");methods();return pin
