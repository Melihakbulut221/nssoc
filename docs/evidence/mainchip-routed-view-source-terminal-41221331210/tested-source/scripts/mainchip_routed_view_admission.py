#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0
"""Read-only routed-view admission. Current source authorizes no native execution."""
import hashlib,json,math,re
from pathlib import Path
import mainchip_stale_wire_admission as inherited

ROOT=Path(__file__).resolve().parents[1]
BRANCH="codex/mainchip-routed-view-admission"
MANIFEST="scripts/mainchip-routed-view-admission-pins.json"
BASE="ae4e05018e4f88943b45e56b76daf620ca1b9497"
PRODUCER="ddc1cbddf68096c5e976bf9acda5c5fb0168c5b9"
RUN=41211382427
FINAL="work/bulk-postdrt-antenna/final-measured.odb"
ENGINE_SHA="2a343c7491353a60e7b06aa134d4b67e3ef2e846a8341164dacffe88f5f7ec2f"
CORNERS=("nom_slow_1p08V_125C","nom_typ_1p20V_25C","nom_fast_1p32V_m40C")
PG={"POWER","GROUND"}
FLAGS=dict(native_acquisition=False,native_executed=False,physical_acceptance=False,timing_accepted=False,full_phy_accepted=False)
SIGNALS={"SIGNAL","CLOCK","ANALOG","RESET","SCAN","TIEOFF"}
IO={"INPUT","OUTPUT","INOUT","FEEDTHRU"}

def require(ok,why):
    if not ok:raise ValueError(why)
def exact(a,b,why):
    require(type(a)is type(b)and a==b,why)
def unique(pairs):
    out={}
    for k,v in pairs:
        require(k not in out,"duplicate JSON key");out[k]=v
    return out
def decode(raw):
    return json.loads(raw,object_pairs_hook=unique,parse_constant=lambda x:(_ for _ in ()).throw(ValueError("nonfinite JSON")))
def encode(value):
    return (json.dumps(value,sort_keys=True,separators=(",",":"),allow_nan=False)+"\n").encode()
def pin_bytes(raw):return dict(bytes=len(raw),sha256=hashlib.sha256(raw).hexdigest())
def pin(path):return inherited.pin(path)
def name(v):
    require(type(v)is str and v and "\x00"not in v and "\n"not in v and "\r"not in v,"invalid literal native name")
    return v
def sha(v):require(type(v)is str and re.fullmatch("[0-9a-f]{64}",v)is not None,"SHA256");return v
def filepin(v):
    require(type(v)is dict and set(v)=={"bytes","sha256"},"file pin fields")
    require(type(v["bytes"])is int and v["bytes"]>0,"file pin bytes");sha(v["sha256"]);return v

def source_gate():
    original=inherited.source_gate()
    require(pin(ROOT/inherited.MANIFEST)["sha256"]=="87782a2295d755d32143f8349e8831ad154abd1eb54726fac540ecd6d6af29b7","qualified inherited manifest")
    m=decode(inherited.regular(ROOT,MANIFEST).read_bytes())
    exact(m["schema"],"mainchip-routed-view-source-v1","source schema")
    exact(m["base"],BASE,"base source")
    require(m["source_controls_authorized"]is True and m["terminal_binding"]is None,"unbound source proposal")
    require(all(m[k]is False for k in ("native_export_authorized","native_acquisition_authorized","rc_sta_authorized",*FLAGS)),"source-only flags")
    require(set(original["files"])|{inherited.MANIFEST}<=set(m["files"]),"unchanged inherited protection")
    for path,digest in original["files"].items():exact(m["files"][path],digest,"inherited pin")
    for path,digest in m["files"].items():
        sha(digest);require(pin(inherited.regular(ROOT,path))["sha256"]==digest,"source pin "+path)
    return m

def authorize_native():
    # Deliberate unconditional source boundary. A future reviewed activation must
    # bind the terminal capsule and add its own cloud controls; flipping JSON is insufficient.
    source_gate()
    raise PermissionError("Native export disabled: terminal candidate envelope is not bound")

def validate_envelope(e):
    exact(set(e),{"run","attempt","source","member","candidate","archive","outputs_sha256","parts_sha256","receipt_sha256"},"envelope fields")
    require(type(e["run"])is int and e["run"]==RUN and type(e["attempt"])is int and e["attempt"]==1,"producer run")
    exact(e["source"],PRODUCER,"producer source");exact(e["member"],FINAL,"final measured member only")
    filepin(e["candidate"]);filepin(e["archive"])
    for k in ("outputs_sha256","parts_sha256","receipt_sha256"):sha(e[k])
    return e

