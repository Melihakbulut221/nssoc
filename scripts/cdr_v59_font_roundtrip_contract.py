#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0
"""Admit only the measured font2-to-NoFont GDS transition; no normalization."""
import ast,copy,hashlib,json
from pathlib import Path
import cdr_v59_serialized_shape_diagnostic as observed
import materialize_cdr_v59_static_annotations as frozen
ROOT=Path(__file__).resolve().parents[1]
COMPARISON='docs/evidence/cdr-v59-serialized-shape-diagnostic-comparison-20261025.json'
COMPARISON_SHA='6d3f73f925ab9767c3b161f293ce0c105074ec03e9052f516ab6f1c2553530f4'
AUDIT='docs/evidence/cdr-klayout-gds-font-source-audit-20261025.json'
AUDIT_SHA='0c999207e72f40011329f7382d04e3688064fdc00ef66e4c21d44f5f8ee3ffca'
FIELDS={'layer','datatype','string','transform','x','y','size','font','halign_center','valign_center','property_id','properties'}
LABELS={
 'rppd$v59_static_old':{52:('rppd','r0 2000,3700',2000,3700,1),63:('rppd r=497.780','r90 2000,3700',2000,3700,100)},
 'rppd$v59_static_new':{52:('rppd','r0 2000,2500',2000,2500,1),63:('rppd r=342.013','r90 2000,2500',2000,2500,100)}}
def digest(text):return hashlib.sha256(text.encode()).hexdigest()
def expected():
    raw=(ROOT/COMPARISON).read_bytes();assert hashlib.sha256(raw).hexdigest()==COMPARISON_SHA
    assert hashlib.sha256((ROOT/AUDIT).read_bytes()).hexdigest()==AUDIT_SHA
    d=json.loads(raw)
    assert d['saved_sidecar_sha256']==observed.SIDECAR_SHA and d['frozen_helper_sha256']==observed.FROZEN_SHA
    assert [x['serialized_cell']for x in d['cells']]==list(frozen.NAMES)
    return d['cells']
def validate_fields(name,native,saved):
    assert name in LABELS and len(native)==len(saved)==2
    assert len({(r['layer'],r['datatype'])for r in native})==2
    assert len({(r['layer'],r['datatype'])for r in saved})==2
    a=sorted(native,key=lambda r:(r['layer'],r['datatype']))
    b=sorted(saved,key=lambda r:(r['layer'],r['datatype']))
    for n,s in zip(a,b):
        assert set(n)==set(s)==FIELDS
        assert type(n['font'])is int and type(s['font'])is int and n['font']==2 and s['font']==-1
        assert {k:v for k,v in n.items()if k!='font'}=={k:v for k,v in s.items()if k!='font'}
        assert n['layer']in(52,63)and n['datatype']==0
        assert (n['string'],n['transform'],n['x'],n['y'],n['size'])==LABELS[name][n['layer']]
        assert n['halign_center']is True and n['valign_center']is True
        assert n['property_id']==0 and n['properties']==[]
    return True
def text_fields(pya,layout,cell,records):
    out=[]
    for i in layout.layer_indexes():
        info=layout.get_info(i)
        for s in cell.each_shape(i):
            if not s.is_text():continue
            t=s.text
            matches=[r for r in records if r['layer']==info.layer and r['datatype']==info.datatype and r['raw']==s.to_s()]
            assert len(matches)==1
            out.append(dict(layer=info.layer,datatype=info.datatype,string=t.string,transform=t.trans.to_s(),
              x=t.x,y=t.y,size=t.size,font=t.font,halign_center=t.halign==pya.Text.HAlignCenter,
              valign_center=t.valign==pya.Text.VAlignCenter,property_id=s.prop_id,properties=matches[0]['properties']))
    return sorted(out,key=lambda r:(r['layer'],r['datatype']))
