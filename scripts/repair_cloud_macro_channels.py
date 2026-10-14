#!/usr/bin/env python3
# SPDX-FileCopyrightText: 2026 Hasan Melih Akbulut
# SPDX-License-Identifier: Apache-2.0
"""Native placement-only experiment for source-bound SRAM-channel congestion.

Run by OpenROAD Python on hosted runners. Selected combinational endpoint
cells, and explicitly selected data flip-flops in the incremental profile,
may move near SRAM channels; every other cell is temporarily fixed. Exact
connectivity, masters and all unselected positions are checked after native
legalization. Nothing is an adopted design or timing/route signoff.
"""
import hashlib
import json
import os
import re
from pathlib import Path
import odb

OUT = Path('cloud-newer-postcts')
SOURCE = OUT / 'inputs/postcts.odb'
SOURCE_SHA = 'e4e04605899913e69784bc32d4fabc39350fec8b975c6fdab095a6b95262d292'
DIAGNOSIS_SHA = '1d19f4d2bdf24f865144b28c57060c3cfed96ac3d0a4a79b23ce23f12c0a027c'


def sha(path):
    with path.open('rb') as stream:
        return hashlib.file_digest(stream,'sha256').hexdigest()


def load(path):
    db=odb.dbDatabase.create();odb.read_db(db,str(path))
    return db,db.getChip().getBlock()


def signature(block):
    h=hashlib.sha256()
    for inst in sorted(block.getInsts(),key=lambda i:i.getName()):
        row=[inst.getName(),inst.getMaster().getName(),
             sorted((t.getMTerm().getName(),t.getNet().getName() if t.getNet() else None)
                    for t in inst.getITerms())]
        h.update((json.dumps(row,separators=(',',':'))+'\n').encode())
    for net in sorted(block.getNets(),key=lambda n:n.getName()):
        row=[net.getName(),str(net.getSigType()),sorted(t.getName() for t in net.getBTerms())]
        h.update((json.dumps(row,separators=(',',':'))+'\n').encode())
    return h.hexdigest()


def position(inst):
    return [*inst.getLocation(),str(inst.getOrient())]


def boundary_geometry(block):
    return {term.getName(): sorted((box.getTechLayer().getName(),box.xMin(),box.yMin(),box.xMax(),box.yMax())
            for pin in term.getBPins() for box in pin.getBoxes()) for term in block.getBTerms()}


def check(block,before):
    assert signature(block)==before['connectivity_sha256'],'Connectivity or masters changed'
    assert boundary_geometry(block)=={k:[tuple(x) for x in v] for k,v in before['boundary_geometry'].items()}, 'Boundary pin geometry changed'
    actual={i.getName():i for i in block.getInsts()}
    assert set(actual)==set(before['instances']),'Instance set changed'
    selected=set(before['selected'])
    for name,row in before['instances'].items():
        if name not in selected:
            assert position(actual[name])==row['position'],'Unselected placement changed: '+name
    return actual


