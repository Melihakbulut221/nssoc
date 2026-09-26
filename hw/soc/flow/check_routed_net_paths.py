# SPDX-FileCopyrightText: 2026 Hasan Melih Akbulut
# SPDX-License-Identifier: Apache-2.0
"""Check geometric continuity of selected small signal nets in an OpenDB file.

Run with OpenROAD's Python interpreter. Same-layer conductors must overlap
with positive area; a native via joins its routing-layer enclosures. Cell
ports are black boxes. This is not cross-net short detection, cell-interior
LVS, antenna, timing or full-chip signoff. Top ports and special wires are
explicitly unsupported, rather than silently excluded.
"""
import argparse
import hashlib
import json
from pathlib import Path


def connectivity(nodes, links, pins):
    """Nodes are (routing layer, rectangle); links represent vias/cell ports."""
    if not nodes or not pins or len(nodes) > 5000:
        raise ValueError('Require pins and 1..5000 conductor rectangles')
    for layer, (a, b, c, d) in nodes:
        if not layer or a >= c or b >= d:
            raise ValueError('Invalid conductor rectangle')
    parent = list(range(len(nodes)))

    def root(i):
        while parent[i] != i:
            parent[i] = parent[parent[i]]
            i = parent[i]
        return i

    def join(i, j):
        if not (0 <= i < len(nodes) and 0 <= j < len(nodes)):
            raise ValueError('Invalid connectivity link')
        parent[root(i)] = root(j)

    for i, j in links:
        join(i, j)
    for label, i in pins.items():
        if not label or not 0 <= i < len(nodes):
            raise ValueError('Invalid cell pin')
    for i, (layer, a) in enumerate(nodes):
        for j, (other, z) in enumerate(nodes[:i]):
            if (layer == other and min(a[2], z[2]) > max(a[0], z[0])
                    and min(a[3], z[3]) > max(a[1], z[1])):
                join(i, j)
    components = {label: root(i) for label, i in pins.items()}
    return {
        'pins': components,
        'all_pins_connected': len(set(components.values())) == 1,
        'all_route_shapes_connected': len({root(i) for i in range(len(nodes))}) == 1,
        'rectangles': len(nodes),
    }


def geometry(net):
    import odb
    if (net.getSigType() not in ('SIGNAL', 'CLOCK') or net.getBTerms()
            or net.getSWires() or not net.getWire()):
        raise ValueError('Require routed signal/clock net without top ports or special wires')
    nodes, links, pins = [], [], {}

    def rect(shape, dx=0, dy=0):
        layer = shape.getTechLayer()
        if layer.getType() != 'ROUTING':
            return None
        nodes.append((layer.getName(), (shape.xMin() + dx, shape.yMin() + dy,
                                       shape.xMax() + dx, shape.yMax() + dy)))
        return len(nodes) - 1

    it, path, row = odb.dbWirePathItr(), odb.dbWirePath(), odb.dbWirePathShape()
    it.begin(net.getWire())
    while it.getNextPath(path):
        while it.getNextShape(row):
            shape = row.shape
            if shape.isVia():
                via = shape.getTechVia() or shape.getVia()
                ids = [rect(part, *shape.getViaXY()) for part in via.getBoxes()]
                ids = [i for i in ids if i is not None]
                if len({nodes[i][0] for i in ids}) < 2:
                    raise ValueError('Via lacks two routing-layer enclosures')
                links.extend(zip(ids, ids[1:]))
            else:
                rect(shape)
    it, shape = odb.dbITermShapeItr(), odb.dbShape()
    for pin in net.getITerms():
        label = pin.getInst().getName() + '/' + pin.getMTerm().getName()
        ids = []
        it.begin(pin)
        while it.next(shape):
            if shape.isVia():
                raise ValueError('Explicit via pin unsupported')
            i = rect(shape)
            if i is not None:
                ids.append(i)
        if not ids:
            raise ValueError('Cell pin has no conductor: ' + label)
        # All shapes of one declared cell port are internally connected.
        links.extend(zip(ids, ids[1:]))
        pins[label] = ids[0]
    return nodes, links, pins


def check(source, names):
    import odb
    if not names or len(names) != len(set(names)):
        raise ValueError('Require distinct selected nets')
    digest = lambda: hashlib.sha256(source.read_bytes()).hexdigest()
    before = digest()
    db = odb.dbDatabase.create()
    try:
        odb.read_db(db, str(source))
        block = db.getChip().getBlock()
        rows = {}
        for name in names:
            net = block.findNet(name)
            if net is None:
                raise ValueError('Missing selected net: ' + name)
            rows[name] = connectivity(*geometry(net))
    finally:
        odb.dbDatabase.destroy(db)
    if digest() != before:
        raise ValueError('Source changed during geometric check')
    return {'scope': __doc__, 'source': str(source), 'source_sha256': before,
            'source_unchanged': True, 'nets': rows,
            'passed': all(r['all_pins_connected'] and r['all_route_shapes_connected']
                          for r in rows.values())}


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('source', type=Path)
    parser.add_argument('output', type=Path)
    parser.add_argument('--nets', nargs='+', required=True)
    args = parser.parse_args()
    if args.output.exists():
        raise ValueError('Refusing to replace previous evidence')
    result = check(args.source.resolve(), args.nets)
    with args.output.open('x') as output:
        output.write(json.dumps(result, indent=2) + '\n')
    print(json.dumps(result, indent=2))
    raise SystemExit(0 if result['passed'] else 1)
