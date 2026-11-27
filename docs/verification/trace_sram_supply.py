# SPDX-FileCopyrightText: 2026 Hasan Melih Akbulut
# SPDX-License-Identifier: Apache-2.0
import collections
import pathlib
import re
import sys

def trace(path, top):
    text = pathlib.Path(path).read_text()
    lines = re.sub(r'\n\s*\+\s*', ' ', text).upper().splitlines()
    cells = {}
    for line in lines:
        words = line.split()
        if not words:
            continue
        if words[0] == '.SUBCKT':
            name = words[1]
            pins = words[2:]
            instances = []
            cells[name] = pins, instances
        elif words[0].startswith('X'):
            instances.append(words)
    leaf = 'RSC_IHPSG13_CDLYX1_DUMMY'
    counts = collections.Counter()
    examples = {}
    def walk(name, mapping, route):
        if name == leaf:
            pins = cells[name][0]
            rails = tuple(mapping[p] for p in pins if p not in ('A', 'Z'))
            counts[rails] += 1
            examples.setdefault(rails, '/'.join(route))
            return
        for row in cells[name][1]:
            master = row[-1]
            if master not in cells:
                raise ValueError(row)
            ports = cells[master][0]
            nets = row[1:-1]
            if nets and nets[-1] == '/':
                nets.pop()
            assert len(ports) == len(nets), (name, row[0], master, len(ports), len(nets))
            args = {p: mapping.get(n, '/'.join((*route, n))) for p,n in zip(ports,nets)}
            walk(master, args, (*route,row[0]))
    pins = cells[top][0]
    walk(top, {p:p for p in pins}, (top,))
    print(path, cells[leaf][0], counts, examples)
trace(sys.argv[1],sys.argv[2].upper())
