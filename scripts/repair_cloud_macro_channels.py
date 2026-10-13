#!/usr/bin/env python3
# SPDX-FileCopyrightText: 2026 Hasan Melih Akbulut
# SPDX-License-Identifier: Apache-2.0
"""Native placement-only experiment for source-bound SRAM-channel congestion.

Run by OpenROAD Python on hosted runners. Selected combinational endpoint
cells move out of SRAM channels; every other cell is temporarily fixed. Exact
connectivity, masters and all unselected positions are checked after native
legalization. Nothing is an adopted design or timing/route signoff.
"""
import hashlib
import json
import os
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


def check(block,before):
    assert signature(block)==before['connectivity_sha256'],'Connectivity or masters changed'
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
    path=OUT/'endpoint-diagnosis.json';assert sha(path)==DIAGNOSIS_SHA
    d=json.loads(path.read_text());assert d['source_odb_sha256']==SOURCE_SHA
    db,block=load(source);scale=block.getDbUnitsPerMicron()
    instances={i.getName():i for i in block.getInsts()}
    seen={p['instance']:p for net in d['all_congested_net_endpoints'].values() for p in net['terminals']}
    selected={}
    eligible_before_clock=[]
    requested_profile=os.environ['NSSOC_PLACEMENT_PROFILE']
    include_data_buffers=requested_profile=='local_optimize_buffers'
    for name,p in seen.items():
        inst=instances[name];b=inst.getBBox()
        actual=[v/scale for v in (b.xMin(),b.yMin(),b.xMax(),b.yMax())]
        assert actual==p['bbox_um'] and inst.getMaster().getName()==p['master']
        eligible=name.startswith('$abc$') or (include_data_buffers and
            p['master'].startswith(('sg13g2_buf_','sg13g2_inv_')))
        upper_y=1750 if include_data_buffers else 1700
        if not(eligible and not p['macro'] and actual[0]>=2340 and 1180<=actual[1]<=upper_y):
            continue
        eligible_before_clock.append(name)
        if include_data_buffers and any(t.getNet() and
               (str(t.getNet().getSigType())=='CLOCK' or t.getNet().getName().startswith('clknet_'))
               for t in inst.getITerms()):
            continue  # Preserve every clock-connected cell, including clock buffers.
        # Guard against mapped combinational clock gating despite its ABC name.
        if any(str(t.getIoType())=='OUTPUT' and t.getNet() and
               (str(t.getNet().getSigType())=='CLOCK' or t.getNet().getName().startswith('clknet_'))
               for t in inst.getITerms()):
            continue
        assert str(inst.getPlacementStatus())=='PLACED',name
        selected[name]=inst
    # Exact spatial/master envelope from the frozen diagnosis, before native
    # clock-connectivity exclusion. The old932bound described ABC-only cells.
    expected_envelope=1563 if include_data_buffers else 932
    assert len(eligible_before_clock)==expected_envelope
    assert 0<len(selected)<=expected_envelope
    before=dict(connectivity_sha256=signature(block),source_odb_sha256=source_sha,original_odb_sha256=SOURCE_SHA,
        selected=sorted(selected),eligible_before_clock_count=len(eligible_before_clock),profile=os.environ['NSSOC_PLACEMENT_PROFILE'],
        instances={n:dict(position=position(i),status=str(i.getPlacementStatus())) for n,i in instances.items()})
    profile=before['profile'];assert profile in ('left_compact','left_spread','local_optimize','local_optimize_buffers')
    xstart,width={'left_compact':(2110.,160.),'left_spread':(2010.,260.),'local_optimize':(0.,0.),'local_optimize_buffers':(0.,0.)}[profile]
    for name,inst in instances.items():
        if name not in selected:
            if str(inst.getPlacementStatus())=='PLACED':inst.setPlacementStatus('FIRM')
        else:
            if profile in ('local_optimize','local_optimize_buffers'):
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
        selected_count=len(before['selected']),eligible_before_clock_count=before['eligible_before_clock_count'],changed_count=len(changed),changed=changed,
        native_fault_controls=['unselected_cell_displacement_rejected','disconnected_cell_pin_rejected'])
    (OUT/'placement-repair.json').write_text(json.dumps(report,indent=2)+'\n')
    print(json.dumps({k:v for k,v in report.items() if k!='changed'}),flush=True)


if __name__=='__main__':
    mode=os.environ['NSSOC_PLACEMENT_MODE'];assert mode in ('prepare','verify')
    prepare() if mode=='prepare' else verify()
