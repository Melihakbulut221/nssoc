# SPDX-FileCopyrightText: 2026 Hasan Melih Akbulut
# SPDX-License-Identifier: Apache-2.0
"""Hierarchy normalization must retain MOS data and reject ambiguous sources."""
from pathlib import Path
import sys

import pytest

FLOW = Path(__file__).resolve().parents[2] / 'hw/soc/flow'
sys.path.insert(0, str(FLOW))
try:
    from inline_cdl import inline
    from transistor_schematic import read_cdl
finally:
    sys.path.pop(0)


SOURCE = '''.subckt leaf VDD VSS A Y
M1 n A VSS VSS nmos W=0.78u L=0.13u
M2 Y n VDD VDD pmos W=2.12u L=0.13u
.ends leaf
.subckt parent power ground in out
Xa power ground in mid leaf
Xb power ground mid out leaf
.ends parent
'''


def convert(tmp_path, source=SOURCE, selected=('leaf',)):
    path = tmp_path / 'input.cir'
    path.write_text(source)
    defs, ports = read_cdl([path])
    return inline(defs, ports, selected)


def test_two_instances_keep_parameters_and_private_nodes(tmp_path):
    result = convert(tmp_path)
    assert set(result) == {'parent'}
    rows = [line.split() for line in result['parent'].splitlines()[1:-1]]
    assert len(rows) == 4
    assert len({row[0] for row in rows}) == 4
    assert rows[0][1] == rows[1][2]
    assert rows[2][1] == rows[3][2]
    assert rows[0][1] != rows[2][1]
    assert rows[0][2:5] == ['in', 'ground', 'ground']
    assert rows[1][1] == rows[2][2] == 'mid'
    assert rows[3][1] == 'out'
    assert rows[0][5:] == ['nmos', 'W=0.78u', 'L=0.13u']
    assert rows[1][5:] == ['pmos', 'W=2.12u', 'L=0.13u']


def test_nested_case_insensitive_helpers(tmp_path):
    source = SOURCE + '.subckt top p g a y\nXone p g a y PARENT\n.ends top\n'
    result = convert(tmp_path, source, ('LEAF', 'parent'))
    assert set(result) == {'top'}
    assert result['top'].count('W=') == 4


@pytest.mark.parametrize('before,after', [
    ('Xa power ground in mid leaf', 'Xa power ground in leaf'),
    ('M2 Y n VDD VDD', 'M1 Y n VDD VDD'),
    ('M1 n A VSS VSS nmos W=0.78u L=0.13u', 'R1 n A 100'),
    ('M1 n A VSS VSS nmos W=0.78u L=0.13u', 'Xrecursive VDD VSS A Y leaf'),
    ('M1 n A VSS VSS', 'M__cdl_inline_collision n A VSS VSS'),
    ('M1 n A VSS VSS', 'M1 __cdl_inline_collision A VSS VSS'),
    ('Xa power ground in mid leaf', 'Xa power ground in mid leaf scale=2'),
])
def test_invalid_helpers_fail_closed(tmp_path, before, after):
    with pytest.raises(ValueError):
        convert(tmp_path, SOURCE.replace(before, after))


def test_ground_and_tied_inputs_are_preserved(tmp_path):
    result = convert(tmp_path, SOURCE.replace('Xa power ground in mid leaf',
                                            'Xa power 0 power mid leaf'))
    rows = [line.split() for line in result['parent'].splitlines()[1:-1]]
    assert rows[0][2:5] == ['power', '0', '0']


def test_missing_selection_is_rejected(tmp_path):
    with pytest.raises(ValueError):
        convert(tmp_path, selected=('absent',))


def test_unrelated_definitions_are_verbatim(tmp_path):
    untouched = '.subckt empty vdd vss\n.ends empty'
    unrelated = '.subckt filler p g\nXtie p g empty\nXtie p g empty\n.ends filler'
    result = convert(tmp_path, SOURCE + untouched + '\n' + unrelated + '\n')
    assert result['filler'] == unrelated
    assert result['empty'] == untouched
