#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0
"""Existing-diode additive route contract. No native or execution authority."""
import hashlib,json,re
from pathlib import Path
import mainchip_single_antenna_trial as legacy
import mainchip_original_clock_restoration as c
import mainchip_fixed_clock_signal_repair as old
import mainchip_two_signal_geometry as geometry
import mainchip_net459_connectivity as graph
import mainchip_full_antenna_report as antenna
import mainchip_antenna_escape_window as diagnostic
MEMBER=diagnostic.MEMBER
RUN=diagnostic.RUN
SOURCE=diagnostic.SOURCE
RELEASE=diagnostic.RELEASE
TAG=diagnostic.TAG
ASSETS=diagnostic.ASSETS
producer_binding=diagnostic.producer_binding

ROOT=Path(__file__).resolve().parents[1]
NET=legacy.NET
NEW=legacy.NEW
SINK=legacy.SINK
INPUT=dict(bytes=213428829,sha256="72d382ab18e905d13fef8145b70944e681a7a50c16bad0848616652fa93fc0ee")
DIODE=dict(name=NEW,master="sg13g2_antennanp",location=[98880,502740],orientation="MX")
MANIFEST="scripts/mainchip-multilayer-antenna-trial-pins.json"
SEED=(
 ("Metal1",160,(99600,505680),(101280,505680),"tech:3"),
 ("Metal2",200,(101280,505680),(101280,506520),"tech:22"),
 ("Metal3",200,(101280,506520),(97440,506520),"tech:22"),
)
VIA_DEFINITIONS={
 "tech:3":dict(name="Via1_XY",bottom="Metal1",top="Metal2",box=[-145,-145,145,145],components=[
  dict(layer="Metal1",box=[-145,-105,145,105],component_ordinal=0),
  dict(layer="Via1",box=[-95,-95,95,95],component_ordinal=1),
  dict(layer="Metal2",box=[-100,-145,100,145],component_ordinal=2)]),
 "tech:22":dict(name="Via2_YX",bottom="Metal2",top="Metal3",box=[-145,-145,145,145],components=[
  dict(layer="Metal2",box=[-105,-145,105,145],component_ordinal=0),
  dict(layer="Via2",box=[-95,-95,95,95],component_ordinal=1),
  dict(layer="Metal3",box=[-145,-100,145,100],component_ordinal=2)]),
}
FROZEN={
 "scripts/mainchip_single_antenna_trial.py":"0e0a81e6559b57254de15da506d53cc90404c47354ed0682070cc744f4d22b97",
 "scripts/mainchip_original_clock_restoration.py":"fd69f21bae8beed99f1886accec86a9b35bfa7db5437cdb792813a76e60f9194",
 "scripts/mainchip_fixed_clock_signal_repair.py":"fefe067abf459cd9827dcd89113eec3a63b948bf7a46146fdfe1f902e69f7c2d",
 "scripts/mainchip_two_signal_geometry.py":"5f044322e06af04ebb9590e7011dc8ed7e31969e226153ba6e829c1d69940072",
 "scripts/mainchip_net459_connectivity.py":"bb7bd69687272f10b188030c0d78004377ab9de83145d8c2314070e014478b6b",
 "scripts/mainchip_full_antenna_report.py":"c59f6fbb0ac4e9ab6acb4b13637539356f4d39fb52bd8a051e7f41139cd70195",
}
encode=legacy.encode
pin=legacy.pin
run_phase=legacy.run_phase
patch_def=c.patch_def

def exact(a,b,reason):
    assert encode(a)==encode(b),reason

def source_guard():
    m=json.loads(c.regular(ROOT/MANIFEST).read_bytes())
    assert m["schema"]=="multilayer-antenna-trial-pins-v1","manifest schema"
    files=m["files"]
    required=set(FROZEN)|{"scripts/mainchip_multilayer_antenna_trial.py","scripts/check_mainchip_multilayer_antenna_trial.py"}
    assert required<=files.keys(),"required source pins"
    for name,row in files.items():
        assert type(name)is str and not name.startswith("/")and ".."not in Path(name).parts,"source path"
        exact(pin(c.regular(ROOT/name).read_bytes()),row,"source: "+name)
    for name,digest in FROZEN.items():assert files[name]["sha256"]==digest,"frozen helper: "+name
    return m

