#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0
"""Existing capture replay only. No simulator, extraction, geometry or acceptance."""
import argparse,ast,base64,copy,gzip,hashlib,importlib,json,math,os,re,shutil
import subprocess,sys,tarfile,tempfile,traceback,zlib
from collections import Counter
from decimal import Decimal
from pathlib import Path,PurePosixPath
from types import SimpleNamespace
ROOT=Path(__file__).resolve().parents[1]
CONFIG='scripts/cdr-drain-m1-wave-replay-inputs.json'
CONFIG_SHA='98258d652c2e1bc4af48219cd3f20c8ce2fdb1f4f48b63640aa448745feca2d6'
BRANCH='codex/cdr-drain-m1-loaded-electrical'
REPOSITORY='Melihakbulut221/nssoc'
GROUP="cdr-drain-m1-wave-replay"
CASES=("nominal_early","constant_one")
NEW_SOURCES=['scripts/cloud_cdr_drain_m1_wave_replay.py', 'scripts/check_cdr_drain_m1_wave_replay.py']
READBACK_FLAGS=dict(accepted=False,cdr_accepted=False,physical_acceptance=False,
 full_phy_accepted=False,timing_accepted=False,electrical_accepted=False,reduced_element_ownership_proved=False,causality_proven=False,new_simulation=False,geometry_changed=False)
SOURCE_GROUPS=['source', 'metadata', 'live', 'archives', 'raw', 'binding_scalar', 'full_rows', 'lifecycle']
SOURCE_REFUSALS=['source_tamper', 'missing_helper', 'context_branch', 'attempt', 'disabled_readback', 'wrong_case', 'wrong_source', 'wrong_native_status', 'raw_summary_swap', 'missing_member', 'parts_duplicate', 'parts_missing', 'parts_digest', 'vectors_missing', 'vectors_duplicate', 'vector_order', 'wrong_lineage', 'live_source', 'live_job', 'live_release', 'live_ref', 'reservation_assets', 'reservation_source', 'archive_missing', 'archive_extra', 'archive_duplicate', 'archive_traversal', 'archive_link', 'archive_corruption', 'part_transport_corruption', 'raw_truncated', 'raw_extra', 'raw_nonfinite', 'raw_backward', 'raw_duplicate_time', 'raw_vector_missing', 'raw_vector_duplicate', 'raw_wrong_kind', 'raw_wrong_order', 'binding_terminal', 'binding_filter', 'scalar_HBT', 'scalar_VI', 'scalar_status', 'scalar_original_rejection', 'rows_missing_vector', 'rows_length_mismatch']
SOURCE_COUNTS=dict(groups=8,refusals=47,lifecycle=4)
np=None

def require(ok,message):
    if not ok:raise AssertionError(message)

def encode(obj):
    return (json.dumps(obj,sort_keys=True,indent=2,allow_nan=False)+"\n").encode()

def decode(raw):
    def pairs(items):
        d={}
        for k,v in items:
            require(k not in d,"duplicate JSON key");d[k]=v
        return d
    return json.loads(raw,object_pairs_hook=pairs,
      parse_constant=lambda x:(_ for _ in ()).throw(ValueError("nonfinite JSON")))

def fingerprint(raw):
    return dict(bytes=len(raw),sha256=hashlib.sha256(raw).hexdigest())

def regular(root,name):
    checked_path(name);p=Path(root)/name
    for q in (p,*p.parents):
        require(not q.is_symlink(),"path symlink: "+name)
        if q==Path(root):break
    require(p.is_file(),"missing regular file: "+name)
    return p

def checked_path(name):
    require(isinstance(name,str)and name and "\\"not in name and "\x00"not in name,
            "unsafe archive path")
    p=PurePosixPath(name)
    require(not p.is_absolute()and str(p)==name and all(v not in ("",".","..")for v in p.parts),
            "unsafe archive path")
    return p

def context(env,case=None):
    require(env.get("GITHUB_ACTIONS")=="true","hosted only")
    require(env.get("GITHUB_EVENT_NAME")=="workflow_dispatch","manual only")
    require(env.get("GITHUB_REPOSITORY")==REPOSITORY,"repository")
    require(env.get("GITHUB_REF")=="refs/heads/"+BRANCH,"readback branch")
    require(env.get("GITHUB_RUN_ATTEMPT")=="1","attempt one only")
    run=env.get("GITHUB_RUN_ID","");source=env.get("GITHUB_SHA","")
    require(re.fullmatch(r"[1-9][0-9]*",run)is not None,"run ID")
    require(re.fullmatch(r"[0-9a-f]{40}",source)is not None,"immutable source")
    result=dict(source=source,run_id=int(run),attempt=1)
    if case is not None:
        require(case in CASES,"case")
        result.update(case=case,group=GROUP+"-"+case,token=run+"-1")
    return result

def api(endpoint):
    return decode(subprocess.check_output(["gh","api","repos/"+REPOSITORY+"/"+endpoint]))

def release_binding(info,ref,tag,source):
    require(type(info.get("id"))is int and info["id"]>0 and info.get("tag_name")==tag,
            "release identity")
    require(info.get("target_commitish")==source and info.get("prerelease")is True and
      info.get("draft")is False,"release target")
    require(ref.get("ref")=="refs/tags/"+tag and ref.get("object",{}).get("type")=="commit"and
      ref["object"].get("sha")==source,"release tag target")
    assets=info.get("assets",[])
    require(isinstance(assets,list)and len({a["id"]for a in assets})==len(assets)and
      len({a["name"]for a in assets})==len(assets),"release asset duplicates")
    return {a["name"]:a for a in assets}

