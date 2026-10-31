#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0
"""Cloud-only experimental diode reconstruction, preserving original wires."""
import json,os,sys,gc
from pathlib import Path
sys.path.insert(0,"/work/tail-source/scripts")
import odb
import mainchip_bulk_postdrt_antenna as p
import mainchip_bulk_postdrt_antenna_native as native
import mainchip_saved_diode_reconstruction as plan
from mainchip_bulk_postdrt_antenna_native import n
ROOT=Path("/work/failed-repair-inputs")
DATA=Path("/work/out/bulk-postdrt-antenna")
WORK=Path("/work/out/work/bulk-postdrt-antenna")
CURRENT=Path("/work/current-input.odb")
CANDIDATE=WORK/"reconstruction.odb"

def save(name,value):native.save(DATA/name,value)
def read(name):return json.loads((DATA/name).read_bytes())
def saved(name):return json.loads((ROOT/"bulk-postdrt-antenna"/name).read_bytes())
def native_pointer(obj):
    address=int(obj.this)
    if address<=0:raise ValueError("null or invalid native pointer")
    return address
def same_native(a,b):
    # Meaningful only while both wrappers belong to this one live database.
    return native_pointer(a)==native_pointer(b)
def instance_row(inst):
    master=inst.getMaster()
    return dict(master=[master.getLib().getName(),master.getName()],master_type=str(master.getType()),
      location=list(inst.getLocation()),origin=list(inst.getOrigin()),orientation=str(inst.getOrient()),
      status=str(inst.getPlacementStatus()),pins={t.getMTerm().getName():native.pin_row(t)for t in inst.getITerms()})
def verify_inputs():
    pins=json.loads((p.ROOT/plan.PINS).read_bytes())["files"]
    for name in sorted(plan.SELECTED):p.exact(native.fp(ROOT/name),pins[name],"authentic failed input "+name)
    p.exact(native.fp(CURRENT),p.INPUT,"unchanged accepted original ODB")

def saved_plan():
    before=saved("baseline-snapshot.json")
    after=saved("insertion-before-pg-snapshot.json")
    diagnosis=json.loads((p.ROOT/plan.DIAGNOSIS).read_bytes())
    result=plan.make_plan(before,after,diagnosis)
    save("reconstruction-plan.json",result)

def original_snapshot():
    result=native.snapshot(CURRENT,WORK/"reconstruction-original.def")
    save("reconstruction-original-snapshot.json",result)
    del result;gc.collect()
    pins=json.loads((p.ROOT/plan.PINS).read_bytes())["files"]
    p.exact(native.fp(DATA/"reconstruction-original-snapshot.json"),
      pins["bulk-postdrt-antenna/baseline-snapshot.json"],"complete fresh original snapshot byte identity")
    save("reconstruction-original-identity.json",dict(complete_snapshot_identical=True,
      snapshot=native.fp(DATA/"reconstruction-original-snapshot.json"),
      def_pin=native.fp(WORK/"reconstruction-original.def"),**p.FLAGS))

