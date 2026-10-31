#!/usr/bin/env python3
"""Fresh RC authority bound to the actual eight-drain graph; no new geometry."""
import hashlib,json,os,re,shutil,subprocess,types
from pathlib import Path
import cdr_drain_m1_fresh_rc_admission as previous
import cloud_cdr_current_tail_graph as graph
import ensure_cloud_tested_source_release as release
from wait_cloud_tested_source_release import wait
from run_cloud_tx_layout_repair import sha
ROOT=Path(__file__).resolve().parents[1]
BRANCH="codex/cdr-drain-m1-loaded-electrical"
GROUP="cdr-current-eight-drain-fresh-rc"
OUT=ROOT/("hw/soc/out/cloud-"+GROUP)
METHOD=ROOT/"scripts/cdr-current-eight-drain-fresh-rc-methods.json"
CONFIG=ROOT/"scripts/cdr-current-eight-drain-fresh-rc-inputs.json"
ANALYSIS=ROOT/"hw/soc/out/cdr-current-eight-drain-graph-41206809668-1/native/candidate"
GRAPH_RUN=41206809668
GRAPH_HEAD="de79f76bc60b3ef2b06c88736f4f3d0ee3491257"
PHYSICAL_RUN=41203881385
PHYSICAL_HEAD="39496d034c4c1f2c9bcc3a9fe70cb3d82823fb53"
GRAPH_MANIFEST_SHA="7318774a4b27685ae8e9c92db7522501c1c9b2bf614fa04909c5967e642d2537"
GRAPH_MEMBERS=330
NATIVE=previous.NATIVE
FALSE=previous.FALSE
SCOPE="CURRENT_EIGHT_DRAIN_GRAPH_CURRENT75_FRESH500_BINDING_WIRE_RC_SEVEN_MIM_BOTH_ORDERS"
RESERVATION=ROOT/"hw/soc/out/cdr-current-eight-drain-fresh-rc-preflight/reservation.json"
RESERVATION_ENV="CDR_CURRENT_RC_RESERVATION_SHA256"
CONTROLS=ROOT/"ownership-source-proof/fresh-rc-controls.json"
BINDING_FILES=previous.BINDING_FILES
ENTRIES={key:"scripts/cloud_cdr_current_eight_drain_fresh_"+suffix+".py" for key,suffix in
 (("binding","binding"),("rc","wire_rc"),("capture","mim_capture"),("audit","mim_audit"),("precision","mim_precision"))}
require=previous.require
regular=previous.regular
relative=previous.relative
atomic=previous.atomic
write=atomic
read_json=previous.read_json

def validate_authorizations(method):
    require(method["schema"]=="cdr-current-eight-drain-fresh-rc-v1"and method["scope"]==SCOPE,"current RC scope")
    for name in NATIVE+FALSE+("source_controls_authorized","controller_readiness"):
        require(type(method[name])is bool,"typed current RC authority")
    require(all(method[name]is True for name in NATIVE+("source_controls_authorized","controller_readiness")),"bounded RC enabled")
    require(all(method[name]is False for name in FALSE),"no unsupported acceptance")
    return method

def methods():
    m=validate_authorizations(read_json(regular(ROOT,METHOD.relative_to(ROOT).as_posix())))
    old=previous.methods()
    g=graph.source_guard(GRAPH_MANIFEST_SHA)
    expected={**old["protected_sha256"],**g["files"]}
    require(all(old["protected_sha256"].get(k,v)==v for k,v in g["files"].items()),"no inherited pin conflict")
    require(all(m["protected_sha256"].get(k)==v for k,v in expected.items()),"complete old RC and current graph sources retained")
    for name,digest in m["protected_sha256"].items():
        require(sha(regular(ROOT,name))==digest,"changed current RC source: "+name)
    require(subprocess.check_output(["git","rev-parse","HEAD"],cwd=ROOT,text=True).strip()==os.environ["GITHUB_SHA"],"exact source")
    return m

def context(method):
    validate_authorizations(method)
    require(ROOT==Path("/home/runner/work/nssoc/nssoc")and os.environ.get("GITHUB_ACTIONS")=="true"
      and os.environ.get("RUNNER_ENVIRONMENT")=="github-hosted"and os.environ.get("GITHUB_REPOSITORY")=="Melihakbulut221/nssoc"
      and os.environ.get("GITHUB_EVENT_NAME")=="workflow_dispatch"and os.environ.get("GITHUB_RUN_ATTEMPT")=="1"
      and os.environ.get("GITHUB_REF")=="refs/heads/"+BRANCH,"exact hosted current RC branch")
    release.context(GROUP,os.environ)
    return method