def check_serialized(pya,N,native,R,static,want):
    # Both full raw inventories are pinned by the actual completed observation.
    # This equality admits no additional raw difference on any shape or property.
    got=json.loads(observed.encoded(observed.pair(pya,N,native,R,static)));observed.validate_pair(got)
    assert got==want,'Different actual drawing, text, property or serialized witness'
    assert got['all_layer_sets_equal']and got['all_layer_material_equal']
    assert got['native_shape_count']==got['serialized_shape_count']==21
    assert got['pin_difference']['equal']and len(got['native_pin_shapes'])==len(got['serialized_pin_shapes'])==2
    nontext=lambda rows:sorted([(r['layer'],r['datatype'],r['kind'],r['raw'],r['property_id'],r['properties'])
      for r in rows if r['kind']!='text'],key=observed.encoded)
    assert nontext(got['native_records'])==nontext(got['serialized_records'])
    assert len(got['raw_difference']['left_only'])==len(got['raw_difference']['right_only'])==2
    assert pya.Text().font==-1,'Actual default constructor must expose NoFont, not DefaultFont0'
    n=text_fields(pya,N,native,got['native_records']);s=text_fields(pya,R,static,got['serialized_records'])
    validate_fields(static.name,n,s)
    pins=[frozen.witness.box_values(shape.box)for shape in static.each_shape(R.layer(8,2))if shape.is_box()]
    assert len(pins)==2 and len({tuple(p)for p in pins})==2
    return dict(all_layers=got['all_layers'],all_raw_shapes=got['serialized_raw_shapes'],all_text=got['serialized_text'],
      exact_annotations=got['serialized_pin_shapes'],metal1_pin_boxes=sorted(pins),
      actual_font_fields=dict(native=n,serialized=s,native_font=2,serialized_font=-1,serialized_is_NoFont_not_DefaultFont=True),
      complete_original_comparison=got,no_text_or_shape_mutated=True)
def original_failure(exact,pya,N,O,R,static):
    try:exact(pya,N,O,R,static)
    except AssertionError as error:
        tb=error.__traceback__
        while tb.tb_next is not None:tb=tb.tb_next
        assert error.args==('Changed complete raw native shapes',)
        assert tb.tb_frame.f_code is exact.__code__ and tb.tb_lineno==40
        f=tb.tb_frame.f_locals
        assert f['native_layout']is N and f['native']is O and f['static_layout']is R and f['static']is static
        return dict(error=repr(error),function='exact_static',line=40,
          exact_code_object_bound=True,actual_first_native_and_saved_cell_objects_bound=True,
          original_rejection_preserved=True)
    raise AssertionError('Original exact raw-shape rejection did not recur')
