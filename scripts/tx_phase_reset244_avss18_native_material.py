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
import make_pcie_tx_phase_reset244_avss18_v1 as candidate
LYP_SHA = "5d2a8f297dc951d97e1a0a1a4a2604eb756604b8ac443f5a69f31fc623d03974"
VERSION = "0.30.7"
FAULTS = ("old_geometry", "trunk_width", "trunk_center", "trunk_y", "trunk_other_layer",
          "unrelated_top_material", "changed_other_top_box", "changed_leaf_material",
          "changed_text_string", "changed_text_font", "changed_text_halign", "changed_text_valign", "instance_transform", "instance_array",
          "instance_target", "instance_property", "shape_property", "cell_property",
          "cell_name", "wrong_dbu")

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

def compare(pya, before, after, top, layer, old_box, new_box):
    assert before.dbu==after.dbu==0.001
    a,b=snapshot(before),snapshot(after)
    assert a["tops"]==b["tops"]==[top]
    assert set(a["layers"])==set(b["layers"]) and layer in a["layers"]
    assert set(a["cells"])==set(b["cells"])
    old_record,new_record=box_record(old_box),box_record(new_box)
    assert a["cells"][top]["shapes"][layer][old_record]==1
    assert a["cells"][top]["shapes"][layer][new_record]==0
    expected=copy.deepcopy(a["cells"])
    counter=expected[top]["shapes"][layer]
    counter.subtract({old_record:1}); counter+=Counter(); counter[new_record]+=1
    assert b["cells"]==expected,"Native hierarchy/shape/text/property/multiplicity differs outside one exact top rectangle"
    c0,c1=before.cell(top),after.cell(top)
    assert c0.bbox()==c1.bbox()
    materials=[]
    for key in sorted(a["layers"]):
        ra=pya.Region(c0.begin_shapes_rec(a["layers"][key]))
        rb=pya.Region(c1.begin_shapes_rec(b["layers"][key]))
        if key==layer:
            # Bind the complete material union, including any already-present
            # native material. Do not infer net ownership from this comparison.
            want=ra|pya.Region(new_box)
            assert (rb^want).is_empty() and (ra-rb).is_empty()
            added=rb-ra; exact=(pya.Region(new_box)-pya.Region(old_box))-ra
            assert (added^exact).is_empty() and not added.is_empty()
            materials.append(dict(layer=list(key),before_area_dbu2=ra.area(),after_area_dbu2=rb.area(),
                                  added_area_dbu2=added.area(),removed_area_dbu2=0,
                                  exact_expected_union=True))
        else:
            assert (ra^rb).is_empty(),("Unexpected material layer",key)
            materials.append(dict(layer=list(key),unchanged=True,area_dbu2=ra.area()))
    return dict(status="PASS_EXACT_ONE_AVSS_TOPMETAL1_RECTANGLE_NATIVE_DELTA_NO_ELECTRICAL_CLAIM",
                cells=len(a["cells"]),layers=len(a["layers"]),top=top,dbu_um=.001,
                total_shapes=sum(sum(v.values()) for c in a["cells"].values() for v in c["shapes"].values()),
                total_instances=sum(sum(c["instances"].values()) for c in a["cells"].values()),
                changed_shape_records=1,old_box_dbu=str(old_box),new_box_dbu=str(new_box),
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

def mutate(pya,layout,top,layer,new_box,name):
    c=layout.cell(top);i=layer_map(layout)[layer]
    if name in ("trunk_width","trunk_center","trunk_y","trunk_other_layer","shape_property"):
        s=find_box(layout,top,layer,new_box)
        if name=="trunk_width":s.box=pya.Box(new_box.left,new_box.bottom,new_box.right+5,new_box.top)
        elif name=="trunk_center":s.box=pya.Box(new_box.left+5,new_box.bottom,new_box.right+5,new_box.top)
        elif name=="trunk_y":s.box=pya.Box(new_box.left,new_box.bottom,new_box.right,new_box.top-5)
        elif name=="shape_property":s.set_property(999,"fault")
        else:
            box=s.box; c.shapes(i).erase(s); c.shapes(layout.layer(8,0)).insert(box)
    elif name=="unrelated_top_material": c.shapes(layout.layer(8,0)).insert(pya.Box(1000,1000,1100,1100))
    elif name=="changed_other_top_box":
        s=next(s for index in layout.layer_indices() for s in c.each_shape(index) if s.is_box() and s.box!=new_box)
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
        entries=[p for p in ET.parse(lyp).getroot().iter("properties") if p.findtext("name")=="TopMetal1.drawing"]
        assert len(entries)==1;raw_layer_source=entries[0].findtext("source")
        match=re.fullmatch(r"([0-9]+)/([0-9]+)(?:@[0-9]+)?",raw_layer_source);assert match
        layer=(int(match[1]),int(match[2]));assert layer[1]==0
        import pya
        assert pya.__version__==old_report["klayout_version"]==VERSION
        original=load(pya,old/(top+".gds"));changed=load(pya,new/(top+".gds"))
        old_box=native_box(pya,candidate.OLD_RECT,old_report["origin_translation_um"])
        new_box=native_box(pya,candidate.NEW_RECT,old_report["origin_translation_um"])
        report.update(polarity=pol,runtime_klayout_version=pya.__version__,layer_map_sha256=LYP_SHA,
                      actual_topmetal1_layer=list(layer),actual_layer_source=raw_layer_source,input_sha256=immutable)
        text_proofs=[]
        for label,layout in (("original",original),("candidate",changed)):
            shape=first_text(layout);record=shape_record(shape)
            assert type(record["value"]["halign"]) is type(record["value"]["valign"]) is int
            assert canonical(json.loads(canonical(record)))==canonical(record)
            assert record["value"]["halign"]==int(shape.text.halign)
            assert record["value"]["valign"]==int(shape.text.valign)
            text_proofs.append(dict(layout=label,actual_native_text=record,json_roundtrip=True))
        report["actual_text_serialization_positives"]=text_proofs
        report["native_comparison"]=compare(pya,original,changed,top,layer,old_box,new_box);save()
        faults=[]
        for name in FAULTS:
            trial=load(pya,(old if name=="old_geometry" else new)/(top+".gds"))
            if name!="old_geometry":mutate(pya,trial,top,layer,new_box,name)
            try:compare(pya,original,trial,top,layer,old_box,new_box)
            except (AssertionError,ValueError,RuntimeError) as e:faults.append(dict(name=name,rejected=True,error=repr(e)))
            else:raise AssertionError("Accepted actual native material fault "+name)
            report["actual_native_faults"]=faults;save()
        assert len(faults)==20
        # Reread the pristine candidate after actual in-memory corruptions.
        report["post_fault_positive"]=compare(pya,original,load(pya,new/(top+".gds")),top,layer,old_box,new_box)
        assert all(sha(Path(p))==h for p,h in immutable.items()) and sha(lyp)==LYP_SHA
        report.update(status="PASS_EXACT_AVSS18_NATIVE_MATERIAL_AND20_ACTUAL_FAULTS_REQUIRES_DRC_LVS_RC_LOADED",
                      native_geometry_delta_proved=True,all_inputs_byte_unchanged=True,
                      no_GDS_written=True,original_electrical_rejection_preserved=True)
    except BaseException as e:
        report.update(status="FAIL_OR_ERROR",error=repr(e),traceback=traceback.format_exc());raise
    finally:save()

if __name__=="__main__":main()
