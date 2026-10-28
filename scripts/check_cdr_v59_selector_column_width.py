#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0
"""Hosted source controls. Synthetic KLayout geometry is not native input qualification."""
import argparse
import copy
import hashlib
import io
import json
import os
import sys
import tempfile
from contextlib import redirect_stderr
from pathlib import Path
from types import SimpleNamespace
import generate_cdr_v59_selector_column_width as g

def refused(name,call,reason):
    try:
        call()
    except AssertionError as error:
        assert reason in str(error),(name,repr(error))
        return dict(case=name,rejected=True,error=repr(error))
    raise AssertionError("Accepted "+name)

def contract_controls(contract):
    proposal = g.boxes(contract,contract["source_routes"])
    assert len(proposal) == 26 and {r["layer"] for r in proposal} == {50,126}
    assert sum(r["net"] == "M_SE" for r in proposal) == 10
    screen = g.source_column_screen(contract)
    assert screen["minimum_gap_dbu"] == 2580 and screen["full_geometry_clearance"] is False
    cases = []
    for name,change,reason in (
        ("wrong_width",lambda c:c.update(width_dbu=3300),""),
        ("declared_box_shift",lambda c:c["declared_rectangles"][0]["new"].__setitem__(0,c["declared_rectangles"][0]["new"][0]-5),"Declared coordinate plan differs"),
        ("boolean_width",lambda c:c.update(width_dbu=True),""),
        ("wrong_origin",lambda c:c.update(origin_dbu=[0,-3975]),"Changed normalization"),
        ("shift_old_bus",lambda c:c["old_bus_dbu"].update(M_SE=150005),"Changed old buses"),
        ("extend_new_endpoint",lambda c:c["width_end_dbu"].update(M_TE=240000),"Changed width endpoints"),
        ("relaxed_clearance",lambda c:c["clearance_dbu"].update({"126":100}),"Changed clearance"),
        ("missing_selected",lambda c:c["source_routes"].pop(next(i for i,r in enumerate(c["source_routes"]) if r["net"]=="M_SE")),"Changed selected source routes"),
        ("duplicate_selected",lambda c:c["source_routes"].append(copy.deepcopy(c["selected_original_routes"][0])),"Changed selected source routes"),
        ("shift_route",lambda c:c["source_routes"][0].update(escape_lane_um=-123),"Changed selected source routes")):
        changed = copy.deepcopy(contract)
        if name == "shift_route":
            index = next(i for i,r in enumerate(changed["source_routes"]) if r["net"]=="M_SE")
            changed["source_routes"][index]["escape_lane_um"] += .005
        else:
            change(changed)
        assert g.canonical(changed) != g.canonical(contract)
        cases.append(refused(name,lambda:g.boxes(changed,changed["source_routes"]),reason))
    changed = copy.deepcopy(contract)
    selected = changed["selected_original_routes"][0]
    foreign = next(r for r in changed["source_routes"] if r["net"] not in ("M_SE","M_TE"))
    foreign["escape_lane_um"] = selected["escape_lane_um"] + 2.5
    cases.append(refused("foreign_column",lambda:g.source_column_screen(changed),"Source column clearance"))
    graph = json.loads((g.ROOT/contract["qualified_graph_path"]).read_text())["geometry"]
    g.validate_graph(contract,graph)
    for name,change in (
        ("wrong_owner",lambda x:x["owner_partitions"]["sd"]["M_SE"].update(native_cluster=28)),
        ("missing_terminal",lambda x:x["owner_partitions"]["sc"]["M_TE"]["device_terminals"].pop()),
        ("changed_terminal",lambda x:x["owner_partitions"]["sd"]["M_SE"]["device_terminals"][0].update(terminal="C")),
        ("changed_net_name",lambda x:x["owner_partitions"]["sc"]["M_SE"].update(name="$149"))):
        changed = copy.deepcopy(contract)
        change(changed)
        cases.append(refused(name,lambda:g.validate_graph(changed,graph),"Changed complete native owner partition"))
    assert len(cases)==15
    return dict(positive=3,refusals=15,cases=cases,screen=screen)

