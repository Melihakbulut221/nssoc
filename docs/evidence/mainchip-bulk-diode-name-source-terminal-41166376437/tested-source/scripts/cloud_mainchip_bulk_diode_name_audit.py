#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0
"""Read an authenticated existing instance snapshot on GitHub; never run CAD."""
import argparse,hashlib,io,json,os,re,shutil,subprocess,sys,traceback,types
from pathlib import Path
import ijson
import cloud_mainchip_bulk_postdrt_antenna as host
import cloud_mainchip_full_antenna_readback as archive_reader
ROOT=Path(__file__).resolve().parents[1]
MANIFEST="scripts/mainchip-bulk-diode-name-audit-pins.json"
CONFIG="scripts/mainchip-bulk-diode-name-audit-inputs.json"
FLAGS=dict(native_CAD_executed=False,geometry_changed=False,physical_acceptance=False,timing_accepted=False,full_phy_accepted=False,actual_crash_causality_proven=False)
def require(value,message):
    if not value:raise AssertionError(message)
def encode(value):return (json.dumps(value,sort_keys=True,indent=2,allow_nan=False)+"\n").encode()
def write(path,value):host.f.write_new(path,encode(value))
def guard():
    ctx=host.context(os.environ)
    require(subprocess.check_output(["git","rev-parse","HEAD"],cwd=ROOT,text=True).strip()==ctx["source"],"exact checkout")
    raw=(ROOT/MANIFEST).read_bytes()
    require(raw==subprocess.check_output(["git","show",ctx["source"]+":"+MANIFEST],cwd=ROOT),"immutable own manifest")
    manifest=host.f.decode(raw)
    require(manifest["schema"]=="bulk-diode-name-audit-pins-v1"and manifest["native_CAD_authorized"]is False,"read-only source scope")
    for path,pin in manifest["files"].items():
        require(host.f.file_digest(host.c.secure_file(ROOT,path))==pin,"own source pin: "+path)
    host.source_gate()
    require(ijson.__version__=="3.4.0"and sys.version_info[:2]==(3,12),"qualified streaming runtime")
    return ctx,host.f.decode((ROOT/CONFIG).read_bytes())
def census(stream):
    names=[];seen=set();selected={}
    for name,row in ijson.kvitems(stream,"instances"):
        require(isinstance(name,str)and name and name not in seen,"duplicate/invalid instance name")
        require(isinstance(row,dict),"instance row type")
        seen.add(name);names.append(name)
        if name.startswith("ANTENNA_"):
            selected[name]={k:row[k]for k in("master","master_type","status")}
    require(names,"no instance object")
    return sorted(names),selected
def allocator(names):
    require(isinstance(names,list)and all(isinstance(n,str)and n for n in names),"name list")
    require(len(names)==len(set(names)),"duplicate allocator name")
    occupied=set(names);first=1
    while "ANTENNA_"+str(first)in occupied:first+=1
    canonical=sorted(int(m[1])for n in names if (m:=re.fullmatch(r"ANTENNA_([1-9][0-9]*)",n)))
    later=[n for n in canonical if n>first]
    collision=later[0]if later else None
    return dict(first_unused_index=first,first_unused_name="ANTENNA_"+str(first),
      first_later_occupied_index=collision,first_later_occupied_name=None if collision is None else "ANTENNA_"+str(collision),
      consecutive_insertions_before_possible_collision=None if collision is None else collision-first,
      existing_canonical_antenna_count=len(canonical),highest_existing_index=max(canonical,default=0),
      legacy_allocator_has_collision_risk=collision is not None,
      interpretation="Exact legacy naming algorithm only. A later collision requires enough insertion calls; the actual failing attempted name is not yet observed.")
