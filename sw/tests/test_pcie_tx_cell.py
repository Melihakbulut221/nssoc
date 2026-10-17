# SPDX-FileCopyrightText: 2026 Hasan Melih Akbulut
# SPDX-License-Identifier: Apache-2.0
"""Check extracted-device translation without inventing metal parasitics."""
from pathlib import Path
import sys

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[2]/'scripts'))
from translate_pcie_tx_cell import number, translate

EXTRACTED = r'''.SUBCKT nssoc_tx_cml_layout INP INN AVDD AVSS IREF OUTN OUTP SUB
R$1 SUB \$9 ptap1 A=32p P=64u
R$9 OUTN AVDD \$9 rsil w=10u l=70.215u ps=0u b=0 m=1
R$10 OUTP AVDD \$9 rsil w=10u l=70.215u ps=0u b=0 m=1
Q$11 OUTN INP \$19 \$9 npn13G2 we=70n le=900n Nx=8 m=1
Q$12 OUTP INN \$19 \$9 npn13G2 we=70n le=900n Nx=8 m=1
Q$13 \$19 IREF AVSS \$9 npn13G2 we=70n le=900n Nx=8 m=1
Q$14 IREF IREF AVSS \$9 npn13G2 we=70n le=900n Nx=1 m=1
.ENDS nssoc_tx_cml_layout
'''


def test_all_devices_and_substrate_contact_remain_in_simulation():
    result, record = translate(EXTRACTED, .980e-9, .980e-3)
    assert '.subckt nssoc_tx_cml_rsil inp inn outp outn avdd avss sub iref' in result
    assert record['tap_resistance_ohm'] == pytest.approx(81.6666666667/8)
    assert len(record['source_devices']) == 7
    assert sum(line.startswith('XQ') for line in result.splitlines()) == 4
    assert sum(line.startswith('XR') for line in result.splitlines()) == 2
    assert sum(line.startswith('V') for line in result.splitlines()) == 3
    assert 'VTAIL tailmon avss 0' in result
    assert 'OUTN' not in result
    assert not record['qualified_pex'] and not record['interconnect_parasitics_included']
    assert not record['substrate_spatial_parasitics_included']


@pytest.mark.parametrize('old,new', [
    ('nssoc_tx_cml_layout','wrong_top'), ('OUTP SUB\n','OUTP OUTP\n'),
    ('R$10','R$9'), ('ptap1','ntap1'), ('npn13G2','npn13G2v'),
    ('Nx=8','Nx=0'), ('we=70n','we=NaN'), ('w=10u','w=-10u'),
    ('ps=0u','ps=1u'), ('b=0','b=1'), ('P=64u','P=64u P=64u'),
    ('P=64u','P=64u extra=1'), ('Q$13 \\$19 IREF','Q$13 \\$19 INN'),
    ('R$9 OUTN AVDD','R$9 OUTN INN'), ('Q$12 OUTP INN \\$19','Q$12 OUTP INN \\$20'),
])
def test_unknown_or_malformed_device_inventory_fails_closed(old,new):
    assert old in EXTRACTED
    with pytest.raises(ValueError): translate(EXTRACTED.replace(old,new), .980e-9, .980e-3)


@pytest.mark.parametrize('value', ['NaN','inf','1meg','0','-1','1e999','1u;quit'])
def test_numeric_parser_rejects_nonphysical_or_injected_values(value):
    with pytest.raises(ValueError): number(value)


@pytest.mark.parametrize('area,perimeter', [(0,1),(1,-1),(float('nan'),1),(1,float('inf'))])
def test_tap_model_coefficients_must_be_finite_and_positive(area,perimeter):
    with pytest.raises(ValueError): translate(EXTRACTED,area,perimeter)


def test_reordered_extraction_does_not_change_device_connections():
    rows=EXTRACTED.splitlines()
    _, first=translate(EXTRACTED,.980e-9,.980e-3)
    _, second=translate('\n'.join([rows[0],*reversed(rows[1:-1]),rows[-1]]),.980e-9,.980e-3)
    assert sorted(first['source_devices'],key=lambda d:d['id']) == sorted(second['source_devices'],key=lambda d:d['id'])
    assert first['tap_resistance_ohm']==second['tap_resistance_ohm']
