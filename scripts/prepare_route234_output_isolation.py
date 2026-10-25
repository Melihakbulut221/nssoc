#!/usr/bin/env python3
# SPDX-FileCopyrightText: 2026 Hasan Melih Akbulut
# SPDX-License-Identifier: Apache-2.0
"""Five real output-isolation buffers: placement feasibility, never routed acceptance."""
import hashlib
import json
import os
from pathlib import Path
import odb
from route_cloud_newer_postcts import sha

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / 'cloud-route234-output-isolation'
PARENT = OUT / 'parent/routed.odb'
PARENT_SHA = '4a044ffdb4d92ec3e9150cb4a9696ed7dbfacc05361e64bc6b278259e6c3eeb4'
assert sha(PARENT) == PARENT_SHA

def load(path):
    db = odb.dbDatabase.create()
    odb.read_db(db, str(path))
    return db

def cells(block):
    return {i.getName(): dict(master=i.getMaster().getName(),
        location=list(i.getLocation()), origin=list(i.getOrigin()),
        orientation=str(i.getOrient()), status=str(i.getPlacementStatus()),
        pins={t.getMTerm().getName(): t.getNet().getName() if t.getNet() else None
              for t in i.getITerms()}) for i in block.getInsts()}

def nets(block):
    return {n.getName(): dict(signal=str(n.getSigType()),
        ndr=n.getNonDefaultRule().getName() if n.getNonDefaultRule() else None,
        special=n.isSpecial(),
        terminals=sorted((t.getInst().getName(), t.getMTerm().getName()) for t in n.getITerms()),
        ports=sorted(t.getName() for t in n.getBTerms())) for n in block.getNets()}

def fixed(db):
    b = db.getChip().getBlock()
    power = [(n.getName(), [(x.isVia(),
        x.getTechVia().getName() if x.isVia() and x.getTechVia() else None,
        x.getBlockVia().getName() if x.isVia() and x.getBlockVia() else None,
        x.getTechLayer().getName() if not x.isVia() else None,
        x.xMin(), x.yMin(), x.xMax(), x.yMax())
        for w in n.getSWires() for x in w.getWires()])
        for n in b.getNets() if str(n.getSigType()) in ('POWER','GROUND')]
    ports = [(p.getName(), str(p.getIoType()), str(p.getSigType()),
        [(x.getTechLayer().getName(), x.xMin(), x.yMin(), x.xMax(), x.yMax())
         for pin in p.getBPins() for x in pin.getBoxes()]) for p in b.getBTerms()]
    rules = []
    for n in b.getNets():
        rule = n.getNonDefaultRule()
        if rule:
            rules.append((n.getName(), rule.getName(), rule.getHardSpacing(),
                [(l.getName(), rule.getLayerRule(l).getWidth(), rule.getLayerRule(l).getSpacing())
                 for l in db.getTech().getLayers() if rule.getLayerRule(l)]))
    return dict(power=power, ports=ports, rules=rules)

source = load(PARENT)
sb = source.getChip().getBlock()
original = cells(sb)
original_nets = nets(sb)
original_fixed = fixed(source)
assert len(original) == 114025 and len(original_nets) == 114097
screen = json.loads((OUT / 'screen.json').read_text())
assert screen['status'] == 'COMPLETE_AVAILABLE_DRIVER_FROZEN_RC_SIZING_SCREEN_NOT_PHYSICAL_ACCEPTANCE'
requests = screen['preparation']['unavailable']
assert [r['index'] for r in requests] == [0, 1, 3, 4, 6]
expected_nets = {n: dict(v, terminals=list(v['terminals'])) for n, v in original_nets.items()}
expected_cells = {n: dict(v, pins=dict(v['pins'])) for n, v in original.items()}
plan = []
for k, row in enumerate(requests):
    name, pin = row['pin'].rsplit('/', 1)
    inst = sb.findInst(name)
    assert inst and inst.getMaster().getName() == row['master']
    term = inst.findITerm(pin)
    net = term.getNet()
    assert net.getName() == row['net'] and str(term.getIoType()) == 'OUTPUT'
    assert len(net.getITerms()) == 2 and not net.getBTerms() and not net.getNonDefaultRule()
    assert not net.getSWires() and not net.isSpecial() and str(net.getSigType()) == 'SIGNAL'
    assert sum(str(t.getIoType()) == 'OUTPUT' for t in net.getITerms()) == 1
    assert source.findMaster(row['requested_replacement']) is None
    added = 'nssoc_setup_isolation_buf_' + str(k)
    local = 'nssoc_setup_isolation_branch_' + str(k)
    assert added not in original and local not in original_nets
    pg = {}
    for kind in ('POWER', 'GROUND'):
        peers = [t for t in inst.getITerms() if str(t.getSigType()) == kind]
        assert len(peers) == 1 and peers[0].getNet()
        pg[kind] = peers[0].getNet().getName()
    bmaster = source.findMaster('sg13g2_buf_4')
    assert bmaster
    newpins = {'A': local, 'X': net.getName()}
    for p in bmaster.getMTerms():
        if str(p.getSigType()) in pg:
            newpins[p.getName()] = pg[str(p.getSigType())]
    assert len(newpins) == len(bmaster.getMTerms())
    expected_nets[net.getName()]['terminals'].remove((name, pin))
    expected_nets[net.getName()]['terminals'].append((added, 'X'))
    expected_nets[local] = dict(signal='SIGNAL', ndr=None, special=False,
                               terminals=[(name, pin), (added, 'A')], ports=[])
    for p, n in newpins.items():
        if p not in ('A','X'):
            expected_nets[n]['terminals'].append((added, p))
    expected_cells[name]['pins'][pin] = local
    plan.append(dict(index=row['index'], driver=name, pin=pin, original_net=net.getName(),
                     buffer=added, local_net=local, master='sg13g2_buf_4', pins=newpins))
