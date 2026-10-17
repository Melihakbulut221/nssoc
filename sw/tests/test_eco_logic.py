# SPDX-FileCopyrightText: 2026 Hasan Melih Akbulut
# SPDX-License-Identifier: Apache-2.0
"""Adversarial controls for the restricted local-equation ECO proof."""
import copy
import importlib.util
from pathlib import Path

import pytest

SPEC = importlib.util.spec_from_file_location('eco_logic',
    Path(__file__).resolve().parents[2] / 'hw/soc/flow/eco_logic.py')
ECO = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(ECO)


def lib(pins):
    return {'ports': {p: {'direction': d, 'bits': [i]} for i, (p, d) in enumerate(pins.items())}}


@pytest.fixture
def circuit():
    libraries = {
        'sg13g2_buf_1': lib({'A': 'input', 'X': 'output'}),
        'sg13g2_buf_8': lib({'A': 'input', 'X': 'output'}),
        'NAND1': lib({'A': 'input', 'B': 'input', 'Y': 'output'}),
        'NAND2': lib({'A': 'input', 'B': 'input', 'Y': 'output'}),
        'FF': lib({'D': 'input', 'CLK': 'input', 'Q': 'output'}),
        'sg13g2_fill_1': lib({}),
    }
    models = {name: ({'A': ('input', None), 'X': ('output', 'A')}, ())
              for name in ('sg13g2_buf_1', 'sg13g2_buf_8')}
    models.update({name: ({'A': ('input', None), 'B': ('input', None), 'Y': ('output', '!(A*B)')}, ())
                   for name in ('NAND1', 'NAND2')})
    models['FF'] = ({'D': ('input', None), 'CLK': ('input', None), 'Q': ('output', 'IQ')}, ('ff(IQ){next_state:D;clocked_on:CLK;}',))
    before = {'ports': {'a': {'direction': 'input', 'bits': [2]},
                         'b': {'direction': 'input', 'bits': [3]},
                         'clk': {'direction': 'input', 'bits': [4]},
                         'y': {'direction': 'output', 'bits': [8]}},
              'cells': {
                  'buffer': {'type': 'sg13g2_buf_1', 'connections': {'A': [2], 'X': [5]}},
                  'g': {'type': 'NAND1', 'connections': {'A': [5], 'B': [3], 'Y': [6]}},
                  'q': {'type': 'FF', 'connections': {'D': [6], 'CLK': [4], 'Q': [8]}},
                  'fill': {'type': 'sg13g2_fill_1', 'connections': {}},
              }}
    after = copy.deepcopy(before)
    del after['cells']['buffer']
    del after['cells']['fill']
    after['cells']['g'] = {'type': 'NAND2', 'connections': {'A': [3], 'B': [2], 'Y': [6]}}
    return before, after, libraries, models


def test_removal_sizing_symmetric_swap_and_filler(circuit):
    before, after, libraries, models = circuit
    result = ECO.compare(before, after, libraries, models)
    assert result['positive_buffers_before'] == 1
    assert result['positive_buffers_after'] == 0
    assert result['equivalent_sizes'] == result['equivalent_input_permutations'] == 1


@pytest.mark.parametrize('mutation', ['data', 'clock', 'multiple', 'cycle', 'undriven', 'output', 'missing', 'extra', 'state', 'function', 'invert_buffer', 'tristate'])
def test_faults_cannot_be_hidden_by_contraction(circuit, mutation):
    before, after, libraries, models = circuit
    cells = after['cells']
    if mutation == 'data':
        cells['q']['connections']['D'] = [3]
    elif mutation == 'clock':
        cells['q']['connections']['CLK'] = [2]
    elif mutation == 'multiple':
        cells['bad'] = {'type': 'sg13g2_buf_1', 'connections': {'A': [3], 'X': [2]}}
    elif mutation == 'cycle':
        cells['bad'] = {'type': 'sg13g2_buf_1', 'connections': {'A': [11], 'X': [10]}}
        cells['bad2'] = {'type': 'sg13g2_buf_1', 'connections': {'A': [10], 'X': [11]}}
    elif mutation == 'undriven':
        cells['g']['connections']['A'] = [50]
    elif mutation == 'output':
        after['ports']['y']['bits'] = [6]
    elif mutation == 'missing':
        del cells['q']['connections']['CLK']
    elif mutation == 'extra':
        cells['extra'] = copy.deepcopy(cells['g'])
        cells['extra']['connections']['Y'] = [90]
    elif mutation == 'state':
        libraries['FF2'] = copy.deepcopy(libraries['FF'])
        models['FF2'] = (models['FF'][0], ('ff(IQ){next_state:!D;clocked_on:CLK;}',))
        cells['q']['type'] = 'FF2'
    elif mutation == 'function':
        models['NAND2'] = ({'A': ('input', None), 'B': ('input', None), 'Y': ('output', '(A*B)')}, ())
    elif mutation == 'invert_buffer':
        models['sg13g2_buf_1'] = ({'A': ('input', None), 'X': ('output', '!A')}, ())
    else:
        libraries['NAND2']['ports']['A']['direction'] = 'inout'
    with pytest.raises(ValueError):
        ECO.compare(before, after, libraries, models)


