#!/usr/bin/env python3
# SPDX-FileCopyrightText: 2026 Hasan Melih Akbulut
# SPDX-License-Identifier: Apache-2.0
"""Assemble full vendor CDL beneath a powered OpenROAD implementation netlist.

Yosys is used only as a Verilog connectivity reader, without optimization. Its
temporary blackbox interfaces are replaced by the original transistor CDL in
the output. This creates the schematic side of LVS, not an LVS verdict.
Unsupported directives, missing inputs and ambiguous connectivity fail closed.
"""
import argparse
import hashlib
import json
from pathlib import Path
import re
import subprocess


def digest(path):
    with Path(path).open('rb') as stream:
        return hashlib.file_digest(stream, 'sha256').hexdigest()


def read_cdl(paths):
    definitions, ports = {}, {}
    pattern = re.compile(r'^\.SUBCKT\b.*?^\.ENDS[^\n]*', re.M | re.S | re.I)
    for path in paths:
        content = Path(path).read_text()
        chunks = pattern.findall(content)
        outside = pattern.sub('', content)
        if not chunks or any(line.strip() and not line.lstrip().startswith('*')
                             for line in outside.splitlines()):
            raise ValueError('Unsupported CDL outside subcircuits: ' + str(path))
        for chunk in chunks:
            logical = re.sub(r'\n\s*\+\s*', ' ', chunk)
            header = logical.splitlines()[0].split()
            name = header[1]
            if not re.fullmatch(r'\w+', name) or len(set(header[2:])) != len(header[2:]):
                raise ValueError('Ambiguous CDL name or duplicate port: ' + name)
            existing = next((n for n in definitions if n.casefold() == name.casefold()), None)
            if existing is not None:
                old = re.sub(r'\n\s*\+\s*', ' ', definitions[existing])
                if existing != name or re.sub(r'\s+', ' ', old) != re.sub(r'\s+', ' ', logical):
                    raise ValueError('Conflicting CDL definition: ' + name)
            else:
                definitions[name], ports[name] = chunk, header[2:]
    return definitions, ports


def port_groups(pins):
    groups = {}
    for pin in pins:
        match = re.fullmatch(r'(.+)<(\d+)>', pin)
        base, index = (match[1], int(match[2])) if match else (pin, None)
        groups.setdefault(base, []).append(index)
    for base, indices in groups.items():
        if indices != [None] and (None in indices or
                sorted(indices) != list(range(min(indices), max(indices) + 1))):
            raise ValueError('Noncontiguous or mixed CDL bus: ' + base)
    return groups


def reachable_cdl(definitions, roots):
    """Keep verbatim device bodies reachable from the actual implementation.

    Uninstantiated library helpers are not additional schematic top circuits.
    Reject unresolved/recursive/parameterized calls rather than dropping them.
    """
    names = {name.casefold(): name for name in definitions}
    reachable, active = set(), set()

    def visit(requested):
        name = names.get(requested.casefold())
        if name is None:
            raise ValueError('Unresolved CDL subcircuit: ' + requested)
        if name in active:
            raise ValueError('Recursive CDL hierarchy: ' + name)
        if name in reachable:
            return
        active.add(name)
        logical = re.sub(r'\n\s*\+\s*', ' ', definitions[name])
        for line in logical.splitlines():
            fields = line.split()
            if fields and fields[0].upper().startswith('X'):
                if len(fields) < 3 or any('=' in field for field in fields):
                    raise ValueError('Unsupported parameterized CDL call: ' + line)
                visit(fields[-1])
        active.remove(name)
        reachable.add(name)

    for name in roots:
        visit(name)
    return {name: body for name, body in definitions.items() if name in reachable}


def interfaces(types, ports):
    lines = []
    for name in sorted(types):
        groups = port_groups(ports[name])
        lines.append('(* blackbox *) module ' + name + ' (' +
                     ', '.join('\\' + base + ' ' for base in groups) + ');')
        for base, indices in groups.items():
            width = '' if indices == [None] else f'[{max(indices)}:{min(indices)}] '
            lines.append('inout ' + width + '\\' + base + ' ;')
        lines.append('endmodule')
    return '\n'.join(lines) + '\n'


def declared_outputs(verilog):
    """Only scalar output declarations in the pinned vendor model are accepted."""
    result = {}
    for module in re.finditer(r'module\s+(\w+)\s*\(.*?endmodule', verilog, re.S):
        result[module[1]] = set(re.findall(r'\boutput\s+(\w+)\s*;', module[0]))
    return result


