#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0
"""Read-only native witness for one exact saved annotation rejection; no qualification."""
import argparse,hashlib,importlib.util,json,sys,traceback
from pathlib import Path
sys.dont_write_bytecode=True
TOP='nssoc_cdr_pd500_resistor_v59'
METALS=(8,10,30,50,67,126,134)
MODELS={'npn13G2','rppd','ptap1','cmim','nmos'}
EXPECTED_CELL='rppd$v59_cd_shunt'
EXPECTED_KEY=('rppd','26cb371619de68fbd6248f25a98a6b1c2ef649e3e75d56b082c7eafb9d35ec91')
RECOVER_SHA='29b92f3ae273b3f5bf6f0f9ae4b144c3257b73bf38307500c27f8853d00d90ea'
def digest(value):return hashlib.sha256(value.encode()if isinstance(value,str)else value).hexdigest()
def file_sha(path):
    with path.open('rb')as stream:return hashlib.file_digest(stream,'sha256').hexdigest()
def encoded(value):return json.dumps(value,sort_keys=True,separators=(',',':'),allow_nan=False)
def write(path,value):
    temporary=path.with_suffix(path.suffix+'.tmp');temporary.write_text(json.dumps(value,indent=2,allow_nan=False)+'\n');temporary.replace(path)
def original_failure(module):
    try:module.recover()
    except AssertionError as error:
        tb=error.__traceback__
        while tb.tb_next is not None:tb=tb.tb_next
        assert tb.tb_frame.f_code is module.recover.__code__ and tb.tb_lineno==62
        frame=tb.tb_frame.f_locals
        assert error.args==((EXPECTED_CELL,EXPECTED_KEY),)
        assert frame['c'].name==EXPECTED_CELL and frame['key']==EXPECTED_KEY
        assert EXPECTED_KEY not in frame['sources']
        proof=dict(code_file_sha256=RECOVER_SHA,function='recover',line=62,
          error=repr(error),cell=frame['c'].name,key=list(frame['key']),
          original_traceback=traceback.format_exc(),source_key_count=len(frame['sources']),
          source_file_count=len(frame['inputs']),original_rejection_retained=True)
        return proof,frame
    raise AssertionError('Original frozen recovery did not reject at the exact saved predicate')
def annotation(layer,datatype):return layer in METALS and datatype in (2,25)
def box_values(box):return [box.left,box.bottom,box.right,box.top]
def pin_shapes(layout,cell):
    result=[]
    for idx in layout.layer_indexes():
        info=layout.get_info(idx)
        if not annotation(info.layer,info.datatype):continue
        for shape in cell.each_shape(idx):
            kind=('box'if shape.is_box()else'simple_polygon'if shape.is_simple_polygon()else
              'polygon'if shape.is_polygon()else'path'if shape.is_path()else
              'text'if shape.is_text()else'other')
            row=dict(layer=info.layer,datatype=info.datatype,type=kind,serialization=shape.to_s())
            if shape.is_box():row['box']=box_values(shape.box)
            result.append(row)
    return sorted(result,key=encoded)
def material_region(pya,layout,cell,key):
    indexes=[idx for idx in layout.layer_indexes()if(layout.get_info(idx).layer,layout.get_info(idx).datatype)==key]
    assert len(indexes)<=1
    return pya.Region(cell.begin_shapes_rec(indexes[0])).flatten().merged()if indexes else pya.Region()
def inspect_cell(pya,layout,cell,signature,full=False):
    old_drawing=[];material_drawing=[];layers=[]
    for idx in layout.layer_indexes():
        info=layout.get_info(idx);key=(info.layer,info.datatype)
        raw=pya.Region(cell.begin_shapes_rec(idx)).merged()
        raw_empty=raw.is_empty();raw_polygons=sorted(p.to_s()for p in raw.each())
        flat=material_region(pya,layout,cell,key);flat_polygons=sorted(p.to_s()for p in flat.each())
        included=not annotation(*key)
        if included and not raw_empty:old_drawing.append((key[0],key[1],raw_polygons))
        if included and not flat.is_empty():material_drawing.append((key[0],key[1],flat_polygons))
        row=dict(layer=key[0],datatype=key[1],included_in_original_signature=included,
          original_region_is_empty=raw_empty,original_polygon_count=len(raw_polygons),
          original_polygon_strings_sha256=digest(encoded(raw_polygons)),
          material_region_is_empty=flat.is_empty(),material_polygon_count=len(flat_polygons),
          material_area_dbu2=flat.area(),material_polygon_strings_sha256=digest(encoded(flat_polygons)))
        if full:row.update(original_polygon_strings=raw_polygons,material_polygon_strings=flat_polygons)
        layers.append(row)
    original_hash=digest(json.dumps(sorted(old_drawing),separators=(',',':')))if old_drawing else None
    if old_drawing:assert original_hash==signature(layout,cell)
    return dict(cell=cell.name,kind=cell.name.split('$')[0],original_signature=original_hash,
      material_representation_sha256=digest(encoded(sorted(material_drawing))),
      layer_witnesses=layers,pin_shapes=pin_shapes(layout,cell),
      original_empty_polygon_entries=[r for r in layers if r['included_in_original_signature']and
        not r['original_region_is_empty']and r['original_polygon_count']==0])
