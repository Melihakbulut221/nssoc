#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0
"""Native scoped guide continuation from the fully admitted saved diode ODB."""
import gc,json,os,shutil,sys
from pathlib import Path
sys.path.insert(0,"/work/tail-source/scripts")
import odb
import mainchip_bulk_postdrt_antenna as p
import mainchip_bulk_postdrt_antenna_native as native
import mainchip_saved_diode_routing as plan
from mainchip_saved_diode_reconstruction_native import native_pointer,same_native
from mainchip_bulk_postdrt_antenna_native import n,own
ROOT=Path("/work/reconstruction-inputs")
DONOR=Path("/work/failed-repair-inputs")
DATA=Path("/work/out/bulk-postdrt-antenna")
WORK=Path("/work/out/work/bulk-postdrt-antenna")
CURRENT=Path("/work/current-input.odb")
CANDIDATE=ROOT/"work/bulk-postdrt-antenna/reconstruction.odb"
GUIDED=WORK/"guide-overlay.odb"
def save(name,value):native.save(DATA/name,value)
def read(name):return json.loads((DATA/name).read_bytes())
def source_json(name):return json.loads((p.ROOT/plan.PROOF/name).read_bytes())
def verify_inputs():
    pins=source_json("capsule-metadata/candidate-outputs.json")["files"]
    for name in sorted(plan.RECONSTRUCTION_SELECTED):p.exact(native.fp(ROOT/name),pins[name],"saved reconstruction input "+name)
    pins=json.loads((p.ROOT/plan.DONOR_PROOF/"capsule-metadata/candidate-outputs.json").read_bytes())["files"]
    for name in sorted(plan.DONOR_SELECTED):p.exact(native.fp(DONOR/name),pins[name],"saved donor input "+name)
    p.exact(native.fp(CURRENT),p.INPUT,"unchanged original ODB")
def bootstrap():
    inner=json.loads((ROOT/"bulk-postdrt-inner-result.json").read_bytes())
    result=json.loads((ROOT/"bulk-postdrt-antenna/reconstruction-result.json").read_bytes())
    host=source_json("readable-records/result.json")
    save("route-producer-admission.json",plan.validate_saved_native(inner,result,host))
    copies={
      "bulk-postdrt-antenna/reconstruction-original-snapshot.json":DATA/"baseline-snapshot.json",
      "bulk-postdrt-antenna/reconstruction-candidate-snapshot.json":DATA/"insertion-snapshot.json",
      "bulk-postdrt-antenna/reconstruction-original-admission.json":DATA/"insertion-plan.json",
      "bulk-postdrt-antenna/reconstruction-plan.json":DATA/"saved-construction-plan.json",
      "work/bulk-postdrt-antenna/reconstruction-original.def":WORK/"baseline.def",
      "work/bulk-postdrt-antenna/reconstruction-candidate.def":WORK/"insertion.def",
      "work/bulk-postdrt-antenna/reconstruction.odb":WORK/"insertion-connected.odb"}
    for name,target in copies.items():
        p.require(not target.exists(),"new continuation target")
        shutil.copyfile(ROOT/name,target);p.exact(native.fp(target),native.fp(ROOT/name),"exact saved continuation copy")
    shutil.copyfile(DONOR/"bulk-postdrt-antenna/baseline-antenna-violations.json",DATA/"baseline-antenna-violations.json")

def guides(block,owners=None):
    rows={}
    nets=block.getNets()if owners is None else [block.findNet(x)for x in sorted(owners)]
    for net in nets:
        p.require(net is not None,"native guide owner exists");name=net.getName()
        p.require(name not in rows,"unique guide net name");out=[]
        for guide in net.getGuides():
            p.require(same_native(guide.getNet(),net),"same live native guide owner")
            props=list(odb.dbProperty.getProperties(guide))
            p.require(not props,"nonempty guide properties require separate complete copier")
            layer=guide.getLayer();via=guide.getViaLayer()
            p.require(layer is not None and via is not None,"complete native guide layers")
            row=dict(box=own.box(guide.getBox()),layer=layer.getName(),via_layer=via.getName(),
              congested=guide.isCongested(),jumper=guide.isJumper(),connected_to_term=guide.isConnectedToTerm(),properties=[])
            plan.validate_guide(row);out.append(row)
        rows[name]=out
    return rows
def read_guides(path,owners=None):
    db,block=n.load(path)
    try:return guides(block,owners)
    finally:odb.dbDatabase.destroy(db)
