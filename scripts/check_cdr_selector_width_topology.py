#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0
"""Hosted-only synthetic controls and separately invoked real-root native faults."""
import argparse
import copy
import json
import os
from pathlib import Path
import cdr_selector_width_topology as s

def reject(action, reason, function):
    try:
        action()
    except AssertionError as error:
        frames=[];tb=error.__traceback__
        while tb:
            frames.append(tb.tb_frame.f_code);tb=tb.tb_next
        assert function.__code__ in frames, ("Wrong tested function",function.__name__,repr(error))
        assert error.args==(reason,),("Wrong refusal",reason,error.args)
        return dict(reason=reason,function=function.__name__)
    raise AssertionError(("Accepted fault",reason))


def source_controls():
    """No pya import, geometry work, or native payload access."""
    contract=s.source_guard()
    baseline=dict(origin_translation_um=[0,-3.97],routes=copy.deepcopy(contract["source_routes"]))
    positives=[]
    for zero in (0,0.0,-0.0):
        metadata=copy.deepcopy(baseline);metadata["origin_translation_um"][0]=zero
        result=s.expected_plan(contract,metadata)
        assert result==contract["declared_rectangles"]
        positives.append(dict(origin=metadata["origin_translation_um"],rectangles=len(result)))
    refusals=[]
    for mode,reason in (
      ("origin_x","Changed exact numeric child origin"),("origin_y","Changed exact numeric child origin"),
      ("origin_bool","Changed exact numeric child origin"),("origin_string","Changed exact numeric child origin"),
      ("origin_nan","Changed exact numeric child origin"),("origin_infinite","Changed exact numeric child origin"),
      ("route","Changed source route rows"),("literal","Width literal/formula mismatch"),
      ("width","Changed width/origin"),("placement","Changed declared placements"),
      ("endpoint","Changed width endpoints"),("dbu","Changed width coordinate scope")):
        c=copy.deepcopy(contract);m=copy.deepcopy(baseline)
        if mode=="origin_x":m["origin_translation_um"][0]=.001
        elif mode=="origin_y":m["origin_translation_um"][1]=-3.969
        elif mode=="origin_bool":m["origin_translation_um"][0]=False
        elif mode=="origin_string":m["origin_translation_um"][0]="0"
        elif mode=="origin_nan":m["origin_translation_um"][0]=float("nan")
        elif mode=="origin_infinite":m["origin_translation_um"][0]=float("inf")
        elif mode=="route":next(r for r in m["routes"]if r["net"]=="M_SE")["escape_lane_um"]+=.005
        elif mode=="literal":c["declared_rectangles"][0]["new"][0]+=5
        elif mode=="width":c["width_dbu"]+=5
        elif mode=="placement":c["placements"]["sc"][0]+=5
        elif mode=="endpoint":c["width_end_dbu"]["M_TE"]+=5
        elif mode=="dbu":c["dbu_um"]=.002
        refusals.append(reject(lambda:s.expected_plan(c,m),reason,s.expected_plan))
    assert len(positives)==3 and len(refusals)==12
    return dict(status="PASS_WIDTH_TOPOLOGY_SOURCE_CONTROLS",positive_cases=3,
      rejected_cases=12,positives=positives,refusals=refusals,pya_imported=False,
      native_geometry_executed=False,actual_saved_candidate_read=False,**s.FALSE)

