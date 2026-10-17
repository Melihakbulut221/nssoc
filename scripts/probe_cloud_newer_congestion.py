#!/usr/bin/env python3
# SPDX-FileCopyrightText: 2026 Hasan Melih Akbulut
# SPDX-License-Identifier: Apache-2.0
"""Bind every failed global-route marker to the exact newer chip database."""
from collections import Counter, defaultdict
import argparse
from bisect import bisect_left, bisect_right
import hashlib
import json
import os
from pathlib import Path
import re
import subprocess
import tarfile

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / 'cloud-congestion-probe'
URL = 'https://github.com/Melihakbulut221/nssoc/releases/download/cloud-migration-20261012-000/newer-postcts-cloud-38317996877-1.tar.gz'
ARCHIVE_SHA = 'f8270a24dbd199e1ab9c3fc33ab670ceb81629c1d7220f0f2f4642b6828b318c'
ODB_SHA = 'e4e04605899913e69784bc32d4fabc39350fec8b975c6fdab095a6b95262d292'


def sha(path):
    with path.open('rb') as stream:
        return hashlib.file_digest(stream, 'sha256').hexdigest()


def spelling(name):
    return re.sub(r'\\([\[\]])', r'\1', name)


def transformed_rectangle(bounds, orientation, origin):
    """OpenDB orientation followed by instance origin, in integer DBU.

    The frozen runtime's Python dbTransform.apply rejects constructed Rect
    wrappers. Use the eight documented orthogonal transforms and independently
    compare every resulting pin union with OpenDB's native ITerm bbox below.
    """
    transforms = {
        'R0': lambda x, y: (x, y), 'R90': lambda x, y: (-y, x),
        'R180': lambda x, y: (-x, -y), 'R270': lambda x, y: (y, -x),
        'MY': lambda x, y: (-x, y), 'MYR90': lambda x, y: (-y, -x),
        'MX': lambda x, y: (x, -y), 'MXR90': lambda x, y: (y, x),
    }
    assert orientation in transforms
    x0, y0, x1, y1 = bounds
    assert x0 <= x1 and y0 <= y1
    points = [transforms[orientation](x, y) for x in (x0, x1) for y in (y0, y1)]
    return (min(x for x, y in points) + origin[0], min(y for x, y in points) + origin[1],
            max(x for x, y in points) + origin[0], max(y for x, y in points) + origin[1])


