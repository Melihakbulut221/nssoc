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
    (OUT / 'diagnosis.json').write_text(json.dumps(report, indent=2) + '\n')


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--source-profile', choices=('baseline', 'local_optimize', 'reserved_m5', 'local_optimize_buffers'), default='baseline')
    args = parser.parse_args()
    url, archive_sha, odb_sha = URL, ARCHIVE_SHA, ODB_SHA
    odb_member = 'cloud-newer-postcts/inputs/postcts.odb'
    report_sha = None
    archive_bytes = None
    if args.source_profile in ('local_optimize', 'reserved_m5', 'local_optimize_buffers'):
        evidence_name = {'local_optimize': 'cloud-local-optimize-route-failure-20261013.json',
                         'reserved_m5': 'cloud-reserved-m5-route-failure-20261013.json',
                         'local_optimize_buffers': 'cloud-local-optimize-buffers-route-failure-20261013.json'}[args.source_profile]
        evidence = json.loads((ROOT / 'docs/evidence' / evidence_name).read_text())
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
    native() if os.environ.get('NSSOC_CONGESTION_NATIVE') == '1' else main()
