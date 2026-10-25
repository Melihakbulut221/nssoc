#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0
"""Observe exact saved sidecar differences without accepting any replacement."""
import ast,collections,copy,hashlib,json
from pathlib import Path
import materialize_cdr_v59_static_annotations as frozen
ROOT=Path(__file__).resolve().parents[1]
FROZEN='scripts/materialize_cdr_v59_static_annotations.py'
FROZEN_SHA='fb51f63f3e934747ba1fbc6af8a06a176b7d6e47e52794abaaa5108d2989d217'
SIDECAR_SHA='3a9b62c8597335b253671bb135dfcacf2778a71e5a1d62eb59c0ab72345c354f'
def digest(text):return hashlib.sha256(text.encode()).hexdigest()
def encoded(value):return json.dumps(value,sort_keys=True,separators=(',',':'),allow_nan=False)
def difference(left,right):
    a,b=collections.Counter(map(encoded,left)),collections.Counter(map(encoded,right))
    return dict(left_only=[dict(value=json.loads(k),count=n)for k,n in sorted((a-b).items())],
      right_only=[dict(value=json.loads(k),count=n)for k,n in sorted((b-a).items())],
      equal=a==b,left_count=len(left),right_count=len(right))
def shape_records(layout,cell):
    rows=[]
    for i in layout.layer_indexes():
        info=layout.get_info(i)
        for s in cell.each_shape(i):
            kind=('box'if s.is_box()else'simple_polygon'if s.is_simple_polygon()else
              'polygon'if s.is_polygon()else'path'if s.is_path()else'text'if s.is_text()else'other')
            # Property values supplement raw Shape.to_s; they never replace it.
            if s.prop_id==0:properties=[];method='no_properties_id'
            else:
                if hasattr(s,'properties'):v=s.properties();method='Shape.properties'
                else:v=layout.properties(s.prop_id);method='Layout.properties_legacy'
                items=v.items()if isinstance(v,dict)else v
                properties=sorted([dict(key_type=type(k).__name__,key_repr=repr(k),
                  value_type=type(value).__name__,value_repr=repr(value))for k,value in items],key=encoded)
            row=dict(layer=info.layer,datatype=info.datatype,layer_description=info.to_s(),
              kind=kind,raw=s.to_s(),property_id=s.prop_id,properties=properties,property_api=method)
            if s.is_box():row['box']=frozen.witness.box_values(s.box)
            if s.is_text():row['text']=str(s.text)
            rows.append(row)
    return sorted(rows,key=encoded)
def pair(pya,al,ac,bl,bc):
    assert al.dbu==bl.dbu==.001 and not list(ac.each_inst())and not list(bc.each_inst())
    a,b=frozen.all_regions(pya,al,ac),frozen.all_regions(pya,bl,bc);layers=[]
    for key in sorted(set(a)|set(b)):
        left=a.get(key,pya.Region());right=b.get(key,pya.Region())
        x=(left^right).flatten().merged();polys=sorted(p.to_s()for p in x.each())
        assert x.is_empty()==(not polys)
        layers.append(dict(layer=key[0],datatype=key[1],native_area_dbu2=left.area(),
          serialized_area_dbu2=right.area(),xor_empty=x.is_empty(),xor_area_dbu2=x.area(),
          xor_polygon_strings=polys))
    nr,sr=shape_records(al,ac),shape_records(bl,bc)
    raw_native=[list(v)for v in frozen.raw_shapes(al,ac)]
    raw_saved=[list(v)for v in frozen.raw_shapes(bl,bc)]
    assert sorted([r['layer'],r['datatype'],r['raw']]for r in nr)==raw_native
    assert sorted([r['layer'],r['datatype'],r['raw']]for r in sr)==raw_saved
    nt,st=frozen.labels(al,ac),frozen.labels(bl,bc)
    np,sp=frozen.witness.pin_shapes(al,ac),frozen.witness.pin_shapes(bl,bc)
    return dict(native_cell=ac.name,serialized_cell=bc.name,dbu_um=.001,
      native_shape_count=len(nr),serialized_shape_count=len(sr),native_records=nr,serialized_records=sr,
      native_raw_shapes=raw_native,serialized_raw_shapes=raw_saved,raw_difference=difference(raw_native,raw_saved),
      native_text=nt,serialized_text=st,text_difference=difference(nt,st),
      native_pin_shapes=np,serialized_pin_shapes=sp,pin_difference=difference(np,sp),
      all_layers=layers,all_layer_sets_equal=set(a)==set(b),all_layer_material_equal=all(v['xor_empty']for v in layers),
      annotation_binding_accepted=False)