def reservation(ctx,proof,info,ref):
    tag="cloud-results-"+ctx["token"]+"-"+ctx["group"]
    assets=release_binding(info,ref,tag,ctx["source"])
    require(proof.get("tag")==tag and proof.get("tested_source")==ctx["source"]and
      proof.get("release_id")==info["id"],"reservation identity")
    require(proof.get("target_verified")is True and proof.get("assets_overwritten")is False and
      proof.get("externally_reserved")is True and proof.get("creation_attempted")is False,
      "externally verified reservation")
    require(proof.get("existing_assets")==[]and assets=={},"fresh reservation required")
    return dict(release_id=info["id"],tag=tag,source=ctx["source"],
      verified_before_archive_acquisition=True,assets_overwritten=False)

def pinned(c,root,path):
    raw=regular(root,path).read_bytes()
    require(fingerprint(raw)==c["required_files"][path],"pinned input bytes: "+path)
    return raw

def download(pin,path):
    require(not path.exists()and not path.is_symlink(),"download no overwrite")
    with path.open("xb")as f:
        subprocess.run(["gh","api","-H","Accept: application/octet-stream",
          "repos/"+REPOSITORY+"/releases/assets/"+str(pin["id"])],
          stdout=f,check=True,timeout=1800)
    require(file_pin(path)=={k:pin[k]for k in ("bytes","sha256")},"download fingerprint")

def digest(path):
    with Path(path).open("rb")as stream:
        return hashlib.file_digest(stream,"sha256").hexdigest()

def file_pin(path):
    require(path.is_file()and not path.is_symlink(),"regular downloaded file")
    return dict(bytes=path.stat().st_size,sha256=digest(path))

def acquire(c,case,parts,tmp,fetch=download):
    e=c["cases"][case];archive=tmp/"source.tar.gz"
    require(not archive.exists(),"archive no overwrite")
    whole=hashlib.sha256();size=0;observed=[]
    with archive.open("xb")as out:
        for row in parts["parts"]:
            pin=e["assets"][row["name"]];p=tmp/row["name"]
            fetch(pin,p)
            require(file_pin(p)=={k:row[k]for k in ("bytes","sha256")},"part fingerprint")
            with p.open("rb")as f:
                while block:=f.read(1024*1024):
                    out.write(block);whole.update(block);size+=len(block)
            observed.append(dict(row,asset_id=pin["id"]));p.unlink()
    require(size==parts["bytes"]and whole.hexdigest()==parts["sha256"],"combined archive fingerprint")
    return archive,dict(parts=observed,bytes=size,sha256=whole.hexdigest())

def select_archive(archive,expected,selected,directory,out):
    """Verify EVERY member; retain only exact wave and derived input JSON on runner."""
    require(set(selected)<=set(expected),"selected map")
    require(not out.exists()and not out.is_symlink(),"selected output new")
    out.mkdir()
    directories={str(p)for name in expected for p in PurePosixPath(name).parents if str(p)!="."}
    seen=set();observed={};total=0
    with tarfile.open(archive,"r|gz")as tar:
        for member in tar:
            raw=member.name
            if member.isdir()and raw.endswith("/"):raw=raw[:-1]
            checked_path(raw)
            if raw==directory:
                require(member.isdir()and raw not in seen,"archive root type/duplicate")
                seen.add(raw);continue
            require(raw.startswith(directory+"/"),"archive root namespace")
            name=raw[len(directory)+1:];checked_path(name)
            require(raw not in seen,"duplicate archive member");seen.add(raw)
            if member.isdir():
                require(name in directories,"unexpected archive directory");continue
            require(member.isfile()and not member.issparse(),"archive link/special/sparse")
            require(name in expected,"unexpected archive member")
            require(0<=member.size<=8*1024**3,"member size bound")
            total+=member.size;require(total<=16*1024**3,"archive expansion bound")
            h=hashlib.sha256();size=0;target=None
            if name in selected:
                p=out/name;p.parent.mkdir(parents=True,exist_ok=True);target=p.open("xb")
            try:
                stream=tar.extractfile(member);require(stream is not None,"archive stream")
                with stream:
                    while block:=stream.read(1024*1024):
                        size+=len(block);h.update(block)
                        if target is not None:target.write(block)
                require(size==member.size and h.hexdigest()==expected[name],"member fingerprint: "+name)
            finally:
                if target is not None:target.close()
            observed[name]=dict(bytes=size,sha256=h.hexdigest())
    require(set(observed)==set(expected),"incomplete full archive map")
    require(all(regular(out,n).is_file()for n in selected),"selected missing")
    return dict(full_members=observed,full_member_count=len(observed),uncompressed_bytes=total,
      every_member_authenticated=True,selected={n:observed[n]for n in selected},
      extraction_only_on_runner=True,source_archives_modified=False)

def source_guard(root=ROOT):
    raw=regular(root,CONFIG).read_bytes()
    require(fingerprint(raw)["sha256"]==CONFIG_SHA,"input contract bytes")
    c=decode(raw)
    require(c["schema"]=="cdr-drain-m1-wave-replay-inputs-v1" and c["branch"]==BRANCH and c["repository"]==REPOSITORY,"contract identity")
    require(c["native_simulation"] is False and c["all_acceptance_false"] is True,"contract scope")
    require(type(c["source_controls_authorized"]) is bool and type(c["readback_authorized"]) is bool,"typed authority")
    require(not c["readback_authorized"] or c["source_controls_authorized"],"readback requires controls")
    for name,pin in c["required_files"].items():
        require(fingerprint(regular(root,name).read_bytes())==pin,"source/input bytes: "+name)
    return c