def geometry_fixture(pya,contract,plan,mutation=None):
    """Synthetic shared child; not the 500-device candidate or its LVS."""
    layout=pya.Layout();layout.dbu=.001
    top=layout.create_cell(s.TOP);child=layout.create_cell(s.CHILD)
    top.shapes(layout.layer(200,0)).insert(pya.Box(0,0,3000000,2000000))
    child.shapes(layout.layer(201,0)).insert(pya.Box(0,0,1200000,300000))
    for i,row in enumerate(plan):
        if mutation=="remove_original" and i==0:
            continue
        child.shapes(layout.layer(row["layer"],0)).insert(pya.Box(*row["old"]))
    for tag,(x,y)in contract["placements"].items():
        if mutation=="transform" and tag=="sc":
            x+=5
        top.insert(pya.CellInstArray(child.cell_index(),pya.Trans(x,y)))
    if mutation=="multiplicity":
        top.insert(pya.CellInstArray(child.cell_index(),pya.Trans(0,0)))
    if mutation!="baseline":
        rows=copy.deepcopy(plan)
        if mutation=="missing":
            rows=rows[:-1]
        if mutation=="duplicate":
            rows.append(copy.deepcopy(rows[0]))
        if mutation=="shift":
            rows[0]["new"][0]+=5;rows[0]["new"][2]+=5
        for row in rows:
            child.shapes(layout.layer(row["layer"],0)).insert(pya.Box(*row["new"]))
    if mutation=="foreign_layer":
        child.shapes(layout.layer(67,0)).insert(pya.Box(1000,1000,1100,1100))
    if mutation=="outside_child":
        top.shapes(layout.layer(50,0)).insert(pya.Box(500,500,600,600))
    if mutation=="text":
        child.shapes(layout.layer(50,0)).insert(pya.Text("UNAPPROVED",pya.Trans(0,0)))
    return layout

def synthetic_owners(pya,contract,plan,placed):
    target={(tag,net):s.partition(row) for tag,rows in contract["owner_partitions"].items()
      for net,row in rows.items()}
    keys=list(target.values())+["synthetic-unrelated-partition-"+str(i)for i in range(109)]
    before={k:{m:pya.Region()for m in s.LAYERS}for k in keys}
    for tag,(x,y)in contract["placements"].items():
        for row in plan:
            before[target[(tag,row["net"])]][row["layer"]]+=pya.Region(
              pya.Box(*row["old"])).transformed(pya.Trans(x,y))
    for i,key in enumerate(keys[4:]):
        before[key][8]=pya.Region(pya.Box(4000000+i*1000,0,4000100+i*1000,100))
    before={k:{m:r.merged()for m,r in rows.items()}for k,rows in before.items()}
    after={k:dict(rows)for k,rows in before.items()}
    for (tag,net,layer),r in placed.items():
        key=target[(tag,net)]
        after[key][layer]=(after[key][layer]+r).merged()
    return before,after,target

