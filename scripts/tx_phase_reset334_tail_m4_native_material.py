#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0
"""Read-only native GDS comparison; fault layouts exist only in hosted RAM."""
import argparse, copy, hashlib, json, os, re, sys, traceback
from collections import Counter
from decimal import Decimal
from pathlib import Path
import xml.etree.ElementTree as ET
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "hw/soc/flow"))
import make_pcie_tx_phase_reset334_tail_m4_v1 as candidate
LYP_SHA = "5d2a8f297dc951d97e1a0a1a4a2604eb756604b8ac443f5a69f31fc623d03974"
VERSION = "0.30.7"
FAULTS = ("old_geometry", "trunk_width", "trunk_center", "trunk_y", "trunk_other_layer",
          "unrelated_top_material", "changed_other_top_box", "changed_leaf_material",
          "changed_text_string", "changed_text_font", "changed_text_halign", "changed_text_valign", "instance_transform", "instance_array",
          "instance_target", "instance_property", "shape_property", "cell_property",
          "cell_name", "wrong_dbu")
FAULTS = FAULTS + tuple("width_target_"+str(i)for i in range(12)) + ("omit_last","retain_old","duplicate_new","split_new","wrong_M5")

def sha(path):
    with Path(path).open("rb") as f: return hashlib.file_digest(f, "sha256").hexdigest()

def canonical(value):
    return json.dumps(value, sort_keys=True, separators=(",", ":"), allow_nan=False)

def props(value):
    # GDS property keys are integers; retain both type and value, not layout-local IDs.
    p = value.properties()
    assert isinstance(p, dict)
    return sorted([(type(k).__name__, repr(k), type(v).__name__, repr(v)) for k, v in p.items()])

def shape_record(s):
    if s.is_box():
        b=s.box; kind="box"; value=[b.left,b.bottom,b.right,b.top]
    elif s.is_simple_polygon(): kind="simple_polygon"; value=str(s.simple_polygon)
    elif s.is_polygon(): kind="polygon"; value=str(s.polygon)
    elif s.is_path(): kind="path"; value=str(s.path)
    elif s.is_text():
        t=s.text; kind="text"
        value=dict(string=t.string,trans=str(t.trans),size=t.size,font=t.font,halign=int(t.halign),valign=int(t.valign))
    else: raise AssertionError(("Unsupported native GDS shape",str(s)))
    return dict(kind=kind,value=value,properties=props(s))

def instance_record(i):
    return dict(child=i.cell.name,transform=str(i.cplx_trans),a=str(i.a),b=str(i.b),
                na=i.na,nb=i.nb,properties=props(i))

def layer_map(layout):
    answer={}
    for i in layout.layer_indices():
        info=layout.get_info(i); key=(info.layer,info.datatype)
        assert key not in answer
        answer[key]=i
    return answer

def snapshot(layout):
    layers=layer_map(layout); cells={}
    for c in layout.each_cell():
        assert c.name not in cells
        cells[c.name]=dict(properties=props(c),bbox=str(c.bbox()),
            instances=Counter(canonical(instance_record(i)) for i in c.each_inst()),
            shapes={key:Counter(canonical(shape_record(s)) for s in c.each_shape(index)) for key,index in layers.items()})
    return dict(dbu=layout.dbu,tops=sorted(c.name for c in layout.top_cells()),cells=cells,layers=layers)

def native_box(pya, coordinates, translation):
    values=[]
    for i,v in enumerate(coordinates):
        d=(Decimal(str(v))+Decimal(str(translation[i%2])))/Decimal("0.001")
        assert d==d.to_integral_value()
        values.append(int(d))
    return pya.Box(*values)

def box_record(box):
    return canonical(dict(kind="box",value=[box.left,box.bottom,box.right,box.top],properties=[]))

