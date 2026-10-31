#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0
"""Current composed CDR metal ownership and endpoint diagnosis, never PHY acceptance."""
from collections import Counter,defaultdict
from decimal import Decimal
from fractions import Fraction
import ast,hashlib,math,shlex
from pathlib import Path
from types import SimpleNamespace
import build_pcie_local_vco_hybrid_v6 as parser
FLAGS=dict(physical_acceptance=False,timing_accepted=False,full_phy_accepted=False,
 electrical_accepted=False,qualified_pex=False,causality_proven=False,geometry_changed=False)
PRECISE_PREFIX="native/current-mim-bundle/mim/precise/"
MODEL_SHA="5d4de0f4c9fcd6d6aa18d6e1f007a8dab68f1c72efc925d9c4064ca1e4209fed"

def require(value,message):
    if not value:raise AssertionError(message)

def element_rows(text):
    rows=parser.statements(text)
    require(rows[0][0].lower()==".subckt"and rows[-1][0].lower()==".ends","one complete subcircuit")
    names=[r[0].lower()for r in rows[1:-1]]
    require(len(names)==len(set(names)),"unique element names")
    require(all(r[0][0].upper()in("R","C","X")for r in rows[1:-1]),"complete known element classes")
    return rows

def bind_export(model,wire,contract):
    """All raw R/C tokens and intrinsic cards, not matching aggregate counts alone."""
    got=element_rows(model);raw=element_rows(wire);mapping=contract["wire_node_map"]
    require(got[0][2:]==contract["interface"],"actual composed interface")
    require(len(set(v.lower()for v in mapping.values()))==len(mapping),"injective current wire-node mapping")
    actual={r[0].lower():r for r in got[1:-1]}
    native=[r for r in raw[1:-1]if r[0][0].upper()in("R","C")]
    require(Counter(r[0][0].upper()for r in native)=={k:contract["counts"][k]for k in("R","C")},"all raw R/C")
    require({r[0].lower()for r in native}=={k for k,v in actual.items()if v[0][0].upper()in("R","C")},"exact passive element census")
    edges=[]
    for row in native:
        require(len(row)==4 and row[1]!=row[2],"raw two-terminal element")
        expected=[row[0],mapping[row[1]],mapping[row[2]],row[3]]
        require(actual[row[0].lower()]==expected,"exact current raw token projection: "+row[0])
        value=parser.number(row[3]);require(value.is_finite(),"finite raw passive")
        if row[0][0].upper()=="R":
            require(value>0,"positive actual metal resistor")
            edges.append((row[0],expected[1].lower(),expected[2].lower(),float(value)))
        else:require(value>=0,"nonnegative actual capacitance")
    expected_cards=contract["native_extracted_mim_cards_projected_once"]
    require(Counter(tuple(r)for r in raw[1:-1]if r[0][0].upper()=="X")==
      Counter(tuple(d["export"])for d in expected_cards),"exact native MIM card set")
    require(len([r for r in got[1:-1]if r[0][0].upper()=="X"])==contract["counts"]["devices"],"all composed devices")
    return edges,native

def ownership(edges,contract,anchors):
    """Every metal component has exactly one source-bound native conductor owner."""
    parent={}
    def root(node):
        parent.setdefault(node,node)
        while parent[node]!=node:parent[node]=parent[parent[node]];node=parent[node]
        return node
    for name,a,b,r in edges:
        require(a!=b and math.isfinite(r)and r>0,"finite positive nonalias metal edge")
        parent[root(a)]=root(b)
    physical={a["label"]:a for a in anchors["anchors"]}
    require(len(physical)==len(anchors["anchors"]),"unique current anchors")
    owners=defaultdict(set);logical_components=defaultdict(set);terminals={}
    def add(label,node,owner):
        key=node.lower();require(key in {v.lower()for v in contract["wire_node_map"].values()},"unknown mapped metal terminal: "+label)
        component=root(key);owner=tuple(owner)
        owners[component].add(owner);logical_components[owner].add(component)
        require(label not in terminals,"duplicate metal anchor")
        terminals[label]=dict(node=key,owner=list(owner),component=component)
    for device in contract["device_records"]:
        for term in device["terminals"]:
            label=term["anchor"]
            if label is None:continue
            a=physical[label]
            require(a["native_cluster"]==term["native_cluster"],"actual contact cluster")
            require(contract["wire_node_map"][label]==term["node"],"actual composed terminal node")
            add(label,term["node"],(term["native_cluster"],term["native_net"]))
    public={}
    for label,a in physical.items():
        if "public_port"in a["detail"]:
            port=a["detail"]["public_port"];require(port not in public,"unique public anchor")
            public[port]=label
            require(label=="P_"+port and contract["wire_node_map"][label]==port,"actual public node")
            add(label,port,(a["native_cluster"],port))
    require(set(owners)=={root(n)for n in parent},"all metal components anchored")
    require(all(len(x)==1 for x in owners.values()),"cross-conductor metal short")
    require(all(len(x)==1 for x in logical_components.values()),"split native conductor")
    return dict(terminals=terminals,public=public,components=len(owners),
      owners={component:list(next(iter(value)))for component,value in owners.items()})

