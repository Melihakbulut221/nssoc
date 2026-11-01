#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0
"""Compare fresh wire evidence with the complete original device/terminal census."""
import collections
import copy
import hashlib
import json

CENSUS={"sg13_lv_nmos":50,"npn13G2":124,"rppd":98,"cap_cmim":7,"ptap1":221}
COUNTS={"native_device_count":500,"native_terminal_count":1446,"wire_component_count":113,
        "native_net_count":238,"native_electrical_net_count":114}
DISPOSITIONS={"ACTUAL_TERMINAL_METAL_POINT_REFERENCE":953,
              "RETAINED_INTRINSIC_BODY_NO_SUBSTRATE_RESISTANCE":493}

def canonical(value):
    return json.dumps(value,sort_keys=True,separators=(",",":"),allow_nan=False)

def graph_index(graph):
    for key,value in COUNTS.items():assert type(graph[key]) is int and graph[key]==value,(key,graph[key])
    assert graph["native_devices"]==CENSUS and len(graph["native_ports"])==len(set(graph["native_ports"]))==25
    assert graph["no_component_union_by_native_label"] is graph["no_wire_geometry_change"] is True
    assert graph["wire_rc_extracted"] is graph["full_pex_qualified"] is graph["substrate_r_modeled"] is False
    nets=graph["native_net_coverage"];components=graph["wire_components"]
    assert len(nets)==238 and len(components)==113
    by_cluster={};terminals={};ports={};component_keys={};component_rows={}
    for row in nets:
        cluster=row["native_cluster"];assert type(cluster) is int and cluster not in by_cluster
        ts=[(v["device"],v["model"],v["terminal"]) for v in row["device_terminals"]]
        assert len(ts)==len(set(ts)) and len(row["public_ports"])==len(set(row["public_ports"]))
        for t in ts:assert t not in terminals;terminals[t]=cluster
        for p in row["public_ports"]:assert p not in ports;ports[p]=cluster
        key=canonical({"terminals":sorted(ts),"public_ports":sorted(row["public_ports"])})
        by_cluster[cluster]={"key":key,"name":row["name"],"row":row}
        owners=row["wire_components"];assert len(owners)<=1
        if not ts:assert row["metal_area_dbu2"]==0 and not row["public_ports"] and not owners
        if row["metal_area_dbu2"]:assert len(owners)==1
        for component in owners:
            assert type(component) is int and component not in component_keys
            component_keys[component]=key
    assert len(terminals)==1446 and len(ports)==25 and set(ports)==set(graph["native_ports"])
    assert len(component_keys)==113
    assert len({r["key"] for r in by_cluster.values() if r["row"]["device_terminals"]})==114
    for row in components:
        component=row["component"];assert component not in component_rows and component in component_keys
        cluster=row["native_cluster"];assert cluster in by_cluster
        assert component_keys[component]==by_cluster[cluster]["key"]
        assert row["native_name"]==by_cluster[cluster]["name"]
        component_rows[component]=row
    assert set(component_rows)==set(component_keys)
    return {"nets":by_cluster,"terminals":terminals,"ports":ports,"component_keys":component_keys,
            "component_rows":component_rows}

def normalize(value,index):
    if isinstance(value,list):return [normalize(v,index) for v in value]
    if not isinstance(value,dict):return value
    result={k:normalize(v,index) for k,v in value.items()}
    if "native_cluster" in value:
        cluster=value["native_cluster"];assert cluster in index["nets"]
        key=index["nets"][cluster]["key"];result["native_cluster"]=key
        for field in ("native_net","net"):
            if field in value:
                assert value[field]==index["nets"][cluster]["name"]
                result[field]=key
    if "wire_component" in value:
        component=value["wire_component"];assert component in index["component_keys"]
        result["wire_component"]=index["component_keys"][component]
        if "native_cluster" in result:assert result["native_cluster"]==result["wire_component"]
    return result

def normalized_locations(locations,index):
    assert locations["model_census"]==CENSUS and locations["native_terminal_count"]==1446
    devices=locations["devices"];assert len(devices)==500
    ids=[d["native_id"] for d in devices];assert all(type(v) is int for v in ids) and sorted(ids)==list(range(1,501))
    seen=set()
    for device in devices:
        names=[t["name"] for t in device["terminals"]];assert len(names)==len(set(names))
        for terminal in device["terminals"]:
            key=(device["native_id"],device["model"],terminal["name"])
            assert key not in seen and key in index["terminals"] and index["terminals"][key]==terminal["native_cluster"]
            seen.add(key)
    assert seen==set(index["terminals"])
    result=normalize({k:v for k,v in locations.items() if k!="inputs"},index)
    result["devices"]=sorted(result["devices"],key=lambda d:d["native_id"])
    return result

