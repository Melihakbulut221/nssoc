#!/usr/bin/env python3
# SPDX-FileCopyrightText: 2026 Hasan Melih Akbulut
# SPDX-License-Identifier: Apache-2.0
"""Apply exactly nine measured sizes, legalize only them, preserve every other cell and net."""
import hashlib,json,os
from pathlib import Path
import odb
from route_cloud_newer_postcts import sha
ROOT=Path(__file__).resolve().parents[1];OUT=ROOT/'cloud-route234-sized-eco';PARENT=OUT/'parent/routed.odb'
SOURCE_SHA='4a044ffdb4d92ec3e9150cb4a9696ed7dbfacc05361e64bc6b278259e6c3eeb4'
def signature(i):
    return dict(master=i.getMaster().getName(),location=list(i.getLocation()),orientation=str(i.getOrient()),status=str(i.getPlacementStatus()),pins={t.getMTerm().getName():t.getNet().getName()if t.getNet()else None for t in i.getITerms()})
def fixed(db):
    block=db.getChip().getBlock();rows=[]
    for n in block.getNets():
        rule=n.getNonDefaultRule()
        rows.append(('net',n.getName(),str(n.getSigType()),sorted((t.getInst().getName(),t.getMTerm().getName())for t in n.getITerms()),sorted(t.getName()for t in n.getBTerms())))
        if rule:rows.append(('ndr',n.getName(),rule.getName(),rule.getHardSpacing(),[(l.getName(),rule.getLayerRule(l).getWidth(),rule.getLayerRule(l).getSpacing())for l in db.getTech().getLayers()if rule.getLayerRule(l)]))
        if str(n.getSigType())in ('POWER','GROUND'):
            rows.append(('power',n.getName(),[(b.isVia(),b.getTechVia().getName()if b.isVia()and b.getTechVia()else None,b.getBlockVia().getName()if b.isVia()and b.getBlockVia()else None,b.getTechLayer().getName()if not b.isVia()else None,b.xMin(),b.yMin(),b.xMax(),b.yMax())for w in n.getSWires()for b in w.getWires()]))
    rows += [('port',p.getName(),str(p.getIoType()),str(p.getSigType()),[(b.getTechLayer().getName(),b.xMin(),b.yMin(),b.xMax(),b.yMax())for pin in p.getBPins()for b in pin.getBoxes()])for p in block.getBTerms()]
    return hashlib.sha256(json.dumps(rows,sort_keys=True).encode()).hexdigest()
def load(path):
    db=odb.dbDatabase.create();odb.read_db(db,str(path));return db
assert sha(PARENT)==SOURCE_SHA
source=load(PARENT);base=source.getChip().getBlock()
assert len(base.getInsts())==114025 and len(base.getNets())==114097
original={i.getName():signature(i)for i in base.getInsts()};fixed_hash=fixed(source)
screen=json.loads((OUT/'sizing-screen.json').read_text())
assert screen['status']=='COMPLETE_AVAILABLE_DRIVER_FROZEN_RC_SIZING_SCREEN_NOT_PHYSICAL_ACCEPTANCE'
changes=screen['preparation']['changes'];assert len(changes)==9 and [r['index']for r in changes]==[2,5,7,8,9,10,11,12,13]
targets={r['pin'].rsplit('/',1)[0]:r for r in changes}
mode=os.environ['NSSOC_SIZED_ECO_MODE']
(OUT/'source-targets.json').write_text(json.dumps({n:original[n]for n in targets},indent=2)+'\n')
def validate(db,restore_status=False):
    b=db.getChip().getBlock();assert len(b.getInsts())==114025 and len(b.getNets())==114097 and {i.getName()for i in b.getInsts()}==set(original)
    delta=[];limit=200*db.getTech().getDbUnitsPerMicron()
    for i in b.getInsts():
        name=i.getName();observed=signature(i);expected=dict(original[name])
        if name in targets:
            expected['master']=targets[name]['replacement']
            displacement=[observed['location'][k]-expected['location'][k]for k in (0,1)]
            assert max(map(abs,displacement))<=limit,('Selected move outside200um',name)
            expected['location']=observed['location']
            if mode=='prepare':
                assert observed['orientation']==original[name]['orientation'],('Preparation changed source orientation',name)
            else:
                # Horizontal site rotations/reflections; native check_placement
                # is authoritative for actual row and master symmetry legality.
                assert observed['orientation'] in ('R0','MX','MY','R180'),('Non-horizontal cell orientation',name,observed['orientation'])
            expected['orientation']=observed['orientation']
            delta.append(dict(instance=name,before=original[name],after=dict(observed,status=original[name]['status']),displacement_dbu=displacement))
        observed['status']=expected['status']
        assert observed==expected,('Unexpected retained cell change',name)
        if restore_status:i.setPlacementStatus(original[name]['status'])
    assert fixed(db)==fixed_hash,'Net membership, PG, NDR or top pins changed'
    return sorted(delta,key=lambda x:x['instance'])
