#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0
"""Hosted source fixtures. No Pya, CAD, extraction, or simulator is loaded."""
import ast, copy, hashlib, json, sys, tempfile
from collections import Counter
from pathlib import Path
from unittest.mock import patch
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/"hw/soc/flow"))
import make_pcie_tx_phase_reset334_tail_m4_v1 as g
OUT=ROOT/"hw/soc/out/tx-phase-reset334-tail-m4-source-controls"

def canonical(v):
    return json.dumps(v,sort_keys=True,separators=(",",":"),allow_nan=False)

def terminals(report):
    result={};counts=Counter()
    def add(net,rid,x,y):
        result.setdefault(net,[]).append((rid,x,y))
    devices={x["name"]:x for x in report["instances"]}
    assert len(devices)==334
    for r in report["routes"]:
        d=devices[r["device"]];rid=d["placement_row"]
        if set(r)==g.SCALAR:
            counts["scalar"]+=1;add(r["net"],rid,r["escape_lane_um"],r["escape_y_um"])
        else:
            assert set(r)==g.MIM
            counts["mim"]+=1
            for side in ("plus","minus"):
                add(r[side+"_net"],rid,*r[side+"_escape_um"])
    for d in devices.values():
        if d["kind"]=="substrate_tap":
            counts["tap"]+=1;x,y=d["placement_um"]
            # Exact frozen substrate_tap_position + native2x2 pin center.
            rid=next(int(i)for i,start in report["row_starts_um"].items()if start==y-4)
            add("SUB",rid,x+1,y+1)
    assert counts==dict(scalar=578,mim=8,tap=90)
    assert sum(map(len,result.values()))==684
    return result

def route_plan(main_text,report):
    tree=ast.parse(main_text)
    loops=[n for n in ast.walk(tree)if isinstance(n,ast.For)and isinstance(n.target,ast.Tuple)
        and [x.id for x in n.target.elts if isinstance(x,ast.Name)]==["_","x","start"]]
    assert len(loops)==1
    program=ast.fix_missing_locations(ast.Module(body=[copy.deepcopy(loops[0])],type_ignores=[]))
    terminal_map=terminals(report);rects=[];vias=[]
    for bus in report["local_buses"]:
        net=bus["net"];rid=bus["row"];xs=[]
        def rect(layer,*coords):
            # Actual float expression is recorded. Integer projection models
            # the frozen1nm DBU conversion; actual GDS proof is separate.
            dbu=[round(v*1000)for v in coords]
            assert all(abs(v*1000-i)<1e-6 for v,i in zip(coords,dbu,strict=True))
            rects.append(dict(net=net,row=rid,layer=layer,dbu=dbu))
        def via(bottom,upper,x,y,owner,cols):
            vias.append([net,rid,bottom,upper,x,y,owner,cols])
        ns=dict(rect=rect,via=via,ts=terminal_map[net],rid=rid,y=bus["y_um"],net=net,
                row_starts={int(k):v for k,v in report["row_starts_um"].items()},xs=xs)
        exec(compile(program,"<actual-frozen-M4-loop-fixture>","exec"),ns)
        assert len(xs)==sum(t[0]==rid for t in terminal_map[net])
    return dict(rects=rects,vias=vias,actual_loop_ast=ast.dump(loops[0],include_attributes=False))

def assert_plan(old,new,report):
    assert len(old["rects"])==len(new["rects"])==684
    assert old["vias"]==new["vias"] and len(old["vias"])==684
    expected=g.target_plan(report);deltas=[]
    for a,b in zip(old["rects"],new["rects"],strict=True):
        if a!=b:deltas.append((a,b))
    assert len(deltas)==12
    for a,b in deltas:
        assert a["net"]==b["net"] and a["row"]==b["row"] and a["layer"]==b["layer"]==4
        e=next(x for x in expected if x["net"]==a["net"]and x["old_source_box_dbu"]==a["dbu"])
        assert b["dbu"]==e["new_source_box_dbu"]
    assert Counter(a["net"]for a,b in deltas)==dict.fromkeys(g.TAIL_NETS,3)
    return dict(all_M4_branches=684,all_branch_vias=684,exact_changed_rectangles=12,
        non_target_branches_equal=True,via_parameters_equal=True,expected_deltas=expected,
        native_geometry_or_DRC_proved=False)

