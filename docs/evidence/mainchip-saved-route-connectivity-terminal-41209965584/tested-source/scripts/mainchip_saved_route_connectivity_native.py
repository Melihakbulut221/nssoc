#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0
"""Read every admitted diode A pin and its complete wire directly from the saved ODB."""
import hashlib,json,os,sys,traceback
from pathlib import Path
sys.path.insert(0,"/work/tail-source/scripts")
import odb
import mainchip_bulk_postdrt_antenna_native as native
import mainchip_net459_connectivity as graph
from cloud_mainchip_saved_route_connectivity import source_guard,FLAGS
ROOT=Path("/work")
OUT=ROOT/"out/connectivity"
def pin(path):
    with path.open("rb")as f:return dict(bytes=path.stat().st_size,sha256=hashlib.file_digest(f,"sha256").hexdigest())
def save(path,value):path.write_text(json.dumps(value,sort_keys=True,indent=2,allow_nan=False)+"\n")
def require(v,msg):
    if not v:raise AssertionError(msg)
def observe(db,block,name,added,layers,api):
    net=block.findNet(name)
    require(net is not None and net.getWire()is not None and not net.isSpecial()and not list(net.getSWires()),"ordinary existing signal wire")
    require(str(net.getSigType())=="SIGNAL"and str(net.getWireType())=="ROUTED","actual routed signal metadata")
    require(not list(net.getBTerms()),"BTerm topology requires explicit complete native geometry support")
    projection=native.own.native_wire(db,block,net.getWire(),layers,api);pins=[]
    for term in net.getITerms():
        inst=term.getInst()
        pins.append(dict(kind="iterm",scoped_identity=["iterm",inst.getName(),term.getMTerm().getName()],
          geometries=[[layer.getName(),native.own.box(rect)]for layer,rect in term.getGeometries()]))
    ids={tuple(p["scoped_identity"])for p in pins}
    require(len(ids)==len(pins)and all(("iterm",i,"A")in ids for i in added),"every admitted diode A physically observed")
    modes={}
    for mode in("positive_area","closed_boundary"):
        modes[mode]=graph.observe(projection["shapes"],pins,mode)
    return dict(net=name,added_diodes=added,identity=native.n.identity(db,net),
      encoded=native.n.encoded(net),projection=projection,modes=modes,**FLAGS)