def guide_overlay():
    admission=read("insertion-plan.json");owners=admission["mutable_nets"];protected=admission["protected_nets"]
    before=read_guides(CURRENT)
    p.exact(read_guides(CANDIDATE),before,"reconstruction retained every original guide")
    save("guide-original.json",before)
    db,block=n.load(DONOR/"work/bulk-postdrt-antenna/insertion-after-shim.odb")
    try:
        construction=read("saved-construction-plan.json")
        for name,row in construction["rows"].items():
            inst=block.findInst(name);p.require(inst is not None,"authentic donor diode")
            term=inst.findITerm("A");p.require(term is not None and term.getNet()is not None,"authentic donor attachment")
            p.exact(term.getNet().getName(),row["pins"]["A"]["net"],"exact donor signal owner")
        donor=guides(block,owners)
    finally:odb.dbDatabase.destroy(db)
    expected,delta=plan.guide_overlay(before,donor,owners,protected)
    save("guide-donor.json",donor);save("guide-expected.json",expected);save("guide-delta.json",delta)
    del before,donor;gc.collect()
    db,block=n.load(CANDIDATE);report=dict(complete=False,mutated=[],**p.FLAGS)
    try:
        for name in delta["changed_owners"]:
            net=block.findNet(name);p.require(net is not None,"owned live net")
            net.clearGuides()
            for row in reversed(expected[name]):
                layer=db.getTech().findLayer(row["layer"]);via=db.getTech().findLayer(row["via_layer"])
                p.require(layer is not None and via is not None,"actual named guide layers")
                g=odb.dbGuide.create(net,layer,via,odb.Rect(*row["box"]),row["congested"])
                p.require(g is not None and same_native(g.getNet(),net),"created exact guide owner")
                g.setIsJumper(row["jumper"]);g.setIsConnectedToTerm(row["connected_to_term"])
            report["mutated"].append(name)
        p.exact(guides(block),expected,"all native guide fields order and multiplicity")
        odb.write_db(db,str(GUIDED));report.update(complete=True,candidate=native.fp(GUIDED))
    except BaseException as exc:
        report["error"]=repr(exc)
        try:
            target=WORK/"guide-overlay-unadmitted-partial.odb";odb.write_db(db,str(target));report["partial"]=native.fp(target)
        except BaseException as secondary:report["preservation_error"]=repr(secondary)
        raise
    finally:
        odb.dbDatabase.destroy(db);save("guide-overlay-construction.json",report)
def guide_reload_audit():
    expected=read("guide-expected.json")
    p.exact(read_guides(GUIDED),expected,"all guide fields survived native write/reload")
    del expected;gc.collect()
    snapshot=native.snapshot(GUIDED,WORK/"guide-reloaded.def")
    save("guide-reloaded-snapshot.json",snapshot);del snapshot;gc.collect()
    pins=source_json("capsule-metadata/candidate-outputs.json")["files"]
    p.exact(native.fp(DATA/"guide-reloaded-snapshot.json"),pins["bulk-postdrt-antenna/reconstruction-candidate-snapshot.json"],"all native physical material unchanged by guide overlay")
    p.exact(native.fp(WORK/"guide-reloaded.def"),pins["work/bulk-postdrt-antenna/reconstruction-candidate.def"],"exact original candidate DEF after guides")
    shutil.copyfile(GUIDED,WORK/"insertion-connected.odb")
    save("guide-reload-admission.json",dict(complete=True,full_guides_preserved=True,
      only_admitted_signal_guides_updated=True,all_physical_material_preserved=True,**p.FLAGS))