def checkout_binding(ctx,c,root=ROOT):
    require(subprocess.check_output(["git","rev-parse","HEAD"],cwd=root,text=True).strip()==ctx["source"],"checkout identity")
    pins={}
    for name in c["new_files"]:
        raw=regular(root,name).read_bytes()
        frozen=subprocess.check_output(["git","show",ctx["source"]+":"+name],cwd=root)
        require(raw==frozen,"current source changed: "+name)
        pins[name]=fingerprint(raw)
    return pins

def validate_live(c,case,run,jobs,info,ref):
    p=c["producer"];e=c["cases"][case]
    require(run.get("workflow_id")==p["workflow_id"] and run.get("status")=="completed" and run.get("conclusion")=="failure","terminal producer failure")
    require([{k:j[k] for k in ("id","name","status","conclusion")} for j in jobs["jobs"]]==c["job_inventory"],"complete terminal jobs")
    require(all(j.get("run_id")==p["run_id"] and j.get("head_sha")==p["source"] for j in jobs["jobs"]),"all job sources")
    require(run.get("id")==p["run_id"]and run.get("run_attempt")==1 and
      run.get("head_sha")==p["source"]and run.get("head_branch")==p["branch"]and
      run.get("path")==p["workflow"]and run.get("event")=="workflow_dispatch",
      "producer run binding")
    rows=jobs["jobs"]
    require(jobs["total_count"]==len(rows)and len({j["id"]for j in rows})==len(rows),
      "complete producer job list")
    found=[j for j in rows if j["id"]==e["job_id"]]
    require(len(found)==1,"producer case job")
    j=found[0]
    require(j["name"]==e["job_name"]and j["run_id"]==p["run_id"]and
      j["head_sha"]==p["source"]and j["status"]=="completed"and
      j["conclusion"]=="failure","actual failed case binding")
    require([{k:s[k]for k in ("number","name","status","conclusion")}for s in j["steps"]]==e["steps"],
      "original case steps")
    assets=release_binding(info,ref,e["tag"],p["source"])
    require(info["id"]==e["release_id"]and set(assets)==set(e["assets"]),"producer release assets")
    for name,pin in e["assets"].items():
        a=assets[name]
        require(a.get("id")==pin["id"]and a.get("size")==pin["bytes"]and
          a.get("digest")=="sha256:"+pin["sha256"]and a.get("state")=="uploaded",
          "producer asset: "+name)
    return dict(case=case,source=p["source"],run_id=p["run_id"],attempt=1,
      release_id=e["release_id"],job_id=e["job_id"],job_conclusion="failure",
      original_electrical_rejection_preserved=True,overall_producer_success_assumed=False)

def metadata(c,case,root=ROOT):
    e=c["cases"][case];p=c["producer"]
    summary=decode(pinned(c,root,e["summary_path"]))
    parts=decode(pinned(c,root,e["parts_path"]))
    report=decode(pinned(c,root,e["report_path"]))
    plan=decode(pinned(c,root,e["plan_path"]))
    expected=decode(pinned(c,root,e["map_path"]))
    require(summary["source_head"]==p["source"] and summary["run_id"]==p["run_id"] and summary["run_attempt"]==1 and summary["case"]==case,"summary context")
    require(summary["status"]=="FAIL_UNQUALIFIED_CURRENT_WIDTH_LOADED_EVIDENCE" and summary["publication_qualified_as_success"] is False and summary["raw_terminal_bytes_unchanged"] is True and summary["raw_terminal_error"] is None and summary["publication_source_check"]["qualified"] is True,"original failure meaning")
    require(all(summary[k] is False for k in ("accepted","cdr_accepted","full_phy_accepted","physical_accepted","native_case_passed")),"summary acceptance")
    require(report["source_head"]==p["source"] and report["case"]==case and report["returncode"]==0 and report["diagnostics"]==[],"native report binding")
    require({k:report[k] for k in e["native_outcomes"]}==e["native_outcomes"],"original rejected verdicts")
    require(report["status"]=="REJECTED_WHOLE_MIM_PD500_LOADED" and report["vi"]["passed"] is False,"original VI rejection")
    require({k:report["composition_source"][k] for k in c["lineage_required"]}==e["lineage"],"current RC lineage")
    require(len(expected)==2797 and expected==summary["outputs"],"full outer map")
    for name,h in expected.items():
        checked_path(name);require(re.fullmatch(r"[0-9a-f]{64}",h) is not None,"member hash")
    require(all(expected[k]==v for k,v in e["selected"].items()),"selected map")
    require(expected[e["report_member"]]==c["required_files"][e["report_path"]]["sha256"],"native result bytes")
    require(expected["result.json"]==summary["raw_terminal"]["sha256"],"raw outer result distinct")
    require(len(report["outputs"])==2786 and all(expected["native/"+k]==v for k,v in report["outputs"].items()),"complete nested native map")
    require(plan["publication_qualified_as_success"] is False and plan["zero_byte_files_preserved_in_archive"] is True,"publication plan")
    require(parts["format"]=="ordered-tar-gzip-parts-v1" and parts["source_directory"]=="cloud-cdr-drain-m1-loaded-evidence-"+case and parts["stem"]=="cdr-drain-m1-loaded-"+case+"-"+str(p["run_id"])+"-1","archive namespace")
    require([x["index"] for x in parts["parts"]]==[0,1,2] and sum(x["bytes"] for x in parts["parts"])==parts["bytes"],"complete ordered parts")
    require(parts["verification"]==dict(parts=3,bytes=parts["bytes"],sha256=parts["sha256"],all_parts_and_combined_bytes_verified=True),"original parts verification")
    for row in parts["parts"]:
        pin=e["assets"][row["name"]]
        require(all(row[k]==pin[k] for k in ("bytes","sha256")),"part asset join")
    require({k:v for k,v in report["raw_capture"].items() if k!="logical_vector_order"}==e["raw_capture"],"capture metadata")
    require(len(report["vectors"])==len(set(report["vectors"]))==1151 and report["raw_capture"]["logical_vector_order"]==["time",*report["vectors"]],"complete vector order")
    require(report["binding"]["vi_names"]==e["VI_roles"],"VI roles")
    return summary,parts,report