def lineage(before,inserted,final,plan,violations):
    """Reuse original complete insertion/route checks, with enumerated exact census."""
    for state,count in ((before,153129),(inserted,154480),(final,154480)):
        require(len(state["instances"])==count and len(state["nets"])==143820,"enumerated whole candidate census")
    old=inherited.p
    actual=old.admit_insertions(before,inserted,before["protected"],violations)
    old.exact(actual,plan,"authentic insertion plan")
    require(len(plan["added_instances"])==1351 and len(plan["attachments"])==1351
      and len(plan["mutable_nets"])==608 and len(plan["protected_nets"])==1691,"complete native delta census")
    delta=old.route_delta(inserted,final,plan)
    old.exact(final["clock_record_pins"],before["clock_record_pins"],"all original clock records")
    return dict(baseline_instances=153129,added_diodes=1351,final_instances=154480,nets=143820,delta=delta,**FLAGS)

def inventory_from_snapshot(snapshot):
    instances={}
    for n,row in snapshot["instances"].items():
        instances[n]=dict(master=list(row["master"]),master_type=row["master_type"],pins=row["pins"])
    nets={n:dict(sigtype=row["identity"]["sigtype"],wire=row["encoded"]["wire_present"])for n,row in snapshot["nets"].items()}
    ports={}
    for net,row in snapshot["nets"].items():
        for port,io,sigtype,geometry in row["identity"]["bterms"]:
            require(port not in ports,"duplicate boundary terminal")
            ports[port]=dict(net=net,io=io,sigtype=sigtype)
    result=dict(block=snapshot["block"]["name"],dbu=snapshot["block"]["dbu"],instances=instances,nets=nets,ports=ports)
    validate_inventory(result);return result

def validate_inventory(v):
    exact(set(v),{"block","dbu","instances","nets","ports"},"inventory fields")
    exact(v["block"],"soc_top","top");require(type(v["dbu"])is int and v["dbu"]==1000,"DBU")
    require(type(v["instances"])is dict and type(v["nets"])is dict and type(v["ports"])is dict,"inventory maps")
    for n,row in v["nets"].items():
        name(n);exact(set(row),{"sigtype","wire"},"net fields")
        require(row["sigtype"]in SIGNALS|PG and type(row["wire"])is bool,"net type")
    def terminal(row):
        exact(set(row),{"net","sigtype","io"},"terminal fields")
        require(row["sigtype"]in SIGNALS|PG and row["io"]in IO,"terminal type")
        require(row["net"]is None or row["net"]in v["nets"],"unknown terminal net")
        if row["net"]is not None and row["sigtype"]in PG:exact(v["nets"][row["net"]]["sigtype"],row["sigtype"],"PG ownership")
    for n,row in v["instances"].items():
        name(n);exact(set(row),{"master","master_type","pins"},"instance fields")
        require(type(row["master"])is list and len(row["master"])==2,"master pair")
        for x in row["master"]:name(x)
        name(row["master_type"]);require(type(row["pins"])is dict,"pin map")
        for p,r in row["pins"].items():name(p);terminal(r)
    for n,row in v["ports"].items():name(n);terminal(row)
    return v

def projection(v,include_pg):
    validate_inventory(v);used=set();instances={};excluded_pg=[]
    for n,row in v["instances"].items():
        pins={}
        for p,r in row["pins"].items():
            if not include_pg and r["sigtype"]in PG:excluded_pg.append([n,p]);continue
            pins[p]=dict(r,sigtype=r["sigtype"]if r["sigtype"]in PG else "SIGNAL")
            if r["net"]is not None:used.add(r["net"])
        instances[n]=dict(master=row["master"],master_type=row["master_type"],pins=pins)
    ports={}
    for n,row in v["ports"].items():
        if not include_pg and row["sigtype"]in PG:continue
        ports[n]=dict(row,sigtype=row["sigtype"]if row["sigtype"]in PG else "SIGNAL")
        if row["net"]is not None:used.add(row["net"])
    # Verilog linkers may discard unused net declarations. Preserve their exact
    # physical inventory, but do not invent electrically connected terminals.
    # Verilog carries electrical incidence, not ODB clock/route metadata.
    # Physical CLOCK classification remains protected by the original snapshot gate.
    net_types={n:(v["nets"][n]["sigtype"]if v["nets"][n]["sigtype"]in PG else "SIGNAL")for n in sorted(used)}
    result=dict(block=v["block"],instances=instances,ports=ports,nets=net_types)
    accounting=dict(physical_only_instances=sorted(n for n,row in v["instances"].items()if not any(p["sigtype"]not in PG for p in row["pins"].values())),
      excluded_pg_terminals=sorted(excluded_pg),unreferenced_physical_nets=sorted(set(v["nets"])-used),
      pg_ports_excluded=sorted(n for n,r in v["ports"].items()if not include_pg and r["sigtype"]in PG))
    return result,accounting