def compare(pya,before,after,top,layer,plan):
    assert before.dbu==after.dbu==.001 and layer==(50,0)
    assert len(plan)==12 and {r["net"]for r in plan}==set(candidate.TAIL_NETS)
    assert Counter((r["net"],r["role"])for r in plan)==Counter((n,k)for n in candidate.TAIL_NETS for k in ("XSA","XSB","XT"))
    old_coords=[tuple(r["old_native_box_dbu"])for r in plan]
    new_coords=[tuple(r["new_native_box_dbu"])for r in plan]
    assert len(set(old_coords))==len(set(new_coords))==12
    old_boxes=[];new_boxes=[]
    for r,a,b in zip(plan,old_coords,new_coords,strict=True):
        assert r["layer"]==[50,0] and all(type(v)is int for v in a+b)
        assert a[2]-a[0]==1200 and b==(a[0]-600,a[1],a[2]+600,a[3]) and a[3]>a[1]
        old_boxes.append(pya.Box(*a));new_boxes.append(pya.Box(*b))
    a,b=snapshot(before),snapshot(after)
    assert a["tops"]==b["tops"]==[top]
    assert set(a["layers"])==set(b["layers"]) and layer in a["layers"]
    assert set(a["cells"])==set(b["cells"])
    expected=copy.deepcopy(a["cells"]);counter=expected[top]["shapes"][layer]
    old_records=[box_record(v)for v in old_boxes];new_records=[box_record(v)for v in new_boxes]
    assert not set(old_records)&set(new_records)
    for old_record,new_record in zip(old_records,new_records,strict=True):
        assert a["cells"][top]["shapes"][layer][old_record]==1
        assert a["cells"][top]["shapes"][layer][new_record]==0
        counter.subtract({old_record:1});counter[new_record]+=1
    counter+=Counter()
    assert b["cells"]==expected,"Raw hierarchy/shape/text/property/multiplicity differs outside12 exact M4 boxes"
    c0,c1=before.cell(top),after.cell(top);assert c0.bbox()==c1.bbox()
    old_union=pya.Region();new_union=pya.Region()
    for box in old_boxes:old_union.insert(box)
    for box in new_boxes:new_union.insert(box)
    materials=[]
    for key in sorted(a["layers"]):
        ra=pya.Region(c0.begin_shapes_rec(a["layers"][key]))
        rb=pya.Region(c1.begin_shapes_rec(b["layers"][key]))
        if key==layer:
            want=ra|new_union;added=rb-ra;exact=new_union-ra
            assert (rb^want).is_empty() and (ra-rb).is_empty()
            assert (added^exact).is_empty() and not added.is_empty()
            assert (old_union-new_union).is_empty()
            materials.append(dict(layer=list(key),before_area_dbu2=ra.area(),after_area_dbu2=rb.area(),
                added_area_dbu2=added.area(),removed_area_dbu2=0,exact_expected_union=True))
        else:
            assert (ra^rb).is_empty(),("Unexpected material layer",key)
            materials.append(dict(layer=list(key),unchanged=True,area_dbu2=ra.area()))
    return dict(status="PASS_EXACT12_TAIL_M4_BOXES_NATIVE_DELTA_NOT_ELECTRICAL",
        cells=len(a["cells"]),layers=len(a["layers"]),top=top,dbu_um=.001,
        total_shapes=sum(sum(v.values())for c in a["cells"].values()for v in c["shapes"].values()),
        total_instances=sum(sum(c["instances"].values())for c in a["cells"].values()),
        changed_shape_records=12,exact_target_plan=plan,
        original_multisets_sha256=hashlib.sha256(canonical({name:{"properties":c["properties"],"bbox":c["bbox"],"instances":dict(c["instances"]),"shapes":{str(k):dict(v)for k,v in c["shapes"].items()}}for name,c in a["cells"].items()}).encode()).hexdigest(),
        all_non_target_shapes_text_properties_instances_equal=True,materials=materials,
        native_net_ownership_proved=False,DRC_LVS_proved=False,RC_or_electrical_accepted=False)

def load(pya,path):
    layout=pya.Layout();layout.read(str(path));return layout

def find_box(layout,top,layer,box):
    c=layout.cell(top);i=layer_map(layout)[layer]
    rows=[s for s in c.each_shape(i) if s.is_box() and s.box==box and props(s)==[]]
    assert len(rows)==1
    return rows[0]

def first_text(layout):
    for c in layout.each_cell():
        for i in layout.layer_indices():
            for s in c.each_shape(i):
                if s.is_text(): return s
    raise AssertionError("No actual native text available for control")

