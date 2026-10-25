#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0
"""Reversible immutable-controller adaptations for one fresh AVSS18 RC pipeline."""
import ast,hashlib,json,os,shutil,types
from pathlib import Path
import tx_phase_reset334_avss18_rc_admission as a
ROOT=a.ROOT
GROUP='tx-phase-reset334-avss18-rc'
OUT=ROOT/'hw/soc/out/cloud-tx-phase-reset334-avss18-rc'
INTRINSIC=OUT/'intrinsic'
PRECISION=OUT/'precision'
FROZEN={
 'source':('scripts/tx_phase_reset334_intrinsic_mim_source.py','efaaa597d6fd7f228e5be58ffc481d1eb6a770005ff52d6f2e51defa48f87da1'),
 'intrinsic':('scripts/cloud_tx_phase_reset334_intrinsic_mim.py','c162ff874e7c4135567b2f9cb20ee28d4c9f275e1fde21aec4ed1dcb3def31a6'),
 'precision':('scripts/cloud_tx_phase_reset334_mim_precision.py','1a515a5c0eb8c9a50d0e7bcd79a39e25e6333455914e6d9b1c5ae6a506179967')}
OLD_GDS=dict(p='601e5611ae555d4a39891a095bce443851665853439d379377d9a1f6cb60c834',n='c30c73110c4e8f0507b2a10058a2dbfe9a7e2abb22dcb1af7cad1213e4df167b')

def derive(text,edits):
    original=text;records=[]
    for before,after,count in edits:
        assert before!=after and text.count(before)==count,(before,text.count(before),count)
        text=text.replace(before,after);records.append(dict(before=before,after=after,count=count))
    reverse=text
    for before,after,count in reversed(edits):
        assert reverse.count(after)==count;reverse=reverse.replace(after,before)
    assert reverse==original;ast.parse(text)
    return text,dict(original_sha256=a.digest(original.encode()),generated_sha256=a.digest(text.encode()),
      edits=records,reversed_byte_exact=True)

def changes(kind):
    if kind=='source':return [(OLD_GDS[p],a.GDS[p],1)for p in ('p','n')]
    if kind=='intrinsic':return [
      ("record,proof=reports.restore_report(SOURCE['group'],SOURCE['run'],SOURCE['summary'],SOURCE['parts'],physical,list(prior['outputs']))",
       "proof=_actual_physical_restore(prior,physical);record=prior",1)]
    assert kind=='precision'
    return [
      ("and len(prior['outputs'])==250","and len(prior['outputs'])==459",1),
      ("restored,proof=reports.restore_report(SOURCE['group'],SOURCE['run'],SOURCE['summary'],SOURCE['parts'],full,list(prior['outputs']))\n        assert restored==prior and sha(full/'result.json')==SOURCE['summary'];validate(restored);result['source']=proof;save()",
       "proof=_fresh_intrinsic_copy(prior,full);restored=prior\n        assert sha(full/'result.json')==_fresh_intrinsic_digest;validate(restored);result['source']=proof;save()",1),
      ("name='tx_phase_reset334_'+pol+'_'+kind+'_generated.py';path=ROOT/'scripts'/name;assert not path.exists()",
       "name='tx_phase_reset334_'+pol+'_'+kind+'_generated.py';path=ROOT/'scripts'/name;assert path.is_file()and not path.is_symlink()",1),
      ("path.write_text(data);generated[path]=sha(path)","assert path.read_text()==data;generated[path]=sha(path)",1),
      ("original_prefix='/home/runner/work/nssoc/nssoc/hw/soc/out/cloud-tx-phase-reset334-intrinsic-mim/'",
       "original_prefix='/home/runner/work/nssoc/nssoc/hw/soc/out/cloud-tx-phase-reset334-avss18-rc/intrinsic/'",1)]

def sources(kind,data=None):
    path,digest=FROZEN[kind];b=(ROOT/path).read_bytes()if data is None else data;assert a.digest(b)==digest
    return derive(b.decode(),changes(kind))

def module(kind):
    text,proof=sources(kind);path=ROOT/FROZEN[kind][0]
    m=types.ModuleType('avss18_frozen_'+kind);m.__file__=str(path)
    exec(compile(text,'avss18-derived-'+kind,'exec'),m.__dict__)
    assert a.sha(path)==FROZEN[kind][1]
    return m,proof

def inventory(root,expected):
    assert root.is_dir()and not root.is_symlink()
    for p in root.rglob('*'):assert not p.is_symlink()and(p.is_file()or p.is_dir())
    actual={str(p.relative_to(root)):a.sha(p)for p in root.rglob('*')if p.is_file()}
    assert actual==expected,'Fresh input inventory changed or has extra/missing files'
    return dict(files=len(actual),all_hashes_unchanged=True,inventory_sha256=a.digest((json.dumps(actual,sort_keys=True)+'\n').encode()))

def intrinsic_output_names():
    m=a.methods();_,p=a.physical()
    physical={'physical/'+n for n in a.expected_files(p)}
    transport={'physical-transport/summary.json','physical-transport/parts.json','physical-transport/'+a.ASSETS['archive']['name']}
    generated=set(m['original_intrinsic_generated_paths'])
    assert len(generated)==49 and not(physical&generated or transport&generated or physical&transport)
    result=physical|transport|generated;assert len(result)==459
    return result

