#!/usr/bin/env python3
# SPDX-FileCopyrightText: 2026 Hasan Melih Akbulut
# SPDX-License-Identifier: Apache-2.0
"""Audit a KLayout LVS database and deck verdict instead of trusting exit zero.

Requires the optional klayout Python module. The caller must independently
check process completion and input identities. This audits comparison results,
not extraction-rule adequacy, blackbox policy or fabrication acceptance.
"""
import argparse
from collections import Counter
import hashlib
import json
from pathlib import Path


def read_pairs(report, extraction_diagnostics=None):
    import klayout.db as db

    lvs = db.LayoutVsSchematic()
    lvs.read(str(report))
    if extraction_diagnostics is not None:
        extraction_diagnostics.extend(
            {'severity': str(entry.severity), 'category': entry.category_name,
             'cell': entry.cell_name, 'net': entry.net_name,
             'message': entry.message}
            for entry in lvs.each_log_entry())
    xref = lvs.xref()
    if xref is None:
        raise ValueError('Database contains no comparison cross-reference')

    def devices(circuit, cache, active):
        if circuit is None:
            return 0
        name = circuit.name
        if name in active:
            raise ValueError('Recursive circuit hierarchy: ' + name)
        if name not in cache:
            cache[name] = sum(1 for _ in circuit.each_device()) + sum(
                devices(sub.circuit_ref(), cache, active | {name})
                for sub in circuit.each_subcircuit())
        return cache[name]

    layout_cache, schematic_cache = {}, {}
    rows = []
    for pair in xref.each_circuit_pair():
        first, second = pair.first(), pair.second()
        rows.append({
            'layout': first.name if first is not None else None,
            'schematic': second.name if second is not None else None,
            'status': str(pair.status()),
            'layout_devices_recursive': devices(first, layout_cache, set()),
            'schematic_devices_recursive': devices(second, schematic_cache, set()),
        })
    return rows


def assess(rows, top, deck_log, extraction_diagnostics=()):
    extraction_diagnostics = list(extraction_diagnostics)
    reasons = []
    if not rows:
        reasons.append('Empty circuit comparison')
    # Spice readers may uppercase names. Layout names must identify the exact
    # requested top; ambiguous matches or a missing reference fail closed.
    tops = [r for r in rows if r['layout'] == top and
            (r['schematic'] or '').casefold() == top.casefold()]
    if len(tops) != 1:
        reasons.append('Expected exactly one compared top circuit')
    elif min(tops[0]['layout_devices_recursive'],
             tops[0]['schematic_devices_recursive']) <= 0:
        reasons.append('Top has no compared primitive devices')
    if any(r['status'] != 'Match' or not r['layout'] or not r['schematic']
           for r in rows):
        reasons.append('Non-matching, skipped, missing or warning circuit')
    # flag_missing_ports may fail after compare(), so the database alone is
    # insufficient. Require the strict deck's explicit final success as well.
    if 'INFO : Congratulations! Netlists match.' not in deck_log:
        reasons.append('Missing explicit successful deck verdict')
    if "ERROR : Netlists don't match" in deck_log:
        reasons.append('Deck explicitly reported a mismatch')
    # KLayout can report all circuit pairs as Match and print a successful
    # verdict while retaining a must-connect open in the database's extraction
    # log. It need not appear in the text log. Never discard those diagnostics.
    if any(entry.get('severity') != 'Info' or entry.get('category') == 'must-connect'
           for entry in extraction_diagnostics):
        reasons.append('Unresolved extraction warning, error or must-connect requirement')
    return {'status': 'FAIL' if reasons else 'PASS within comparison scope',
            'top': top, 'reasons': reasons,
            'extraction_diagnostics': list(extraction_diagnostics),
            'circuit_status_counts': dict(Counter(r['status'] for r in rows)),
            'circuits': rows}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('report', type=Path)
    parser.add_argument('--top', required=True)
    parser.add_argument('--deck-log', required=True, type=Path)
    parser.add_argument('--output', required=True, type=Path)
    args = parser.parse_args()
    try:
        diagnostics = []
        rows = read_pairs(args.report, diagnostics)
        result = assess(rows, args.top, args.deck_log.read_text(), diagnostics)
        result['inputs'] = {}
        for p in (args.report, args.deck_log):
            with p.open('rb') as stream:
                digest = hashlib.file_digest(stream, 'sha256').hexdigest()
            result['inputs'][str(p)] = {'bytes': p.stat().st_size, 'sha256': digest}
        with args.output.open('x') as stream:
            json.dump(result, stream, indent=2)
            stream.write('\n')
    except (OSError, ValueError, RuntimeError, ImportError) as error:
        parser.exit(2, str(error) + '\n')
    print(result['status'])
    raise SystemExit(1 if result['reasons'] else 0)


if __name__ == '__main__':
    main()
