#!/usr/bin/env python3
# SPDX-FileCopyrightText: 2026 Hasan Melih Akbulut
# SPDX-License-Identifier: Apache-2.0
"""Physically witnessed diagnostic boundary annotations, never conductor joins."""
import argparse
import hashlib
import io
import json
from pathlib import Path
import resource
import struct
import sys

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT/'scripts'))
from extract_gds_hierarchy import index_stream, records  # noqa: E402
from make_chip_io_floorplan import parse_lef, box_transform  # noqa: E402
from io_parent_path_probe import CHAIN, TOP, db_module, require  # noqa: E402
from repair_parent_resistor_markers import record, region  # noqa: E402

RAILS = ('iovdd', 'iovss', 'vdd', 'vss')
NET_LABELS = {(n, 25) for n in (8, 10, 30, 50, 67, 126, 134)}
SOURCE_GDS_SHA = 'd846215231733f66265b2cbfe3eb4859c001723d8b2819bd4a236b0f255ac895'
SOURCE_DB_SHA = 'a5600482612ff5139dc02fedd2014578662db969a24fef773323dd226e3c288d'
LEF_SHA = '8b3dc3960960c08e07a1cde3dd9cd0484f5b12df07c4628726fff551bb775c0c'


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def write(path, value):
    path.write_text(json.dumps(value, indent=2)+'\n')


