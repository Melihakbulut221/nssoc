# SPDX-FileCopyrightText: 2026 Hasan Melih Akbulut
# SPDX-License-Identifier: Apache-2.0
"""Model interfaces and fail-closed native result parsing for the private pilot."""
import importlib.util
from pathlib import Path
import sys

import pytest

SCRIPTS = Path(__file__).resolve().parents[2] / 'scripts'
sys.path.insert(0, str(SCRIPTS))
spec = importlib.util.spec_from_file_location('bank_hybrid_test', SCRIPTS / 'build_pcie_bank_hybrid_v1.py')
h = importlib.util.module_from_spec(spec)
spec.loader.exec_module(h)
import measure_pcie_bank_wires_v1 as m  # noqa: E402


def test_pmos_native_and_model_order_are_different():
    assert h.NATIVE_ORDER['sg13_hv_pmos'] == ['S', 'G', 'D', 'B']
    assert h.MODEL_ORDER['sg13_hv_pmos'] == ['D', 'G', 'S', 'B']


def test_esd_polarities_keep_three_distinct_native_terminals():
    assert h.MODEL_ORDER['diodevdd_2kv'] == ['B', 'E', 'C']
    assert h.MODEL_ORDER['diodevss_2kv'] == ['C', 'E', 'B']


@pytest.mark.parametrize('name', ['ptap1', 'ntap1'])
def test_actual_square_contact_uses_foundry_area_perimeter_formula(name):
    d = dict(model=name, parameters=dict(A=4.0, P=8.0))
    tech = {name + '_raspec': '0.980n', name + '_rpspec': '0.980m'}
    p = h.model_params(d, tech)
    assert abs(h.number(p['R']) - h.Decimal(245) / 3) < h.Decimal('1e-24')
    assert p['w'] == p['l'] == '2u'
    assert p['R'] != '262.8'


@pytest.mark.parametrize('params', [dict(A=8, P=8), dict(A=4, P=9), dict(A=0, P=0)])
def test_contact_geometry_does_not_silently_inherit_default(params):
    with pytest.raises(ValueError, match='Contact geometry'):
        h.model_params(dict(model='ptap1', parameters=params), {})


def test_hbt_dimensions_and_multiplier():
    d = dict(model='npn13G2', parameters=dict(Nx=4.0, we=0.07, le=0.9, m=1.0))
    assert h.model_params(d, {}) == dict(Nx='4', we='0.07u', le='0.9u')
    d['parameters']['m'] = 2
    with pytest.raises(ValueError, match='multiplier'):
        h.model_params(d, {})


def test_mim_geometry_is_not_independently_fitted():
    d = dict(model='cap_cmim', parameters=dict(w=12.2, l=12, A=146.4, P=48.4, m=1))
    assert h.model_params(d, {}) == dict(w='12.2u', l='12u')
    d['parameters']['A'] = 144
    with pytest.raises(ValueError, match='MIM geometry'):
        h.model_params(d, {})


@pytest.mark.parametrize('bad', ['nan', 'inf', '1e309x', '2mil', '1;quit', 'abc'])
def test_invalid_spice_numbers_rejected(bad):
    with pytest.raises(ValueError):
        h.number(bad)


def test_float_serialization_mapping_is_exact_not_tolerance():
    assert h.geometry_decimal('38.400000000000006') == h.Decimal('38.4')
    assert h.geometry_decimal('38.400000000000007') != h.Decimal('38.4')
    assert h.geometry_decimal('12.200000000000001') == h.Decimal('12.2')
    assert h.geometry_decimal('12.200000000000002') != h.Decimal('12.2')


@pytest.mark.parametrize('wrong', [
    'X1 b c e body npn13G2 Nx=1',  # actual anchor swap
    'X1 c b e return npn13G2 Nx=1',  # body short
    'X1 c b e body npn13G2 Nx=2',
    '',
    'X1 c b e body npn13G2 Nx=1\nRshort c b 0',
])
def test_output_device_anchor_body_and_extra_short_changes_reject(wrong):
    with pytest.raises(ValueError, match='contract changed'):
        h.verify_output(wrong, 'X1 c b e body npn13G2 Nx=1')


def write_ac(path, mode='good'):
    header = ['frequency'] + [v for n in m.VECTORS for v in (n, n)]
    fs = [1e9, 8e9, 15e9]
    rows = [[f] + [v for i in range(24) for v in ((0.3 if i % 2 == 0 else -0.3), -0.1)] for f in fs]
    if mode == 'missing_frequency':
        rows.pop()
    elif mode == 'wrong_frequency':
        rows[1][0] = 7e9
    elif mode == 'wrong_vector':
        header[1] = 'v(unobserved)'
    elif mode == 'missing_imaginary':
        rows[1].pop()
    elif mode == 'nan':
        rows[1][3] = float('nan')
    path.write_text(' '.join(header) + '\n' + '\n'.join(' '.join(map(str, r)) for r in rows) + '\n')


def test_ac_reads_actual_complex_pairs_and_exact_frequency_grid(tmp_path):
    p = tmp_path / 'ac.dat'; write_ac(p)
    q = m.read_ac(p)
    assert q[1][0] == 8e9 and q[1][1][0] == complex(0.3, -0.1)


@pytest.mark.parametrize('mode', ['missing_frequency', 'wrong_frequency', 'wrong_vector', 'missing_imaginary', 'nan'])
def test_ac_missing_or_forged_fields_reject(tmp_path, mode):
    p = tmp_path / 'ac.dat'; write_ac(p, mode)
    with pytest.raises(ValueError):
        m.read_ac(p)


def test_native_warning_or_completion_loss_cannot_pass(tmp_path):
    for log in ['NSSOC_PASSIVE_WIRE_COMPLETE\nWarning: singular matrix', '',
                'NSSOC_PASSIVE_WIRE_COMPLETE\nNSSOC_PASSIVE_WIRE_COMPLETE']:
        (tmp_path / 'native.log').write_text(log)
        with pytest.raises(ValueError, match='Native incomplete'):
            m.measure(tmp_path)