def normalized_def(raw):
    """Retain every component, connection, property and other wire; exclude only target routing."""
    parsed=c.parse_def(raw);record=parsed["records"][NET];a,b=parsed["spans"][NET]
    head=old.wire_head(record)
    assert re.findall(rb"\+[ \t]+[A-Z_]+",record[len(head):])==[b"+ ROUTED"],"target route properties"
    raw=raw[:a]+head+b" + ROUTED __EXISTING_DIODE_TARGET_WIRE__ ;\n"+raw[b:]
    header=list(re.finditer(rb"(?m)^COMPONENTS ([0-9]+) ;\n",raw))
    assert len(header)==1 and int(header[0].group(1))==153129,"current instance census"
    end=raw.index(b"END COMPONENTS\n",header[0].end())
    body=raw[header[0].end():end]
    starts=list(re.finditer(rb"(?m)^[ \t]*- ([^\s]+)(?=\s)",body))
    assert len(starts)==153129 and not body[:starts[0].start()].strip(),"component records"
    names=[m.group(1).decode("ascii")for m in starts]
    assert len(set(names))==len(names)and names.count(NEW)==1,"existing diode identity"
    digest=hashlib.sha256();cursor=0
    for match in re.finditer(rb'"(?:\\.|[^"\\])*"|[^\s"]+',raw):
        assert not raw[cursor:match.start()].strip(),"unparsed DEF token"
        cursor=match.end();token=match.group();token.decode("ascii")
        digest.update(len(token).to_bytes(8,"big"));digest.update(token)
    assert not raw[cursor:].strip(),"unparsed trailing DEF token"
    return dict(sha256=digest.hexdigest(),excluded_target_route=NET,
      removed_components=[],removed_connection_counts={})

def append_branch(record):
    parsed=c.parse_def(b"NETS 1 ;\n"+record+b"END NETS\n")
    assert list(parsed["records"])==[NET]and parsed["records"][NET]==record,"exact single target record"
    head=old.wire_head(record);wire=record[len(head):]
    assert wire.count(b";")==1 and wire.rstrip().endswith(b";"),"wire terminator"
    assert re.findall(rb"\+[ \t]+[A-Z_]+",wire)==[b"+ ROUTED"],"wire properties"
    extra=[]
    for layer,width,a,b,key in SEED:
        assert all(type(v)is int and v%5==0 for v in (*a,*b))
        assert (a[0]==b[0])!=(a[1]==b[1])
        extra.append(" NEW %s ( %d %d ) ( %d %d ) %s\n"%(layer,*a,*b,VIA_DEFINITIONS[key]["name"]))
    i=record.index(b";")
    return record[:i]+"".join(extra).encode("ascii")+record[i:]

def expected_added_shapes(catalog):
    """Independent declared material; native decoder remains the actual observation."""
    geometry.validate_catalog(catalog)
    for key,value in VIA_DEFINITIONS.items():exact(catalog["vias"][key],value,"via definition: "+key)
    result=[]
    for layer,width,a,b,key in SEED:
        lr=catalog["layers"][layer]
        assert type(lr["width"])is int and lr["width"]==width,"default layer width"
        assert type(lr["wrong_way_width"])is int and lr["wrong_way_width"]==width,"wrong-way layer width"
        h=width//2
        box=[min(a[0],b[0])-h,min(a[1],b[1])-h,max(a[0],b[0])+h,max(a[1],b[1])+h]
        result.append(dict(kind="wire",layer_key=layer,layer=layer,box=box,
          from_xy=list(a),to_xy=list(b),previous_extension=None,current_extension=None,
          half_width=h,default_extension=h))
        via=VIA_DEFINITIONS[key]
        for ordinal,row in enumerate(via["components"]):
            q=row["box"];x,y=b
            result.append(dict(kind="via",layer_key=row["layer"],layer=row["layer"],
              box=[q[0]+x,q[1]+y,q[2]+x,q[3]+y],via_key=key,via_name=via["name"],
              component_ordinal=ordinal,component_identity=[key,ordinal],origin_xy=list(b),
              definition_box=list(q),definition_bbox=list(via["box"])))
    assert len(result)==12
    return result

def material(shapes):
    result=[]
    for row in shapes:
        assert type(row["opcode_index"])is int and row["opcode_index"]>=0,"shape opcode"
        result.append({k:v for k,v in row.items()if k!="opcode_index"})
    return result

def restore_target_catalog(record):
    """Restore native integer OIDs after the authenticated JSON evidence transport."""
    keys=record["projection"]["catalog"]["path_layers"]
    assert all(type(k)is str and k==str(int(k))and int(k)>0 for k in keys),"serialized native layer OID"
    record["projection"]["catalog"]["path_layers"]={int(k):v for k,v in keys.items()}
    geometry.validate_catalog(record["projection"]["catalog"])
    return record