def prepare():
    source=SOURCE;source_sha=SOURCE_SHA
    assert sha(SOURCE)==SOURCE_SHA
    depth=int(os.environ.get('NSSOC_ETHERNET_HOLD_DEPTH','0'));assert depth in (0,2)
    if depth:
        evidence=json.loads(Path('docs/evidence/cloud-ethernet-hold-estimate-20261013.json').read_text())
        case=next(c for c in evidence['cases'] if c['depth']==depth)
        assert case['logic']['status']=='PASS within scope' and case['inversion_control']=='EXPECTED_FUNCTIONAL_CHANGE_REJECTED'
        source=OUT/'inputs/ethernet-hold.odb';source_sha=case['candidate_odb_sha256']
        assert sha(source)==source_sha
    requested_profile=os.environ['NSSOC_PLACEMENT_PROFILE']
    routability=requested_profile=='routability_data'
    incremental=requested_profile in ('local_data_endpoints','routability_data')
    diagnosis_sha=DIAGNOSIS_SHA
    diagnosis_odb_sha=SOURCE_SHA
    if incremental:
        assert depth==2, 'Incremental source includes the proven Ethernet hold ECO'
        evidence_path = ('docs/evidence/cloud-seed13-buffers-route-failure-20261014.json' if routability
            else 'docs/evidence/cloud-local-optimize-buffers-route-failure-20261013.json')
        evidence=json.loads(Path(evidence_path).read_text())
        failure_outputs=evidence['failure_outputs']
        source=OUT/'inputs/previous-relocated.odb'
        source_sha=failure_outputs['relocated-placement.odb']
        assert sha(source)==source_sha
        diagnosis_odb_sha=failure_outputs['failed-global.odb']
        diagnosis_sha=('ca29ac20363e4f419ee3577dbd91085e48b541f91ca8d89f48e4bae72d46f01b' if routability
            else '962bf2b58b82799d346cb48a45a5af1d88fac6c10a2b582a2c41fc445000917f')
        failed_path=OUT/'inputs/previous-failed-global.odb'
        assert sha(failed_path)==diagnosis_odb_sha
        failed_db,failed_block=load(failed_path)
        candidate_db,candidate_block=load(source)
        assert signature(candidate_block)==signature(failed_block)
        failed_instances={i.getName():i for i in failed_block.getInsts()}
        assert all(position(i)==position(failed_instances[i.getName()]) for i in candidate_block.getInsts()), 'Failed-route diagnosis does not match resumed placement'
        hold_db,hold_block=load(OUT/'inputs/ethernet-hold.odb')
        assert signature(candidate_block)==signature(hold_block), 'Previous placement changed the proven hold-ECO connectivity'
    path=OUT/'endpoint-diagnosis.json';assert sha(path)==diagnosis_sha
    d=json.loads(path.read_text());assert d['source_odb_sha256']==diagnosis_odb_sha
    db,block=load(source);scale=block.getDbUnitsPerMicron()
    instances={i.getName():i for i in block.getInsts()}
    seen={p['instance']:p for net in d['all_congested_net_endpoints'].values() for p in net['terminals']}
    # Bind every diagnosed endpoint before selecting a broader data-only
    # placement domain. The new profile starts from the exact132-overflow DB.
    for name,p in seen.items():
        inst=instances[name]; box=inst.getBBox()
        assert [v/scale for v in (box.xMin(),box.yMin(),box.xMax(),box.yMax())]==p['bbox_um']
        assert inst.getMaster().getName()==p['master']
    preserved_hold=[]
    if routability:
        original_db,original_block=load(SOURCE)
        original_names={i.getName() for i in original_block.getInsts()}
        preserved_hold=sorted(set(instances)-original_names)
        assert len(preserved_hold)==20
        assert original_names <= set(instances)
        seen={}
        for name,inst in instances.items():
            box=inst.getBBox()
            seen[name]=dict(master=inst.getMaster().getName(),macro=inst.getMaster().isBlock(),
                bbox_um=[v/scale for v in (box.xMin(),box.yMin(),box.xMax(),box.yMax())])
    selected={}
    eligible_before_clock=[]
    include_data_buffers=requested_profile in ('local_optimize_buffers','local_data_endpoints','routability_data')
    for name,p in seen.items():
        inst=instances[name];b=inst.getBBox()
        actual=[v/scale for v in (b.xMin(),b.yMin(),b.xMax(),b.yMax())]
        assert actual==p['bbox_um'] and inst.getMaster().getName()==p['master']
        data_flop=incremental and not routability and p['master']=='sg13g2_dfrbpq_1'
        eligible=name.startswith('$abc$') or data_flop or (include_data_buffers and
            p['master'].startswith(('sg13g2_buf_','sg13g2_inv_')))
        upper_y=1750 if include_data_buffers else 1700
        in_x=(2280<=actual[0]<=3300) if incremental else actual[0]>=2340
        in_y=1180<=actual[1]<=upper_y
        if routability:
            eligible=bool(re.fullmatch(r'sg13g2_(?:a[0-9]+o?i?|o[0-9]+a?i?|and[0-9]+|nand[0-9]+|or[0-9]+|nor[0-9]+|xor[0-9]+|xnor[0-9]+|inv|buf|mux[0-9]+)_[0-9]+',p['master']))
            eligible=eligible and name not in preserved_hold and str(inst.getPlacementStatus())=='PLACED'
            in_x=in_y=True
        if not(eligible and not p['macro'] and in_x and in_y):
            continue
        eligible_before_clock.append(name)
        if include_data_buffers and not data_flop and any(t.getNet() and
               (str(t.getNet().getSigType())=='CLOCK' or t.getNet().getName().startswith('clknet_'))
               for t in inst.getITerms()):
            continue  # Only explicit data flops may have clock input connections.
        # Guard against mapped combinational clock gating despite its ABC name.
        if any(str(t.getIoType())=='OUTPUT' and t.getNet() and
               (str(t.getNet().getSigType())=='CLOCK' or t.getNet().getName().startswith('clknet_'))
               for t in inst.getITerms()):
            continue
        assert str(inst.getPlacementStatus())=='PLACED',name
        selected[name]=inst
    # Exact spatial/master envelope from the frozen diagnosis, before native
    # clock-connectivity exclusion. The old932bound described ABC-only cells.
    expected_envelope=1821 if incremental else (1563 if include_data_buffers else 932)
    if routability:
        assert len(selected)>1563, 'Routability profile must exceed prior narrow endpoint selection'
        expected_envelope=len(eligible_before_clock)
    assert len(eligible_before_clock)==expected_envelope
    assert 0<len(selected)<=expected_envelope
    before=dict(connectivity_sha256=signature(block),boundary_geometry=boundary_geometry(block),source_odb_sha256=source_sha,original_odb_sha256=SOURCE_SHA,
        selected=sorted(selected),eligible_before_clock_count=len(eligible_before_clock),profile=os.environ['NSSOC_PLACEMENT_PROFILE'],
        diagnosis_sha256=diagnosis_sha, diagnosis_odb_sha256=diagnosis_odb_sha,
        preserved_hold_cells=preserved_hold,
        selected_data_flops=[n for n,i in selected.items() if i.getMaster().getName()=='sg13g2_dfrbpq_1'],
        instances={n:dict(position=position(i),status=str(i.getPlacementStatus())) for n,i in instances.items()})
    if routability:
        assert not before['selected_data_flops'] and not set(preserved_hold)&set(selected)
    elif incremental:
        assert len(before['selected_data_flops'])==227, 'Changed source-bound data-flop envelope'
    profile=before['profile'];assert profile in ('left_compact','left_spread','local_optimize','local_optimize_buffers','local_data_endpoints','routability_data')
    xstart,width={'left_compact':(2110.,160.),'left_spread':(2010.,260.),'local_optimize':(0.,0.),'local_optimize_buffers':(0.,0.),'local_data_endpoints':(0.,0.),'routability_data':(0.,0.)}[profile]
    for name,inst in instances.items():
        if name not in selected:
            if str(inst.getPlacementStatus())=='PLACED':inst.setPlacementStatus('FIRM')
        else:
            if profile in ('local_optimize','local_optimize_buffers','local_data_endpoints','routability_data'):
                continue  # Native DPO starts from the exact original positions.
            x,y=inst.getLocation()
            fraction=(x/scale-2340.)/(3266.4-2340.)
            assert 0<=fraction<=1
            inst.setLocation(round((xstart+width*fraction)*scale),y)
    assert signature(block)==before['connectivity_sha256']
    (OUT/'placement-before.json').write_text(json.dumps(before,separators=(',',':'))+'\n')
    odb.write_db(db,str(OUT/'proposed-placement.odb'))
    print(json.dumps(dict(selected=len(selected),profile=profile,source_sha256=source_sha)),flush=True)