def controls_binding():
    r=read_json(regular(CONTROLS.parent,CONTROLS.name))
    require(r["status"]=="PASS_CURRENT_EIGHT_DRAIN_FRESH_RC_SOURCE_CONTROLS"and r["passed"]is True,"current RC controls")
    require(r["current_context"]==dict(source=os.environ["GITHUB_SHA"],run_id=int(os.environ["GITHUB_RUN_ID"]),attempt=1,
      source_controls_only=True,native_executed=False),"same-source current RC controls")
    require(r["inherited"]==dict(positive=8,refusal=110)and r["new_tests"]==16,"complete numerical and adapter tests")
    require(r["native_executed"]is False and r["electrical_acceptance"]is False,"source-only evidence")
    return dict(bytes=CONTROLS.stat().st_size,sha256=sha(CONTROLS))

def validate_reservation(value,method):
    tag,head=release.context(GROUP,os.environ)
    require(value["schema"]=="current-eight-drain-fresh-rc-reservation-v1"and value["source_head"]==head
      and type(value["run_id"])is int and value["run_id"]==int(os.environ["GITHUB_RUN_ID"])
      and type(value["run_attempt"])is int and value["run_attempt"]==1,"reservation identity")
    require(value["method_sha256"]==sha(METHOD)and value["graph_manifest_sha256"]==GRAPH_MANIFEST_SHA,"reservation source")
    controls=value["current_source_controls"]
    require(type(controls["bytes"])is int and controls["bytes"]>0 and re.fullmatch("[0-9a-f]{64}",controls["sha256"]),"control fingerprint")
    proof=release.validate_release(value["release"],value["ref"],tag,head)
    require(proof["existing_assets"]==[]and value["empty_before_dependencies"]is True and value["creation_attempted"]is False,"external empty reservation")
    return proof

def reservation(method):
    require(sha(regular(ROOT,RESERVATION.relative_to(ROOT).as_posix()))==os.environ.get(RESERVATION_ENV),"reservation bytes")
    value=read_json(RESERVATION)
    return dict(receipt_sha256=sha(RESERVATION),receipt=value,validated=validate_reservation(value,method))

def authorize():
    method=context(methods());proof=reservation(method)
    require(proof["receipt"]["current_source_controls"]==controls_binding(),"unchanged current controls")
    return method

def preflight():
    method=context(methods());controls=controls_binding()
    require(not RESERVATION.exists()and not RESERVATION.is_symlink(),"no reservation overwrite")
    wait(GROUP,os.environ);tag,head=release.context(GROUP,os.environ)
    value=dict(schema="current-eight-drain-fresh-rc-reservation-v1",source_head=head,run_id=int(os.environ["GITHUB_RUN_ID"]),run_attempt=1,
      method_sha256=sha(METHOD),graph_manifest_sha256=GRAPH_MANIFEST_SHA,current_source_controls=controls,
      release=release.api("releases/tags/"+tag),ref=release.api("git/ref/tags/"+tag),empty_before_dependencies=True,creation_attempted=False)
    validate_reservation(value,method);atomic(RESERVATION,value)
    return dict(receipt=str(RESERVATION),sha256=sha(RESERVATION),reservation=value)

def publication_authorize():
    method=context(validate_authorizations(read_json(METHOD)));reservation(method)
    tag,head=release.context(GROUP,os.environ)
    return release.validate_release(release.api("releases/tags/"+tag),release.api("git/ref/tags/"+tag),tag,head)