def native():
    import odb
    db = odb.dbDatabase.create()
    odb.read_db(db, str(OUT / 'postcts.odb'))
    block = db.getChip().getBlock()
    scale = block.getDbUnitsPerMicron()

    def box(rect):
        return [value / scale for value in (rect.xMin(), rect.yMin(), rect.xMax(), rect.yMax())]

    def intersects(a, b, margin=0):
        return a[0] <= b[2] + margin and a[2] >= b[0] - margin and a[1] <= b[3] + margin and a[3] >= b[1] - margin

    nets = {}
    for net in block.getNets():
        name = spelling(net.getName())
        assert name not in nets, ('Ambiguous net rendering', name)
        nets[name] = net
    macros, bins, cells = [], defaultdict(list), {}
    for inst in block.getInsts():
        bounds = box(inst.getBBox())
        row = dict(name=inst.getName(), master=inst.getMaster().getName(), bbox_um=bounds,
                   placement_status=str(inst.getPlacementStatus()))
        cells[inst.getName()] = row
        if inst.getMaster().isBlock():
            macros.append(row)
        else:
            cx, cy = (bounds[0] + bounds[2]) / 2, (bounds[1] + bounds[3]) / 2
            bins[(int(cx // 25), int(cy // 25))].append(row)
    source = (OUT / 'congestion.rpt').read_text()
    markers = []
    for part in source.split('violation type:')[1:]:
        capacity = re.search(r'capacity:(\d+) usage:(\d+) overflow:(\d+)', part)
        bounds = re.search(r'bbox = \(([-\d.]+), ([-\d.]+)\) - \(([-\d.]+), ([-\d.]+)\) on Layer (\S+)', part)
        names = re.search(r'(?m)^\s*srcs: (.+)$', part)
        assert capacity and bounds and names, part
        area = list(map(float, bounds.groups()[:4]))
        related = []
        for token in names[1].split():
            assert token.startswith('net:'), token
            rendered = spelling(token[4:])
            assert rendered in nets, ('Unbound report net', rendered)
            net = nets[rendered]
            drivers = []
            for terminal in net.getITerms():
                if str(terminal.getIoType()) == 'OUTPUT':
                    inst = terminal.getInst()
                    drivers.append(dict(instance=inst.getName(), master=inst.getMaster().getName(),
                                        pin=terminal.getMTerm().getName(), bbox_um=box(inst.getBBox())))
            related.append(dict(reported=token[4:], net=net.getName(), drivers=drivers,
                                terminals=len(net.getITerms()), signal_type=str(net.getSigType())))
        nearby = []
        for bx in range(int((area[0] - 25) // 25), int((area[2] + 25) // 25) + 1):
            for by in range(int((area[1] - 25) // 25), int((area[3] + 25) // 25) + 1):
                nearby.extend(r for r in bins[(bx, by)] if intersects(r['bbox_um'], area, 14.4))
        markers.append(dict(kind=part.splitlines()[0].strip(), bbox_um=area, reported_layer=bounds[5],
                            capacity=int(capacity[1]), demand=int(capacity[2]), overflow=int(capacity[3]),
                            nets=related, adjacent_macros=[r for r in macros if intersects(r['bbox_um'], area, 14.4)],
                            nearby_standard_cells=len(nearby), nearby_masters=dict(Counter(r['master'] for r in nearby))))
    assert markers and len(markers) == source.count('violation type:')
    counted = Counter(n['net'] for m in markers for n in m['nets'])
    # Report every endpoint of every involved net, not just its driver. This
    # distinguishes pin escape over macros from logic density in nearby rows.
    endpoints = {}
    for name in sorted(counted):
        net = nets[spelling(name)]
        pins = []
        for terminal in net.getITerms():
            inst = terminal.getInst()
            pins.append(dict(instance=inst.getName(), pin=terminal.getMTerm().getName(),
                             direction=str(terminal.getIoType()),
                             macro=inst.getMaster().isBlock(), **{
                                 k: v for k, v in cells[inst.getName()].items() if k != 'name'}))
        endpoints[name] = dict(signal_type=str(net.getSigType()), terminals=pins,
                               boundary_pins=[p.getName() for p in net.getBTerms()])
    tile_size = 100
    density = []
    # Geometric occupied area is intentionally not called legal row capacity.
    # Macro obstructions and real rows must still be respected by legalization.
    envelope = [min(m['bbox_um'][0] for m in markers)-200,
                min(m['bbox_um'][1] for m in markers)-200,
                max(m['bbox_um'][2] for m in markers)+200,
                max(m['bbox_um'][3] for m in markers)+200]
    def overlap(a, b):
        return max(0, min(a[2], b[2])-max(a[0], b[0])) * max(0, min(a[3], b[3])-max(a[1], b[1]))
    for x in range(int(envelope[0]//tile_size), int(envelope[2]//tile_size)+1):
        for y in range(int(envelope[1]//tile_size), int(envelope[3]//tile_size)+1):
            area = [x*tile_size,y*tile_size,(x+1)*tile_size,(y+1)*tile_size]
            near = [r for bx in range(x*4-1,x*4+5) for by in range(y*4-1,y*4+5)
                    for r in bins[(bx,by)] if intersects(r['bbox_um'],area)]
            density.append(dict(bbox_um=area, standard_cell_area_um2=sum(overlap(r['bbox_um'],area) for r in near),
                                intersecting_cells=len(near),
                                macro_area_um2=sum(overlap(r['bbox_um'],area) for r in macros)))
    report = dict(status='PASS_EXACT_CONGESTION_CONNECTIVITY_DIAGNOSIS_NOT_ROUTE_CLOSURE',
                  source_odb_sha256=sha(OUT / 'postcts.odb'), source_report_sha256=sha(OUT / 'congestion.rpt'),
                  die_um=box(block.getDieArea()), core_um=box(block.getCoreArea()), macros=macros,
                  marker_count=len(markers), report_overflow_sum=sum(m['overflow'] for m in markers),
                  note='DRC-viewer marker totals and layer-level final overflow totals are separate native reports; neither is waived.',
                  most_repeated_nets=counted.most_common(40), markers=markers,
                  all_congested_net_endpoints=endpoints, local_geometric_density=density,
                  density_note='Clipped standard-cell and macro area per100um tile, not routability or legal-site capacity.')
    # Inspect actual abstract pin shapes/obstructions at the remaining macro
    # hotspots before choosing another placement or routing experiment. A
    # track center inside a pin rectangle is not a legal detailed-router AP.
    tracks = {g.getTechLayer().getName(): (list(g.getGridX()), list(g.getGridY()))
              for g in block.getTrackGrids()}
    wanted = {m['name'] for row in markers for m in row['adjacent_macros']}
    macro_access = {}
    for inst in block.getInsts():
        if inst.getName() not in wanted:
            continue
        def placed(shape):
            bounds = (shape.xMin(), shape.yMin(), shape.xMax(), shape.yMax())
            return odb.Rect(*transformed_rectangle(bounds, str(inst.getOrient()), inst.getOrigin()))
        pin_shapes = []
        for term in inst.getITerms():
            shapes = []
            for pin in term.getMTerm().getMPins():
                for shape in pin.getGeometry():
                    assert shape.getTechLayer() is not None, 'Unmodeled native pin-via geometry'
                    rect = placed(shape)
                    layer = shape.getTechLayer().getName()
                    xs, ys = tracks.get(layer, ([], []))
                    row = dict(pin=term.getMTerm().getName(), layer=layer, bbox_um=box(rect),
                        direction=str(term.getIoType()), signal_type=str(term.getSigType()),
                        net=term.getNet().getName() if term.getNet() else None,
                        x_track_centers=bisect_right(xs, rect.xMax())-bisect_left(xs, rect.xMin()),
                        y_track_centers=bisect_right(ys, rect.yMax())-bisect_left(ys, rect.yMin()))
                    shapes.append(row)
            if shapes:
                # Check every transformed pin against OpenDB's own placed bbox.
                union = [min(s['bbox_um'][i] for s in shapes) if i < 2 else
                         max(s['bbox_um'][i] for s in shapes) for i in range(4)]
                assert union == box(term.getBBox()), (inst.getName(), term.getMTerm().getName())
            pin_shapes.extend(shapes)
        obstructions = []
        for shape in inst.getMaster().getObstructions():
            assert shape.getTechLayer() is not None, 'Unmodeled native obstruction-via geometry'
            obstructions.append(dict(layer=shape.getTechLayer().getName(), bbox_um=box(placed(shape))))
        nearby = []
        bounds = box(inst.getBBox())
        for index, marker in enumerate(markers):
            area = marker['bbox_um']
            if not intersects(bounds, area, 14.4):
                continue
            pins = [s for s in pin_shapes if intersects(s['bbox_um'], area, 7.2)]
            obs = [s for s in obstructions if intersects(s['bbox_um'], area)]
            macro_nets = {s['net'] for s in pin_shapes if s['net']}
            involved = {n['net'] for n in marker['nets']}
            nearby.append(dict(marker_index=index, bbox_um=area, overflow=marker['overflow'],
                overlaps_macro=intersects(bounds, area),
                nearby_pin_shapes=pins, intersecting_obstruction_boxes=obs,
                involved_macro_terminal_nets=sorted(involved & macro_nets),
                involved_nets_without_terminal_on_this_macro=sorted(involved-macro_nets)))
        macro_access[inst.getName()] = dict(master=inst.getMaster().getName(),
            orientation=str(inst.getOrient()), bbox_um=bounds, pin_shapes=pin_shapes,
            obstruction_boxes=obstructions, nearby_markers=nearby)
    assert set(macro_access) == wanted
    report['macro_pin_access'] = macro_access
    report['macro_pin_access_scope'] = ('Exact transformed native LEF pin and obstruction rectangles, '
        'with every pin union checked against native ITerm bbox. Track-center counts are geometric '
        'observations only, not legal via access, DRC, or routing acceptance. Obstructions remain unchanged.')
    pin_counts=Counter(); low_degree=[]
    for net in block.getNets():
        if str(net.getSigType()) in ('POWER','GROUND'):
            continue
        iterms=list(net.getITerms()); bterms=list(net.getBTerms())
        degree=len(iterms)+len(bterms); pin_counts[degree]+=1
        if degree<2:
            low_degree.append(dict(name=net.getName(),signal_type=str(net.getSigType()),
                iterms=[dict(instance=t.getInst().getName(),pin=t.getMTerm().getName()) for t in iterms],
                bterms=[t.getName() for t in bterms],physical_terminal_count=degree))
    report['signal_net_terminal_inventory']=dict(count_by_degree=dict(sorted(pin_counts.items())),
        low_degree_nets=sorted(low_degree,key=lambda row:row['name']),
        scope='Read-only original native database terminals. No net/pin deletion, no exclusion from routing, no claim about CUGR selected access points. Tests the empty-net hypothesis for stage1 vector::reserve failure.')
    (OUT / 'diagnosis.json').write_text(json.dumps(report, indent=2) + '\n')



# Restore the actual October 12 pre-CTS lineage, never the older September
# chip. All native reads and bulk archive restoration run on hosted machines.
PRECTS_BATCHES = {
    13: ('e55c3b18997b7ee871cca6dfd21400f66ecab824c038f7dcd385c09f2ac67313',
         'e9653c2c3b1fcf1ff248759db6374c0356b2db6d52e2e15680898e84ea13a781'),
    14: ('00ef57438d9021e48a863afb9a80af39d5c067ee8114b767288e620b2d3c28c9',
         'a7f993fbf53b6f1bc07245eba6a71391d7a18cd7d94892191e5d9c65fc8cbb5b'),
    15: ('6fc9d73aba25812cb24af818928b54c7c13caacad6e73062c5cd137e16c9f8dc',
         '36536854aa6d634ada8b22ede623ef6eaf7f06c71209729e2891240f7090c4c2'),
    16: ('026ffa6be2ca58807f8d0a598257436b088d003409d8cc318ff2674730fc5d83',
         '2b804a75f501025631c0955adedf155df2c095686c537ae46d2c1751ad826912'),
}
PRECTS_PREFIX = 'hw/soc/out/pcie-rx-return-metadata-20261012/'
PRECTS_RUN = PRECTS_PREFIX + 'physical19/runs/metadata-postcts19/'
PRECTS_DATABASES = {
    'preplacement': ('13-openroad-ioplacement/soc_top.odb',
        '518b889c9d8dc9674509be7bab88d9ecadfc4262769f824c1af270dd041fbcb7'),
    'prects': ('22-openroad-detailedplacement/soc_top.odb',
        '4739da2254a80397ab82f5c70550b9215e7ac5853c0e78cd0fb7dabefece20d8'),
    'postcts': ('final/odb/soc_top.odb', ODB_SHA),
}


def prects_native():
    import odb
    from repair_cloud_macro_channels import signature, boundary_geometry
    result = {}
    for label, (_, expected) in PRECTS_DATABASES.items():
        path = OUT / (label + '.odb')
        assert sha(path) == expected
        db = odb.dbDatabase.create(); odb.read_db(db, str(path))
        block = db.getChip().getBlock(); scale = block.getDbUnitsPerMicron()
        def bounds(rect):
            return [x/scale for x in (rect.xMin(),rect.yMin(),rect.xMax(),rect.yMax())]
        macros, masters, hierarchy, data_flops = {}, Counter(), Counter(), []
        for inst in block.getInsts():
            name = inst.getName(); master = inst.getMaster().getName()
            masters[master] += 1
            if inst.getMaster().isBlock():
                macros[name] = dict(master=master,bbox_um=bounds(inst.getBBox()),
                    origin_dbu=list(inst.getOrigin()),orientation=str(inst.getOrient()))
            # Hierarchical names and all connected net names are retained for
            # placement-domain design. A name is not a functional equivalence proof.
            if master.startswith('sg13g2_df'):
                connected = sorted(t.getNet().getName() for t in inst.getITerms() if t.getNet())
                domains = sorted({prefix for prefix in ('u_pcie.','u_eth.','u_ibex.')
                    if name.startswith(prefix) or any(n.startswith(prefix) for n in connected)})
                hierarchy.update(domains or ['other'])
                if 'u_pcie.' in domains or 'u_eth.' in domains:
                    data_flops.append(dict(name=name,master=master,bbox_um=bounds(inst.getBBox()),nets=connected))
        result[label] = dict(odb_sha256=expected,instances=len(block.getInsts()),nets=len(block.getNets()),
            connectivity_sha256=signature(block),masters=dict(masters),macros=macros,
            boundary_geometry=boundary_geometry(block),die_um=bounds(block.getDieArea()),
            core_um=bounds(block.getCoreArea()),data_flop_domain_counts=dict(hierarchy),data_flops=data_flops)
        assert sha(path) == expected, 'Read-only native source changed'
    # Resizing/CTS legitimately change instances and connectivity; do not call
    # equal macro geometry functional equivalence of these three databases.
    for label in ('preplacement','prects'):
        for key in ('macros','boundary_geometry','die_um','core_um'):
            assert result[label][key] == result['postcts'][key], (label,key)
    assert result['prects']['instances'] < result['postcts']['instances']
    (OUT/'prects-native.json').write_text(json.dumps(dict(
        status='PASS_NATIVE_PRECTS_LINEAGE_GEOMETRY_NOT_EQUIVALENCE', stages=result),indent=2)+'\n')


def prects_inventory():
    assert os.environ.get('GITHUB_ACTIONS') == 'true', 'Hosted-only recovery'
    OUT.mkdir(exist_ok=False)
    result = dict(status='RUNNING',adopted=False,source_profile='prects_inventory',
        scope='Exact current-chip preplacement/pre-CTS recovery and native geometry audit. No placement change, circuit equivalence, CTS, route or timing acceptance.')
    def save():
        (OUT/'result.json').write_text(json.dumps(result,indent=2)+'\n')
    save()
    try:
        metadata, restored = {}, {}
        wanted = {PRECTS_RUN+member:(label,expected) for label,(member,expected) in PRECTS_DATABASES.items()}
        for index,(archive_sha,manifest_sha) in PRECTS_BATCHES.items():
            prefix = 'batch-'+str(index).zfill(6)
            url = 'https://github.com/Melihakbulut221/nssoc/releases/download/cloud-migration-20261012-000/'+prefix
            archive_path=OUT/(prefix+'.tar.gz'); manifest_path=OUT/(prefix+'.manifest.json')
            for path,suffix,digest in [(archive_path,'.tar.gz',archive_sha),(manifest_path,'.manifest.json',manifest_sha)]:
                subprocess.run(['curl','--fail','--location','--retry','4',url+suffix,'-o',str(path)],check=True)
                assert sha(path)==digest,path
            manifest=json.loads(manifest_path.read_text())
            records={r['path']:r for r in manifest['records']}
            assert len(records)==len(manifest['records']), 'Duplicate source record'
            with tarfile.open(archive_path) as tar:
                names=[m.name for m in tar.getmembers()]
                assert len(names)==len(set(names)), 'Duplicate archive path'
                for name,row in records.items():
                    parent=Path(name).parent.name
                    text_selected=(name.startswith(PRECTS_PREFIX) and row['bytes']<65536 and
                        (name in [PRECTS_PREFIX+'physical19.py',PRECTS_PREFIX+'physical-result19.json',
                                  PRECTS_PREFIX+'physical19/config.json',PRECTS_PREFIX+'physical19/physical.sdc']
                         or name.startswith(PRECTS_RUN) and
                            (parent in ['16-openroad-globalplacement','20-openroad-repairdesignpostgpl',
                              '22-openroad-detailedplacement','23-openroad-cts','25-openroad-resizertimingpostcts']
                             and Path(name).suffix in ['.json','.tcl','.log']
                             or name==PRECTS_RUN+'resolved.json')))
                    if name not in wanted and not text_selected: continue
                    member=tar.getmember(name)
                    assert member.isfile() or member.islnk()
                    raw=tar.extractfile(member).read()
                    assert len(raw)==row['bytes'] and hashlib.sha256(raw).hexdigest()==row['sha256'],name
                    if name in wanted:
                        label,expected=wanted[name]; assert row['sha256']==expected
                        (OUT/(label+'.odb')).write_bytes(raw)
                        restored[label]=dict(row,archive_sha256=archive_sha,manifest_sha256=manifest_sha)
                    else:
                        metadata[name]=dict(sha256=row['sha256'],text=raw.decode())
            archive_path.unlink()
        assert set(restored)==set(PRECTS_DATABASES)
        assert PRECTS_PREFIX+'physical19.py' in metadata and PRECTS_RUN+'23-openroad-cts/config.json' in metadata
        result.update(restored_databases=restored,bound_metadata=metadata)
        save()
        with (OUT/'native.log').open('w') as log:
            code=subprocess.call([os.environ['CLOUD_APPIMAGE'],'openroad','-exit','-python',str(Path(__file__).resolve())],
                env=dict(os.environ,NSSOC_PRECTS_NATIVE='1'),stdout=log,stderr=subprocess.STDOUT)
        assert code==0,(code,(OUT/'native.log').read_text()[-8000:])
        result['native']=json.loads((OUT/'prects-native.json').read_text())
        result['status']='PASS_SOURCE_BOUND_PRECTS_RECOVERY_NOT_IMPLEMENTATION'
        (OUT/'diagnosis.json').write_text(json.dumps(result,indent=2)+'\n')
    except BaseException as error:
        result.update(status='FAIL_OR_ERROR',error=repr(error)); raise
    finally:
        save()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--source-profile', choices=('baseline', 'local_optimize', 'reserved_m5', 'local_optimize_buffers', 'local_data_endpoints', 'critical30_buffers', 'seed13_buffers','halo1_seed13_buffers','routability_data','prects_inventory','prects_grt','packet193'), default='baseline')
    args = parser.parse_args()
    if args.source_profile == 'prects_inventory':
        prects_inventory(); return
    url, archive_sha, odb_sha = URL, ARCHIVE_SHA, ODB_SHA
    odb_member = 'cloud-newer-postcts/inputs/postcts.odb'
    report_sha = None
    archive_bytes = None
    if args.source_profile=='prects_grt':
        url='https://github.com/Melihakbulut221/nssoc/releases/download/cloud-results-38598795406-1-route-prects_grt/newer-postcts-placement-prects_grt-38598795406-1.tar.gz'
        archive_sha='7ff9afaba0a51ba9ec4882466bc6061dc027ff75f5d83f95d65bf56f077ea444'
        archive_bytes=144385152
        odb_sha='9986a3170149679957242ad825a329c924aae5a151907a7db5903188d553f273'
        report_sha='a56c1d7e0a88b4eaa01f02576be97fc71fde0ae68f1edf5eda009c99fb2fc7c1'
        odb_member='cloud-newer-postcts/failed-global.odb'
    if args.source_profile == 'packet193':
        evidence = json.loads((ROOT/'docs/evidence/pcie-packet-cluster-targeted-rejection-20261015.json').read_text())
        assert evidence['run'] == 38683404082
        receipt = evidence['receipt']
        url, archive_sha, archive_bytes = receipt['url'], receipt['sha256'], receipt['bytes']
        odb_sha = evidence['result']['failure_outputs']['failed-global.odb']
        report_sha = evidence['result']['failure_outputs']['congestion.rpt']
        odb_member = 'cloud-newer-postcts/failed-global.odb'
    if args.source_profile in ('local_optimize', 'reserved_m5', 'local_optimize_buffers', 'local_data_endpoints', 'critical30_buffers', 'seed13_buffers','halo1_seed13_buffers','routability_data'):
        evidence_name = {'local_optimize': 'cloud-local-optimize-route-failure-20261013.json',
                         'reserved_m5': 'cloud-reserved-m5-route-failure-20261013.json',
                         'local_optimize_buffers': 'cloud-local-optimize-buffers-route-failure-20261013.json',
                         'local_data_endpoints': 'cloud-closure-continuation-20261013.json',
                         'critical30_buffers': 'cloud-critical30-buffers-route-failure-20261013.json',
                         'seed13_buffers': 'cloud-seed13-buffers-route-failure-20261014.json',
                         'halo1_seed13_buffers': 'cloud-seed13-buffers-route-failure-20261014.json',
                         'routability_data': 'cloud-closure-continuation-20261013.json'}[args.source_profile]
        evidence = json.loads((ROOT / 'docs/evidence' / evidence_name).read_text())
        if args.source_profile == 'routability_data':
            evidence=evidence['routability_data_terminal_20261014']
            assert evidence['run']==38511490580 and evidence['routing_seed']==13
            assert evidence['placement_profile']=='routability_data'
            assert evidence['macro_routing_profile']=='baseline'
            assert evidence['routing_capacity_perturbation_percentage']==0
        if args.source_profile == 'halo1_seed13_buffers':
            evidence=evidence['halo1_terminal']
            assert evidence['run']==38490952579 and evidence['routing_seed']==13
            assert evidence['macro_routing_profile']=='halo1'
            assert evidence['routing_capacity_perturbation_percentage']==0
            assert evidence['placement_profile']=='local_optimize_buffers'
        if args.source_profile == 'local_data_endpoints':
            evidence = evidence['local_data_endpoints_terminal']
            assert evidence['run'] == 38395878470
        if args.source_profile == 'critical30_buffers':
            assert evidence['run'] == 38420407838
            assert evidence['critical_nets_percentage'] == 30
            assert evidence['placement_profile'] == 'local_optimize_buffers'
        if args.source_profile == 'seed13_buffers':
            assert evidence['run'] == 38448901835 and evidence['routing_seed'] == 13
            assert evidence['routing_capacity_perturbation_percentage'] == 0
            assert evidence['placement_profile'] == 'local_optimize_buffers'
        assert evidence['status'] == 'FAILED_NATIVE_GLOBAL_ROUTE_CONGESTION'
        receipt = evidence['receipt']
        url, archive_sha, archive_bytes = receipt['url'], receipt['sha256'], receipt['bytes']
        odb_sha = evidence['failure_outputs']['failed-global.odb']
        report_sha = evidence['failure_outputs']['congestion.rpt']
        odb_member = 'cloud-newer-postcts/failed-global.odb'
    OUT.mkdir(exist_ok=False)
    result = dict(status='RUNNING', adopted=False, source_profile=args.source_profile,
                  source_url=url, source_archive_sha256=archive_sha,
                  source_odb_member=odb_member, source_odb_sha256=odb_sha)
    try:
        packed = OUT / 'source.tar.gz'
        subprocess.run(['curl', '--fail', '--location', '--retry', '4', url, '-o', str(packed)], check=True)
        assert sha(packed) == archive_sha
        assert archive_bytes is None or packed.stat().st_size == archive_bytes
        with tarfile.open(packed) as tar:
            if args.source_profile=='prects_grt':
                raw=tar.extractfile('cloud-newer-postcts/result.json').read()
                assert hashlib.sha256(raw).hexdigest()=='81eaedc5f7bef9f47e93c3b4ab1150fc5b6c75a8c1f0dd02f54256cd3516320e'
                original=json.loads(raw)
                assert original['status']=='FAIL_OR_ERROR'
                assert original['placement_profile']=='prects_grt'
                assert original['routing_seed']==13 and original['routing_capacity_perturbation_percentage']==0
                assert original['router_solver']=='fast_route' and original['ethernet_hold_depth']==0
                assert original['fresh_cts']['status']=='PASS_PLACEMENT_AND_TRANSPARENT_CTS_GRAPH_NOT_TIMING'
                assert original['failure_outputs']['failed-global.odb']==odb_sha
                assert original['failure_outputs']['congestion.rpt']==report_sha
                result['source_run']=38598795406
                result['source_summary_sha256']=hashlib.sha256(raw).hexdigest()
            if args.source_profile == 'packet193':
                raw = tar.extractfile('cloud-newer-postcts/result.json').read()
                assert hashlib.sha256(raw).hexdigest() == evidence['summary_sha256']
                original = json.loads(raw)
                assert original == evidence['result']
                assert original['status'] == 'FAIL_OR_ERROR' and original['packet_clusters_requested']
                assert original['packet_cluster_guidance']['cluster_scope'] == 'diagnosed_193_only'
                assert original['packet_cluster_guidance']['clustered_packet_bit_nets'] == 193
                assert original['routing_capacity_perturbation_percentage'] == 0
                assert original['fresh_cts']['status'] == 'PASS_PLACEMENT_AND_TRANSPARENT_CTS_GRAPH_NOT_TIMING'
                result['source_run'] = evidence['run']
                result['source_summary_sha256'] = hashlib.sha256(raw).hexdigest()
            if args.source_profile == 'routability_data':
                raw=tar.extractfile('cloud-newer-postcts/result.json').read()
                assert hashlib.sha256(raw).hexdigest()==evidence['summary_sha256']
                original=json.loads(raw)
                assert original['status']=='FAIL_OR_ERROR'
                for key in ('placement_profile','routing_seed','macro_routing_profile','routing_capacity_perturbation_percentage','failure_outputs'):
                    assert original[key]==evidence[key], key
            for local, member in [('postcts.odb', odb_member),
                                  ('congestion.rpt', 'cloud-newer-postcts/congestion.rpt')]:
                item = tar.getmember(member)
                assert item.isfile()
                (OUT / local).write_bytes(tar.extractfile(item).read())
        packed.unlink()
        assert sha(OUT / 'postcts.odb') == odb_sha
        assert report_sha is None or sha(OUT / 'congestion.rpt') == report_sha
        protected = {name: sha(OUT / name) for name in ['postcts.odb', 'congestion.rpt']}
        with (OUT / 'native.log').open('w') as log:
            code = subprocess.call([os.environ['CLOUD_APPIMAGE'], 'openroad', '-exit', '-python', str(Path(__file__).resolve())],
                                   env=dict(os.environ, NSSOC_CONGESTION_NATIVE='1'), stdout=log, stderr=subprocess.STDOUT)
        assert code == 0, (code, (OUT / 'native.log').read_text()[-8000:])
        assert all(sha(OUT / name) == digest for name, digest in protected.items())
        diagnosis = json.loads((OUT / 'diagnosis.json').read_text())
        result.update(status=diagnosis['status'], markers=diagnosis['marker_count'], diagnosis_sha256=sha(OUT / 'diagnosis.json'))
    except BaseException as error:
        result.update(status='FAIL_OR_ERROR', error=repr(error))
        raise
    finally:
        (OUT / 'result.json').write_text(json.dumps(result, indent=2) + '\n')


if __name__ == '__main__':
    if os.environ.get('NSSOC_PRECTS_NATIVE') == '1': prects_native()
    elif os.environ.get('NSSOC_CONGESTION_NATIVE') == '1': native()
    else: main()