def exact_functions(c,path,names,namespace,root=ROOT):
    text=pinned(c,root,path).decode("utf-8");tree=ast.parse(text)
    selected=[]
    for name in names:
        found=[n for n in tree.body if isinstance(n,ast.FunctionDef) and n.name==name]
        require(len(found)==1,"exact function: "+name)
        node=found[0]
        block="".join(text.splitlines(keepends=True)[node.lineno-1:node.end_lineno])
        # Function fingerprints use the exact source segment plus trailing newline.
        require(hashlib.sha256(block.encode()).hexdigest()==c["function_pins"][path][name],"function bytes: "+name)
        selected.append(node)
    module=ast.Module(body=selected,type_ignores=[])
    exec(compile(module,"<pinned:"+path+">","exec"),namespace)
    return namespace

def load_numeric(c,root=ROOT):
    source_guard(root)
    global np
    np=importlib.import_module("numpy")
    require(np.__version__=="2.3.3","exact NumPy version")
    require(sys.version_info[:2]==(3,12),"exact Python major/minor")
    rows=importlib.import_module("cdr_v58_saved_rows")
    core=importlib.import_module("cdr_v59_headroom_rows")
    for mod,name in ((rows,"scripts/cdr_v58_saved_rows.py"),(core,"scripts/cdr_v59_headroom_rows.py")):
        require(Path(mod.__file__).resolve()==regular(root,name).resolve(),"numeric module shadow")
        require(fingerprint(regular(root,name).read_bytes())==c["required_files"][name],"numeric source changed")
    parser=exact_functions(c,"scripts/build_pcie_local_vco_hybrid_v6.py",["require","statements","number"],dict(re=re,Decimal=Decimal),root)
    source=pinned(c,root,"scripts/cloud_cdr_drain_m1_loaded.py").decode()
    constants={}
    for node in ast.parse(source).body:
        if isinstance(node,ast.Assign) and len(node.targets)==1 and isinstance(node.targets[0],ast.Name) and node.targets[0].id in ("MODEL","BIASES"):
            constants[node.targets[0].id]=ast.literal_eval(node.value)
    require(set(constants)=={"MODEL","BIASES"},"binding constants")
    bind=exact_functions(c,"scripts/cloud_cdr_drain_m1_loaded.py",["bind_native"],dict(Counter=Counter,Decimal=Decimal,parser=SimpleNamespace(**parser),**constants),root)["bind_native"]
    read=exact_functions(c,"scripts/cloud_tx_stream.py",["digest","read_streamed_wave"],dict(np=np,Path=Path,hashlib=hashlib),root)["read_streamed_wave"]
    pin=c["measurement_block"]
    block="".join(source.splitlines(keepends=True)[pin["first_line"]-1:pin["last_line"]])
    require(fingerprint(block.encode())=={k:pin[k] for k in ("bytes","sha256")},"original measurement bytes")
    wrapper="def replay(t,d,capture,bound,bits,offset,constant,devices,mos,caps):\n        r={}\n"+block+"        return r\n"
    env=dict(np=np,UI=rows.UI,START=rows.START,STOP=rows.STOP,STEP=rows.STEP)
    exec(compile(wrapper,"<exact-original-measurement-block>","exec"),env)
    return SimpleNamespace(core=core,rows=rows,bind=bind,read=read,replay=env["replay"])

def validate_binding(numeric,report,contract,planes,model):
    bound=numeric.bind(model,contract,planes)
    require(bound==report["binding"],"full current native binding")
    require(contract["counts"]==dict(devices=500,R=24356,C=15566),"current composition counts")
    records={d["native_id"]:d for d in contract["device_records"]}
    for role,i,base,collector in (("xxp",167,"xp","vin"),("xxn",168,"xn","vip"),("xyp",171,"yp","vip"),("xyn",172,"yn","vin")):
        terms={t["terminal"]:t for t in records[i]["terminals"]}
        require(bound["vi_names"][role]=="xpd.xd"+str(i).zfill(4) and terms["B"]["native_net"]==base and terms["C"]["native_net"]==collector,"current VI contact")
    cap=records[279]
    require(cap["model"]=="cap_cmim" and cap["parameters"]==dict(w="40u",l="40u"),"current filter")
    require([(t["terminal"],t["native_cluster"],t["native_net"]) for t in cap["terminals"]]==[("mim_top",230,"vip"),("mim_btm",229,"vin")],"filter contacts")
    return bound