def native_controls(pya,N,natives,R,cells,wants):
    rejected=[];positive_copies=0
    def fields_change(change):
        def mutate(L,c):
            shapes=[s for s in c.each_shape(L.layer(52,0))if s.is_text()]
            assert len(shapes)==1
            shape=shapes[0];t=shape.text;change(t);shape.text=t
        return mutate
    def text_shape(L,c):
        shapes=[s for s in c.each_shape(L.layer(52,0))if s.is_text()]
        assert len(shapes)==1;return shapes[0]
    def move_layer(L,c):
        s=text_shape(L,c);t=s.text;s.delete();c.shapes(L.layer(53,0)).insert(t)
    def remove(L,c):text_shape(L,c).delete()
    def duplicate(L,c):c.shapes(L.layer(52,0)).insert(text_shape(L,c).text)
    def property_change(L,c):text_shape(L,c).set_property('font_contract_fault','changed')
    mutations=[
      ('changed_label',fields_change(lambda t:setattr(t,'string',t.string+'X'))),
      ('changed_x',fields_change(lambda t:setattr(t,'x',t.x+1))),
      ('changed_y',fields_change(lambda t:setattr(t,'y',t.y+1))),
      ('changed_transform',fields_change(lambda t:setattr(t,'trans',pya.Trans(1,t.x,t.y)))),
      ('changed_size',fields_change(lambda t:setattr(t,'size',t.size+1))),
      ('changed_halign',fields_change(lambda t:setattr(t,'halign',pya.Text.HAlignLeft))),
      ('changed_valign',fields_change(lambda t:setattr(t,'valign',pya.Text.VAlignBottom))),
      ('DefaultFont0_not_NoFont',fields_change(lambda t:setattr(t,'font',0))),
      ('unexpected_font1',fields_change(lambda t:setattr(t,'font',1))),
      ('native_font2_on_serialized',fields_change(lambda t:setattr(t,'font',2))),
      ('changed_text_layer',move_layer),('missing_text',remove),('duplicated_text',duplicate),
      ('changed_text_property',property_change)]
    for native,name,want in zip(natives,frozen.NAMES,wants):
        for label,mutate in mutations:
            L=pya.Layout();L.dbu=.001;c=L.create_cell(name);c.copy_tree(cells[name])
            check_serialized(pya,N,native,L,c,want);positive_copies+=1
            mutate(L,c)
            try:check_serialized(pya,N,native,L,c,want)
            except AssertionError:rejected.append(name+':'+label)
            else:raise AssertionError('Accepted actual serialized font/text corruption '+label)
    assert len(rejected)==28 and positive_copies==28
    return dict(rejected=rejected,positive_exact_saved_copies=positive_copies,actual_serialized_shapes_mutated=True,
      no_original_candidate_or_saved_sidecar_mutated=True)
def admit_all(pya,N,O,F,R,cells,exact,path):
    wants=expected()
    proof=dict(status='RUNNING_EXACT_OBSERVED_FONT_ROUNDTRIP_ADMISSION',annotation_binding_accepted=False,
      comparison_sha256=COMPARISON_SHA,source_audit_sha256=AUDIT_SHA,source_audit_is_not_embedded_module_attestation=True,
      pya_reported_version=str(getattr(pya,'__version__','unavailable')),material_or_electrical_acceptance=False)
    def save():frozen.witness.write(path,proof)
    save()
    try:
        proof['original_failure']=original_failure(exact,pya,N,O,R,cells[frozen.NAMES[0]]);save()
        rows=[dict(cell=name,**check_serialized(pya,N,native,R,cells[name],want))
          for name,native,want in zip(frozen.NAMES,(O,F),wants)]
        proof['serialized']=rows;save()
        proof['native_controls']=native_controls(pya,N,(O,F),R,cells,wants);save()
        proof['status']='PASS_ONLY_EXACT_OBSERVED_FONT2_TO_NoFont_TRANSITION_ALL_OTHER_FIELDS_EXACT'
        save();return rows
    except BaseException as error:
        proof.update(status='FAIL_EXACT_FONT_ROUNDTRIP_CONTRACT',error=repr(error));save();raise
