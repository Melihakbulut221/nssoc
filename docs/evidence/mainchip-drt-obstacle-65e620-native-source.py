#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0
"""Observe endpoint wire/pin obstacles in the exact saved preroute ODB, read-only."""
import hashlib,json,os,sys
from pathlib import Path
sys.path.insert(0,"/work/tail-source/scripts")
import odb
import mainchip_drt_obstacle_contract as k
import mainchip_original_clock_restoration_native as original
import mainchip_two_signal_ownership_native as geom
import mainchip_bulk_postdrt_antenna as old
q=k.q
ROOT=Path("/work/tail-source")
INPUTS=Path("/work/obstacle-inputs")
OUT=Path("/work/out/obstacle-native")
ODB_MEMBER="work/bulk-postdrt-antenna/stale-wire-cleared.odb"
REPORT_MEMBER="work/bulk-postdrt-antenna/fixed-routing.drc-10.rpt"
PLAN_MEMBER="bulk-postdrt-antenna/insertion-plan.json"
MUTATION_MEMBER="bulk-postdrt-antenna/stale-wire-mutation.json"
def record(name,value):
    target=OUT/name;tmp=target.with_name(target.name+".partial")
    tmp.write_bytes(q.encode(value));tmp.replace(target)
def all_pin_geometry(t):
    """Reconcile actual ITerm geometry against every transformed decomposed MPin box."""
    actual=[(layer.getName(),geom.box(rect))for layer,rect in t.getGeometries()]
    transform=t.getInst().getTransform();expected=[]
    for mpin in t.getMTerm().getMPins():
        for box in mpin.getGeometry():
            q.require(not box.isVia(),"MPin via requires separate qualified transformation")
            expected.append((box.getTechLayer().getName(),geom.placed_box(transform,box)))
    q.require(sorted(actual)==sorted(expected),"complete transformed MPin/ITerm geometry equality")
    return actual
