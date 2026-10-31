#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0
"""Exact-source cloud-only native connectivity readback of the preserved routed chip."""
import argparse,hashlib,json,os,shutil,subprocess,sys,traceback,types
from pathlib import Path
import cloud_mainchip_saved_route_diagnosis as saved
import cloud_mainchip_fixed_engine_route_tail as tail
import mainchip_fixed_engine_route_tail_contract as c
import mainchip_witness_engine_build as build
ROOT=Path(__file__).resolve().parents[1]
MANIFEST="scripts/mainchip-saved-route-connectivity-pins.json"
GROUP="mainchip-saved-route-connectivity"
CANDIDATE="work/bulk-postdrt-antenna/candidate.odb"
PLAN="bulk-postdrt-antenna/insertion-plan.json"
SELECTED={CANDIDATE,PLAN}
FLAGS=dict(physical_acceptance=False,timing_accepted=False,full_phy_accepted=False,geometry_modified=False)
require=saved.require
pin=saved.pin
save=saved.save
def source_guard(root=ROOT):
    p=root/MANIFEST;require(not p.is_symlink()and p.is_file(),"source manifest")
    m=json.loads(p.read_bytes())
    require(m["schema"]=="mainchip-saved-route-connectivity-pins-v1"and m["native_readback_authorized"]is True,"only native readback")
    require(m["routing_authorized"]is False and all(m[k]is False for k in FLAGS),"no geometry or acceptance authority")
    for name,digest in m["files"].items():
        require(not Path(name).is_absolute()and ".."not in Path(name).parts,"source member")
        path=root/name;require(path.is_file()and not path.is_symlink()and pin(path)["sha256"]==digest,"source pin "+name)
    return m
def bind_function(fn,**bindings):
    require(set(bindings)<=set(fn.__globals__),"known immutable function bindings")
    return types.FunctionType(fn.__code__,{**fn.__globals__,**bindings},fn.__name__,fn.__defaults__,fn.__closure__)
def copy_projection(work,method):
    dest=work/"tail-source";dest.mkdir(exist_ok=False)
    for name in [*method["files"],MANIFEST]:
        src=ROOT/name;target=dest/name;target.parent.mkdir(parents=True,exist_ok=True);shutil.copyfile(src,target)
        require(pin(target)==pin(src),"projection bytes")
    source_guard(dest);c.method(dest)
    shutil.copyfile(ROOT/"scripts/mainchip_saved_route_connectivity_inner.py",work/"inner.py")
    require(pin(work/"inner.py")==pin(ROOT/"scripts/mainchip_saved_route_connectivity_inner.py"),"exact native entry")
def preserve(work,out,evidence,frozen):
    target=evidence/"native";target.mkdir(exist_ok=False)
    frozen_files={}if frozen is None else frozen["files"]
    records={};skipped={}
    for path in sorted(out.rglob("*")):
        require(not path.is_symlink(),"native output symlink")
        if not path.is_file():continue
        name=str(path.relative_to(out));source_member="out/"+name;actual=pin(path)
        if source_member in frozen_files and actual=={k:frozen_files[source_member][k]for k in("bytes","sha256")}:
            skipped[name]=actual;continue
        dest=target/name;dest.parent.mkdir(parents=True,exist_ok=True);shutil.copyfile(path,dest)
        require(pin(dest)==actual,"all actual available output bytes")
        records[name]=actual
    proof=dict(files=records,unchanged_inherited_prefix_files_not_duplicated=skipped,
      every_available_new_or_changed_native_output_preserved=True,native_payload_locally_acquired=False)
    save(evidence/"native-output-preservation.json",proof)
    return proof
def cleanup(ctx,work,result,command,identity):
    # Recover only our labeled container, including an interrupted create response.
    inspected=subprocess.run(["docker","inspect",ctx["name"]],capture_output=True)
    if inspected.returncode:
        names=subprocess.check_output(["docker","container","ls","-a","--format","{{.Names}}"],text=True)
        require(ctx["name"]not in names.splitlines(),"owned container cannot be inspected")
        return dict(absent=True)
    observed=json.loads(inspected.stdout)[0];c.validate_container(observed,ctx,work)
    if identity is not None:require(observed["Id"]==identity,"same owned container")
    identity=observed["Id"];save(work/"out/container-before-cleanup.json",observed)
    errors=[]
    if observed["State"]["Running"]:
        try:command("owned-stop",["docker","stop","--time","10",identity],45)
        except BaseException as exc:errors.append(repr(exc))
        observed=json.loads(subprocess.check_output(["docker","inspect",identity]))[0]
        c.validate_container(observed,ctx,work)
        if observed["State"]["Running"]:command("owned-kill",["docker","kill",identity],45)
        observed=json.loads(subprocess.check_output(["docker","inspect",identity]))[0]
    c.validate_container(observed,ctx,work,require_stopped=True)
    save(work/"out/container-terminal.json",observed)
    command("owned-remove",["docker","rm",identity],120)
    names=subprocess.check_output(["docker","container","ls","-a","--format","{{.Names}}"],text=True)
    require(ctx["name"]not in names.splitlines(),"owned container removed")
    require(not errors,"container cleanup retained errors "+repr(errors))
    return dict(absent=True,owned_container_removed=True,terminal_state=observed["State"])