def validate_pair(p):
    assert p['dbu_um']==.001 and p['annotation_binding_accepted']is False
    for prefix in('native','serialized'):
        rows=p[prefix+'_records'];assert len(rows)==p[prefix+'_shape_count']
        raw=sorted([r['layer'],r['datatype'],r['raw']]for r in rows)
        assert raw==p[prefix+'_raw_shapes']
    for key,a,b in(('raw','native_raw_shapes','serialized_raw_shapes'),
      ('text','native_text','serialized_text'),('pin','native_pin_shapes','serialized_pin_shapes')):
        assert p[key+'_difference']==difference(p[a],p[b])
    layers=p['all_layers'];assert len({(v['layer'],v['datatype'])for v in layers})==len(layers)
    assert all(v['xor_empty']==(not v['xor_polygon_strings'])for v in layers)
    assert p['all_layer_material_equal']==all(v['xor_empty']for v in layers)
    return True
def capture(pya,N,O,F,R,cells,path):
    rows=[pair(pya,N,native,R,cells[name])for name,native in zip(frozen.NAMES,(O,F))]
    for r in rows:validate_pair(r)
    report=dict(status='CAPTURED_ACTUAL_NATIVE_AND_EXACT_SAVED_SHAPES_BEFORE_ORIGINAL_ASSERTION',
      frozen_helper_sha256=FROZEN_SHA,saved_sidecar_sha256=SIDECAR_SHA,cells=rows,
      complete_raw_text_pin_multisets_retained=True,interpretation='Observed differences only; no representation equivalence assumed.',
      annotation_binding_accepted=False,strict_wires_executed=False,qualified_pex=False,electrical_accepted=False)
    frozen.witness.write(path,report)
def derive(original):
    assert digest(original)==FROZEN_SHA
    edits=[
      ("for n in('capsule','pdk','out'):","for n in('capsule','pdk','out','saved-sidecar'):"),
      ("S.write(str(sidecar))","assert a.saved_sidecar.resolve()!=sidecar and a.saved_sidecar.stat().st_size==2910\n        assert sha(a.saved_sidecar)=='"+SIDECAR_SHA+"'\n        sidecar.write_bytes(a.saved_sidecar.read_bytes());assert sha(sidecar)=='"+SIDECAR_SHA+"'"),
      ("        serialized=[dict(cell=name,**exact_static(pya,N,native,R,cells[name]))\n          for name,native in zip(NAMES,(O,F))]",
       "        from cdr_v59_serialized_shape_diagnostic import capture\n        capture(pya,N,O,F,R,cells,out/'serialized-comparison.json')\n        try:\n            serialized=[dict(cell=name,**exact_static(pya,N,native,R,cells[name]))\n              for name,native in zip(NAMES,(O,F))]\n        except AssertionError as error:\n            tb=error.__traceback__\n            while tb.tb_next is not None:tb=tb.tb_next\n            assert error.args==('Changed complete raw native shapes',)\n            assert tb.tb_frame.f_code is exact_static.__code__ and tb.tb_lineno==40\n            f=tb.tb_frame.f_locals\n            assert f['native_layout']is N and f['native']is O\n            assert f['static_layout']is R and f['static']is cells[NAMES[0]]\n            result['raw_failure_identity']=dict(function='exact_static',line=40,\n              executing_helper_sha256=sha(Path(__file__)),native_cell=O.name,serialized_cell=NAMES[0],\n              first_native_and_saved_cell_objects_bound=True)\n            save()\n            raise"),
      ("        assert sidecar.stat().st_size>66","        raise AssertionError('Expected saved raw-shape rejection did not recur; no binding permitted')\n        assert sidecar.stat().st_size>66")]
    generated=original
    for before,after in edits:
        assert generated.count(before)==1,(before,generated.count(before));generated=generated.replace(before,after)
    reversed_source=generated
    for before,after in reversed(edits):
        assert reversed_source.count(after)==1;reversed_source=reversed_source.replace(after,before)
    assert reversed_source==original
    old={v.name:ast.dump(v,include_attributes=False)for v in ast.parse(original).body if isinstance(v,ast.FunctionDef)}
    new={v.name:ast.dump(v,include_attributes=False)for v in ast.parse(generated).body if isinstance(v,ast.FunctionDef)}
    assert set(old)==set(new)and all(new[n]==v for n,v in old.items()if n!='main')
    assert generated.splitlines()[39]==original.splitlines()[39]
    return generated,dict(original_sha256=FROZEN_SHA,generated_sha256=digest(generated),
      reversible_edits=[dict(before=a,after=b,count=1)for a,b in edits],
      unchanged_functions=[n for n in old if n!='main'],original_raw_assertion_line=40,
      binding_blocked_after_original_serialized_checks=True,original_layout_write_removed=True)
