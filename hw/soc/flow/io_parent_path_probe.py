#!/usr/bin/env python3
# SPDX-FileCopyrightText: 2026 Hasan Melih Akbulut
# SPDX-License-Identifier: Apache-2.0
"""Native read-only actual I/O adjacency, source identity and conductor path probe."""
import argparse
from collections import Counter, deque
import hashlib
import json
from pathlib import Path

METALS = ('metal1_con', 'metal2_con', 'metal3_con', 'metal4_con', 'metal5_con', 'topmetal1_con', 'topmetal2_con')
VIAS = ('via1_drw', 'via2_drw', 'via3_drw', 'via4_drw', 'topvia1_n_cap', 'topvia2_drw')
LAYERS = (*METALS, *VIAS, 'cont_drw')
EDGES = tuple((METALS[i], v) for i, v in enumerate(VIAS)) + tuple((v, METALS[i+1]) for i, v in enumerate(VIAS)) + (('cont_drw', 'metal1_con'),)
CHAIN = (
 dict(instance='u_supply_Vdd', master='sg13g2_IOPadVdd', rotation=3, x_nm=0, y_nm=1157000),
 dict(instance='u_guard_3_23', master='sg13g2_Filler200', rotation=3, x_nm=0, y_nm=1077000),
 dict(instance='u_supply_Vss', master='sg13g2_IOPadVss', rotation=3, x_nm=0, y_nm=1076000),
 dict(instance='u_guard_3_24', master='sg13g2_Filler200', rotation=3, x_nm=0, y_nm=996000),
 dict(instance='u_supply_IOVdd', master='sg13g2_IOPadIOVdd', rotation=3, x_nm=0, y_nm=995000),
 dict(instance='u_guard_3_25', master='sg13g2_Filler200', rotation=3, x_nm=0, y_nm=915000),
 dict(instance='u_supply_IOVss', master='sg13g2_IOPadIOVss', rotation=3, x_nm=0, y_nm=914000),
)
TOP = 'ACTUAL_IO_ADJACENCY'
CASES = ['connected', 'same_name_open', 'missing_via', 'transformed_adjacency']


def require(ok, message):
    if not ok:
        raise ValueError(message)


def write(path, value):
    path.write_text(json.dumps(value, indent=2)+'\n')


def db_module():
    import klayout.db as db
    require(db.__version__ == '0.30.7', 'Unexpected native version')
    return db


def key(layer, poly):
    return layer+':'+hashlib.sha256(poly.to_s().encode()).hexdigest()


def physical(db, regions, points, edges=EDGES):
    """Cross-check native probe IDs with an explicit same-polygon/via path."""
    regions = {name: reg.merged() for name, reg in regions.items()}
    native = db.LayoutToNetlist('PATH', 0.001)
    for name, region in regions.items():
        native.register(region, name)
        native.connect(region)
    neighbors = {name: set() for name in regions}
    for a, b in edges:
        if a in regions and b in regions:
            native.connect(regions[a], regions[b])
            neighbors[a].add(b); neighbors[b].add(a)
    native.extract_netlist()
    identities = []
    seeds = []
    nodes = {key(name, p): (name, p) for name, reg in regions.items() for p in reg.each_merged()}
    for layer, xy in points:
        point = db.Point(*xy)
        net = native.probe_net(regions[layer], point)
        require(net is not None, 'Missing endpoint conductor')
        identities.append([net.circuit().name, net.cluster_id])
        hits = [key(layer, p) for p in regions[layer].each_merged() if p.inside(point)]
        require(len(hits) == 1, 'Endpoint is not in exactly one merged polygon')
        seeds.append(hits[0])
    previous = {seeds[0]: None}; queue = deque([seeds[0]])
    while queue and not set(seeds).issubset(previous):
        current = queue.popleft(); layer, polygon = nodes[current]
        for other in sorted(neighbors[layer]):
            for hit in regions[other].interacting(db.Region(polygon)).each_merged():
                ident = key(other, hit)
                require(ident in nodes, 'Interaction returned altered polygon')
                if ident not in previous:
                    previous[ident] = current; queue.append(ident)
    paths = []
    for seed in seeds[1:]:
        path = []
        if seed in previous:
            while seed is not None:
                path.append(seed); seed = previous[seed]
            path.reverse()
        paths.append(path)
    graph_joined = all(paths)
    native_joined = len({tuple(v) for v in identities}) == 1
    require(graph_joined == native_joined, 'Native/explicit physical graph disagree')
    used = sorted(set().union(*(set(p) for p in paths)))
    witnesses = {ident: dict(layer=nodes[ident][0], polygon=nodes[ident][1].to_s()) for ident in used}
    return dict(joined=native_joined, native_identities=identities, endpoints=points,
                paths=paths, polygon_witnesses=witnesses, visited_polygons=len(previous),
                virtual_connections=False, devices_conducting=False)


