#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0
"""Native independent source-child projection and unchanged fresh graph readers."""
import argparse, importlib.util, json, sys
from collections import Counter
from pathlib import Path
import cdr_v59_selector_column_width_graph as s
import generate_cdr_v59_selector_column_width as generator
frozen=generator.frozen

def drawings(pya,layout,cell):
    result={}
    for li in layout.layer_indexes():
        info=layout.get_info(li)
        if info.layer in (8,10,30,50,67,126,134)and info.datatype in (2,25):continue
        r=pya.Region(cell.begin_shapes_rec(li)).flatten().merged()
        if not r.is_empty():result[(info.layer,info.datatype)]=r
    s.require(bool(result),"Empty independent source drawing")
    return result

def project_reference(out):
    import pya
    out=Path(out);s.validate_view(out);s.check_derived(out)
    parent=out/"candidate/parent";base=s.baseline(out)/"parent"
    meta=s.read(parent/"layout/result.json");manifest=s.read(parent/"children.json")
    name=meta["source_plan"]["types"]["sampler_cd"]["top"]
    rel=Path(manifest["children"]["sampler_cd"]["directory"])/(name+".gds")
    source=s.regular(base,rel.as_posix());dest=s.regular(parent,rel.as_posix())
    s.require(s.sha(dest)==s.sha(source),"Copied independent source differs")
    childmeta=s.read(base/"inputs/sampler_cd/layout/result.json")
    s.previous.inherited.origin_exact(childmeta["origin_translation_um"],[0,-3.97],"Changed child origin")
    contract=s.read(generator.CONTRACT);proposal=generator.boxes(contract,childmeta["routes"])
    original_inputs={p.relative_to(parent).as_posix():s.sha(p)for p in (parent/"inputs").rglob("*")if p.is_file()}
    old=pya.Layout();old.read(str(base/"layout"/(s.TOP+".gds")))
    layout=pya.Layout();layout.read(str(source));child=layout.cell(name)
    s.require(layout.dbu==old.dbu==.001 and child is not None,"Wrong source native hierarchy")
    s.require(child.dbbox().left==child.dbbox().bottom==0,"Unnormalized independent source child")
    original=old.cell("pd_child_sampler_cd");s.require(original is not None,"Baseline parent child missing")
    frozen.same_material(pya,drawings(pya,layout,child),drawings(pya,old,original))
    before={c.name:(frozen.material(pya,layout,c),frozen.raw_records(layout,c),frozen.hierarchy(c))
      for c in layout.each_cell()}
    bbox=child.bbox();expected=dict(before[name][0])
    for row in proposal:
        key=(row["layer"],0);box=pya.Box(*row["new"])
        previous=[shape for shape in child.shapes(layout.layer(*key)).each()
          if shape.is_box()and shape.box==pya.Box(*row["old"])and shape.properties()=={}]
        s.require(len(previous)==1,"Independent original rectangle absent or ambiguous")
        child.shapes(layout.layer(*key)).insert(box)
        expected[key]=(expected.get(key,pya.Region())+pya.Region(box)).merged()
    expected_raw=frozen.raw_records(layout,child)
    prior=Counter(before[name][1]);after=Counter(expected_raw);extras=list((after-prior).elements())
    s.require(not(prior-after)and len(extras)==26,"Independent raw delta is not exactly26")
    s.require(all((r[0],r[1])in generator.KEYS and r[3]=="{}"and r[4]is False for r in extras),"Unexpected raw addition")
    def verify(candidate):
        s.require(candidate.dbu==.001 and {c.name for c in candidate.each_cell()}==set(before),"Source cell inventory changed")
        s.require(candidate.cell(name).bbox()==bbox,"Independent source bbox changed")
        for cellname,(material,raw,instances)in before.items():
            c=candidate.cell(cellname)
            frozen.same_material(pya,expected if cellname==name else material,frozen.material(pya,candidate,c))
            s.require(frozen.raw_records(candidate,c)==(expected_raw if cellname==name else raw),"Source raw/text/properties changed")
            s.require(frozen.hierarchy(c)==instances,"Independent hierarchy changed")
    verify(layout);layout.write(str(dest))
    reread=pya.Layout();reread.read(str(dest));verify(reread)
    after_inputs={p.relative_to(parent).as_posix():s.sha(p)for p in (parent/"inputs").rglob("*")if p.is_file()}
    s.require(set(after_inputs)==set(original_inputs),"Source file census changed")
    s.require({n for n in original_inputs if after_inputs[n]!=original_inputs[n]}=={rel.as_posix()},"Unexpected reference file mutation")
    s.require(s.sha(parent/"layout"/(s.TOP+".gds"))==s.GDS_SHA,"Physically qualified parent changed")
    s.validate_view(out)
    result=dict(status="PASS_INDEPENDENT26BOX_SOURCE_REFERENCE_AND_SERIALIZED_REREAD",
      source_child_relative=str((Path("parent")/rel).as_posix()),source_child_before_sha256=s.sha(source),
      source_child_after_sha256=s.sha(dest),original_parent_gds_sha256=s.GDS_SHA,
      original_source_child_drawings_matched_parent=True,added_raw_record_count=len(extras),
      added_raw_records=extras,proposal=proposal,all_original_source_raw_text_properties_hierarchy_preserved=True,
      original_input_hashes=original_inputs,derived_input_hashes=after_inputs,
      inputs={str(p):s.sha(p)for p in (source,base/"layout"/(s.TOP+".gds"),generator.CONTRACT,
        base/"inputs/sampler_cd/layout/result.json",parent/"layout"/(s.TOP+".gds"))},
      independent_source_used=True,parent_as_own_reference_used=False,original_capsule_unmodified=True,
      engineering_parent_geometry_edited=False,new_physical_qualification=False,qualified_pex=False,
      graph_equivalence_accepted=False,electrical_accepted=False,full_phy_accepted=False)
    s.atomic(out/"reference-projection.json",result)

def derived(mode,out):
    out=Path(out);s.check_derived(out);directory=out/"candidate/methods"
    sys.path.insert(0,str(directory))
    name,entry={"planes":("width_planes","native"),"recover":("width_source_pins","recover")}[mode]
    spec=importlib.util.spec_from_file_location(name,directory/(name+".py"))
    module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)
    module.ROOT=s.ROOT;module.OUT=out/"candidate"
    getattr(module,entry)()
    s.check_derived(out)

def main():
    p=argparse.ArgumentParser();p.add_argument("mode",choices=("reference","planes","recover"));args=p.parse_args()
    s.authorize()
    if args.mode=="reference":project_reference(s.OUT)
    else:derived(args.mode,s.OUT)

if __name__=="__main__":main()
