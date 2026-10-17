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


@pytest.mark.parametrize('severity', ['Warning', 'Error', 'NoSeverity', 'future-severity'])
def test_extraction_diagnostics_reject_an_otherwise_successful_comparison(severity):
    entry = {'severity': severity, 'category': 'must-connect', 'cell': 'memory',
             'message': 'Must-connect subnets of VDD must be connected further up'}
    result = audit.assess([matched()], 'memory', SUCCESS, [entry])
    assert result['status'] == 'FAIL'
    assert result['extraction_diagnostics'] == [entry]


def test_must_connect_cannot_be_downgraded_to_information():
    entry = {'severity': 'Info', 'category': 'must-connect'}
    assert audit.assess([matched()], 'memory', SUCCESS, [entry])['status'] == 'FAIL'


def test_unclassified_extraction_warning_also_requires_review():
    entry = {'severity': 'Warning', 'category': 'unknown-extractor'}
    assert audit.assess([matched()], 'memory', SUCCESS, [entry])['status'] == 'FAIL'


def test_plain_extraction_information_is_retained_without_being_a_failure():
    entry = {'severity': 'Info', 'category': 'statistics', 'message': '4 devices'}
    result = audit.assess([matched()], 'memory', SUCCESS, [entry])
    assert result['status'] == 'PASS within comparison scope'
    assert result['extraction_diagnostics'] == [entry]
