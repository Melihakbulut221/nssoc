#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0
"""Read-only saved genuine-repair diagnosis; never repair, route or write a DB."""
import hashlib,json,os,sys,gc
from pathlib import Path
sys.path.insert(0,"/work/tail-source/scripts")
import odb
import mainchip_bulk_postdrt_antenna as p
import mainchip_bulk_postdrt_antenna_native as native
from mainchip_bulk_postdrt_antenna_native import n,own
ROOT=Path("/work/failed-repair-inputs")
OUT=Path("/work/out/bulk-postdrt-antenna")
WORK=Path("/work/out/work/bulk-postdrt-antenna")
CURRENT=Path("/work/current-input.odb")
PARTIAL=ROOT/"work/bulk-postdrt-antenna/insertion-after-shim.odb"
PINS="docs/evidence/mainchip-bulk-namespace-real-repair-terminal-41172959321/capsule-metadata/candidate-outputs.json"
PHASES=("snapshot-delta","master-identity","wire-before","wire-after","wire-compare")

def digest(value):
    return hashlib.sha256(json.dumps(value,sort_keys=True,separators=(",",":"),allow_nan=False).encode()).hexdigest()

def compact(snapshot):
    return dict(
      instances={name:digest(row)for name,row in snapshot["instances"].items()},
      instance_masters={name:row["master"]for name,row in snapshot["instances"].items()},
      nets={name:dict(wire=row["wire"],identity=digest(row["identity"]),encoded=digest(row["encoded"]))
            for name,row in snapshot["nets"].items()},
      protected=snapshot["protected"],clock_record_pins=snapshot["clock_record_pins"],
      material={key:digest(snapshot[key])for key in("block","immutable","masters","diode_template")})

def difference(before,after):
    bi=before["instances"];ai=after["instances"];bn=before["nets"];an=after["nets"]
    added=sorted(set(ai)-set(bi));removed=sorted(set(bi)-set(ai))
    changed=sorted(name for name in set(bi)&set(ai)if bi[name]!=ai[name])
    delta={name:[key for key in("wire","identity","encoded")if bn[name][key]!=an[name][key]]
       for name in sorted(set(bn)&set(an))if bn[name]!=an[name]}
    return dict(added_instances=added,removed_instances=removed,changed_original_instances=changed,
      added_nets=sorted(set(an)-set(bn)),removed_nets=sorted(set(bn)-set(an)),
      changed_nets=delta,changed_wire_nets=sorted(name for name,fields in delta.items()if"wire"in fields),
      protected_changed_nets=sorted(set(delta)&set(before["protected"])),
      protected_sets_equal=before["protected"]==after["protected"],
      clock_record_pins_equal=before["clock_record_pins"]==after["clock_record_pins"],
      material_equal={key:before["material"][key]==after["material"][key]for key in before["material"]})

def geometry(projection):
    # A multiset of computed conductor/cut rectangles, not an electrical proof.
    # Preserve duplicates, kind and layer. Junction/operand ordering is separate.
    rows=[]
    for shape in projection["shapes"]:
        if shape["kind"]not in("wire","via"):raise ValueError("unknown shape")
        box=shape["box"]
        if len(box)!=4 or any(type(x)is not int for x in box)or box[0]>=box[2]or box[1]>=box[3]:
            raise ValueError("invalid rectangle")
        if not isinstance(shape["layer"],str)or not shape["layer"]:raise ValueError("layer")
        rows.append([shape["kind"],shape["layer"],box])
    return sorted(rows)

def save(name,value):
    native.save(OUT/name,value)
def read(name):
    return json.loads((OUT/name).read_bytes())
def verify_inputs():
    pins=json.loads((p.ROOT/PINS).read_bytes())["files"]
    for name in("bulk-postdrt-antenna/baseline-snapshot.json",
      "bulk-postdrt-antenna/insertion-before-pg-snapshot.json",
      "work/bulk-postdrt-antenna/insertion-after-shim.odb"):
        p.exact(native.fp(ROOT/name),pins[name],"saved input identity "+name)
    p.exact(native.fp(CURRENT),p.INPUT,"original accepted current input")

