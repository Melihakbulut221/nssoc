#!/usr/bin/env python3
# SPDX-FileCopyrightText: 2026 Hasan Melih Akbulut
# SPDX-License-Identifier: Apache-2.0
"""Name the probe's worst paths after the uncapped repair by RTL register.

Reads the deep-repair log of the implementation probe (its per-corner group
summaries and, with path_nets, the NSSOC_NETS section of ten worst slow-corner
paths per group) and the flip-flop map written by
scripts/pcie_timing/trace_paths.py (instance -> RTL register, plain or gzip).
Prints the worst setup slack per corner and group, then every named path:
group, slack, start register, end register (docs/combined-timing.md).
"""
import gzip
import re
import sys
from pathlib import Path


def load_map(path):
    opener = gzip.open if str(path).endswith('.gz') else open
    names = {}
    with opener(path, 'rt') as f:
        for line in f:
            cols = line.rstrip('\n').split('\t')
            if len(cols) >= 3 and cols[0] != 'instance' and cols[2] not in ('', 'None'):
                names[cols[0]] = cols[2]
    return names


def main():
    log, flop_map = Path(sys.argv[1]), Path(sys.argv[2])
    names = load_map(flop_map)
    lines = log.read_text(errors='replace').split('\n')
    ff_net = {}
    for line in lines:
        if line.startswith('NSSOC_FF '):
            _, cell, net = line.split(' ', 2)
            ff_net[cell] = net

    def rtl(point):
        inst = point.split('/')[0]
        return names.get(inst) or ff_net.get(inst) or inst

    # Worst setup slack per corner and group (the first endpoint of each group).
    corner = None
    group = None
    print('worst setup slack after the repair (ns)')
    for line in lines:
        m = re.match(r'NSSOC_DEEP_CORNER_BEGIN (\S+)', line)
        if m:
            corner = m.group(1)
            continue
        if line.startswith('NSSOC_DEEP_CORNER_END'):
            corner = None
            continue
        m = re.match(r'(max_delay/setup|min_delay/hold) group (.+)$', line)
        if m and corner:
            group = (m.group(1), m.group(2).strip())
            continue
        m = re.search(r'\s(-?\d+\.\d+) \((VIOLATED|MET)\)\s*$', line)
        if m and corner and group:
            if group[0] == 'max_delay/setup':
                print(f'  {corner:24s} {group[1]:16s} {float(m.group(1)):8.2f}')
            group = None

    if 'NSSOC_NETS_BEGIN' not in lines:
        print('no NSSOC_NETS section (path_nets was off)')
        return 0
    start, end = lines.index('NSSOC_NETS_BEGIN'), lines.index('NSSOC_NETS_END')
    paths, cur = [], None
    for line in lines[start:end]:
        if line.startswith('Startpoint:'):
            cur = {'start': line.split()[1]}
            paths.append(cur)
        elif cur is None:
            continue
        elif line.startswith('Endpoint:'):
            cur['end'] = line.split()[1]
        elif line.startswith('Path Group:'):
            cur['group'] = line.split(':', 1)[1].strip()
        elif 'slack' in line and 'slack' not in cur:
            m = re.match(r'\s*(-?\d+\.\d+)\s+slack', line)
            if m:
                cur['slack'] = float(m.group(1))
    print('\nworst slow-corner paths per group (group, slack, start -> end)')
    for p in paths:
        print(f"{p.get('group', '?')}\t{p.get('slack', float('nan')):.3f}\t"
              f"{rtl(p['start'])}\t->\t{rtl(p.get('end', '?'))}")
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