def synthetic_controls(pya):
    contract=s.source_guard()
    metadata=dict(origin_translation_um=[-0.0,-3.97],routes=copy.deepcopy(contract["source_routes"]))
    plan=s.expected_plan(contract,metadata)
    old=geometry_fixture(pya,contract,plan,"baseline")
    new=geometry_fixture(pya,contract,plan)
    geometry,placed=s.geometry_proof(pya,old,new,contract,plan)
    assert len(geometry["typed_additions"])==26 and len(geometry["placed_additions"])==52
    before,after,target=synthetic_owners(pya,contract,plan,placed)
    ownership=s.owned_union(pya,before,after,target,placed)
    assert ownership["component_count"]==113 and ownership["checked_component_layers"]==1469
    assert len(ownership["changed"])==8
    rejected=[]
    for mode,reason in (
      ("remove_original","Original raw record or multiplicity removed"),
      ("missing","Exact 26 addition coordinates/multiplicity changed"),
      ("duplicate","Exact 26 addition coordinates/multiplicity changed"),
      ("shift","Exact 26 addition coordinates/multiplicity changed"),
      ("foreign_layer","Unauthorized raw addition type"),
      ("outside_child","Raw addition outside shared child"),
      ("text","Unauthorized raw addition type"),
      ("transform","Changed shared-child transform"),
      ("multiplicity","Changed shared-child multiplicity")):
        bad=geometry_fixture(pya,contract,plan,mode)
        rejected.append(reject(lambda:s.geometry_proof(pya,old,bad,contract,plan),reason,s.geometry_proof))
    first=target[("sd","M_SE")];second=target[("sc","M_SE")]
    other=next(k for k in after if k not in target.values())
    for mode in ("missing_component","missing_layer","missing_width","wrong_owner","foreign_layer","shifted_width","lost_original"):
        bad={k:dict(v)for k,v in after.items()}
        if mode=="missing_component":
            del bad[other];reason="Changed complete component partition set"
        elif mode=="missing_layer":
            del bad[other][19];reason="Incomplete owned layer census"
        else:
            reason="Owned full region differs from declared union"
            if mode=="missing_width":
                bad[first][50]=before[first][50]
            elif mode=="wrong_owner":
                bad[first][50],bad[second][50]=bad[second][50],bad[first][50]
            elif mode=="foreign_layer":
                bad[other][67]=pya.Region(pya.Box(100,100,200,200))
            elif mode=="shifted_width":
                bad[first][50]=bad[first][50].transformed(pya.Trans(5,0))
            elif mode=="lost_original":
                bad[other][8]=pya.Region()
        rejected.append(reject(lambda:s.owned_union(pya,before,bad,target,placed),reason,s.owned_union))
    for mode,reason in (("origin","Changed exact numeric child origin"),
      ("boolean_origin","Changed exact numeric child origin"),
      ("route","Changed source route rows"),("literal","Width literal/formula mismatch")):
        c=copy.deepcopy(contract);m=copy.deepcopy(metadata)
        if mode=="origin":
            m["origin_translation_um"][0]=.001
        elif mode=="boolean_origin":
            m["origin_translation_um"][0]=False
        elif mode=="route":
            next(r for r in m["routes"]if r["net"]=="M_SE")["escape_lane_um"]+=.005
        else:
            c["declared_rectangles"][0]["new"][0]+=5
        rejected.append(reject(lambda:s.expected_plan(c,m),reason,s.expected_plan))
    assert len(rejected)==20
    return dict(status="PASS_WIDTH_TOPOLOGY_SYNTHETIC_CONTROLS",positive_cases=3,
      rejected_cases=len(rejected),refusals=rejected,
      actual_pya_geometry_functions_exercised=True,actual_saved_candidate_read=False,
      fixture_scope="Synthetic two-cell geometry and synthetic113-partition Region maps. No native500-device/LVS qualification.",
      **s.FALSE)