def native_scope(db,block,scope,owners,plan,progress):
    q.require(not list(block.getChildren()),"no hidden child blocks")
    all_nets=list(block.getNets());all_instances=list(block.getInsts())
    k.census([n.getName()for n in all_nets],[i.getName()for i in all_instances],plan["added_instances"],plan["attachments"])
    q.require(db.getTech().getDbUnitsPerMicron()==block.getDbUnitsPerMicron()==scope["dbu"],"native DBU binding")
    mutable,protected,attachments=owners
    actual_new={i.getName():i for i in all_instances if i.getName().startswith("NSSOC_BULK_NEW_")}
    q.require(set(actual_new)==set(plan["added_instances"])==set(attachments)and len(actual_new)==1351,"complete added diode census")
    for name,inst in actual_new.items():
        q.require(inst.getMaster().getName()==old.DIODE,"exact qualified diode master")
        a=inst.findITerm("A")
        q.require(a is not None and a.getNet()is not None and a.getNet().getName()==attachments[name],"actual added diode A connection")
    proof=geom.api_evidence();layers=geom.named_layers(db.getTech(),proof)
    markers=scope["markers"];by_net={}
    for m in markers:
        for name in m["nets"]:by_net.setdefault(name,[]).append(m)
    observed={};seen_iterms={};seen_bterms={};witnesses={str(m["ordinal"]):[]for m in markers}
    for name in scope["endpoint_names"]:
        net=block.findNet(name);q.require(net is not None and net.getName()==name,"exact endpoint net lookup")
        identity=original.identity(db,net);encoded=original.encoded(net)
        if name in mutable:
            q.require(encoded==dict(wire_present=False,metadata="ROUTED",paths=[]),"selected mutable wire was cleared; iteration10 routes absent")
        stats={};digest=hashlib.sha256();pins=[];records=0
        def feed(row,is_pin=False):
            nonlocal records
            q.require(row["owner"]==name and type(row["layer"])is str,"native shape identity")
            row["box"]=k.rectangle(row["box"])
            raw=q.encode(row);digest.update(len(raw).to_bytes(8,"big"));digest.update(raw)
            records+=1;stats[row["kind"]]=stats.get(row["kind"],0)+1
            if is_pin:pins.append(row)
            for marker in by_net[name]:
                found=k.witness(marker,row,allow_cross_layer_pin=is_pin)
                if found is not None:witnesses[str(marker["ordinal"])].append(found)
        wire=net.getWire();wire_pin=None;wire_projection_pin=None
        if wire is not None:
            projection=geom.native_wire(db,block,wire,layers,proof)
            wire_pin=k.source_pin(projection["raw"]);wire_projection_pin=k.source_pin(projection)
            for i,shape in enumerate(projection["shapes"]):
                feed(dict(shape,owner=name,record_id=["net",name,"wire","shape",i],route_metadata=encoded["metadata"],encoded_classes=encoded["paths"]))
        for t in net.getITerms():
            inst=t.getInst();terminal=t.getMTerm().getName()
            q.require(t.getNet()is not None and t.getNet().getName()==name,"actual ITerm connection")
            key=(inst.getName(),terminal);q.require(key not in seen_iterms,"unique connected endpoint ITerm")
            seen_iterms[key]=name
            for i,(layer,rect)in enumerate(all_pin_geometry(t)):
                feed(dict(owner=name,record_id=["iterm",inst.getName(),terminal,"geometry",i],
                  kind="iterm-pin",layer=layer,box=rect,instance=inst.getName(),
                  terminal=terminal,master=[inst.getMaster().getLib().getName(),inst.getMaster().getName()],
                  added_diode=inst.getName()in actual_new),is_pin=True)
        for t in net.getBTerms():
            q.require(t.getNet()is not None and t.getNet().getName()==name,"actual BTerm connection")
            q.require(t.getName()not in seen_bterms,"unique connected endpoint BTerm");seen_bterms[t.getName()]=name
            for pi,pin in enumerate(t.getBPins()):
                for i,b in enumerate(pin.getBoxes()):
                    q.require(not b.isVia(),"BPin via requires separate qualification")
                    feed(dict(owner=name,record_id=["bterm",t.getName(),"bpin",pi,"box",i],
                      kind="bterm-pin",layer=b.getTechLayer().getName(),box=geom.box(b),terminal=t.getName()),is_pin=True)
        for si,swire in enumerate(net.getSWires()):
            for i,b in enumerate(swire.getWires()):
                rid=["net",name,"swire",si,"box",i]
                if b.isVia():
                    tech=b.getTechVia();via=tech if tech is not None else b.getBlockVia()
                    q.require(via is not None,"actual special via")
                    v=geom.via_record(via,layers);xy=list(b.getViaXY())
                    q.require(len(xy)==2 and all(type(x)is int for x in xy),"native via origin")
                    for ci,part in enumerate(v["components"]):
                        r=part["box"]
                        feed(dict(owner=name,record_id=[*rid,"component",ci],kind="special-via",
                          layer=part["layer"],box=[r[0]+xy[0],r[1]+xy[1],r[2]+xy[0],r[3]+xy[1]],
                          via=v,origin_xy=xy,via_namespace="tech"if tech is not None else"block"))
                else:feed(dict(owner=name,record_id=rid,kind="special-wire",layer=b.getTechLayer().getName(),box=geom.box(b)))
        observed[name]=dict(identity=identity,encoded=encoded,wire_raw_pin=wire_pin,
          wire_projection_pin=wire_projection_pin,native_geometry_records=records,native_geometry_counts=stats,
          native_geometry_sha256=digest.hexdigest(),all_endpoint_pin_geometry=pins,
          manifest_membership="mutable_cleared_manifest"if name in mutable else"protected_manifest"if name in protected else"not_in_either_manifest")
        progress(dict(stage="native-endpoint-census",complete=False,observed_endpoint_names=sorted(observed),required_endpoint_names=scope["endpoint_names"],**k.FLAGS))
    endpoint_set=set(scope["endpoint_names"])
    expected_iterms={(t.getInst().getName(),t.getMTerm().getName()):t.getNet().getName()for t in block.getITerms()if t.getNet()is not None and t.getNet().getName()in endpoint_set}
    expected_bterms={t.getName():t.getNet().getName()for t in block.getBTerms()if t.getNet()is not None and t.getNet().getName()in endpoint_set}
    q.require(seen_iterms==expected_iterms and seen_bterms==expected_bterms,"independent block connected endpoint terminal census")
    q.require(set(observed)==set(scope["endpoint_names"])and set(witnesses)=={str(m["ordinal"])for m in markers},"complete scoped observation")
    return dict(status="COMPLETE_PREROUTE_ENDPOINT_OBSTACLE_OBSERVATION",markers=[dict(m,endpoint_witnesses=witnesses[str(m["ordinal"])])for m in markers],
      other_markers=scope["other_markers"],endpoint_nets=observed,all_net_count=len(all_nets),all_instance_count=len(all_instances),
      actual_added_diode_A_connections=len(actual_new),dbu_per_micron=scope["dbu"],
      complete_selected_marker_count=len(markers),complete_endpoint_net_count=len(observed),
      native_api_evidence_sha256=geom.API_SHA,
      scope="All selected endpoint ordinary raw-wire boxes/via components, special wires/vias and every transformed connected endpoint ITerm/BTerm pin. Third-party nets, fill and obstructions are not a full physical ownership census.",
      interpretation="Iteration10 mutable routing is absent from this preroute ODB. Endpoint intersections are candidate obstacle evidence, not a root cause or irreparability proof.",
      native_tools_executed=True,read_only=True,**k.FLAGS)