def validate_route_delta(before,after):
    for key in("scoped_identity","wire_identity","metadata_class","sigtype"):
        exact(before[key],after[key],"target identity: "+key)
    exact(before["scoped_identity"],["net",NET],"target net")
    exact(before["wire_identity"],["net",NET,"wire"],"target wire")
    assert before["metadata_class"]=="ROUTED"and before["sigtype"]=="SIGNAL","target classes"
    key=lambda r:tuple(r["scoped_identity"])
    exact(sorted(before["pins"],key=key),sorted(after["pins"],key=key),"all baseline pins")
    identities=[r["scoped_identity"]for r in before["pins"]]
    assert identities.count(["iterm",NEW,"A"])==1 and identities.count(["iterm",*SINK])==1,"required baseline pins"
    bp=before["projection"];ap=after["projection"]
    assert bp["shape_count"]==len(bp["shapes"])==40,"original forty shapes"
    assert ap["shape_count"]==len(ap["shapes"])==52,"exact twelve additions"
    exact(material(ap["shapes"][:40]),material(bp["shapes"]),"original target material")
    # The baseline records only vias actually used by its wire.
    # New via definitions are independently admitted on the candidate catalog.
    geometry.validate_catalog(bp["catalog"])
    expected_added_shapes(ap["catalog"])
    extra=ap["shapes"][40:]
    exact(material(extra),expected_added_shapes(ap["catalog"]),"exact added material")
    previous={r["opcode_index"]for r in ap["shapes"][:40]}
    groups=[]
    for offset in(0,4,8):
        wire=extra[offset];via=extra[offset+1:offset+4]
        assert all(r["opcode_index"]not in previous for r in [wire]+via),"new opcode overlaps old"
        assert len({r["opcode_index"]for r in via})==1,"one native via opcode"
        assert wire["opcode_index"]!=via[0]["opcode_index"],"wire/via opcode collision"
        groups.extend([wire["opcode_index"],via[0]["opcode_index"]])
    assert len(set(groups))==6,"distinct native path elements"
    return dict(original_shapes=40,added_wires=3,added_via_components=9,
      baseline_target_pins_unchanged=True,global_instance_invariance_required=True,
      scope="Target material and pins only; caller authenticates native/source/global invariants.",physical_acceptance=False)

def validate_connectivity(actual):
    result={}
    for mode in("positive_area","closed_boundary"):
        observed=graph.observe(actual["projection"]["shapes"],actual["pins"],mode)
        assert observed["all_wire_material_one_component"],"wire connectivity: "+mode
        assert observed["all_pins_share_one_wire_component"],"pin connectivity: "+mode
        assert all(len(r["wire_components"])==1 for r in observed["pins"]),"unique pin access"
        result[mode]=observed
    return result

def validate_antenna(baseline,candidate,historical_violations,drc_count):
    """Parsed complete reports supplied by unchanged native antenna/DRC collection."""
    assert type(drc_count)is int and drc_count>=0,"DRC count"
    for label,row in(("baseline",baseline),("candidate",candidate)):
        counts=row["counts"];vv=row["violations"]
        assert type(vv)is list and all(v["violated"]is True for v in vv),"complete violations: "+label
        for name in("target_count","target_violation","full_count"):
            assert type(counts[name])is int and counts[name]>=0,"antenna count: "+label
        assert counts["target_count"]in(0,1)and counts["target_violation"]in(0,1),"single-target boolean counts"
        assert counts["full_count"]==len({v["net"]for v in vv}),"full report net count"
        target=any(v["net"]==NET for v in vv)
        assert (counts["target_count"]>0)==target and bool(counts["target_violation"])==target,"target/full report join"
    semantics=lambda vv:sorted((antenna.semantics(v)for v in vv if v["net"]!=NET),key=encode)
    expected=semantics(historical_violations)
    exact(semantics(baseline["violations"]),expected,"baseline other antenna semantics")
    exact(semantics(candidate["violations"]),expected,"candidate other antenna semantics")
    passed=drc_count==0 and candidate["counts"]["target_count"]==candidate["counts"]["target_violation"]==0
    return dict(bounded_trial_passed=passed,candidate_rejected=not passed,
      baseline_target_count=baseline["counts"]["target_count"],other_violation_semantics_unchanged=True,
      physical_acceptance=False,timing_accepted=False,full_phy_accepted=False)