def test_asymmetric_input_swap_is_rejected(circuit):
    before, after, libraries, models = circuit
    for name in ('NAND1', 'NAND2'):
        models[name] = ({'A': ('input', None), 'B': ('input', None), 'Y': ('output', '!A*B')}, ())
    with pytest.raises(ValueError, match='Boolean input equation'):
        ECO.compare(before, after, libraries, models)


def test_unchanged_opaque_macro_requires_every_input_equal(circuit):
    before, after, libraries, models = circuit
    del models['FF']
    ECO.compare(before, after, libraries, models)
    after['cells']['q']['connections']['D'] = [3]
    with pytest.raises(ValueError, match='State/macro input'):
        ECO.compare(before, after, libraries, models)


@pytest.mark.parametrize('text', ['A B', 'A;', '__import__(x)', '(A+B', 'A)', 'A&&B', ''])
def test_unsupported_boolean_syntax_fails(text):
    with pytest.raises(ValueError):
        ECO.expression(text)


def test_boolean_operator_precedence():
    assert ECO.evaluate(ECO.expression('!A*B+C'), {'A': True, 'B': False, 'C': True})
    assert not ECO.evaluate(ECO.expression('!(A*B+C)'), {'A': False, 'B': True, 'C': True})
    assert ECO.evaluate(ECO.expression('A^B'), {'A': False, 'B': True})


def test_liberty_parser_preserves_function_and_state():
    text = '''library(test) {
      cell (BUF) { pin (A) { direction : input; }
        pin (X) { direction : output; function : "A"; timing () { related_pin : "A"; } } }
      cell (FF) { ff (IQ,IQN) { next_state : "D"; clocked_on : "CLK"; clear : "!R"; }
        pin (D) { direction : input; } pin (Q) { direction : output; function : "IQ"; } }
    }'''
    models = ECO.standard_models(text)
    assert models['BUF'] == ({'A': ('input', None), 'X': ('output', 'A')}, ())
    assert models['FF'][1] == ('ff(IQ,IQN){next_state:"D";clocked_on:"CLK";clear:"!R";}',)
    assert ECO.standard_models(text.replace('"!R"', '"R"'))['FF'] != models['FF']


@pytest.mark.parametrize('construct', ['statetable (A,X) { table : "x:x"; }',
                                      'three_state : "A";', 'ff_bank (IQ, IQN, 2) {}'])
def test_unsupported_liberty_semantics_remain_opaque(construct):
    text = 'cell (sg13g2_buf_1) { ' + construct + ' pin (A) { direction: input; } pin (X) { direction: output; function: "A"; } }'
    assert 'sg13g2_buf_1' not in ECO.standard_models(text)


def test_unterminated_library_fails():
    with pytest.raises(ValueError, match='Unterminated'):
        ECO.standard_models('cell (BUF) { pin (A) { direction : input; }')


def test_real_tie_cell_fanout_repair_preserves_constants(circuit):
    before, after, libraries, models = circuit
    libraries['sg13g2_tielo'] = lib({'L_LO': 'output'})
    libraries['sg13g2_tiehi'] = lib({'L_HI': 'output'})
    models['sg13g2_tielo'] = ({'L_LO': ('output', '0')}, ())
    models['sg13g2_tiehi'] = ({'L_HI': ('output', '1')}, ())
    before['cells']['g']['connections']['A'] = ['0']
    after['cells']['g']['connections']['B'] = [99]
    after['cells']['new_tie'] = {'type': 'sg13g2_tielo', 'connections': {'L_LO': [99]}}
    result = ECO.compare(before, after, libraries, models)
    assert result['proven_tie_cells_before'] == 0
    assert result['proven_tie_cells_after'] == 1
    wrong = copy.deepcopy(after)
    wrong['cells']['new_tie'] = {'type': 'sg13g2_tiehi', 'connections': {'L_HI': [99]}}
    with pytest.raises(ValueError, match='Boolean input equation changed'):
        ECO.compare(before, wrong, libraries, models)
    for bad in [({'L_LO': ('output', '1')}, ()),
                ({'L_LO': ('output', '0')}, ('ff(IQ){clocked_on:C;}',))]:
        forged = {**models, 'sg13g2_tielo': bad}
        with pytest.raises(ValueError, match='Non-buffer instance'):
            ECO.compare(before, after, libraries, forged)


def test_explicit_unused_macro_output_bus_and_live_sink_control(circuit):
    before, after, libraries, models = circuit
    libraries['RAM'] = {'ports': {'A': {'direction': 'input', 'bits': [0]},
                                 'Q': {'direction': 'output', 'bits': [1, 2]}}}
    before['cells']['ram'] = {'type': 'RAM', 'connections': {'A': [2]}}
    after['cells']['ram'] = {'type': 'RAM', 'connections': {'A': [2], 'Q': [90, 91]}}
    assert ECO.compare(before, after, libraries, models)['unobserved_output_port_changes'] == 1
    wrong = copy.deepcopy(after)
    wrong['cells']['q']['connections']['D'] = [90]
    with pytest.raises(ValueError):
        ECO.compare(before, wrong, libraries, models)
    wrong = copy.deepcopy(after)
    wrong['ports']['y']['bits'] = [91]
    with pytest.raises(ValueError):
        ECO.compare(before, wrong, libraries, models)
