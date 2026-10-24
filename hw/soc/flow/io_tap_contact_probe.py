#!/usr/bin/env python3
# SPDX-FileCopyrightText: 2026 Hasan Melih Akbulut
# SPDX-License-Identifier: Apache-2.0
"""Read-only native contact ownership and conditional perimeter lower bound."""
import argparse
import hashlib
import json
from pathlib import Path
import resource

TOP = 'ACTUAL_IO_ADJACENCY'
MASTER = 'sg13g2_IOPadVss'
STRIPE = [0, 156850, 80000, 157150]
TRANSFORM = [3, False, 0, 1076000]
CONTACT_COUNT = 234
CONTACT_BOXES_SHA = 'd3f7f37041aa752514664ec0224148d08a3f9e70c12c76f6846a3b4317478289'
EXCEPTIONS = {'EdgeSeal': [39, 0], 'SRAM': [25, 0], 'DigiBnd': [16, 0],
              'Activ-mask': [1, 20], 'NWell': [31, 0]}
CONTROL_CASES = ['connected', 'rotation', 'split', 'wrong_net', 'missing_contact',
                 'wrong_transform', 'exception', 'missing_enclosure', 'pruned_unrelated_contact',
                 'pruned_selected_contact', 'overlapping_projection']


def require(ok, message):
    if not ok:
        raise ValueError(message)


def write(path, value):
    path.write_text(json.dumps(value, indent=2)+'\n')


def digest(value):
    return hashlib.sha256(json.dumps(value, separators=(',', ':')).encode()).hexdigest()


def native_module():
    import klayout.db as db
    require(db.__version__ == '0.30.7', 'Expected pinned KLayout 0.30.7')
    return db


def projection_length(intervals):
    """Measure a union, including overlap/touch; disconnected intervals stay valid."""
    require(bool(intervals), 'Empty projection')
    total = 0; right = None
    for left, end in sorted(intervals):
        require(isinstance(left, int) and isinstance(end, int) and left < end,
                'Invalid integer projection interval')
        if right is None or left > right:
            total += end-left
        elif end > right:
            total += end-right
        right = end if right is None else max(right, end)
    return total


def box_list(box):
    return [box.left, box.bottom, box.right, box.top]


def region(db, layout, cell, pair):
    index = layout.find_layer(*pair)
    return db.Region() if index is None else db.Region(cell.begin_shapes_rec(index)).merged()


def same_net(a, b):
    return (a is not None and b is not None and a.cluster_id == b.cluster_id
            and a.circuit().name == b.circuit().name)


def net_info(net):
    return dict(name=net.name, cluster_id=net.cluster_id, circuit=net.circuit().name)


def owned_contact(db, native, contact_layer, tie_layer, body_layer, contact, expected_tie, expected_body):
    """Require full polygon ownership, not merely a center-point label match."""
    center = contact.bbox().center()
    layers = [layer if isinstance(layer, int) else native.layer_index(layer)
              for layer in (contact_layer, tie_layer, body_layer)]
    nets = [native.probe_net(native.layer_by_index(layer), center) for layer in layers]
    require(same_net(nets[0], expected_tie) and same_net(nets[1], expected_tie)
            and same_net(nets[2], expected_body) and not same_net(expected_tie, expected_body),
            'Contact/tie/body belongs to the wrong or absent physical net')
    rows = {}
    for name, layer, net in zip(('contact', 'recognized_tie', 'substrate'),
                                layers, nets):
        native_shapes = native.polygons_of_net(net, layer, True)
        require((contact-native_shapes).is_empty(), 'Contact split across physical ownership: '+name)
        rows[name] = net_info(net)
    return rows


def enclosure_gate(db, contact_box, recognized_tie, exceptions, enclosure_nm):
    expanded = db.Region(contact_box.enlarged(enclosure_nm))
    require((expanded-recognized_tie).is_empty(), 'Expanded contact not covered by recognized TIE')
    hits = {name: int((expanded & shape).area()) for name, shape in exceptions.items()}
    require(all(area == 0 for area in hits.values()), 'Unsupported DRC exception intersects contact enclosure')
    return dict(rule='Cnt.c', enclosure_nm=enclosure_nm, exception_overlap_area_nm2=hits,
                expanded_box_nm=box_list(contact_box.enlarged(enclosure_nm)),
                rectangular_enclosure_witness=True, full_drc_pass=False)