def assemble(module, top, ports, outputs):
    names, top_pins = {}, []
    for port, value in module['ports'].items():
        if not re.fullmatch(r'[A-Za-z_][\w$]*', port):
            raise ValueError('Unsupported top port name: ' + port)
        for index, bit in enumerate(value['bits']):
            # Reject opposite bus orientations until explicitly supported.
            if value.get('upto', 0):
                raise ValueError('Ascending top port is unsupported')
            name = port if len(value['bits']) == 1 else f"{port}[{index + value.get('offset', 0)}]"
            if type(bit) is not int or bit in names:
                raise ValueError('Constant or aliased top ports')
            names[bit] = name
            top_pins.append(name)
    reserved = set(top_pins)

    def net(bit):
        if type(bit) is not int:
            raise ValueError('Constant/unknown connection requires explicit tie cell')
        name = names.get(bit, 'n' + str(bit))
        if bit not in names and name in reserved:
            raise ValueError('Generated net collides with top port')
        return name

    body, floating = ['.SUBCKT ' + top + ' ' + ' '.join(top_pins)], []
    for index, (inst, cell) in enumerate(module['cells'].items()):
        typ, connections = cell['type'], cell['connections']
        if typ not in ports or cell.get('parameters'):
            raise ValueError('Missing CDL type or parameterized instance: ' + inst)
        groups = port_groups(ports[typ])
        absent = set(groups) - set(connections)
        if set(connections) - set(groups) or absent - outputs.get(typ, set()):
            raise ValueError('Missing input/power or extra port: ' + inst)
        args = []
        for pin in ports[typ]:
            match = re.fullmatch(r'(.+)<(\d+)>', pin)
            base, offset = (match[1], int(match[2]) - min(groups[match[1]])) if match else (pin, 0)
            if base in absent:
                if groups[base] != [None]:
                    raise ValueError('Missing bus output is unsupported')
                node = f'float_{index}_{base}'
                if node in reserved:
                    raise ValueError('Floating net collides with top port')
                floating.append({'instance': inst, 'type': typ, 'output': base})
                args.append(node)
            else:
                if len(connections[base]) != len(groups[base]):
                    raise ValueError('Connection width mismatch: ' + inst + ' ' + base)
                args.append(net(connections[base][offset]))
        body.append('X' + str(index) + ' ' + ' '.join(args) + ' ' + typ)
    body.append('.ENDS ' + top)
    return '\n'.join(body) + '\n', floating


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('powered_netlist', type=Path)
    parser.add_argument('--top', required=True)
    parser.add_argument('--cdl', type=Path, action='append', required=True)
    parser.add_argument('--standard-cell-verilog', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    if not re.fullmatch(r'[A-Za-z_]\w*', args.top):
        parser.error('Unsupported top identifier')
    inputs = [args.powered_netlist, *args.cdl, args.standard_cell_verilog, Path(__file__)]
    expected = {str(p.resolve()): digest(p) for p in inputs}
    definitions, ports = read_cdl(args.cdl)
    text = args.powered_netlist.read_text()
    types = set(re.findall(r'^\s*((?:sg13g2_|RM_IHPSG13_)\w+)\s+(?:\\\S+|\w+)\s*\(', text, re.M))
    if not types or types - set(ports):
        parser.error('Missing used-cell CDL')
    output = args.output.resolve()
    output.mkdir(parents=True, exist_ok=False)
    (output / 'interfaces.v').write_text(interfaces(types, ports))
    def quote(path):
        return '"' + str(path).replace('\\', '\\\\').replace('"', '\\"') + '"'
    script = (f'read_verilog -lib {quote(output / "interfaces.v")}\n'
              f'read_verilog {quote(args.powered_netlist.resolve())}\n'
              f'hierarchy -check -top {args.top}\nwrite_json {quote(output / "powered.json")}\n')
    (output / 'read.ys').write_text(script)
    with (output / 'yosys.log').open('w') as stream:
        subprocess.run(['yosys', '-s', str(output / 'read.ys')], stdout=stream,
                       stderr=subprocess.STDOUT, check=True)
    module = json.loads((output / 'powered.json').read_text())['modules'][args.top]
    body, floating = assemble(module, args.top, ports,
                              declared_outputs(args.standard_cell_verilog.read_text()))
    selected = reachable_cdl(definitions, {cell['type'] for cell in module['cells'].values()})
    if any(digest(p) != sha for p, sha in expected.items()):
        raise ValueError('Source changed during schematic construction')
    schematic = output / 'schematic.cir'
    schematic.write_text('* Original vendor transistor CDL and powered implementation connectivity\n' +
                         '\n'.join(selected.values()) + '\n' + body)
    (output / 'sources.json').write_text(json.dumps({
        'scope': 'Source-side full transistor schematic; requires separate extracted LVS',
        'top': args.top, 'instances': len(module['cells']), 'cdl_definitions': len(selected),
        'excluded_uninstantiated_definitions': sorted(set(definitions) - set(selected)),
        'floating_outputs': floating, 'sources': expected,
        'schematic_sha256': digest(schematic),
    }, indent=2) + '\n')
    print(schematic)


if __name__ == '__main__':
    main()
