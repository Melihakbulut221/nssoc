# SPDX-FileCopyrightText: 2026 Hasan Melih Akbulut
# SPDX-License-Identifier: Apache-2.0
"""Prevent sizing/buffer checks from accepting altered logic or state."""
import hashlib
import importlib.util
import json
from pathlib import Path
import subprocess
import sys

import pytest

SCRIPT = Path(__file__).resolve().parents[2] / 'hw/soc/flow/check_physical_eco.py'
spec = importlib.util.spec_from_file_location('physical_eco', SCRIPT)
eco = importlib.util.module_from_spec(spec)
spec.loader.exec_module(eco)


def cell(name, function='A', state=None):
    pins = {'A': ('input', None), 'X': ('output', function)}
    if state:
        pins = {'D': ('input', None), 'CLK': ('input', None), 'Q': ('output', 'IQ')}
    text = f'  cell ({name}) {{\n'
    if state:
        text += f'    ff (IQ, IQ_N) {{ next_state : "{state[0]}"; clocked_on : "{state[1]}"; }}\n'
    for pin, (direction, function) in pins.items():
        text += f'    pin ({pin}) {{\n      direction : {direction};\n'
        if function:
            text += f'      function : "{function}";\n'
        text += '    }\n'
    return text + '  }\n'


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


@pytest.fixture
def design(tmp_path):
    lib = tmp_path / 'std.lib'
    lib.write_text('library (test) {\n' + ''.join(cell('sg13g2_buf_' + str(n)) for n in (1, 2, 4, 8, 16)) + ''.join(cell('sg13g2_dlygate4sd' + str(n) + '_1') for n in (1, 2, 3)) + cell('FF1', state=('D', 'CLK')) + cell('FF2', state=('D', 'CLK')) + '}\n')
    macro = tmp_path / 'macro.lib'
    macro.write_text('library(test) { cell(RM_TEST) { bus(A_DOUT) { direction : output; pin(A_DOUT[1:0]) { capacitance : 0; } } } }')
    before = tmp_path / 'before.v'
    before.write_text('module chip(y); output [1:0] y; wire n0,n1; RM_TEST memory (.A_DOUT({n1,n0})); sg13g2_buf_1 b0 (.A(n0),.X(y[0])); sg13g2_buf_8 b1 (.A(n1),.X(y[1])); endmodule')
    after = tmp_path / 'after.v'
    after.write_text(before.read_text().replace('sg13g2_buf_1', 'sg13g2_buf_8').replace('.A(n0)', '.A(eco_net)').replace(' endmodule', ' sg13g2_buf_8 eco (.A(n0),.X(eco_net)); endmodule'))
    inputs = {'liberty': str(lib), 'liberty_sha256': digest(lib), 'macro_libraries': [{'path': str(macro), 'sha256': digest(macro)}], 'before_sha256': digest(before), 'after_sha256': digest(after), 'new_buffer_drivers': {'n0': {}}, 'substitutions': {'b0': {'old': 'sg13g2_buf_1', 'new': 'sg13g2_buf_8'}}}
    return before, after, inputs, lib, macro


def test_bus_and_equivalent_sizing_pass(design):
    before, after, inputs, _, _ = design
    result = eco.check(before, after, inputs)
    assert result['added_noninverting_buffers'] == 1
    assert result['added_stateless_positive_cells'] == 1
    assert result['equivalent_combinational_substitutions'] == 1


@pytest.mark.parametrize('master', [
    *['sg13g2_buf_' + str(n) for n in (1, 2, 4, 8, 16)],
    *['sg13g2_dlygate4sd' + str(n) + '_1' for n in (1, 2, 3)],
])
def test_each_legal_buffer_or_delay_uses_the_library_function(design, master):
    before, after, inputs, lib, _ = design
    after.write_text(after.read_text().replace('sg13g2_buf_8 eco', master + ' eco'))
    inputs['after_sha256'] = digest(after)
    result = eco.check(before, after, inputs)
    assert result['added_stateless_positive_cells'] == 1
    assert result['added_noninverting_buffers'] == int('buf_' in master)
    assert result['added_delay_cells'] == int('dlygate' in master)
    # Same family name and pin list, but a corrupted logic function must fail.
    lib.write_text(lib.read_text().replace(cell(master), cell(master, '!A')))
    inputs['liberty_sha256'] = digest(lib)
    with pytest.raises(ValueError):
        eco.check(before, after, inputs)