def read_masks(db, path):
    raw = json.loads(path.read_text())
    require(raw['status'] == 'DERIVED_CONTACT_MASKS_ONLY' and raw['dbu_um'] == .001
            and raw['top'] == TOP, 'Wrong derived mask scope/DBU')
    result = {}
    for name, row in raw['masks'].items():
        value = db.Region()
        for text in row['polygons']:
            value.insert(db.Polygon.from_s(text))
        value.merge()
        require(value.area() == row['area_nm2'] and value.perimeter() == row['perimeter_nm'],
                'Mask export roundtrip differs: '+name)
        result[name] = value
    require(set(result) == {'ptap1_tie', 'ptap1_sub', 'pwell', 'pactiv', 'ptap1_mk',
                            'ptap1_exc', 'activ_drw', 'psd_drw', 'nwell_drw'}, 'Missing exact masks')
    return result


def geometry_layer(native, shape):
    """Identify a captured layer by complete geometric equality, never a guessed index."""
    candidates = []
    for index in native.layer_indexes():
        try:
            found = native.layer_by_index(index)
            if found.area() == shape.area() and (found ^ shape).is_empty():
                candidates.append(index)
        except TypeError:  # Captured TEXT layers are not polygon candidates.
            continue
    require(len(candidates) == 1, 'Captured physical layer identification is ambiguous or absent')
    return candidates[0]


def contact_layer(native, source, selected):
    """Allow captured pruning only outside the fully preserved selected contacts."""
    candidates = []
    for index in native.layer_indexes():
        try:
            found = native.layer_by_index(index)
            if (not found.is_empty() and found.area() <= source.area()
                    and (selected-found).is_empty() and (found-source).is_empty()):
                candidates.append(index)
        except TypeError:
            continue
    require(len(candidates) == 1, 'Captured contact-layer ownership is ambiguous or absent')
    index = candidates[0]
    absent = source-native.layer_by_index(index)
    require((absent & selected).is_empty(), 'Captured contact pruning touches a selected contact')
    return index, dict(source_area_nm2=source.area(), captured_area_nm2=native.layer_by_index(index).area(),
        source_absent_from_capture_area_nm2=absent.area(), selected_missing_area_nm2=0,
        scope='Global source contacts may be absent from the saved extraction; every selected contact must be present unchanged.')


def terminal_layer(native, device, name):
    net = device.net_for_terminal(name)
    matches = [ref for ref in net.each_terminal()
               if ref.device().id() == device.id() and ref.terminal_def().name == name]
    require(len(matches) == 1, 'Ambiguous native terminal reference')
    shapes = native.shapes_of_terminal(matches[0])
    require(len(shapes) == 1, 'Ambiguous native terminal geometry layer')
    index, shape = next(iter(shapes.items()))
    return index, shape, net