def source_identity(current,changed,proof):
    assert g.q.exact_replace(current,g.TAIL_EDITS)==changed
    assert g.q.exact_replace(changed,[(b,a)for a,b in reversed(g.TAIL_EDITS)])==current
    assert hashlib.sha256(changed.encode()).hexdigest()==proof["candidate_main_sha256"]
    a,b=ast.parse(current),ast.parse(changed)
    assert len(a.body)==len(b.body)==1 and a.body[0].name==b.body[0].name=="main"

def main_entry(full,proof,raises):
    saved=copy.deepcopy(g.q.MAIN_EDITS);events=[];p="p"
    class Boundary(Exception):pass
    with tempfile.TemporaryDirectory()as td:
        out=Path(td)/"synthetic-layout"
        def fake_native():
            events.append("qualified-q-main-boundary")
            assert g.q.MAIN_EDITS==saved+g.avss.TRUNK_EDITS+g.TAIL_EDITS
            if raises:raise Boundary("Explicit stop before native CAD")
            out.mkdir();r=copy.deepcopy(full["variants"][p]["generation"])
            for k in ("avss18_report_comparison","avss18_derivation"):del r[k]
            (out/"result.json").write_text(json.dumps(r))
        fake_method=dict(source_derivation=proof,native_generation_authorized=True)
        with patch.object(g,"host",lambda:None),patch.object(g,"methods",lambda:fake_method),patch.object(g.q,"main",fake_native),patch.object(sys,"argv",["fixture","--out",str(out),"--preset",p]):
            if raises:
                try:g.main()
                except Boundary:events.append("expected-boundary")
                else:raise AssertionError("Missing explicit pre-CAD stop")
            else:
                g.main();r=json.loads((out/"result.json").read_text())
                assert r["tail_m4_plan"]==g.target_plan(full["variants"][p]["generation"])
                assert r["tail_m4_derivation"]==proof
                events.append("actual-main-returned-complete-synthetic-report")
        assert g.q.MAIN_EDITS==saved
    return dict(events=events,main_and_finally_exercised=True,synthetic_collaborator=True,native_executed=False)

