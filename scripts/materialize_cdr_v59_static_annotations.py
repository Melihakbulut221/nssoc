#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0
"""Materialize missing native annotation sidecars; never edit the saved candidate."""
import argparse,hashlib,importlib.util,json,os,sys,traceback
from pathlib import Path
sys.dont_write_bytecode=True
import diagnose_cdr_v59_annotation_native as witness
ROOT=Path(__file__).resolve().parents[1]
SUMMARY_SHA='c07cfcd6f1172d54dd1fdda3cf5d8c69e0522121fcc245a0b85d58ac5fa9258f'
RPPD_SHA='58d53384ef0bb92a4fa413d3c92e8dcbcb8f422c5205da9260129049f07f1d6b'
GEOMETRY_SHA='479a648a1d25678af42ebe495ae6cd855e8441fb071f49817972529eee5713e2'
SIDECAR='parent/inputs/sampler_cd/layout/native-rppd-v59-static-cd_shunt.gds'
NAMES=('rppd$v59_static_old','rppd$v59_static_new')
def sha(path):return witness.file_sha(Path(path))
def labels(layout,cell):
    return sorted((layout.get_info(i).layer,layout.get_info(i).datatype,str(s.text))
      for i in layout.layer_indexes()for s in cell.each_shape(i)if s.is_text())
def raw_shapes(layout,cell):
    return sorted((layout.get_info(i).layer,layout.get_info(i).datatype,s.to_s())
      for i in layout.layer_indexes()for s in cell.each_shape(i))
def all_regions(pya,layout,cell):
    result={}
    for i in layout.layer_indexes():
        info=layout.get_info(i);key=(info.layer,info.datatype)
        assert key not in result
        r=pya.Region(cell.begin_shapes_rec(i)).flatten().merged()
        if not r.is_empty():result[key]=r
    return result
def exact_static(pya,native_layout,native,static_layout,static):
    assert native_layout.dbu==static_layout.dbu==.001
    assert not list(native.each_inst())and not list(static.each_inst())
    a,b=all_regions(pya,native_layout,native),all_regions(pya,static_layout,static)
    assert set(a)==set(b),'Changed complete native material/annotation layer set'
    rows=[]
    for key in sorted(a):
        x=(a[key]^b[key]).flatten().merged()
        assert x.is_empty()and not list(x.each()),('Changed actual layer',key)
        rows.append(dict(layer=key[0],datatype=key[1],native_area_dbu2=a[key].area(),
          serialized_area_dbu2=b[key].area(),xor_empty=True))
    assert raw_shapes(native_layout,native)==raw_shapes(static_layout,static),'Changed complete raw native shapes'
    assert labels(native_layout,native)==labels(static_layout,static),'Changed native text'
    assert witness.pin_shapes(native_layout,native)==witness.pin_shapes(static_layout,static),'Changed exact annotation shape'
    pins=[witness.box_values(s.box)for s in static.each_shape(static_layout.layer(8,2))if s.is_box()]
    assert len(pins)==2 and len({tuple(p)for p in pins})==2
    return dict(all_layers=rows,all_raw_shapes=raw_shapes(static_layout,static),all_text=labels(static_layout,static),
      exact_annotations=witness.pin_shapes(static_layout,static),metal1_pin_boxes=sorted(pins))
def exact_cell_inventory(layout):
    cells=list(layout.each_cell())
    assert sorted(c.name for c in cells)==sorted(NAMES)and len(cells)==2
    assert all(not list(c.each_inst())and not c.is_proxy()for c in cells)
    return {c.name:c for c in cells}
def native_controls(pya,native_layout,old,new):
    rejected=[]
    def reject(label,mutate,reference=new):
        C=pya.Layout();C.dbu=.001;c=C.create_cell('rppd$control');c.copy_tree(new)
        mutate(C,c)
        try:exact_static(pya,native_layout,reference,C,c)
        except AssertionError:rejected.append(label)
        else:raise AssertionError('Accepted annotation sidecar fault '+label)
    reject('added_native_metal',lambda L,c:c.shapes(L.layer(8,0)).insert(pya.Box(100000,100000,100010,100010)))
    reject('removed_native_metal',lambda L,c:c.shapes(L.layer(8,0)).clear())
    reject('old_length_substituted_for_new',lambda L,c:None,reference=old)
    reject('missing_actual_pin',lambda L,c:c.shapes(L.layer(8,2)).clear())
    def moved(L,c):
        pins=[s.box for s in c.each_shape(L.layer(8,2))if s.is_box()]
        assert len(pins)==2
        c.shapes(L.layer(8,2)).clear()
        c.shapes(L.layer(8,2)).insert(pins[0].transformed(pya.Trans(1,0)))
        c.shapes(L.layer(8,2)).insert(pins[1])
    reject('moved_actual_pin',moved)
    def duplicate(L,c):
        pins=[s.box for s in c.each_shape(L.layer(8,2))if s.is_box()]
        assert len(pins)==2;c.shapes(L.layer(8,2)).insert(pins[0])
    reject('duplicated_actual_pin',duplicate)
    reject('added_annotation_text',lambda L,c:c.shapes(L.layer(8,25)).insert(pya.Text('WRONG',pya.Trans())))
    reject('extra_material_layer',lambda L,c:c.shapes(L.layer(999,0)).insert(pya.Box(0,0,5,5)))
    for name,names in [('missing_serialized_cell',NAMES[:1]),('extra_serialized_cell',NAMES+('extra',))]:
        L=pya.Layout()
        for n in names:L.create_cell(n)
        try:exact_cell_inventory(L)
        except AssertionError:rejected.append(name)
        else:raise AssertionError('Accepted '+name)
    assert len(rejected)==10
    return dict(rejected=rejected,actual_native_drawings_used=True,no_candidate_geometry_mutated=True)