def test_positive_delay_with_hidden_state_is_rejected(design):
    before, after, inputs, lib, _ = design
    master = 'sg13g2_dlygate4sd3_1'
    after.write_text(after.read_text().replace('sg13g2_buf_8 eco', master + ' eco'))
    inputs['after_sha256'] = digest(after)
    # Keeping function A and the expected pins must not conceal new storage.
    ordinary = cell(master)
    stateful = ordinary.replace('    pin (A)',
        '    ff (IQ, IQ_N) { next_state : "A"; clocked_on : "A"; }\n    pin (A)')
    lib.write_text(lib.read_text().replace(ordinary, stateful))
    inputs['liberty_sha256'] = digest(lib)
    with pytest.raises(ValueError, match='not a stateless positive buffer'):
        eco.check(before, after, inputs)


@pytest.mark.parametrize('old,new', [
    ('{n1,n0}', '{n0,n1}'),
    ('eco (.A(n0),.X(eco_net))', 'eco (.A(eco_net),.X(n0))'),
    ('eco (.A(n0),.X(eco_net))', 'eco (.A(n1),.X(eco_net))'),
    ('eco (.A(n0),.X(eco_net))', 'eco (.A(eco_net),.X(eco_net))'),
    ('output [1:0] y', 'input [1:0] y'),
    ('sg13g2_buf_8 b1 (.A(n1),.X(y[1]));', ''),
    ('wire n0,n1;', 'wire n0,n1; assign n0=n1;'),
    ('wire n0,n1;', 'wire [0:1] n0,n1;'),
    ('sg13g2_buf_8 eco', 'sg13g2_inv_1 eco'),
    (' endmodule', ' unexpected statement; endmodule'),
])
def test_altered_connectivity_is_rejected_even_when_rehashed(design, old, new):
    before, after, inputs, _, _ = design
    assert old in after.read_text()
    after.write_text(after.read_text().replace(old, new))
    inputs['after_sha256'] = digest(after)
    with pytest.raises(ValueError):
        eco.check(before, after, inputs)


@pytest.mark.parametrize('key', ['before_sha256', 'after_sha256', 'liberty_sha256', 'macro'])
def test_every_input_is_hash_pinned(design, key):
    before, after, inputs, _, _ = design
    if key == 'macro':
        inputs['macro_libraries'][0]['sha256'] = '0' * 64
    else:
        inputs[key] = '0' * 64
    with pytest.raises(ValueError):
        eco.check(before, after, inputs)


def test_macro_input_cannot_be_buffer_driver(design):
    before, after, inputs, _, macro = design
    macro.write_text(macro.read_text().replace('direction : output', 'direction : input'))
    inputs['macro_libraries'][0]['sha256'] = digest(macro)
    with pytest.raises(ValueError, match='driver count'):
        eco.check(before, after, inputs)


@pytest.mark.parametrize('state', [('D', 'CLK'), ('!D', 'CLK'), ('D', '!CLK')])
def test_sequential_data_and_clock_semantics(design, state):
    before, after, inputs, lib, _ = design
    before.write_text('module chip(y); output y; wire d,c; FF1 q (.D(d),.CLK(c),.Q(y)); endmodule')
    after.write_text(before.read_text().replace('FF1', 'FF2'))
    lib.write_text('library(test) {\n' + cell('sg13g2_buf_8') + cell('FF1', state=('D', 'CLK')) + cell('FF2', state=state) + '}\n')
    inputs.update(before_sha256=digest(before), after_sha256=digest(after), liberty_sha256=digest(lib), new_buffer_drivers={}, substitutions={'q': {'old': 'FF1', 'new': 'FF2'}})
    if state == ('D', 'CLK'):
        assert eco.check(before, after, inputs)['equivalent_sequential_substitutions'] == 1
    else:
        with pytest.raises(ValueError):
            eco.check(before, after, inputs)


def test_inverted_combinational_cell_is_not_equivalent(design):
    before, after, inputs, lib, _ = design
    lib.write_text(lib.read_text().replace(cell('sg13g2_buf_1'), cell('sg13g2_buf_1', '!A')))
    inputs['liberty_sha256'] = digest(lib)
    with pytest.raises(ValueError):
        eco.check(before, after, inputs)


@pytest.mark.parametrize('extra', [
    'three_state : "A";',
    'statetable (A, X) { table : "- : - : -"; }',
    'ff (IQ, IQ_N) { next_state : "A"; clocked_on : "A"; }',
])
def test_unrecognized_state_or_tristate_cannot_be_silently_ignored(design, extra):
    before, after, inputs, lib, _ = design
    lib.write_text(lib.read_text().replace('cell (sg13g2_buf_8) {', 'cell (sg13g2_buf_8) { ' + extra))
    inputs['liberty_sha256'] = digest(lib)
    with pytest.raises(ValueError):
        eco.check(before, after, inputs)