def main():
    g.host();m=g.methods()
    assert m["source_controls_authorized"]is True
    assert all(type(m[k])is bool for k in g.AUTH_FLAGS)
    assert m["simulation_authorized"]is m["extraction_authorized"]is m["continuation_authorized"]is False
    OUT.mkdir(parents=True,exist_ok=False);result=dict(status="RUNNING",native_executed=False,positives=[],faults=[])
    def save():(OUT/"result.json").write_text(json.dumps(result,indent=2,allow_nan=False)+"\n")
    def bad(name,fn):
        try:fn()
        except (AssertionError,ValueError,KeyError,TypeError,StopIteration)as e:
            result["faults"].append(dict(name=name,rejected=True,error=repr(e)));save()
        else:raise AssertionError("Accepted fault "+name)
    save()
    try:
        full=g.baseline();flat,current,changed,proof=g.derivations()
        assert proof==m["source_derivation"];source_identity(current,changed,proof)
        result["derivation"]=proof
        old_material=ast.parse((ROOT/"scripts/tx_phase_reset244_avss18_native_material.py").read_text())
        new_material=ast.parse((ROOT/"scripts/tx_phase_reset334_tail_m4_native_material.py").read_text())
        defs=lambda tree:{n.name:ast.dump(n,include_attributes=False)for n in tree.body if isinstance(n,ast.FunctionDef)}
        od,nd=defs(old_material),defs(new_material)
        assert set(od)==set(nd)
        assert {k for k in od if od[k]!=nd[k]}=={"compare","mutate","main"}
        result["unchanged_native_material_functions"]=sorted(k for k in od if od[k]==nd[k])
        plans={}
        for p in ("p","n"):
            report=full["variants"][p]["generation"]
            a,b=route_plan(current,report),route_plan(changed,report)
            plans[p]=assert_plan(a,b,report)
            result["positives"].append(dict(name="actual_report_full_loop_"+p,proof=plans[p]))
        assert plans["p"]["expected_deltas"]==plans["n"]["expected_deltas"]
        for name,value,expected in (("strict_decimal2167.995",2167.995,2167995),("strict_decimal2333.28",2333.28,2333280)):
            assert g.grid_dbu(value)==expected
            result["positives"].append(dict(name=name,dbu=g.grid_dbu(value)))
        for name,v in (("half_grid",1.0005),("off_grid",1.0001),("NaN",float("nan")),("infinity",float("inf")),("boolean",True),("numeric_string","2167.995")):
            bad(name,lambda v=v:g.grid_dbu(v))
        report=full["variants"]["p"]["generation"];a=route_plan(current,report)
        # Real program mutants execute the actual extracted loop and must
        # violate complete branch/via deltas, not a mirrored expected helper.
        mutants={
            "legacy_1p2":current,
            "all_nets_widened":changed.replace("tail_half_width = 1.2 if net in "+repr(g.TAIL_NETS)+" else 0.6","tail_half_width = 1.2"),
            "only_first_net":changed.replace(repr(g.TAIL_NETS),repr(g.TAIL_NETS[:1])),
            "wrong_width":changed.replace("tail_half_width = 1.2 if","tail_half_width = 1.1 if"),
            "moved_center":changed.replace("x - tail_half_width","x + .005 - tail_half_width"),
            "changed_start":changed.replace("start - 0.2, x + tail_half_width","start - 0.205, x + tail_half_width"),
            "changed_end":changed.replace("x + tail_half_width, y + 0.2","x + tail_half_width, y + 0.205"),
            "wrong_layer":changed.replace("rect(4, x - tail_half_width","rect(3, x - tail_half_width"),
            "changed_via_columns":changed.replace("via(4, 5, x, y, net, 2)","via(4, 5, x, y, net, 3)"),
        }
        assert all(v!=changed for v in mutants.values())
        for name,text in mutants.items():
            bad(name,lambda text=text:assert_plan(a,route_plan(text,report),report))
        for name,mutate in (
            ("missing_route",lambda r:r["routes"].pop(next(i for i,x in enumerate(r["routes"])if x.get("net")in g.TAIL_NETS))),
            ("duplicate_route",lambda r:r["routes"].append(copy.deepcopy(next(x for x in r["routes"]if x.get("net")in g.TAIL_NETS)))),
            ("wrong_route_layer",lambda r:next(x for x in r["routes"]if x.get("net")in g.TAIL_NETS).__setitem__("source_layer",3)),
            ("wrong_route_lane",lambda r:next(x for x in r["routes"]if x.get("net")in g.TAIL_NETS).__setitem__("escape_lane_um",462)),
            ("wrong_source_net",lambda r:next(x for x in r["routes"]if x.get("net")in g.TAIL_NETS).__setitem__("net","UNKNOWN")),
            ("wrong_role",lambda r:next(x for x in r["routes"]if x.get("net")in g.TAIL_NETS).__setitem__("device","PHASE__XM__XDATA__XAP")),
            ("source_point_half_grid",lambda r:next(x for x in r["routes"]if x.get("net")in g.TAIL_NETS).__setitem__("escape_y_um",1675.9905)),
            ("wrong_bus_extent",lambda r:next(x for x in r["local_buses"]if x["net"]in g.TAIL_NETS).__setitem__("right_um",505)),
            ("wrong_origin",lambda r:r.__setitem__("origin_translation_um",[0,-3.975])),
        ):
            r=copy.deepcopy(report);mutate(r);bad(name,lambda r=r:g.target_plan(r))
        for label,raises in (("full_main_return",False),("full_main_finally_stop",True)):
            result["positives"].append(dict(name=label,proof=main_entry(full,proof,raises)))
        assert len(result["positives"])==6 and len(result["faults"])==24
        result.update(status="PASS_AUTHORED_SOURCE_PLAN_CONTROLS_NOT_NATIVE",source_geometry_material_proved=False,
            source_generation_executed=False,original_electrical_rejection_preserved=True,
            native_material_faults_authored_but_not_executed=40)
        g.methods()
    except BaseException as e:
        result.update(status="FAIL_OR_ERROR",error=repr(e));raise
    finally:
        save();print(json.dumps(result,indent=2,allow_nan=False))
if __name__=="__main__":main()