def verify():
    before=json.loads((OUT/'placement-before.json').read_text())
    db,block=load(OUT/'legalized-placement.odb')
    actual=check(block,before)
    # Two native in-memory corruption controls. Restore and recheck each before
    # writing the candidate: these do not alter the preserved source database.
    fixed=next(i for n,i in actual.items() if n not in before['selected'] and not i.getMaster().isBlock())
    old=fixed.getLocation();fixed_status=str(fixed.getPlacementStatus())
    # OpenDB itself forbids moving FIRM instances. Explicitly unlock only this
    # in-memory negative-control victim, then restore its original status.
    fixed.setPlacementStatus('PLACED')
    fixed.setLocation(old[0]+block.getDbUnitsPerMicron(),old[1])
    try:check(block,before)
    except AssertionError:pass
    else:raise AssertionError('Fixed-cell displacement escaped verification')
    fixed.setLocation(*old);fixed.setPlacementStatus(fixed_status);check(block,before)
    pin=next(t for t in actual[before['selected'][0]].getITerms() if t.getNet())
    net=pin.getNet();pin.disconnect()
    try:check(block,before)
    except AssertionError:pass
    else:raise AssertionError('Disconnected cell pin escaped verification')
    pin.connect(net);check(block,before)
    changed={n:dict(before=before['instances'][n]['position'],after=position(actual[n]))
             for n in before['selected'] if position(actual[n])!=before['instances'][n]['position']}
    assert changed,'Placement experiment produced no movement'
    for name,inst in actual.items():inst.setPlacementStatus(before['instances'][name]['status'])
    check(block,before)
    path=OUT/'relocated-placement.odb';odb.write_db(db,str(path))
    report=dict(status='PASS_NATIVE_PLACEMENT_ONLY_INVARIANTS_REQUIRES_STA_AND_ROUTING',
        profile=before['profile'],source_odb_sha256=before['source_odb_sha256'],
        original_odb_sha256=before.get('original_odb_sha256',SOURCE_SHA),output_odb_sha256=sha(path),
        connectivity_sha256=before['connectivity_sha256'],instances=len(actual),
        diagnosis_sha256=before['diagnosis_sha256'], diagnosis_odb_sha256=before['diagnosis_odb_sha256'],
        selected_data_flop_count=len(before['selected_data_flops']),
        preserved_hold_cells=before.get('preserved_hold_cells',[]),
        boundary_geometry_unchanged=True,
        changed_data_flop_count=sum(n in changed for n in before['selected_data_flops']),
        selected_count=len(before['selected']),eligible_before_clock_count=before['eligible_before_clock_count'],changed_count=len(changed),changed=changed,
        native_fault_controls=['unselected_cell_displacement_rejected','disconnected_cell_pin_rejected'])
    (OUT/'placement-repair.json').write_text(json.dumps(report,indent=2)+'\n')
    print(json.dumps({k:v for k,v in report.items() if k!='changed'}),flush=True)


if __name__=='__main__':
    mode=os.environ['NSSOC_PLACEMENT_MODE'];assert mode in ('prepare','verify')
    prepare() if mode=='prepare' else verify()
