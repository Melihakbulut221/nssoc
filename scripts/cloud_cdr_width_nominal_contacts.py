#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0
"""Hosted read-only current nominal contact observations. No CAD or acceptance."""
import argparse,ast,base64,copy,hashlib,importlib,json,math,os,re,shutil
import subprocess,sys,tarfile,tempfile,traceback,zlib
from pathlib import Path,PurePosixPath
ROOT=Path(__file__).resolve().parents[1]
CONFIG="scripts/cdr-width-nominal-contact-inputs.json"
CONFIG_SHA="a9597e38ece856b86a9e668d4750e02c0a15954420263aeb952b6f9b8fe8090a"
BRANCH="codex/cdr-width-nominal-contact-readback"
REPOSITORY="Melihakbulut221/nssoc"
GROUP="cdr-width-nominal-contact-readback"
CASES=("nominal_early","nominal_late")
READBACK_FLAGS=dict(accepted=False,cdr_accepted=False,physical_acceptance=False,
 full_phy_accepted=False,causality_proven=False,new_simulation=False,geometry_changed=False)
SOURCE_COUNTS=dict(positive=16,refusal=66,lifecycle=5)
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
def source_guard(root=ROOT):
    raw=regular(root,CONFIG).read_bytes()
    require(hashlib.sha256(raw).hexdigest()==CONFIG_SHA,"input contract bytes")
    c=decode(raw)
    require(c["schema"]=="current-width-nominal-contact-inputs-v1"and
      c["all_acceptance_false"]is True and c["native_simulation"]is False,"contract scope")
    for p,pin in c["required_files"].items():
        require(fingerprint(regular(root,p).read_bytes())==pin,"source/input bytes: "+p)
    return c
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
def validate_live(c,case,run,jobs,info,ref):
    p=c["producer"];e=c["cases"][case]
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
def pinned(c,root,path):
    raw=regular(root,path).read_bytes()
    require(fingerprint(raw)==c["required_files"][path],"pinned input bytes: "+path)
    return raw
def metadata(c,case,root=ROOT):
    e=c["cases"][case]
    summary=decode(pinned(c,root,e["summary_path"]))
    parts=decode(pinned(c,root,e["parts_path"]))
    report=decode(pinned(c,root,e["report_path"]))
    plan=decode(pinned(c,root,e["plan_path"]))
    p=c["producer"]
    require(summary["source_head"]==p["source"]and summary["run_id"]==p["run_id"]and
      summary["run_attempt"]==1 and summary["case"]==case,"summary context")
    require(summary["status"]=="FAIL_UNQUALIFIED_CURRENT_WIDTH_LOADED_EVIDENCE"and
      summary["publication_qualified_as_success"]is False and
      summary["raw_terminal_bytes_unchanged"]is True and summary["raw_terminal_error"]is None and
      summary["publication_source_check"]["qualified"]is True,"original failure meaning")
    for key in ("accepted","cdr_accepted","full_phy_accepted","physical_accepted","native_case_passed"):
        require(summary[key]is False,"summary acceptance")
    require(report["source_head"]==p["source"]and report["case"]==case and
      report["returncode"]==0 and report["diagnostics"]==[]and
      report["status"]=="REJECTED_WHOLE_MIM_PD500_LOADED","native report binding")
    for key in ("accepted","data_passed","phase_passed","devices_passed","full_phy_accepted"):
        require(report[key]is False,"original electrical rejection")
    lineage=report["composition_source"]
    require(lineage["run"]==40830441311 and lineage["source_head"]=="7ddf83d17a3b3fe0efb1eb31594b7d4d3e831b8f"and
      lineage["complete_graph_members"]==4103 and lineage["current_members"]==75 and
      lineage["raw_result_sha256"]=="9d128f021278fc2a3fa0be68db8f8c0b73824fa24939341802ba3ba6bfe1a820"and
      lineage["summary_sha256"]=="c5695d1cde81f3aac997f461ba6e663eed7e5dfb827600d84e1ec768d84f6a23",
      "current RC lineage")
    expected=summary["outputs"]
    require(len(expected)==e["outer_members"],"full outer member count")
    for name,h in expected.items():
        checked_path(name);require(re.fullmatch(r"[0-9a-f]{64}",h)is not None,"member hash")
    require(expected[e["report_member"]]==c["required_files"][e["report_path"]]["sha256"]and
      expected[e["wave_member"]]==e["wave"]["sha256"]and
      expected[c["composition"]["member"]]==c["composition"]["sha256"],"selected member joins")
    require(len(report["outputs"])==e["native_output_members"]and
      all(expected["native/"+k]==v for k,v in report["outputs"].items()),"complete nested native map")
    require(plan["publication_qualified_as_success"]is False and
      plan["zero_byte_files_preserved_in_archive"]is True,"publication plan meaning")
    require(parts["format"]=="ordered-tar-gzip-parts-v1"and
      parts["source_directory"]=="cloud-cdr-width-loaded-evidence-"+case and
      parts["stem"]=="cdr-width-loaded-"+case+"-"+str(p["run_id"])+"-1","archive namespace")
    require([x["index"]for x in parts["parts"]]==list(range(5))and
      sum(x["bytes"]for x in parts["parts"])==parts["bytes"],"complete ordered parts")
    require(parts["verification"]==dict(parts=5,bytes=parts["bytes"],sha256=parts["sha256"],
      all_parts_and_combined_bytes_verified=True),"original part verification")
    for row in parts["parts"]:
        pin=e["assets"][row["name"]]
        require(all(row[k]==pin[k]for k in ("bytes","sha256")),"part asset join")
    require({k:v for k,v in report["raw_capture"].items()if k!="logical_vector_order"}==e["raw_capture"],
      "capture metadata")
    require(report["raw_capture"]["logical_vector_order"]==["time",*report["vectors"]],"vector order")
    return summary,parts,report
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
def load_numeric():
    global np
    np=importlib.import_module("numpy")
    require(np.__version__=="2.3.3","exact NumPy version")
    core=importlib.import_module("cdr_v59_headroom_rows")
    rows=importlib.import_module("cdr_v58_saved_rows")
    for mod,p in ((core,"scripts/cdr_v59_headroom_rows.py"),(rows,"scripts/cdr_v58_saved_rows.py")):
        require(Path(mod.__file__).resolve()==regular(ROOT,p).resolve(),"numeric module shadow")
    return core,rows

