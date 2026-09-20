#!/usr/bin/env python3
# SPDX-FileCopyrightText: 2026 Hasan Melih Akbulut
# SPDX-License-Identifier: Apache-2.0
"""Check restricted flat OpenROAD sizing/buffer ECOs against pinned inputs.

Requires unchanged original instances, ports, aliases and original pin nets
after contracting non-inverting buffers and stateless delay cells. Substituted cells must have identical
Liberty pin functions and complete ff/latch state declarations. Added buffers
must form singly driven acyclic branches. SRAM bus directions come only from
explicitly hash-pinned macro libraries; no installed-PDK discovery is implicit.

This is a structural combinational/sequential-function check, not delay/SDF,
power-up, analog, memory-interior, timing or whole-core formal verification.
Only the emitted OpenROAD syntax is accepted; unsupported inputs fail closed.
"""
import functools
import hashlib
import json
from pathlib import Path
import re
NET = '(?:\\\\\\S+|[A-Za-z_$][\\w$]*)(?:\\s*\\[\\d+\\])?'

def parse(path):
    text = Path(path).read_text()
    cells = {}
    decl = []
    assign = []
    for raw in text.split(';'):
        s = raw.strip()
        if not s or s == 'endmodule':
            continue
        if re.match('^(module|input|output|inout)\\b', s):
            decl.append(re.sub('\\s+', ' ', s))
            continue
        if re.match('^wire\\b', s):
            continue
        if re.match('^assign\\b', s):
            assign.append(re.sub('\\s+', ' ', s))
            continue
        m = re.fullmatch('(\\w+)\\s+(\\\\\\S+|\\w+)\\s+\\((.*)\\)', s, re.S)
        if not m:
            raise ValueError(('Unparsed statement', s[:120]))
        master, name, body = m.groups()
        pins = {}
        matches = list(re.finditer('\\.([A-Za-z_]\\w*)\\s*\\(([^()]*)\\)', body))
        tail = 0
        for match in matches:
            if body[tail:match.start()].strip() not in ('', ','):
                raise ValueError(body[tail:match.start()])
            pin, value = match.groups()
            if pin in pins:
                raise ValueError('Unsupported or inconsistent ECO input')
            pins[pin] = re.sub('\\s+', ' ', value.strip())
            tail = match.end()
        if body[tail:].strip():
            raise ValueError(body[tail:])
        if name in cells:
            raise ValueError('Unsupported or inconsistent ECO input')
        cells[name] = (master, pins)
    return (cells, decl, assign)

