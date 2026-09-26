# SPDX-FileCopyrightText: 2026 Hasan Melih Akbulut
# SPDX-License-Identifier: Apache-2.0
"""Source-side LVS must not hide missing pins, bus swaps or changed device bodies."""
import copy
import importlib.util
from pathlib import Path

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


def test_global_directives_cannot_be_silently_discarded(tmp_path):
    path = tmp_path / 'x.cdl'
    path.write_text('.GLOBAL VDD VSS\n.SUBCKT INV Y A\n.ENDS INV\n')
    with pytest.raises(ValueError, match='outside subcircuits'):
        SCHEMATIC.read_cdl([path])


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