def scalar_replay(numeric,t,d,capture,report):
    actual=numeric.replay(t,d,capture,report["binding"],report["source_bits"],report["data_offset_s"],report["case"]=="constant_one",report["devices"],report["mos_devices"],report["native_caps"])
    compare_replay(actual,report)
    return actual

def compare_replay(actual,report):
    require(actual and set(actual)<=set(report),"replay field set")
    for name,value in actual.items():require(value==report[name],"original scalar replay: "+name)
    require(report["status"]=="REJECTED_WHOLE_MIM_PD500_LOADED","unchanged rejected status")
    require(not(actual["devices_passed"] and actual["data_passed"] and actual["vi"]["passed"]),"unchanged rejected predicate")
    return {"original_status":report["status"],"same_original_rejection":True,"fields":sorted(actual)}

def topology(c,report,contract,core):
    require(contract["counts"]==dict(devices=500,R=24356,C=15566),"current composition counts")
    records,branches,selected=core.topology(contract,report["binding"])
    for ident,pair in c["measurement"]["expected_current_collector_pairs"].items():
        term=next(t for t in records[int(ident)]["terminals"]if t["terminal"]=="C")
        require([term["native_cluster"],term["native_net"]]==pair,"current selector collector identity")
    require(c["measurement"]["gain"]in selected,"gain60 not in incident physical graph")
    require({11,40,179,217,59,60,111,112}<=set(selected),"reference/gain/bleeder contact closure")
    names=core.names_for(records,selected,report["binding"])
    require(set(names)<=set(report["vectors"]),"missing saved contact")
    require(len(names)==len(set(names)),"duplicate selected contact")
    return records,branches,selected,names

def contact_spreads(records,selected,bound,d,row,core):
    nets={}
    for i in selected:
        for term in records[i]["terminals"]:
            # Physical accesses remain distinct even on one native electrical net.
            key=(term["native_cluster"],term["native_net"])
            dev=bound["groups"][records[i]["model"]][core.name(i)]
            order=[t["terminal"]for t in records[i]["terminals"]]
            node=dev["nodes"][order.index(term["terminal"])]
            vec=None if node=="0"else "v("+node+")"
            value=0.0 if vec is None else float(d[vec][row])
            nets.setdefault(key,[]).append(dict(native_id=i,terminal=term["terminal"],
              vector=vec,value_v=value,explicit_ideal_ground=node=="0"))
    out=[]
    for (cluster,net),contacts in sorted(nets.items()):
        if len(contacts)<2:continue
        reference=contacts[0]["value_v"]
        for p in contacts:p["minus_first_contact_v"]=p["value_v"]-reference
        out.append(dict(native_cluster=cluster,native_net=net,contacts=contacts,
          max_minus_min_v=max(p["value_v"]for p in contacts)-min(p["value_v"]for p in contacts),
          reference_is_arbitrary_contact_not_ideal_alias=True))
    return out

def observations(c,t,d,report,contract,core,rows):
    records,branches,selected,names=topology(c,report,contract,core)
    rows.validate_rows(t,{n:d[n]for n in names},names)
    require(t[0]==0 and abs(float(t[-1])-rows.STOP)<1e-18,"capture time coverage")
    require(float(np.diff(t).max())<=rows.STEP*1.00001,"capture time spacing")
    active=np.flatnonzero(t>=c["measurement"]["active_start_s"])
    require(len(active)>0,"no active rows")
    focus=[*c["measurement"]["selectors"],c["measurement"]["gain"]]
    targets={};chosen=set();replay={}
    for i in focus:
        name=core.name(i);dev=report["devices"][name]
        vc=d[core.vector(report["binding"],i,"C")]
        vb=d[core.vector(report["binding"],i,"B")]
        ve=d[core.vector(report["binding"],i,"E")]
        ic=d[core.current_vector(records[i])]
        vce=vc-ve;check=report["device_checks"][name]
        actual=dict(minimum_active_vce_v=float(vce[active].min()),
          maximum_alltime_abs_vce_v=float(abs(vce).max()),
          maximum_alltime_abs_vbe_v=float(abs(vb-ve).max()),
          maximum_alltime_abs_ic_per_emitter_a=float(abs(ic).max()/dev["nx"]))
        require(all(actual[k]==check[k]for k in actual),"original scalar replay: "+name)
        replay[str(i)]=actual
        if i in c["measurement"]["selectors"]:
            value=actual["minimum_active_vce_v"];ties=active[vce[active]==value]
            spans=core.intervals(t,vce,rows.START,.4)
            kind="minimum_active_signed_VCE";signed=value
        else:
            value=actual["maximum_alltime_abs_vce_v"]
            ties=np.flatnonzero(abs(vce)==value);spans=[]
            kind="maximum_alltime_absolute_VCE";signed=float(vce[int(ties[0])])
        require(len(ties)>0,"missing extremum")
        first=int(ties[0]);windows=[]
        for native_row in ties:
            index=int(native_row)
            chosen.update(range(max(0,index-2),min(len(t),index+3)))
            lo=float(t[index])-c["measurement"]["window_half_width_s"]
            hi=float(t[index])+c["measurement"]["window_half_width_s"]
            ids=np.flatnonzero((t>=lo)&(t<=hi));chosen.update(map(int,ids))
            windows.append(dict(center_row=index,requested_start_s=lo,requested_end_s=hi,
              first_native_row=int(ids[0]),last_native_row=int(ids[-1]),
              clipped_start=lo<float(t[0]),clipped_end=hi>float(t[-1])))
        witness=core.frame(t,d,first,records,branches,selected,report["binding"])
        witness["shared_net_contact_spreads"]=contact_spreads(records,selected,report["binding"],d,first,core)
        witness["focus_device"]=rows.hbt_point(t,d,first,name,dev)
        targets[str(i)]=dict(kind=kind,original_scalar=value,signed_VCE_at_first_witness_v=signed,
          first_native_row=first,all_exact_tie_rows=list(map(int,ties)),first_witness=witness,
          all_violation_intervals=spans,fixed_windows=windows)
    return dict(status="CURRENT_NOMINAL_CONTACT_OBSERVATIONS_ONLY",targets=targets,
      original_five_device_scalar_replay=replay,selected_vectors=names,frame_rows=sorted(chosen),
      full_native_rows=len(t),selected_native_ids=selected,
      selected_records=[records[i]for i in selected],topology=branches,
      windows_half_width_s=c["measurement"]["window_half_width_s"],adjacent_rows_each_side=2,
      ties_preserved=True,interpolation=False,decimation=False,
      unsaved=["HBT Ib/Ie","intrinsic rppd current","unsaved internal wire voltages",
               "complete dynamic KCL"],**READBACK_FLAGS)

