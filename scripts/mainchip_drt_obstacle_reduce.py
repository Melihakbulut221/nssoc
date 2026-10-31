#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0
"""Complete reduction of one authenticated preroute observation; never a route decision.

Only the hosted adapter acquires the report. This module does not import CAD,
download inputs, modify a layout, or grant production acceptance.
"""
import collections,json,re
from fractions import Fraction
import mainchip_terminal_readback as q

FLAGS=dict(native_tools_executed=False,routing_executed=False,physical_acceptance=False,
           timing_accepted=False,full_phy_accepted=False,physical_cause_proven=False,
           iteration10_mutable_routes_present=False)
SOURCE_FLAGS=("physical_acceptance","timing_accepted","full_phy_accepted",
              "physical_cause_proven","routing_executed","iteration10_mutable_routes_present")
MEMBERSHIPS=("mutable_cleared_manifest","protected_manifest","not_in_either_manifest")
PIN_KINDS=("iterm-pin","bterm-pin")
WIRE_KINDS=("wire","wire-rect","via")
KINDS=PIN_KINDS+WIRE_KINDS+("special-wire","special-via")
EXPECTED=dict(all_net_count=143820,all_instance_count=154480,
              actual_added_diode_A_connections=1351,complete_selected_marker_count=434,
              complete_endpoint_net_count=373)
API_SHA="6fd2b5881c98fb1c57a7ba774a03862d5c7ce561da8a9e8592afbce0c732aea8"

def integer(x):
    q.require(type(x)is int,"exact integer")
    return x

def text(x):
    q.require(type(x)is str and bool(x),"nonempty text")
    return x

def box(x):
    q.require(type(x)is list and len(x)==4,"complete four-coordinate box")
    a=[integer(v)for v in x]
    q.require(a[0]<=a[2]and a[1]<=a[3],"ordered exact DBU box")
    return a

def relation(a,b):
    a=box(a);b=box(b)
    x=min(a[2],b[2])-max(a[0],b[0]);y=min(a[3],b[3])-max(a[1],b[1])
    return dict(closed_intersection=x>=0 and y>=0,positive_area_intersection=x>0 and y>0,
                x_overlap_dbu=x,y_overlap_dbu=y)

def rid(value):
    q.require(type(value)is list and value and all(type(x)in(str,int)for x in value),"owned scalar record identity")
    return tuple(value)

def false_scope(value):
    q.require(all(value[k]is False for k in SOURCE_FLAGS),"preroute observation acceptance scope")

def validate_scope(scope):
    false_scope(scope)
    q.require(integer(scope["report_records"])==596 and integer(scope["selected_records"])==434 and integer(scope["other_records"])==162,"complete original report census")
    dbu=integer(scope["dbu"]);q.require(dbu>0,"positive DBU")
    markers=scope["markers"];other=scope["other_markers"]
    q.require(type(markers)is list and len(markers)==434 and type(other)is list and len(other)==162,"all scoped records")
    all_rows=markers+other
    q.require(sorted(integer(r["ordinal"])for r in all_rows)==list(range(596)),"exact full original ordinals without duplicates")
    for row in markers:
        q.require(row["kind"]=="Short"and row["layer"]=="Metal2","only selected Metal2 Short records")
        q.require(type(row["nets"])is list and len(row["nets"])==2 and len(set(row["nets"]))==2,"two distinct exact endpoint nets")
        for name in row["nets"]:text(name)
        m=re.fullmatch(r"\tbbox = \((-?\d+\.\d+), (-?\d+\.\d+)\) - \((-?\d+\.\d+), (-?\d+\.\d+)\) on Layer Metal2",row["bbox_text"])
        q.require(m is not None,"original exact bbox grammar")
        numbers=[Fraction(m[i])*dbu for i in range(1,5)]
        q.require(all(v.denominator==1 for v in numbers),"exact DBU grid")
        q.require(box(row["box"])==[v.numerator for v in numbers],"source bbox and exact DBU equality")
        q.require(row["raw"]=="violation type: "+row["kind"]+"\n\tsrcs: "+" ".join("net:"+n for n in row["nets"])+"\n"+row["bbox_text"]+"\n","complete original raw marker record")
    q.require(all(not(r["kind"]=="Short"and r["layer"]=="Metal2")for r in other),"no selected record hidden among other kinds")
    endpoints=sorted({n for row in markers for n in row["nets"]})
    q.require(len(endpoints)==373 and scope["endpoint_names"]==endpoints,"all exact endpoint names")
    return markers,endpoints