def native_controls(pya,old_root,new_root,expected):
    """Only an externally authorized hosted stage may invoke this on restored roots."""
    complete=s.compare(pya,old_root,new_root,expected)
    old=complete["original_acquired_witness"];new=complete["fresh_acquired_witness"]
    identity_controls=s.identity.witness_controls(old,new)
    contract=s.source_guard()
    plan=s.expected_plan(contract,s.read(Path(old_root)/"parent/inputs/sampler_cd/layout/result.json"))
    old_layout,_=s.identity.read_side(pya,Path(old_root),s.FILES,s.ROOT/s.PRODUCER)
    new_layout,_=s.identity.read_side(pya,Path(new_root),s.FILES,s.ROOT/s.PRODUCER)
    original=s.acquire_regions(pya,old_layout,Path(old_root),old)
    fresh=s.acquire_regions(pya,new_layout,Path(new_root),new)
    target=s.targets(contract,old,new)
    _,placed=s.geometry_proof(pya,old_layout,new_layout,contract,plan)
    refusals=[]
    for mode,reason in (("duplicate","Exact 26 addition coordinates/multiplicity changed"),
      ("foreign_layer","Unauthorized raw addition type"),("outside_child","Raw addition outside shared child")):
        bad=pya.Layout();bad.read(str(Path(new_root)/s.FILES["gds"]))
        if mode=="duplicate":
            row=plan[0];bad.cell(s.CHILD).shapes(bad.layer(row["layer"],0)).insert(pya.Box(*row["new"]))
        elif mode=="foreign_layer":
            bad.cell(s.CHILD).shapes(bad.layer(67,0)).insert(pya.Box(1000,1000,1100,1100))
        else:
            # Inside the existing parent bbox; only the parent raw-record gate should reject.
            box=bad.cell(s.TOP).bbox();x=box.center().x;y=box.center().y
            bad.cell(s.TOP).shapes(bad.layer(50,0)).insert(pya.Box(x,y,x+5,y+5))
        refusals.append(reject(lambda:s.geometry_proof(pya,old_layout,bad,contract,plan),reason,s.geometry_proof))
    before=original["owned"];after=fresh["owned"]
    first=target[("sd","M_SE")];other=next(k for k in after if k not in target.values())
    for mode in ("missing_width","foreign_metal","foreign_via"):
        bad={k:dict(v)for k,v in after.items()}
        if mode=="missing_width":
            bad[first][50]=before[first][50]
        else:
            layer=67 if mode=="foreign_metal" else 133
            # Strictly outside this component's current bbox; nonempty added material.
            box=bad[other][layer].bbox();x=box.right+10000000;y=box.top+10000000
            bad[other][layer]=bad[other][layer]+pya.Region(pya.Box(x,y,x+5,y+5))
        refusals.append(reject(lambda:s.owned_union(pya,before,bad,target,placed),
          "Owned full region differs from declared union",s.owned_union))
    for mode,reason in (("global","Saved global region witness differs"),
      ("mapping","Saved native layer mapping differs"),
      ("component","Saved component geometry differs")):
        bad=copy.deepcopy(new)
        if mode=="global":
            bad["graph"]["layers"]["50"]["source_union_sha256"]="0"*64
        elif mode=="mapping":
            bad["graph"]["native_layer_mapping"]["50"]+=1000000
        else:
            bad["graph"]["wire_components"][0]["layers"]["50"]["area_dbu2"]+=1
        assert s.digest(bad)!=s.digest(new)
        refusals.append(reject(lambda:s.acquire_regions(pya,new_layout,Path(new_root),bad),reason,s.acquire_regions))
    assert len(refusals)==9
    assert s.inventory(old_root)==expected["old"] and s.inventory(new_root)==expected["fresh"]
    # Full positive after faults; all mutations above were in-memory copies only.
    pristine=s.compare(pya,old_root,new_root,expected)
    assert s.digest(pristine)==s.digest(complete)
    return dict(status="PASS_ACTUAL_WIDTH_NATIVE_FAULT_CONTROLS",positive_complete_comparisons=2,
      native_refusals=refusals,identity_controls=identity_controls,
      native_original_inputs_unchanged=True,comparison=complete,**s.FALSE)

def main():
    p=argparse.ArgumentParser()
    p.add_argument("--source-controls",action="store_true")
    p.add_argument("--native-synthetic","--synthetic",dest="synthetic",action="store_true")
    p.add_argument("--native",action="store_true")
    p.add_argument("--old-root",type=Path)
    p.add_argument("--new-root",type=Path)
    p.add_argument("--expected",type=Path)
    p.add_argument("--output",type=Path,required=True)
    args=p.parse_args()
    assert os.environ.get("GITHUB_ACTIONS")=="true" and os.environ.get("RUNNER_ENVIRONMENT")=="github-hosted"
    assert sum((args.source_controls,args.synthetic,args.native))<=1,"Select one hosted control mode"
    if not(args.synthetic or args.native):
        assert args.old_root is args.new_root is args.expected is None
        result=source_controls()
    elif args.synthetic:
        import pya
        assert args.old_root is args.new_root is args.expected is None
        result=synthetic_controls(pya)
    else:
        import pya
        # This entrypoint grants no authority and cannot restore/download any input.
        assert args.old_root and args.new_root and args.expected
        result=native_controls(pya,args.old_root,args.new_root,s.read(args.expected))
    assert args.output.parent.is_dir() and not args.output.exists() and not args.output.is_symlink()
    args.output.write_text(json.dumps(result,indent=2,sort_keys=True,allow_nan=False)+"\n")
    print(result["status"],flush=True)

if __name__=="__main__":
    main()
