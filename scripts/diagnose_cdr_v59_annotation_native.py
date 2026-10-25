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
def gds_record_inventory(raw):
    rows=[];offset=0
    while offset<len(raw):
        assert len(raw)-offset>=4,'Truncated GDS record header'
        size=int.from_bytes(raw[offset:offset+2],'big')
        assert size>=4 and size%2==0 and offset+size<=len(raw),'Invalid GDS record extent'
        data=raw[offset:offset+size]
        rows.append(dict(offset=offset,bytes=size,record_type=data[2],data_type=data[3],
          exact_record_hex=data.hex(),sha256=digest(data)))
        offset+=size
    assert offset==len(raw)
    return rows
def complete_census(layout,rows):
    expected={c.cell_index():c.name for c in layout.each_cell()}
    assert len(rows)==len(expected)
    assert {r['cell_index']:r['cell']for r in rows}==expected
    assert len({r['cell_index']for r in rows})==len(rows)
def all_cell_census(pya,layout,target_layout,target,signature):
    rows=[]
    for cell in layout.each_cell():
        row=inspect_cell(pya,layout,cell,signature,full=True)
        children=[dict(cell=i.cell.name,cell_index=i.cell.cell_index(),transform=str(i.cplx_trans),
          na=i.na,nb=i.nb,a=str(i.a),b=str(i.b))for i in cell.each_inst()]
        pins=[]
        for metal in METALS:
            indexes=[i for i in layout.layer_indexes()if
              (layout.get_info(i).layer,layout.get_info(i).datatype)==(metal,2)]
            assert len(indexes)<=1
            if indexes:
                pins.extend([metal,box_values(s.box)]for s in cell.each_shape(indexes[0])if s.is_box())
        row.update(cell_index=cell.cell_index(),direct_instances=children,original_box_pins=sorted(pins),
          original_name_filter_passed=row['kind']in MODELS,original_leaf_filter_passed=not children,
          original_pin_filter_passed=bool(pins),
          comparison_with_actual_missing_target=compare_material(pya,target_layout,target,layout,cell))
        rows.append(row)
    complete_census(layout,rows)
    return rows
def saved_native_source_census(pya,capsule,target_layout,target,signature):
    path=capsule/'parent/inputs/sampler_cd/layout/native-rppd-v59-cd_shunt.gds'
    raw=path.read_bytes()
    assert len(raw)==66 and digest(raw)=='d0463267c8b53af161a7f47384eb6a83578f7d588bf03453729a0d077c66dd18'
    layout=pya.Layout();layout.read(str(path));assert layout.dbu==.001
    rows=all_cell_census(pya,layout,target_layout,target,signature)
    return dict(source=str(path.relative_to(capsule)),bytes=len(raw),sha256=digest(raw),
      exact_file_hex=raw.hex(),record_inventory=gds_record_inventory(raw),dbu_um=layout.dbu,
      cell_count=len(rows),top_cells=[dict(cell=c.name,cell_index=c.cell_index())for c in layout.top_cells()],
      cells=rows,all_cells_included_without_model_or_leaf_or_pin_filter=True,
      interpretation='Actual serialized cell census and comparison only; no source role or annotation binding accepted.',
      annotation_binding_accepted=False,target_geometry_edited=False)
def census_controls(pya):
    L=pya.Layout();L.dbu=.001
    target=L.create_cell('target')
    target.shapes(L.layer(8,0)).insert(pya.Box(0,0,20,40))
    # A deliberately unrecognized name and a non-leaf wrapper must both be
    # reported, never admitted as an rppd or silently removed by the old filter.
    source=L.create_cell('unrecognized_native_name')
    source.shapes(L.layer(8,0)).insert(pya.Box(0,0,20,40))
    source.shapes(L.layer(8,2)).insert(pya.Box(0,0,10,10))
    wrapper=L.create_cell('rppd$wrapper')
    wrapper.insert(pya.CellInstArray(source.cell_index(),pya.Trans()))
    def signature(layout,cell):
        drawing=[]
        for i in layout.layer_indexes():
            info=layout.get_info(i)
            if annotation(info.layer,info.datatype):continue
            reg=pya.Region(cell.begin_shapes_rec(i)).merged()
            if not reg.is_empty():drawing.append((info.layer,info.datatype,sorted(p.to_s()for p in reg.each())))
        assert drawing
        return digest(json.dumps(sorted(drawing),separators=(',',':')))
    rows=all_cell_census(pya,L,L,target,signature)
    by={r['cell']:r for r in rows}
    assert not by[source.name]['original_name_filter_passed']
    assert by[source.name]['original_pin_filter_passed']
    assert by[source.name]['comparison_with_actual_missing_target']['all_nonannotation_layers_material_equal']
    assert not by[wrapper.name]['original_leaf_filter_passed']
    assert by[wrapper.name]['comparison_with_actual_missing_target']['all_nonannotation_layers_material_equal']
    E=pya.Layout();E.dbu=.001
    assert all_cell_census(pya,E,L,target,signature)==[]
    positives=['unrecognized_annotated_leaf_reported','nonleaf_wrapper_reported','empty_layout_reported']
    rejected=[]
    def reject(label,fn):
        try:fn()
        except AssertionError:rejected.append(label)
        else:raise AssertionError('Accepted census fault '+label)
    reject('omitted_unrecognized_cell',lambda:complete_census(L,[r for r in rows if r['cell']!=source.name]))
    reject('duplicate_cell_census',lambda:complete_census(L,rows+[rows[0]]))
    raw=bytes.fromhex('00060002025800040400')
    assert b''.join(bytes.fromhex(r['exact_record_hex'])for r in gds_record_inventory(raw))==raw
    reject('truncated_record',lambda:gds_record_inventory(raw[:-1]))
    reject('zero_record_length',lambda:gds_record_inventory(bytes(4)))
    reject('odd_record_length',lambda:gds_record_inventory(bytes.fromhex('0005000200')))
    assert len(positives)==3 and len(rejected)==5
    return dict(positive_cases=positives,rejected=rejected,record_bytes_preserved=True)
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
        module=importlib.util.module_from_spec(spec)
        # Execute exact authenticated source bytes, never a saved bytecode cache.
        exec(compile(frozen.read_bytes(),str(frozen),'exec'),module.__dict__);module.OUT=capsule
        assert module.TOP==TOP and module.METALS==METALS and module.MODELS==MODELS
        proof,frame=original_failure(module);result['original_failure']=proof;save()
        signature=frame['signature'];target_layout=frame['L'];target=frame['c']
        assert target_layout.cell(TOP)is not None and target_layout.dbu==.001
        result['target_dbu_um']=target_layout.dbu
        assert set(frame['inputs'])=={str(f)for f in(capsule/'parent/inputs').rglob('*.gds')}
        result['native_controls']=native_controls(pya)
        result['source_census_controls']=census_controls(pya)
        result['saved_new_source_census']=saved_native_source_census(pya,capsule,target_layout,target,signature);save()
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