def contract():
    methods();c=read_json(CONFIG)
    require(c["schema"]=="current-eight-drain-fresh-rc-inputs-v1","current input schema")
    require(c["graph_producer"]==dict(run=GRAPH_RUN,source=GRAPH_HEAD,attempt=1,workflow=401118236,branch=BRANCH),"actual graph producer")
    full=c["full_capsule_files"];q=c["graph_qualification"]
    require(len(full)==330 and len(q["current_files"])==75 and "result.json"not in q["current_files"],"complete330/current75")
    for name,pin in full.items():
        relative(name);require(set(pin)=={"bytes","sha256"}and type(pin["bytes"])is int and pin["bytes"]>=0
          and re.fullmatch("[0-9a-f]{64}",pin["sha256"]),"complete member pins")
    require(q["status"]=="PASS_FRESH_EIGHT_DRAIN_GRAPH_IDENTITIES_FULL_PARTITION_UNIONS_REQUIRES_RC","actual graph qualification")
    require(q["candidate_gds"]==dict(bytes=997620,sha256="9d8984fd4852a04618146732c0d473ca80c6bb1d2f441d0da27854ed7ca69bff")
      and q["candidate_lvs"]==dict(bytes=2720487,sha256="6b75a97dd6c1791622efd4676322a8f694efabec83b540e369d61b6a6270ee34"),"exact current physical bytes")
    require(all(q[k]is False for k in ("physical_acceptance","electrical_acceptance","full_phy_accepted","fresh_RC_executed")),"input is graph only")
    prefix=c["graph_proof"]["prefix"]
    require(sha(regular(ROOT,prefix+"receipt.json"))=="4ac7964c7642fed727cfbeb84c20e6f172912d2800c4a35ab6fd5edd7831ae42","complete original graph receipt")
    receipt=read_json(regular(ROOT,prefix+"receipt.json"))
    require(receipt["graph"]==q and receipt["run"]==GRAPH_RUN and receipt["source"]==GRAPH_HEAD
      and receipt["workflow_conclusion"]=="success"and receipt["capsule_files"]==330,"actual receipt graph and producer")
    index=read_json(regular(ROOT,prefix+"capsule-metadata/complete-output-index.json"))
    require(index["files"]==full,"complete archived map equals original producer index")
    parts=read_json(regular(ROOT,prefix+"capsule-metadata/cdr-current-eight-drain-graph-41206809668-1.parts.json"))
    require(q["material"]==receipt["graph"]["material"]and c["archive"]==parts,"original material and transport")
    saved_release=read_json(regular(ROOT,prefix+"release.json"))
    require(c["release_id"]==saved_release["id"]and c["tag"]==saved_release["tag_name"],"original release identity")
    require(c["assets"]=={v["name"]:dict(id=v["id"],bytes=v["size"],sha256=v["digest"].removeprefix("sha256:"))for v in saved_release["assets"]},"complete actual saved asset map")
    raw=regular(ROOT,prefix+"readable-records/native-records/graph-qualification.json")
    require(sha(raw)==c["graph_report_pin"]["sha256"]and read_json(raw)==q,"raw graph report")
    material=read_json(regular(ROOT,prefix+"readable-records/native-records/full-partition-material.json"))
    require(material["status"]=="PASS_ALL113_COMPONENTS_13LAYERS_EXACT_574_EIGHT_DRAIN_ADDITIONS"
      and material["actual_added_shapes"]==574 and len(material["records"])==1469,"complete original material")
    lifecycle=read_json(regular(ROOT,prefix+"readable-records/native-records/native-lifecycle.json"))
    require(lifecycle["errors"]==[]and lifecycle["primary_error"]is None and len(lifecycle["commands"])==9
      and all(x["returncode"]==0 and x["supervision_failure"]is None and not x["process_group_cleanup"]["remaining_live"]for x in lifecycle["commands"]),"all9 actual native graph phases")
    ident=q["actual_native_identity"]
    require(all(ident[k]==v for k,v in dict(devices=500,terminals=1446,ports=25,anchors=978,native_nets=238).items())
      and ident["all_levels_and_instance_ordinals_and_transforms_equal"]is True
      and ident["topology_comparator_modified"]is False,"complete original identity")
    require(q["physical_producer"]["id"]==PHYSICAL_RUN and q["physical_producer"]["head_sha"]==PHYSICAL_HEAD,"actual physical producer")
    require(c["current_view_prefix"]=="native/candidate/","current view namespace")
    for name,pin in q["current_files"].items():
        relative(name);require(full[c["current_view_prefix"]+name]==pin,"current/full join")
    return dict(schema="current-eight-drain-RC-input-contract-v1",qualified_input=c,
      transport=dict(expected_sha256={n:v["sha256"]for n,v in full.items()}),
      canonical_candidate=dict(expected_sha256={n:v["sha256"]for n,v in q["current_files"].items()},members=75),
      historical_authority_reused=False)