def read_streamed_wave(path,vectors,stop,step):
    """Strict full regular-file raw reader with bounded memory mapping."""
    path=Path(path);assert vectors and len(vectors)==len(set(vectors))
    with path.open('rb') as stream:
        parts=[]
        while True:
            row=stream.readline(1048576)
            assert row and row.endswith(b'\n'),'Incomplete native header'
            parts.append(row)
            assert sum(map(len,parts))<=1048576,'Unbounded native header'
            if row==b'Binary:\n':break
        offset=stream.tell()
    header=b''.join(parts).decode('ascii')
    def field(key):
        matches=[line.split(':',1)[1].strip() for line in header.splitlines() if line.startswith(key+':')]
        assert len(matches)==1,('Missing/duplicate raw field',key)
        return matches[0]
    assert field('Flags')=='real' and field('Plotname')=='Transient Analysis'
    width=int(field('No. Variables'));count=int(field('No. Points'))
    assert width==len(vectors)+1 and count>1
    assert header.count('Variables:\n')==1
    table=[row.split() for row in header.split('Variables:\n')[1].split('Binary:\n')[0].splitlines()]
    assert len(table)==width and all(len(row)==3 for row in table)
    assert [r[0] for r in table]==list(map(str,range(width)))
    assert table[0]==['0','time','time']
    aliases={'time':'time'}
    for name in vectors:
        for native in ([name,'i('+name+')'] if name.startswith('@') else [name]):
            assert native not in aliases or aliases[native]==name
            aliases[native]=name
    names=[]
    for _,native,kind in table:
        assert native in aliases,('Unexpected native vector',native)
        logical=aliases[native]
        expected='time' if logical=='time' else 'voltage' if logical.startswith('v(') else 'current'
        assert kind==expected,(native,kind,expected)
        names.append(logical)
    assert len(set(names))==width and set(names)=={'time',*vectors}
    assert path.stat().st_size-offset==count*width*8,'Truncated/extra raw payload or incorrect header row count'
    matrix=np.memmap(path,mode='r',dtype='<f8',offset=offset,shape=(count,width))
    for first in range(0,count,1024):
        assert np.isfinite(matrix[first:first+1024]).all(),'Nonfinite native sample'
    t=matrix[:,0]
    assert t[0]==0 and abs(t[-1]-stop)<1e-18
    delta=np.diff(t)
    assert np.all(delta>0) and np.max(delta)<=step*1.00001
    values={n:matrix[:,i] for i,n in enumerate(names) if i}
    return t,values,dict(header_rows=count,columns=width,header_bytes=offset,
        raw_bytes=path.stat().st_size,raw_sha256=digest(path),
        start_s=float(t[0]),end_s=float(t[-1]),max_step_s=float(delta.max()),
        logical_vector_order=names,complete_unmodified_rows=True,
        method='Memory-mapped full binary raw; every original vector retained; no interpolation/decimation')


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
def write_frames(path,t,d,diagnosis):
    names=diagnosis["selected_vectors"];h=hashlib.sha256();size=0;count=0
    with path.open("xb")as out:
        for row in diagnosis["frame_rows"]:
            vals=[float(t[row]),*[float(d[n][row])for n in names]]
            raw=(json.dumps(dict(row=row,time_s=vals[0],values=vals,
              float64_le_hex=np.asarray(vals,dtype="<f8").tobytes().hex()),
              separators=(",",":"),allow_nan=False)+"\n").encode()
            out.write(raw);h.update(raw);size+=len(raw);count+=1
    require(count==len(diagnosis["frame_rows"]),"incomplete selected frame rows")
    return dict(columns=["time",*names],rows=count,bytes=size,sha256=h.hexdigest(),
      row_indices=diagnosis["frame_rows"],format="JSONL values and exact original little-endian float64 bits",
      time_interpolation=False,all_declared_window_and_tie_neighbor_rows_preserved=True)