def component_controls(pya):
    full = pya.Region(pya.Box(-600,0,600,10000))+pya.Region(pya.Box(3500,0,4700,10000))
    addition = pya.Region(pya.Box(-1600,0,1600,10000))
    probe = lambda layer,point:SimpleNamespace(cluster_id=28)
    args = [pya,full,full,probe,[0,1000],28,addition,1640,pya.Region()]
    _, proof = g.owned_component(*args)
    assert proof["added_area_dbu2"] == 20000000 and proof["native_cluster"] == 28
    cases = []
    mutations = (
        ("wrong_net",3,lambda layer,point:SimpleNamespace(cluster_id=38),"Wrong actual native owner"),
        ("unknown_net",3,lambda layer,point:None,"Wrong actual native owner"),
        ("missing_component",4,[20000,20000],"Missing unique old component"),
        ("foreign_clearance",6,pya.Region(pya.Box(-1600,0,2000,10000)),"Foreign metal clearance"),
        ("no_width",6,pya.Region(pya.Box(-600,0,600,10000)),"No added width"),
        ("new_via_contact",8,pya.Region(pya.Box(700,1000,900,1200)),"New adjacent-via contact"))
    for name,index,value,reason in mutations:
        altered = list(args); altered[index] = value
        cases.append(refused(name,lambda:g.owned_component(*altered),reason))
    return dict(positive=1,refusals=len(cases),cases=cases)

def synthetic_layout(pya,contract):
    layout = pya.Layout(); layout.dbu=.001
    top = layout.create_cell(g.TOP); child=layout.create_cell(g.CHILD)
    for row in g.boxes(contract,contract["source_routes"]):
        child.shapes(layout.layer(row["layer"],0)).insert(pya.Box(*row["old"]))
    # Unchanged lower-metal and enclosing geometry make preservation assertions meaningful.
    child.shapes(layout.layer(30,0)).insert(pya.Box(0,0,2000000,5))
    top.shapes(layout.layer(8,0)).insert(pya.Box(0,0,3000000,3000000))
    top.shapes(layout.layer(8,2)).insert(pya.Text("unchanged",pya.Trans(5,5)))
    for dx,dy in contract["placements"].values():
        top.insert(pya.CellInstArray(child.cell_index(),pya.Trans(dx,dy)))
    return layout

class SyntheticDB:
    """Only native extraction/probe is substituted; actual Region/serialization code runs."""
    def __init__(self,pya,layout,contract,wrong=False):
        self.pya,self.layout,self.contract,self.wrong=pya,layout,contract,wrong
        self.full=g.frozen.material(pya,layout,layout.cell(g.TOP),True)
        self.layers=[(50,0),(126,0)]
    def read(self,path):
        assert Path(path).read_text()=="EXPLICIT_SYNTHETIC_LVS"
    def netlist(self):
        return SimpleNamespace(top_circuit=lambda:SimpleNamespace(name=g.TOP,pin_count=lambda:25,each_device=lambda:iter(range(500))))
    def layer_indexes(self):
        return range(2)
    def layer_by_index(self,index):
        return self.full[self.layers[index]]
    def probe_net(self,layer,point):
        for tag,(dx,dy) in self.contract["placements"].items():
            for row in g.boxes(self.contract,self.contract["source_routes"]):
                if point.x==row["probe"][0]+dx and point.y==row["probe"][1]+dy:
                    owner=self.contract["owner_partitions"][tag][row["net"]]["native_cluster"]
                    return SimpleNamespace(cluster_id=owner+1 if self.wrong else owner)
        return None

class NativeProxy:
    def __init__(self,pya,db):
        self.pya,self.db=pya,db
    def __getattr__(self,name):
        return self.pya.__getattribute__(name)
    def LayoutVsSchematic(self):
        return self.db

