# SPDX-FileCopyrightText: 2026 Hasan Melih Akbulut
# SPDX-License-Identifier: Apache-2.0
"""Source-side LVS must not hide missing pins, bus swaps or changed device bodies."""
import copy
import importlib.util
import json
from pathlib import Path
import shutil
import subprocess
import sys

import pytest

SCRIPT = Path(__file__).resolve().parents[2] / 'hw/soc/flow/transistor_schematic.py'
SPEC = importlib.util.spec_from_file_location('transistor_schematic', SCRIPT)
SCHEMATIC = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(SCHEMATIC)


@pytest.fixture
def design():
    return {
        'ports': {'clk': {'bits': [2]}, 'y': {'bits': [3, 4]},
                  'VPWR': {'bits': [5]}, 'VGND': {'bits': [6]}},
        'cells': {
            'mem': {'type': 'RAM', 'parameters': {}, 'connections': {
                'CLK': [2], 'Q': [3, 4], 'VDD!': [5], 'VSS!': [6]}},
            'clock_load': {'type': 'INV', 'connections': {'A': [2], 'VDD': [5], 'VSS': [6]}}
        }
    }


PORTS = {'RAM': ['VDD!', 'VSS!', 'Q<1>', 'Q<0>', 'CLK'],
         'INV': ['Y', 'A', 'VDD', 'VSS']}
OUTPUTS = {'INV': {'Y'}}


def test_bus_order_power_and_distinct_floating_output(design):
    text, missing = SCHEMATIC.assemble(design, 'chip', PORTS, OUTPUTS)
    assert 'X0 VPWR VGND y[1] y[0] clk RAM' in text
    assert 'X1 float_1_Y clk VPWR VGND INV' in text
    assert missing == [{'instance': 'clock_load', 'type': 'INV', 'output': 'Y'}]
    swapped = copy.deepcopy(design)
    swapped['cells']['mem']['connections']['Q'] = [4, 3]
    assert 'X0 VPWR VGND y[0] y[1] clk RAM' in SCHEMATIC.assemble(swapped, 'chip', PORTS, OUTPUTS)[0]


def test_generated_square_bus_preserves_reference_order(design):
    ports = {**PORTS, 'RAM': ['VDD!', 'VSS!', 'Q[1]', 'Q[0]', 'CLK']}
    assert SCHEMATIC.assemble(design, 'chip', ports, OUTPUTS) == SCHEMATIC.assemble(
        design, 'chip', PORTS, OUTPUTS)
    with pytest.raises(ValueError, match='Noncontiguous'):
        SCHEMATIC.port_groups(['Q[0]', 'Q<0>'])


def test_unprefixed_cell_types_are_not_silently_omitted():
    text = '''module chip (a);
    SP6TSRAM512x64 \\ram.bank[0].mem  (.clk(a));
    DP8TSRAMDP256x16 fifo (.clk1(a));
    unexpected_missing_reference bad (.A(a));
    sg13g2_inv_1 u0 (.A(a));
    endmodule
    '''
    assert SCHEMATIC.instantiated_types(text) == {
        'SP6TSRAM512x64', 'DP8TSRAMDP256x16',
        'unexpected_missing_reference', 'sg13g2_inv_1'}


@pytest.mark.parametrize('pin', ['CLK', 'VDD!', 'VSS!'])
def test_missing_input_or_power_is_rejected(design, pin):
    del design['cells']['mem']['connections'][pin]
    with pytest.raises(ValueError, match='Missing input/power'):
        SCHEMATIC.assemble(design, 'chip', PORTS, OUTPUTS)


@pytest.mark.parametrize('bad', [[3], [3, 4, 7], ['x', 4], ['0', 4], ['1', 4]])
def test_wrong_bus_width_or_implicit_constant_is_rejected(design, bad):
    design['cells']['mem']['connections']['Q'] = bad
    with pytest.raises(ValueError):
        SCHEMATIC.assemble(design, 'chip', PORTS, OUTPUTS)


def test_missing_output_requires_authoritative_direction(design):
    with pytest.raises(ValueError, match='Missing input/power'):
        SCHEMATIC.assemble(design, 'chip', PORTS, {})
    assert SCHEMATIC.declared_outputs('module INV(Y,A); output Y; input A; endmodule') == OUTPUTS


@pytest.mark.parametrize('mutation', ['alias', 'constant', 'collision', 'ascending', 'unknown', 'parameter', 'extra'])
def test_ambiguous_connectivity_is_rejected(design, mutation):
    if mutation == 'alias':
        design['ports']['alias'] = {'bits': [2]}
    elif mutation == 'constant':
        design['ports']['clk']['bits'] = ['0']
    elif mutation == 'collision':
        design['ports']['float_1_Y'] = {'bits': [22]}
    elif mutation == 'ascending':
        design['ports']['y']['upto'] = 1
    elif mutation == 'unknown':
        design['cells']['mem']['type'] = 'NO_CDL'
    elif mutation == 'parameter':
        design['cells']['mem']['parameters'] = {'WIDTH': 2}
    else:
        design['cells']['mem']['connections']['EXTRA'] = [2]
    with pytest.raises(ValueError):
        SCHEMATIC.assemble(design, 'chip', PORTS, OUTPUTS)