def controls():
    rows=[]
    cases=[
      ("dense",["ANTENNA_1","ANTENNA_2","ANTENNA_3"],4,None),
      ("gap",["ANTENNA_1","ANTENNA_3"],2,3),
      ("leading_gap",["ANTENNA_5"],1,5),
      ("empty_namespace",["ordinary"],1,None),
      ("leading_zero_is_distinct",["ANTENNA_01","ANTENNA_5"],1,5),
      ("non_numeric",["ANTENNA_X","ANTENNA_0"],1,None),
      ("multiple_gaps",["ANTENNA_1","ANTENNA_4","ANTENNA_7"],2,4)]
    for label,names,first,later in cases:
        result=allocator(names)
        require((result["first_unused_index"],result["first_later_occupied_index"])==(first,later),"analytic allocation case "+label)
        require(result==allocator(list(reversed(names))),"input order independent")
        rows.append(dict(label=label,result=result,passed=True))
    for names in (["ANTENNA_1","ANTENNA_1"],[""],[1]):
        try:allocator(names)
        except AssertionError:rows.append(dict(label="invalid names refused",input=names,passed=True))
        else:raise AssertionError("invalid allocator names accepted")
    fixture=dict(instances={"ordinary":{},"ANTENNA_1":dict(master=["lib","diode"],master_type="CORE_ANTENNACELL",status="PLACED")},other={"deep":[{"skip":1}]*30})
    names,selected=census(io.BytesIO(encode(fixture)))
    require(names==["ANTENNA_1","ordinary"]and list(selected)==["ANTENNA_1"],"actual streaming projection")
    rows.append(dict(label="actual streaming projection",passed=True))
    for raw in (b'{"instances":{"x":{},"x":{}}}',b'{"instances":{"x":{}}} trailing',b'{"instances":{"x":{}}',b'{"instances":{}}'):
        try:census(io.BytesIO(raw))
        except (AssertionError,ijson.JSONError):rows.append(dict(label="malformed snapshot refused",raw=raw.decode(),passed=True))
        else:raise AssertionError("malformed snapshot accepted")
    require(len(rows)==15,"full source control census")
    return dict(status="PASS_BULK_DIODE_NAME_AUDIT_SOURCE_CONTROLS",count=len(rows),rows=rows,**FLAGS)