def geometry_controls(pya,contract):
    proposal=g.boxes(contract,contract["source_routes"])
    layout=synthetic_layout(pya,contract)
    db=SyntheticDB(pya,layout,contract)
    additions,proof=g.native_plan(pya,layout,db,contract,proposal)
    assert len(proof)==52
    cases=[]
    cases.append(refused("native_wrong_owner",lambda:g.native_plan(pya,layout,SyntheticDB(pya,layout,contract,True),contract,proposal),"Wrong actual native owner"))
    moved=synthetic_layout(pya,contract)
    cell=moved.cell(g.CHILD); row=proposal[0]
    shapes=cell.shapes(moved.layer(row["layer"],0))
    matching=[s for s in shapes.each() if s.is_box() and s.box==pya.Box(*row["old"])]
    assert len(matching)==1
    shapes.erase(matching[0])
    box=list(row["old"]); box[0]-=5
    shapes.insert(pya.Box(*box))
    cases.append(refused("wrong_original_rectangle",lambda:g.native_plan(pya,moved,SyntheticDB(pya,moved,contract),contract,proposal),"Original exact rectangle"))
    with tempfile.TemporaryDirectory() as td:
        source=Path(td)/"source"; out=Path(td)/"out"; source.mkdir();out.mkdir()
        (source/g.GDS).parent.mkdir(parents=True)
        layout.write(str(source/g.GDS))
        (source/g.LVS).parent.mkdir(parents=True)
        (source/g.LVS).write_text("EXPLICIT_SYNTHETIC_LVS")
        c=copy.deepcopy(contract);c["baseline_inventory"]=g.frozen.files(source)
        result=g.generate_admitted(NativeProxy(pya,db),source,out,(c,proposal,g.source_column_screen(contract)))
        assert len(result["added_raw_records"])==26 and len(result["actual_original_native_ownership_and_clearance"])==52
        assert result["physical_accepted"] is result["electrical_accepted"] is False
        assert result["candidate_gds_sha256"]==g.frozen.sha(out/(g.TOP+".gds"))
        reread=pya.Layout();reread.read(str(out/(g.TOP+".gds")))
        before={cell.name:(g.frozen.material(pya,layout,cell),g.frozen.raw_records(layout,cell),g.frozen.hierarchy(cell)) for cell in layout.each_cell()}
        expected=g.frozen.material(pya,reread,reread.cell(g.CHILD))
        raw=g.frozen.raw_records(reread,reread.cell(g.CHILD))
        bbox=layout.cell(g.TOP).bbox()
        g.verify_snapshot(pya,reread,before,expected,raw,bbox)
        # Every fault starts from the serialized synthetic candidate.
        for name,mutate,reason in (
            ("lower_metal_removed",lambda l:l.cell(g.CHILD).shapes(l.layer(30,0)).clear(),"Changed material"),
            ("extra_text",lambda l:l.cell(g.CHILD).shapes(l.layer(126,0)).insert(pya.Text("bad",pya.Trans(5,5))),"Raw shape"),
            ("extra_cell",lambda l:l.create_cell("bad"),"Cell census"),
            ("extra_instance",lambda l:l.cell(g.TOP).insert(pya.CellInstArray(l.cell(g.CHILD).cell_index(),pya.Trans(0,0))),"Hierarchy"),
            ("extra_allowed_layer_box",lambda l:l.cell(g.CHILD).shapes(l.layer(126,0)).insert(pya.Box(1,1,5,5)),"Changed material")):
            fresh=pya.Layout();fresh.read(str(out/(g.TOP+".gds")));mutate(fresh)
            cases.append(refused(name,lambda:g.verify_snapshot(pya,fresh,before,expected,raw,bbox),reason))
    assert len(cases)==7
    return dict(positive=3,refusals=7,cases=cases,geometry="Explicit synthetic geometry, full native extraction substituted; no actual current GDS admission or DRC/LVS")