def test_generated_internal_net_cannot_alias_top(design):
    design['ports']['n100'] = {'bits': [200]}
    design['cells']['mem']['connections']['CLK'] = [100]
    with pytest.raises(ValueError, match='collides'):
        SCHEMATIC.assemble(design, 'chip', PORTS, OUTPUTS)


def test_cdl_bodies_are_preserved_and_deduplicated(tmp_path):
    a, b = tmp_path / 'a.cdl', tmp_path / 'b.cdl'
    body = '.SUBCKT INV Y A VDD VSS\nMP Y A VDD VDD sg13_lv_pmos w=1u l=0.13u\n.ENDS INV'
    a.write_text('* source\n' + body + '\n')
    b.write_text(body + '\n')
    definitions, ports = SCHEMATIC.read_cdl([a, b])
    assert definitions == {'INV': body}
    assert ports == {'INV': ['Y', 'A', 'VDD', 'VSS']}
    b.write_text(body.replace('w=1u', 'w=2u'))
    with pytest.raises(ValueError, match='Conflicting'):
        SCHEMATIC.read_cdl([a, b])


@pytest.mark.parametrize('declaration', ['.GLOBAL VDD VSS', '*.GLOBAL sub!'])
def test_global_directives_cannot_be_silently_discarded(tmp_path, declaration):
    path = tmp_path / 'x.cdl'
    path.write_text(declaration + '\n.SUBCKT INV Y A\n.ENDS INV\n')
    with pytest.raises(ValueError, match='outside subcircuits'):
        SCHEMATIC.read_cdl([path])


def test_multiple_cdl_globals_keep_case_order_and_verbatim_bodies(tmp_path):
    a, b = tmp_path/'a.cdl', tmp_path/'b.cdl'
    left = '.SUBCKT LEFT a b\nR0  a sub! 1000\nR1 sub! b 1000\n.ENDS LEFT'
    right = '.SUBCKT RIGHT a b\nX0 a\n+ b LEFT\n.ENDS RIGHT'
    a.write_text('*.GLOBAL sub!\n' + left + '\n')
    b.write_text('.GLOBAL sub! WELL!\n' + right + '\n')
    cells, ports, globals_ = SCHEMATIC.read_cdl_with_globals([a, b])
    assert cells == {'LEFT': left, 'RIGHT': right}
    assert ports == {'LEFT': ['a', 'b'], 'RIGHT': ['a', 'b']}
    assert globals_ == ['sub!', 'WELL!']
    b.write_text('.GLOBAL SUB!\n' + right + '\n')
    with pytest.raises(ValueError, match='Ambiguous global-name case'):
        SCHEMATIC.read_cdl_with_globals([a, b])
    b.write_text('.GLOBAL sub!\n' + left.replace('1000', '1001') + '\n')
    with pytest.raises(ValueError, match='Conflicting CDL definition'):
        SCHEMATIC.read_cdl_with_globals([a, b])


@pytest.mark.parametrize('line', ['.INCLUDE another.cdl', '.CONNECT sub! VSS',
    '.GLOBAL', '*.GLOBAL sub! SUB!', '.PARAM R=1', '+ sub!'])
def test_retaining_reader_refuses_unknown_or_ambiguous_outside_lines(line):
    with pytest.raises(ValueError):
        SCHEMATIC.parse_cdl_text(line + '\n.SUBCKT leaf a b\nR0 a b 1000\n.ENDS leaf\n')


def test_retaining_reader_never_infers_global_from_bang_or_prose():
    body = '.SUBCKT leaf a b\nR0 a sub! 1000\nR1 sub! b 1000\n.ENDS leaf'
    cells, _, globals_ = SCHEMATIC.parse_cdl_text('* .GLOBAL is merely prose\n' + body + '\n')
    assert cells == {'leaf': body} and globals_ == []
    with pytest.raises(ValueError, match='outside subcircuits'):
        SCHEMATIC.parse_cdl_text(body.replace('R0', '*.GLOBAL sub!\nR0'))
    with pytest.raises(ValueError, match='LF newlines'):
        SCHEMATIC.parse_cdl_text(body.replace('\n', '\r\n'))


@pytest.mark.parametrize('kind', ['internal', 'floating'])
def test_declared_global_cannot_alias_generated_unrelated_net(design, kind):
    if kind == 'internal':
        design['cells']['mem']['connections']['CLK'] = [100]
        globals_ = ['N100']
    else:
        globals_ = ['FLOAT_1_y']
    with pytest.raises(ValueError, match='collides with declared global'):
        SCHEMATIC.assemble(design, 'chip', PORTS, OUTPUTS, globals_)


