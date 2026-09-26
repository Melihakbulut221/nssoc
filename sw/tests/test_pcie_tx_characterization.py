# SPDX-FileCopyrightText: 2026 Hasan Melih Akbulut
# SPDX-License-Identifier: Apache-2.0
"""Guard measurement evidence, not just whether a SPICE process returns zero."""
from pathlib import Path
import sys

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[2]/'scripts'))
import characterize_pcie_tx as tx
import spdx_check


def test_prbs_period_and_balance():
    bits = tx.prbs7(count=261)
    assert bits[:7] == [1]*7
    assert bits[:127] == bits[127:254]
    assert sum(bits[:127]) == 64
    windows = {tuple(bits[i:i+7]) for i in range(127)}
    assert len(windows) == 127 and (0,)*7 not in windows
    assert tx.prbs7(108) != tx.prbs7(127)


@pytest.mark.parametrize('seed', [0, -1, 128])
def test_invalid_prbs_seed(seed):
    with pytest.raises(ValueError):
        tx.prbs7(seed)


def test_pvt_and_fault_coverage():
    cases = tx.cases()
    assert len({c['name'] for c in cases}) == len(cases) == 43
    assert len([c for c in cases if c['lanes'] == 4]) == 10
    assert {c['fault'] for c in cases} == {None, 'swapped', 'no_bias', 'overload'}
    assert {c['temp'] for c in cases} == {-40, 27, 125}
    assert {c['supply'] for c in cases} == {1.71, 1.8, 1.89}


@pytest.fixture
def wave(tmp_path, monkeypatch):
    monkeypatch.setattr(tx, 'BITS', 20)
    bits = [i % 2 for i in range(20)]
    path = tmp_path/'wave.dat'
    header = 'time v(avdd) i(vdd) v(op0) v(on0) v(xlane.tail) v(ref0) i(v.xlane.vtail)\n'
    rows = []
    for j in range(4501):
        t = j*1e-12
        bit = bits[max(0, min(19, int((t-tx.START)/tx.UI)))]
        op, on = (1.6, 1.2) if bit else (1.2, 1.6)
        rows.append(f'{t:.15g} 1.8 -.018 {op} {on} .55 .9 .016\n')
    path.write_text(header+''.join(rows))
    return path, dict(lanes=1, supply=1.8), [bits]


def test_measures_known_signal(wave):
    result = tx.measure(*wave)
    assert result['screen_pass']
    assert result['analog_supply_power_w'] == pytest.approx(.0324)
    lane = result['lanes'][0]
    assert lane['sign_errors'] == 0
    assert lane['samples'] == 12
    assert lane['min_signed_margin_v'] == pytest.approx(.4)
    assert lane['sampled_eye_height_v'] == pytest.approx(.8)


@pytest.mark.parametrize('fault', ['short', 'nan', 'wrong_header', 'time_gap'])
def test_rejects_corrupt_evidence(wave, fault):
    path, case, bits = wave
    lines = path.read_text().splitlines(keepends=True)
    if fault == 'short':
        lines = lines[:-10]
    elif fault == 'nan':
        lines[10] = lines[10].replace('1.8', 'nan')
    elif fault == 'wrong_header':
        lines[0] = lines[0].replace('v(op0)', 'v(ip0)')
    else:
        del lines[100]
    path.write_text(''.join(lines))
    with pytest.raises(ValueError):
        tx.measure(path, case, bits)


@pytest.mark.parametrize('fault', ['inverted', 'zero_signal', 'overvoltage', 'overcurrent'])
def test_physical_failures_cannot_pass(wave, fault):
    path, case, bits = wave
    lines = path.read_text().splitlines()
    for i in range(1, len(lines)):
        row = lines[i].split()
        if fault == 'inverted':
            row[3], row[4] = row[4], row[3]
        elif fault == 'zero_signal':
            row[3] = row[4] = '1.4'
        elif fault == 'overvoltage':
            row[6] = '1.7'
        else:
            row[7] = '.025'
        lines[i] = ' '.join(row)
    path.write_text('\n'.join(lines)+'\n')
    assert not tx.measure(path, case, bits)['screen_pass']


def test_spice_is_hardware_source():
    assert spdx_check.classify('hw/soc/analog/pcie/tx_cml.spice') == (
        'CERN-OHL-W-2.0', ('* ', ''))
