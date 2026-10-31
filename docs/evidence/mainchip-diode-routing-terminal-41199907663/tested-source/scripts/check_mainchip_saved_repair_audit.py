#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0
"""Pure source/data controls; no native acquisition or OpenDB import."""
import ast,copy,hashlib,json,os,sys,base64
import mainchip_saved_geometry_contract as replay
from pathlib import Path
def main():
    path=Path(__file__).with_name("mainchip_saved_repair_audit.py")
    tree=ast.parse(path.read_bytes());names={"digest","compact","difference","geometry","native_pointer","untyped_geometry"}
    nodes=[n for n in tree.body if isinstance(n,ast.FunctionDef)and n.name in names]
    assert len(nodes)==len(names)
    scope={"hashlib":hashlib,"json":json}
    exec(compile(ast.Module(body=nodes,type_ignores=[]),str(path),"exec"),scope)
    compact,difference,geometry=(scope[n]for n in("compact","difference","geometry"))
    raw=dict(instances={"old":dict(master=["lib","diode"],location=[1,2])},
      nets={"clock":dict(wire=dict(pin="wire",opcode_count=2),identity=dict(pin="old"),encoded=dict(kind="FIXED"))},
      protected=["clock"],clock_record_pins={"clock":"raw-def"},block={"name":"chip"},
      immutable={"special":"power"},masters={"lib/diode":"full-geometry"},diode_template="old")
    before=compact(raw);rows=[]
    def check(name,condition):
        assert condition,name;rows.append(name)
    def changed(edit):
        x=copy.deepcopy(raw);edit(x);return difference(before,compact(x))
    empty=difference(before,compact(copy.deepcopy(raw)))
    check("unchanged full census",not empty["changed_nets"]and not empty["changed_original_instances"]and empty["clock_record_pins_equal"])
    d=changed(lambda x:x["instances"].update(new=copy.deepcopy(x["instances"]["old"])))
    check("new instance named explicitly",d["added_instances"]==["new"]and not d["changed_original_instances"])
    d=changed(lambda x:x["instances"].pop("old"))
    check("missing original retained",d["removed_instances"]==["old"])
    d=changed(lambda x:x["instances"]["old"].update(location=[1,3]))
    check("original movement detected",d["changed_original_instances"]==["old"])
    d=changed(lambda x:x["nets"]["clock"]["wire"].update(pin="different"))
    check("protected wire change retained",d["changed_wire_nets"]==["clock"]and d["protected_changed_nets"]==["clock"])
    d=changed(lambda x:x["nets"]["clock"]["identity"].update(pin="new"))
    check("terminal change distinct",d["changed_nets"]=={"clock":["identity"]}and not d["changed_wire_nets"])
    d=changed(lambda x:x["nets"]["clock"]["encoded"].update(kind="ROUTED"))
    check("metadata change distinct",d["changed_nets"]=={"clock":["encoded"]})
    d=changed(lambda x:x["nets"].update(new=copy.deepcopy(x["nets"]["clock"])))
    check("new net retained",d["added_nets"]==["new"])
    d=changed(lambda x:x["nets"].pop("clock"))
    check("removed net retained",d["removed_nets"]==["clock"])
    d=changed(lambda x:x["clock_record_pins"].update(clock="changed-def"))
    check("raw clock DEF change detected",d["clock_record_pins_equal"]is False)
    d=changed(lambda x:x["immutable"].update(special="modified"))
    check("immutable material change detected",d["material_equal"]["immutable"]is False)
    shapes=[dict(kind="wire",layer="Metal1",box=[0,0,1,4],opcode_index=1),
      dict(kind="via",layer="Via1",box=[0,0,1,1],opcode_index=2)]
    def g(s):return geometry(dict(shapes=s))
    check("geometry order independent",g(shapes)==g(list(reversed(shapes))))
    check("geometry multiplicity retained",g(shapes)!=g(shapes+shapes[:1]))
    different=copy.deepcopy(shapes);different[0]["layer"]="Metal2"
    check("layer distinction retained",g(shapes)!=g(different))
    different=copy.deepcopy(shapes);different[0]["kind"]="via"
    check("via and wire distinction retained",g(shapes)!=g(different))
    for name,edit in(
      ("boolean coordinate rejected",lambda x:x[0]["box"].__setitem__(0,False)),
      ("zero area rejected",lambda x:x[0]["box"].__setitem__(2,0)),
      ("unknown geometry rejected",lambda x:x[0].update(kind="guess"))):
        bad=copy.deepcopy(shapes);edit(bad)
        try:g(bad)
        except ValueError:rows.append(name)
        else:raise AssertionError(name)
    native_pointer=scope["native_pointer"]
    class Proxy:
        def __init__(self,address):self.this=address
    a,b=Proxy(4096),Proxy(4096)
    check("distinct wrappers same native address",a is not b and native_pointer(a)==native_pointer(b))
    check("distinct native addresses remain distinct",native_pointer(a)!=native_pointer(Proxy(8192)))
    for name,value in(("null native address rejected",Proxy(0)),("negative native address rejected",Proxy(-1)),("missing native pointer rejected",object())):
        try:native_pointer(value)
        except(ValueError,AttributeError):rows.append(name)
        else:raise AssertionError(name)
    rect=dict(kind="wire-rect",layer="Metal1",box=[0,0,1,4],opcode_index=7)
    check("wire RECT retained",g([rect])==[["wire-rect","Metal1",[0,0,1,4]]])
    check("typed RECT differs from wire",g([rect])!=g(shapes[:1]))
    untyped=scope["untyped_geometry"]
    check("same copper rectangle ignores encoding kind only",untyped(dict(shapes=[rect]))==untyped(dict(shapes=shapes[:1])))
    root=Path(__file__).resolve().parents[1];proof=root/replay.PREFIX
    fixture="native/bulk-postdrt-antenna/saved-before-wire-001f19cbeef062f064a47c80e0f111e65c043cc88ffa32263f3d971b3c19cbff.json"
    locations=json.loads((proof/"native-record-locations.json").read_bytes())
    loc=locations[fixture]
    shard=json.loads((proof/loc["path"]).read_bytes())
    found=[x for x in shard["records"]if x["name"]==fixture];assert len(found)==1
    fixture_raw=base64.b64decode(found[0]["base64"],validate=True)
    assert len(fixture_raw)==149140 and hashlib.sha256(fixture_raw).hexdigest()=="0953f7bbd05c377fb985bff37a8bbe8abb8948a8aefff6db34385b7d385064bc"
    actual=json.loads(fixture_raw)["projection"]
    prior=ast.parse((proof/"tested-source/scripts/mainchip_saved_repair_audit.py").read_bytes())
    prior_geo=[x for x in prior.body if isinstance(x,ast.FunctionDef)and x.name=="geometry"];assert len(prior_geo)==1
    old_scope={};exec(compile(ast.Module(body=prior_geo,type_ignores=[]),"prior-authentic-geometry","exec"),old_scope)
    try:old_scope["geometry"](actual)
    except ValueError as exc:assert str(exc)=="unknown shape"
    else:raise AssertionError("original comparator must reproduce recorded rejection")
    check("authentic previously rejected wire RECT projection",len(geometry(actual))==actual["shape_count"]and any(x["kind"]=="wire-rect"for x in actual["shapes"]))
    metadata=json.loads((proof/"capsule-metadata/candidate-outputs.json").read_bytes())
    selected=replay.select(metadata["files"])
    check("complete native replay input selection",len(selected)==1223)
    for name,missing in(("missing wire refuses replay",next(x for x in sorted(selected)if "-wire-"in x and not x.endswith("-index.json"))),
      ("missing core record refuses replay","bulk-postdrt-inner-result.json")):
        bad=dict(metadata["files"]);bad.pop(missing)
        try:replay.select(bad)
        except ValueError:rows.append(name)
        else:raise AssertionError(name)
    assert len(rows)==30 and len(set(rows))==30
    result=dict(status="PASS_SAVED_REPAIR_AUDIT_SOURCE_CONTROLS",passed_cases=rows,count=30,
      source=os.environ["GITHUB_SHA"],run_id=int(os.environ["GITHUB_RUN_ID"]),attempt=int(os.environ["GITHUB_RUN_ATTEMPT"]),
      source_pin=hashlib.sha256(path.read_bytes()).hexdigest(),native_executed=False,
      physical_acceptance=False,timing_accepted=False,full_phy_accepted=False)
    Path(sys.argv[1]).write_text(json.dumps(result,sort_keys=True,indent=2)+"\n")
    print(json.dumps(result,sort_keys=True))
if __name__=="__main__":main()
