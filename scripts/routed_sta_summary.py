#!/usr/bin/env python3
# SPDX-FileCopyrightText: 2026 Hasan Melih Akbulut
# SPDX-License-Identifier: Apache-2.0
"""Summarise the routed measurement: per corner and clock group, from SPEF.

docs/combined-timing.md. Reads the run directory of
ReplayOnehotRoutedExtraction (AuditedRCX, AuditedRoutedSTA), the DRT step's
state of the routing run and the probe's flip-flop map. Writes
routed-summary.json and prints: the routing result (DRC markers), the gate
metrics per corner, the worst setup and hold slack per path group and corner
(from the full max/min reports), and the worst path of each group at the
slow corner by RTL register.
"""
import collections
import gzip
import json
import re
import sys
from pathlib import Path

CORNERS = ['nom_slow_1p08V_125C', 'nom_typ_1p20V_25C', 'nom_fast_1p32V_m40C']


def paths(report):
    rows, cur = [], None
    with open(report, errors='replace') as f:
        for line in f:
            s = line.strip()
            if s.startswith('Startpoint:'):
                cur = {'start': s.split()[1]}
            elif cur is None:
                continue
            elif s.startswith('Endpoint:'):
                cur['end'] = s.split()[1]
            elif s.startswith('Path Group:'):
                cur['group'] = s.split(':', 1)[1].strip()
            elif s.endswith('slack (VIOLATED)') or s.endswith('slack (MET)'):
                try:
                    cur['slack'] = float(s.split()[0])
                except ValueError:
                    pass
                rows.append(cur)
                cur = None
    return rows


def flop_names(path):
    names = {}
    if not path or not Path(path).exists():
        return names
    opener = gzip.open if str(path).endswith('.gz') else open
    with opener(path, 'rt') as f:
        for line in f:
            c = line.rstrip('\n').split('\t')
            if len(c) >= 3 and c[0] != 'instance' and c[2] not in ('', 'None'):
                names[c[0]] = c[2]
    return names


def main(sta_run, route_state, flop_map, out):
    sta_run, route_state = Path(sta_run), Path(route_state)
    names = flop_names(flop_map)
    rtl = lambda p: names.get(p.split('/')[0], p.split('/')[0])
    result = {}
    state = json.loads(route_state.read_text())
    result['route'] = {k: v for k, v in state.get('metrics', {}).items()
                       if k.startswith(('route__', 'antenna__'))}
    sta, = [d for d in sta_run.glob('*onehotroutedsta*')]
    metrics = json.loads((sta / 'state_out.json').read_text())['metrics']
    result['corners'] = {}
    for c in CORNERS:
        entry = {'metrics': {k.split('__corner:')[0]: v for k, v in metrics.items() if k.endswith('__corner:' + c)}}
        for kind in ('max', 'min'):
            rows = paths(sta / c / f'{kind}.rpt')
            worst = {}
            for r in rows:
                g = r.get('group', '?')
                if 'slack' in r and (g not in worst or r['slack'] < worst[g]['slack']):
                    worst[g] = dict(r, start_rtl=rtl(r['start']), end_rtl=rtl(r.get('end', '?')))
            entry[kind] = worst
            entry[kind + '_paths_in_report'] = len(rows)
            entry[kind + '_violating_by_group'] = dict(collections.Counter(
                r.get('group') for r in rows if r.get('slack', 0) < 0))
        result['corners'][c] = entry
    Path(out).write_text(json.dumps(result, indent=1, sort_keys=True) + '\n')
    print('routing:', json.dumps(result.get('route', {})))
    for c in CORNERS:
        e = result['corners'][c]
        print(c, {k: e['metrics'].get(k) for k in ('timing__setup__ws', 'timing__hold__ws', 'timing__setup_vio__count', 'timing__hold_vio__count')})
    groups = sorted({g for c in CORNERS for k in ('max', 'min') for g in result['corners'][c][k]})
    print('\nworst slack (ns) per group: setup slow/typ/fast | hold slow/typ/fast')
    for g in groups:
        cells = []
        for kind in ('max', 'min'):
            cells.append(' / '.join(
                f"{result['corners'][c][kind][g]['slack']:.2f}" if g in result['corners'][c][kind] else '-'
                for c in CORNERS))
        print(f'  {g:16s} {cells[0]:24s} | {cells[1]}')
    print('\nworst slow-corner setup path per group (start -> end)')
    for g, r in sorted(result['corners'][CORNERS[0]]['max'].items(), key=lambda x: x[1]['slack']):
        print(f"  {g:16s} {r['slack']:.3f}  {r['start_rtl']} -> {r['end_rtl']}")
    print('\nworst slow-corner hold path per group (start -> end)')
    for g, r in sorted(result['corners'][CORNERS[0]]['min'].items(), key=lambda x: x[1]['slack']):
        print(f"  {g:16s} {r['slack']:.3f}  {r['start_rtl']} -> {r['end_rtl']}")
    return 0


if __name__ == '__main__':
    raise SystemExit(main(*sys.argv[1:5]))
