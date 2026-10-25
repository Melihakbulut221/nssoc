# SPDX-FileCopyrightText: 2026 Hasan Melih Akbulut
# SPDX-License-Identifier: Apache-2.0
"""Independent analytic signals and adversarial waveform controls."""
import copy
from pathlib import Path
import sys

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / 'hw/soc/flow'))
from measure_sram_wave import analyze, crossings, read_wave


def fixture():
    header = ['time', 'v(vdd)', 'v(clk1)', 'v(clk2)']
    header += [f'v({node}_{i})' for node, width in
               [('a1', 8), ('a2', 8), ('we1', 2), ('we2', 2),
                ('d1', 16), ('d2', 16), ('q2', 16)] for i in range(width)]
    header += ['i(vvdd)']
    config = dict(voltage=1.2, maxstep_ns=.05, input_transition_ns=.1,
                  write_schedule=[dict(edge=t, addr=0, data=d, we=3)
                                  for t, d in [(10, 0), (18, 65535), (26, 0)]],
                  read_schedule=[dict(edge=t, addr=0) for t in [14, 22, 30]])
    rows = []
    for i in range(801):
        t = i*.05
        values = {'v(vdd)': 1.2, 'i(vvdd)': -.001}
        for port, edges in [(1, [10, 18, 26]), (2, [14, 22, 30])]:
            clock = 0.0
            for edge in edges:
                clock = max(clock, max(0, min(1, (t-edge)/.1, (edge+4-t)/.1)))
            values[f'v(clk{port})'] = 1.2*clock
        # 1 ns clock50->output50 delay; 0.4 ns full swing -> 0.24 ns 20-80.
        output = max(0, min(1, (t-22.85)/.4)) - max(0, min(1, (t-30.85)/.4))
        for key in header[4:-1]:
            values[key] = (1.2*output if key.startswith('v(q2_') else
                           1.2 if key.startswith('v(we1_') or
                           (key.startswith('v(d1_') and 16 <= t < 24) else 0)
        rows.append([t*1e-9] + [values[k] for k in header[1:]])
    return header, rows, config


def test_known_delay_slew_and_supply_integral():
    result = analyze(*fixture())
    for direction in ['rise', 'fall']:
        row = result['summary'][direction]
        assert row['count'] == 16
        assert row['max_delay_ns'] == pytest.approx(1)
        assert row['max_slew_20_80_ns'] == pytest.approx(.24)
    assert result['supply_energy']['mean_mw'] == pytest.approx(1.2)
    assert result['supply_energy']['total_pj'] == pytest.approx(38.4)
    assert result['characterization_complete'] is False


def test_crossing_interpolation_not_nearest_sample():
    assert crossings([[0, 0], [2, 1]], 1, .2) == pytest.approx([.4])
    assert crossings([[0, 1], [2, 0]], 1, .2, False) == pytest.approx([1.6])


@pytest.mark.parametrize('fault', ['wrong_output', 'false_clock', 'wrong_address',
                                  'wrong_enable', 'supply', 'current_sign',
                                  'missing_column', 'clock_slew'])
def test_actual_measurement_rejects_fault(fault):
    header, rows, config = fixture()
    if fault == 'clock_slew':
        config['input_transition_ns'] = .5
    elif fault == 'missing_column':
        header[header.index('v(a2_0)')] = 'unobserved_address'
    else:
        for row in rows:
            t = row[0]*1e9
            if fault == 'wrong_output' and 28 < t < 29:
                row[header.index('v(q2_0)')] = 0
            if fault == 'false_clock' and 20 < t < 20.5:
                row[header.index('v(clk2)')] = 1.2
            if fault == 'wrong_address' and 22 < t < 22.2:
                row[header.index('v(a2_0)')] = 1.2
            if fault == 'wrong_enable' and 18 < t < 18.2:
                row[header.index('v(we1_0)')] = 0
            if fault == 'supply':
                row[header.index('v(vdd)')] = .8
            if fault == 'current_sign':
                row[header.index('i(vvdd)')] *= -1
    with pytest.raises(ValueError):
        analyze(header, rows, config)


@pytest.mark.parametrize('fault', ['nan', 'missing_sample', 'reverse_time', 'truncated',
                                  'missing_value', 'duplicate_header'])
def test_wave_reader_rejects_corruption(tmp_path, fault):
    header, rows, _ = fixture()
    rows = copy.deepcopy(rows)
    if fault == 'nan':
        rows[100][1] = float('nan')
    elif fault == 'missing_sample':
        del rows[100]
    elif fault == 'reverse_time':
        rows[100][0] = rows[99][0]
    elif fault == 'truncated':
        rows.pop()
    elif fault == 'missing_value':
        rows[100].pop()
    elif fault == 'duplicate_header':
        header[-1] = header[-2]
    wave = tmp_path / 'wave.txt'
    wave.write_text(' '.join(header)+'\n'+'\n'.join(' '.join(map(str, r)) for r in rows))
    with pytest.raises(ValueError):
        read_wave(wave, .05, 40)