def main():
    import pya
    parser=argparse.ArgumentParser()
    for n in('capsule','pdk','out'):parser.add_argument('--'+n,type=Path,required=True)
    a=parser.parse_args();capsule=a.capsule.resolve();pdk=a.pdk.resolve();out=a.out.resolve()
    assert os.environ.get('GITHUB_ACTIONS')=='true'
    out.mkdir(exist_ok=False)
    report=json.loads((capsule/'result.json').read_text());assert sha(capsule/'result.json')==SUMMARY_SHA
    before={n:sha(capsule/n)for n in report['outputs']};assert before==report['outputs']and len(before)==339
    result=dict(status='RUNNING',candidate_geometry_edited=False,candidate_reference_edited=False,
      physical_checks_rerun=False,qualified_pex=False,electrical_accepted=False,full_phy_accepted=False)
    def save():witness.write(out/'materialization.json',result)
    save()
    try:
        frozen=capsule/'methods/cdr_v59_recover.py';assert sha(frozen)==witness.RECOVER_SHA
        spec=importlib.util.spec_from_file_location('frozen_v59_annotation_recovery',frozen)
        module=importlib.util.module_from_spec(spec)
        exec(compile(frozen.read_bytes(),str(frozen),'exec'),module.__dict__);module.OUT=capsule
        failure,frame=witness.original_failure(module);result['original_failure']=failure;save()
        target_layout=frame['L'];target=frame['c'];signature=frame['signature']
        census=witness.saved_native_source_census(pya,capsule,target_layout,target,signature)
        assert census['cell_count']==0 and census['cells']==census['top_cells']==[]
        result['original_empty_source_census']=census;save()
        assert not(capsule/'wire/source-pins.json').exists()and not(capsule/SIDECAR).exists()
        delta=report['candidate_delta']
        assert delta['arm']=='cd_shunt'and delta['replacement_native_devices']==4
        assert delta['specification']==dict(kind='sampler_cd',tags=['sc','sd'],names=['DN','DP'],
          ids=[184,185,222,223],width=4.,old_length=7.4,new_length=5.)
        src=pdk/'libs.tech/klayout/python'
        assert sha(src/'sg13g2_pycell_lib/ihp/rppd_code.py')==RPPD_SHA
        assert sha(src/'sg13g2_pycell_lib/ihp/geometry.py')==GEOMETRY_SHA
        # Expected runtime files are from the authenticated actual failed physical
        # report, not inferred by hashing the freshly restored files.
        prefix='/home/runner/work/nssoc/nssoc/pdk/'
        runtime_pins={}
        for n,h in delta['source_inputs'].items():
            if not n.startswith(prefix):continue
            relative=Path(n[len(prefix):])
            assert not relative.is_absolute()and '..'not in relative.parts
            path=pdk/relative;assert sha(path)==h,n;runtime_pins[str(relative)]=h
        assert len(runtime_pins)==88 and 'libs.tech/klayout/python/sg13g2_pycell_lib/ihp/rppd_code.py'in runtime_pins
        sys.path[:0]=[str(src),str(src/'pycell4klayout-api/source/python')]
        import sg13g2_pycell_lib
        N=pya.Layout();N.dbu=.001
        # These are the exact native calls of the passed geometry stage.
        O=N.create_cell('rppd','SG13_dev',dict(w='4u',l='7.4u',b=0,m='1'))
        F=N.create_cell('rppd','SG13_dev',dict(w='4u',l='5u',b=0,m='1'))
        assert O is not None and F is not None and not O.is_empty()and not F.is_empty()
        assert not list(O.each_inst())and not list(F.each_inst())and N.dbu==.001
        assert O.pcell_parameters_by_name()==delta['native_pcell_parameters_before']
        assert F.pcell_parameters_by_name()==delta['native_pcell_parameters_after']
        old_path=capsule/'source/parent/layout/nssoc_cdr_pd500_input_access_v58.gds'
        assert sha(old_path)==report['outputs'][str(old_path.relative_to(capsule))]
        B=pya.Layout();B.read(str(old_path));assert B.dbu==.001
        old_names={r['old_cell']for r in delta['bridges']}
        assert old_names=={'rppd$1$15'}
        old_proofs=[]
        for name in sorted(old_names):
            old=B.cell(name);assert old is not None
            proof=witness.compare_material(pya,N,O,B,old)
            assert proof['all_nonannotation_layers_material_equal']
            old_proofs.append(dict(cell=name,**proof))
        new_proof=witness.compare_material(pya,N,F,target_layout,target)
        assert new_proof['all_nonannotation_layers_material_equal']
        assert target.name==witness.EXPECTED_CELL and signature(target_layout,target)==witness.EXPECTED_KEY[1]
        S=pya.Layout();S.dbu=.001
        old_static=S.create_cell(NAMES[0]);old_static.copy_tree(O)
        new_static=S.create_cell(NAMES[1]);new_static.copy_tree(F)
        exact_cell_inventory(S)
        exact_static(pya,N,O,S,old_static);exact_static(pya,N,F,S,new_static)
        sidecar=capsule/SIDECAR;assert not sidecar.exists();S.write(str(sidecar))
        R=pya.Layout();R.read(str(sidecar));assert R.dbu==.001
        cells=exact_cell_inventory(R)
        serialized=[dict(cell=name,**exact_static(pya,N,native,R,cells[name]))
          for name,native in zip(NAMES,(O,F))]
        assert sidecar.stat().st_size>66
        # Keep the original exact signature admission, with no geometric fallback.
        new_key=signature(R,cells[NAMES[1]])
        assert new_key==witness.EXPECTED_KEY[1]
        old_key=signature(R,cells[NAMES[0]])
        assert ('rppd',old_key)in frame['sources']
        assert [[8,b]for b in serialized[0]['metal1_pin_boxes']]==frame['sources'][('rppd',old_key)]['pins']
        result.update(native_parameters_before=O.pcell_parameters_by_name(),
          native_parameters_after=F.pcell_parameters_by_name(),old_saved_material=old_proofs,
          new_candidate_material=new_proof,serialized_native_identity=serialized,
          sidecar=dict(path=SIDECAR,bytes=sidecar.stat().st_size,sha256=sha(sidecar),
            old_signature=old_key,new_signature=new_key,plain_static_cells=list(NAMES)),
          native_controls=native_controls(pya,N,O,F),
          runtime_source_pins=runtime_pins);save()
        module.recover() # Byte-exact original code, now seeing the additional proven source.
        recovered=json.loads((capsule/'wire/source-pins.json').read_text())
        assert recovered['status']=='PASS_RECOVERED_SOURCE_PIN_BOXES_ON_IDENTICAL_PRIMITIVE_DRAWING'
        assert recovered['target_geometry_edited']is False and recovered['missing_referenced_primitive_rejected']
        bound=recovered['cells'][witness.EXPECTED_CELL]
        assert bound['drawing_sha256']==new_key and bound['source']==str(sidecar)
        assert bound['cell']==NAMES[1]and bound['pins']==[[8,b]for b in serialized[1]['metal1_pin_boxes']]
        for name,row in recovered['cells'].items():
            key=(name.split('$')[0],row['drawing_sha256'])
            if name==witness.EXPECTED_CELL:continue
            assert key in frame['sources']and row['pins']==frame['sources'][key]['pins']
        assert recovered['inputs']=={**frame['inputs'],str(sidecar):sha(sidecar)}
        for n,h in runtime_pins.items():assert sha(pdk/n)==h
        result.update(status='PASS_STATIC_NATIVE_SIDECAR_AND_UNCHANGED_EXACT_ANNOTATION_RECOVERY_REQUIRES_STRICT_WIRES',
          recovered_annotation_sha256=sha(capsule/'wire/source-pins.json'),
          original_recovery_source_unchanged=sha(frozen)==witness.RECOVER_SHA,
          all_original_source_pin_sets_preserved=True,signature_fallback_used=False)
    except BaseException as error:
        result.update(status='FAIL_STATIC_NATIVE_ANNOTATION_RECOVERY',error=repr(error),traceback=traceback.format_exc());raise
    finally:
        try:
            result['all339_original_files_unchanged']=all(sha(capsule/n)==h for n,h in before.items())
            result['original_report_unchanged']=sha(capsule/'result.json')==SUMMARY_SHA
            assert result['all339_original_files_unchanged']and result['original_report_unchanged']
        except BaseException as error:
            result.update(status='FAIL_STATIC_NATIVE_ANNOTATION_RECOVERY_INTEGRITY',integrity_error=repr(error));raise
        finally:save()
if __name__=='__main__':main()