def validate_relocations(original,current,changes):
    assert len(original['rows'])==len(current['rows'])==1010 and len(current['anchors'])==695
    assert len(changes)==8
    selected={(x['native_id'],'mim_btm'):x for x in changes};assert len(selected)==8
    labels={x['label']:x for x in current['anchors']};assert len(labels)==695
    old_labels={x['label']:x for x in original['anchors']};assert set(old_labels)==set(labels)
    moved={x['reference_label']:x for x in changes};assert len(moved)==8
    for label,before in old_labels.items():
        expected=dict(before)
        if label in moved:expected['point_dbu']=moved[label]['new_point_dbu']
        assert labels[label]==expected
    touched=[]
    for before,after in zip(original['rows'],current['rows'],strict=True):
        key=(before['device'],before['terminal']);assert key==(after['device'],after['terminal'])
        if key not in selected:
            assert before==after
            continue
        x=selected[key];touched.append(key)
        assert before['model']==after['model']=='cap_cmim'
        assert before['point_dbu']==x['old_point_dbu']and after['point_dbu']==x['new_point_dbu']
        assert x['old_point_dbu']!=x['new_point_dbu']
        for k in ('device','model','terminal','native_cluster','disposition','reference_label','metal','wire_component'):assert before[k]==after[k]
        assert after['reference_label']==x['reference_label']and after['native_cluster']==x['native_cluster']and after['wire_component']==x['wire_component']
        old=after['original_native_terminal_selection']
        assert old==dict(selection=before['selection'],point_dbu=before['point_dbu'],candidate_contacts=before['candidate_contacts'])
        assert after['selection']=='actual_placed_mim_bottom_Metal5_access_outside_intrinsic_mask'
        assert after['candidate_contacts']==[dict(metal=67,point_dbu=x['new_point_dbu'],kind=after['selection'])]
        anchor=labels[x['reference_label']]
        assert anchor['point_dbu']==x['new_point_dbu']and anchor['metal']==67
        assert anchor['native_cluster']==x['native_cluster']and anchor['wire_component']==x['wire_component']
    assert set(touched)==set(selected)
    return dict(relocated_bottom_accesses=8,other_terminal_rows_unchanged=1002,other_reference_planes_unchanged=687,
      original_native_and_fresh_extraction_points_both_retained=True)

def validate_intrinsic(r,root,algorithm):
    # The exact old validator retains every original model/MIM/ownership gate.
    p,_=module('precision');p.intrinsic_source=algorithm;p.SOURCE={'head':os.environ['GITHUB_SHA']}
    p.validate(r)
    assert set(r['outputs'])==intrinsic_output_names()
    assert r['physical_prerequisite']['source']==a.SOURCE
    assert r['restore']['all407_files_authenticated']and r['restore']['original_electrical_rejection_preserved']
    expected={**r['outputs'],'result.json':a.sha(root/'result.json')}
    proof=inventory(root,expected)
    assert json.loads((root/'result.json').read_bytes())==r
    for pol in ('p','n'):
        physical=root/'physical'/pol
        assert a.sha(physical/'layout'/('nssoc_tx_phase_reset244_'+pol+'_v1.gds'))==a.GDS[pol]
        g=r['variants'][pol]['mim_geometry'];anchors=json.loads((root/pol/'mim/anchors.json').read_bytes())
        original=json.loads((physical/'anchors.json').read_bytes())
        validate_relocations(original,anchors,g['bottom_access_changes'])
    return proof

def copy_intrinsic(prior,destination,algorithm):
    before=validate_intrinsic(prior,INTRINSIC,algorithm)
    assert not destination.exists();shutil.copytree(INTRINSIC,destination)
    expected={**prior['outputs'],'result.json':a.sha(INTRINSIC/'result.json')}
    copied=inventory(destination,expected);after=inventory(INTRINSIC,expected)
    assert before==copied==after
    return dict(fresh_current_run_intrinsic=True,source_head=os.environ['GITHUB_SHA'],
      prior_result_sha256=expected['result.json'],original=before,copied=copied,
      old_intrinsic_artifact_consumed=False,original_electrical_rejection_preserved=True)

def run_intrinsic():
    algorithm,algproof=module('source');m,proof=module('intrinsic')
    m.OUT=INTRINSIC;m.GROUP=GROUP;m.METHOD=a.METHOD;m.source=algorithm
    m.SOURCE={**a.SOURCE,'parts':a.ASSETS['parts']['sha256']};m.pins=a.methods
    m.prerequisite=a.prerequisite;m.validate=a.validate;m._actual_physical_restore=a.restore
    m.main()
    r=json.loads((INTRINSIC/'result.json').read_bytes())
    verified=validate_intrinsic(r,INTRINSIC,algorithm)
    return r,dict(source_derivation=algproof,controller_derivation=proof,complete_inventory=verified)

def run_precision(prior):
    algorithm,algproof=module('source');m,proof=module('precision')
    m.OUT=PRECISION;m.GROUP=GROUP;m.METHOD=a.METHOD;m.intrinsic_source=algorithm
    m.SOURCE={'head':os.environ['GITHUB_SHA']};m.pins=a.methods
    digest=a.sha(INTRINSIC/'result.json');m._fresh_intrinsic_digest=digest
    def prerequisite():
        validate_intrinsic(prior,INTRINSIC,algorithm);return prior
    m.prerequisite=prerequisite
    m._fresh_intrinsic_copy=lambda r,d:copy_intrinsic(r,d,algorithm)
    m.main()
    r=json.loads((PRECISION/'result.json').read_bytes())
    assert r['status']==m.STATUS and r['sources_unchanged']and not r['validation_errors']
    assert r['both_polarities_and_orders_verified']and r['native_RC_and_device_records_equal_in_both_orders']
    validate_intrinsic(prior,INTRINSIC,algorithm)
    return r,dict(source_derivation=algproof,controller_derivation=proof,
      fresh_intrinsic_result_sha256=digest,old_R_rescaled=False)
