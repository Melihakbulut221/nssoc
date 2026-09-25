#!/usr/bin/env python3
# SPDX-FileCopyrightText: 2026 Hasan Melih Akbulut
# SPDX-License-Identifier: Apache-2.0
"""Inline named CDL helpers without changing transistor nodes or parameters.

This is a source-side hierarchy transformation, not an extraction, LVS waiver
or replacement of the independent schematic with an extracted netlist.
"""
import argparse
import json
from pathlib import Path
import re

from transistor_schematic import read_cdl, reachable_cdl


PREFIX = '__cdl_inline_'


def inline(definitions, ports, selected):
    names = {name.casefold(): name for name in definitions}
    wanted = {name.casefold() for name in selected}
    if not wanted or not wanted <= names.keys():
        raise ValueError('Missing or empty helper selection')
    bodies = {}
    for name, text in definitions.items():
        lines = re.sub(r'\n\s*\+\s*', ' ', text).splitlines()
        body = [line.split() for line in lines[1:-1]
                if line.strip() and not line.lstrip().startswith('*')]
        instances = [row[0].casefold() for row in body]
        rewritten = instances if name.casefold() in wanted else [
            row[0].casefold() for row in body
            if row[0].upper().startswith('X') and row[-1].casefold() in wanted]
        if any(instances.count(instance) != 1 for instance in rewritten):
            raise ValueError('Duplicate instance: ' + name)
        if any(token.casefold().startswith(PREFIX) for row in body for token in row) or any(
                row[0][1:].casefold().startswith(PREFIX) for row in body):
            raise ValueError('Reserved namespace collision')
        if len({pin.casefold() for pin in ports[name]}) != len(ports[name]):
            raise ValueError('Ambiguous case-insensitive ports')
        bodies[name] = body

    def unique(kind, path):
        return PREFIX + kind + json.dumps(path, separators=(',', ':')).encode().hex()

    def expand(name, connections, path, active):
        if name in active:
            raise ValueError('Recursive helper: ' + name)
        if len(connections) != len(ports[name]):
            raise ValueError('Wrong helper pin count: ' + name)
        bindings = {pin.casefold(): net for pin, net in zip(ports[name], connections)}

        def net(token):
            key = token.casefold()
            if key == '0':
                return '0'
            return bindings.get(key, unique('n', [*path, key]))

        rows = []
        for fields in bodies[name]:
            instance = fields[0].casefold()
            kind = instance[0]
            if kind == 'm':
                if len(fields) < 6 or any('=' in token for token in fields[1:6]):
                    raise ValueError('Unsupported MOS syntax')
                rows.append(['M' + unique('i', [*path, instance]),
                             *(net(token) for token in fields[1:5]), *fields[5:]])
            elif kind == 'x':
                target = names.get(fields[-1].casefold())
                if target is None or any('=' in token for token in fields):
                    raise ValueError('Unsupported or unresolved subcircuit')
                nodes = [net(token) for token in fields[1:-1]]
                if target.casefold() in wanted:
                    rows.extend(expand(target, nodes, [*path, instance], active | {name}))
                else:
                    if len(nodes) != len(ports[target]):
                        raise ValueError('Wrong nested pin count')
                    rows.append(['X' + unique('i', [*path, instance]), *nodes, fields[-1]])
            else:
                raise ValueError('Unsupported helper statement: ' + fields[0])
        return rows

    output = {}
    for name, text in definitions.items():
        if name.casefold() in wanted:
            continue
        lines = re.sub(r'\n\s*\+\s*', ' ', text).splitlines()
        changed = False
        result = [lines[0]]
        for line in lines[1:-1]:
            fields = line.split()
            if fields and fields[0].upper().startswith('X') and fields[-1].casefold() in wanted:
                if any('=' in token for token in fields):
                    raise ValueError('Parameterized helper instance')
                target = names[fields[-1].casefold()]
                result.extend(' '.join(row) for row in expand(
                    target, fields[1:-1], [fields[0].casefold()], set()))
                changed = True
            else:
                result.append(line)
        result.append(lines[-1])
        output[name] = '\n'.join(result) if changed else text
    reachable_cdl(output, output.keys())
    return output


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('source', type=Path)
    parser.add_argument('--cell', action='append', required=True)
    parser.add_argument('--output', required=True, type=Path)
    args = parser.parse_args()
    definitions, ports = read_cdl([args.source])
    result = inline(definitions, ports, args.cell)
    with args.output.open('x') as stream:
        stream.write('\n\n'.join(result.values()) + '\n')


if __name__ == '__main__':
    main()