@pytest.mark.parametrize('declared', [False, True])
def test_full_chip_cli_preserves_explicit_globals_and_uninferred_hierarchical_nodes(tmp_path, declared):
    # This executes the real Yosys connectivity reader on a two-cell circuit.
    # It is source construction, not transistor extraction or an LVS verdict.
    assert shutil.which('yosys'), 'The small integration test requires the installed Yosys reader'
    body = '.SUBCKT CELL A Y VDD VSS\nR0 A sub! 1000\nR1 sub! Y 1000\n.ENDS CELL'
    unused = '.SUBCKT UNUSED A Y\nR0 A local! 500\nR1 local! Y 500\n.ENDS UNUSED'
    a, b = tmp_path/'cells.cdl', tmp_path/'more.cdl'
    a.write_text(('*.GLOBAL sub!\n' if declared else '') + body + '\n')
    b.write_text(('.GLOBAL sub! WELL!\n' if declared else '') + unused + '\n')
    models = tmp_path/'models.v'
    models.write_text('module CELL (A,Y,VDD,VSS); input A; output Y; inout VDD,VSS; endmodule\n')
    powered = tmp_path/'powered.v'
    powered.write_text('''module chip(input a, output y, inout p, inout n);
wire middle;
CELL u0(.A(a), .Y(middle), .VDD(p), .VSS(n));
CELL u1(.A(middle), .Y(y), .VDD(p), .VSS(n));
endmodule
''')
    output = tmp_path/'result'
    completed = subprocess.run([sys.executable, str(SCRIPT), str(powered), '--top', 'chip',
        '--cdl', str(a), '--cdl', str(b), '--standard-cell-verilog', str(models), '--output', str(output)],
        capture_output=True, text=True, check=False)
    assert completed.returncode == 0, completed.stderr
    text = (output/'schematic.cir').read_text()
    cells, _, globals_ = SCHEMATIC.parse_cdl_text(text)
    assert cells['CELL'] == body
    assert set(cells) == {'CELL', 'chip'}
    assert sum(line.endswith(' CELL') for line in cells['chip'].splitlines()) == 2
    assert globals_ == (['sub!', 'WELL!'] if declared else [])
    assert ('.GLOBAL ' in text) is declared
    receipt = json.loads((output/'sources.json').read_text())
    assert receipt['globals'] == globals_
    assert receipt['explicit_global_declarations_preserved'] is True
    assert receipt['excluded_uninstantiated_definitions'] == ['UNUSED']
    assert receipt['sources'][str(a.resolve())] == SCHEMATIC.digest(a)
    assert receipt['sources'][str(b.resolve())] == SCHEMATIC.digest(b)


@pytest.mark.parametrize('pins', [['Q<0>', 'Q<2>'], ['Q', 'Q<0>'], ['Q<0>', 'Q<0>']])
def test_ambiguous_cdl_bus_rejected(pins):
    with pytest.raises(ValueError):
        SCHEMATIC.port_groups(pins)


def test_interface_preserves_escaped_supply_and_bus_range():
    text = SCHEMATIC.interfaces({'RAM'}, PORTS)
    assert 'inout \\VDD! ;' in text
    assert 'inout [1:0] \\Q ;' in text


def test_reachable_cdl_preserves_shared_device_bodies_and_continuations():
    definitions = {
        'MEM': '.SUBCKT MEM A B\nX1 A\n+ B leaf\nX2 B A LEAF\n.ENDS',
        'LEAF': '.SUBCKT LEAF A B\nR1 A B lvsres w=0.26u l=0.6u\n.ENDS',
        'UNUSED': '.SUBCKT UNUSED A\nX1 A MISSING\n.ENDS',
    }
    assert SCHEMATIC.reachable_cdl(definitions, ['mem']) == {
        name: definitions[name] for name in ('MEM', 'LEAF')}
    # Making a previously unused helper reachable must reveal its missing body.
    with pytest.raises(ValueError, match='Unresolved'):
        SCHEMATIC.reachable_cdl(definitions, ['MEM', 'UNUSED'])


@pytest.mark.parametrize('call, message', [
    ('X1 A MISSING', 'Unresolved'),
    ('X1 A MEM', 'Recursive'),
    ('X1 A LEAF P=1', 'parameterized'),
    ('X1', 'parameterized'),
])
def test_reachable_cdl_refuses_incomplete_or_ambiguous_hierarchy(call, message):
    definitions = {'MEM': '.SUBCKT MEM A\n' + call + '\n.ENDS',
                   'LEAF': '.SUBCKT LEAF A\n.ENDS'}
    with pytest.raises(ValueError, match=message):
        SCHEMATIC.reachable_cdl(definitions, ['MEM'])