def main():
    k.native_authorization(ROOT)
    q.require(not any(x in os.environ for x in("GH_TOKEN","GITHUB_TOKEN")),"credential-free native process")
    config=q.decode((ROOT/"scripts/mainchip-drt-obstacle-readback-inputs.json").read_bytes())
    k.validate_config(config);q.require(config["native_readonly_authorized"]is True,"configured native observation disabled")
    q.require(not OUT.exists(),"exclusive native outputs");OUT.mkdir(parents=True)
    result=dict(status="IN_PROGRESS",**k.FLAGS);db=None;primary=None;terminal_errors=[]
    source=INPUTS/ODB_MEMBER
    try:
        for name,pin in config["selected_members"].items():
            q.require(q.pin(INPUTS/name)==pin,"authenticated native input "+name)
        q.require(q.pin(source)==k.INPUT_ODB,"exact stale-wire-cleared input")
        q.require(q.pin(INPUTS/"hosted-analysis.json")==config["analysis_result"]["pin"],"qualified hosted text analysis bytes")
        plan=q.decode((INPUTS/PLAN_MEMBER).read_bytes());mutation=q.decode((INPUTS/MUTATION_MEMBER).read_bytes())
        analysis=q.decode((INPUTS/"hosted-analysis.json").read_bytes())
        q.require(analysis["source"]=="7ecad63b24ed156a42f7bd1cda24c3326667444a"and analysis["run"]==41232959125,"qualified text analysis source/run")
        db,block=original.load(source)
        scope,owners=k.scope((INPUTS/REPORT_MEMBER).read_bytes(),plan,mutation,analysis,block.getDbUnitsPerMicron(),596,434)
        record("scope.json",dict(scope,**k.FLAGS))
        result=native_scope(db,block,scope,owners,plan,lambda row:record("progress.json",row))
    except BaseException as exc:
        primary=exc;result.update(status="FAIL_PREROUTE_ENDPOINT_OBSTACLE_OBSERVATION",error=repr(exc))
    finally:
        def attempt(label,fn):
            try:fn()
            except BaseException as exc:terminal_errors.append(dict(stage=label,error=repr(exc)))
        if db is not None:attempt("destroy-read-only-database",lambda:odb.dbDatabase.destroy(db))
        def unchanged():
            result["input_odb_unchanged"]=q.pin(source)==k.INPUT_ODB
            q.require(result["input_odb_unchanged"],"input database changed")
        attempt("input-unchanged",unchanged)
        result["terminal_errors"]=terminal_errors
        if primary is not None or terminal_errors:result["status"]="FAIL_PREROUTE_ENDPOINT_OBSTACLE_OBSERVATION"
        try:record("result.json",result)
        except BaseException:
            if primary is None:raise
    if primary is not None:raise primary
    q.require(not terminal_errors,"native terminal failures")
if __name__=="__main__":main()
