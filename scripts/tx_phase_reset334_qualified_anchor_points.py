#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0
"""Exact recorded MIM reference relocation; no geometry, extraction or tolerance."""
import copy,hashlib,json
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
PHYSICAL='docs/evidence/tx-phase-reset334-physical-full-result-20261024.json'
PHYSICAL_SHA='5591fe784df1cc1294302ac38a13a8db4b6285f37335fa7c2fbe2d477c7fa913'
MIM='docs/evidence/tx-phase-reset334-intrinsic-mim-full-result-20261024.json'
MIM_SHA='02671c9de96e779054cc37f7be26f0625351f0238b25dc210e78e94cf2e6db1d'
SELECTION='actual_placed_mim_bottom_Metal5_access_outside_intrinsic_mask'

def provenance():
    p=(ROOT/PHYSICAL).read_bytes();m=(ROOT/MIM).read_bytes()
    assert hashlib.sha256(p).hexdigest()==PHYSICAL_SHA
    assert hashlib.sha256(m).hexdigest()==MIM_SHA
    physical=json.loads(p);mim=json.loads(m)
    assert physical['source_head']=='2e1f26e9c4fdf37d63433a0c859c2d305db3486b'
    assert mim['source_head']=='15f733863e43fb0ed3660829ffd24c2a1205139b'
    assert mim['physical_prerequisite']['summary_sha256']==PHYSICAL_SHA
    assert mim['validation_errors']==[] and mim['sources_unchanged'] and mim['generated_sources_unchanged']
    for sign in ('p','n'):
        v=mim['variants'][sign];g=v['mim_geometry']
        assert v['physical_GDS_sha256']==physical['variants'][sign]['wires']['physical_GDS_sha256']
        assert g['outputs']['anchors.json']==mim['outputs'][sign+'/mim/anchors.json']
        assert g['actual_mim_devices']==8 and g['physical_points']==695 and g['wire_components']==119
        assert all(g[k] for k in ('all_metal_via_drawings_unchanged','intrinsic_mask_union_exact',
            'all_original_native_terminal_identities_unchanged','all695_native_and_physical_owners_verified'))
        assert len(g['controls'])==6 and all(x['rejected'] for x in g['controls'])
    return physical,mim

def expected_fields(original,proof):
    """Replay only producer lines70-73 over pinned JSON; no PCell or native API."""
    rows=copy.deepcopy(original['rows']);anchors=copy.deepcopy(original['anchors'])
    byterm={(r['device'],r['terminal']):r for r in rows};bylabel={r['label']:r for r in anchors}
    assert len(rows)==len(byterm)==1010 and len(anchors)==len(bylabel)==695
    changes=proof['bottom_access_changes']
    assert len(changes)==8 and {x['native_id'] for x in changes}==set(range(237,245))
    assert len({x['reference_label'] for x in changes})==8
    for x in changes:
        r=byterm[x['native_id'],'mim_btm'];a=bylabel[x['reference_label']]
        assert r['model']=='cap_cmim' and r['reference_label']==a['label']==x['reference_label']
        assert r['metal']==a['metal']==67
        for key in ('native_cluster','wire_component'):assert r[key]==a[key]==x[key]
        assert r['point_dbu']==a['point_dbu']==x['old_point_dbu']
        assert x['old_point_dbu']!=x['new_point_dbu']
        assert len(x['new_point_dbu'])==2 and all(type(v)is int for v in x['new_point_dbu'])
        r['original_native_terminal_selection']=dict(selection=r['selection'],
            point_dbu=copy.deepcopy(x['old_point_dbu']),candidate_contacts=copy.deepcopy(r['candidate_contacts']))
        r['point_dbu']=copy.deepcopy(x['new_point_dbu']);a['point_dbu']=copy.deepcopy(x['new_point_dbu'])
        r['selection']=SELECTION
        r['candidate_contacts']=[dict(metal=67,point_dbu=copy.deepcopy(x['new_point_dbu']),kind=SELECTION)]
    assert len({(x['metal'],*x['point_dbu']) for x in anchors})==695
    return dict(rows=rows,anchors=anchors,public=copy.deepcopy(original['public']),
        mim_bottom_point_changes=copy.deepcopy(changes))