def live(c,run,jobs,rel,ref):
    q=c["qualified_input"]
    require(run["id"]==GRAPH_RUN and run["head_sha"]==GRAPH_HEAD and run["head_branch"]==BRANCH
      and run["run_attempt"]==1 and run["workflow_id"]==401118236 and run["event"]=="workflow_dispatch"
      and run["status"]=="completed"and run["conclusion"]=="success","actual successful graph")
    rows=jobs["jobs"]
    require(len({j["id"]for j in rows})==len(rows),"unique native producer jobs")
    require(len(rows)==4 and {j["name"]for j in rows}=={"source-controls","preserve-job-log","graph","preserve-graph-job-logs"}
      and all(j["head_sha"]==GRAPH_HEAD and j["run_id"]==GRAPH_RUN and j["status"]=="completed"and j["conclusion"]=="success"for j in rows),"all actual graph jobs")
    require(rel["id"]==q["release_id"]==429962223 and rel["tag_name"]==q["tag"]
      and rel["target_commitish"]==GRAPH_HEAD and rel["draft"]is False and rel["prerelease"]is True,"graph release")
    require(ref["object"]["type"]=="commit"and ref["object"]["sha"]==GRAPH_HEAD,"graph tag")
    assets={a["name"]:a for a in rel["assets"]}
    require(len(assets)==len(rel["assets"])and set(assets)==set(q["assets"]),"all graph assets")
    for name,pin in q["assets"].items():
        a=assets[name]
        require(a["state"]=="uploaded"and a["id"]==pin["id"]and a["size"]==pin["bytes"]and a["digest"]=="sha256:"+pin["sha256"],"live asset fingerprint")
    return dict(graph_run=GRAPH_RUN,graph_source=GRAPH_HEAD,complete_assets=True,successful_fresh_graph_only=True)

def verify_saved(root,c):
    expected=c["transport"]["expected_sha256"];actual={}
    require(root.is_dir()and not root.is_symlink(),"saved graph directory")
    for path in root.rglob("*"):
        require(not path.is_symlink()and(path.is_dir()or path.is_file()),"regular saved graph")
        if path.is_file():actual[path.relative_to(root).as_posix()]=sha(path)
    require(actual==expected,"complete actual330 member inventory")
    q=c["qualified_input"]
    require(read_json(regular(root,"native/graph-qualification.json"))==q["graph_qualification"],"raw archived graph")
    receipt=read_json(regular(ROOT,q["graph_proof"]["prefix"]+"receipt.json"))
    require(read_json(regular(root,"evidence/result.json"))==receipt["actual_result"],"raw successful native producer")
    for member,proof in (("native/native-lifecycle.json","readable-records/native-records/native-lifecycle.json"),
                        ("native/full-partition-material.json","readable-records/native-records/full-partition-material.json")):
        require(sha(regular(root,member))==sha(regular(ROOT,q["graph_proof"]["prefix"]+proof)),"archived actual proof identity")
    return dict(files=len(actual),full_sha256=actual,all_original_bytes_unchanged=True,
      graph_source=GRAPH_HEAD,graph_run=GRAPH_RUN,physical_run=PHYSICAL_RUN)

def qualify_saved(root,c):
    saved=verify_saved(root,c)
    return dict(status="PASS_CURRENT_EIGHT_DRAIN_GRAPH_AND_CURRENT75_FOR_FRESH_RC",
      source_head=os.environ["GITHUB_SHA"],run_id=int(os.environ["GITHUB_RUN_ID"]),
      graph_source=GRAPH_HEAD,graph_run=GRAPH_RUN,physical_source=PHYSICAL_HEAD,physical_run=PHYSICAL_RUN,
      complete_graph_members=330,current_members=75,restored=saved,current_files=c["canonical_candidate"]["expected_sha256"],
      actual_terminal_identity_join=c["qualified_input"]["graph_qualification"]["actual_native_identity"],
      fresh_RC_executed=False,electrical_accepted=False,qualified_pex=False,full_phy_accepted=False)

