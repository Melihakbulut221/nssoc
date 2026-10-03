#!/usr/bin/env python3
# SPDX-FileCopyrightText: 2026 Hasan Melih Akbulut
# SPDX-License-Identifier: Apache-2.0
"""Render a run's measured placement without historical full3 annotations."""
import argparse
import hashlib
import json
import math
from html import escape
from pathlib import Path

from floorplan_map import LOGIC, _density, check_classes, extract, self_check


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--run', type=Path, required=True)
    parser.add_argument('--svg', type=Path, required=True)
    parser.add_argument('--json', type=Path, required=True)
    args = parser.parse_args()
    for relative in ('resolved.json', 'final/def/soc_top.def', 'final/metrics.json'):
        if not (args.run / relative).is_file():
            parser.error(f'Missing completed-run input: {args.run / relative}')
    e, _ = extract(str(args.run))
    x0, y0, x1, y1 = e['die_um']
    scale = 860 / (x1-x0)
    top, left = 130, 60
    height = (y1-y0)*scale
    legend_rows = math.ceil(len(e['macros']) / 2)
    page_height = height + top + max(180, 80 + legend_rows * 20)
    def x(v):
        return left+(v-x0)*scale
    def y(v):
        return top+(y1-v)*scale
    def rect(ax, ay, width, h, color, extra=''):
        return (f'<rect x="{x(ax):.2f}" y="{y(ay+h):.2f}" '
                f'width="{width*scale:.2f}" height="{h*scale:.2f}" '
                f'fill="{color}" {extra}/>')
    def text(px, py, label, size=15, extra=''):
        return f'<text x="{px}" y="{py}" font-size="{size}" {extra}>{escape(label)}</text>'
    svg = [f'<svg xmlns="http://www.w3.org/2000/svg" width="980" height="{page_height:.0f}" viewBox="0 0 980 {page_height:.0f}" font-family="sans-serif" fill="#172b3a">',
           '<rect width="100%" height="100%" fill="#f5f7fa"/>',
           text(60, 45, 'soc_top · measured placement', 27, 'font-weight="bold"'),
           text(60, 75, args.run.name),
           text(60, 101, f'{x1-x0:.1f} × {y1-y0:.1f} µm · {len(e["macros"])} SRAM macros · {sum(e["counts"].values()):,} placed instances'),
           rect(x0, y0, x1-x0, y1-y0, '#ffffff', 'stroke="#20374a" stroke-width="1.5"')]
    cells = [r for kind in LOGIC for r in e['_rects'][kind]]
    grid, _, _, _, _ = _density(cells, e, 20)
    for (ix, iy), density in sorted(grid.items()):
        shade = min(1, max(0, density))
        color = '#%02x%02x%02x' % (int(220-195*shade), int(241-125*shade), int(245-105*shade))
        ax, ay = x0+20*ix, y0+20*iy
        svg.append(rect(ax, ay, min(20, x1-ax), min(20, y1-ay), color))
    for i, m in enumerate(e['macros'], 1):
        svg.append(rect(m['x_um'], m['y_um'], m['w_um'], m['h_um'], '#e5ba66', 'stroke="#755722" stroke-width="1"'))
        svg.append(text(x(m['x_um']+m['w_um']/2), y(m['y_um']+m['h_um']/2), str(i), 23, 'text-anchor="middle" font-weight="bold"'))
    footer = top+height+28
    svg.append(text(60, footer, 'Teal: logic-cell density (20 µm bins). Gold: LEF macro footprints.', 14))
    svg.append(text(60, footer+23, 'Placement view only; routing is hidden. This image is not physical signoff.', 14))
    for i, m in enumerate(e['macros'], 1):
        column, row = (i-1)//legend_rows, (i-1)%legend_rows
        label = m['instance'].replace('u_ram.g_ram_2048x64_ecc.', 'RAM ').replace('u_rom.g_rom_1024x32_ecc.', 'ROM ')
        label = label.replace('u_eth.u_mac.rx_fifo.fifo_inst.mem.0.', 'ETH RX bank ')
        label = label.replace('u_eth.u_mac.tx_fifo.fifo_inst.mem.0.', 'ETH TX bank ')
        svg.append(text(60+column*430, footer+50+row*20, f'{i}. {label}', 13))
    svg.append('</svg>')
    checks = [(name.replace('six rectangles', 'macro rectangles'), ok, detail)
              for name, ok, detail in self_check(e)]
    for name, observed, expected in check_classes(e, str(args.run)):
        # OpenROAD serializes these area metrics to six significant digits;
        # compare within that rounding unit, retaining exact count checks.
        tolerance = 0
        if 'um2' in name and expected is not None:
            tolerance = max(1, 0.5 * 10 ** (math.floor(math.log10(max(1, abs(expected)))) - 5))
        ok = expected is not None and abs(observed-expected) <= tolerance
        checks.append((name, ok, f'DEF/LEF={observed}, tool={expected}'))
    bad = [c for c in checks if not c[1]]
    if bad:
        raise SystemExit(f'Layout geometry/metric checks failed: {bad}')
    record = {k: e[k] for k in ('source_def', 'die_um', 'core_um', 'macros', 'counts', 'declared')}
    record['def_sha256'] = hashlib.sha256(Path(e['source_def']).read_bytes()).hexdigest()
    record['checks'] = checks
    args.svg.parent.mkdir(parents=True, exist_ok=True)
    args.json.parent.mkdir(parents=True, exist_ok=True)
    args.svg.write_text('\n'.join(svg)+'\n')
    args.json.write_text(json.dumps(record, indent=2)+'\n')
    print(f'{args.svg}: {len(checks)} geometry/metric checks passed')


if __name__ == '__main__':
    main()