def snapshots():
    observations={}
    for label,name in(("before","baseline-snapshot.json"),("after","insertion-before-pg-snapshot.json")):
        raw=json.loads((ROOT/"bulk-postdrt-antenna"/name).read_bytes())
        p.require(len(raw["nets"])==143820 and len(raw["protected"])==1691,"full saved census")
        small=compact(raw);del raw;gc.collect()
        observations[label]=small;save("saved-"+label+"-fingerprints.json",small)
    delta=difference(observations["before"],observations["after"])
    save("saved-delta.json",delta)
    save("saved-delta-summary.json",dict(counts={key:len(delta[key])for key in(
      "added_instances","removed_instances","changed_original_instances","added_nets","removed_nets",
      "changed_nets","changed_wire_nets","protected_changed_nets")},
      protected_sets_equal=delta["protected_sets_equal"],clock_record_pins_equal=delta["clock_record_pins_equal"],
      material_equal=delta["material_equal"],**p.FLAGS))

def native_pointer(obj):
    # SWIG .this holds the native C++ address. Scope is one live database;
    # never compare or persist these values as IDs across loads/processes.
    address=int(obj.this)
    if address<=0:raise ValueError("null or invalid native pointer")
    return address

def master_key(master):
    return dict(library_address=native_pointer(master.getLib()),library_name=master.getLib().getName(),
      master_address=native_pointer(master),master_name=master.getName(),master_type=str(master.getType()),
      width=master.getWidth(),height=master.getHeight(),
      mterms={m.getName():dict(address=native_pointer(m),io=str(m.getIoType()),sigtype=str(m.getSigType()))
              for m in master.getMTerms()})

def net_key(net):
    return None if net is None else dict(address=native_pointer(net),name=net.getName(),sigtype=str(net.getSigType()))

def master_identity():
    before=read("saved-before-fingerprints.json");delta=read("saved-delta.json")
    db,b=n.load(PARTIAL)
    try:
        p.require(len(list(b.getNets()))==143820,"full partial native net census")
        names={i.getName()for i in b.getInsts()}
        p.exact(sorted(names-set(before["instances"])),delta["added_instances"],"actual added names")
        p.exact(sorted(set(before["instances"])-names),delta["removed_instances"],"actual removed names")
        template=b.findInst("ANTENNA_1573");p.require(template is not None,"actual template")
        tm=template.getMaster();key=master_key(tm);rows=[]
        p.require(native_pointer(template.getMaster())==native_pointer(tm),"repeat native master pointer")
        p.require(native_pointer(tm.getLib())==native_pointer(template.getMaster().getLib()),"repeat native library pointer")
        different=next((i.getMaster()for i in b.getInsts()if native_pointer(i.getMaster())!=native_pointer(tm)),None)
        p.require(different is not None and native_pointer(different)!=native_pointer(template.getMaster()),"distinct native master control")
        scope=dict(database_address=native_pointer(db),block_address=native_pointer(b),
          lifetime="This loaded database only; addresses are not persistent IDs.",
          repeat_master_pointer_equal=True,repeat_library_pointer_equal=True,
          distinct_master=dict(name=different.getName(),address=native_pointer(different)))
        for name in delta["added_instances"]:
            inst=b.findInst(name);master=inst.getMaster()
            pins={}
            for term in inst.getITerms():
                mt=term.getMTerm();reference=template.findITerm(mt.getName())
                a=term.getNet();r=None if reference is None else reference.getNet()
                pins[mt.getName()]=dict(sigtype=str(mt.getSigType()),net=net_key(a),template_net=net_key(r),
                  legacy_net_wrapper_equal=None if a is None or r is None else bool(a==r))
            rows.append(dict(name=name,master=master_key(master),
              stable_scoped_master_equal=master_key(master)==key,
              legacy_master_wrapper_equal=bool(master==tm),
              legacy_repeated_master_wrapper_equal=bool(inst.getMaster()==inst.getMaster()),pins=pins))
        save("saved-native-master-identity.json",dict(template=key,pointer_scope=scope,
          template_repeated_wrapper_equal=bool(template.getMaster()==template.getMaster()),instances=rows,
          stable_same_master_count=sum(x["stable_scoped_master_equal"]for x in rows),
          legacy_wrapper_equal_count=sum(x["legacy_master_wrapper_equal"]for x in rows),
          observed_added_count=len(rows),read_only=True,**p.FLAGS))
    finally:odb.dbDatabase.destroy(db)