def lifecycle_controls():
    original=(g.ROOT,g.METHOD,g.admitted,g.generate_admitted,g.os.replace,sys.modules.get("pya"))
    cases=[]
    try:
        for mode in ("success","body","save","body_and_save"):
            with tempfile.TemporaryDirectory() as td:
                root=Path(td);source=root/"hw/soc/out/source";source.mkdir(parents=True)
                (source/"input").write_text("synthetic")
                method=root/"method.json";method.write_text(json.dumps({"protected_sha256":{}}))
                out=root/"hw/soc/out/candidate"
                g.ROOT=root;g.METHOD=method;sys.modules["pya"]=SimpleNamespace()
                baseline=g.frozen.files(source)
                g.admitted=lambda s:({"baseline_inventory":baseline},[],{})
                body_error=RuntimeError("exact body primary")
                save_error=OSError("exact atomic replace failure")
                def body(pya,s,o,a):
                    (o/"partial.bin").write_bytes(b"kept\x00exact")
                    if mode in ("body","body_and_save"):
                        raise body_error
                    return dict(status="GENERATED_UNQUALIFIED_ADDITIVE_COLUMN_WIDTH")
                def replace(a,b):
                    assert Path(a).is_file() and Path(a).name.endswith(".incomplete")
                    raise save_error
                g.generate_admitted=body
                g.os.replace=replace if mode in ("save","body_and_save") else original[4]
                output=io.StringIO(); caught=None
                try:
                    with redirect_stderr(output):
                        got=g.run(source,out)
                except BaseException as error:
                    caught=error
                if mode=="success":
                    assert caught is None and got["status"]=="GENERATED_UNQUALIFIED_ADDITIVE_COLUMN_WIDTH"
                elif mode=="body":
                    assert caught is body_error
                elif mode=="save":
                    assert caught is save_error
                else:
                    assert caught is body_error
                if mode in ("save","body_and_save"):
                    saved=json.loads(output.getvalue())
                    assert saved["outputs"]==g.frozen.files(out)
                    assert any(n.endswith(".incomplete") for n in saved["outputs"])
                    assert any(r["action"]=="atomic_save" for r in saved["terminal_errors"])
                else:
                    saved=json.loads((out/"result.json").read_text())
                    assert saved["outputs"]=={k:v for k,v in g.frozen.files(out).items() if k!="result.json"}
                assert saved["physical_accepted"] is saved["electrical_accepted"] is saved["full_phy_accepted"] is False
                assert g.frozen.files(source)==baseline
                assert saved["outputs"]["partial.bin"]==hashlib.sha256(b"kept\x00exact").hexdigest()
                cases.append(dict(case=mode,expected_primary_preserved=True,complete_existing_outputs=True))
    finally:
        g.ROOT,g.METHOD,g.admitted,g.generate_admitted,g.os.replace=original[:5]
        if original[5] is None:sys.modules.pop("pya",None)
        else:sys.modules["pya"]=original[5]
    return dict(cases=cases,count=4,synthetic_admission_and_generation=True,actual_run_and_atomic_writer=True)

def controls():
    assert os.environ.get("GITHUB_ACTIONS")=="true","Hosted source controls only"
    method=json.loads(g.METHOD.read_text())
    assert method["source_controls_authorized"] is True
    for p,h in method["protected_sha256"].items():
        assert g.frozen.sha(g.ROOT/p)==h,("Changed protected source",p)
    assert all(method[k] is False for k in ("native_execution_authorized","geometry_generation_authorized","simulation_authorized","physical_accepted","electrical_accepted","full_phy_accepted"))
    contract=json.loads(g.CONTRACT.read_text())
    import klayout.db as pya
    import importlib.metadata
    assert importlib.metadata.version("klayout")=="0.30.7"
    disabled=refused("disabled_native",lambda:g.admitted(g.ROOT/"hw/soc/out/absent"),"Disabled geometry candidate")
    result=dict(status="PASS_SOURCE_CONTROLS_ONLY",source=contract_controls(contract),
                component=component_controls(pya),geometry=geometry_controls(pya,contract),
                lifecycle=lifecycle_controls(),disabled_native=disabled,
                native_input_qualified=False,physical_accepted=False,electrical_accepted=False)
    assert result["source"]["refusals"]+result["component"]["refusals"]+result["geometry"]["refusals"]==28
    return result

def main():
    parser=argparse.ArgumentParser();parser.add_argument("--output",type=Path,required=True);args=parser.parse_args()
    try:
        result=controls()
    except BaseException as error:
        failure=dict(status="FAIL_SOURCE_CONTROLS",error=repr(error),physical_accepted=False,electrical_accepted=False)
        try:
            g.atomic(args.output,failure)
        except BaseException as save:
            failure["save_error"]=repr(save)
            try:
                print(json.dumps(failure,sort_keys=True),file=sys.stderr,flush=True)
            except BaseException:
                pass
        raise
    g.atomic(args.output,result)
    print(json.dumps(result,sort_keys=True,allow_nan=False))

if __name__=="__main__":
    main()