def runtime_restore():
    import cloud_cdr_v59_tail_access_physical as physical
    gate=authorize
    fn=types.FunctionType(physical.runtime_worker.__code__,dict(physical.runtime_worker.__globals__,authorize=gate,methods=methods,OUT=OUT),
                          physical.runtime_worker.__name__)
    require(fn.__code__ is physical.runtime_worker.__code__,"unchanged runtime restoration")
    fn()
    manifest=read_json(OUT/"runtime-source-manifest.json")
    require(all(sha(regular(ROOT,n))==v["sha256"]for n,v in manifest["files"].items()),"complete frozen runtime bytes")
    methods()

def runtime_policy():
    policy=read_json(regular(ROOT,"current-cdr-runtime-policy.json"))
    app=Path(os.environ["CLOUD_APPIMAGE"])
    require(policy["source"]==os.environ["GITHUB_SHA"]and policy["run_id"]==int(os.environ["GITHUB_RUN_ID"])
      and policy["attempt"]==1,"same-source hosted runtime policy")
    require(policy["appimage"]==str(app)and policy["appimage_sha256"]==sha(app)
      and sha(app)=="d6a349ec65be11456e96c4981d35f63ca34d3c85daf79a51e1ccb907bb5d7466","pinned scoped executable")
    require(policy["loaded"]is True and policy["global_policy_changed"]is False
      and policy["restriction_before"]==policy["restriction_after"],"scoped user namespace exception only")
    require(policy["profile"]=="/etc/apparmor.d/nssoc-cdr-runtime-"+os.environ["GITHUB_RUN_ID"]+"-1"
      and hashlib.sha256(policy["profile_text"].encode()).hexdigest()==policy["profile_sha256"],"owned policy bytes")
    return policy

def restore():
    authorize();c=contract();q=c["qualified_input"]
    write(OUT/"runtime-policy.json",runtime_policy())
    observed=live(c,release.api("actions/runs/"+str(GRAPH_RUN)),
      release.api("actions/runs/"+str(GRAPH_RUN)+"/attempts/1/jobs?per_page=100"),
      release.api("releases/"+str(q["release_id"])),release.api("git/ref/tags/"+q["tag"]))
    out=OUT/"restore";require(not out.exists()and not out.is_symlink(),"new restore destination");out.mkdir(parents=True)
    transport=out/"transport";transport.mkdir()
    archive,received=graph.r.acquire(dict(cases=dict(graph=dict(assets=q["assets"]))),"graph",q["archive"],transport)
    saved=out/"graph-input"
    census=graph.r.select_archive(archive,c["transport"]["expected_sha256"],list(c["transport"]["expected_sha256"]),q["archive"]["source_directory"],saved)
    require(census["full_member_count"]==330 and census["every_member_authenticated"]is True and len(census["selected"])==330,"authenticate every native member")
    write(out/"restore.json",dict(complete_graph_census=census,live=observed,transport=received))
    pin=qualify_saved(saved,c);write(out/"joint-admission.json",pin);write(out/"live-graph-and-physical.json",observed)
    expected=c["canonical_candidate"]["expected_sha256"]
    require(not ANALYSIS.exists()and not ANALYSIS.is_symlink(),"fresh canonical current view")
    for parent in ANALYSIS.parents:require(not parent.is_symlink(),"no symlink ancestry")
    ANALYSIS.mkdir(parents=True)
    for name,digest in expected.items():
        target=ANALYSIS/relative(name);target.parent.mkdir(parents=True,exist_ok=True)
        shutil.copyfile(regular(saved,q["current_view_prefix"]+name),target)
        require(sha(target)==digest,"unchanged projected member")
    require({p.relative_to(ANALYSIS).as_posix():sha(p)for p in ANALYSIS.rglob("*")if p.is_file()}==expected,"exact75 file projection")
    for bindings in q["graph_qualification"]["fresh_report_bindings"].values():
        for name,digest in bindings.items():
            path=Path(name)
            require(path.is_relative_to(ANALYSIS)and str(path)==name and sha(regular(ANALYSIS,path.relative_to(ANALYSIS).as_posix()))==digest,"exact original absolute report binding")
    write(out/"canonical-candidate.json",dict(files=expected,complete_members=75,original_absolute_path=str(ANALYSIS),
      all_original_bytes_unchanged=True,current_root_result_fabricated=False))
    require(qualify_saved(saved,c)==pin,"immutable graph changed during projection")
    runtime_restore()
    methods();return pin