def boundary_witness(database, lef):
    """Read completed native extraction; no new extraction or label-name unions."""
    db = db_module()
    require(sha(database) == SOURCE_DB_SHA and sha(lef) == LEF_SHA, 'Wrong native database/LEF source')
    lvs = db.LayoutVsSchematic(); lvs.read(str(database))
    require(str(lvs.layer_info(31)) == '126/25', 'Captured label-layer mapping differs')
    # The exact producer database and unchanged deck bind l31 to l20 (TopMetal1).
    # Layer names are database-local; never transfer these indexes to another run.
    macros = parse_lef(lef.read_text()); points = []; rail_ids = {}
    for item in CHAIN:
        for rail in RAILS:
            boxes = macros[item['master']]['pins'][rail]
            require(bool(boxes), 'Missing original LEF boundary')
            for box in boxes:
                placed = box_transform(box, item['rotation'], item['x_nm'], item['y_nm'])
                xy = [(placed[0]+placed[2])//2, (placed[1]+placed[3])//2]
                net = lvs.probe_net(lvs.layer_by_index(20), db.Point(*xy))
                require(net is not None, 'LEF boundary has no actual conductor')
                points.append(dict(instance=item['instance'], master=item['master'], rail=rail,
                    original_box_nm=box, placed_box_nm=placed, point_nm=xy, cluster=net.cluster_id, net=net.name))
                rail_ids.setdefault(rail, set()).add(net.cluster_id)
    require(len(points) == 53 and all(len(v) == 1 for v in rail_ids.values())
            and len(set.union(*rail_ids.values())) == 4, 'Four separate connected rail boundaries not proven')
    top = lvs.netlist().circuit_by_name(TOP); bodies = []
    for device in top.each_device():
        cls = device.device_class()
        if cls.name == 'sg13_hv_pmos': continue
        for terminal in cls.terminal_definitions():
            if terminal.name.casefold() in ('well', 'rppd_sub', 'b'):
                net = device.net_for_terminal(terminal.id())
                bodies.append(dict(model=cls.name, terminal=terminal.name, cluster=net.cluster_id, net=net.name))
    require(len(bodies) == 10 and len({r['cluster'] for r in bodies}) == 1, 'Common physical substrate not proven')
    substrate = bodies[0]['cluster']
    require(substrate not in set.union(*rail_ids.values()), 'Substrate shorted to a rail')
    # l1 is pwell_sub, the first registered layer of this exact captured deck.
    substrate_point = [1000, 834000]
    net = lvs.probe_net(lvs.layer_by_index(1), db.Point(*substrate_point))
    require(net is not None and net.cluster_id == substrate, 'Boundary substrate annotation misses physical body')
    labels = [dict(name=rail, layer=[126, 25], point_nm=next(p['point_nm'] for p in points if p['rail'] == rail)) for rail in RAILS]
    labels.append(dict(name='sub!', layer=[40, 25], point_nm=substrate_point))
    return dict(status='PASS_PHYSICAL_BOUNDARY_WITNESS', rail_points=points, substrate_terminals=bodies,
        rail_clusters={k:next(iter(v)) for k,v in rail_ids.items()}, substrate_cluster=substrate,
        labels=labels, source_database_sha256=SOURCE_DB_SHA, original_lef_sha256=LEF_SHA,
        no_virtual_connections=True, new_extraction=False)


def text_record(label):
    value = label['name'].encode('ascii'); value += b'\0'*(len(value)%2)
    return (record(12)+record(13, 2, struct.pack('>h', label['layer'][0]))
        +record(22, 2, struct.pack('>h', label['layer'][1]))
        +record(16, 3, struct.pack('>ii', *label['point_nm']))+record(25, 6, value)+record(17))


def annotate_bytes(raw, labels):
    original = index_stream(io.BytesIO(raw)); require(TOP in original['cells'], 'Missing exact diagnostic top')
    require([v['name'] for v in labels] == [*RAILS, 'sub!'], 'Wrong boundary names/order')
    require([v['layer'] for v in labels] == [[126, 25]]*4+[[40, 25]], 'Wrong boundary label layers')
    kept = []; removed = []; element = []; cell = None; current_kind = None
    for offset, kind, payload, data in records(io.BytesIO(raw)):
        if kind == 6: cell = payload.rstrip(b'\0').decode('ascii')
        if kind in (8, 9, 10, 11, 12, 45):
            require(not element, 'Nested GDS element'); current_kind = kind
        if current_kind is not None:
            element.append((offset, kind, payload, data))
            if kind != 17: continue
            drop = False
            if current_kind == 12:
                fields = {k:p for _,k,p,_ in element}
                pair = tuple(struct.unpack('>h', fields[k])[0] for k in (13, 22))
                drop = pair in NET_LABELS
                if drop:
                    removed.append(dict(cell=cell, layer=list(pair), text=fields[25].rstrip(b'\0').decode('ascii'),
                        offset=element[0][0], bytes=sum(len(v[3]) for v in element),
                        sha256=hashlib.sha256(b''.join(v[3] for v in element)).hexdigest()))
            if not drop: kept.extend(v[3] for v in element)
            current_kind = None; element = []
        else:
            if kind == 7 and cell == TOP: kept.append(b''.join(text_record(v) for v in labels))
            kept.append(data)
    require(not element and removed, 'Incomplete GDS or no conductive labels removed')
    changed = b''.join(kept); after = index_stream(io.BytesIO(changed))
    require(original['cells'].keys() == after['cells'].keys(), 'Cell catalog changed')
    # Reconstruction is exact: remove precisely inventoried old TEXT records,
    # then insert only the five new TEXT elements. Every other byte is retained.
    return changed, dict(removed_conductive_texts=removed, added_boundary_labels=labels,
        unchanged_non_text_bytes=True, recognition_text_layers_untouched=True)


def verify_annotations(db, before, after):
    require(before.dbu == after.dbu == .001, 'Database units changed')
    require({c.name for c in before.each_cell()} == {c.name for c in after.each_cell()}, 'Cell catalog changed')
    layers = {(i.layer, i.datatype) for layout in (before, after) for i in layout.layer_infos()}
    for c in before.each_cell():
        d = after.cell(c.name)
        def instances(cell):
            return sorted((i.cell.name, str(i.cplx_trans), str(i.a), str(i.b), i.na, i.nb) for i in cell.each_inst())
        require(instances(c) == instances(d), 'Instance transform changed')
        for pair in layers:
            require((region(db, before, c, pair)^region(db, after, d, pair)).is_empty(), 'Conductor/device polygon changed')
            if pair in NET_LABELS or (c.name == TOP and pair == (40, 25)): continue
            def texts(layout, cell):
                idx = layout.find_layer(*pair)
                return [] if idx is None else sorted(str(s.text) for s in cell.shapes(idx).each() if s.is_text())
            require(texts(before, c) == texts(after, d), 'Recognition or unrelated text changed')
    return dict(status='PASS_ALL_POLYGONS_INSTANCES_AND_NON_BOUNDARY_TEXTS_PRESERVED', cells=before.cells(), layer_pairs=len(layers))


def prepare(source, database, lef, output):
    db = db_module(); require(sha(source) == SOURCE_GDS_SHA, 'Wrong marker-only actual parent')
    output.mkdir(parents=True, exist_ok=False)
    witness = boundary_witness(database, lef); raw = source.read_bytes()
    changed, edits = annotate_bytes(raw, witness['labels'])
    target = output/'actual-adjacency.gds'; target.write_bytes(changed)
    before = db.Layout(); before.read(str(source)); after = db.Layout(); after.read(str(target))
    body_text_layer = before.find_layer(40, 25)
    require(body_text_layer is None or not any(s.is_text() for c in before.each_cell()
            for s in c.shapes(body_text_layer).each()), 'Unexpected pre-existing substrate annotations')
    preservation = verify_annotations(db, before, after)
    require(source.read_bytes() == raw, 'Original GDS changed')
    result = dict(status='PREPARED_DIAGNOSTIC_BOUNDARY_NOT_LVS_ACCEPTANCE', witness=witness, annotation_edits=edits,
        preservation=preservation, original_gds_sha256=SOURCE_GDS_SHA, wrapper_gds_sha256=sha(target),
        full_chip_changed=False, qualified_deck_acceptance=False, lvs_accepted=False, manufacturing_approval=False)
    write(output/'boundary.json', result)


def controls(output):
    """Generic resistor geometry tests label attachment and strict missing ports."""
    db = db_module(); output.mkdir(parents=True, exist_ok=False); rows = {}
    for case in ('connected', 'mislabeled', 'open_substrate', 'same_name_open', 'missing_substrate_label'):
        lvs = db.LayoutVsSchematic('CONTROL', .001)
        wires = db.Region(); contacts = db.Region(); metal = db.Region()
        body = db.Region(db.Box(-200, -100, 0, 800)); labels = db.Texts()
        body_labels = db.Texts([db.Text('sub!', db.Trans(-100, 10))])
        if case in ('open_substrate', 'same_name_open'):
            body = db.Region([db.Box(-200, i*200, 0, i*200+100) for i in range(4)])
        if case == 'same_name_open': body_labels = db.Texts([db.Text('sub!', db.Trans(-100, i*200+10)) for i in range(4)])
        if case == 'missing_substrate_label': body_labels = db.Texts()
        for i, rail in enumerate(RAILS):
            y = i*200; right = 1000+i*100
            wires.insert(db.Box(0, y, right, y+100)); contacts.insert(db.Box(-100, y, 0, y+100))
            contacts.insert(db.Box(right, y, right+100, y+100)); metal.insert(db.Box(right, y, right+100, y+100))
            labels.insert(db.Text('wrong' if case == 'mislabeled' and i == 0 else rail, db.Trans(right+50, y+50)))
        for name, layer in [('wire', wires), ('contact', contacts), ('metal', metal), ('body', body), ('labels', labels), ('body_labels', body_labels)]:
            lvs.register(layer, name)
        lvs.extract_devices(db.DeviceExtractorResistor('R', 1), {'R':wires, 'C':contacts})
        for layer in (contacts, metal, body): lvs.connect(layer)
        for a,b in [(contacts,metal), (contacts,body), (metal,labels), (body,body_labels)]: lvs.connect(a,b)
        lvs.extract_netlist()
        ref = db.Netlist(); cls = db.DeviceClassResistor(); cls.name = 'R'; ref.add(cls)
        top = db.Circuit(); top.name = 'CONTROL'; ref.add(top); nets = {}
        for name in (*RAILS, 'sub!'):
            nets[name] = top.create_net(name); pin = top.create_pin(name); top.connect_pin(pin.id(), nets[name])
        for i, rail in enumerate(RAILS):
            device = top.create_device(cls, 'R'+str(i)); device.connect_terminal('A', nets['sub!'])
            device.connect_terminal('B', nets[rail]); device.set_parameter('R', 10+i)
        lvs.reference = ref; compared = lvs.compare(db.NetlistComparer())
        strict = lvs.flag_missing_ports(lvs.netlist().circuit_by_name('CONTROL')) if compared else False
        require(strict == (case == 'connected'), 'Boundary negative control accepted: '+case)
        lvs.write(str(output/(case+'.lvsdb.gz')))
        rows[case] = dict(compare=compared, strict_ports=strict, expected=case == 'connected')
    # Exercise the actual GDS TEXT filter and round-trip, including protected
    # device-recognition text and an unchanged transformed child instance.
    layout = db.Layout(); layout.dbu = .001
    top = layout.create_cell(TOP); child = layout.create_cell('CONTROL_CHILD')
    child.shapes(layout.layer(1, 0)).insert(db.Box(0, 0, 100, 200))
    child.shapes(layout.layer(8, 25)).insert(db.Text('internal', db.Trans(10, 20)))
    child.shapes(layout.layer(63, 0)).insert(db.Text('ptap1', db.Trans(30, 40)))
    top.insert(db.CellInstArray(child.cell_index(), db.Trans(3, False, 500, 600)))
    original = output/'annotation-original.gds'; layout.write(str(original))
    annotation_labels = [dict(name=n, layer=[126,25], point_nm=[10+20*i,50]) for i,n in enumerate(RAILS)]
    annotation_labels.append(dict(name='sub!', layer=[40,25], point_nm=[50,100]))
    changed, edits = annotate_bytes(original.read_bytes(), annotation_labels)
    target = output/'annotation-wrapper.gds'; target.write_bytes(changed)
    restored = db.Layout(); restored.read(str(target))
    preservation = verify_annotations(db, layout, restored)
    require(len(edits['removed_conductive_texts']) == 1, 'Unexpected tiny annotation inventory')
    write(output/'result.json', dict(status='PASS_TINY_NATIVE_BOUNDARY_CONTROLS', cases=rows,
        annotation_roundtrip=preservation,
        scope='Generic resistor geometry; label attachment never joins disjoint bodies. Not IHP validation.'))


def main():
    resource.setrlimit(resource.RLIMIT_AS, (2*1024**3, 2*1024**3))
    parser = argparse.ArgumentParser(description=__doc__); sub = parser.add_subparsers(dest='mode', required=True)
    sub.add_parser('controls').add_argument('output', type=Path)
    prep = sub.add_parser('prepare')
    for n in ('source', 'database', 'lef', 'output'): prep.add_argument(n, type=Path)
    args = parser.parse_args()
    if args.mode == 'controls': controls(args.output)
    else: prepare(args.source, args.database, args.lef, args.output)


if __name__ == '__main__': main()