def derive(original):
    assert digest(original)==observed.FROZEN_SHA
    edits=[
      ("for n in('capsule','pdk','out'):","for n in('capsule','pdk','out','saved-sidecar'):"),
      ("S.write(str(sidecar))","assert a.saved_sidecar.resolve()!=sidecar and a.saved_sidecar.stat().st_size==2910\n        assert sha(a.saved_sidecar)=='"+observed.SIDECAR_SHA+"'\n        sidecar.write_bytes(a.saved_sidecar.read_bytes());assert sha(sidecar)=='"+observed.SIDECAR_SHA+"'"),
      ("        serialized=[dict(cell=name,**exact_static(pya,N,native,R,cells[name]))\n          for name,native in zip(NAMES,(O,F))]",
       "        from cdr_v59_font_roundtrip_contract import admit_all\n        serialized=admit_all(pya,N,O,F,R,cells,exact_static,out/'font-roundtrip.json')")]
    generated=original
    for before,after in edits:
        assert generated.count(before)==1;generated=generated.replace(before,after)
    reversed_source=generated
    for before,after in reversed(edits):
        assert reversed_source.count(after)==1;reversed_source=reversed_source.replace(after,before)
    assert reversed_source==original
    old={n.name:ast.dump(n)for n in ast.parse(original).body if isinstance(n,ast.FunctionDef)}
    new={n.name:ast.dump(n)for n in ast.parse(generated).body if isinstance(n,ast.FunctionDef)}
    assert set(old)==set(new)and all(new[n]==v for n,v in old.items()if n!='main')
    assert generated.splitlines()[39]==original.splitlines()[39]
    return generated,dict(original_sha256=observed.FROZEN_SHA,generated_sha256=digest(generated),
      reversible_edits=[dict(before=a,after=b,count=1)for a,b in edits],
      unchanged_functions=[n for n in old if n!='main'],preserialization_native_to_static_exact_unchanged=True,
      original_raw_failure_required_before_narrow_admission=True,original_recovery_and10_native_controls_unchanged=True)
def controls():
    generated,proof=derive((ROOT/observed.FROZEN).read_text());wants=expected();rejected=[]
    assert all(w['native_shape_count']==w['serialized_shape_count']==21 and w['all_layer_material_equal']and w['pin_difference']['equal']for w in wants)
    def fixture(name):
        a=[dict(layer=layer,datatype=0,string=v[0],transform=v[1],x=v[2],y=v[3],size=v[4],font=2,
          halign_center=True,valign_center=True,property_id=0,properties=[])for layer,v in LABELS[name].items()]
        b=copy.deepcopy(a)
        for v in b:v['font']=-1
        return a,b
    name=frozen.NAMES[0];a,b=fixture(name);validate_fields(name,a,b)
    cases=[('native_font',lambda a,b:a[0].__setitem__('font',0)),
      ('saved_DefaultFont0',lambda a,b:b[0].__setitem__('font',0)),
      ('saved_font1',lambda a,b:b[0].__setitem__('font',1)),
      ('saved_font2',lambda a,b:b[0].__setitem__('font',2)),
      ('changed_string',lambda a,b:b[0].__setitem__('string','wrong')),
      ('changed_transform',lambda a,b:b[0].__setitem__('transform','r90 2000,3700')),
      ('changed_x',lambda a,b:b[0].__setitem__('x',2001)),
      ('changed_y',lambda a,b:b[0].__setitem__('y',3701)),
      ('changed_size',lambda a,b:b[0].__setitem__('size',2)),
      ('changed_halign',lambda a,b:b[0].__setitem__('halign_center',False)),
      ('changed_valign',lambda a,b:b[0].__setitem__('valign_center',False)),
      ('changed_layer',lambda a,b:b[0].__setitem__('layer',53)),
      ('changed_property',lambda a,b:b[0].__setitem__('properties',[['fault','changed']])),
      ('missing_label',lambda a,b:b.pop()),
      ('extra_label',lambda a,b:b.append(copy.deepcopy(b[0])))]
    for label,mutate in cases:
        x,y=copy.deepcopy((a,b));mutate(x,y)
        try:validate_fields(name,x,y)
        except AssertionError:rejected.append(label)
        else:raise AssertionError('Accepted font contract fixture '+label)
    try:derive((ROOT/observed.FROZEN).read_text()+'\n')
    except AssertionError:rejected.append('changed_frozen_source')
    else:raise AssertionError('Changed frozen source accepted')
    assert len(rejected)==16
    return dict(status='PASS16_EXACT_FONT_CONTRACT_AND_DERIVATION_SOURCE_CONTROLS',rejected=rejected,
      derivation=proof,actual_numeric_accessors_executed=False,native_shapes_executed=False,
      positive_scope='Explicit numeric field fixtures only; actual saved raw comparison authenticated, native accessors remain unexecuted.')