def shape_identity(shape,owner):
    q.require(shape["owner"]==owner and shape["kind"]in KINDS,"shape owner/kind")
    text(shape["layer"]);box(shape["box"]);identity=rid(shape["record_id"])
    if shape["kind"]=="iterm-pin":
        q.require(len(identity)==5 and identity[0]=="iterm"and identity[3]=="geometry"and type(identity[4])is int and identity[4]>=0,"ITerm identity")
        q.require(identity[1]==text(shape["instance"])and identity[2]==text(shape["terminal"]),"named ITerm identity")
        q.require(type(shape["master"])is list and len(shape["master"])==2 and all(type(v)is str and v for v in shape["master"])and type(shape["added_diode"])is bool,"ITerm master/diode metadata")
    elif shape["kind"]=="bterm-pin":
        q.require(len(identity)==6 and identity[0]=="bterm"and identity[2]=="bpin"and identity[4]=="box"and all(type(identity[i])is int and identity[i]>=0 for i in(3,5)),"BTerm identity")
        q.require(identity[1]==text(shape["terminal"]),"named BTerm identity")
    elif shape["kind"]in WIRE_KINDS:
        q.require(len(identity)==5 and identity[:4]==("net",owner,"wire","shape")and type(identity[4])is int and identity[4]>=0,"ordinary wire shape identity")
    else:
        q.require(len(identity)==(8 if shape["kind"]=="special-via"else 6)and identity[:3]==("net",owner,"swire")and identity[4]=="box"and all(type(identity[i])is int and identity[i]>=0 for i in(3,5)),"special wire identity")
        if shape["kind"]=="special-via":q.require(identity[6]=="component"and type(identity[7])is int and identity[7]>=0,"special via component identity")
    return identity

def special_component(shape):
    via=shape["via"];origin=shape["origin_xy"]
    q.require(type(origin)is list and len(origin)==2 and all(type(v)is int for v in origin),"exact via origin")
    q.require(shape["via_namespace"]in("tech","block"),"observed native via namespace")
    for key in("name","top","bottom"):text(via[key])
    box(via["box"]);parts=via["components"];q.require(type(parts)is list and parts,"all via components")
    for i,part in enumerate(parts):
        q.require(integer(part["component_ordinal"])==i,"complete ordered via components")
        text(part["layer"]);box(part["box"])
    i=shape["record_id"][-1];q.require(i<len(parts),"existing via component")
    part=parts[i];r=part["box"];x,y=origin
    q.require(shape["layer"]==part["layer"]and shape["box"]==[r[0]+x,r[1]+y,r[2]+x,r[3]+y],"exact component layer and translated geometry")
    return dict(name=via["name"],namespace=shape["via_namespace"],component_ordinal=i,
                component_count=len(parts),origin_xy=origin)

