# SPDX-FileCopyrightText: 2026 Hasan Melih Akbulut
# SPDX-License-Identifier: Apache-2.0
"""A successful process or partial comparison must not masquerade as LVS."""
import importlib.util
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
spec = importlib.util.spec_from_file_location(
    'lvs_audit', ROOT / 'hw/soc/flow/audit_klayout_lvs.py')
audit = importlib.util.module_from_spec(spec)
spec.loader.exec_module(audit)
SUCCESS = 'INFO : Congratulations! Netlists match.'


def matched():
    return {'layout': 'memory', 'schematic': 'MEMORY', 'status': 'Match',
            'layout_devices_recursive': 4096, 'schematic_devices_recursive': 4096}


def test_complete_match_including_spice_case_normalization():
    assert not audit.assess([matched()], 'memory', SUCCESS)['reasons']


@pytest.mark.parametrize('status', [
    'Skipped', 'NoMatch', 'Mismatch', 'MatchWithWarning', 'None', 'future-status'])
def test_any_unresolved_circuit_rejects_a_positive_banner(status):
    child = dict(matched(), layout='leaf', schematic='LEAF', status=status)
    result = audit.assess([matched(), child], 'memory', SUCCESS)
    assert result['status'] == 'FAIL'


@pytest.mark.parametrize('side', ['layout', 'schematic'])
def test_missing_circuit_is_not_a_match(side):
    row = matched()
    row[side] = None
    assert audit.assess([row], 'memory', SUCCESS)['reasons']


@pytest.mark.parametrize('rows', [[], [matched(), matched()]])
def test_empty_and_ambiguous_top_comparisons_fail(rows):
    assert audit.assess(rows, 'memory', SUCCESS)['reasons']


@pytest.mark.parametrize('side', ['layout', 'schematic'])
def test_empty_top_cannot_borrow_unrelated_devices(side):
    top = matched()
    top[side + '_devices_recursive'] = 0
    child = dict(matched(), layout='unrelated', schematic='UNRELATED')
    assert audit.assess([top, child], 'memory', SUCCESS)['reasons']


@pytest.mark.parametrize('log', ['', 'ERROR : Netlists don\'t match',
                                SUCCESS + '\nERROR : Netlists don\'t match'])
def test_deck_failure_after_compare_is_not_hidden(log):
    assert audit.assess([matched()], 'memory', log)['reasons']


def test_other_top_is_not_evidence_for_requested_top():
    assert audit.assess([matched()], 'different_memory', SUCCESS)['reasons']
