# SPDX-FileCopyrightText: 2026 Hasan Melih Akbulut
# SPDX-License-Identifier: Apache-2.0
"""Tie placed timing paths to RTL registers.

usage: trace_paths.py <mapped.json> <report> <out prefix> [top] [flop map .tsv]

<report> is OpenSTA `report_checks` text (full paths). Every flip-flop and
cell instance on a path is looked up in the synthesized netlist (Yosys JSON
of the netlist that entered placement; instance names survive placement and
repair, only inserted buffers are new). A flip-flop is named by the public
nets on its Q pin, which carry the RTL register name and bit, and by its
`src` attribute when synthesis kept one.

Writes <prefix>.json (every path) and <prefix>.txt (the path list, then
start/end register pairs ranked by their worst slack). With a flop map
path, also writes every flip-flop instance of the netlist with its type,
RTL register name and src, one per line.
"""
import collections
import json
import re
import sys

POINT = re.compile(r'^[-\d.\s]*\s[\^v]\s+(\S+)/(\w+)\s+\((\w+)\)')


def parse_report(text):
    paths = []
    for block in text.split('Startpoint: ')[1:]:
        start = block.split()[0]
        m = re.search(r'Endpoint: (\S+)', block)
        s = re.search(r'(-?\d+\.\d+)\s+slack \((MET|VIOLATED)\)', block)
        g = re.search(r'Path Group: (\S+)', block)
        if not (m and s):
            continue
        arrival = block.split('data arrival time')[0]
        cells = []
        for line in arrival.splitlines():
            p = POINT.match(line)
            if p:
                inst, pin, master = p.groups()
                if not cells or cells[-1][0] != inst:
                    cells.append((inst, master, pin))
        paths.append(dict(start=start, end=m.group(1), slack=float(s.group(1)),
                          group=g.group(1) if g else None,
                          cells=[dict(inst=i, master=c, pin=p) for i, c, p in cells]))
    return paths


def base(name):
    return re.sub(r'\s*\[\d+\]$', '', name or '?')


def main():
    mapped, report, prefix = sys.argv[1:4]
    top = int(sys.argv[4]) if len(sys.argv) > 4 else 10
    flop_map = sys.argv[5] if len(sys.argv) > 5 else None
    paths = parse_report(open(report, errors='replace').read())
    wanted = set()
    for p in paths:
        wanted.add(p['start'])
        wanted.add(p['end'])
        wanted.add(p['end'].rsplit('/', 1)[0])
        wanted.update(c['inst'] for c in p['cells'])
    design = json.load(open(mapped))
    module = next(m for m in design['modules'].values() if m.get('attributes', {}).get('top'))
    cells = {}
    q_bits = {}
    for name, cell in module['cells'].items():
        if name in wanted or (flop_map and re.match(r'sg13g2_s?df', cell['type'])):
            outs = [b for pin, d in cell.get('port_directions', {}).items() if d == 'output'
                    for b in cell['connections'].get(pin, [])]
            if not outs:
                outs = [b for pin in ('Q', 'X', 'Y') for b in cell['connections'].get(pin, [])]
            cells[name] = dict(type=cell['type'], src=cell.get('attributes', {}).get('src'), out=outs)
            for b in outs:
                q_bits.setdefault(b, [])
    for net, row in module['netnames'].items():
        if row.get('hide_name') or net.startswith('$'):
            continue
        for i, b in enumerate(row['bits']):
            if b in q_bits:
                off = row.get('offset', 0)
                q_bits[b].append(net if len(row['bits']) == 1 else '%s[%d]' % (net, i + off))
    del design

    def rtl(inst):
        c = cells.get(inst)
        if c is None:
            return dict(rtl=None, src=None, type=None)
        names = sorted({n for b in c['out'] for n in q_bits.get(b, [])}, key=lambda n: ('.' not in n, len(n)))
        src = re.sub(r'^.*?/(hw/)', r'\1', c['src'] or '') or None
        return dict(rtl=names[0] if names else None, aliases=names[1:4], src=src, type=c['type'])

    if flop_map:
        with open(flop_map, 'w') as f:
            f.write('instance\ttype\trtl\tsrc\n')
            for name in sorted(cells):
                if re.match(r'sg13g2_s?df', cells[name]['type']):
                    r = rtl(name)
                    f.write('%s\t%s\t%s\t%s\n' % (name, r['type'], r['rtl'], r['src']))
    for p in paths:
        p['start_rtl'] = rtl(p['start'])
        p['end_rtl'] = rtl(p['end']) if p['end'] in cells else rtl(p['end'].rsplit('/', 1)[0])
        for c in p['cells']:
            c.update(rtl(c['inst']))
    json.dump(paths, open(prefix + '.json', 'w'), indent=1)
    out = []
    out.append('%d paths' % len(paths))
    out.append('')
    out.append('Worst paths (slack, start register -> end register, logic cells, cells):')
    for p in paths[:top]:
        logic = [c['master'] for c in p['cells'][1:] if not re.match(r'sg13g2_(buf|inv|dlygate)', c['master'])]
        out.append('%+.3f  %s -> %s  [%d logic]  %s' % (
            p['slack'], p['start_rtl']['rtl'] or p['start'], p['end_rtl']['rtl'] or p['end'], len(logic),
            ' '.join(c['master'].replace('sg13g2_', '') for c in p['cells'][1:])))
        for side in ('start_rtl', 'end_rtl'):
            if p[side].get('src'):
                out.append('        %s src %s' % (side[:-4], p[side]['src']))
    pairs = collections.OrderedDict()
    for p in paths:
        key = (base(p['start_rtl']['rtl'] or p['start']), base(p['end_rtl']['rtl'] or p['end']))
        if key not in pairs:
            pairs[key] = [p['slack'], 0]
        pairs[key][1] += 1
    out.append('')
    out.append('Register pairs by worst slack (worst slack, endpoint count in the report, start -> end):')
    for (s, e), (slack, n) in list(pairs.items())[:max(top, 20)]:
        out.append('%+.3f  %4d  %s -> %s' % (slack, n, s, e))
    open(prefix + '.txt', 'w').write('\n'.join(out) + '\n')
    print('\n'.join(out[:top * 3 + 30]))


if __name__ == '__main__':
    main()
