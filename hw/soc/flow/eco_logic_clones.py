# SPDX-FileCopyrightText: 2026 Hasan Melih Akbulut
# SPDX-License-Identifier: Apache-2.0
"""Prove added combinational duplicates before the existing retained-cell check.

Each added gate must compute every output of an original, retained gate from
the same canonical sources. Added state, opaque macros, removed original gates,
cycles and unsupported Boolean models are rejected. This is a functional ECO
proof, not a timing, SRAM-interior, initialization or physical-layout proof.
"""
import copy
from collections import defaultdict

from eco_logic import canonical_design, compare as compare_retained, functions_equal


def combinational_model(cell, libraries, models):
    master = cell['type']
    model = models.get(master)
    if model is None or model[1]:
        raise ValueError('Clone has state or an opaque model: ' + master)
    ports = libraries[master]['ports']
    if set(ports) != set(model[0]):
        raise ValueError('Clone Liberty interface differs from elaboration')
    if set(cell['connections']) != set(ports):
        raise ValueError('Clone requires every port to be connected')
    for pin, info in ports.items():
        if (len(info['bits']) != 1 or len(cell['connections'][pin]) != 1
                or info['direction'] != model[0][pin][0]):
            raise ValueError('Unsupported clone pin interface')
    inputs = tuple(sorted(p for p, d in ports.items() if d['direction'] == 'input'))
    outputs = tuple(sorted(p for p, d in ports.items() if d['direction'] == 'output'))
    if not outputs or any(model[0][p][1] is None for p in outputs):
        raise ValueError('Clone has no complete output functions')
    return inputs, outputs, model[0]


def compare(before, after, libraries, models):
    original, original_root, _ = canonical_design(before, libraries, models)
    candidate, candidate_root, _ = canonical_design(after, libraries, models)
    if set(original) - set(candidate):
        raise ValueError('Original non-buffer instance removed')
    added = set(candidate) - set(original)
    if not added:
        return dict(compare_retained(before, after, libraries, models),
                    equivalent_combinational_clones={})

    index = defaultdict(list)
    for name, cell in original.items():
        try:
            inputs, outputs, functions = combinational_model(cell, libraries, models)
        except ValueError:
            continue
        equations = tuple((pin, original_root(cell['connections'][pin][0]))
                          for pin in inputs)
        index[(outputs, frozenset(v for _, v in equations))].append(
            (name, equations, functions))

    proven, visiting = {}, set()

    def resolve(bit):
        root = candidate_root(bit)
        if root[0] == 'cell' and root[1] in added:
            prove(root[1])
            return ('cell', proven[root[1]], root[2], root[3])
        return root

    def prove(name):
        if name in proven:
            return
        if name in visiting:
            raise ValueError('Combinational clone dependency cycle')
        visiting.add(name)
        cell = candidate[name]
        inputs, outputs, functions = combinational_model(cell, libraries, models)
        equations = tuple((pin, resolve(cell['connections'][pin][0])) for pin in inputs)
        matches = index[(outputs, frozenset(v for _, v in equations))]
        for target, reference, reference_functions in matches:
            # A physical resizing may retain the name but change its pins;
            # the legacy checker below must still validate that entire cell.
            if not all(pin in candidate[target]['connections'] for pin in outputs):
                continue
            if all(functions_equal(reference_functions[pin][1], functions[pin][1],
                                   reference, equations) for pin in outputs):
                proven[name] = target
                visiting.remove(name)
                return
        raise ValueError('Added gate has no proven original equation: ' + name)

    for name in sorted(added):
        prove(name)

    # Remove only proven duplicates, reconnecting their users to the retained
    # original output. Positive buffer chains and all remaining cell inputs
    # are then checked by the unmodified retained-cell checker.
    replace = {}
    for name, target in proven.items():
        _, outputs, _ = combinational_model(candidate[name], libraries, models)
        for pin in outputs:
            replace[candidate[name]['connections'][pin][0]] = candidate[target]['connections'][pin][0]
    normalized = copy.deepcopy(after)
    for name in added:
        del normalized['cells'][name]
    for cell in normalized['cells'].values():
        for pin, bits in cell['connections'].items():
            cell['connections'][pin] = [replace.get(bit, bit) for bit in bits]
    for port in normalized['ports'].values():
        port['bits'] = [replace.get(bit, bit) for bit in port['bits']]
    result = compare_retained(before, normalized, libraries, models)
    result['equivalent_combinational_clones'] = dict(sorted(proven.items()))
    return result