def compare_material(pya,a,ac,b,bc):
    keys={(L.get_info(i).layer,L.get_info(i).datatype)for L in(a,b)for i in L.layer_indexes()}
    result=[]
    for key in sorted(keys):
        if annotation(*key):continue
        left=material_region(pya,a,ac,key);right=material_region(pya,b,bc,key)
        xor=(left^right).flatten().merged();polygons=sorted(p.to_s()for p in xor.each())
        assert xor.is_empty()==(not polygons)
        result.append(dict(layer=key[0],datatype=key[1],left_area_dbu2=left.area(),right_area_dbu2=right.area(),
          xor_is_empty=xor.is_empty(),xor_area_dbu2=xor.area(),xor_polygon_count=len(polygons),
          xor_polygon_strings=polygons))
    return dict(all_nonannotation_layers_material_equal=all(r['xor_is_empty']for r in result),layers=result)
def native_controls(pya):
    L=pya.Layout();L.dbu=.001;a=L.create_cell('a');b=L.create_cell('b')
    layer=L.layer(8,0);pins=L.layer(8,2)
    a.shapes(layer).insert(pya.Box(0,0,20,40));b.shapes(layer).insert(pya.Box(0,0,20,40))
    assert compare_material(pya,L,a,L,b)['all_nonannotation_layers_material_equal']
    b.shapes(pins).insert(pya.Box(0,0,10,10))
    assert compare_material(pya,L,a,L,b)['all_nonannotation_layers_material_equal']
    assert pin_shapes(L,b)[0]['box']==[0,0,10,10]and pin_shapes(L,b)[0]['type']=='box'
    controls=[]
    b.shapes(layer).insert(pya.Box(20,0,30,40))
    assert not compare_material(pya,L,a,L,b)['all_nonannotation_layers_material_equal'];controls.append('added_actual_material')
    b.shapes(layer).clear()
    assert not compare_material(pya,L,a,L,b)['all_nonannotation_layers_material_equal'];controls.append('removed_actual_material')
    b.shapes(layer).insert(pya.Box(1,0,21,40))
    assert not compare_material(pya,L,a,L,b)['all_nonannotation_layers_material_equal'];controls.append('translated_actual_material')
    b.shapes(layer).clear();b.shapes(layer).insert(pya.Box(0,0,20,40))
    other=L.layer(10,0);b.shapes(other).insert(pya.Box(0,0,1,1))
    assert not compare_material(pya,L,a,L,b)['all_nonannotation_layers_material_equal'];controls.append('additional_actual_layer')
    return dict(positive_equal_material=True,annotation_exclusion_does_not_hide_pin_witness=True,rejected=controls)