def vi_observations(t,d,report,contract,numeric):
    rows=numeric.rows;records={r["native_id"]:r for r in contract["device_records"]}
    names=set()
    for i in (167,168,169,171,172,173,279):
        dev=report["binding"]["groups"][records[i]["model"]]["xpd.xd"+str(i).zfill(4)]
        names.update("v("+n+")" for n in dev["nodes"] if n!="0")
        if i!=279:names.add("@q.xpd.xd"+str(i).zfill(4)+".qnpn13g2[ic]")
    names.update("v("+n+")" for n in ("vip","vin","xp","xn","yp","yn","irvx","irvy"))
    require(names<=set(d),"missing VI saved contact")
    def current(i):return d["@q.xpd.xd"+str(i).zfill(4)+".qnpn13g2[ic]"]
    series={"vi_signed_current_a":(current(167)+current(172))-(current(168)+current(171)),
      "vi_output_difference_v":d["v(vip)"]-d["v(vin)"],
      "filter_difference_v":d["v(xpd.w_t279_mim_top)"]-d["v(xpd.w_t279_mim_btm)"]}
    for i,port,plate in ((167,"vin","btm"),(172,"vin","btm"),(168,"vip","top"),(171,"vip","top")):
        collector=d["v(xpd.w_t"+str(i).zfill(3)+"_c)"]
        series[str(i)+"_collector_minus_macro_v"]=collector-d["v("+port+")"]
        series[str(i)+"_collector_minus_filter_v"]=collector-d["v(xpd.w_t279_mim_"+plate+")"]
    windows=[]
    for label,lo,hi in [("original",8,255),*[(str(k)+"UI",k,k+1) for k in range(8,255)],("quarter0",8,70),("quarter1",70,132),("quarter2",132,194),("quarter3",194,255)]:
        ids=np.flatnonzero((t>=rows.START+lo*rows.UI)&(t<=rows.START+hi*rows.UI))
        require(len(ids)>=2,"incomplete settling window")
        window=(t>=rows.START+lo*rows.UI)&(t<=rows.START+hi*rows.UI)
        values={}
        for name,value in series.items():
            sampled=value[window]
            values[name]=dict(mean=float(np.trapezoid(sampled,t[window])/(t[window][-1]-t[window][0])),
              first=float(sampled[0]),last=float(sampled[-1]),minimum=float(sampled.min()),maximum=float(sampled.max()))
        windows.append(dict(label=label,UI_offsets=[lo,hi],first_row=int(ids[0]),last_row=int(ids[-1]),sample_count=len(ids),actual_start_s=float(t[ids[0]]),actual_end_s=float(t[ids[-1]]),observations=values))
    require(windows[0]["observations"]["vi_signed_current_a"]["mean"]==report["vi"]["mean_signed_current_a"] and windows[0]["observations"]["vi_output_difference_v"]["mean"]==report["vi"]["mean_output_difference_v"],"VI original mean reproduction")
    return dict(status="VI_CONTACT_SETTLING_OBSERVATIONS_ONLY",case=report["case"],selected_vectors=sorted(names),windows=windows,original_vi=report["vi"],longer_time_settling_proved=False,complete_dynamic_KCL=False,**READBACK_FLAGS),series

def write_full_rows(path,t,d,names,series):
    require(not path.exists() and not path.is_symlink(),"full rows no overwrite")
    require(names==sorted(set(names)) and set(names)<=set(d),"full rows vector binding")
    require(all(len(v)==len(t) for v in [*(d[n] for n in names),*series.values()]),"full row lengths")
    derived=sorted(series);count=0
    with gzip.open(path,"xt",encoding="utf-8") as f:
        f.write(json.dumps(dict(schema="full-native-selected-rows-v1",vectors=names,vector_units=["V" if n.startswith("v(") else "A" for n in names],derived=derived,derived_units=["A" if n.endswith("_a") else "V" for n in derived],time_unit="s",rows=len(t),interpolation=False,decimation=False),allow_nan=False)+"\n")
        for index,time in enumerate(t):
            row=dict(index=index,time_s=float(time),values=[float(d[n][index]) for n in names],derived=[float(series[n][index]) for n in derived])
            f.write(json.dumps(row,separators=(",",":"),allow_nan=False)+"\n");count+=1
    require(count==len(t),"complete full rows")
    return dict(**file_pin(path),rows=count,vectors=names,derived=derived,all_selected_native_rows_preserved=True)