def controls(path):
    db = db_module(); results = {}
    for case in CASES[:3]:
        a = db.Region(db.Box(0, 0, 100, 20))
        b = db.Region(db.Box(80, 0, 100, 100))
        via = db.Region(db.Box(85, 5, 95, 15)) if case == 'connected' else db.Region()
        if case == 'same_name_open':
            a = db.Region(db.Box(0, 0, 20, 20)) + db.Region(db.Box(80, 0, 100, 20))
            points = [('metal1_con', [10,10]), ('metal1_con', [90,10])]
        else:
            points = [('metal1_con', [10,10]), ('metal2_con', [90,90])]
        row = physical(db, dict(metal1_con=a, metal2_con=b, via1_drw=via), points)
        require(row['joined'] == (case == 'connected'), 'Incorrect native control '+case)
        results[case] = row
    layout = db.Layout(); layout.dbu = .001
    top = layout.create_cell('CONTROL'); child = layout.create_cell('CHILD'); li = layout.layer(8,0)
    child.shapes(li).insert(db.Box(0,0,100,20))
    top.insert(db.CellInstArray(child.cell_index(), db.Trans(3,False,200,100)))
    top.insert(db.CellInstArray(child.cell_index(), db.Trans(3,False,200,0)))
    reg = db.Region(top.begin_shapes_rec(li)).merged()
    row = physical(db, {'metal1_con':reg}, [('metal1_con',[210,90]),('metal1_con',[210,-90])])
    require(row['joined'], 'Transformed native adjacency failed')
    results[CASES[3]] = row
    write(path, dict(status='PASS_NATIVE_PARENT_PATH_CONTROLS', cases=CASES, results=results,
                     klayout_version=db.__version__, dbu_um=.001))


def validate_placements(actual, expected):
    require(all(actual[name, trans] == 1 for name, trans in expected),
            'Selected real parent instance is missing or ambiguous')


def raw_regions(db, layout, cell):
    return {(layout.get_info(i).layer, layout.get_info(i).datatype): db.Region(cell.begin_shapes_rec(i)).merged()
            for i in layout.layer_indexes()}


def box_values(box):
    return [box.left, box.bottom, box.right, box.top]