def main():
    import pya
    p=argparse.ArgumentParser();p.add_argument('--capsule',type=Path,required=True);p.add_argument('--out',type=Path,required=True)
    args=p.parse_args();capsule=args.capsule.resolve();out=args.out.resolve();out.mkdir(exist_ok=False)
    frozen=capsule/'methods/cdr_v59_recover.py';assert file_sha(frozen)==RECOVER_SHA
    report=json.loads((capsule/'result.json').read_text())
    before={n:file_sha(capsule/n)for n in report['outputs']};assert before==report['outputs']
    assert not(capsule/'wire/source-pins.json').exists()
    result=dict(status='RUNNING',diagnostic_only=True,annotation_binding_accepted=False,
      target_geometry_edited=False,strict_wire_qualification=False,qualified_pex=False,electrical_accepted=False)
    def save():write(out/'diagnosis.json',result)
    save()
    try:
        spec=importlib.util.spec_from_file_location('exact_failed_v59_annotation',frozen)
        module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module);module.OUT=capsule
        assert module.TOP==TOP and module.METALS==METALS and module.MODELS==MODELS
        proof,frame=original_failure(module);result['original_failure']=proof;save()
        signature=frame['signature'];target_layout=frame['L'];target=frame['c']
        assert target_layout.cell(TOP)is not None
        assert set(frame['inputs'])=={str(f)for f in(capsule/'parent/inputs').rglob('*.gds')}
        result['native_controls']=native_controls(pya)
        source_rows=[];source_objects=[];actual_keys={}
        for path in sorted((capsule/'parent/inputs').rglob('*.gds')):
            L=pya.Layout();L.read(str(path));assert L.dbu==.001
            for cell in L.each_cell():
                kind=cell.name.split('$')[0]
                if kind not in MODELS or list(cell.each_inst()):continue
                # Match the original lookup order, including creation of absent annotation layers.
                pins=[]
                for metal in METALS:
                    pins.extend([metal,box_values(s.box)]for s in cell.each_shape(L.layer(metal,2))if s.is_box())
                row=inspect_cell(pya,L,cell,signature,full=kind=='rppd')
                row.update(source=str(path.relative_to(capsule)),file_sha256=file_sha(path),
                  original_box_pins=sorted(pins),eligible_in_original_source_lookup=bool(pins))
                source_rows.append(row);source_objects.append((L,cell,row))
                if pins:
                    assert row['original_signature']is not None
                    key=(kind,row['original_signature'])
                    actual_keys.setdefault(key,[]).append(row)
        assert set(actual_keys)==set(frame['sources'])
        for key,rows in actual_keys.items():
            assert all(row['original_box_pins']==frame['sources'][key]['pins']for row in rows)
            assert any(str(capsule/row['source'])==frame['sources'][key]['source']and row['cell']==frame['sources'][key]['cell']for row in rows)
        target_rows=[];comparisons=[]
        for cell in target_layout.each_cell():
            kind=cell.name.split('$')[0]
            if kind not in MODELS or list(cell.each_inst()):continue
            row=inspect_cell(pya,target_layout,cell,signature,full=kind=='rppd')
            row.update(reachable_from_original_top=cell.cell_index()in frame['reachable'],
              original_hash_key_found=(kind,row['original_signature'])in actual_keys,
              original_cmim_exemption=kind=='cmim')
            target_rows.append(row)
            if not row['reachable_from_original_top']or kind=='cmim'or row['original_hash_key_found']:continue
            same_kind=[]
            for L,source,source_row in source_objects:
                if source_row['kind']!=kind:continue
                comparison=compare_material(pya,target_layout,cell,L,source)
                same_kind.append(dict(source=source_row['source'],cell=source.name,
                  original_signature=source_row['original_signature'],
                  eligible_in_original_source_lookup=source_row['eligible_in_original_source_lookup'],
                  original_box_pins=source_row['original_box_pins'],**comparison))
            equal=[r for r in same_kind if r['all_nonannotation_layers_material_equal']and r['eligible_in_original_source_lookup']]
            pinsets=sorted({encoded(r['original_box_pins'])for r in equal})
            comparisons.append(dict(target_cell=cell.name,original_signature=row['original_signature'],
              all_same_kind_sources=same_kind,material_equal_annotated_source_count=len(equal),
              distinct_equal_source_pin_sets=[json.loads(v)for v in pinsets],
              unique_pin_set_observed=len(pinsets)==1))
        assert any(r['target_cell']==EXPECTED_CELL and r['original_signature']==EXPECTED_KEY[1]for r in comparisons)
        result.update(source_primitive_inventory=source_rows,target_primitive_inventory=target_rows,
          all_original_hash_missing_primitives=comparisons,
          original_source_input_hashes={str(Path(n).relative_to(capsule)):h for n,h in frame['inputs'].items()},
          old_signature_and_material_xor_are_separate=True,
          status='COMPLETE_READ_ONLY_V59_ANNOTATION_WITNESS_ORIGINAL_REJECTION_RETAINED')
    except BaseException as error:
        result.update(status='FAIL_V59_ANNOTATION_WITNESS',error=repr(error),traceback=traceback.format_exc());raise
    finally:
        try:
            after={n:file_sha(capsule/n)for n in report['outputs']}
            result['restored_capsule_files_unchanged']=after==before
            result['restored_report_unchanged']=file_sha(capsule/'result.json')=='c07cfcd6f1172d54dd1fdda3cf5d8c69e0522121fcc245a0b85d58ac5fa9258f'
            assert result['restored_capsule_files_unchanged']and result['restored_report_unchanged']
            assert not(capsule/'wire/source-pins.json').exists()
        except BaseException as error:
            result.update(status='FAIL_V59_ANNOTATION_WITNESS_INTEGRITY',integrity_error=repr(error));raise
        finally:save()
if __name__=='__main__':main()