if mode=='prepare':
    db=load(PARENT);b=db.getChip().getBlock()
    for i in b.getInsts():i.setPlacementStatus('FIRM')
    for name,row in targets.items():
        i=b.findInst(name);assert original[name]['master']==row['master']and original[name]['location']==row['location_dbu']
        m=db.findMaster(row['replacement']);assert m
        assert {(t.getName(),str(t.getIoType()),str(t.getSigType()))for t in m.getMTerms()}=={(t.getName(),str(t.getIoType()),str(t.getSigType()))for t in i.getMaster().getMTerms()}
        i.setPlacementStatus('PLACED');anchor=i.getLocation();assert i.swapMaster(m);i.setLocation(*anchor)
    validate(db)
    odb.write_db(db,str(OUT/'proposed.odb'))
elif mode=='audit':
    db=load(OUT/'legalized.odb');delta=validate(db,True);b=db.getChip().getBlock()
    control=next(i for i in b.getInsts()if i.getName()not in targets);anchor=control.getLocation();saved_status=control.getPlacementStatus();control.setPlacementStatus('PLACED');control.setLocation(anchor[0]+1000,anchor[1])
    try:validate(db)
    except AssertionError as e:assert 'Unexpected retained cell change'in str(e)
    else:raise AssertionError('Unselected movement fault escaped')
    control.setLocation(*anchor);control.setPlacementStatus(saved_status);assert validate(db)==delta
    selected=sorted({t.getNet().getName()for name in targets for t in b.findInst(name).getITerms()if t.getNet()and str(t.getNet().getSigType())not in ('POWER','GROUND')})
    assert selected
    odb.write_db(db,str(OUT/'candidate.odb'))
    (OUT/'geometry-proof.json').write_text(json.dumps(dict(status='PASS_EXACT_NINE_SIZES_ONLY_SELECTED_LEGAL_MOVEMENT',parent_odb_sha256=SOURCE_SHA,instances=114025,nets=114097,changes=delta,selected_nets=selected,fixed_net_pg_ndr_pin_sha256=fixed_hash,unselected_movement_control='REJECTED',accepted=False),indent=2)+'\n')
elif mode=='guide-input':
    # GRT excludes nets already carrying detailed dbWire routes. Remove only
    # the23 resized-cell nets on a separate copy; keep candidate.odb intact.
    candidate=OUT/'candidate.odb';candidate_sha=sha(candidate)
    db=load(candidate);validate(db);b=db.getChip().getBlock()
    candidate_cells={i.getName():signature(i)for i in b.getInsts()}
    receipt=json.loads((OUT/'geometry-proof.json').read_text())
    selected=set(receipt['selected_nets'])
    actual={t.getNet().getName()for name in targets for t in b.findInst(name).getITerms()if t.getNet()and str(t.getNet().getSigType())not in ('POWER','GROUND')}
    assert selected==actual and len(selected)==23
    def wires():
        result={}
        for n in b.getNets():
            w=n.getWire()
            payload=None if w is None else [(str(w.getOpcode(k)),w.getData(k))for k in range(w.length())]
            special=[(str(sw.getWireType()),[(x.isVia(),x.getTechVia().getName()if x.isVia()and x.getTechVia()else None,x.getBlockVia().getName()if x.isVia()and x.getBlockVia()else None,x.getTechLayer().getName()if not x.isVia()else None,x.xMin(),x.yMin(),x.xMax(),x.yMax())for x in sw.getWires()])for sw in n.getSWires()]
            result[n.getName()]=dict(wire_sha256=None if payload is None else hashlib.sha256(json.dumps(payload,separators=(',',':')).encode()).hexdigest(),wire_type=str(n.getWireType()),special=n.isSpecial(),special_wires_sha256=hashlib.sha256(json.dumps(special,separators=(',',':')).encode()).hexdigest())
        return result
    before=wires()
    # saveGuides only replaces routed nets; write_guides exports every dbGuide.
    # Remove stale guide metadata on this disposable copy before selected GRT.
    # Actual wires remain obstacles and are audited independently below.
    old_guides={n.getName():len(list(n.getGuides()))for n in b.getNets()}
    assert sum(v>0 for v in old_guides.values())==113790
    for n in b.getNets():n.clearGuides()
    assert not any(list(n.getGuides())for n in b.getNets())
    expected={name:dict(row,wire_sha256=None)if name in selected else row for name,row in before.items()}
    for name in sorted(selected):
        n=b.findNet(name)
        assert str(n.getSigType())not in ('POWER','GROUND')and not n.isSpecial()and not list(n.getSWires())
        assert n.getWire()is not None and before[name]['wire_sha256']is not None
        odb.dbWire.destroy(n.getWire())
    def verify_guide_copy():
        assert not any(list(n.getGuides())for n in b.getNets()),'Stale guide metadata survived'
        assert wires()==expected,'Unexpected wire removal or route mutation'
        assert {i.getName():signature(i)for i in b.getInsts()}==candidate_cells
        assert fixed(db)==fixed_hash
    verify_guide_copy()
    # A real unselected wire loss must be detected by the same full census.
    victim=next(n for n in b.getNets()if n.getName()not in selected and n.getWire()and str(n.getSigType())=='SIGNAL')
    held=victim.getWire();held.detach()
    try:verify_guide_copy()
    except AssertionError as error:assert 'Unexpected wire removal'in str(error)
    else:raise AssertionError('Unselected wire removal escaped')
    held.attach(victim);verify_guide_copy()
    odb.write_db(db,str(OUT/'guide-input.odb'))
    # Re-read the published database, so serialization is also covered.
    db=load(OUT/'guide-input.odb');b=db.getChip().getBlock();verify_guide_copy()
    assert sha(candidate)==candidate_sha
    (OUT/'guide-input-proof.json').write_text(json.dumps(dict(status='PASS_EXACT_23_SIGNAL_WIRES_REMOVED_ONLY_FROM_GUIDE_COPY',accepted=False,candidate_odb_sha256=candidate_sha,guide_input_odb_sha256=sha(OUT/'guide-input.odb'),selected_nets=sorted(selected),removed_wire_sha256={n:before[n]['wire_sha256']for n in sorted(selected)},unselected_wire_count=sum(v['wire_sha256']is not None for n,v in before.items()if n not in selected),all_unselected_wire_opcodes_and_data_unchanged=True,all_cells_and_net_membership_unchanged=True,all_special_wires_and_pg_ndr_ports_unchanged=True,unselected_wire_loss_control='REJECTED',candidate_odb_unchanged=True,old_guide_nets_cleared=sum(v>0 for v in old_guides.values()),old_guide_rectangles_cleared=sum(old_guides.values()),guide_metadata_empty_before_grt=True),indent=2)+'\n')