def controls_binding(raw,ctx):
    r=decode(raw)
    require(r.get("status")=="PASS_DRAIN_M1_WAVE_REPLAY_SOURCE_CONTROLS" and r.get("passed") is True,"source controls status")
    require(r.get("current_context")==dict(source=ctx["source"],run_id=ctx["run_id"],attempt=1,source_controls_only=True,native_executed=False),"same-source current controls")
    require(r.get("native_executed") is False and r.get("physical_acceptance") is False and r.get("actual_capture_replayed") is False,"source controls scope")
    require(r.get("completed_groups")==SOURCE_GROUPS and r.get("failures")==[],"complete controls")
    require(r.get("counts")==SOURCE_COUNTS,"controls counts")
    return fingerprint(raw)

def perform(ctx,reserved,controls_raw,out,c,root=ROOT,api_call=api,fetch=download):
    require(c["source_controls_authorized"] is True and c["readback_authorized"] is True,"readback disabled")
    binding=checkout_binding(ctx,c,root)
    write_new(out/"current-source-binding.json",encode(binding))
    control_pin=controls_binding(controls_raw,ctx)
    tag="cloud-results-"+ctx["token"]+"-"+ctx["group"]
    fresh=reservation(ctx,reserved,api_call("releases/tags/"+tag),api_call("git/ref/tags/"+tag))
    write_new(out/"reservation.json",encode(fresh));write_new(out/"source-controls.json",controls_raw)
    case=ctx["case"];e=c["cases"][case]
    run=api_call("actions/runs/"+str(c["producer"]["run_id"]))
    jobs=api_call("actions/runs/"+str(c["producer"]["run_id"])+"/attempts/1/jobs?per_page=100")
    release=api_call("releases/"+str(e["release_id"]));ref=api_call("git/ref/tags/"+e["tag"])
    for name,obj in (("producer-run.json",run),("producer-jobs.json",jobs),("producer-release.json",release),("producer-ref.json",ref)):write_new(out/name,encode(obj))
    live=validate_live(c,case,run,jobs,release,ref)
    summary,parts,report=metadata(c,case,root)
    for suffix,key in (("summary.json","summary_path"),("parts.json","parts_path"),("native-result.json","report_path")):write_new(out/("producer-"+suffix),pinned(c,root,e[key]))
    write_new(out/"live-binding.json",encode(live))
    require(shutil.disk_usage(out.parent).free>=parts["bytes"]+e["wave"]["bytes"]+2*1024**3,"runner space before acquisition")
    primary=None;tmp=tempfile.TemporaryDirectory(prefix="cdr-drain-wave-",dir=out.parent)
    try:
        work=Path(tmp.name);archive,transport=acquire(c,case,parts,work,fetch)
        write_new(out/"transport-proof.json",encode(transport))
        selected=list(e["selected"])
        full=select_archive(archive,summary["outputs"],selected,parts["source_directory"],work/"selected")
        write_new(out/"complete-input-census.json",encode(full));saved=work/"selected"
        require(file_pin(regular(saved,e["wave_member"]))==e["wave"],"selected wave identity")
        require(regular(saved,e["report_member"]).read_bytes()==pinned(c,root,e["report_path"]),"actual archived native result")
        require(file_pin(regular(saved,"result.json"))=={k:summary["raw_terminal"][k] for k in ("bytes","sha256")},"actual raw outer result")
        comp=decode(regular(saved,c["composition"]["member"]).read_bytes())
        numeric=load_numeric(c,root)
        model=regular(saved,"native/current-mim-bundle/mim/composition/pd500-mim-wire.spice").read_text()
        planes=decode(regular(saved,"native/current-mim-bundle/canonical-current-view/native-planes.json").read_bytes())
        validate_binding(numeric,report,comp,planes,model)
        t,d,capture=numeric.read(regular(saved,e["wave_member"]),report["vectors"],numeric.rows.STOP,numeric.rows.STEP)
        capture_binding(capture,report)
        replay=scalar_replay(numeric,t,d,capture,report)
        write_new(out/"original-scalar-replay.json",encode(replay))
        diag=observations(c,t,d,report,comp,numeric.core,numeric.rows)
        vi,series=vi_observations(t,d,report,comp,numeric)
        write_new(out/"selector-gain-diagnosis.json",encode(diag));write_new(out/"vi-diagnosis.json",encode(vi))
        names=sorted(set(diag["selected_vectors"])|set(vi["selected_vectors"])|set(c["minimum_vectors"]))
        frames=write_full_rows(out/"full-selected-contact-rows.jsonl.gz",t,d,names,series)
        write_new(out/"full-row-index.json",encode(frames))
        write_new(out/"saved-vector-census.json",encode(dict(vectors=report["vectors"],raw_order=capture["logical_vector_order"],selected=names,unobserved=diag["unsaved"])))
        for name in selected:require(file_pin(regular(saved,name))==full["selected"][name],"selected source changed")
        source_guard(root);checkout_binding(ctx,c,root)
        result=dict(status="PASS_AUTHENTIC_EXISTING_CAPTURE_REPLAY_ONLY",current_context=ctx,producer=live,current_controls=control_pin,reservation=fresh,source_capture=capture,complete_input_members=full["full_member_count"],frames=frames,original_electrical_status=report["status"],same_original_rejection=True,native_CAD_executed=False,**READBACK_FLAGS)
        del t,d
        return result
    except BaseException as exc:
        primary=exc;raise
    finally:
        try:tmp.cleanup()
        except BaseException as exc:
            preserve_error(out,"cleanup-error.json",exc,primary)
            if primary is None:raise

