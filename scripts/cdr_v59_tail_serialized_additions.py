#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0
"""Read-only, source-bound admission for seventeen acquired rectangle records only."""
import collections
import json
import re
import cdr_v59_tail_saved_identity as source

TOP="nssoc_cdr_pd500_resistor_v59"
CHILD="pd_child_sampler_cd"
CONTRACT="docs/evidence/cdr-v59-tail-serialized-additions-contract-20261026.json"
DIAGNOSTIC_SHA="57d0d5cc7609908dffd95905df571b42bc987947611a46a1613a2ef69fae609b"
RAW_ERROR="Original shape/text/properties or exact added records changed"

def require(value,message):
    if not value:raise AssertionError(message)

def rectangle(record):
    require(isinstance(record,(list,tuple)) and len(record)==5,"Invalid complete raw record")
    layer,datatype,text,properties,is_text=record
    require(type(layer) is int and type(datatype) is int and isinstance(text,str)
      and isinstance(properties,str) and type(is_text) is bool,"Invalid raw record types")
    require((layer,datatype) in ((126,0),(133,0),(134,0)),"Unapproved addition layer/datatype")
    require(properties=="{}" and is_text is False,"Addition properties or text changed")
    box=re.fullmatch(r"box \((-?\d+),(-?\d+);(-?\d+),(-?\d+)\)",text)
    polygon=re.fullmatch(r"polygon \((-?\d+),(-?\d+);(-?\d+),(-?\d+);(-?\d+),(-?\d+);(-?\d+),(-?\d+)\)",text)
    require(box is not None or polygon is not None,"Addition is not an exact box or four-corner polygon")
    if box:
        x0,y0,x1,y1=map(int,box.groups())
        require(x0<x1 and y0<y1,"Degenerate or reversed rectangle")
        kind="box"
    else:
        x0,y0,xa,ya,x1,y1,xb,yb=map(int,polygon.groups())
        require(x0==xa<x1==xb and y0==yb<ya==y1,"Nonrectangular or self-intersecting polygon")
        kind="polygon"
    return (layer,datatype,x0,y0,x1,y1,properties,is_text),kind

def load_contract(generation):
    path=source.ROOT/CONTRACT
    pins=source.methods()["protected_sha256"]
    require(CONTRACT in pins and source.sha(path)==pins[CONTRACT],"Unprotected rectangle contract")
    return validate_contract(source.read_json(path),generation)

def validate_contract(contract,generation):
    require(contract["schema"]=="cdr-v59-exact17-serialized-additions-v1"
      and contract["diagnostic_sha256"]==DIAGNOSTIC_SHA
      and contract["diagnostic_run"]==40392469979
      and contract["target_cell"]==CHILD,"Wrong acquired rectangle contract")
    require(source.value_hash(generation)==contract["generation_value_sha256"],"Original generation metadata changed")
    pairs=contract["pairs"]
    require(len(pairs)==17,"Exact seventeen authorized additions required")
    expected=collections.Counter()
    prewrite=collections.Counter()
    for pair in pairs:
        before=pair["prewrite_record"];after=pair["serialized_record"]
        a,ak=rectangle(before);b,bk=rectangle(after)
        require(ak=="polygon" and bk=="box" and a==b and type(pair["multiplicity"]) is int and pair["multiplicity"]==1,
          "Unqualified serialization pair")
        require(pair["exact_rectangle_bounds_dbu"]==list(a[2:6]),"Contract rectangle coordinates changed")
        expected[a]+=1;prewrite[tuple(before)]+=1
    require(len(expected)==17 and all(v==1 for v in expected.values()),"Duplicate authorized rectangle")
    require(collections.Counter(k[0] for k in expected)=={126:8,133:8,134:1},"Authorized layer distribution changed")
    require(collections.Counter(tuple(r) for r in generation["added_raw_records"])==prewrite,
      "Original seventeen prewrite additions changed")
    return contract,expected

def reproduce_original_failure(original,old_layout,new_layout,generation,generator):
    try:original(old_layout,new_layout,generation,generator)
    except AssertionError as error:
        frames=[];tb=error.__traceback__
        while tb:
            frames.append(tb);tb=tb.tb_next
        require(error.args==(RAW_ERROR,) and len(frames)>=2
          and frames[-2].tb_frame.f_code is original.__code__
          and frames[-1].tb_frame.f_code.co_name=="require",
          "Original exact raw rejection was not reproduced")
        return {"status":"ORIGINAL_EXACT_RAW_GUARD_FAILURE_REPRODUCED",
          "error":repr(error),"file":original.__code__.co_filename,
          "function":original.__name__,"line":frames[-2].tb_lineno,
          "original_guard_passed":False,"original_failure_preserved":True}
    raise AssertionError("Original exact raw guard unexpectedly passed")

