# SPDX-FileCopyrightText: 2026 Hasan Melih Akbulut
# SPDX-License-Identifier: Apache-2.0
"""Adversarial checks for combinational duplication in physical timing repair."""
import copy
import importlib.util
from pathlib import Path
import sys

import pytest

FLOW = Path(__file__).resolve().parents[2] / 'hw/soc/flow'
sys.path.insert(0, str(FLOW))
try:
    SPEC = importlib.util.spec_from_file_location('clone_checker', FLOW / 'eco_logic_clones.py')
    CLONES = importlib.util.module_from_spec(SPEC)
    SPEC.loader.exec_module(CLONES)
finally:
    sys.path.pop(0)

CONTROL_SPEC = importlib.util.spec_from_file_location('retained_controls',
                                                    Path(__file__).with_name('test_eco_logic.py'))
CONTROLS = importlib.util.module_from_spec(CONTROL_SPEC)
CONTROL_SPEC.loader.exec_module(CONTROLS)
circuit = CONTROLS.circuit


def add_clone(after):
    after['cells']['duplicate'] = copy.deepcopy(after['cells']['g'])
    after['cells']['duplicate']['connections']['Y'] = [90]
    after['cells']['q']['connections']['D'] = [90]


def test_duplicate_with_resizing_permutation_and_buffer_contraction(circuit):
    before, after, libraries, models = circuit
    add_clone(after)
    result = CLONES.compare(before, after, libraries, models)
    assert result['equivalent_combinational_clones'] == {'duplicate': 'g'}
    assert result['retained_cells'] == 2
    assert result['equivalent_sizes'] == 1


def test_no_duplicates_uses_original_checker(circuit):
    before, after, libraries, models = circuit
    assert CLONES.compare(before, after, libraries, models) == dict(
        CONTROLS.ECO.compare(before, after, libraries, models),
        equivalent_combinational_clones={})


def test_dependency_order_does_not_determine_equivalence(circuit):
    before, after, libraries, models = circuit
    before['cells']['second'] = {'type': 'NAND1', 'connections': {'A': [6], 'B': [3], 'Y': [7]}}
    after['cells']['second'] = copy.deepcopy(before['cells']['second'])
    before['cells']['q']['connections']['D'] = [7]
    add_clone(after)
    after['cells']['a_first_alphabetically'] = {
        'type': 'NAND1', 'connections': {'A': [90], 'B': [3], 'Y': [91]}}
    after['cells']['q']['connections']['D'] = [91]
    result = CLONES.compare(before, after, libraries, models)
    assert result['equivalent_combinational_clones'] == {
        'a_first_alphabetically': 'second', 'duplicate': 'g'}


@pytest.mark.parametrize('fault', [
    'wrong_input', 'wrong_function', 'state', 'opaque', 'removed_original',
    'clock', 'original_input', 'self_cycle', 'cycle_through_buffer',
    'two_clone_cycle', 'multiple_driver', 'missing_output', 'top_port',
    'wrong_model_direction', 'wrong_model_width', 'parameter',
])
def test_invalid_duplication_is_rejected(circuit, fault):
    before, after, libraries, models = circuit
    add_clone(after)
    cells = after['cells']
    duplicate = cells['duplicate']
    if fault == 'wrong_input':
        duplicate['connections']['A'] = [4]
    elif fault == 'wrong_function':
        libraries['AND'] = copy.deepcopy(libraries['NAND1'])
        models['AND'] = ({'A': ('input', None), 'B': ('input', None),
                          'Y': ('output', 'A*B')}, ())
        duplicate['type'] = 'AND'
    elif fault == 'state':
        cells['duplicate'] = {'type': 'FF', 'connections': {'D': [6], 'CLK': [4], 'Q': [90]}}
    elif fault == 'opaque':
        libraries['MACRO'] = copy.deepcopy(libraries['NAND1'])
        duplicate['type'] = 'MACRO'
    elif fault == 'removed_original':
        del cells['g']
    elif fault == 'clock':
        cells['q']['connections']['CLK'] = [3]
    elif fault == 'original_input':
        cells['g']['connections']['A'] = [4]
    elif fault == 'self_cycle':
        duplicate['connections']['A'] = [90]
    elif fault == 'cycle_through_buffer':
        cells['loop'] = {'type': 'sg13g2_buf_1', 'connections': {'A': [90], 'X': [91]}}
        duplicate['connections']['A'] = [91]
    elif fault == 'two_clone_cycle':
        cells['duplicate2'] = copy.deepcopy(duplicate)
        cells['duplicate2']['connections'] = {'A': [90], 'B': [3], 'Y': [91]}
        duplicate['connections']['A'] = [91]
    elif fault == 'multiple_driver':
        duplicate['connections']['Y'] = [6]
    elif fault == 'missing_output':
        del duplicate['connections']['Y']
    elif fault == 'top_port':
        after['ports']['y']['bits'] = [90]
    elif fault == 'wrong_model_direction':
        libraries['NAND2']['ports']['A']['direction'] = 'output'
    elif fault == 'wrong_model_width':
        libraries['NAND2']['ports']['Y']['bits'] = [0, 1]
        duplicate['connections']['Y'] = [90, 91]
        cells['g']['connections']['Y'] = [6, 7]
    else:
        duplicate['parameters'] = {'unsupported': 1}
    with pytest.raises(ValueError):
        CLONES.compare(before, after, libraries, models)


def test_cloned_source_cannot_mask_a_retained_input_error(circuit):
    before, after, libraries, models = circuit
    add_clone(after)
    # Both the retained original and the duplicate have the same wrong input.
    # Comparing duplicates only against the candidate would miss this fault.
    after['cells']['g']['connections']['A'] = [4]
    after['cells']['duplicate']['connections']['A'] = [4]
    with pytest.raises(ValueError):
        CLONES.compare(before, after, libraries, models)