def inspect(output):
    db = native_module()
    result = dict(status='FAILED_CONTACT_ATTRIBUTION', interpreted_bound=None,
                  lvs_accepted=False, qualified_deck_acceptance=False, full_chip_changed=False,
                  manufacturing_approval=False, repeated_lvs_comparison=False)
    try:
        root = output/'inputs'
        layout = db.Layout(); layout.read(str(root/'actual-adjacency.gds'))
        require(layout.dbu == .001, 'GDS DBU differs')
        top = layout.cell(TOP); cell = layout.cell(MASTER)
        require(top is not None and cell is not None, 'Missing exact cell hierarchy')
        instances = [i for i in top.each_inst() if i.cell.name == MASTER]
        require(len(instances) == 1, 'Vss direct-parent instance is ambiguous')
        trans = db.Trans(*TRANSFORM)
        require(instances[0].cplx_trans == db.ICplxTrans(trans)
                and instances[0].na == 0 and instances[0].nb == 0, 'Actual Vss parent transform differs')
        stripe = db.Region(db.Box(*STRIPE)).transformed(trans)
        contacts = []
        for shape in cell.shapes(layout.layer(6, 0)).each():
            if shape.is_text():
                continue
            polygon = shape.polygon
            part = db.Region(polygon)
            if not (part & db.Region(db.Box(*STRIPE))).is_empty():
                require((part-db.Region(db.Box(*STRIPE))).is_empty() and polygon.is_box(),
                        'Non-rectangular or boundary-crossing direct contact')
                box = polygon.bbox()
                require(box.width() == box.height() == 160, 'Contact is not a 160 nm square')
                contacts.append(box_list(box))
        contacts.sort()
        require(len(contacts) == CONTACT_COUNT and len({tuple(b) for b in contacts}) == CONTACT_COUNT
                and digest(contacts) == CONTACT_BOXES_SHA, 'Direct contact census differs from pinned source')
        native = db.LayoutVsSchematic(); native.read(str(root/'flat.lvsdb.gz'))
        circuit = native.netlist().circuit_by_name(TOP)
        require(circuit is not None and len(list(circuit.each_device())) == 18, 'Native flat circuit differs')
        devices = [d for d in circuit.each_device() if d.device_class().name == 'ptap1'
                   and d.net_for_terminal('TIE').name == 'VSS']
        require(len(devices) == 1, 'Native VSS tap not unique')
        tap = devices[0]
        tie_index, terminal_stripe, tie_net = terminal_layer(native, tap, 'TIE')
        sub_index, _, body_net = terminal_layer(native, tap, 'WELL')
        # Parallel tap combination keeps one representative terminal abstract,
        # which need not be this Vss instance. Bind its layer, then use the full
        # physically connected TIE region below for actual parent attribution.
        require(body_net.name == 'SUB!' and not terminal_stripe.is_empty(),
                'Native tap terminal/body is absent')
        masks = read_masks(db, output/'masks.json')
        require((native.layer_by_index(tie_index)^masks['ptap1_tie']).is_empty()
                and (native.layer_by_index(sub_index)^masks['ptap1_sub']).is_empty(),
                'Original-deck masks differ from captured native extraction')
        contact_region = region(db, layout, top, (6, 0))
        selected_contacts = db.Region()
        for local in contacts:
            selected_contacts.insert(db.Box(*local).transformed(trans))
        contact_index, contact_capture = contact_layer(native, contact_region, selected_contacts)
        body_index = geometry_layer(native, masks['pwell'])
        tie_shapes = native.polygons_of_net(tie_net, tie_index, True)
        require((stripe-tie_shapes).is_empty(), 'Transformed Vss stripe not covered by native VSS tap')
        area, perimeter = tap.parameter('A'), tap.parameter('P')
        require(abs(tie_shapes.area()/1e6-area) < 1e-8
                and abs(tie_shapes.perimeter()/1000-perimeter) < 1e-8,
                'Combined tap mask does not reproduce captured native A/P')
        required = ['pactiv', 'ptap1_mk', 'activ_drw', 'psd_drw']
        for name in required:
            require((stripe-masks[name]).is_empty(), 'Stripe recognition coverage missing: '+name)
        require((stripe & masks['ptap1_exc']).is_empty(), 'Stripe intersects tap exclusion')
        exceptions = {name: region(db, layout, top, pair) for name, pair in EXCEPTIONS.items()}
        rule = json.loads((output/'drc-rule-contract.json').read_text())
        require(rule['minimum_enclosure_nm'] == 70 and rule['contact_width_nm'] == 160,
                'Exact contact DRC constants differ')
        rows = []
        for number, local in enumerate(contacts):
            box = db.Box(*local).transformed(trans); contact = db.Region(box)
            membership = owned_contact(db, native, contact_index, tie_index, body_index,
                                       contact, tie_net, body_net)
            drc = enclosure_gate(db, box, tie_shapes, exceptions, 70)
            rows.append(dict(index=number, local_box_nm=local, parent_box_nm=box_list(box),
                transform=TRANSFORM, physical_membership=membership,
                tap_device_id=tap.id(), tap_terminal='TIE', well_terminal='WELL', drc= drc))
        write(output/'contacts.json', rows)
        reference = native.reference.circuit_by_name(TOP)
        refs = [d for d in reference.each_device() if d.device_class().name.lower() == 'ptap1'
                and d.net_for_terminal('TIE').name == 'VSS']
        require(len(refs) == 1, 'Reference VSS tap not unique')
        reference_p = refs[0].parameter('P')
        # Rotation preserves perimeter. Project the expanded local boxes onto
        # local x, equivalent to global y after the witnessed 270 degree rotation.
        bare = projection_length([(b[0], b[2]) for b in contacts])
        expanded = projection_length([(b[0]-70, b[2]+70) for b in contacts])
        require(bare == 37440 and expanded == 70200, 'Projection census changed')
        result.update(status='PASS_CONTACT_ATTRIBUTION_DIAGNOSTIC_ONLY', contact_count=len(rows),
            direct_contact_boxes_sha256=digest(contacts), native_klayout_version=db.__version__,
            native_layers=dict(contact=contact_index, tie=tie_index, well=sub_index, pwell=body_index),
            source_to_captured_contact_geometry=contact_capture,
            native_tap=dict(id=tap.id(), tie=net_info(tie_net), well=net_info(body_net),
                            area_um2=area, perimeter_um=perimeter,
                            representative_terminal_bbox_nm=box_list(terminal_stripe.bbox()),
                            representative_is_source_stripe=(terminal_stripe ^ stripe).is_empty()),
            mask_to_extraction_xor_area_nm2=dict(tie=0, well=0),
            parent_transform=TRANSFORM, stripe_area_um2=stripe.area()/1e6,
            stripe_perimeter_um=stripe.perimeter()/1000,
            interpreted_bound=dict(bare_contact_projection_nm=bare,
                enclosure_projection_nm=expanded, conservative_perimeter_lower_bound_um=2*expanded/1000,
                reference_combined_vss_perimeter_um=reference_p,
                literal_perimeter_contract_incompatible=2*expanded/1000 > reference_p,
                proof='For any enclosing planar tap region, perimeter is at least twice the measure of its x projection. Use the union of contact projection intervals; rotation preserves perimeter.',
                conditions='All 234 contacts keep their present VSS/SUB! ownership, Cnt.c branch and recognized tap/enclosure role. No contact deletion, net reassignment or recognition reclassification.',
                limitation='A rectangular 70 nm enclosure is a conservative current-geometry witness, not a full Euclidean DRC verdict. The bound concerns literal extracted perimeter only.',
                reference_caveat='The isolated A=23.523 um^2/P=19.4 um resembles a 4.85 um equivalent square. No claim that reference P is an authoritative physical-shape target or that the tap is electrically invalid. A qualified consistent extraction/model contract is still required.'))
    except BaseException as exc:
        result['error'] = str(exc)
        raise
    finally:
        write(output/'analysis.json', result)
    return result