def write_new(path,raw):
    with path.open("xb")as out:out.write(raw)
def controls_binding(raw,ctx):
    r=decode(raw)
    require(r.get("status")=="PASS_CURRENT_WIDTH_CONTACT_SOURCE_CONTROLS","source controls status")
    require(r.get("current_context")==dict(source=ctx["source"],run_id=ctx["run_id"],attempt=1,
      source_controls_only=True,native_executed=False),"same-source current controls")
    require(r.get("native_executed")is False and r.get("physical_acceptance")is False,
      "source controls scope")
    require(r.get("passed")is True,"source controls passed")
    require(r.get("counts")==SOURCE_COUNTS,"complete source control counts")
    return fingerprint(raw)
def perform(ctx,reserved,controls_raw,out,c,root=ROOT,api_call=api,fetch=download):
    control_pin=controls_binding(controls_raw,ctx)
    tag="cloud-results-"+ctx["token"]+"-"+ctx["group"]
    fresh=reservation(ctx,reserved,api_call("releases/tags/"+tag),api_call("git/ref/tags/"+tag))
    write_new(out/"reservation.json",encode(fresh));write_new(out/"source-controls.json",controls_raw)
    case=ctx["case"];e=c["cases"][case]
    run=api_call("actions/runs/"+str(c["producer"]["run_id"]))
    jobs=api_call("actions/runs/"+str(c["producer"]["run_id"])+"/attempts/1/jobs?per_page=100")
    release=api_call("releases/"+str(e["release_id"]));ref=api_call("git/ref/tags/"+e["tag"])
    live=validate_live(c,case,run,jobs,release,ref)
    for name,obj in (("producer-run.json",run),("producer-jobs.json",jobs),("producer-release.json",release),("producer-ref.json",ref)):
        write_new(out/name,encode(obj))
    summary,parts,report=metadata(c,case,root)
    for suffix,key in (("summary.json","summary_path"),("parts.json","parts_path"),("native-result.json","report_path")):
        write_new(out/("producer-"+suffix),regular(root,e[key]).read_bytes())
    write_new(out/"live-binding.json",encode(live))
    require(shutil.disk_usage(out.parent).free>=parts["bytes"]+e["wave"]["bytes"]+2*1024**3,
      "runner space before acquisition")
    primary=None;tmp=tempfile.TemporaryDirectory(prefix="cdr-current-contact-",dir=out.parent)
    try:
        work=Path(tmp.name);archive,transport=acquire(c,case,parts,work,fetch)
        write_new(out/"transport-proof.json",encode(transport))
        selected=[e["wave_member"],e["report_member"],c["composition"]["member"]]
        full=select_archive(archive,summary["outputs"],selected,parts["source_directory"],work/"selected")
        write_new(out/"complete-input-census.json",encode(full))
        saved=work/"selected"
        require(file_pin(regular(saved,e["wave_member"]))==e["wave"],"selected wave identity")
        require(regular(saved,e["report_member"]).read_bytes()==regular(root,e["report_path"]).read_bytes(),
          "actual archived native report bytes")
        comp=regular(saved,c["composition"]["member"]).read_bytes()
        require(fingerprint(comp)=={k:c["composition"][k]for k in ("bytes","sha256")},
          "current archived composition")
        core,rows=load_numeric()
        t,d,capture=read_streamed_wave(regular(saved,e["wave_member"]),report["vectors"],rows.STOP,rows.STEP)
        require(capture==report["raw_capture"],"original native parser metadata reproduction")
        diagnosis=observations(c,t,d,report,decode(comp),core,rows)
        frames=write_frames(out/"contact-windows.jsonl",t,d,diagnosis)
        write_new(out/"frames.json",encode(frames));write_new(out/"diagnosis.json",encode(diagnosis))
        for name in selected:require(file_pin(regular(saved,name))==full["selected"][name],"selected source changed")
        result=dict(status="PASS_CURRENT_NOMINAL_CONTACT_READBACK_NOT_ACCEPTANCE",current_context=ctx,
          producer=live,current_controls=control_pin,reservation=fresh,source_capture=capture,
          complete_input_members=full["full_member_count"],frames=frames,
          extrema={k:{q:v[q]for q in ("kind","first_native_row","all_exact_tie_rows","original_scalar")}
            for k,v in diagnosis["targets"].items()},native_CAD_executed=False,**READBACK_FLAGS)
        del t,d
        return result
    except BaseException as exc:
        primary=exc;raise
    finally:
        try:tmp.cleanup()
        except BaseException as exc:
            try:write_new(out/"cleanup-error.json",encode(dict(error=repr(exc),primary_error=None if primary is None else repr(primary))))
            except BaseException:pass
            if primary is None:raise
