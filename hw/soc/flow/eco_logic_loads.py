# SPDX-FileCopyrightText: 2026 Hasan Melih Akbulut
# SPDX-License-Identifier: Apache-2.0
"""Account for antenna and disconnected clock loads in a digital connection proof.

This does not remove devices from physical LVS or waive their capacitance,
leakage or antenna requirements. It only recognizes the actual Liberty
stateless, input-only interface and unobserved buffer/inverter outputs when
comparing digital functions.
"""
import copy
import re

from eco_logic import (canonical_design, compare as compare_logic,
                       unobserved_output_pins, expression)


def without_antenna_loads(module, libraries, models):
    _, resolve, _ = canonical_design(module, libraries, models)
    normalized = copy.deepcopy(module)
    loads = {}
    for name, cell in module['cells'].items():
        if cell['type'] != 'sg13g2_antennanp':
            continue
        ports = libraries[cell['type']]['ports']
        if (models.get(cell['type']) != ({'A': ('input', None)}, ())
                or set(ports) != {'A'} or ports['A']['direction'] != 'input'
                or len(ports['A']['bits']) != 1
                or set(cell['connections']) != {'A'}
                or len(cell['connections']['A']) != 1):
            raise ValueError('Unsupported antenna load interface: ' + name)
        loads[name] = resolve(cell['connections']['A'][0])
        del normalized['cells'][name]
    return normalized, loads


def without_disconnected_clock_loads(module, libraries, models):
    """Only exact stateless IHP buf/inv outputs with no observers are removable."""
    _, resolve, _ = canonical_design(module, libraries, models)
    unused = unobserved_output_pins(module, libraries)
    normalized = copy.deepcopy(module)
    loads = {}
    for name, cell in module['cells'].items():
        match = re.fullmatch(r'sg13g2_(buf|inv)_(1|2|4|8|16)', cell['type'])
        if not match:
            continue
        output, function = ('X', 'A') if match[1] == 'buf' else ('Y', '!A')
        model = models.get(cell['type'])
        if (model is None or model[1] or set(model[0]) != {'A', output}
                or model[0]['A'] != ('input', None)
                or model[0][output][0] != 'output'):
            continue
        try:
            if expression(model[0][output][1]) != expression(function):
                continue
        except (TypeError, ValueError):
            continue
        ports = libraries[cell['type']]['ports']
        if (set(ports) != {'A', output}
                or any(len(info['bits']) != 1 for info in ports.values())
                or ports['A']['direction'] != 'input'
                or ports[output]['direction'] != 'output'
                or set(cell['connections']) not in ({'A'}, {'A', output})
                or len(cell['connections']['A']) != 1):
            continue
        if output in cell['connections'] and (name, output) not in unused:
            continue
        loads[name] = {'master': cell['type'],
                       'input': resolve(cell['connections']['A'][0]),
                       'output': output, 'output_unobserved': True}
        del normalized['cells'][name]
    return normalized, loads


def compare(before, after, libraries, models):
    first, old_loads = without_antenna_loads(before, libraries, models)
    second, new_loads = without_antenna_loads(after, libraries, models)
    first, old_clocks = without_disconnected_clock_loads(first, libraries, models)
    second, new_clocks = without_disconnected_clock_loads(second, libraries, models)
    result = compare_logic(first, second, libraries, models)
    result['disconnected_clock_loads_before'] = old_clocks
    result['disconnected_clock_loads_after'] = new_clocks
    result['digital_input_only_antenna_loads_before'] = old_loads
    result['digital_input_only_antenna_loads_after'] = new_loads
    return result