def actual(ctx,cfg,out,work,proof,control):
    require(cfg["readback_authorized"]is True,"readback disabled")
    require(control["status"]=="PASS_BULK_DIODE_NAME_AUDIT_SOURCE_CONTROLS"and control["count"]==15 and control["context"]==ctx,"same-source controls")
    require(not out.exists()and not work.exists(),"owned paths new")
    out.mkdir(parents=True);work.mkdir(mode=0o700)
    (work/"owner.json").write_bytes(host.f.encode(ctx))
    data=out/"bulk-postdrt-name-audit";data.mkdir()
    publication=work/"publication";publication.mkdir()
    primary=None;publication_error=None;report=dict(status="RUNNING",context=ctx,**FLAGS)
    try:
        reserved=host.reservation(ctx,proof,host.f.api("releases/"+str(proof["release_id"])),host.f.api("git/ref/tags/"+proof["tag"]))
        write(data/"reservation.json",reserved);write(data/"source-controls.json",control)
        producer=cfg["producer"]
        run=host.f.api("actions/runs/"+str(producer["run"]))
        jobs=host.f.api("actions/runs/"+str(producer["run"])+"/attempts/1/jobs?per_page=100")
        info=host.f.api("releases/"+str(producer["release"]))
        ref=host.f.api("git/ref/tags/"+producer["tag"])
        require(run["workflow_id"]==401215446 and run["head_branch"]==host.BRANCH and run["event"]=="workflow_dispatch","producer workflow context")
        require(jobs["total_count"]==len(jobs["jobs"])==4,"complete producer job count")
        require(run["id"]==producer["run"]and run["head_sha"]==producer["source"]and run["run_attempt"]==1 and run["status"]=="completed"and run["conclusion"]=="failure","failed producer binding")
        require([{k:j[k]for k in("id","name","status","conclusion")}for j in jobs["jobs"]]==cfg["jobs"],"full producer jobs")
        require(all(j["head_sha"]==producer["source"]and j["run_id"]==producer["run"]for j in jobs["jobs"]),"producer job source")
        assets=host.f.release_binding(info,ref,producer["tag"],producer["source"])
        require(info["id"]==producer["release"]and set(assets)==set(cfg["assets"]),"producer asset census")
        for name,pin in cfg["assets"].items():
            a=assets[name];require(a["id"]==pin["id"]and a["size"]==pin["bytes"]and a["digest"]=="sha256:"+pin["sha256"]and a["state"]=="uploaded","live asset "+name)
        for name,value in (("producer-run.json",run),("producer-jobs.json",jobs),("producer-release.json",info),("producer-ref.json",ref)):
            write(data/name,value)
        require(shutil.disk_usage(work).free>=3*1024**3,"runner disk before archive")
        transport=work/"transport";transport.mkdir()
        fn=archive_reader.download
        download=types.FunctionType(fn.__code__,dict(fn.__globals__,ASSETS=cfg["assets"]),fn.__name__,fn.__defaults__,fn.__closure__)
        paths={name:download(name,transport,data)for name in cfg["assets"]}
        outputs=host.f.decode(paths["candidate-outputs.json"].read_bytes())
        parts=host.f.decode(paths["candidate-parts.json"].read_bytes())
        require(outputs==cfg["outputs"]and parts==cfg["parts"],"exact authenticated metadata")
        require(len(parts["parts"])==1 and parts["parts"][0]["name"]=="candidate-native.tar.gz.part000","single exact existing part")
        require(parts["archive"]=={k:cfg["assets"]["candidate-native.tar.gz.part000"][k]for k in("bytes","sha256")},"whole input archive")
        selected=transport/"selected";member=cfg["snapshot_member"]
        complete=archive_reader.restore(paths["candidate-native.tar.gz.part000"],outputs["files"],{member},selected)
        require(len(complete)==48,"complete failed-output census")
        write(data/"complete-input-census.json",complete)
        snapshot=selected/member
        with snapshot.open("rb")as stream:names,antenna=census(stream)
        require(len(names)==153129,"actual original instance census")
        write(data/"all-instance-names.json",names)
        write(data/"all-antenna-prefixed-instances.json",antenna)
        result=allocator(names);write(data/"legacy-allocation-diagnosis.json",result)
        require(host.f.file_digest(snapshot)==outputs["files"][member],"snapshot unchanged")
        report.update(status="PASS_AUTHENTIC_CURRENT_INSTANCE_NAME_AUDIT",instance_count=len(names),antenna_prefixed_count=len(antenna),
          snapshot_pin=outputs["files"][member],diagnosis=result,all_48_input_members_authenticated=True,
          native_input_acquired_on_GitHub_only=True,original_failed_repair_preserved=True)
        guard()
    except BaseException as exc:
        primary=exc;report.update(status="FAIL_CURRENT_INSTANCE_NAME_AUDIT",error=repr(exc),traceback=traceback.format_exc())
    finally:
        write(data/"result.json",report)
        try:host.publish_capsule(ctx,proof,work,out,publication)
        except BaseException as exc:
            publication_error=exc
            write(publication/"publication-failure.json",dict(error=repr(exc),traceback=traceback.format_exc(),**FLAGS))
        # Publication receipts/empty streams are retained independently of the archive they describe.
        retained=out/"publication";retained.mkdir()
        for path in publication.iterdir():
            require(path.is_file()and not path.is_symlink(),"publication record type")
            shutil.copyfile(path,retained/path.name)
        host.emit(out)
    if primary is not None:raise primary
    if publication_error is not None:raise publication_error
    return report
def main():
    p=argparse.ArgumentParser()
    mode=p.add_mutually_exclusive_group(required=True);mode.add_argument("--controls",action="store_true");mode.add_argument("--readback",action="store_true")
    p.add_argument("--output",type=Path,required=True);p.add_argument("--work",type=Path);p.add_argument("--reservation",type=Path);p.add_argument("--controls-proof",type=Path)
    args=p.parse_args();ctx,cfg=guard()
    if args.controls:
        try:value=dict(controls(),context=ctx)
        except BaseException as exc:
            args.output.parent.mkdir(parents=True,exist_ok=True)
            value=dict(status="FAIL_BULK_DIODE_NAME_AUDIT_SOURCE_CONTROLS",error=repr(exc),traceback=traceback.format_exc(),context=ctx,**FLAGS)
            write(args.output,value);print(encode(value).decode(),end="");raise
        args.output.parent.mkdir(parents=True,exist_ok=True);write(args.output,value);print(encode(value).decode(),end="")
    else:
        require(args.work is not None and args.reservation is not None and args.controls_proof is not None,"readback arguments")
        actual(ctx,cfg,args.output,args.work,host.f.decode(args.reservation.read_bytes()),host.f.decode(args.controls_proof.read_bytes()))
if __name__=="__main__":main()