def wires(label):
    expected=read("saved-"+label+"-fingerprints.json");delta=read("saved-delta.json")
    path=CURRENT if label=="before"else PARTIAL
    db,b=n.load(path)
    try:
        proof=own.api_evidence();layers=own.named_layers(db.getTech(),proof);index={}
        for name in delta["changed_wire_nets"]:
            net=b.findNet(name);p.require(net is not None,"changed wire exists")
            wire=net.getWire()
            raw=None if wire is None else[[wire.getOpcode(i),wire.getData(i)]for i in range(wire.length())]
            pin=dict(pin=p.pin(p.encode(raw)),opcode_count=0 if raw is None else len(raw))
            p.exact(pin,expected["nets"][name]["wire"],"actual native wire matches saved snapshot "+name)
            p.exact(digest(n.encoded(net)),expected["nets"][name]["encoded"],"actual encoded "+name)
            p.exact(digest(n.identity(db,net)),expected["nets"][name]["identity"],"actual terminals "+name)
            projection=None if wire is None else own.native_wire(db,b,wire,layers,proof)
            value=dict(net=name,wire_pin=pin,encoded=n.encoded(net),identity=n.identity(db,net),
              projection=projection,read_only=True)
            filename="saved-"+label+"-wire-"+hashlib.sha256(name.encode()).hexdigest()+".json"
            save(filename,value);index[name]=dict(path=filename,**native.fp(OUT/filename))
        save("saved-"+label+"-wire-index.json",index)
    finally:odb.dbDatabase.destroy(db)

def compare_wires():
    delta=read("saved-delta.json");a=read("saved-before-wire-index.json");b=read("saved-after-wire-index.json")
    p.exact(sorted(a),delta["changed_wire_nets"],"complete before observations")
    p.exact(sorted(b),delta["changed_wire_nets"],"complete after observations")
    rows={}
    for name in delta["changed_wire_nets"]:
        raw=[]
        for index in(a,b):
            path=OUT/index[name]["path"]
            p.exact(native.fp(path),{k:index[name][k]for k in("bytes","sha256")},"wire observation identity")
            raw.append(json.loads(path.read_bytes()))
        old,new=raw
        ga=None if old["projection"]is None else geometry(old["projection"])
        gb=None if new["projection"]is None else geometry(new["projection"])
        rows[name]=dict(rectangle_multiset_equal=ga==gb,encoded_equal=old["encoded"]==new["encoded"],
          terminal_identity_equal=old["identity"]==new["identity"],
          shape_counts=[None if x is None else len(x)for x in(ga,gb)],
          before_geometry_sha256=digest(ga),after_geometry_sha256=digest(gb))
    save("saved-wire-comparison.json",dict(nets=rows,
      rectangle_multiset_equal_count=sum(x["rectangle_multiset_equal"]for x in rows.values()),
      rectangle_multiset_changed_count=sum(not x["rectangle_multiset_equal"]for x in rows.values()),
      total=len(rows),read_only=True,geometry_equality_is_not_connectivity_or_DRC_acceptance=True,**p.FLAGS))
    master=read("saved-native-master-identity.json")
    save("saved-audit-result.json",dict(status="COMPLETE_SAVED_BULK_REPAIR_DIAGNOSIS",read_only=True,
      repair_calls=0,route_calls=0,original_failed_run=41172959321,
      snapshot=read("saved-delta-summary.json"),
      master=dict(observed_added_count=master["observed_added_count"],
         stable_same_master_count=master["stable_same_master_count"],
         legacy_wrapper_equal_count=master["legacy_wrapper_equal_count"],
         template_repeated_wrapper_equal=master["template_repeated_wrapper_equal"]),
      wire=dict(total=len(rows),rectangle_multiset_equal_count=sum(x["rectangle_multiset_equal"]for x in rows.values()),
         rectangle_multiset_changed_count=sum(not x["rectangle_multiset_equal"]for x in rows.values())),
      prior_failure_remains_failure=True,no_candidate_promoted=True,**p.FLAGS))

def main():
    phase=os.environ["NSSOC_SAVED_REPAIR_PHASE"];p.require(phase in PHASES,"read-only phase")
    p.require(not any(x in os.environ for x in("GH_TOKEN","GITHUB_TOKEN")),"credential-free native")
    p.source_guard();verify_inputs();OUT.mkdir(exist_ok=True,parents=True)
    actions={"snapshot-delta":snapshots,"master-identity":master_identity,
      "wire-before":lambda:wires("before"),"wire-after":lambda:wires("after"),"wire-compare":compare_wires}
    p.run_phase("saved-"+phase,actions[phase],verify_inputs,lambda name,value:save(name,value))
if __name__=="__main__":main()