def reduce_report(report,scope,emit_witness):
    markers,endpoints=validate_scope(scope)
    false_scope(report)
    q.require(report["status"]=="COMPLETE_PREROUTE_ENDPOINT_OBSTACLE_OBSERVATION"and report["input_odb_unchanged"]is True and report["terminal_errors"]==[],"complete unchanged-source observation")
    q.require(report["read_only"]is True and report["native_tools_executed"]is True,"actual original observer scope")
    q.require(all(type(report[k])is int and report[k]==v for k,v in EXPECTED.items()),"complete actual observer census")
    q.require(report["dbu_per_micron"]==scope["dbu"]and report["native_api_evidence_sha256"]==API_SHA,"actual DBU/API source")
    q.require(type(report["endpoint_nets"])is dict and sorted(report["endpoint_nets"])==endpoints,"complete endpoint inventory")
    q.require(report["other_markers"]==scope["other_markers"],"all other marker kinds preserved separately")
    q.require(type(report["markers"])is list and len(report["markers"])==len(markers),"all selected marker records")
    needed_pins=collections.defaultdict(set)
    for source,current in zip(markers,report["markers"],strict=True):
        q.require(set(current)==set(source)|{"endpoint_witnesses"}and all(current[k]==v for k,v in source.items()),"unaltered complete source marker")
        q.require(type(current["endpoint_witnesses"])is list,"complete witness list")
        for shape in current["endpoint_witnesses"]:
            q.require(shape["owner"]in source["nets"],"only marker endpoint witness")
            key=shape_identity(shape,shape["owner"])
            if shape["kind"]in PIN_KINDS:needed_pins[shape["owner"]].add(key)
    pin_lookup={};compact_endpoints=[];memberships=collections.Counter();pins_checked=0
    for name in endpoints:
        row=report["endpoint_nets"][name];identity=row["identity"];encoded=row["encoded"]
        q.require(identity["name"]==name,"exact endpoint identity");sigtype=text(identity["sigtype"])
        membership=row["manifest_membership"];q.require(membership in MEMBERSHIPS,"explicit manifest membership");memberships[membership]+=1
        q.require(type(encoded["wire_present"])is bool and type(encoded["paths"])is list,"complete encoded wire metadata")
        text(encoded["metadata"])
        classes=collections.Counter(text(v)for v in encoded["paths"])
        if membership=="mutable_cleared_manifest":
            q.require(encoded==dict(wire_present=False,metadata="ROUTED",paths=[]),"mutable iteration10 routes must remain absent")
        counts=row["native_geometry_counts"]
        q.require(type(counts)is dict and all(k in KINDS and type(v)is int and v>=0 for k,v in counts.items()),"complete recognized geometry-kind counts")
        q.require(integer(row["native_geometry_records"])==sum(counts.values()),"all geometry record count")
        q.require(type(row["native_geometry_sha256"])is str and re.fullmatch("[0-9a-f]{64}",row["native_geometry_sha256"])is not None,"original complete geometry digest")
        pins=row["all_endpoint_pin_geometry"];q.require(type(pins)is list and len(pins)==sum(counts.get(k,0)for k in PIN_KINDS),"complete endpoint pin record count")
        seen=set();actual=collections.Counter()
        for shape in pins:
            q.require(shape["kind"]in PIN_KINDS,"pin-only inventory")
            key=shape_identity(shape,name);q.require(key not in seen,"unique endpoint pin record")
            seen.add(key);actual[shape["kind"]]+=1;pins_checked+=1
            if key in needed_pins[name]:pin_lookup[(name,key)]=shape
        q.require(all(actual[k]==counts.get(k,0)for k in PIN_KINDS),"each complete pin-kind count")
        q.require(needed_pins[name]<=seen,"every pin witness exists in complete pin inventory")
        compact_endpoints.append(dict(name=name,signal_type=sigtype,manifest_membership=membership,
          encoded_wire_present=encoded["wire_present"],route_metadata=encoded["metadata"],
          encoded_class_counts=dict(sorted(classes.items())),native_geometry_records=row["native_geometry_records"],
          native_geometry_counts=counts,native_geometry_sha256=row["native_geometry_sha256"],
          complete_pin_records=len(pins),wire_raw_pin=row["wire_raw_pin"],wire_projection_pin=row["wire_projection_pin"]))
    endpoint_index={r["name"]:r for r in compact_endpoints}
    compact_markers=[];total=0;global_groups=collections.Counter()
    for marker_index,(source,current)in enumerate(zip(markers,report["markers"],strict=True)):
        seen=set();groups=collections.Counter();per_owner=collections.Counter()
        for witness_index,shape in enumerate(current["endpoint_witnesses"]):
            name=shape["owner"];key=shape_identity(shape,name)
            q.require((name,key)not in seen,"no duplicate source witness record");seen.add((name,key))
            observed=relation(source["box"],shape["box"])
            q.require(observed["closed_intersection"]is True and shape["relation"]==observed,"exact complete recorded intersection")
            same=shape["layer"]==source["layer"];pin=shape["kind"]in PIN_KINDS
            q.require(same or pin,"cross-layer projection allowed only for pins")
            relation_name="same_layer"if same else"xy_projection_only_different_layer"
            q.require(shape["layer_relation"]==relation_name and shape["observation"]=="candidate_endpoint_obstacle_evidence_not_root_cause","explicit limited physical interpretation")
            base={k:v for k,v in shape.items()if k not in("relation","layer_relation","observation")}
            if pin:q.require(base==pin_lookup[(name,key)],"witness equals actual complete endpoint pin record")
            ep=endpoint_index[name];details={}
            if shape["kind"]in WIRE_KINDS:
                encoded=report["endpoint_nets"][name]["encoded"]
                q.require(encoded["wire_present"]is True and shape["route_metadata"]==encoded["metadata"]and shape["encoded_classes"]==encoded["paths"],"ordinary wire metadata equality")
                details=dict(route_metadata=shape["route_metadata"],encoded_class_counts=ep["encoded_class_counts"])
            elif shape["kind"]=="special-via":details=dict(via=special_component(shape))
            if shape["kind"]in WIRE_KINDS:
                evidence="ordinary-wire-FIXED"if shape["route_metadata"]=="FIXED"else"ordinary-wire-other-metadata"
            elif shape["kind"]in("special-wire","special-via"):
                evidence="special-PG"if ep["signal_type"]in("POWER","GROUND")else"special-other-signal-type"
            else:evidence=shape["kind"]
            overlap="positive-area"if observed["positive_area_intersection"]else"boundary-only"
            group="|".join((ep["manifest_membership"],evidence,relation_name,overlap))
            groups[group]+=1;global_groups[group]+=1;per_owner[name]+=1;total+=1
            emit_witness(dict(source_marker_index=marker_index,source_marker_ordinal=source["ordinal"],
              source_witness_index=witness_index,owner=name,other_endpoint=next(n for n in source["nets"]if n!=name),
              manifest_membership=ep["manifest_membership"],signal_type=ep["signal_type"],record_id=shape["record_id"],
              kind=shape["kind"],layer=shape["layer"],box=shape["box"],relation=observed,layer_relation=relation_name,
              evidence_group=evidence,source_pointer="/markers/"+str(marker_index)+"/endpoint_witnesses/"+str(witness_index),
              details=details))
        compact_markers.append(dict(source_marker_index=marker_index,ordinal=source["ordinal"],nets=source["nets"],
          layer=source["layer"],box=source["box"],bbox_text=source["bbox_text"],
          endpoint_membership={n:endpoint_index[n]["manifest_membership"]for n in source["nets"]},
          all_witnesses=len(current["endpoint_witnesses"]),witnesses_by_owner=dict(sorted(per_owner.items())),
          evidence_groups=dict(sorted(groups.items())),no_observed_endpoint_intersection=not current["endpoint_witnesses"]))
    q.require(total==sum(m["all_witnesses"]for m in compact_markers),"every witness reduced exactly once")
    summary=dict(status="COMPLETE_AUTHENTICATED_PREROUTE_OBSTACLE_REDUCTION",
      selected_markers=len(compact_markers),endpoints=len(compact_endpoints),other_marker_records=len(report["other_markers"]),
      complete_pin_records_checked=pins_checked,complete_witness_records=total,endpoint_membership_counts=dict(sorted(memberships.items())),
      evidence_groups=dict(sorted(global_groups.items())),original_observer_census=EXPECTED,
      original_observer_api_sha256=API_SHA,dbu_per_micron=scope["dbu"],geometry_computed=True,
      all_source_marker_and_witness_records_retained=True,
      interpretation="Exact observed preroute endpoint intersections. Mutable iteration10 route geometry is absent; fixed/special/pin evidence is not proof of the original violation cause or permission to mutate protected nets.",
      **FLAGS)
    return dict(summary=summary,endpoints=compact_endpoints,markers=compact_markers,other_markers=report["other_markers"])