def mutate(pya,layout,top,layer,plan,name):
    new_boxes=[pya.Box(*r["new_native_box_dbu"])for r in plan]
    old_boxes=[pya.Box(*r["old_native_box_dbu"])for r in plan]
    new_box=new_boxes[0]
    c=layout.cell(top);i=layer_map(layout)[layer]
    if name.startswith("width_target_"):
        index=int(name.rsplit("_",1)[1]);assert 0<=index<12
        s=find_box(layout,top,layer,new_boxes[index]);b=s.box
        s.box=pya.Box(b.left,b.bottom,b.right+5,b.top)
    elif name in ("omit_last","retain_old","duplicate_new","split_new","wrong_M5"):
        index=11 if name=="omit_last"else 0
        box=new_boxes[index];s=find_box(layout,top,layer,box)
        if name=="omit_last":s.box=old_boxes[index]
        elif name=="retain_old":c.shapes(i).insert(old_boxes[index])
        elif name=="duplicate_new":c.shapes(i).insert(box)
        elif name=="wrong_M5":
            c.shapes(i).erase(s);c.shapes(layout.layer(67,0)).insert(box)
        else:
            c.shapes(i).erase(s);mid=(box.left+box.right)//2
            c.shapes(i).insert(pya.Box(box.left,box.bottom,mid,box.top))
            c.shapes(i).insert(pya.Box(mid,box.bottom,box.right,box.top))
    elif name in ("trunk_width","trunk_center","trunk_y","trunk_other_layer","shape_property"):
        s=find_box(layout,top,layer,new_box)
        if name=="trunk_width":s.box=pya.Box(new_box.left,new_box.bottom,new_box.right+5,new_box.top)
        elif name=="trunk_center":s.box=pya.Box(new_box.left+5,new_box.bottom,new_box.right+5,new_box.top)
        elif name=="trunk_y":s.box=pya.Box(new_box.left,new_box.bottom,new_box.right,new_box.top-5)
        elif name=="shape_property":s.set_property(999,"fault")
        else:
            box=s.box; c.shapes(i).erase(s); c.shapes(layout.layer(8,0)).insert(box)
    elif name=="unrelated_top_material": c.shapes(layout.layer(8,0)).insert(pya.Box(1000,1000,1100,1100))
    elif name=="changed_other_top_box":
        s=next(s for index in layout.layer_indices() for s in c.each_shape(index) if s.is_box() and all(s.box!=v for v in new_boxes))
        b=s.box;s.box=pya.Box(b.left,b.bottom,b.right+5,b.top)
    elif name=="changed_leaf_material":
        leaves=[v for v in layout.each_cell() if v.name!=top and not list(v.each_inst())]
        assert leaves;leaf=leaves[0]
        leaf.shapes(layout.layer(8,0)).insert(pya.Box(0,0,5,5))
    elif name in ("changed_text_string","changed_text_font","changed_text_halign","changed_text_valign"):
        s=first_text(layout); t=s.text
        if name=="changed_text_string": t.string=t.string+"_fault"
        elif name=="changed_text_font":t.font=2 if t.font!=2 else 1
        elif name=="changed_text_halign":
            old=int(t.halign)
            t.halign=pya.Text.HAlignRight if t.halign==pya.Text.HAlignLeft else pya.Text.HAlignLeft
            assert int(t.halign)!=old
        else:
            old=int(t.valign)
            t.valign=pya.Text.VAlignTop if t.valign==pya.Text.VAlignBottom else pya.Text.VAlignBottom
            assert int(t.valign)!=old
        s.text=t
    elif name in ("instance_transform","instance_array","instance_target","instance_property"):
        item=next(c.each_inst())
        if name=="instance_transform":item.transform(pya.Trans(5,0))
        elif name=="instance_array":item.na=item.na+1
        elif name=="instance_property":item.set_property(999,"fault")
        else:
            alternative=next(v for v in layout.each_cell() if v.name not in (top,item.cell.name))
            item.cell_index=alternative.cell_index()
    elif name=="cell_property":c.set_property(999,"fault")
    elif name=="cell_name":next(v for v in layout.each_cell() if v.name!=top).name+="_fault"
    elif name=="wrong_dbu":layout.dbu=.002
    else:raise AssertionError(name)