def preserve_error(out,name,error,primary=None):
    record=dict(error=dict(type=type(error).__name__,message=str(error)),primary_error=None if primary is None else dict(type=type(primary).__name__,message=str(primary)))
    try:write_new(out/name,encode(record))
    except BaseException as save_error:
        try:print("CDR_DRAIN_REPLAY_PRESERVATION_ERROR "+json.dumps(dict(record,save_error=repr(save_error)),sort_keys=True),flush=True)
        except BaseException:pass

def run(ctx,reserved,controls_raw,out,root=ROOT,api_call=api,fetch=download):
    require(not out.exists() and not out.is_symlink(),"output no overwrite")
    out.mkdir(parents=True);primary=None
    try:
        c=source_guard(root)
        result=perform(ctx,reserved,controls_raw,out,c,root,api_call,fetch)
        source_guard(root);write_new(out/"readback-result.json",encode(result));return result
    except BaseException as exc:
        primary=exc
        failure=dict(status="FAIL_DRAIN_M1_EXISTING_WAVE_REPLAY",current_context=ctx,error=dict(type=type(exc).__name__,message=str(exc)),traceback=traceback.format_exc(),native_CAD_executed=False,**READBACK_FLAGS)
        try:write_new(out/"readback-failure.json",encode(failure))
        except BaseException as save_error:
            try:print("CDR_DRAIN_REPLAY_FAILURE "+json.dumps(dict(failure,save_error=repr(save_error)),sort_keys=True),flush=True)
            except BaseException:pass
        for name in (CONFIG,*NEW_SOURCES):
            try:write_new(out/("retained-source/"+name),regular(root,name).read_bytes())
            except BaseException as save_error:preserve_error(out,"retain-"+Path(name).name+".error.json",save_error,exc)
        try:retain_source_changes(root,out)
        except BaseException as save_error:preserve_error(out,"source-change-preservation-error.json",save_error,exc)
        raise
    finally:
        try:emit(out)
        except BaseException as exc:
            preserve_error(out,"emission-error.json",exc,primary)
            if primary is None:raise

def emit(out,writer=print):
    records={p.relative_to(out).as_posix():file_pin(p)for p in sorted(out.rglob("*"))if p.is_file()}
    writer("CDR_DRAIN_REPLAY_INDEX "+json.dumps(records,sort_keys=True),flush=True)
    for name,pin in records.items():
        if name.endswith(".jsonl.gz"):
            writer("CDR_DRAIN_REPLAY_EXTERNAL_COMPLETE_FILE "+json.dumps(dict(name=name,transport="reserved-release-and-fallback-artifact",**pin),sort_keys=True),flush=True)
            continue
        compressor=zlib.compressobj(level=6);pending=b"";index=0
        with regular(out,name).open("rb")as f:
            while block:=f.read(65536):
                pending+=compressor.compress(block)
                while len(pending)>=24576:
                    part,pending=pending[:24576],pending[24576:]
                    writer("CDR_DRAIN_REPLAY_CHUNK "+json.dumps(dict(name=name,index=index,encoding="zlib+base64",
                      data=base64.b64encode(part).decode()),sort_keys=True),flush=True);index+=1
        pending+=compressor.flush()
        for pos in range(0,len(pending),24576):
            writer("CDR_DRAIN_REPLAY_CHUNK "+json.dumps(dict(name=name,index=index,encoding="zlib+base64",
              data=base64.b64encode(pending[pos:pos+24576]).decode()),sort_keys=True),flush=True);index+=1
        writer("CDR_DRAIN_REPLAY_END "+json.dumps(dict(name=name,chunks=index,**pin),sort_keys=True),flush=True)
    return records

def main():
    p=argparse.ArgumentParser()
    p.add_argument("--readback",action="store_true",required=True)
    p.add_argument("--case",choices=CASES,required=True)
    p.add_argument("--output",type=Path,required=True)
    p.add_argument("--reservation",type=Path,required=True)
    p.add_argument("--controls-proof",type=Path,required=True)
    args=p.parse_args();ctx=context(os.environ,args.case)
    require(subprocess.check_output(["git","rev-parse","HEAD"],cwd=ROOT,text=True).strip()==ctx["source"],
      "checkout identity")
    require(args.reservation.is_file()and not args.reservation.is_symlink(),"reservation regular")
    require(args.controls_proof.is_file()and not args.controls_proof.is_symlink(),"controls regular")
    run(ctx,decode(args.reservation.read_bytes()),args.controls_proof.read_bytes(),args.output)

def write_new(path,raw):
    path.parent.mkdir(parents=True,exist_ok=True)
    with path.open("xb") as out:out.write(raw)

def capture_binding(capture,report):
    require(capture==report["raw_capture"],"original native parser metadata reproduction")
    return capture

def retain_source_changes(root,out):
    raw=regular(root,CONFIG).read_bytes()
    if fingerprint(raw)["sha256"]!=CONFIG_SHA:return
    c=decode(raw);changes={}
    for name,expected in c["required_files"].items():
        try:
            actual=regular(root,name).read_bytes();pin=fingerprint(actual)
            if pin!=expected:
                write_new(out/("retained-input/"+name),actual)
                changes[name]=dict(expected=expected,observed=pin,raw_bytes_retained=True)
        except BaseException as error:
            changes[name]=dict(expected=expected,error=repr(error))
    write_new(out/"source-change-census.json",encode(changes))

if __name__=='__main__':main()