def check(before, after, inputs):
    if hashlib.sha256(Path(before).read_bytes()).hexdigest() != inputs['before_sha256']:
        raise ValueError('Before netlist hash mismatch')
    if hashlib.sha256(Path(after).read_bytes()).hexdigest() != inputs['after_sha256']:
        raise ValueError('After netlist hash mismatch')
    a, ports, assign = parse(before)
    b, p2, as2 = parse(after)
    if not (ports == p2 and assign == as2):
        raise ValueError('Interface/alias changed')
    # Ignoring declaration widths could conceal truncation or a changed bus
    # orientation even when every textual cell connection still matches.
    def wires(path):
        return {re.sub(r'\s+', ' ', raw.strip()) for raw in Path(path).read_text().split(';')
                if re.match(r'^\s*wire\b', raw)}
    old_wires, new_wires = wires(before), wires(after)
    if not old_wires <= new_wires:
        raise ValueError('Original wire declaration changed or removed')
    if not set(a) <= set(b):
        raise ValueError('Original instances removed')
    added = set(b) - set(a)
    if len(added) != len(inputs['new_buffer_drivers']):
        raise ValueError('Unsupported or inconsistent ECO input')
    original_nets = set()
    for _, pins in a.values():
        for value in pins.values():
            original_nets.update(re.findall(NET, value))
    graph = {}
    for name in added:
        master, pins = b[name]
        if not (re.fullmatch(r'sg13g2_(?:buf_(?:1|2|4|8|16)|dlygate4sd[123]_1)', master)
                and set(pins) == {'A', 'X'}):
            raise ValueError((name, master, pins))
        for value in pins.values():
            if not re.fullmatch(NET, value):
                raise ValueError(value)
        x, y = (pins['A'], pins['X'])
        if x == y:
            raise ValueError('Unsupported or inconsistent ECO input')
        graph.setdefault(x, set()).add(y)
        graph.setdefault(y, set()).add(x)
    for declaration in new_wires - old_wires:
        match = re.fullmatch(r'wire\s+(' + NET + r')', declaration)
        if match is None or match[1] not in graph or '[' in match[1]:
            raise ValueError(('Unsupported added wire declaration', declaration))
    aliases = {}
    visited = set()
    for start in graph:
        if start in visited:
            continue
        component = set()
        pending = [start]
        while pending:
            item = pending.pop()
            if item in component:
                continue
            component.add(item)
            pending.extend(graph[item] - component)
        visited.update(component)
        old = component & original_nets
        if len(old) != 1:
            raise ValueError(('Buffer component merges original nets or floats', component))
        canonical = next(iter(old))
        aliases.update({x: canonical for x in component})

    def normalize(value):
        return re.sub(NET, lambda m: aliases.get(m[0], m[0]), value)
    changed = {}
    for name, (master, pins) in a.items():
        target, p2 = b[name]
        if set(pins) != set(p2):
            raise ValueError(('Pins changed', name))
        if {p: normalize(v) for p, v in pins.items()} != {p: normalize(v) for p, v in p2.items()}:
            raise ValueError(('Connectivity changed', name))
        if master != target:
            changed[name] = {'old': master, 'new': target}
    if changed != inputs['substitutions']:
        raise ValueError('Unexpected substitutions')
    lib = Path(inputs['liberty'])
    if hashlib.sha256(lib.read_bytes()).hexdigest() != inputs['liberty_sha256']:
        raise ValueError('Unsupported or inconsistent ECO input')
    text = lib.read_text()

    @functools.lru_cache(None)
    def shape(master):
        block = text.split('cell (' + master + ') {', 1)[1].split('\n  cell (', 1)[0]
        if re.search(r'\b(?:ff_bank|latch_bank|statetable|bus|three_state)\s*[:(]', block):
            raise ValueError('Unsupported state table, bus or tristate substitution')
        state_groups = re.findall('\\n    (?:ff|latch)\\s*\\([^\\n]+\\)\\s*\\{[^{}]*\\}', block)
        if len(state_groups) != len(re.findall(r'\b(?:ff|latch)\s*\(', block)):
            raise ValueError('Unparsed state group')
        states = tuple(sorted((re.sub('\\s+', '', group) for group in state_groups)))
        result = {}
        pin_parts = re.split('\\n    pin \\(', block)[1:]
        if len(pin_parts) != len(re.findall(r'\bpin\s*\(', block)):
            raise ValueError('Unsupported standard-cell pin formatting')
        for part in pin_parts:
            pin = part.split(')', 1)[0]
            d = re.search('direction\\s*:\\s*"?(\\w+)', part)
            f = re.search('function\\s*:\\s*"([^"]+)"', part)
            if d is None or d[1] not in ('input', 'output') or pin in result:
                raise ValueError('Missing, duplicate or unsupported pin direction')
            if d[1] == 'output' and f is None:
                raise ValueError('Output without a logic function')
            result[pin] = (d[1], re.sub('\\s+', '', f[1]) if f else None)
        if not result:
            raise ValueError('Unsupported or inconsistent ECO input')
        return (result, states)
    for c in changed.values():
        if shape(c['old']) != shape(c['new']):
            raise ValueError(c)
    # A recognized family/strength name alone is insufficient: prove the
    # actual library function and lack of stored state for every added type.
    for master in {b[name][0] for name in added}:
        if shape(master) != ({'A': ('input', None), 'X': ('output', 'A')}, ()):
            raise ValueError(('Added cell is not a stateless positive buffer', master))
    libraries = [text]
    for entry in inputs.get('macro_libraries', []):
        path = Path(entry['path'])
        if hashlib.sha256(path.read_bytes()).hexdigest() != entry['sha256']:
            raise ValueError(('Macro Liberty hash mismatch', str(path)))
        libraries.append(path.read_text())

    @functools.lru_cache(None)
    def output_pins(master):
        cell_pattern = re.compile('\\bcell\\s*\\(\\s*"?' + re.escape(master) + '"?\\s*\\)\\s*\\{')
        source = next((t for t in libraries if cell_pattern.search(t)), None)
        if source is None:
            if not master.startswith(('sg13g2_ant', 'sg13g2_fill', 'sg13g2_decap')):
                raise ValueError(master)
            return set()

        def body_at(text, start):
            depth = 1
            quoted = False
            escaped = False
            i = start
            while i < len(text):
                ch = text[i]
                if quoted:
                    if escaped:
                        escaped = False
                    elif ch == '\\':
                        escaped = True
                    elif ch == '"':
                        quoted = False
                elif ch == '"':
                    quoted = True
                elif ch == '{':
                    depth += 1
                elif ch == '}':
                    depth -= 1
                    if depth == 0:
                        return text[start:i]
                i += 1
            raise ValueError('Unterminated Liberty group')
        block = body_at(source, cell_pattern.search(source).end())
        result = set()
        for match in re.finditer('\\b(?:pin|bus)\\s*\\(\\s*"?([^()"]+)"?\\s*\\)\\s*\\{', block):
            pin = match[1].strip()
            body = body_at(block, match.end())
            attrs = re.split('\\b\\w+\\s*\\([^;{}]*\\)\\s*\\{', body, maxsplit=1)[0]
            direction = re.search('\\bdirection\\s*:\\s*"?(\\w+)"?\\s*;', attrs)
            if direction and direction[1] == 'output':
                result.add(pin.split('[')[0])
        return result
    drivers = {n: [] for n in graph}
    for name, (master, pins) in b.items():
        relevant = {p: v for p, v in pins.items() if any((n in graph for n in re.findall(NET, v)))}
        if not relevant:
            continue
        for pin in output_pins(master):
            if pin in relevant:
                for n in re.findall(NET, relevant[pin]):
                    if n in drivers:
                        drivers[n].append(name + '/' + pin)
    for net, connections in drivers.items():
        if len(connections) != 1:
            raise ValueError(('ECO net driver count', net, connections))
    for net, neighbors in graph.items():
        if net in neighbors:
            raise ValueError('Buffer self-loop')
    if sum(map(len, graph.values())) // 2 != len(graph) - len(set(aliases.values())):
        raise ValueError('Buffer cycle')
    return {
        'original_instances': len(a),
        'added_stateless_positive_cells': len(added),
        'added_noninverting_buffers': sum(b[name][0].startswith('sg13g2_buf_')
                                        for name in added),
        'added_delay_cells': sum(b[name][0].startswith('sg13g2_dlygate')
                                 for name in added),
        'equivalent_combinational_substitutions': sum(
            not shape(c['old'])[1] for c in changed.values()),
        'equivalent_sequential_substitutions': sum(
            bool(shape(c['old'])[1]) for c in changed.values()),
        'state_definitions_compared_exactly': True,
        'unchanged_ports_and_assigns': True,
        'unchanged_original_wire_declarations': True,
        'all_original_pin_connections_equal_after_buffer_contraction': True,
    }


def main():
    import argparse
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('before', type=Path)
    parser.add_argument('after', type=Path)
    parser.add_argument('inputs', type=Path, help='JSON with netlist hashes, Liberty paths/hashes, exact substitutions and new_buffer_drivers')
    args = parser.parse_args()
    try:
        result = check(args.before, args.after, json.loads(args.inputs.read_text()))
    except (ValueError, KeyError, IndexError, OSError) as exc:
        print(json.dumps({'status': 'ERROR', 'reason': str(exc)}))
        return 2
    print(json.dumps({'status': 'PASS', **result}, indent=2))
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
