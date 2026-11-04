"""Independent synthetic faults for scope boundaries before native routing."""
import copy,json
from pathlib import Path
from mainchip_route47_contract import route_program,select,wire_delta
ROOT=Path(__file__).resolve().parents[1]
def fixture():
    def net(n):
        return dict(identity=dict(name=n,sigtype="SIGNAL",terminals=[n+":A"]),encoded=dict(wire_present=True,metadata="ROUTED",paths=["ROUTED"]),wire=dict(pin={"sha256":"original"},opcode_count=2))
    before=dict(nets={n:net(n)for n in("clock","owned","other")},protected=["clock"],instances={"x":[1,2]},immutable={"pg":"same"},clock_record_pins={"clock":"same"},def_pin="before")
    plan=dict(records=[dict(sources="net:owned net:other",names=["owned","other"],selected_owners=["owned"])],violations=1,selected_routing_nets=["owned"],selected_count=1)
    scope=dict(routing_nets=["owned"],protected_nets=["clock"])
    after=copy.deepcopy(before);after["nets"]["owned"].update(encoded=dict(wire_present=False,metadata="ROUTED",paths=[]),wire=dict(pin={"sha256":"null"},opcode_count=0));after["def_pin"]="after"
    return before,after,plan,scope
def main():
    cases=[];a,b,p,s=fixture();assert select(p,s,a)==(["owned"],["other","owned"]);cases.append("exact literal native selection")
    wire_delta(a,b,["owned"],"clear",{"sha256":"null"});cases.append("only selected wire cleared")
    a,b,p,s=fixture();b["nets"]["owned"]["encoded"]=copy.deepcopy(a["nets"]["owned"]["encoded"]);b["nets"]["owned"]["wire"]=dict(pin={"sha256":"new"},opcode_count=3)
    wire_delta(a,b,["owned"],"route",{"sha256":"null"});cases.append("only selected route replaced")
    for label in ("unknown-native-name","misreported-name","wrong-owner","wrong-census","protected-owner","power-owner"):
        a,b,p,s=fixture()
        if label=="unknown-native-name":p["records"][0].update(sources="net:owned net:missing",names=["owned","missing"])
        elif label=="misreported-name":p["records"][0]["names"]=["owned","clock"]
        elif label=="wrong-owner":p["selected_routing_nets"]=["other"]
        elif label=="wrong-census":p["violations"]=2
        elif label=="protected-owner":s["routing_nets"].append("clock")
        elif label=="power-owner":a["nets"]["owned"]["identity"]["sigtype"]="POWER"
        try:select(p,s,a)
        except ValueError:cases.append("refuse "+label)
        else:raise AssertionError(label)
    for label in ("nonowner-wire","clock-wire","terminal","instance","pg","clock-record","net-loss","missing-pin","wrong-class","duplicate-owner","protected-delta"):
        a,b,p,s=fixture();owners=["owned"]
        if label=="nonowner-wire":b["nets"]["other"]["wire"]["opcode_count"]+=1
        elif label=="clock-wire":b["nets"]["clock"]["wire"]["opcode_count"]+=1
        elif label=="terminal":b["nets"]["owned"]["identity"]["terminals"]=[]
        elif label=="instance":b["instances"]["x"]=[2,2]
        elif label=="pg":b["immutable"]["pg"]="other"
        elif label=="clock-record":b["clock_record_pins"]["clock"]="other"
        elif label=="net-loss":b["nets"].pop("other")
        elif label=="missing-pin":b["nets"]["owned"]["wire"]["pin"]={"sha256":"not-null"}
        elif label=="wrong-class":b["nets"]["owned"]["encoded"]["metadata"]="FIXED"
        elif label=="duplicate-owner":owners*=2
        elif label=="protected-delta":owners.append("clock")
        try:wire_delta(a,b,owners,"clear",{"sha256":"null"})
        except ValueError:cases.append("refuse "+label)
        else:raise AssertionError(label)
    route=(ROOT/"scripts/mainchip-bounded-route-baseline.tcl").read_text()
    old="read_db {/work/out/work/bulk-postdrt-antenna/stale-wire-cleared.odb}";new="read_db {/work/out/work/bulk-postdrt-antenna/narrow47-cleared.odb}"
    changed=route_program(route,old,new)
    assert changed.count(new)==1 and old not in changed and changed.count("detailed_route_debug")==route.count("detailed_route_debug")==1
    cases.append("original snapshot-free route program with only input rebound")
    debug="set_debug_level DRT snapshot 1\ndetailed_route_debug -snapshot_dir {/work}\n"
    marker="puts NSSOC_FIXED_CLOCK_SIGNAL_REPAIR_BEGIN"
    for label,text,a,b in [("double-input",route+"\n"+old+"\n",old,new),("double-route",route+"\ndetailed_route {*}$drt_args\n",old,new),
        ("missing-stage",route.replace(marker,"puts OTHER"),old,new),("snapshots-enabled",route.replace('DRT_SAVE_SNAPSHOTS) ne "0"','DRT_SAVE_SNAPSHOTS) ne "1"'),old,new),
        ("binding-already-present",route+"\n#"+new+"\n",old,new),("unchanged-binding",route,old,old)]:
        try:route_program(text,a,b)
        except ValueError:cases.append("refuse "+label)
        else:raise AssertionError(label)
    assert debug+marker not in changed
    assert len(cases)==27
    out=Path("route47-controls");out.mkdir()
    (out/"result.json").write_text(json.dumps(dict(count=27,cases=cases,native_executed=False,physical_acceptance=False,timing_accepted=False,full_phy_accepted=False),indent=2)+"\n")
if __name__=="__main__":main()