def main():
    require(not any(k in os.environ for k in("GH_TOKEN","GITHUB_TOKEN")),"credential-free native")
    source_guard(Path("/work/tail-source"))
    request=json.loads((ROOT/"connectivity-request.json").read_bytes())
    path=ROOT/"selected/work/bulk-postdrt-antenna/candidate.odb"
    pp=ROOT/"selected/bulk-postdrt-antenna/insertion-plan.json"
    require(pin(path)==request["candidate"]and pin(pp)==request["plan"],"exact acquired current input")
    plan=json.loads(pp.read_bytes())
    require(len(plan["mutable_nets"])==608 and len(plan["attachments"])==1351 and len(plan["protected_nets"])==1691,"complete scope")
    require(set(plan["mutable_nets"])==set(plan["attachments"].values())and set(plan["added_instances"])==set(plan["attachments"]),"exact diode ownership")
    require(not(set(plan["mutable_nets"])&set(plan["protected_nets"])),"no protected-net ownership")
    OUT.mkdir(exist_ok=False)
    result=dict(status="IN_PROGRESS",request=request,records={},errors=[],native_readback_executed=True,
      all608_observed=False,physical_connectivity_qualified=False,**FLAGS)
    db=None;primary=None
    try:
        db,block=native.n.load(path)
        result["census"]=dict(instances=len(list(block.getInsts())),nets=len(list(block.getNets())))
        require(result["census"]==dict(instances=154480,nets=143820),"actual whole-chip census")
        require(sorted(native.n.selected(block))==sorted(plan["protected_nets"]),"all1691 current protected nets")
        api=native.own.api_evidence();layers=native.own.named_layers(db.getTech(),api)
        save(OUT/"native-api.json",api)
        for i,name in enumerate(sorted(plan["mutable_nets"])):
            added=sorted(inst for inst,net in plan["attachments"].items()if net==name)
            filename="net-"+hashlib.sha256(name.encode()).hexdigest()+".json"
            try:
                observation=observe(db,block,name,added,layers,api)
                save(OUT/filename,observation)
                summary={}
                for mode,row in observation["modes"].items():
                    added_rows=[p for p in row["pins"]if p["scoped_identity"][1]in added and p["scoped_identity"][2]=="A"]
                    require(len(added_rows)==len(added),"complete per-mode added A census")
                    summary[mode]=dict(all_pins_share_one_wire_component=row["all_pins_share_one_wire_component"],
                      all_wire_material_one_component=row["all_wire_material_one_component"],
                      no_wire_access=[p["scoped_identity"]for p in row["pins"]if p["no_wire_access"]],
                      added_diodes_without_access=[p["scoped_identity"][1]for p in added_rows if p["no_wire_access"]],
                      added_diodes_ambiguous=[p["scoped_identity"][1]for p in added_rows if p["ambiguous_multiple_wire_components"]],
                      wire_components=len(row["wire_components"]),pins=len(row["pins"]))
                result["records"][name]=dict(path=filename,pin=pin(OUT/filename),added_diodes=added,modes=summary)
            except BaseException as exc:
                failure=dict(net=name,added_diodes=added,error=repr(exc),traceback=traceback.format_exc())
                save(OUT/filename,failure);result["errors"].append(dict(**failure,path=filename,pin=pin(OUT/filename)))
            if (i+1)%25==0:
                save(OUT/"progress.json",dict(done=i+1,total=608,observed=len(result["records"]),errors=len(result["errors"])))
                print("NATIVE_CONNECTIVITY_PROGRESS "+json.dumps(dict(done=i+1,total=608,errors=len(result["errors"]))),flush=True)
        require(len(result["records"])+len(result["errors"])==608,"every owner has complete observation or explicit failure")
        result["all608_observed"]=len(result["records"])==608 and not result["errors"]
        result["mode_totals"]={}
        for mode in("positive_area","closed_boundary"):
            rows=[r["modes"][mode]for r in result["records"].values()]
            result["mode_totals"][mode]=dict(observed_nets=len(rows),
              connected_nets=sum(r["all_pins_share_one_wire_component"]and r["all_wire_material_one_component"]for r in rows),
              disconnected_nets=sum(not(r["all_pins_share_one_wire_component"]and r["all_wire_material_one_component"])for r in rows),
              added_diodes_without_access=sum(len(r["added_diodes_without_access"])for r in rows),
              added_diodes_ambiguous=sum(len(r["added_diodes_ambiguous"])for r in rows))
        result["physical_connectivity_qualified"]=result["all608_observed"]and all(
          r["connected_nets"]==608 for r in result["mode_totals"].values())
        result["status"]="COMPLETE_NATIVE_DIODE_CONNECTIVITY_OBSERVATION"if result["all608_observed"]else"INCOMPLETE_NATIVE_DIODE_CONNECTIVITY_OBSERVATION"
    except BaseException as exc:
        primary=exc;result.update(status="FAIL_NATIVE_DIODE_CONNECTIVITY_OBSERVATION",error=repr(exc),traceback=traceback.format_exc())
    finally:
        if db is not None:odb.dbDatabase.destroy(db)
        try:
            require(pin(path)==request["candidate"]and pin(pp)==request["plan"],"native input files unchanged")
            source_guard(Path("/work/tail-source"));result["source_and_input_unchanged"]=True
        except BaseException as exc:
            result.update(status="FAIL_NATIVE_INPUT_OR_SOURCE_INTEGRITY",integrity_error=repr(exc),source_and_input_unchanged=False)
            if primary is None:primary=exc
        save(OUT/"result.json",result)
        print("NATIVE_CONNECTIVITY_RESULT "+json.dumps({k:v for k,v in result.items()if k not in("records","errors")},sort_keys=True),flush=True)
    if primary:raise primary
    require(result["all608_observed"],"one or more native owners could not be completely observed")
if __name__=="__main__":main()