def validate(physical,mim,sign,planes):
    assert sign in ('p','n')
    original=physical['variants'][sign]['wires']['anchors']
    proof=mim['variants'][sign]['mim_geometry']
    expected=expected_fields(original,proof)
    for key,value in expected.items():assert planes[key]==value,('Qualified MIM coordinate field mismatch',sign,key)
    old={(r['device'],r['terminal']):r for r in original['rows']}
    mapping={}
    for r in planes['rows']:
        if 'reference_label' not in r:continue
        o=old[r['device'],r['terminal']];label=r['reference_label']
        assert label==o['reference_label'] and label not in mapping
        moved=o['point_dbu']!=r['point_dbu']
        mapping[label]=dict(native_id=r['device'],terminal=r['terminal'],model=r['model'],
            reference_label=label,native_cluster=r['native_cluster'],wire_component=r['wire_component'],
            original_native_point_dbu=copy.deepcopy(o['point_dbu']),RC_reference_point_dbu=copy.deepcopy(r['point_dbu']),
            recorded_MIM_bottom_relocation=moved)
    assert len(mapping)==684
    all_moved=[x for x in mapping.values() if x['recorded_MIM_bottom_relocation']]
    assert len(all_moved)==8 and all(x['model']=='cap_cmim' and x['terminal']=='mim_btm' for x in all_moved)
    avss=[x for x in mapping.values() if x['native_cluster']==17 and x['wire_component']==13]
    changed=[x for x in avss if x['recorded_MIM_bottom_relocation']]
    assert len(avss)==85 and len(changed)==2
    assert {(x['native_id'],x['terminal'],x['reference_label']) for x in changed}=={(243,'mim_btm','A0591'),(244,'mim_btm','A0593')}
    return mapping,dict(physical_summary_sha256=PHYSICAL_SHA,MIM_summary_sha256=MIM_SHA,
        all_terminal_rows_exact=1010,all_anchor_records_exact=695,recorded_MIM_changes=8,
        AVSS_original_point_equal=83,AVSS_recorded_MIM_changes=changed,
        coordinate_units='KLayout database units, 0.001 micrometer = 1 nm',
        coordinate_frame='Same translated physical layout frame; original plate center and qualified exterior bottom-metal access are distinct points.',
        coordinate_tolerance_used=False,geometry_regenerated=False)

def controls(physical,mim,actual_planes=None):
    """Source-derived JSON positives, or actual restored planes when supplied."""
    rejected=[];positive={}
    for sign in ('p','n'):
        original=physical['variants'][sign]['wires']['anchors'];proof=mim['variants'][sign]['mim_geometry']
        fixture=copy.deepcopy(actual_planes[sign]) if actual_planes is not None else expected_fields(original,proof)
        _,positive[sign]=validate(physical,mim,sign,fixture)
        def row(q,device,terminal):return next(r for r in q['rows'] if r['device']==device and r['terminal']==terminal)
        def anchor(q,label):return next(r for r in q['anchors'] if r['label']==label)
        def change(q,device):return next(r for r in q['mim_bottom_point_changes'] if r['native_id']==device)
        def reverse(q):
            r=row(q,243,'mim_btm');r['point_dbu'],r['original_native_terminal_selection']['point_dbu']=r['original_native_terminal_selection']['point_dbu'],r['point_dbu']
        def alias(q):
            row(q,244,'mim_btm')['point_dbu']=copy.deepcopy(row(q,243,'mim_btm')['point_dbu'])
            anchor(q,'A0593')['point_dbu']=copy.deepcopy(anchor(q,'A0591')['point_dbu'])
        faults=[
            ('unlisted_HBT_displacement',lambda q:row(q,3,'E')['point_dbu'].__setitem__(1,52023)),
            ('MIM_new_point',lambda q:row(q,243,'mim_btm')['point_dbu'].__setitem__(1,1333131)),
            ('MIM_old_witness',lambda q:row(q,243,'mim_btm')['original_native_terminal_selection']['point_dbu'].__setitem__(1,1334431)),
            ('reversed_points',reverse),('aliased_seed_access',alias),
            ('wrong_reference',lambda q:row(q,243,'mim_btm').update(reference_label='A0593')),
            ('wrong_device',lambda q:row(q,243,'mim_btm').update(device=244)),
            ('wrong_terminal',lambda q:row(q,243,'mim_btm').update(terminal='mim_top')),
            ('wrong_cluster',lambda q:row(q,243,'mim_btm').update(native_cluster=1)),
            ('wrong_component',lambda q:row(q,243,'mim_btm').update(wire_component=1)),
            ('wrong_metal',lambda q:row(q,243,'mim_btm').update(metal=8)),
            ('changed_anchor_point',lambda q:anchor(q,'A0591')['point_dbu'].__setitem__(0,873101)),
            ('missing_recorded_change',lambda q:q['mim_bottom_point_changes'].pop()),
            ('duplicate_recorded_change',lambda q:q['mim_bottom_point_changes'].append(copy.deepcopy(q['mim_bottom_point_changes'][0]))),
            ('wrong_change_old_point',lambda q:change(q,243)['old_point_dbu'].__setitem__(0,873101)),
            ('public_alias',lambda q:q['public'][0].update(reference_label='P_AVSS'))]
        for label,mutate in faults:
            q=copy.deepcopy(fixture);mutate(q);assert q!=fixture
            try:validate(physical,mim,sign,q)
            except (AssertionError,KeyError):rejected.append(sign+':'+label)
            else:raise AssertionError('Accepted coordinate corruption '+sign+':'+label)
    assert len(rejected)==32
    return dict(status='PASS_EXACT_RECORDED_MIM_COORDINATE_CONTROLS_ONLY',
        source_derived_JSON_fixture=actual_planes is None,restored_planes_exercised=actual_planes is not None,
        positives=positive,rejected=rejected,new_geometry_or_simulation=False)