def requested_pairs(contacts):
    t=contacts["terminals"];pairs=[]
    def add(name,a,b):
        require(a in t and b in t,"requested actual metal terminals")
        require(t[a]["owner"]==t[b]["owner"]and t[a]["component"]==t[b]["component"],"requested same conductor")
        require(t[a]["node"]!=t[b]["node"],"distinct actual finite-contact nodes")
        pairs.append(dict(name=name,from_anchor=a,to_anchor=b,from_node=t[a]["node"],to_node=t[b]["node"],owner=t[a]["owner"]))
    for upper,selectors in(((54,56),(61,62)),((106,108),(115,116))):
        for first in upper:
            for second in selectors:add("upper_E_to_selector_C_"+str(first)+"_"+str(second),f"T{first:03d}_E",f"T{second:03d}_C")
    for mos,selectors in((range(3,7),(61,62)),(range(32,36),(115,116))):
        for first in mos:
            for second in selectors:add("tail_D_to_selector_E_"+str(first)+"_"+str(second),f"T{first:03d}_D",f"T{second:03d}_E")
    for port,plate,collectors in(("vip","mim_top",(168,171)),("vin","mim_btm",(167,172))):
        label=contacts["public"][port];cap="T279_"+plate
        add("macro_"+port+"_to_filter",label,cap)
        for first in collectors:
            collector=f"T{first:03d}_C"
            add("VI_collector_"+str(first)+"_to_filter",collector,cap)
            add("macro_"+port+"_to_VI_collector_"+str(first),label,collector)
    require(len(pairs)==34 and len({x["name"]for x in pairs})==34,"all30 mandatory and4 optional distinct requested pairs")
    return pairs

def raw_geometry(res_ext,ext,mag,anchors,raw_edges):
    nodes={};resistors=defaultdict(list)
    for line in res_ext.splitlines():
        row=shlex.split(line)
        if not row:continue
        if row[0]=="rnode":
            require(len(row)==7 and row[1]not in nodes,"unique complete rnode")
            nodes[row[1]]=[int(row[4]),int(row[5])]
        elif row[0]=="resist":
            require(len(row)==4,"raw resistor fields")
            value=float(row[3]);require(math.isfinite(value)and value>0,"finite positive raw resistor")
            resistors[tuple(sorted(row[1:3]))].append(value)
    available={k:list(v)for k,v in resistors.items()}
    for row in raw_edges:
        if row[0][0].upper()!="R":continue
        _,a,b,value=row;key=tuple(sorted((a,b)));v=float(parser.number(value))
        matches=[i for i,x in enumerate(available.get(key,[]))if math.isclose(x,v,rel_tol=1e-6,abs_tol=1e-10)]
        require(matches,"exported resistor missing from raw native multiset: "+row[0])
        available[key].pop(matches[0])
        require(a in nodes and b in nodes,"both raw resistor endpoints")
    require(not any(available.values()),"raw native resistors omitted from final model")
    ports={}
    for line in ext.splitlines():
        row=shlex.split(line)
        if row and row[0]=="port":
            require(len(row)>=5 and row[1]not in ports,"unique complete raw port")
            ports[row[1]]=[int(row[3]),int(row[4])]
    physical={a["label"]:a["point_dbu"]for a in anchors["anchors"]}
    require(set(ports)==set(physical)and bool(ports),"all actual precise native ports")
    reference=next(((n,i)for n,xy in ports.items()for i in(0,1)if xy[i]!=0 and physical[n][i]!=0),None)
    require(reference is not None,"nonzero coordinate scale reference")
    n,i=reference;scale=Fraction(str(physical[n][i]))/ports[n][i];require(scale>0,"positive raw coordinate scale")
    errors=[abs(scale*x-Fraction(str(y)))for n,xy in ports.items()for x,y in zip(xy,physical[n],strict=True)]
    require(max(errors)<=scale/2+Fraction(1,10**9),"all raw ports match actual precise anchors")
    rectangles=[];layer=None
    for line in mag.splitlines():
        if line.startswith("<< "):layer=line[3:-3].strip()
        row=line.split()
        if not row:continue
        if row[0]=="tri":raise AssertionError("Native triangular paint requires explicit endpoint containment support")
        if row[0]=="rect"and layer not in("checkpaint","labels","properties"):
            require(len(row)==5 and isinstance(layer,str),"complete named paint rectangle")
            box=list(map(int,row[1:]));require(box[0]<=box[2]and box[1]<=box[3],"ordered paint bounds")
            rectangles.append((layer,*box))
    require(rectangles,"actual native paint")
    return dict(nodes=nodes,rectangles=rectangles,scale=scale,ports=len(ports),max_error=max(errors),
      resistor_count=sum(map(len,resistors.values())))

