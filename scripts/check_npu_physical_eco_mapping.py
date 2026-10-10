#!/usr/bin/env python3
# SPDX-FileCopyrightText: 2026 Hasan Melih Akbulut
# SPDX-License-Identifier: Apache-2.0
"""Check the exact NPU gate replacement after SRAM mapping, without adoption.

Compare actual native Yosys graphs by their shared named signals. All original
cells and ports except one combinational gate must retain their exact equations.
The three replacement gates and two new internal nets are checked explicitly.
This structural bridge supplements the binary truth table; it does not accept
four-state boot, SRAM characterization, placement, routing, or chip timing.
"""
from collections import Counter


def require(value, message):
    if not value:
        raise ValueError(message)


def check(before, after):
    names = ('nssoc_npu_init_b_n', 'nssoc_npu_init_cd')
    added = ('nssoc_npu_init_invert', 'nssoc_npu_init_product')
    oldcells, newcells = before['cells'], after['cells']
    require(not any(n in oldcells for n in added), 'New cell already exists')
    require(set(newcells) == set(oldcells) | set(added), 'Cell inventory differs')
    require(set(after['netnames']) == set(before['netnames']) | set(names), 'Named signal inventory differs')
    mapping = {x: x for x in ('0', '1', 'x', 'z')}
    inverse = {x: x for x in ('0', '1', 'x', 'z')}
    for name, net in before['netnames'].items():
        other = after['netnames'][name]['bits']
        require(len(other) == len(net['bits']), 'Named signal width differs: ' + name)
        for old, new in zip(net['bits'], other):
            require(old not in mapping or mapping[old] == new, 'Inconsistent shared signal: ' + name)
            require(new not in inverse or inverse[new] == old, 'Aliased distinct original signals: ' + name)
            mapping[old] = new
            inverse[new] = old
    require(set(before['ports']) == set(after['ports']), 'Port inventory differs')
    for name, port in before['ports'].items():
        other = after['ports'][name]
        require(port['direction'] == other['direction'] and
                [mapping[b] for b in port['bits']] == other['bits'], 'Port equation differs: ' + name)
    for name, cell in oldcells.items():
        if name == '_103492_':
            continue
        other = newcells[name]
        require(all(cell.get(k) == other.get(k) for k in ('type', 'parameters', 'port_directions')),
                'Unrelated cell changed: ' + name)
        require({p: [mapping[b] for b in bits] for p, bits in cell['connections'].items()} ==
                other['connections'], 'Unrelated cell equation changed: ' + name)

    def node(module, name):
        bits = module['netnames'][name]['bits']
        require(len(bits) == 1 and isinstance(bits[0], int), 'Expected scalar native signal: ' + name)
        return bits

    def gate(module, name, kind, connections):
        c = module['cells'][name]
        require(c['type'] == kind and not c.get('parameters'), 'Wrong native gate: ' + name)
        require(c['connections'] == {p: node(module, n) for p, n in connections.items()},
                'Wrong replacement gate equation: ' + name)

    gate(before, '_103491_', 'sg13g2_nand3_1',
         dict(A='_026035_', B='_032758_', C='_043517_', Y='_043518_'))
    gate(before, '_103492_', 'sg13g2_o21ai_1', dict(A1='_026035_', A2='_043474_', B1='_043518_', Y='_043519_'))
    gate(after, added[0], 'sg13g2_inv_1', dict(A='_043474_', Y=names[0]))
    gate(after, added[1], 'sg13g2_and2_1', dict(A='_032758_', B='_043517_', X=names[1]))
    gate(after, '_103492_', 'sg13g2_mux2_1', dict(A0=names[0], A1=names[1], S='_026035_', X='_043519_'))
    newbits = [node(after, n)[0] for n in names]
    require(len(set(newbits)) == 2 and not any(b in inverse for b in newbits), 'New internal nets alias old signals')
    expected_users = {newbits[0]: {(added[0], 'Y'), ('_103492_', 'A0')},
                      newbits[1]: {(added[1], 'X'), ('_103492_', 'A1')}}
    users = {b: set() for b in newbits}
    for name, cell in newcells.items():
        for port, bits in cell['connections'].items():
            for bit in bits:
                if bit in users:
                    users[bit].add((name, port))
    require(users == expected_users, 'Replacement internal net has unexpected load or driver')
    macros = {n: c['type'] for n, c in newcells.items() if c['type'] in ('SP6TSRAM512x64', 'DP8TSRAMDP256x16')}
    require(Counter(macros.values()) == {'SP6TSRAM512x64': 16, 'DP8TSRAMDP256x16': 16}, 'Physical SRAM census differs')
    return dict(status='PASS_EXACT_MAPPED_COMBINATIONAL_ECO_BRIDGE', unchanged_cells=len(oldcells)-1,
                replaced_cells=1, added_cells=2, shared_named_signals=len(before['netnames']),
                ports=len(before['ports']), macros=macros, all_other_cell_equations_preserved=True,
                full_soc_functional_accepted=False, timing_accepted=False)
