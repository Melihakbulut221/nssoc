# SPDX-FileCopyrightText: 2026 Hasan Melih Akbulut
# SPDX-License-Identifier: Apache-2.0
"""Attribute a completed KLayout DRC report against its actual vendor GDS cells.

Run in KLayout's Python interpreter:
  klayout -b -r classify_klayout_drc.py -rd run=/path/to/run -rd output=result.json
This reports provenance, not a waiver: every DRC marker remains an error.
"""
import collections
import hashlib
import json
import re
import xml.etree.ElementTree as ET
from pathlib import Path

import pya


def digest(path):
    h = hashlib.sha256()
    with path.open('rb') as stream:
        for block in iter(lambda: stream.read(1048576), b''):
            h.update(block)
    return h.hexdigest()


def classify(run_dir):
    run_dir = Path(run_dir)
    resolved = json.loads((run_dir / 'resolved.json').read_text())
    metrics = json.loads((run_dir / 'final/metrics.json').read_text())
    reports = list(run_dir.rglob('drc.klayout.lyrdb'))
    if len(reports) != 1:
        raise ValueError(f'Expected one completed DRC report, found {len(reports)}')
    report = reports[0]
    root = ET.parse(report).getroot()
    if root.tag != 'report-database':
        raise ValueError('Not a KLayout report database')
    items = root.findall('./items/item')
    if len(items) != metrics.get('klayout__drc_error__count'):
        raise ValueError('Report marker count does not match the native metric')
    files = sorted({Path(p) for macro in resolved['MACROS'].values()
                    for p in macro['gds']})
    if not files:
        raise ValueError('No vendor macro GDS declared in the measured config')
    vendor_cells = set()
    for path in files:
        layout = pya.Layout()
        layout.read(str(path))
        vendor_cells.update(cell.name for cell in layout.each_cell())
    counts, cells, outside = collections.Counter(), set(), collections.Counter()
    geometries = collections.defaultdict(set)
    for item in items:
        category = item.findtext('category').strip("'\"")
        cell = item.findtext('cell')
        values = tuple(v.text for v in item.findall('./values/value'))
        if not cell or not values:
            raise ValueError('Marker lacks its cell or geometry')
        counts[category] += 1
        cells.add(cell)
        geometries[category].add((cell, values))
        # KLayout deep mode creates orientation variants such as :m0/:r180.
        base = re.sub(r':(?:m|r)(?:0|90|180|270)$', '', cell)
        if base not in vendor_cells:
            outside[cell] += 1
    return {
        'report': str(report), 'report_sha256': digest(report),
        'drc_status': 'FAIL' if items else 'PASS',
        'markers': len(items),
        'distinct_cell_and_geometry': len(set().union(*geometries.values())),
        'by_category': dict(counts), 'cells_with_markers': len(cells),
        'nonvendor_cells': dict(outside), 'cells': sorted(cells),
        'sdiod_d_equals_e': bool(geometries.get('Sdiod.d')) and
                            geometries['Sdiod.d'] == geometries.get('Sdiod.e'),
        'vendor_cell_count': len(vendor_cells),
        'vendor_gds': [{'path': str(p), 'sha256': digest(p)} for p in files],
        'options': resolved.get('KLAYOUT_DRC_OPTIONS'),
        'scope': 'Cell attribution against declared macro GDS; no markers waived',
    }


if __name__ == '__main__':
    result = classify(run)
    Path(output).write_text(json.dumps(result, indent=2) + '\n')
    print(f"{result['markers']} markers; "
          f"{sum(result['nonvendor_cells'].values())} outside vendor cells; "
          f"DRC {result['drc_status']}")