def prepare(chip, actual_subset, coherent, output):
    db = db_module()
    hierarchy = db.Layout(); opt = db.LoadLayoutOptions(); opt.set_layer_map(db.LayerMap(), False)
    hierarchy.read(str(chip), opt)
    require(hierarchy.dbu == .001 and hierarchy.cell('nssoc_chip') is not None, 'Wrong parent units/top')
    actual = Counter((inst.cell.name,str(t)) for inst in hierarchy.cell('nssoc_chip').each_inst()
                     for t in inst.cell_inst.each_cplx_trans())
    transforms = [db.ICplxTrans(1, r['rotation']*90, False, r['x_nm'],r['y_nm']) for r in CHAIN]
    validate_placements(actual, [(r['master'], str(t)) for r,t in zip(CHAIN,transforms)])
    a = db.Layout(); a.read(str(actual_subset)); b = db.Layout(); b.read(str(coherent))
    require(a.dbu == b.dbu == .001, 'Unexpected master units')
    equality = {}; placements = []
    root = a.create_cell(TOP)
    for row, trans in zip(CHAIN, transforms):
        name = row['master']; left = a.cell(name); right = b.cell(name)
        require(left is not None and right is not None, 'Missing selected master '+name)
        lr = raw_regions(db,a,left); rr = raw_regions(db,b,right)
        diffs = []
        for pair in sorted(lr.keys() | rr.keys()):
            x = lr.get(pair,db.Region()) ^ rr.get(pair,db.Region())
            if not x.is_empty():
                diffs.append(dict(layer=list(pair), xor_area_dbu2=x.area(), xor_polygons=x.count(),
                                  xor_sha256=hashlib.sha256('\n'.join(sorted(p.to_s() for p in x.each_merged())).encode()).hexdigest()))
        equality[name] = dict(all_polygon_layers_equal=not diffs, differences=diffs,
                             actual_bbox_dbu=box_values(left.bbox()), coherent_bbox_dbu=box_values(right.bbox()))
        root.insert(db.CellInstArray(left.cell_index(),trans))
        placements.append(dict(**row, native_transform=str(trans), bbox_dbu=box_values(left.bbox().transformed(trans))))
    a.write(str(output/'actual-adjacency.gds'))
    write(output/'source-reconciliation.json',dict(status='ACTUAL_PARENT_TRANSFORMS_VERIFIED',
          actual_parent_instances=placements, masters=equality,
          all_selected_polygon_layers_equal=all(v['all_polygon_layers_equal'] for v in equality.values()),
          comparison_scope='Flattened polygon geometry on every layer; excludes text, property, cell boundary and recursive instance identity.',
          full_parent_routes_included=False, missing_path_is_inconclusive=True,
          source_cells_changed=False, diagnostic_parent_only=True))


def analyze(output):
    db = db_module(); source = json.loads((output/'source-reconciliation.json').read_text())
    data = json.loads((output/'conductors.json').read_text())
    require(data['dbu_um'] == .001 and set(data['masks']) == set(LAYERS), 'Unexpected conductor exports')
    regions = {}
    for name, row in data['masks'].items():
        reg = db.Region()
        for s in row['polygons']:
            reg.insert(db.Polygon.from_s(s))
        reg.merge()
        require(reg.area() == row['area_dbu2'] and reg.perimeter() == row['perimeter_dbu'], 'Export measurement changed')
        regions[name] = reg
    trans = db.Trans(3,False,0,1076000)
    points = [trans.trans(db.Point(40000,y)) for y in [19750,47250,130000]]
    result = physical(db, regions, [('topmetal1_con',[p.x,p.y]) for p in points])
    for witness in result['polygon_witnesses'].values():
        poly = db.Polygon.from_s(witness['polygon'])
        witness['intersected_actual_instance_windows'] = [r['instance'] for r in source['actual_parent_instances']
            if not (db.Region(poly) & db.Region(db.Box(*r['bbox_dbu']))).is_empty()]
    result.update(status='PARENT_SUBGRAPH_JOIN_PROVEN' if result['joined'] else 'INCONCLUSIVE_EXPAND_PARENT_CONTEXT',
        coherent_polygon_geometry_transfer_allowed=source['all_selected_polygon_layers_equal'],
        witness_owner_scope='Instance windows identify spatial context; polygon witnesses derive from exact source masks, not individual primitive ownership.',
        scope='Actual seven-instance Vdd/Vss/IOVdd/IOVss and three filler adjacency only. A positive physical path exists in the actual chip; a missing path here cannot establish full-parent disconnection.',
        tap_parameters_accepted=False, substrate_contract_accepted=False,
        cell_lvs_accepted=False,full_chip_lvs_accepted=False,manufacturing_approval=False)
    write(output/'analysis.json',result)


def main():
    p = argparse.ArgumentParser(description=__doc__); sub=p.add_subparsers(dest='mode',required=True)
    for name in ('controls','analyze'):
        s=sub.add_parser(name); s.add_argument('output',type=Path)
    s=sub.add_parser('prepare')
    for name in ('chip','actual_subset','coherent','output'):
        s.add_argument(name,type=Path)
    a=p.parse_args()
    if a.mode=='controls': controls(a.output)
    elif a.mode=='prepare': prepare(a.chip,a.actual_subset,a.coherent,a.output)
    else: analyze(a.output)


if __name__ == '__main__':
    main()