def emit(out,writer=print):
    records={p.relative_to(out).as_posix():file_pin(p)for p in sorted(out.rglob("*"))if p.is_file()}
    writer("CDR_CONTACT_INDEX "+json.dumps(records,sort_keys=True),flush=True)
    for name,pin in records.items():
        compressor=zlib.compressobj(level=6);pending=b"";index=0
        with regular(out,name).open("rb")as f:
            while block:=f.read(65536):
                pending+=compressor.compress(block)
                while len(pending)>=24576:
                    part,pending=pending[:24576],pending[24576:]
                    writer("CDR_CONTACT_CHUNK "+json.dumps(dict(name=name,index=index,encoding="zlib+base64",
                      data=base64.b64encode(part).decode()),sort_keys=True),flush=True);index+=1
        pending+=compressor.flush()
        for pos in range(0,len(pending),24576):
            writer("CDR_CONTACT_CHUNK "+json.dumps(dict(name=name,index=index,encoding="zlib+base64",
              data=base64.b64encode(pending[pos:pos+24576]).decode()),sort_keys=True),flush=True);index+=1
        writer("CDR_CONTACT_END "+json.dumps(dict(name=name,chunks=index,**pin),sort_keys=True),flush=True)
    return records
def run(ctx,reserved,controls_raw,out,root=ROOT,api_call=api,fetch=download):
    require(not out.exists()and not out.is_symlink(),"output no overwrite")
    out.mkdir(parents=True);primary=None
    try:
        c=source_guard(root)
        result=perform(ctx,reserved,controls_raw,out,c,root,api_call,fetch)
        source_guard(root)
        write_new(out/"readback-result.json",encode(result));return result
    except BaseException as exc:
        primary=exc
        failure=dict(status="FAIL_CURRENT_NOMINAL_CONTACT_READBACK",current_context=ctx,
          error=dict(type=type(exc).__name__,message=str(exc)),traceback=traceback.format_exc(),
          native_CAD_executed=False,**READBACK_FLAGS)
        try:write_new(out/"readback-failure.json",encode(failure))
        except BaseException:
            try:print("CDR_CONTACT_FAILURE "+json.dumps(failure,sort_keys=True),flush=True)
            except BaseException:pass
        raise
    finally:
        try:emit(out)
        except BaseException:
            if primary is None:raise
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
if __name__=="__main__":main()
