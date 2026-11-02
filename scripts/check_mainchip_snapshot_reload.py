"""Synthetic controls for exact native-snapshot comparisons; no CAD execution."""
import copy,json
from pathlib import Path
from mainchip_snapshot_reload_contract import compare_scope,validate_archive_member
def fixture():
    missing=dict(pin=dict(bytes=5,sha256="synthetic-null"),opcode_count=0)
    def net(name):
        return dict(identity=dict(name=name,sigtype="SIGNAL",terminals=[name+":A"]),
                    encoded=dict(wire_present=False,metadata="ROUTED",paths=[]),wire=copy.deepcopy(missing))
    before=dict(nets={n:net(n)for n in ["clock","owned","other"]},protected=["clock"],
                instances={"i":dict(location=[0,0])},masters={},immutable={"pg":"same"},
                block={"rows":[]},diode_template={"same":True},clock_record_pins={"clock":"same"},def_pin={"synthetic":0})
    after=copy.deepcopy(before)
    after["nets"]["owned"].update(encoded=dict(wire_present=True,metadata="ROUTED",paths=["ROUTED"]),
                                 wire=dict(pin=dict(bytes=7,sha256="synthetic-route"),opcode_count=2))
    after["def_pin"]={"synthetic":1}
    return before,after,dict(routing_nets=["owned"])
def main():
    records=[]
    a,b,s=fixture();r=compare_scope(a,b,s);assert r["changed_owners"]==["owned"]and not r["routing_complete"]
    records.append("accept declared wire delta without completed-route acceptance")
    a,b,s=fixture();r=compare_scope(a,a,s);assert r["still_absent_owners"]==["owned"]
    records.append("retain incomplete missing route explicitly")
    for label in ["net-loss","terminal","nonowned-wire","instance","pg","clock-record","sigtype","wire-class","duplicate-owner","protected-owner","unknown-section"]:
        a,b,s=fixture()
        if label=="net-loss":b["nets"].pop("other")
        elif label=="terminal":b["nets"]["owned"]["identity"]["terminals"]=["wrong"]
        elif label=="nonowned-wire":b["nets"]["other"]["wire"]["opcode_count"]=1
        elif label=="instance":b["instances"]["i"]["location"]=[1,0]
        elif label=="pg":b["immutable"]["pg"]="changed"
        elif label=="clock-record":b["clock_record_pins"]["clock"]="changed"
        elif label=="sigtype":b["nets"]["owned"]["identity"]["sigtype"]="CLOCK"
        elif label=="wire-class":b["nets"]["owned"]["encoded"]["metadata"]="FIXED"
        elif label=="duplicate-owner":s["routing_nets"]*=2
        elif label=="protected-owner":s["routing_nets"].append("clock")
        elif label=="unknown-section":b["extra"]={}
        try:compare_scope(a,b,s)
        except ValueError:records.append("refuse "+label)
        else:raise AssertionError(label)
    expected={"actual/member":dict(bytes=3,sha256="synthetic")}
    seen=set();assert validate_archive_member("actual/member",True,3,expected,seen)
    records.append("accept exact declared regular archive member")
    for label,name,regular,size,seen in [
        ("absolute","/actual/member",True,3,set()),
        ("parent","actual/../member",True,3,set()),
        ("alias","actual//member",True,3,set()),
        ("duplicate","actual/member",True,3,{"actual/member"}),
        ("symlink","actual/member",False,3,set()),
        ("size","actual/member",True,4,set()),
        ("unknown","unknown",True,3,set())]:
        try:validate_archive_member(name,regular,size,expected,seen)
        except ValueError:records.append("refuse archive "+label)
        else:raise AssertionError(label)
    assert len(records)==21
    target=Path("snapshot-reload-controls");target.mkdir()
    (target/"result.json").write_text(json.dumps(dict(status="PASS_PARTIAL_SNAPSHOT_SCOPE_SOURCE_CONTROLS",
        cases=records,count=len(records),native_executed=False,routing_complete=False,
        physical_acceptance=False,timing_accepted=False,full_phy_accepted=False),indent=2)+"\n")
if __name__=="__main__":main()