def compare_views(original,full,timing,added):
    before=encode(original)
    full_projection,full_accounting=projection(original,True)
    actual,_=projection(full,True);exact(actual,full_projection,"full native Verilog reload topology")
    expected,accounting=projection(original,False)
    actual,_=projection(timing,False);exact(actual,expected,"timing native Verilog reload topology")
    require(type(added)is dict and len(added)==1351,"exact added diode incidence")
    for inst,net in added.items():
        row=original["instances"][inst]
        require(row["master"][1]=="sg13g2_antennanp"and row["master_type"]=="CORE_ANTENNACELL","diode master")
        require(row["pins"]["A"]==dict(net=net,sigtype="SIGNAL",io="INPUT"),"diode A endpoint")
        require(inst in full["instances"]and inst in timing["instances"],"diode retained in both real exports")
    require(encode(original)==before,"no inventory mutation")
    return dict(status="PASS_RELOADED_ROUTED_VIEW_TOPOLOGY_WITHIN_SCOPE",actual_physical_instances=len(original["instances"]),
      full_export_instances=len(full["instances"]),timing_export_instances=len(timing["instances"]),
      full_accounting=full_accounting,timing_accounting=accounting,all1351_added_diode_A_pins_preserved=True,**FLAGS)

def validate_loads(inventory,observations,added):
    validate_inventory(inventory)
    expected={(n,p)for n,row in inventory["instances"].items()for p,r in row["pins"].items()if r["sigtype"]not in PG}
    exact(set(observations),set(CORNERS),"all original PVT load models")
    for corner,payload in observations.items():
        exact(set(payload),{"pins","ports"},"native load census fields")
        rows=payload["pins"]
        require(type(rows)is list,"native load rows");seen=set();paths=set()
        for row in rows:
            exact(set(row),{"instance","pin","net","path","driver","liberty_cell","liberty_pin","min","max"},"load row fields")
            key=(row["instance"],row["pin"]);require(key not in seen and key in expected,"unique exact model terminal");seen.add(key)
            name(row["path"]);require(row["path"]not in paths,"unique STA pin path");paths.add(row["path"])
            wanted=inventory["instances"][key[0]]
            require(row["net"]==wanted["pins"][key[1]]["net"],"model terminal net")
            require(row["liberty_cell"]==wanted["master"][1]and row["liberty_pin"]==key[1],"actual Liberty cell/port")
            require(type(row["driver"])is bool,"driver observation")
            for k in ("min","max"):require(type(row[k])in(int,float)and math.isfinite(row[k])and row[k]>=0,"finite nonnegative native Liberty capacitance")
            if key[0]in added and key[1]=="A":require(row["min"]>0 and row["max"]>0,"nonzero actual diode Liberty load")
        exact(seen,expected,"all signal terminals have actual Liberty models")
        observed_ports={}
        for row in payload["ports"]:
            exact(set(row),{"port","net","path","driver"},"native STA port fields")
            require(row["port"]not in observed_ports and row["port"]in inventory["ports"],"unique STA boundary terminal")
            require(type(row["driver"])is bool,"native STA port driver")
            require(row["net"]==inventory["ports"][row["port"]]["net"],"native STA port net")
            name(row["path"]);require(row["path"]not in paths,"unique STA port path");paths.add(row["path"])
            observed_ports[row["port"]]=row
        exact(set(observed_ports),{n for n,r in inventory["ports"].items()if r["sigtype"]not in PG},"complete STA boundary census")
    return dict(status="PASS_ACTUAL_LIBERTY_TERMINAL_LOAD_CENSUS",terminals_per_corner=len(expected),corners=list(CORNERS),**FLAGS)

def audit_saved_candidate(root,envelope):
    """Caller must authenticate complete transport. This never authorizes execution."""
    validate_envelope(envelope)
    require(pin(inherited.regular(root,FINAL))==envelope["candidate"],"candidate byte pin")
    previous=inherited.audit(root)
    def read(n):return decode(inherited.regular(root,"bulk-postdrt-antenna/"+n).read_bytes())
    before=read("baseline-snapshot.json");inserted=read("insertion-snapshot.json");final=read("restored-snapshot.json")
    checked=lineage(before,inserted,final,read("insertion-plan.json"),read("baseline-antenna-violations.json"))
    return dict(previous=previous,lineage=checked,inventory=inventory_from_snapshot(final),envelope=envelope,**FLAGS)