def controls(path):
    db = native_module(); cases = {}
    for case in CONTROL_CASES[:8]:
        layout = db.Layout(); layout.dbu = .001
        top = layout.create_cell('CONTROL'); child = layout.create_cell('CHILD')
        idx = layout.layer(6, 0)
        for x in (0, 400):
            child.shapes(idx).insert(db.Box(x, 0, x+160, 160))
        rotation = db.Trans(3, False, 1000, 2000) if case in ('rotation', 'wrong_transform') else db.Trans()
        top.insert(db.CellInstArray(child.cell_index(), rotation))
        contacts = region(db, layout, top, (6, 0))
        tie = db.Region(db.Box(-70, -70, 630, 230)).transformed(rotation)
        body = db.Region(db.Box(-100, -100, 700, 300)).transformed(rotation)
        if case == 'split':
            tie -= db.Region(db.Box(250, -70, 350, 230)).transformed(rotation)
        if case == 'missing_contact':
            contacts -= db.Region(db.Box(400, 0, 560, 160)).transformed(rotation)
        native = db.LayoutToNetlist('CONTROL', .001)
        for name, shape in [('contact', contacts), ('tie', tie), ('body', body)]:
            native.register(shape, name); native.connect(shape)
        native.connect(contacts, tie); native.extract_netlist()
        expected_tie = native.probe_net(tie, rotation * db.Point(80, 80))
        expected_body = native.probe_net(body, rotation * db.Point(80, 80))
        if case == 'wrong_net':
            expected_tie = expected_body
        probe_transform = db.Trans() if case == 'wrong_transform' else rotation
        failed = False
        try:
            for x in (0, 400):
                box = db.Box(x, 0, x+160, 160).transformed(probe_transform)
                owned_contact(db, native, contacts, tie, body, db.Region(box), expected_tie, expected_body)
                exceptions = {'test_exception': db.Region(box) if case == 'exception' else db.Region()}
                enclosure_gate(db, box, tie if case != 'missing_enclosure' else contacts, exceptions, 70)
        except ValueError:
            failed = True
        expected = case in ('connected', 'rotation')
        require((not failed) == expected, 'Native contact control differs: '+case)
        cases[case] = dict(expected_pass=expected, actual_pass=not failed)
    # Saved extraction can omit unrelated contacts. Prove the narrow subset
    # rule accepts only that case and still rejects a lost selected contact.
    source = db.Region([db.Box(0, 0, 160, 160), db.Box(400, 0, 560, 160)])
    selected = db.Region(db.Box(0, 0, 160, 160))
    for case, captured in [('pruned_unrelated_contact', selected),
                           ('pruned_selected_contact', source-selected)]:
        extraction = db.LayoutToNetlist('CONTROL', .001)
        extraction.register(captured, 'contact'); extraction.connect(captured); extraction.extract_netlist()
        failed = False
        try:
            contact_layer(extraction, source, selected)
        except ValueError:
            failed = True
        expected = case == 'pruned_unrelated_contact'
        require((not failed) == expected, 'Captured-contact pruning control differs: '+case)
        cases[case] = dict(expected_pass=expected, actual_pass=not failed)
    require(projection_length([(0, 160), (100, 260), (400, 560)]) == 420,
            'Overlapping contact projections double-counted')
    cases['overlapping_projection'] = dict(expected_length_nm=420, actual_length_nm=420)
    write(path, dict(status='PASS_NATIVE_CONTACT_CONTROLS', klayout_version=db.__version__, cases=cases,
                     actual_input_processed=False, lvs_acceptance=False))


def main():
    resource.setrlimit(resource.RLIMIT_AS, (2*1024**3,)*2)
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('action', choices=('controls', 'inspect'))
    parser.add_argument('path', type=Path)
    args = parser.parse_args()
    if args.action == 'controls':
        controls(args.path)
    else:
        inspect(args.path)


if __name__ == '__main__':
    main()
