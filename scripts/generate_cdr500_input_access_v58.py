#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0
"""Source-only candidate: add real, native-owned C/D input-access metal and vias.

This script is not an acceptance gate. A reviewed cloud controller must supply
the exact cleaned500 layout/LVS/wire database and pinned PDK, then require fresh
560-rule DRC, unsimplified500-device LVS, strict planes, MIM-aware two-order RC,
and unchanged loaded electrical gates. No transient, device or bias edits here.
"""
import argparse, copy, hashlib, json, re, sys
from pathlib import Path
from collections import Counter
import pya

TOP = 'nssoc_cdr_pd500_active_input_v57'
CANDIDATE = 'nssoc_cdr_pd500_input_access_v58'
GDS_SHA = 'e6ab61471595cd3635c8e2ef3922a09d6b128db0a5338fd6106f3a8e4aefc2f3'
DIAG_SHA = 'dafde770d5ca0f625f8d5116e50b896e9531fdcee525daa4e2398062d6910a01'
METALS = (8, 10, 30, 50, 67, 126, 134)
VIAS = (19, 29, 49, 66, 125, 133)
ALLOWED = set(METALS + VIAS)
CLEARANCE = {m: 2000 if m in (126, 134) else 500 for m in ALLOWED}
CLEARANCE.update({m: 300 for m in VIAS})
EXPECTED_IDS = {59: (69, 187), 60: (70, 188), 111: (121, 225), 112: (124, 226)}

def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()

def require(condition, message):
    if not condition:
        raise ValueError(message)

def box_coordinates(text):
    nums = list(map(int, re.findall(r'-?\d+', text)))
    require(len(nums) == 4, 'Expected exact native via bounding box')
    return nums

