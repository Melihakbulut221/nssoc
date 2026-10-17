# SPDX-FileCopyrightText: 2026 Hasan Melih Akbulut
# SPDX-License-Identifier: Apache-2.0
"""Known two-address/byte-write readback and intentionally defective outputs."""
from pathlib import Path
import sys

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / 'hw/soc/flow'))
from measure_sp_sram_wave import analyze


def fixture(fault=None):
    a, b, c = 0xAAAAAAAAAAAAAAAA, 0x5555555555555555, 0xAAAA55AAAAAAAAAA
    plan = [dict(edge_ns=t, addr=addr, din=data, we=mask) for t, addr, data, mask in
            [(10, 0, a, 255), (30, 257, b, 255), (50, 0, 0, 0),
             (70, 257, 0, 0), (90, 0, c, 32), (110, 0, 0, 0), (130, 257, 0, 0)]]
    header = ['time', 'v(vdd)', 'v(clk)']
    header += [f'v({prefix}_{i})' for prefix, width in
               [('a', 9), ('we', 8), ('d', 64), ('q', 64)] for i in range(width)]
    rows = []
    for index in range(3001):
        t = index*.05
        clock = max(max(0, min(1, (t-item['edge_ns'])/.1,
                                  (item['edge_ns']+10-t)/.1)) for item in plan)
        selected = next((item for item in reversed(plan) if t >= item['edge_ns']-5), plan[0])
        values = [t*1e-9, 1.2, 1.2*clock]
        for field, width in [('addr', 9), ('we', 8), ('din', 64)]:
            values += [1.2*(selected[field] >> i & 1) for i in range(width)]
        for bit in range(64):
            output, previous = 0, 0
            for edge, word in [(50, a), (70, b), (110, c), (130, b)]:
                new = word >> bit & 1
                output += (new-previous)*max(0, min(1, (t-edge-.85)/.4))
                previous = new
            if fault == 'ignored_byte_write' and 126 < t < 129:
                output = a >> bit & 1
            if fault == 'stale_read_address' and 86 < t < 89:
                output = a >> bit & 1
            values.append(1.2*output)
        if fault == 'missing_edge' and 130 <= t <= 141:
            values[2] = 0
        rows.append(values)
    return header, rows, plan


def test_readback_byte_write_and_known_timing():
    result = analyze(*fixture())
    assert len(result['reads']) == 4
    assert result['reads'][2]['expected'] == 0xAAAA55AAAAAAAAAA
    assert result['characterization_complete'] is False
    for row in result['summary'].values():
        assert row['max_delay_ns'] == pytest.approx(1)
        assert row['max_slew_20_80_ns'] == pytest.approx(.24)


@pytest.mark.parametrize('fault', ['ignored_byte_write', 'stale_read_address', 'missing_edge'])
def test_reject_memory_faults(fault):
    with pytest.raises(ValueError):
        analyze(*fixture(fault))


@pytest.mark.parametrize('vdd', [1.08, 1.32])
def test_corner_supply_thresholds_and_wrong_supply(vdd):
    header, rows, plan = fixture()
    scaled = [[row[0], *(x*vdd/1.2 for x in row[1:])] for row in rows]
    result = analyze(header, scaled, plan, vdd)
    for row in result['summary'].values():
        assert row['max_delay_ns'] == pytest.approx(1)
        assert row['max_slew_20_80_ns'] == pytest.approx(.24)
    with pytest.raises(ValueError, match='Unexpected supply'):
        analyze(header, scaled, plan)


@pytest.mark.parametrize('vdd', [0, -1, float('inf'), float('nan')])
def test_invalid_supply(vdd):
    with pytest.raises(ValueError, match='Invalid SP supply'):
        analyze([], [], [], vdd)
