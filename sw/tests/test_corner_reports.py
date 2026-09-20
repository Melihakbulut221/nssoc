# SPDX-FileCopyrightText: 2026 Hasan Melih Akbulut
# SPDX-License-Identifier: Apache-2.0
"""Diagnostic report parsing must not erase failures or ambiguous paths."""
import importlib.util
from pathlib import Path
import subprocess
import sys

import pytest

FLOW = Path(__file__).resolve().parents[2] / 'hw/soc/flow'
spec = importlib.util.spec_from_file_location('probe_generated_clock_corners', FLOW / 'probe_generated_clock_corners.py')
probe = importlib.util.module_from_spec(spec)
spec.loader.exec_module(probe)
sys.modules[spec.name] = probe
spec = importlib.util.spec_from_file_location('route_reports', FLOW / 'report_route_corners.py')
route = importlib.util.module_from_spec(spec)
spec.loader.exec_module(route)


def test_electrical_sections_can_change_order():
    report = ('max fanout\n\nPin   Limit Fanout Slack\n--------\n'
              'buf/X 8 9 -1 (VIOLATED)\n\nmax slew\n'
              'ram/A_DIN[5] .38 .39 -.01 (VIOLATED)\n'
              'max capacitance\ncap/X .3 .4 -.1 (VIOLATED)\n')
    assert route.electrical_counts(report) == dict(slew=1, capacitance=1, fanout=1)
    assert route.electrical_counts('') == dict(slew=0, capacitance=0, fanout=0)


@pytest.mark.parametrize('text', ['Error: report failed', 'buf/X 8 9 -1 (VIOLATED)',
                                 'max slew\nmax slew\n', 'max slew\nx .38 nan -.1 (VIOLATED)',
                                 'max slew\nTRUNCATED', 'Pin Limit Slew Slack'])
def test_incomplete_or_unknown_electrical_report_rejected(text):
    with pytest.raises(ValueError):
        route.electrical_counts(text)


def path(endpoint, value):
    return f'Startpoint: data\nEndpoint: {endpoint}\n {value} slack (VIOLATED)\n'


def test_ordinary_and_generated_paths_preserve_negative_slack():
    assert probe.slacks(path('ff', '-0.3') + path('q', '-0.2')) == dict(ff=-.3, q=-.2)


@pytest.mark.parametrize('text', ['', path('q', '-.2'), path('q', '-.2') * 2,
                                 path('ff', '-.3') + path('unexpected', '-.2')])
def test_missing_duplicate_and_unexpected_paths_rejected(text):
    with pytest.raises(ValueError):
        probe.slacks(text)


def test_tcl_path_is_literal_with_substitutions(tmp_path):
    value = tmp_path / 'braces{} $env(HOME) [exit 99] ; ü'
    result = subprocess.run(['tclsh'], input='puts ' + probe.tcl_path(value) + '\n',
                            capture_output=True, text=True, check=True)
    assert result.stdout.rstrip('\n') == str(value)