def construct():
    proof=read("reconstruction-plan.json")
    db,block=n.load(CURRENT);report=dict(added=[],native_identity_scope="one live database only",complete=False,**p.FLAGS)
    try:
        template=block.findInst("ANTENNA_1573");p.require(template is not None,"existing original template")
        p.exact(instance_row(template),proof["template"],"actual original template")
        master=template.getMaster()
        p.require(same_native(master,template.getMaster())
          and same_native(master.getLib(),template.getMaster().getLib()),"same live native template controls")
        original_names={i.getName()for i in block.getInsts()}
        p.require(len(original_names)==153129 and len(list(block.getNets()))==143820,"actual original census")
        p.require(not(set(proof["rows"])&original_names),"no existing name overwritten")
        other=next(i.getMaster()for i in block.getInsts()if i.getMaster().getName()!=master.getName())
        p.require(not same_native(master,other),"distinct live native masters")
        report["native_identity_controls"]=dict(repeated_master=True,repeated_library=True,different_master=True)
        for name,row in sorted(proof["rows"].items()):
            report["current"]=name
            p.require(block.findInst(name)is None,"new name collision")
            inst=odb.dbInst.create(block,master,name)
            p.require(inst is not None and same_native(inst.getMaster(),master),"created exact native template")
            inst.setOrient(row["orientation"])
            inst.setOrigin(*row["origin"])
            inst.setPlacementStatus(row["status"])
            p.exact(sorted(t.getMTerm().getName()for t in inst.getITerms()),sorted(row["pins"]),"actual created terminals")
            for terminal,pin in sorted(row["pins"].items()):
                term=inst.findITerm(terminal)
                p.require(term is not None and term.getNet()is None,"new disconnected terminal")
                net=block.findNet(pin["net"]);p.require(net is not None,"existing target net")
                p.require(str(net.getSigType())==pin["sigtype"],"actual target net type")
                if terminal=="A":
                    p.require(pin["net"]not in proof["protected"],"never attach to protected clock")
                else:
                    reference=template.findITerm(terminal)
                    p.require(reference is not None and reference.getNet()is not None
                      and same_native(net,reference.getNet()),"exact live template PG identity")
                term.connect(net)
                p.require(term.getNet()is not None and same_native(term.getNet(),net),"actual connection identity")
            p.exact(instance_row(inst),row,"exact reconstructed saved placement and terminals")
            report["added"].append(name)
        p.exact(sorted(i.getName()for i in block.getInsts()),sorted(original_names|set(proof["rows"])),"exact created instance census")
        odb.write_db(db,str(CANDIDATE));report["candidate"]=native.fp(CANDIDATE)
        report["complete"]=True;save("reconstruction-construction.json",report)
    except BaseException as exc:
        report["error"]=repr(exc)
        try:
            odb.write_db(db,str(WORK/"reconstruction-unadmitted-partial.odb"))
            report["partial_candidate"]=native.fp(WORK/"reconstruction-unadmitted-partial.odb")
        except BaseException as secondary:report["preservation_error"]=repr(secondary)
        save("reconstruction-construction.json",report)
        raise
    finally:odb.dbDatabase.destroy(db)

def candidate_snapshot():
    construction=read("reconstruction-construction.json")
    p.require(construction["complete"]is True,"complete actual creation")
    p.exact(native.fp(CANDIDATE),construction["candidate"],"exact created candidate")
    result=native.snapshot(CANDIDATE,WORK/"reconstruction-candidate.def")
    save("reconstruction-candidate-snapshot.json",result)

def admit():
    before=read("reconstruction-original-snapshot.json")
    after=read("reconstruction-candidate-snapshot.json")
    proof=read("reconstruction-plan.json")
    p.exact({name:after["instances"][name]for name in proof["rows"]},proof["rows"],"full reloaded added rows")
    p.exact(after["protected"],before["protected"],"original protected net census")
    p.exact(after["clock_record_pins"],before["clock_record_pins"],"all original1691 clock DEF records")
    p.exact(after["diode_template"],before["diode_template"],"original diode template")
    violations=saved("baseline-antenna-violations.json")
    admitted=p.admit_insertions(before,after,before["protected"],violations)
    p.exact(admitted["added_instances"],sorted(proof["rows"]),"exact admitted diode names")
    p.exact(admitted["mutable_nets"],proof["attachments"],"exact admitted mutable net set")
    save("reconstruction-original-admission.json",admitted)
    save("reconstruction-result.json",dict(status="COMPLETE_SAVED_DIODE_RECONSTRUCTION_QUALIFICATION",
      read_only=False,reconstruction_calls=1,repair_antennas_calls=0,route_calls=0,
      original_failed_run=41172959321,diagnosis_run=41189662022,
      original_instances_preserved=len(before["instances"]),original_nets_preserved=len(before["nets"]),
      original_clock_records_preserved=len(before["clock_record_pins"]),added_diodes=len(proof["rows"]),
      mutable_nets=len(proof["attachments"]),all_original_wire_bytes_and_metadata_preserved=True,
      full_original_admission_passed=True,candidate=native.fp(CANDIDATE),
      original_failure_remains_failure=True,no_candidate_promoted=True,**p.FLAGS))

def main():
    phase=os.environ["NSSOC_DIODE_RECONSTRUCTION_PHASE"]
    p.require(phase in plan.PHASES,"owned reconstruction phase")
    p.require(not any(k in os.environ for k in("GH_TOKEN","GITHUB_TOKEN")),"credential-free native process")
    p.source_guard();verify_inputs();DATA.mkdir(parents=True,exist_ok=True);WORK.mkdir(parents=True,exist_ok=True)
    functions={"saved-plan":saved_plan,"original-snapshot":original_snapshot,"construct":construct,
      "candidate-snapshot":candidate_snapshot,"admit":admit}
    p.run_phase("reconstruction-"+phase,functions[phase],verify_inputs,lambda name,value:save(name,value))
if __name__=="__main__":main()