def test_two_added_drivers_cannot_be_hidden_by_contraction(design):
    before, after, inputs, _, _ = design
    after.write_text(after.read_text().replace(' endmodule', ' sg13g2_buf_8 other (.A(n0),.X(eco_net)); endmodule'))
    inputs['new_buffer_drivers']['second'] = {}
    inputs['after_sha256'] = digest(after)
    with pytest.raises(ValueError, match='driver count'):
        eco.check(before, after, inputs)


def test_added_scalar_wire_is_permitted_but_added_vector_is_not(design):
    before, after, inputs, _, _ = design
    after.write_text(after.read_text().replace('wire n0,n1;', 'wire n0,n1; wire eco_net;'))
    inputs['after_sha256'] = digest(after)
    assert eco.check(before, after, inputs)['added_noninverting_buffers'] == 1
    after.write_text(after.read_text().replace('wire eco_net;', 'wire [0:0] eco_net;'))
    inputs['after_sha256'] = digest(after)
    with pytest.raises(ValueError, match='wire declaration'):
        eco.check(before, after, inputs)


def test_python_optimized_mode_cannot_disable_guard(design, tmp_path):
    before, after, inputs, _, _ = design
    inputs['after_sha256'] = '0' * 64
    path = tmp_path / 'inputs.json'
    path.write_text(json.dumps(inputs))
    result = subprocess.run([sys.executable, '-O', str(SCRIPT), str(before), str(after), str(path)], capture_output=True, text=True)
    assert result.returncode == 2
    assert json.loads(result.stdout)['status'] == 'ERROR'


@pytest.mark.parametrize('declaration,net', [
    ('input p', 'p'), ('input [1:0] p', 'p[0]'),
    ('input [0:1] p', 'p[1]'), ('input [9:8] p', 'p[8]'),
])
def test_primary_input_is_counted_as_exactly_one_driver(design, declaration, net):
    before, after, inputs, _, _ = design
    text = f'module chip(p,y); {declaration}; output y; sg13g2_buf_1 load (.A({net}),.X(y)); endmodule'
    before.write_text(text)
    after.write_text(text.replace(f'.A({net})', '.A(added_net)').replace(' endmodule',
        f' wire added_net; sg13g2_buf_8 eco (.A({net}),.X(added_net)); endmodule'))
    inputs.update(before_sha256=digest(before), after_sha256=digest(after), substitutions={})
    assert eco.check(before, after, inputs)['added_noninverting_buffers'] == 1
    # An internal output tied to that same primary input is a second driver.
    after.write_text(after.read_text().replace(' endmodule',
        f' sg13g2_buf_8 short (.A(added_net),.X({net})); endmodule'))
    inputs['after_sha256'] = digest(after)
    inputs['new_buffer_drivers']['short'] = {}
    with pytest.raises(ValueError, match='ECO net driver count'):
        eco.check(before, after, inputs)


@pytest.mark.parametrize('declaration', ['output p', 'inout p', 'input wire p'])
def test_output_inout_or_unparsed_declaration_cannot_supply_a_driver(design, declaration):
    before, after, inputs, _, _ = design
    text = f'module chip(p,y); {declaration}; output y; sg13g2_buf_1 load (.A(p),.X(y)); endmodule'
    before.write_text(text)
    after.write_text(text.replace('.A(p)', '.A(added_net)').replace(' endmodule',
        ' wire added_net; sg13g2_buf_8 eco (.A(p),.X(added_net)); endmodule'))
    inputs.update(before_sha256=digest(before), after_sha256=digest(after), substitutions={})
    with pytest.raises(ValueError):
        eco.check(before, after, inputs)


def test_inout_with_internal_driver_is_not_treated_as_unidirectional(design):
    before, after, inputs, _, _ = design
    for path in (before, after):
        path.write_text(path.read_text().replace('module chip(y);',
            'module chip(y,n0); inout n0;'))
    inputs.update(before_sha256=digest(before), after_sha256=digest(after))
    # The SRAM already drives n0, but an external inout driver could also
    # affect loads. A positive one-way buffer cannot prove that preserved.
    with pytest.raises(ValueError, match='Bidirectional primary ports'):
        eco.check(before, after, inputs)
