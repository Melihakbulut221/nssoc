# SPDX-FileCopyrightText: 2026 Hasan Melih Akbulut
# SPDX-License-Identifier: Apache-2.0
"""Do not let an input-only antenna normalization hide logic changes."""
import copy
import importlib.util
from pathlib import Path
import sys

import pytest

FLOW = Path(__file__).resolve().parents[2] / 'hw/soc/flow'
sys.path.insert(0, str(FLOW))
try:
    SPEC = importlib.util.spec_from_file_location('load_checker', FLOW / 'eco_logic_loads.py')
    LOADS = importlib.util.module_from_spec(SPEC)
    SPEC.loader.exec_module(LOADS)
finally:
    sys.path.pop(0)
CONTROL_SPEC = importlib.util.spec_from_file_location('load_controls',
                                                    Path(__file__).with_name('test_eco_logic.py'))
CONTROLS = importlib.util.module_from_spec(CONTROL_SPEC)
CONTROL_SPEC.loader.exec_module(CONTROLS)
circuit = CONTROLS.circuit


def add_load(after, libraries, models):
    libraries['sg13g2_antennanp'] = CONTROLS.lib({'A': 'input'})
    models['sg13g2_antennanp'] = ({'A': ('input', None)}, ())
    after['cells']['antenna'] = {'type': 'sg13g2_antennanp', 'connections': {'A': [2]}}


def test_actual_input_only_load_addition_is_digitally_passive(circuit):
    before, after, libraries, models = circuit
    add_load(after, libraries, models)
    snapshot = copy.deepcopy(after)
    result = LOADS.compare(before, after, libraries, models)
    assert result['digital_input_only_antenna_loads_before'] == {}
    assert set(result['digital_input_only_antenna_loads_after']) == {'antenna'}
    assert result['retained_cells'] == 2
    assert after == snapshot


@pytest.mark.parametrize('fault', ['state', 'output', 'unknown', 'undriven',
                                  'wrong_clock', 'missing_pin', 'wrong_width'])
def test_load_normalization_rejects_mutated_contract_or_function(circuit, fault):
    before, after, libraries, models = circuit
    add_load(after, libraries, models)
    cell = after['cells']['antenna']
    if fault == 'state':
        models['sg13g2_antennanp'] = ({'A': ('input', None)}, ('ff(IQ)',))
    elif fault == 'output':
        libraries['sg13g2_antennanp'] = CONTROLS.lib({'A': 'output'})
        models['sg13g2_antennanp'] = ({'A': ('output', '0')}, ())
        cell['connections']['A'] = [90]
    elif fault == 'unknown':
        libraries['other_load'] = libraries['sg13g2_antennanp']
        models['other_load'] = models['sg13g2_antennanp']
        cell['type'] = 'other_load'
    elif fault == 'undriven':
        cell['connections']['A'] = [999]
    elif fault == 'wrong_clock':
        after['cells']['q']['connections']['CLK'] = [3]
    elif fault == 'missing_pin':
        cell['connections'] = {}
    else:
        cell['connections']['A'] = [2, 3]
    with pytest.raises(ValueError):
        LOADS.compare(before, after, libraries, models)


@pytest.mark.parametrize('function', ['!A', '!(A)'])
@pytest.mark.parametrize('explicit_output', [False, True])
def test_clock_balancing_load_requires_unobserved_output(circuit, explicit_output, function):
    before, after, libraries, models = circuit
    libraries['sg13g2_inv_2'] = CONTROLS.lib({'A': 'input', 'Y': 'output'})
    models['sg13g2_inv_2'] = ({'A': ('input', None), 'Y': ('output', function)}, ())
    cell = {'type': 'sg13g2_inv_2', 'connections': {'A': [4]}}
    if explicit_output:
        cell['connections']['Y'] = [90]
    after['cells']['clock_load'] = cell
    result = LOADS.compare(before, after, libraries, models)
    assert set(result['disconnected_clock_loads_after']) == {'clock_load'}
    assert result['disconnected_clock_loads_before'] == {}
    wrong = copy.deepcopy(after)
    wrong['cells']['clock_load']['connections']['Y'] = [90]
    wrong['cells']['q']['connections']['CLK'] = [90]
    with pytest.raises(ValueError):
        LOADS.compare(before, wrong, libraries, models)
    wrong = copy.deepcopy(after)
    wrong['cells']['clock_load']['connections']['Y'] = [90]
    wrong['ports']['y']['bits'] = [90]
    with pytest.raises(ValueError):
        LOADS.compare(before, wrong, libraries, models)
    stateful = {**models, 'sg13g2_inv_2': (models['sg13g2_inv_2'][0], ('latch(IQ)',))}
    with pytest.raises(ValueError):
        LOADS.compare(before, after, libraries, stateful)


def test_disconnected_clock_buffer_output_can_be_omitted(circuit):
    before, after, libraries, models = circuit
    after['cells']['clock_load'] = {'type': 'sg13g2_buf_8', 'connections': {'A': [4]}}
    assert 'clock_load' in LOADS.compare(before, after, libraries, models)['disconnected_clock_loads_after']