def via_center(path, a, b, layer):
    links = [v for v in path['via_links'] if set(v['nodes']) == {a, b}]
    require(len(links) == 1 and links[0]['cuts'], 'Missing original via attachment')
    cuts = links[0]['cuts']
    require(all(v['via_layer'] == layer for v in cuts), 'Wrong original via layer')
    centers = []
    for cut in cuts:
        x1, y1, x2, y2 = box_coordinates(cut['bbox_dbu'])
        require((x1+x2) % 2 == (y1+y2) % 2 == 0, 'Off-grid original via center')
        centers.append(((x1+x2)//2, (y1+y2)//2))
    require(all(sum(p[k] for p in centers) % len(centers) == 0 for k in (0, 1)), 'Fractional via centroid')
    p = tuple(sum(v[k] for v in centers)//len(centers) for k in (0, 1))
    require(all(v % 5 == 0 for v in p), 'Off 5nm attachment grid')
    return p

def build_plan(report):
    require(report['status'] == 'PASS_EXISTING_CDR_INPUT_R_GRAPH_AND_NATIVE_OWNED_PATH_DIAGNOSIS_NOT_CIRCUIT_ACCEPTANCE', 'Unqualified diagnosis')
    require(report['all24550_raw_and_composed_resistor_edges_verified'] and report['sources_unchanged'], 'Raw-source proof absent')
    plans = []
    for g in report['native_geometry']['groups']:
        did = g['role_binding']['gain_native_id']
        require(did in EXPECTED_IDS, 'Unexpected gain device')
        require((g['role_binding']['driver']['native_id'], g['role_binding']['termination']['native_id']) == EXPECTED_IDS[did], 'Native endpoint identity changed')
        p = next(p for p in g['paths'] if p['roles'] == ['driver', 'termination'])
        pieces = p['metal_pieces']
        require([x['metal'] for x in pieces] == [10, 30, 50, 67, 50, 30, 10, 8], 'Upstream owned path differs')
        columns = []
        for role, index, neighbor in [('driver', 2, 1), ('termination', 4, 5)]:
            col = pieces[index]
            require(any('pd_child_rc_retime@' in q['owner'] for q in col['contributors']), 'M4 column lacks original retime ownership')
            low = via_center(p, col['node'], pieces[neighbor]['node'], 49)
            high = via_center(p, col['node'], pieces[3]['node'], 66)
            require(low[0] == high[0] and high[1] > low[1]+100000, 'Wrong original vertical M4 column')
            columns.append(dict(role=role, low_dbu=low, high_dbu=high, original_column=col))
        require(columns[0]['high_dbu'][1] == columns[1]['high_dbu'][1], 'Different original M5 buses')
        cross = next(p for p in g['paths'] if p['roles'] == ['driver', 'gain'])
        metal = cross['metal_pieces']
        # The original parent top-metal endpoint is the first TM1 piece after
        # the upstream M5 bus. Its existing TM2 attachment remains untouched.
        require([v['metal'] for v in metal[:6]] == [10, 30, 50, 67, 126, 134], 'Parent boundary path changed')
        boundary = via_center(cross, metal[3]['node'], metal[4]['node'], 125)
        require(boundary[1] == columns[0]['high_dbu'][1], 'Parent and child buses differ')
        tail = metal[-4:]
        require([v['metal'] for v in tail] == [50, 30, 10, 8], 'Sampler base path differs')
        require(all(any('pd_child_sampler_cd@' in q['owner'] for q in v['contributors']) for v in tail), 'Sampler base is not child-owned')
        base_pin = via_center(cross, tail[2]['node'], tail[3]['node'], 19)
        base_lane = via_center(cross, tail[0]['node'], tail[1]['node'], 49)
        require(base_pin[1] == base_lane[1] and base_pin[0] > base_lane[0], 'Sampler base escape changed')
        require(abs(base_pin[0]-g['anchors']['gain']['point_dbu'][0]) <= 5 and abs(base_pin[1]-g['anchors']['gain']['point_dbu'][1]) == 40, 'Native base pin offset changed')
        plans.append(dict(gain_native_id=did, native_cluster=g['native_cluster'],
                          wire_component=g['wire_component'], anchors=g['anchors'],
                          columns=columns, bus_boundary_dbu=boundary,
                          base_pin_dbu=base_pin, base_lane_dbu=base_lane))
    require(set(p['gain_native_id'] for p in plans) == set(EXPECTED_IDS) and len(plans) == 4, 'Incomplete C/D plan')
    return plans

def main():
    p = argparse.ArgumentParser(description=__doc__)
    for name in ('physical', 'diagnosis', 'pdk', 'out'):
        p.add_argument('--'+name, type=Path, required=True)
    args = p.parse_args()
    require(not args.out.exists(), 'Output must be fresh')
    require(sha(args.diagnosis) == DIAG_SHA, 'Exact passed diagnostic summary required')
    report = json.loads(args.diagnosis.read_text())
    plans = build_plan(report)
    physical = args.physical
    gds = physical/'parent/layout'/('nssoc_cdr_pd500_active_input_v57.gds')
    lvs_path = physical/'parent/physical/lvs_flat/result.lvsdb'
    graph_path = physical/'wire/native05/result.json'
    wire_path = physical/'wire/native05/wires.l2n'
    require(sha(gds) == GDS_SHA, 'Exact cleaned GDS required')
    protected = {str(q): sha(q) for q in (gds, lvs_path, graph_path, wire_path, args.diagnosis, Path(__file__))}
    source = args.pdk/'libs.tech/klayout/python'
    pdk_files = [*source.rglob('*.py'), *source.rglob('*.json')]
    require(pdk_files, 'Missing native PDK source')
    protected.update({str(q): sha(q) for q in pdk_files})
    sys.dont_write_bytecode = True
    sys.path[:0] = [str(source), str(source/'pycell4klayout-api/source/python')]
    import sg13g2_pycell_lib  # noqa: F401
    L = pya.Layout()
    L.read(str(gds))
    T = L.cell(TOP)
    require(T is not None and L.dbu == .001, 'Native layout identity/grid changed')
    original_box = T.bbox()
    original_top_name = T.name
    graph = json.loads(graph_path.read_text())
    native = pya.LayoutVsSchematic()
    native.read(str(lvs_path))
    wire = pya.LayoutToNetlist()
    wire.read(str(wire_path))
    require(sum(1 for _ in native.netlist().circuit_by_name(TOP).each_device()) == 500, 'Original native device census differs')

    def cell_snapshot(layout, cell):
        geometry = {}
        text = {}
        for li in layout.layer_indexes():
            info = layout.get_info(li)
            key = (info.layer, info.datatype)
            region = pya.Region(cell.shapes(li)).merged()
            if not region.is_empty():
                geometry[key] = region
            labels = sorted(str(s.text) for s in cell.shapes(li).each() if s.is_text())
            if labels:
                text[key] = labels
        inst = sorted((i.cell.name, str(i.dcplx_trans), i.na, i.nb, str(i.a), str(i.b)) for i in cell.each_inst())
        return geometry, text, inst

    old_cells = {c.cell_index(): cell_snapshot(L, c) for c in L.each_cell()}
    old_names = {c.cell_index(): c.name for c in L.each_cell()}
    all_before = {}
    for li in L.layer_indexes():
        info = L.get_info(li)
        all_before[info.layer, info.datatype] = pya.Region(T.begin_shapes_rec(li)).merged()
    total = {m: all_before.get((m, 0), pya.Region()) for m in ALLOWED}
    additions = {m: pya.Region() for m in ALLOWED}
    addition_owner = {m: [] for m in ALLOWED}
    route_records = []
    controls = []
    diagnostic_active = False

    def probe(anchor):
        point = pya.Point(*anchor['point_dbu'])
        n = native.probe_net(native.layer_by_index(graph['native_layer_mapping'][str(anchor['metal'])]), point)
        w = wire.probe_net(wire.layer_by_name('gds_'+str(anchor['metal'])), point)
        require(n is not None and n.cluster_id == anchor['native_cluster'], 'Wrong native owner')
        require(w is not None and w.cluster_id == anchor['wire_component'], 'Wrong wire owner')
        return w

    own = {}
    for plan in plans:
        nets = [probe(a) for a in plan['anchors'].values()]
        require(len({n.cluster_id for n in nets}) == 1, 'Endpoint conductor identity changed')
        own[plan['gain_native_id']] = {m: wire.shapes_of_net(nets[0], wire.layer_by_name('gds_'+str(m)), True).flatten().merged() for m in ALLOWED}
        for m in ALLOWED:
            require((own[plan['gain_native_id']][m]-total[m]).is_empty(), 'Wire model not contained in actual cleaned drawings')

    def clear(region, layer, plan):
        require(layer in ALLOWED and not region.is_empty(), 'Forbidden/nonmaterial addition')
        foreign = total[layer]-own[plan['gain_native_id']][layer]
        for did, previous in addition_owner[layer]:
            if did != plan['gain_native_id']:
                foreign += previous
        collision = (region.sized(CLEARANCE[layer]) & foreign).merged()
        if not collision.is_empty() and diagnostic_active:
            native_owners = []
            for net in wire.netlist().top_circuit().each_net():
                if net.cluster_id == plan['wire_component']:
                    continue
                pieces = wire.shapes_of_net(net, wire.layer_by_name('gds_'+str(layer)), True).flatten().merged()
                clipped = (pieces & region.sized(CLEARANCE[layer])).merged()
                if clipped.is_empty():
                    continue
                record = next((q for q in graph['wire_components'] if q['component'] == net.cluster_id), None)
                require(record is not None, 'Collision wire owner absent from original graph')
                native_owners.append(dict(wire_component=net.cluster_id, native_cluster=record['native_cluster'],
                    native_name=record['native_name'], clipped_polygons_dbu=[str(q) for q in clipped.each()]))
            drawing_owners = []
            root_part = (pya.Region(T.shapes(L.layer(layer, 0))) & collision).merged()
            if not root_part.is_empty():
                drawing_owners.append(dict(owner='root_direct', clipped_polygons_dbu=[str(q) for q in root_part.each()]))
            for instance in T.each_inst():
                part = (pya.Region(instance.cell.begin_shapes_rec(L.layer(layer, 0))).transformed(instance.cplx_trans) & collision).merged()
                if not part.is_empty():
                    drawing_owners.append(dict(owner=instance.cell.name+'@'+str(instance.dcplx_trans),
                                              clipped_polygons_dbu=[str(q) for q in part.each()]))
            report = dict(status='REJECTED_UNCHANGED_FOREIGN_MATERIAL_PLANNING_GUARD',
                gain_native_id=plan['gain_native_id'], requested_native_cluster=plan['native_cluster'],
                gds_layer=layer, planning_clearance_dbu=CLEARANCE[layer],
                candidate_polygons_dbu=[str(q) for q in region.each()],
                collision_polygons_dbu=[str(q) for q in collision.each()],
                actual_overlap_polygons_dbu=[str(q) for q in (region & foreign).merged().each()],
                native_foreign_owners=native_owners, actual_drawing_owners=drawing_owners,
                geometry_accepted=False, guard_waived=False)
            (args.out.parent/'access-collision.json').write_text(json.dumps(report, indent=2)+'\n')
            print(json.dumps(report), flush=True)
        require(collision.is_empty(), 'Foreign material or planning clearance collision')
        # New metal must not contact an old foreign adjacent-layer via.
        if layer in METALS:
            idx = METALS.index(layer)
            adjacent = []
            if idx > 0:
                adjacent.append(VIAS[idx-1])
            if idx < len(VIAS):
                adjacent.append(VIAS[idx])
            for via in adjacent:
                foreign_via = total[via]-own[plan['gain_native_id']][via]
                require((region & foreign_via).is_empty(), 'Added metal captures a foreign original via')

    def landing(layer, point, plan):
        x, y = point
        witness = pya.Region(pya.Box(x-5, y-5, x+5, y+5))
        require(not (witness & own[plan['gain_native_id']][layer]).is_empty(), 'Via landing has no original owned conductor')
        require((witness & (total[layer]-own[plan['gain_native_id']][layer])).is_empty(), 'Via landing has foreign original conductor')

    def add_region(layer, region, plan, purpose):
        clear(region, layer, plan)
        additions[layer] += region
        addition_owner[layer].append((plan['gain_native_id'], region.dup()))
        T.shapes(L.layer(layer, 0)).insert(region)
        route_records.append(dict(gain_native_id=plan['gain_native_id'], layer=layer, purpose=purpose, polygons_dbu=[str(q) for q in region.each()]))

    def add_line(layer, a, b, width, plan, purpose):
        require(a[0] == b[0] or a[1] == b[1], 'Only witnessed Manhattan route allowed')
        require(all(v % 5 == 0 for v in (*a, *b, width)) and width % 2 == 0, 'Off-grid candidate route')
        h = width//2
        box = pya.Box(min(a[0], b[0])-h, min(a[1], b[1])-h, max(a[0], b[0])+h, max(a[1], b[1])+h)
        add_region(layer, pya.Region(box), plan, purpose)

    def via(bottom_name, top_name, point, plan, purpose, columns=8, upper=False):
        layer_name = {'Metal1': 8, 'Metal3': 30, 'Metal4': 50, 'Metal5': 67, 'TopMetal1': 126, 'TopMetal2': 134}
        landing(layer_name[bottom_name], point, plan)
        parameters = dict(b_layer=bottom_name, t_layer=top_name, vn_columns=columns, vn_rows=1)
        if upper:
            parameters.update(vt1_columns=2, vt1_rows=1, vt2_columns=1, vt2_rows=1)
        cell = L.create_cell('via_stack', 'SG13_dev', parameters)
        require(cell is not None and not cell.is_empty(), 'Native via PCell failed')
        center = cell.bbox().center()
        tr = pya.Trans(point[0]-center.x, point[1]-center.y)
        require(tr.disp.x % 5 == tr.disp.y % 5 == 0, 'Off-grid native via placement')
        rendered = {}
        for li in L.layer_indexes():
            info = L.get_info(li)
            iterator = cell.begin_shapes_rec(li)
            while not iterator.at_end():
                require(not iterator.shape().is_text(), 'Native via introduces labels')
                iterator.next()
            reg = pya.Region(cell.begin_shapes_rec(li)).transformed(tr).merged()
            if reg.is_empty():
                continue
            require(info.datatype == 0 and info.layer in ALLOWED, 'Native via introduces a nonmetal/device layer')
            clear(reg, info.layer, plan)
            if info.layer in VIAS:
                for old_cut in own[plan['gain_native_id']][info.layer].interacting(reg).each():
                    require((pya.Region(old_cut)-reg).is_empty(), 'New native cut partially overlaps an original cut')
            rendered[info.layer] = reg
        require(layer_name[bottom_name] in rendered and layer_name[top_name] in rendered, 'Native via endpoint missing')
        require(not (rendered[layer_name[bottom_name]] & own[plan['gain_native_id']][layer_name[bottom_name]]).is_empty(), 'Rendered bottom landing misses original owned metal')
        for m, reg in rendered.items():
            additions[m] += reg
            addition_owner[m].append((plan['gain_native_id'], reg.dup()))
        T.insert(pya.CellInstArray(cell.cell_index(), tr))
        route_records.append(dict(gain_native_id=plan['gain_native_id'], purpose=purpose, pcell=cell.name, parameters=parameters, point_dbu=point, transform=str(tr), actual_layers={str(m): [str(q) for q in reg.each()] for m, reg in rendered.items()}))

    for label, corrupt in [('changed_endpoint_identity', lambda x: x['native_geometry']['groups'][0]['role_binding']['driver'].update(native_id=-1)), ('changed_owned_path_layer', lambda x: x['native_geometry']['groups'][0]['paths'][1]['metal_pieces'][2].update(metal=8))]:
        bad = copy.deepcopy(report)
        corrupt(bad)
        try:
            build_plan(bad)
        except ValueError:
            controls.append(label)
        else:
            raise AssertionError('Accepted plan corruption '+label)
    first, second = plans[:2]
    for name, action in [
        ('wrong_native_owner', lambda: probe(dict(first['anchors']['driver'], native_cluster=-1))),
        ('wrong_wire_owner', lambda: probe(dict(first['anchors']['driver'], wire_component=-1))),
        ('foreign_native_terminal', lambda: probe(dict(first['anchors']['driver'], point_dbu=second['anchors']['driver']['point_dbu']))),
        ('missing_original_landing', lambda: landing(50, (-10000, -10000), first)),
        ('forbidden_device_layer', lambda: clear(pya.Region(pya.Box(0, 0, 100, 100)), 1, first)),
        ('foreign_actual_conductor', lambda: clear(own[second['gain_native_id']][8], 8, first)),
    ]:
        try:
            action()
        except ValueError:
            controls.append(name)
        else:
            raise AssertionError('Accepted corruption '+name)

    diagnostic_active = True
    for plan in plans:
        # Both retime output accesses retain their complete original M4 drawing;
        # each real TM1 strap gets separate native M4/M5/TopVia1 endpoint stacks.
        for col in plan['columns']:
            for point in (col['low_dbu'], col['high_dbu']):
                via('Metal4', 'TopMetal1', point, plan, col['role']+'_native_upper_landing', upper=True)
            add_line(126, col['low_dbu'], col['high_dbu'], 3200, plan, col['role']+'_parallel_tm1_access')
        high = [col['high_dbu'] for col in plan['columns']]
        for point in high:
            via('Metal5', 'TopMetal2', point, plan, 'native_m5_tm2_bus_landing', upper=True)
        landing(134, plan['bus_boundary_dbu'], plan)
        add_line(134, plan['bus_boundary_dbu'], max(high, key=lambda q: q[0]), 3200, plan, 'parallel_tm2_bus_to_original_parent_boundary')
        # Existing base M1 geometry, original four cuts and all native devices
        # remain. The sixteen-column stack adds finite metal/via access.
        via('Metal1', 'Metal3', plan['base_pin_dbu'], plan, 'native_sixteen_column_base_access', columns=16)
        add_line(30, plan['base_lane_dbu'], plan['base_pin_dbu'], 1200, plan, 'wider_owned_sampler_base_escape')

    def equal_snapshot(a, b, ignore_instances=False):
        require(a[0].keys() == b[0].keys() and a[1] == b[1], 'Original layer/text inventory changed')
        for key in a[0]:
            require((a[0][key]^b[0][key]).is_empty(), 'Original cell drawing changed')
        if not ignore_instances:
            require(a[2] == b[2], 'Original cell hierarchy changed')

    # Every original cell except the parent is byte-geometrically unchanged.
    for index, before in old_cells.items():
        if index != T.cell_index():
            equal_snapshot(before, cell_snapshot(L, L.cell(index)))
    old_top = old_cells[T.cell_index()]
    now = cell_snapshot(L, T)
    require(old_top[1] == now[1], 'Original public labels changed')
    require(not (Counter(old_top[2])-Counter(now[2])), 'Original parent placement changed')
    require(len(now[2])-len(old_top[2]) == 28, 'Unexpected added via-instance census')
    require(T.bbox() == original_box, 'Candidate changes macro boundary')
    for key, before in all_before.items():
        expected = before + additions.get(key[0], pya.Region()) if key[1] == 0 else before
        actual = pya.Region(T.begin_shapes_rec(L.layer(*key))).merged()
        require((actual^expected).is_empty(), 'Unspecified original material changed')
    for m in ALLOWED:
        actual = pya.Region(T.begin_shapes_rec(L.layer(m, 0))).merged()
        require((actual^(total[m]+additions[m])).is_empty(), 'Added material differs from exact plan')
    # Actual drawn-geometry corruption checks, without mutating the source.
    witness = own[first['gain_native_id']][8]
    poly = next(witness.each())
    missing = total[8]-pya.Region(poly)
    try:
        require((missing^total[8]).is_empty(), 'Original material removed')
    except ValueError:
        controls.append('removed_actual_original_material')
    else:
        raise AssertionError('Accepted original material removal')
    require(len(controls) == 9, 'Missing candidate negative control')
    T.name = CANDIDATE
    args.out.mkdir(parents=True)
    output = args.out/(CANDIDATE+'.gds')
    L.write(str(output))
    reread = pya.Layout()
    reread.read(str(output))
    rt = reread.cell(CANDIDATE)
    require(rt is not None and rt.bbox() == original_box and reread.dbu == L.dbu, 'Serialized boundary/grid changed')
    for key, before in all_before.items():
        expected = before + additions.get(key[0], pya.Region()) if key[1] == 0 else before
        require((pya.Region(rt.begin_shapes_rec(reread.layer(*key)))^expected).is_empty(), 'Serialized original material differs')
    for m in ALLOWED:
        require((pya.Region(rt.begin_shapes_rec(reread.layer(m, 0)))^(total[m]+additions[m])).is_empty(), 'Serialized material differs')
    require(cell_snapshot(reread, rt)[1] == old_top[1], 'Serialized public labels changed')
    for index, before in old_cells.items():
        if index != T.cell_index():
            child = reread.cell(old_names[index])
            require(child is not None, 'Serialized original child disappeared')
            equal_snapshot(before, cell_snapshot(reread, child))
    require(all(sha(Path(q)) == h for q, h in protected.items()), 'Protected input changed')
    result = dict(status='GENERATED_SOURCE_REVIEWED_CANDIDATE_REQUIRES_ALL_NATIVE_PHYSICAL_RC_AND_ELECTRICAL_GATES',
        input_sha256=protected, original_top=original_top_name, candidate_top=CANDIDATE,
        source_diagnostic_run=40085495203, source_diagnostic_sha256=DIAG_SHA,
        plans=plans, additions=route_records, controls=controls,
        original_children_drawings_and_placements_preserved=True,
        original_public_labels_and_boundary_preserved=True,
        serialized_metal_and_via_delta_exact=True, added_via_instances=28,
        all_intrinsic_device_bias_and_stimulus_sources_unchanged=True,
        reduced_resistance_claim=False, electrical_accepted=False,
        drc_accepted=False, lvs_accepted=False, full_phy_accepted=False,
        qualified_pex=False, gds_sha256=sha(output),
        planning_clearance_dbu=CLEARANCE,
        scope='Candidate finite native vias and real upper/lower metal only. Planning clearance is an early collision rejection, not a DRC waiver or process qualification. Fresh physical verification and fresh RC/loading remain mandatory.')
    (args.out/'result.json').write_text(json.dumps(result, indent=2)+'\n')

if __name__ == '__main__':
    main()