def main():
    ap=argparse.ArgumentParser();ap.add_argument("--output",type=Path,required=True);args=ap.parse_args()
    evidence=args.output;evidence.mkdir(parents=True,exist_ok=False)
    result=dict(status="IN_PROGRESS",commands=[],terminal_errors=[],**FLAGS)
    work=None;out=None;frozen=None;identity=None;ctx=None;primary=None
    try:
        current=saved.context();method=source_guard();c.method(ROOT)
        ctx=dict(source=current["source"],run_id=current["run"],attempt=1,token=str(current["run"])+"-1",
          name="nssoc-witness-build-"+str(current["run"])+"-1",group=GROUP)
        result["context"]=current;save(evidence/"context.json",current)
        reserved=bind_function(saved.reservation,GROUP=GROUP)(current)
        result["reservation"]=reserved;save(evidence/"reservation.json",reserved)
        index,parts,release=saved.metadata();live=saved.live_producer(release);save(evidence/"live-producer.json",live)
        work=Path(os.environ["RUNNER_TEMP"])/(GROUP+"-"+ctx["token"]);work.mkdir(exist_ok=False)
        save(work/"owner.json",ctx);out=work/"out";out.mkdir()
        require(shutil.disk_usage(work).free>=24*1024**3,"full native/runtime preservation disk budget")
        selected=bind_function(saved.acquire,SELECTED=SELECTED)(index,parts,live,work,evidence)
        require(selected==work/"selected","native input namespace")
        request=dict(context=current,producer=saved.PRODUCER,producer_source=saved.SOURCE,
          candidate=index["files"][CANDIDATE],plan=index["files"][PLAN],unchanged_original_engine=c.ENGINE,
          native_readback_only=True,**FLAGS)
        save(work/"connectivity-request.json",request);save(evidence/"request.json",request)
        frozen=tail.restore_prefix(work,out)
        copy_projection(work,method)
        command=lambda label,argv,timeout=120:build.execute_command(result,out,label,argv,timeout)
        command("immutable-image-pull",["docker","pull",c.IMAGE],1800)
        c.validate_image(json.loads(command("image-inspect",["docker","image","inspect",c.IMAGE]))[0])
        identity=build.create_owned(ctx,work,result,command,c.create_argv(ctx,work,os.getuid(),os.getgid()))
        c.validate_container(json.loads(subprocess.check_output(["docker","inspect",identity]))[0],ctx,work)
        command("native-connectivity",["docker","start","--attach",identity],1800)
        actual=json.loads((out/"connectivity-inner-result.json").read_bytes())
        require(actual["status"]=="COMPLETE_SAVED_ROUTE_CONNECTIVITY_ENGINE"and actual["native_complete"]is True,"native observation completed")
        result["native_summary"]=actual["native_summary"]
        result["native_complete"]=True
    except BaseException as exc:primary=exc;result.update(error=repr(exc),traceback=traceback.format_exc())
    finally:
        def attempt(label,fn):
            try:
                v=fn();result.setdefault("terminal_actions",[]).append(dict(action=label,complete=True))
                if v is not None:result.setdefault("terminal_evidence",{})[label]=v
            except BaseException as exc:result["terminal_errors"].append(dict(action=label,error=repr(exc),traceback=traceback.format_exc()))
        if work is not None and out is not None:
            if result.get("creation_attempted"):
                attempt("owned-container-cleanup",lambda:cleanup(ctx,work,result,command,identity))
            if frozen is not None:attempt("frozen-runtime-unchanged",lambda:c.frozen_unchanged(work,frozen))
            if (work/"selected").is_dir():
                def unchanged():
                    index,_,_=saved.metadata()
                    require(all(pin(work/"selected"/n)==index["files"][n]for n in SELECTED),"all native inputs unchanged")
                    return dict(all_selected_input_files_unchanged=True)
                attempt("selected-inputs-unchanged",unchanged)
            attempt("preserve-all-available-native-output",lambda:preserve(work,out,evidence,frozen))
        attempt("protected-source-unchanged",lambda:dict(protected_files=len(source_guard()["files"])))
        result["status"]="COMPLETE_CLOUD_NATIVE_CONNECTIVITY_DIAGNOSIS"if primary is None and not result["terminal_errors"]and result.get("native_complete")else"FAIL_CLOUD_NATIVE_CONNECTIVITY_DIAGNOSIS"
        result["outputs"]={str(p.relative_to(evidence)):pin(p)for p in evidence.rglob("*")if p.is_file()}
        save(evidence/"result.json",result)
        print("CLOUD_NATIVE_CONNECTIVITY_RESULT "+json.dumps({k:v for k,v in result.items()if k not in("outputs","terminal_evidence")},sort_keys=True),flush=True)
    if primary:raise primary
    require(result["status"]=="COMPLETE_CLOUD_NATIVE_CONNECTIVITY_DIAGNOSIS","readback finalization failed")
if __name__=="__main__":main()