def verify(pya,properties,old_layout,new_layout,generation,generator):
    contract,expected=load_contract(generation)
    scope={"json":json}
    source.load_definitions(generator,["raw_records","hierarchy"],scope)
    old_names=sorted(c.name for c in old_layout.each_cell())
    new_names=sorted(c.name for c in new_layout.each_cell())
    require(old_names==new_names==contract["cell_names"],"Complete cell-name inventory changed")
    require(old_layout.dbu==new_layout.dbu==contract["dbu_um"],"Original DBU changed")
    require(str(old_layout.cell(TOP).bbox())==str(new_layout.cell(TOP).bbox())==contract["top_bbox_dbu"],
      "Original top bbox changed")
    proof=[];typed=[]
    for name in old_names:
        old=old_layout.cell(name);new=new_layout.cell(name)
        a=scope["raw_records"](old_layout,old);b=scope["raw_records"](new_layout,new)
        ca=collections.Counter(a);cb=collections.Counter(b)
        require(not(ca-cb),"Original raw record or multiplicity changed")
        ha=scope["hierarchy"](old);hb=scope["hierarchy"](new)
        require(ha==hb,"Original named hierarchy changed")
        props=lambda cell:[{"child":i.cell.name,"ordinal":j,"properties":properties(i)}
          for j,i in enumerate(cell.each_inst())]
        pa=props(old);pb=props(new)
        require(pa==pb,"Original instance property/order changed")
        added=cb-ca
        if name!=CHILD:
            require(not added,"Addition outside authorized target child")
        else:
            acquired=collections.Counter()
            for record,count in added.items():
                key,kind=rectangle(record);acquired[key]+=count
            require(acquired==expected,"Exact authorized addition coordinates or multiplicities changed")
            remaining=added.copy()
            for li in new_layout.layer_indexes():
                info=new_layout.get_info(li)
                for shape in new.shapes(li).each():
                    record=(info.layer,info.datatype,shape.to_s(),
                      json.dumps(shape.properties(),sort_keys=True,separators=(",",":")),shape.is_text())
                    if remaining[record]<=0:continue
                    key,kind=rectangle(record)
                    require((kind=="box" and shape.is_box()) or (kind=="polygon" and shape.is_polygon()),
                      "Native addition type disagrees with exact raw record")
                    actual=shape.polygon
                    require(actual is not None and actual.holes()==0 and actual.num_points_hull()==4
                      and actual.is_box(),"Native addition is not a simple rectangle")
                    expected_polygon=pya.Polygon(pya.Box(*key[2:6]))
                    require(actual==expected_polygon,"Native typed rectangle geometry changed")
                    typed.append({"raw_record":list(record),"multiplicity":1,
                      "exact_bounds_dbu":list(key[2:6]),"native_typed_polygon_equal":True,
                      "native_holes":actual.holes(),"native_hull_points":actual.num_points_hull()})
                    remaining[record]-=1
            require(not +remaining and len(typed)==17,"Incomplete native typed addition census")
        proof.append({"cell":name,"original_raw_records":len(a),"current_raw_records":len(b),
          "original_raw_sha256":source.value_hash(a),"current_raw_sha256":source.value_hash(b),
          "original_raw_records_and_multiplicity_exact":True,"named_hierarchy":ha,
          "instance_properties_and_order":pa,"authorized_addition_count":sum(added.values())})
    return {"status":"PASS_EXACT17_SERIALIZED_ADDITIONS_WITH_ALL_ORIGINAL_RAW_RECORDS",
      "contract_path":CONTRACT,"contract_sha256":source.sha(source.ROOT/CONTRACT),
      "all_original_raw_records_and_multiplicities_preserved":True,
      "all_original_properties_text_and_hierarchy_preserved":True,
      "cells":proof,"native_typed_additions":typed,
      "permitted_representation_difference":"Only protected seventeen rectangular polygon/box additions",
      "blanket_normalization_applied":False,"area_only_equality_used":False,
      "original_exact_guard_passed":False,"original_failure_preserved":True,
      "physical_accepted":False,"electrical_accepted":False}
