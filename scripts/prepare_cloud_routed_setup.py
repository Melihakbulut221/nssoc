# SPDX-FileCopyrightText: 2026 Hasan Melih Akbulut
# SPDX-License-Identifier: Apache-2.0
"""OpenDB-only isolated four-cell setup ECO; never modifies the routed input."""
from pathlib import Path
import hashlib
import json
import os
import odb

SOURCE = Path(os.environ['NSSOC_ROUTED_ODB'])
OUT = Path(os.environ['NSSOC_SETUP_OUT'])
SIZES = {'rebuffer45563': ('sg13g2_buf_1', 'sg13g2_buf_8'),
         'place27346': ('sg13g2_buf_2', 'sg13g2_buf_8'),
         'place27039': ('sg13g2_buf_2', 'sg13g2_buf_8')}
DRIVER = '$abc$1702876$auto$blifparse.cc:397:parse_blif$1746178'
ADDED = 'nssoc_setup_nand4_buffer01'


def signature(instance):
    return dict(master=instance.getMaster().getName(), orient=str(instance.getOrient()),
                origin=list(instance.getOrigin()), location=list(instance.getLocation()),
                pins={t.getMTerm().getName(): t.getNet().getName() if t.getNet() else None
                      for t in instance.getITerms()})


def power(block):
    result = {}
    for net in block.getNets():
        if str(net.getSigType()) not in ('POWER', 'GROUND'):
            continue
        shapes = []
        for wire in net.getSWires():
            for box in wire.getWires():
                via = box.getTechVia() if box.isVia() else None
                blockvia = box.getBlockVia() if box.isVia() else None
                shapes.append(('VIA' if box.isVia() else box.getTechLayer().getName(),
                               via.getName() if via else None,
                               blockvia.getName() if blockvia else None,
                               box.xMin(), box.yMin(), box.xMax(), box.yMax()))
        result[net.getName()] = dict(count=len(shapes), sha256=hashlib.sha256(
            json.dumps(sorted(shapes)).encode()).hexdigest())
    return result


def clear_routes(block):
    for net in block.getNets():
        if str(net.getSigType()) in ('POWER', 'GROUND'):
            continue
        assert not net.getSWires()
        assert net.getRSegCount() == net.getCapNodeCount() == 0
        wire, global_wire = net.getWire(), net.getGlobalWire()
        if global_wire and (not wire or global_wire.getId() != wire.getId()):
            odb.dbWire.destroy(global_wire)
        if wire:
            odb.dbWire.destroy(wire)
        net.clearGuides()
        net.clearTracks()
        assert not net.getWire() and not net.getGlobalWire() and not net.getGuides() and not net.getTracks()


def prepare():
    record = dict(status='PREPARING', adopted=False, targets=SIZES, added=ADDED)
    for label in ('baseline', 'buffered'):
        db = odb.dbDatabase.create()
        odb.read_db(db, str(SOURCE))
        block = db.getChip().getBlock()
        original_power = power(block)
        removed = []
        for instance in list(block.getInsts()):
            if instance.getMaster().getName().startswith(('sg13g2_fill', 'sg13g2_decap')):
                removed.append(instance.getName())
                odb.dbInst.destroy(instance)
            else:
                instance.setPlacementStatus('FIRM')
                assert instance.isFixed()
        original = {i.getName(): signature(i) for i in block.getInsts()}
        if label == 'buffered':
            for name, (before, after) in SIZES.items():
                instance = block.findInst(name)
                assert instance and instance.getMaster().getName() == before
                instance.setPlacementStatus('PLACED')
                assert instance.swapMaster(db.findMaster(after))
            driver = block.findInst(DRIVER)
            assert driver and driver.getMaster().getName() == 'sg13g2_nand4_1'
            pin = driver.findITerm('Y')
            old_net = pin.getNet()
            local = odb.dbNet.create(block, 'nssoc_setup_nand4_local01')
            assert local
            instance = odb.dbInst.create(block, db.findMaster('sg13g2_buf_16'), ADDED)
            assert instance
            instance.setOrient(driver.getOrient())
            x, y = driver.getLocation()
            instance.setLocation(x + driver.getMaster().getWidth(), y)
            instance.setPlacementStatus('PLACED')
            pin.disconnect()
            pin.connect(local)
            instance.findITerm('A').connect(local)
            instance.findITerm('X').connect(old_net)
            for term in instance.getITerms():
                kind = str(term.getSigType())
                if kind in ('POWER', 'GROUND'):
                    peers = [t for t in driver.getITerms() if str(t.getSigType()) == kind]
                    assert len(peers) == 1 and peers[0].getNet()
                    term.connect(peers[0].getNet())
            for name, old in original.items():
                new = signature(block.findInst(name))
                expected = dict(old, pins=dict(old['pins']))
                if name in SIZES:
                    expected['master'] = SIZES[name][1]
                if name == DRIVER:
                    expected['pins']['Y'] = local.getName()
                assert new == expected, name
        clear_routes(block)
        assert power(block) == original_power
        odb.write_db(db, str(OUT / (label + '.odb')))
        (OUT / (label + '-preparation.json')).write_text(json.dumps(dict(
            status='PREPARED_REQUIRES_NATIVE_PLACEMENT_AND_PROOF', original=original,
            power=original_power, removed_fillers=removed), indent=2) + '\n')
        record[label] = dict(retained=len(original), removed_fillers=len(removed), power=original_power)
        odb.dbDatabase.destroy(db)
    record['status'] = 'PREPARED_FOUR_CELL_ECO_NO_ROUTING_OR_TIMING_ACCEPTANCE'
    (OUT / 'preparation.json').write_text(json.dumps(record, indent=2) + '\n')


def audit():
    before = json.loads((OUT / 'buffered-preparation.json').read_text())
    db = odb.dbDatabase.create()
    odb.read_db(db, str(OUT / 'buffered/placed.odb'))
    block = db.getChip().getBlock()
    assert len(block.getInsts()) == len(before['original']) + 1
    moved = []
    for name, old in before['original'].items():
        instance = block.findInst(name)
        assert instance
        current = signature(instance)
        expected = dict(old, pins=dict(old['pins']))
        if name in SIZES:
            assert current['master'] == SIZES[name][1] and current['pins'] == old['pins']
            moved.append(dict(name=name, before=old, after=current))
        else:
            if name == DRIVER:
                expected['pins']['Y'] = 'nssoc_setup_nand4_local01'
            assert current == expected, name
            assert instance.isFixed(), name
    assert power(block) == before['power']
    assert block.findInst(ADDED).getMaster().getName() == 'sg13g2_buf_16'
    for net in block.getNets():
        if str(net.getSigType()) not in ('POWER', 'GROUND'):
            assert not net.getWire() and not net.getGlobalWire() and not net.getGuides() and not net.getTracks()
    (OUT / 'geometry-audit.json').write_text(json.dumps(dict(
        status='PASS_ONLY_THREE_RESIZED_BUFFERS_AND_ONE_INSERTED_BUFFER',
        moved_or_resized=moved, retained=len(before['original']), added=ADDED,
        power_special_geometry_unchanged=True, stale_routes_empty=True,
        scope='Restricted geometry/connectivity audit; native placement and logic proof separate. Not routed signoff.'), indent=2) + '\n')


if os.environ.get('NSSOC_SETUP_MODE') == 'audit':
    audit()
else:
    prepare()
