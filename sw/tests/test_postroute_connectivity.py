# SPDX-FileCopyrightText: 2026 Hasan Melih Akbulut
# SPDX-License-Identifier: Apache-2.0
"""Reject routing changes that a physical-cell-only comparison must not hide."""
import importlib.util
import json
from pathlib import Path
import subprocess
import sys

import pytest

FLOW = Path(__file__).resolve().parents[2] / 'hw/soc/flow'
spec = importlib.util.spec_from_file_location('postroute', FLOW / 'check_postroute_connectivity.py')
postroute = importlib.util.module_from_spec(spec)
sys.path.insert(0, str(FLOW))
try:
    spec.loader.exec_module(postroute)
finally:
    sys.path.pop(0)


@pytest.fixture
def design(tmp_path):
    before, after = tmp_path / 'before.v', tmp_path / 'after.v'
    before.write_text('module chip(a,y); input a; output [1:0] y; '
                      'wire [1:0] n; assign y=n; '
                      'BUF b0 (.A(a),.X(n[0])); BUF b1 (.A(a),.X(n[1])); endmodule')
    after.write_text(before.read_text().replace('endmodule',
        'sg13g2_antennanp d0 (.A(n[0])); sg13g2_fill_1 f0 (); '
        'sg13g2_decap_8 f1 (); endmodule'))
    return before, after


def test_original_bus_and_physical_additions(design):
    result = postroute.check(*design)
    assert result['original_instances'] == 2
    assert result['added_instances'] == {'antenna': 1, 'filler_or_decap': 2}
    assert 'Separate LVS required' in result['scope']


@pytest.mark.parametrize('old,new', [
    ('BUF b0', 'INV b0'),
    ('BUF b0 (.A(a),.X(n[0]));', ''),
    ('b0 (.A(a)', 'b0 (.A(n[1])'),
    ('b0 (.A(a),.X(n[0]))', 'b0 (.A(a),.X(n[0]),.Y(y[0]))'),
    ('output [1:0] y', 'output [0:1] y'),
    ('assign y=n', 'assign y=~n'),
    ('wire [1:0] n', 'wire [0:1] n'),
    ('wire [1:0] n;', ''),
    ('d0 (.A(n[0]))', 'd0 (.A(floating))'),
    ('d0 (.A(n[0]))', 'd0 (.A({n[0],n[1]}))'),
    ('d0 (.A(n[0]))', 'd0 (.A(1\'b0))'),
    ('d0 (.A(n[0]))', 'd0 (.A(n[0]),.X(y[0]))'),
    ('d0 (.A(n[0]))', 'd0 (.A(n[0]),.A(n[1]))'),
    ('sg13g2_antennanp d0', 'sg13g2_buf_1 d0'),
    ('f0 ()', 'f0 (.A(a))'),
    ('sg13g2_fill_1 f0', 'sg13g2_fill_fake f0'),
    ('sg13g2_decap_8 f1', 'sg13g2_other_8 f1'),
    ('endmodule', 'unexpected statement; endmodule'),
])
def test_logic_or_unsupported_physical_changes_fail(design, old, new):
    before, after = design
    assert old in after.read_text()
    after.write_text(after.read_text().replace(old, new))
    with pytest.raises(ValueError):
        postroute.check(before, after)


def test_cli_preserves_existing_record(design, tmp_path):
    output = tmp_path / 'verdict.json'
    command = [sys.executable, str(FLOW / 'check_postroute_connectivity.py'),
               *map(str, design), str(output)]
    result = subprocess.run(command, capture_output=True, text=True)
    assert result.returncode == 0, result.stderr
    original = output.read_bytes()
    assert json.loads(original)['original_instances'] == 2
    assert subprocess.run(command, capture_output=True).returncode != 0
    assert output.read_bytes() == original