def power_contact_audit():
    """Direct positive-area metal contact, not global PG/LVS or voltage-drop signoff."""
    db,block=n.load(WORK/"insertion-connected.odb")
    result=dict(complete=False,scope="Each new diode PG terminal touches same-layer metal on its own existing special PG net.",
      full_pg_connectivity_accepted=False,lvs_accepted=False,contacts={},**p.FLAGS)
    try:
        construction=read("saved-construction-plan.json");indices={}
        for netname in sorted({pin["net"]for row in construction["rows"].values()for name,pin in row["pins"].items()if name!="A"}):
            net=block.findNet(netname);p.require(net is not None and str(net.getSigType())in("POWER","GROUND"),"PG owner")
            rows=[];index={}
            for si,swire in enumerate(net.getSWires()):
                for ordinal,b in enumerate(swire.getWires()):
                    components=[]
                    if b.isVia():
                        via=b.getTechVia()
                        if via is None:via=b.getBlockVia()
                        p.require(via is not None,"complete PG via")
                        ox,oy=b.getViaXY()
                        for ci,part in enumerate(via.getBoxes()):
                            p.require(not part.isVia(),"no nested PG via")
                            box=own.box(part);components.append((ci,part.getTechLayer().getName(),[box[0]+ox,box[1]+oy,box[2]+ox,box[3]+oy]))
                    else:components=[(None,b.getTechLayer().getName(),own.box(b))]
                    for ci,layer,box in components:
                        rid=len(rows);rows.append(dict(swire=si,shape=ordinal,component=ci,layer=layer,box=box))
                        for tile in range(box[1]//10000,box[3]//10000+1):index.setdefault((layer,tile),[]).append(rid)
            p.require(rows,"existing PG special conductors");indices[netname]=(rows,index)
        for name,row in sorted(construction["rows"].items()):
            inst=block.findInst(name);p.require(inst is not None,"new diode exists")
            for pin,pinrow in sorted(row["pins"].items()):
                if pin=="A":continue
                term=inst.findITerm(pin);p.require(term is not None and term.getNet().getName()==pinrow["net"],"actual PG attachment")
                rows,index=indices[pinrow["net"]];matches=[]
                for layer,rect in term.getGeometries():
                    box=own.box(rect);ids=set()
                    for tile in range(box[1]//10000,box[3]//10000+1):ids.update(index.get((layer.getName(),tile),()))
                    for rid in sorted(ids):
                        target=rows[rid]["box"]
                        if min(box[2],target[2])>max(box[0],target[0])and min(box[3],target[3])>max(box[1],target[1]):
                            matches.append(dict(pin_layer=layer.getName(),pin_box=box,conductor=rows[rid]))
                result["contacts"][name+"/"+pin]=dict(net=pinrow["net"],positive_area_witnesses=matches)
                p.require(matches,"new diode PG terminal lacks direct physical contact: "+name+"/"+pin)
        p.require(len(result["contacts"])==2702,"all1351 diode VDD/VSS terminals checked")
        result["complete"]=True
    except BaseException as exc:result["error"]=repr(exc);raise
    finally:odb.dbDatabase.destroy(db);save("new-diode-direct-pg-contacts.json",result)
def make_overlay():
    admission=read("insertion-plan.json");inserted=read("insertion-snapshot.json")
    delta=p.insertion_def_delta((WORK/"baseline.def").read_bytes(),(WORK/"insertion.def").read_bytes(),admission,inserted,153129)
    save("insertion-def-delta.json",delta);del inserted,delta;gc.collect()
    native.preserve_owned_routes(WORK/"insertion-connected.odb",admission,DATA,"insertion")
    native.make_overlay(WORK,DATA)
def verdict():
    original=read("result.json");power=read("new-diode-direct-pg-contacts.json")
    p.require(power["complete"]is True and len(power["contacts"])==2702,"all direct PG contacts")
    result=dict(status="COMPLETE_SAVED_DIODE_ROUTING_QUALIFICATION"if original["bounded_cycle_qualified"]else"REJECTED_SAVED_DIODE_ROUTING_QUALIFICATION",
      candidate=original["candidate"],bounded_cycle_qualified=original["bounded_cycle_qualified"],legacy_verdict=original,
      current_repair_antennas_calls=0,current_reconstruction_calls=0,current_route_calls=1,
      prior_repair_calls=1,prior_reconstruction_calls=1,direct_diode_pg_contact_passed=True,
      guide_overlay_admission=read("guide-reload-admission.json"),no_candidate_promoted=True,**p.FLAGS)
    save("saved-diode-routing-result.json",result)
    p.require(result["bounded_cycle_qualified"]is True,"measured DRT/antenna qualification rejected")
def main():
    phase=os.environ["NSSOC_SAVED_DIODE_ROUTE_PHASE"]
    p.require(phase in plan.PREPARATION,"owned routing preparation phase")
    p.require(not any(k in os.environ for k in("GH_TOKEN","GITHUB_TOKEN")),"credential-free native")
    p.source_guard();verify_inputs();DATA.mkdir(parents=True,exist_ok=True);WORK.mkdir(parents=True,exist_ok=True)
    functions={"bootstrap":bootstrap,"guide-overlay":guide_overlay,"guide-reload-audit":guide_reload_audit,
      "power-contact-audit":power_contact_audit,"make-overlay":make_overlay,"verdict":verdict}
    p.run_phase("route-continuation-"+phase,functions[phase],verify_inputs,lambda name,value:save(name,value))
if __name__=="__main__":main()
