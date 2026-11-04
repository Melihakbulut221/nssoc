"""Offline source controls; actual complete netlist roundtrip runs in the native job."""
import copy,json,sys
from pathlib import Path
from mainchip_postroute_handoff_contract import pg,topology,restoration,wire_class,wire_census
ROOT=Path(__file__).resolve().parents[1]
def restoration_controls(rejected):
    def net(cls,wire):return dict(identity=dict(name="n"),encoded=dict(metadata=cls),wire=dict(pin=wire))
    baseline=dict(instances={"u":1},protected=["clk"],clock_record_pins={"clk":"ROUTED"},def_pin="b",
        nets={"clk":net("ROUTED","w1"),"n":net("ROUTED","w2")})
    before=copy.deepcopy(baseline);before["clock_record_pins"]={"clk":"FIXED"};before["def_pin"]="c"
    before["nets"]["clk"]=net("FIXED","w1")
    after=copy.deepcopy(baseline);after["def_pin"]="e"
    result=restoration(before,after,baseline,"e")
    assert result["restored_clock_records"]==["clk"]and result["restored_class_nets"]==["clk"],result
    tupled=copy.deepcopy(after);tupled["instances"]={"u":(1,)}
    try:restoration(before,tupled,baseline,"e")
    except ValueError as error:
        assert "not JSON-normal" in str(error),error;rejected.append("unnormalized_in_memory_snapshot")
    else:raise AssertionError("tuple snapshot admitted")
    for label,change in (("clock_record_not_baseline",lambda a:a["clock_record_pins"].update(clk="OTHER")),
                         ("instance_section_changed",lambda a:a["instances"].update(u=2)),
                         ("clock_record_census",lambda a:a["clock_record_pins"].update(extra="ROUTED"))):
        wrong=copy.deepcopy(after);change(wrong)
        try:restoration(before,wrong,baseline,"e")
        except ValueError:rejected.append(label)
        else:raise AssertionError(label)
def wire_controls(rejected):
    sys.path.insert(0,str(ROOT/"original/scripts"))
    import mainchip_original_clock_restoration as c
    routed=b"- n1 ( u1 A ) ( u2 Y )\n  + ROUTED Metal2 ( 0 0 ) ( 10 0 )\n  NEW Metal3 ( 10 0 ) ( 10 5 ) ;\n"
    fixed=b"- n2 ( u1 B ) ( u3 Y )\n  + FIXED Metal2 ( 0 0 ) ( 0 10 ) ;\n"
    wireless=b"- n3 ( u4 A )\n  + USE SIGNAL ;\n"
    multiple=b"- n4 ( u5 A ) ( u6 Y )\n  + ROUTED Metal2 ( 0 0 ) ( 1 0 )\n  + FIXED Metal3 ( 0 0 ) ( 0 1 ) ;\n"
    inline=b"- n5 ( u7 A ) + ROUTED Metal2 ( 0 0 ) ( 1 0 ) ;\n"
    assert wire_class(c,routed)=="ROUTED" and wire_class(c,fixed)=="FIXED" and wire_class(c,wireless) is None
    try:c.classes(wireless)
    except AssertionError:pass
    else:raise AssertionError("frozen single-clause parser now admits wireless records")
    try:wire_class(c,multiple)
    except AssertionError:rejected.append("multiple_wire_clauses")
    else:raise AssertionError("multiple clauses admitted")
    try:wire_class(c,inline)
    except ValueError:rejected.append("unsupported_inline_wire_syntax")
    else:raise AssertionError("inline wire syntax admitted")
    census=wire_census(c,dict(n1=routed,n2=fixed,n3=wireless,n4=multiple,n5=inline))
    assert census==dict(records=5,single_clause=2,wireless=1,wireless_names=["n3"],multiple_clause=dict(n4=2),unsupported_syntax=["n5"]),census
    return census
def main():
    base=dict(top="soc_top",instances={"d":dict(master="sg13g2_antennanp",pins={"A":"n","VSS":"g"})},
        ports={"p":dict(net="n",io="INPUT")},
        nets={"n":dict(iterms=[["d","A"]],bterms=["p"]),"g":dict(iterms=[["d","VSS"]],bterms=[])})
    topology(base,copy.deepcopy(base))
    rejected=[]
    for label in ("missing_cell","supply_disconnect","master_change","missing_port","lost_incidence"):
        wrong=copy.deepcopy(base)
        if label=="missing_cell":del wrong["instances"]["d"]
        elif label=="supply_disconnect":wrong["instances"]["d"]["pins"]["VSS"]=None
        elif label=="master_change":wrong["instances"]["d"]["master"]="other"
        elif label=="missing_port":wrong["ports"].clear()
        else:wrong["nets"]["n"]["iterms"]=[]
        try:topology(base,wrong)
        except ValueError:rejected.append(label)
        else:raise AssertionError(label)
    row=dict(master=["lib","sg13g2_antennanp"],pins={
        "A":dict(net="n",sigtype="SIGNAL",io="INPUT"),
        "VSS":dict(net="g",sigtype="GROUND",io="INOUT")})
    pg({"d":row},row,[])
    wrong=copy.deepcopy(row);wrong["pins"]["VSS"]["net"]=None
    try:pg({"d":wrong},row,[])
    except ValueError:rejected.append("diode_supply_disconnected")
    else:raise AssertionError("unconnected PG admitted")
    restoration_controls(rejected)
    census=wire_controls(rejected)
    out=Path("postroute-handoff-controls");out.mkdir(exist_ok=False)
    (out/"result.json").write_text(json.dumps(dict(status="PASS_SOURCE_CONTROLS_ONLY",rejected=rejected,wire_census=census,
        native_execution=False,physical_acceptance=False,timing_accepted=False,full_phy_accepted=False),indent=2)+"\n")
if __name__=="__main__":main()