def main():
    candidate.host()
    assert candidate.methods()["native_material_authorized"] is True,"Disabled native material comparison"
    parser=argparse.ArgumentParser();parser.add_argument("--baseline",type=Path,required=True)
    parser.add_argument("--candidate",type=Path,required=True);parser.add_argument("--preset",choices=("p","n"),required=True)
    parser.add_argument("--pdk",type=Path,required=True);parser.add_argument("--output",type=Path,required=True)
    args=parser.parse_args();out=args.output;assert not out.exists();out.parent.mkdir(parents=True,exist_ok=True)
    report=dict(status="RUNNING",native_geometry_delta_proved=False,DRC_LVS_proved=False,RC_or_electrical_accepted=False)
    def save():out.write_text(json.dumps(report,indent=2,allow_nan=False)+"\n")
    save()
    try:
        full=candidate.baseline();pol=args.preset;top="nssoc_tx_phase_reset244_"+pol+"_v1"
        old=args.baseline;new=args.candidate
        names=(top+".gds",top+".lef","schematic.cir","result.json")
        before_hash={str(old/n):full["outputs"][pol+"/layout/"+n]for n in names}
        assert all(sha(Path(p))==h for p,h in before_hash.items())
        old_report=json.loads((old/"result.json").read_text());new_report=json.loads((new/"result.json").read_text())
        assert old_report==full["variants"][pol]["generation"]
        report["generation_comparison"]=candidate.validate_generation(old_report,new_report,pol)
        assert (old/"schematic.cir").read_bytes()==(new/"schematic.cir").read_bytes()
        assert (old/(top+".lef")).read_bytes()==(new/(top+".lef")).read_bytes()
        assert sha(new/(top+".gds"))==new_report["output_sha256"][top+".gds"]
        immutable={**before_hash,**{str(new/n):sha(new/n) for n in names}}
        lyp=args.pdk/"libs.tech/klayout/tech/sg13g2.lyp";assert sha(lyp)==LYP_SHA
        entries=[p for p in ET.parse(lyp).getroot().iter("properties") if p.findtext("name")=="Metal4.drawing"]
        assert len(entries)==1;raw_layer_source=entries[0].findtext("source")
        match=re.fullmatch(r"([0-9]+)/([0-9]+)(?:@[0-9]+)?",raw_layer_source);assert match
        layer=(int(match[1]),int(match[2]));assert layer[1]==0
        import pya
        assert pya.__version__==old_report["klayout_version"]==VERSION
        original=load(pya,old/(top+".gds"));changed=load(pya,new/(top+".gds"))
        plan=candidate.target_plan(old_report)
        assert plan==new_report["tail_m4_plan"] and layer==(50,0)
        report.update(polarity=pol,runtime_klayout_version=pya.__version__,layer_map_sha256=LYP_SHA,
                      actual_metal4_layer=list(layer),actual_layer_source=raw_layer_source,input_sha256=immutable)
        text_proofs=[]
        for label,layout in (("original",original),("candidate",changed)):
            shape=first_text(layout);record=shape_record(shape)
            assert type(record["value"]["halign"]) is type(record["value"]["valign"]) is int
            assert canonical(json.loads(canonical(record)))==canonical(record)
            assert record["value"]["halign"]==int(shape.text.halign)
            assert record["value"]["valign"]==int(shape.text.valign)
            text_proofs.append(dict(layout=label,actual_native_text=record,json_roundtrip=True))
        report["actual_text_serialization_positives"]=text_proofs
        report["native_comparison"]=compare(pya,original,changed,top,layer,plan);save()
        faults=[]
        for name in ("duplicate_descriptor","wrong_descriptor_net","moved_descriptor_dbu"):
            bad_plan=copy.deepcopy(plan)
            if name=="duplicate_descriptor":bad_plan[-1]=copy.deepcopy(bad_plan[0])
            elif name=="wrong_descriptor_net":bad_plan[0]["net"]="UNLISTED_TAIL"
            else:
                for key in ("old_native_box_dbu","new_native_box_dbu"):
                    bad_plan[0][key][0]+=1;bad_plan[0][key][2]+=1
            try:compare(pya,original,changed,top,layer,bad_plan)
            except (AssertionError,ValueError,RuntimeError)as e:
                faults.append(dict(name=name,rejected=True,error=repr(e)))
            else:raise AssertionError("Accepted native descriptor fault "+name)
            report["actual_native_faults"]=faults;save()
        for name in FAULTS:
            trial=load(pya,(old if name=="old_geometry" else new)/(top+".gds"))
            if name!="old_geometry":mutate(pya,trial,top,layer,plan,name)
            try:compare(pya,original,trial,top,layer,plan)
            except (AssertionError,ValueError,RuntimeError) as e:faults.append(dict(name=name,rejected=True,error=repr(e)))
            else:raise AssertionError("Accepted actual native material fault "+name)
            report["actual_native_faults"]=faults;save()
        assert len(faults)==40
        # Reread the pristine candidate after actual in-memory corruptions.
        report["post_fault_positive"]=compare(pya,original,load(pya,new/(top+".gds")),top,layer,plan)
        assert all(sha(Path(p))==h for p,h in immutable.items()) and sha(lyp)==LYP_SHA
        report.update(status="PASS_EXACT12_TAIL_M4_NATIVE_MATERIAL_AND40_ACTUAL_FAULTS_REQUIRES_DRC_LVS_RC_LOADED",
                      native_geometry_delta_proved=True,all_inputs_byte_unchanged=True,
                      no_GDS_written=True,original_electrical_rejection_preserved=True)
    except BaseException as e:
        report.update(status="FAIL_OR_ERROR",error=repr(e),traceback=traceback.format_exc());raise
    finally:save()

if __name__=="__main__":main()