elif mode=='route-input':
    # Full DRT must reconstruct all signal routes against the new cell geometry.
    # Retaining old dbWires as pre-routed geometry left two selected nets broken
    # in38925935829. Keep the original candidate and all merged guide bytes.
    candidate=OUT/'candidate.odb';candidate_sha=sha(candidate)
    db=load(candidate);validate(db);b=db.getChip().getBlock()
    expected_cells={i.getName():signature(i)for i in b.getInsts()}
    removed=[];global_removed=[];guide_count=0
    for n in b.getNets():
        if str(n.getSigType())in ('POWER','GROUND'):continue
        assert not n.getSWires()and n.getRSegCount()==n.getCapNodeCount()==0
        w,g=n.getWire(),n.getGlobalWire()
        if g and (not w or g.getId()!=w.getId()):
            global_removed.append(n.getName());odb.dbWire.destroy(g)
        if w:
            payload=[(str(w.getOpcode(k)),w.getData(k))for k in range(w.length())]
            removed.append(dict(net=n.getName(),sha256=hashlib.sha256(json.dumps(payload,separators=(',',':')).encode()).hexdigest()))
            odb.dbWire.destroy(w)
        guide_count+=len(list(n.getGuides()));n.clearGuides()
    assert len(removed)==113790
    def verify_unrouted():
        assert {i.getName():signature(i)for i in b.getInsts()}==expected_cells
        assert fixed(db)==fixed_hash,'Net membership, PG, NDR or boundary changed while clearing signal routes'
        for n in b.getNets():
            if str(n.getSigType())not in ('POWER','GROUND'):
                assert n.getWire()is None and n.getGlobalWire()is None and not n.getGuides()
    verify_unrouted();odb.write_db(db,str(OUT/'detailed-route-input.odb'))
    db=load(OUT/'detailed-route-input.odb');b=db.getChip().getBlock();verify_unrouted()
    assert sha(candidate)==candidate_sha
    (OUT/'route-input-proof.json').write_text(json.dumps(dict(status='PASS_ALL_SIGNAL_ROUTES_CLEARED_FOR_FULL_DRT_ONLY',accepted=False,candidate_odb_sha256=candidate_sha,route_input_odb_sha256=sha(OUT/'detailed-route-input.odb'),removed_detailed_wire_count=len(removed),removed_detailed_wires=removed,removed_global_wires=global_removed,cleared_signal_guides=guide_count,all_cells_net_membership_pg_ndr_ports_unchanged=True,candidate_odb_unchanged=True,all_signal_routes_must_be_rebuilt=True),indent=2)+'\n')
elif mode=='audit-routed':
    db=load(OUT/'routed.odb');validate(db);b=db.getChip().getBlock();reference=load(OUT/'candidate.odb')
    assert {i.getName():signature(i)for i in b.getInsts()}=={i.getName():signature(i)for i in reference.getChip().getBlock().getInsts()}
    (OUT/'post-route-geometry.json').write_text(json.dumps(dict(status='PASS_NINE_SIZED_CELLS_AND_ALL_NET_MEMBERSHIP_PRESERVED_AFTER_ROUTE',routed_odb_sha256=sha(OUT/'routed.odb'),candidate_odb_sha256=sha(OUT/'candidate.odb'),instances=114025,nets=114097,accepted=False),indent=2)+'\n')
else:raise AssertionError('Unsupported mode')
assert sha(PARENT)==SOURCE_SHA