def locate(edge,raw_by_name,geometry):
    row=raw_by_name[edge["resistor"]];require(row[0][0].upper()=="R","actual raw resistor")
    require(float(parser.number(row[3]))==edge["resistance_ohm"],"actual dominant resistor value")
    ends=[]
    for node in row[1:3]:
        x,y=geometry["nodes"][node]
        paint=sorted({layer for layer,x0,y0,x1,y1 in geometry["rectangles"]if x0<=x<=x1 and y0<=y<=y1})
        require(paint,"raw endpoint has no observed native paint")
        ends.append(dict(raw_node=node,raw_xy=[x,y],dbu_xy=[float(x*geometry["scale"]),float(y*geometry["scale"])],paint_layers=paint))
    return dict(raw_resistor=row,endpoint_witnesses=ends,
      edge_is_straight_segment_proved=False,unique_edge_layer_proved=False)

def analyze(model,wire,contract,anchors,res_ext,ext,mag,solve):
    require(contract["counts"]==dict(devices=500,R=24356,C=15566),"current composed500device model only")
    require(contract["qualified_pex"]is False and contract["all_raw_wire_tokens_preserved"]is True,"original scope retained")
    edges,raw=bind_export(model,wire,contract)
    contacts=ownership(edges,contract,anchors);pairs=requested_pairs(contacts)
    geometry=raw_geometry(res_ext,ext,mag,anchors,raw)
    lookup={r[0]:r for r in raw};evaluations=[]
    reverse={v.lower():k for k,v in contract["wire_node_map"].items()}
    for pair in pairs:
        value=solve(edges,pair["from_node"],pair["to_node"])
        for edge in value["dominant_edges"]:
            original=lookup[edge["resistor"]]
            require([reverse[edge["from_node"]],reverse[edge["to_node"]]]==original[1:3],"dominant raw node direction")
            edge["native_endpoint_binding"]=locate(edge,lookup,geometry)
        evaluations.append(dict(pair=pair,wire_only_solution=value))
    return dict(status="COMPLETE_CURRENT_CDR_WIRE_OWNERSHIP_DIAGNOSIS_ORIGINAL_ELECTRICAL_REJECTION_RETAINED",
      counts=contract["counts"],components=contacts["components"],evaluations=evaluations,
      raw_native_resistors=geometry["resistor_count"],raw_ports=geometry["ports"],
      coordinate_scale=str(geometry["scale"]),max_coordinate_error_dbu=float(geometry["max_error"]),
      interpretation="Mathematical1A wire-only DC with other terminals floating. KCL/energy tests validate only this linear network. Native endpoint paint is not unique edge layer/straight-path evidence. No operating/transient KCL, RF, EM, CDR or PHY acceptance.",
      **FLAGS)

def load_solver():
    """Execute only the byte-bound existing numerical solve/controls functions."""
    import numpy as np
    import scipy
    from scipy.sparse import coo_matrix
    from scipy.sparse.linalg import splu
    require(np.__version__=="2.3.3"and scipy.__version__=="1.16.2","exact numerical dependencies")
    path=Path(__file__).resolve().parent/"analyze_cdr_wire_resistance.py"
    source=path.read_bytes()
    require(hashlib.sha256(source).hexdigest()=="0b3be4b3e7b20fe722240f569a3f55b0f0ab5cb0ef1bafc3b44e92cfd9082288","unchanged original sparse solver source")
    tree=ast.parse(source,filename=str(path));functions=[]
    for name in("solve","controls"):
        found=[x for x in tree.body if isinstance(x,ast.FunctionDef)and x.name==name]
        require(len(found)==1,"one original numerical function");functions.extend(found)
    scope=dict(defaultdict=defaultdict,math=math,np=np,coo_matrix=coo_matrix,splu=splu)
    exec(compile(ast.Module(body=functions,type_ignores=[]),str(path),"exec"),scope)
    return SimpleNamespace(solve=scope["solve"],controls=scope["controls"])