for row in expected_nets.values():
    row['terminals'].sort()

mode = os.environ['NSSOC_ISOLATION_MODE']
db = load(PARENT if mode == 'prepare' else OUT / 'legalized.odb')
b = db.getChip().getBlock()
if mode == 'prepare':
    for i in b.getInsts():
        i.setPlacementStatus('FIRM')
    for row in plan:
        driver = b.findInst(row['driver'])
        pin = driver.findITerm(row['pin'])
        oldnet = pin.getNet()
        local = odb.dbNet.create(b, row['local_net'])
        local.setSigType('SIGNAL')
        added = odb.dbInst.create(b, db.findMaster(row['master']), row['buffer'])
        assert local and added
        box = driver.getBBox()
        added.setOrient('R0')
        added.setLocation(box.xMax(), box.yMin())
        added.setPlacementStatus('PLACED')
        pin.disconnect()
        pin.connect(local)
        for p, name in row['pins'].items():
            added.findITerm(p).connect(b.findNet(name))
        # The five old routes still terminate at the old driver pin; they
        # cannot be treated as valid after this topological change.
        assert oldnet.getWire() is not None
        odb.dbWire.destroy(oldnet.getWire())

def verify():
    assert nets(b) == expected_nets, 'Unexpected connectivity after buffer isolation'
    assert fixed(db) == original_fixed, 'PG geometry, NDR or boundary changed'
    actual = cells(b)
    assert set(actual) == set(original) | {p['buffer'] for p in plan}
    for name, expected in expected_cells.items():
        observed = dict(actual[name], status=expected['status'])
        assert observed == expected, ('Original cell geometry or pins changed', name)
    for row in plan:
        inst = b.findInst(row['buffer'])
        assert inst.getMaster().getName() == row['master']
        assert actual[row['buffer']]['pins'] == row['pins']
        assert b.findNet(row['local_net']).getWire() is None
        assert b.findNet(row['original_net']).getWire() is None
    assert sha(PARENT) == PARENT_SHA

verify()
if mode == 'prepare':
    odb.write_db(db, str(OUT / 'proposed.odb'))
else:
    assert mode == 'audit'
    for i in b.getInsts():
        if i.getName() in original:
            i.setPlacementStatus(original[i.getName()]['status'])
    verify()
    legal_cells = cells(b)
    for row in plan:
        driver_pin = b.findInst(row['driver']).findITerm(row['pin']).getBBox()
        buffer_pin = b.findInst(row['buffer']).findITerm('A').getBBox()
        distance = (abs(driver_pin.xMin()+driver_pin.xMax()-buffer_pin.xMin()-buffer_pin.xMax())
                  + abs(driver_pin.yMin()+driver_pin.yMax()-buffer_pin.yMin()-buffer_pin.yMax())) / 2
        row['input_manhattan_um'] = distance / db.getTech().getDbUnitsPerMicron()
        assert row['input_manhattan_um'] <= 100, ('Buffer not local to weak output', row)
        row['signature'] = legal_cells[row['buffer']]
    victim = b.findInst(plan[0]['buffer']).findITerm('A')
    net = victim.getNet()
    victim.disconnect()
    try:
        verify()
    except AssertionError as error:
        assert 'Unexpected connectivity' in str(error)
    else:
        raise AssertionError('Real disconnected buffer input escaped')
    victim.connect(net)
    verify()
    odb.write_db(db, str(OUT / 'unrouted.odb'))
    result = dict(status='PASS_FIVE_OUTPUT_BUFFERS_LEGAL_PLACEMENT_NOT_ROUTED_OR_TIMED',
        accepted=False, source_odb_sha256=PARENT_SHA, instances=114030, nets=114102,
        added_cells=5, all_original_geometry_unchanged=True,
        original_pg_ndr_boundary_unchanged=True, real_disconnection_control='REJECTED',
        plan=plan, route_validated=False, timing_validated=False,
        note='234 source only; independent of the still-running nine-size candidate. A future merge must revalidate its exact source, logic, placement, fresh route/RC and every timing endpoint.')
    (OUT / 'native-feasibility.json').write_text(json.dumps(result, indent=2)+'\n')