def controls():
    source=(ROOT/FROZEN).read_text();generated,proof=derive(source);rejected=[]
    try:derive(source+'\n')
    except AssertionError:rejected.append('changed_frozen_source')
    else:raise AssertionError('Changed frozen source accepted')
    r=dict(native_cell='native',serialized_cell='saved',dbu_um=.001,
      native_shape_count=2,serialized_shape_count=2,
      native_records=[dict(layer=8,datatype=2,raw='A'),dict(layer=8,datatype=2,raw='A')],
      serialized_records=[dict(layer=8,datatype=2,raw='A'),dict(layer=8,datatype=2,raw='B')],
      native_raw_shapes=[[8,2,'A'],[8,2,'A']],serialized_raw_shapes=[[8,2,'A'],[8,2,'B']],
      native_text=[],serialized_text=[],native_pin_shapes=[dict(box=[0,0,1,1])],serialized_pin_shapes=[dict(box=[1,0,2,1])],
      all_layers=[dict(layer=8,datatype=2,xor_empty=False,xor_polygon_strings=['native_fault'])],
      all_layer_material_equal=False,annotation_binding_accepted=False)
    for k,a,b in(('raw','native_raw_shapes','serialized_raw_shapes'),('text','native_text','serialized_text'),('pin','native_pin_shapes','serialized_pin_shapes')):
        r[k+'_difference']=difference(r[a],r[b])
    validate_pair(r)
    assert r['raw_difference']['left_only']==[dict(value=[8,2,'A'],count=1)]
    assert r['raw_difference']['right_only']==[dict(value=[8,2,'B'],count=1)]
    for label,mutate in [
      ('omitted_native_record',lambda p:p['native_records'].pop()),
      ('changed_raw_record',lambda p:p['serialized_records'][0].__setitem__('raw','WRONG')),
      ('hidden_duplicate_multiplicity',lambda p:p['raw_difference']['left_only'][0].__setitem__('count',2)),
      ('invented_text_equality',lambda p:p['text_difference'].__setitem__('equal',False)),
      ('invented_pin_equality',lambda p:p['pin_difference'].__setitem__('equal',True)),
      ('invented_material_equality',lambda p:p.__setitem__('all_layer_material_equal',True)),
      ('invented_annotation_acceptance',lambda p:p.__setitem__('annotation_binding_accepted',True)),
      ('duplicate_layer_report',lambda p:p['all_layers'].append(copy.deepcopy(p['all_layers'][0])))]:
        q=copy.deepcopy(r);mutate(q)
        try:validate_pair(q)
        except AssertionError:rejected.append(label)
        else:raise AssertionError('Accepted '+label)
    assert len(rejected)==9
    return dict(status='PASS9_DERIVATION_AND_LOSSLESS_DIFFERENCE_CONTROLS',rejected=rejected,
      derivation=proof,native_executed=False)