def normalized_anchors(anchors,index):
    assert anchors["dispositions"]==DISPOSITIONS
    assert anchors["logical_anchor_count"]==anchors["physical_anchor_count"]==978 and anchors["public_ports"]==25
    assert len(anchors["rows"])==1446 and len(anchors["anchors"])==978
    assert anchors["point_quantization_used_to_merge"] is False
    seen=set()
    for row in anchors["rows"]:
        key=(row["device"],row["model"],row["terminal"])
        assert key not in seen and key in index["terminals"] and index["terminals"][key]==row["native_cluster"]
        seen.add(key)
    assert seen==set(index["terminals"])
    result=normalize({k:v for k,v in anchors.items() if k!="inputs"},index)
    result["rows"]=sorted(result["rows"],key=lambda r:(r["device"],r["terminal"]))
    result["anchors"]=sorted(result["anchors"],key=lambda r:r["label"])
    return result

def compare(original,fresh,require_added_material=True):
    old_graph,old_locations,old_anchors=original
    new_graph,new_locations,new_anchors=fresh
    old=graph_index(old_graph);new=graph_index(new_graph)
    assert old_graph["status"]==new_graph["status"]
    assert old_graph["native_ports"]==new_graph["native_ports"]
    assert sorted(v["key"] for v in old["nets"].values())==sorted(v["key"] for v in new["nets"].values()),"Native terminal/public-port partition changed"
    assert canonical(normalized_locations(old_locations,old))==canonical(normalized_locations(new_locations,new)),"Original device geometry, parameters, identity or terminals changed"
    assert canonical(normalized_anchors(old_anchors,old))==canonical(normalized_anchors(new_anchors,new)),"Original terminal/public reference points changed"
    target_keys={old["nets"][old["terminals"][(device,"npn13G2","E")]]["key"] for device in (61,115)}
    assert len(target_keys)==2
    old_components={old["component_keys"][k]:v for k,v in old["component_rows"].items()}
    new_components={new["component_keys"][k]:v for k,v in new["component_rows"].items()}
    assert set(old_components)==set(new_components)
    changed=[]
    for key,before in old_components.items():
        after=new_components[key]
        assert set(before["layers"])==set(after["layers"])
        for layer,value in before["layers"].items():
            if key in target_keys and layer in ("126","134"):
                assert after["layers"][layer]["area_dbu2"]>=value["area_dbu2"]
                if require_added_material and layer=="134":
                    assert after["layers"][layer]["area_dbu2"]>value["area_dbu2"],"No added owned TM2 bus"
                if after["layers"][layer]!=value:changed.append({"partition_sha256":hashlib.sha256(key.encode()).hexdigest(),"layer":int(layer),"before":value,"after":after["layers"][layer]})
            else:assert canonical(after["layers"][layer])==canonical(value),"Foreign or lower-metal component changed"
    assert set(old_graph["layers"])==set(new_graph["layers"])
    for layer,value in old_graph["layers"].items():
        if layer in ("126","133","134"):
            assert new_graph["layers"][layer]["area_dbu2"]>=value["area_dbu2"]
            if require_added_material and layer in ("133","134"):assert new_graph["layers"][layer]["area_dbu2"]>value["area_dbu2"]
        else:assert canonical(new_graph["layers"][layer])==canonical(value),("Unapproved layer changed",layer)
    return {"status":"PASS_ALL500_DEVICES1446_TERMINALS978_POINTS_AND_FULL_NATIVE_PARTITION_UNCHANGED",
      "native_device_count":500,"native_terminal_count":1446,"logical_anchor_count":978,
      "native_net_count":238,"electrical_net_count":114,"wire_components":113,
      "renumbering_policy":"Only cluster/component identifiers and their derived net spellings are replaced by exact full terminal/public-port partitions; all device IDs, intrinsic geometry, parameters and anchor identities remain exact.",
      "changed_owned_component_layers":changed,"added_material_required":require_added_material,
      "physical_accepted":False,"electrical_accepted":False,"qualified_pex":False}

def renumber_fixture(original):
    """Explicit structural JSON fixture; does not represent a new native extraction."""
    graph,locations,anchors=copy.deepcopy(original)
    def change(value):
        if isinstance(value,list):return [change(v) for v in value]
        if not isinstance(value,dict):return value
        result={k:change(v) for k,v in value.items()}
        if "native_cluster" in result:result["native_cluster"]+=1000
        if "wire_component" in result:result["wire_component"]+=2000
        return result
    graph=change(graph);locations=change(locations);anchors=change(anchors)
    for row in graph["wire_components"]:row["component"]+=2000
    for row in graph["native_net_coverage"]:row["wire_components"]=[v+2000 for v in row["wire_components"]]
    return graph,locations,anchors
