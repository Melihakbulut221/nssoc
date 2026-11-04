"""Offline source controls; actual complete netlist roundtrip runs in the native job."""
import copy,json,sys
from pathlib import Path
from mainchip_postroute_handoff_contract import pg,topology,restoration,wire_class,wire_census,clock_gate,verilog_names,compact
ROOT=Path(__file__).resolve().parents[1]
def restoration_controls(rejected):
    def net(cls,wire,paths=1):return dict(identity=dict(name="n"),encoded=dict(wire_present=True,metadata=cls,paths=[cls]*paths),wire=dict(pin=wire))
    baseline=dict(instances={"u":1},protected=["clk"],clock_record_pins={"clk":"ROUTED"},def_pin="b",
        nets={"clk":net("ROUTED","w1"),"n":net("ROUTED","w2")})
    before=copy.deepcopy(baseline);before["clock_record_pins"]={"clk":"FIXED"};before["def_pin"]="c"
    before["nets"]["clk"]=net("FIXED","w1")
    after=copy.deepcopy(baseline);after["def_pin"]="e"
    result=restoration(before,after,baseline,"e")
    assert result["restored_clock_records"]==["clk"]and result["restored_class_nets"]==["clk"],result
    rerouted_before=copy.deepcopy(before);rerouted_before["nets"]["n"]=net("ROUTED","w3",3)
    rerouted_after=copy.deepcopy(after);rerouted_after["nets"]["n"]=net("ROUTED","w3",3)
    assert restoration(rerouted_before,rerouted_after,baseline,"e")["geometry_differs_from_baseline"]==["n"]
    reclassed=copy.deepcopy(rerouted_after);reclassed["nets"]["n"]["encoded"]["paths"]=["ROUTED","FIXED","ROUTED"]
    try:restoration(rerouted_before,reclassed,baseline,"e")
    except ValueError:rejected.append("rerouted_net_class_changed")
    else:raise AssertionError("class change admitted")
    tupled=copy.deepcopy(after);tupled["instances"]={"u":(1,)}
    try:restoration(before,tupled,baseline,"e")
    except ValueError as error:
        assert "not JSON-normal" in str(error),error;rejected.append("unnormalized_in_memory_snapshot")
    else:raise AssertionError("tuple snapshot admitted")
    names=["clk%d"%i for i in range(1690)]+["clknet_3_5_0_pcie_clk_i"]
    term=lambda x:dict(name=x,terminals=[["u",x,"BUF",[0,0],"R0"]])
    base=dict(protected=names,clock_record_pins={x:"rec" for x in names},nets={x:dict(identity=term(x))for x in names})
    assert clock_gate(copy.deepcopy(base),base)["clock_or_fixed_nets"]==1691
    for label,change in (("clock_attached_geometry",lambda a:a["nets"]["clk7"]["identity"]["terminals"][0].__setitem__(3,[5,0])),
                         ("clock_record_changed",lambda a:a["clock_record_pins"].update(clk7="other")),
                         ("clock_scope_changed",lambda a:a.update(protected=names[1:]))):
        wrong=copy.deepcopy(base);change(wrong)
        try:clock_gate(wrong,base)
        except ValueError:rejected.append(label)
        else:raise AssertionError(label)
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
    esc=dict(top="soc_top",instances={"$flatten\\u_a.r":dict(master="dff",pins={"D":"$x\\n","VSS":"g"})},
        ports={"p":dict(net="$x\\n",io="INPUT")},nets={"$x\\n":dict(iterms=[["$flatten\\u_a.r","D"]],bterms=["p"]),"g":dict(iterms=[["$flatten\\u_a.r","VSS"]],bterms=[])})
    doubled=json.loads(json.dumps(esc).replace("\\\\","\\\\\\\\"))
    assert doubled!=esc
    normal,renamed=verilog_names(doubled);topology(esc,normal);assert renamed==dict(instances=1,nets=1),renamed
    try:topology(esc,doubled)
    except ValueError:rejected.append("unnormalized_verilog_escape")
    else:raise AssertionError("doubled escapes compared equal")
    reversed_bus=copy.deepcopy(normal);reversed_bus["instances"]["$flatten\\u_a.r"]["pins"]["D"]="g"
    try:topology(esc,reversed_bus)
    except ValueError:rejected.append("normalized_name_wrong_connection")
    else:raise AssertionError("connection change admitted after normalization")
    collide=copy.deepcopy(doubled);collide["instances"]["$flatten\\u_a.r"]=collide["instances"]["$flatten\\\\u_a.r"]
    try:verilog_names(collide)
    except ValueError:rejected.append("escape_normalization_collision")
    else:raise AssertionError("collision admitted")
    big=dict(restored_class_nets=["n%d"%i for i in range(142877)],status="S",nested=dict(names=list(range(70)),few=[1,2]))
    small=compact(big)
    assert small["restored_class_nets"]["count"]==142877 and small["nested"]["few"]==[1,2] and small["nested"]["names"]["count"]==70
    assert len(json.dumps(small))<2000 and small["status"]=="S"
    other=copy.deepcopy(big);other["restored_class_nets"][5]="changed"
    assert compact(other)["restored_class_nets"]["sha256"]!=small["restored_class_nets"]["sha256"]
    restoration_controls(rejected)
    census=wire_controls(rejected)
    out=Path("postroute-handoff-controls");out.mkdir(exist_ok=False)
    (out/"result.json").write_text(json.dumps(dict(status="PASS_SOURCE_CONTROLS_ONLY",rejected=rejected,wire_census=census,
        native_execution=False,physical_acceptance=False,timing_accepted=False,full_phy_accepted=False),indent=2)+"\n")
if __name__=="__main__":main()
