"""Offline source controls; actual complete netlist roundtrip runs in the native job."""
import copy,json
from pathlib import Path
from mainchip_postroute_handoff_contract import pg,topology,restoration
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
    out=Path("postroute-handoff-controls");out.mkdir(exist_ok=False)
    (out/"result.json").write_text(json.dumps(dict(status="PASS_SOURCE_CONTROLS_ONLY",rejected=rejected,
        native_execution=False,physical_acceptance=False,timing_accepted=False,full_phy_accepted=False),indent=2)+"\n")
if __name__=="__main__":main()
