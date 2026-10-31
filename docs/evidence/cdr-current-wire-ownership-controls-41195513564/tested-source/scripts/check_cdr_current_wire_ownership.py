#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0
"""Hosted synthetic source controls, not actual model/geometry measurements."""
import copy,hashlib,json,os,sys
from pathlib import Path
import analyze_cdr_current_wire_ownership as a

def main():
    assert os.environ.get("GITHUB_ACTIONS")=="true"and os.environ["GITHUB_RUN_ATTEMPT"]=="1"
    solver=a.load_solver()
    rows=[]
    def record(name):
        assert name not in rows
        rows.append(name);print(json.dumps(dict(completed_source_control=name,index=len(rows),synthetic_inputs_only=True)),flush=True)
    def ok(name,fn):fn();record(name)
    def no(name,fn):
        try:fn()
        except(AssertionError,ValueError,KeyError):record(name)
        else:raise AssertionError("accepted invalid fixture: "+name)
    def eq(x,y):assert x==y
    wire=".subckt pump_wires P_a T001_C P_b T001_E\nR1 P_a T001_C 2\nR2 P_b T001_E 3\nC1 T001_C sub 0.5p\n.ends pump_wires\n"
    model=".subckt fixture a b wire_cref\nXD0001 w_T001_C w_T001_E npn13g2\nR1 a w_T001_C 2\nR2 b w_T001_E 3\nC1 w_T001_C wire_cref 0.5p\n.ends fixture\n"
    mapping={"P_a":"a","T001_C":"w_T001_C","P_b":"b","T001_E":"w_T001_E","sub":"wire_cref"}
    contract=dict(interface=["a","b","wire_cref"],wire_node_map=mapping,counts=dict(devices=1,R=2,C=1),
      native_extracted_mim_cards_projected_once=[],device_records=[dict(native_id=1,terminals=[
      dict(anchor="T001_C",node="w_T001_C",native_cluster=1,native_net="a"),
      dict(anchor="T001_E",node="w_T001_E",native_cluster=2,native_net="b")])])
    anchors=dict(anchors=[
      dict(label="P_a",point_dbu=[0,0],native_cluster=1,detail=dict(public_port="a")),
      dict(label="T001_C",point_dbu=[10,0],native_cluster=1,detail={}),
      dict(label="P_b",point_dbu=[0,20],native_cluster=2,detail=dict(public_port="b")),
      dict(label="T001_E",point_dbu=[10,20],native_cluster=2,detail={})])
    edges,raw=a.bind_export(model,wire,contract)
    ok("exact raw passive token projection",lambda:eq(len(edges),2))
    for name,m,w in(
      ("changed final resistor",model.replace("R1 a w_T001_C 2","R1 a w_T001_C 4"),wire),
      ("changed raw resistor",model,wire.replace("P_a T001_C 2","P_a T001_C 4")),
      ("changed raw direction",model,wire.replace("R1 P_a T001_C","R1 T001_C P_a")),
      ("missing final resistor",model.replace("R1 a w_T001_C 2\n",""),wire),
      ("duplicate final element",model.replace(".ends fixture","R1 a w_T001_C 2\n.ends fixture"),wire),
      ("changed capacitor token",model.replace("0.5p","0.6p"),wire),
      ("unexpected raw MIM",model,wire.replace(".ends pump_wires","XBAD T001_C T001_E cap_cmim w=1u l=1u\n.ends pump_wires")),
      ("negative actual resistor",model.replace("w_T001_C 2","w_T001_C -2"),wire.replace("T001_C 2","T001_C -2"))):
        no(name,lambda m=m,w=w:a.bind_export(m,w,contract))
    ok("source native conductor ownership",lambda:eq(a.ownership(edges,contract,anchors)["components"],2))
    no("cross conductor short",lambda:a.ownership(edges+[("short","w_t001_c","w_t001_e",1.)],contract,anchors))
    no("split native conductor",lambda:a.ownership(edges[1:],contract,anchors))
    no("unanchored resistor component",lambda:a.ownership(edges+[("orphan","x","y",1.)],contract,anchors))
    wrong=copy.deepcopy(contract);wrong["device_records"][0]["terminals"][0]["native_cluster"]=3
    no("wrong physical cluster",lambda:a.ownership(edges,wrong,anchors))
    wrong2=copy.deepcopy(contract);wrong2["device_records"][0]["terminals"][0]["node"]="wrong"
    no("wrong composed terminal mapping",lambda:a.ownership(edges,wrong2,anchors))
    wrong3=copy.deepcopy(anchors);wrong3["anchors"].append(copy.deepcopy(anchors["anchors"][0]))
    no("duplicate native physical anchor",lambda:a.ownership(edges,contract,wrong3))
    isolated=copy.deepcopy(contract);isolated["wire_node_map"]["P_c"]="c"
    isoanchors=copy.deepcopy(anchors);isoanchors["anchors"].append(dict(label="P_c",point_dbu=[50,50],native_cluster=3,detail=dict(public_port="c")))
    ok("legitimate isolated single metal contact",lambda:eq(a.ownership(edges,isolated,isoanchors)["components"],3))
    groups=[
      ["T054_E","T056_E","T061_C","T062_C"],["T106_E","T108_E","T115_C","T116_C"],
      ["T003_D","T004_D","T005_D","T006_D","T061_E","T062_E"],
      ["T032_D","T033_D","T034_D","T035_D","T115_E","T116_E"],
      ["P_vip","T279_mim_top","T168_C","T171_C"],["P_vin","T279_mim_btm","T167_C","T172_C"]]
    contacts=dict(terminals={label:dict(node=label.lower(),owner=[i,"net"+str(i)],component=str(i))for i,group in enumerate(groups)for label in group},public=dict(vip="P_vip",vin="P_vin"))
    ok("all34 source targeted contact pairs",lambda:eq(len(a.requested_pairs(contacts)),34))
    missing=copy.deepcopy(contacts);missing["terminals"].pop("T003_D")
    no("missing required tail contact",lambda:a.requested_pairs(missing))
    cross=copy.deepcopy(contacts);cross["terminals"]["T061_C"]["owner"]=[999,"other"]
    no("incorrect requested contact ownership",lambda:a.requested_pairs(cross))
    res='rnode "P_a" 0 0 0 0 m1\nrnode "T001_C" 0 0 10 0 m1\nrnode "P_b" 0 0 0 20 m1\nrnode "T001_E" 0 0 10 20 m1\nresist "P_a" "T001_C" 2\nresist "P_b" "T001_E" 3\n'
    ext='port "P_a" 1 0 0 m1\nport "T001_C" 2 10 0 m1\nport "P_b" 3 0 20 m1\nport "T001_E" 4 10 20 m1\n'
    mag="magic\ntech ihp\n<< metal1 >>\nrect -1 -1 11 1\nrect -1 19 11 21\n<< end >>\n"
    geometry=a.raw_geometry(res,ext,mag,anchors,raw)
    ok("complete raw resistor coordinates and paint",lambda:eq(geometry["resistor_count"],2))
    for name,r,e,m in(
      ("changed raw resistance",res.replace('"T001_C" 2','"T001_C" 3'),ext,mag),
      ("extra raw parallel resistor",res+'resist "P_a" "T001_C" 2\n',ext,mag),
      ("missing raw resistor node",res.replace('rnode "P_a" 0 0 0 0 m1\n',''),ext,mag),
      ("shifted native port",res,ext.replace('4 10 20','4 13 20'),mag),
      ("missing native port",res,ext.replace('port "P_a" 1 0 0 m1\n',''),mag),
      ("unhandled triangle paint",res,ext,mag.replace("<< end >>","tri 0 0 1 1 ne\n<< end >>"))):
        no(name,lambda r=r,e=e,m=m:a.raw_geometry(r,e,m,anchors,raw))
    edge=dict(resistor="R1",resistance_ohm=2.)
    lookup={x[0]:x for x in raw}
    ok("dominant endpoint witnesses",lambda:eq(len(a.locate(edge,lookup,geometry)["endpoint_witnesses"]),2))
    no("dominant resistance mismatch",lambda:a.locate(dict(edge,resistance_ohm=3.),lookup,geometry))
    empty=copy.deepcopy(geometry);empty["rectangles"]=[]
    no("missing endpoint paint",lambda:a.locate(edge,lookup,empty))
    ok("original sparse solver analytic reciprocity KCL energy and fault controls",solver.controls)
    result=solver.solve(edges,"a","w_t001_c")
    ok("actual imported solver exact two terminal value",lambda:eq(result["effective_wire_R_ohm"],2.))
    no("incomplete real model census",lambda:a.analyze(model,wire,contract,anchors,res,ext,mag,solver.solve))
    assert len(rows)==33 and len(set(rows))==33
    result=dict(status="PASS_CURRENT_CDR_WIRE_OWNERSHIP_SOURCE_CONTROLS",count=33,passed_cases=rows,
      source=os.environ["GITHUB_SHA"],run_id=int(os.environ["GITHUB_RUN_ID"]),attempt=1,
      synthetic_inputs_only=True,actual_native_inputs_acquired=False,actual_model_analyzed=False,**a.FLAGS)
    Path(sys.argv[1]).write_text(json.dumps(result,sort_keys=True,indent=2)+"\n")
    print(json.dumps(result,sort_keys=True))
if __name__=="__main__":main()
