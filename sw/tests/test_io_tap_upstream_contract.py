# SPDX-FileCopyrightText: 2026 Hasan Melih Akbulut
# SPDX-License-Identifier: Apache-2.0
"""Fail-closed upstream fixture identity, strict options and native verdict gates."""
from copy import deepcopy
import hashlib
import json
from pathlib import Path
import sys

import pytest

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT/'scripts'))
import probe_io_tap_upstream_contract as run  # noqa: E402


def reference():
    return ('.SUBCKT test_ntap_ptap_ext_deep VDD VSS vin vout\n'
            'RT1 VSS B_SUB ptap1 A=21.276p P=141.84u\n'
            'RT2 VDD B_WELL ntap1 A=24.06p P=160.4u\n.ENDS\n')


def review(case='original'):
    counts = dict(sg13_lv_nmos=2, sg13_lv_pmos=2, ptap1=1, ntap1=1)
    taps = [dict(kind=k, parameters={p:r[p] for p in ('A', 'P')},
                 terminals=dict(TIE=r['TIE'], WELL='body_'+k))
            for k, r in run.lock()['expected_taps'].items()]
    ports = ['VDD', 'VSS', 'VIN', 'VOUT']
    expected_deck_pass = case in ('original', 'wrong_top_port')
    reasons = [] if expected_deck_pass else ['Nonmatching']
    strict_reasons = reasons + (['Exact four-port top census mismatch'] if case == 'wrong_top_port' else [])
    return dict(klayout_version='0.30.7',
        strict_status='PASS' if case == 'original' else 'FAIL', strict_reasons=strict_reasons,
        exact_top_ports_match=case != 'wrong_top_port',
        audit=dict(status='PASS within comparison scope' if expected_deck_pass else 'FAIL',
                   reasons=reasons,
                   extraction_diagnostics=[], circuits=[dict(layout=run.TOP)]),
        layout=dict(counts=dict(sg13_lv_nmos=2, sg13_lv_pmos=2) if case == 'promoted_markers' else counts,
                    taps=[] if case == 'promoted_markers' else taps, ports={run.TOP: ports}),
        reference=dict(counts=counts, ports={run.TOP.upper(): ['VDD', 'VSS', 'VOUT'] if case == 'wrong_top_port' else ports}))


def test_pinned_inventory():
    value = run.lock()
    assert len(value['files']) == 4
    assert value['expected_taps']['ptap1']['P'] == 141.84
    assert value['expected_taps']['ntap1']['P'] == 160.4
    for name, digest in value['method_sha256'].items():
        assert run.native.sha(ROOT/name) == digest


@pytest.mark.parametrize('mutation', ['commit', 'top', 'files', 'url', 'bytes', 'path', 'markers'])
def test_rejects_changed_lock(tmp_path, monkeypatch, mutation):
    value = run.lock()
    if mutation == 'files':
        value['files'].pop()
    elif mutation in ('commit', 'top'):
        value[mutation] = 'wrong'
    elif mutation == 'markers':
        value['markers']['shapes'] = 6
    else:
        value['files'][0][mutation] = {'url':'https://example.org/input', 'bytes':200001, 'path':'../bad'}[mutation]
    path = tmp_path/'lock.json'; path.write_text(json.dumps(value)); monkeypatch.setattr(run, 'LOCK', path)
    with pytest.raises(ValueError):
        run.lock()


def test_blob_identity_binds_both_hashes():
    raw = b'fixture'
    row = dict(bytes=len(raw), sha256=hashlib.sha256(raw).hexdigest(),
               git_blob=hashlib.sha1(b'blob 7\0'+raw).hexdigest())
    run.verify_raw(raw, row)
    for key in ('bytes', 'sha256', 'git_blob'):
        wrong = dict(row); wrong[key] = 0 if key == 'bytes' else '0'*len(wrong[key])
        with pytest.raises(ValueError):
            run.verify_raw(raw, wrong)
    with pytest.raises(ValueError):
        run.verify_raw(raw+b'\0', row)


@pytest.mark.parametrize('case', run.CASES)
def test_reference_changes_only_one_declared_line(case):
    before = reference(); after = run.reference_variant(before, case)
    if case in ('original', 'promoted_markers'):
        assert after == before
    else:
        assert sum(a != b for a, b in zip(before.splitlines(), after.splitlines(), strict=True)) == 1
        with pytest.raises(ValueError):
            run.reference_variant(before+before, case)
    assert 'RT2 VDD B_WELL ntap1 A=24.06p P=160.4u' in after


def test_unknown_variant_rejected():
    with pytest.raises(ValueError):
        run.reference_variant(reference(), 'ignore_ports')


def test_native_command_has_no_ignore_or_extraction_waiver(tmp_path):
    args = run.command(tmp_path/'deck', tmp_path/'input', tmp_path/'cdl', tmp_path/'out')
    options = dict(a.split('=', 1) for a in args if '=' in a)
    assert options['disable_tap_extraction'] == 'false'
    assert options['ignore_top_ports_mismatch'] == 'false'
    assert options['run_mode'] == 'deep'
    assert options['topcell'] == run.TOP
    assert options['thr'] == '1'
    assert set(options) == {'input','schematic','topcell','report','log','target_netlist',
                            'run_mode','thr','disable_tap_extraction','ignore_top_ports_mismatch'}


@pytest.mark.parametrize('case', run.CASES)
def test_each_native_case_expected_verdict(case):
    run.check_case(case, review(case))


@pytest.mark.parametrize('mutation', ['version', 'reference_count', 'no_circuit', 'diagnostic',
    'bad_verdict', 'reason', 'missing_tap', 'duplicate_tap', 'perimeter', 'area',
    'terminal_swapped', 'body_short', 'parameter_absent', 'terminal_absent', 'lost_mos'])
def test_incomplete_or_weakened_positive_rejected(mutation):
    value = review(); tap = value['layout']['taps'][0]
    if mutation == 'version': value['klayout_version'] = '0.30.6'
    elif mutation == 'reference_count': value['reference']['counts'] = {}
    elif mutation == 'no_circuit': value['audit']['circuits'] = []
    elif mutation == 'diagnostic': value['audit']['extraction_diagnostics'] = [dict(severity='Warning')]
    elif mutation == 'bad_verdict': value['audit']['status'] = 'FAIL'
    elif mutation == 'reason': value['audit']['reasons'] = ['Mismatch']
    elif mutation == 'missing_tap': value['layout']['taps'].pop()
    elif mutation == 'duplicate_tap': value['layout']['taps'] = [tap, deepcopy(tap)]
    elif mutation == 'perimeter': tap['parameters']['P'] += 1
    elif mutation == 'area': tap['parameters']['A'] += 1
    elif mutation == 'terminal_swapped': tap['terminals'] = dict(TIE='body', WELL='VSS')
    elif mutation == 'body_short': tap['terminals']['WELL'] = tap['terminals']['TIE']
    elif mutation == 'parameter_absent': del tap['parameters']['P']
    elif mutation == 'terminal_absent': del tap['terminals']['WELL']
    elif mutation == 'lost_mos': value['layout']['counts'] = {}
    with pytest.raises(ValueError): run.check_case('original', value)


@pytest.mark.parametrize('case', run.CASES[1:])
def test_negative_cannot_become_pass(case):
    value = review(case); value['audit']['status'] = 'PASS within comparison scope'; value['audit']['reasons'] = []
    value['strict_status'] = 'PASS'; value['strict_reasons'] = []
    with pytest.raises(ValueError): run.check_case(case, value)


def test_hierarchy_failure_must_retain_four_mos_and_show_two_lost_taps():
    value = review('promoted_markers'); value['layout']['taps'] = review()['layout']['taps']
    with pytest.raises(ValueError): run.check_case('promoted_markers', value)
    value = review('promoted_markers'); value['layout']['counts'] = {}
    with pytest.raises(ValueError): run.check_case('promoted_markers', value)


@pytest.mark.parametrize('pins', [[], ['VDD','VSS','VOUT'], ['VDD','VSS','VOUT','WRONG'],
    ['VDD','VSS','VIN','VOUT','EXTRA'], ['VDD','VSS','VIN','VIN']])
def test_exact_port_census_catches_deck_simplification_false_positive(pins):
    good = review()
    good['reference']['ports'][run.TOP.upper()] = pins
    assert not run.exact_top_ports(good['layout'], good['reference'])
    with pytest.raises(ValueError): run.check_case('original', good)


def test_observed_wrong_port_false_positive_is_preserved_but_rejected():
    value = review('wrong_top_port')
    assert value['audit']['status'] == 'PASS within comparison scope'
    assert value['strict_status'] == 'FAIL'
    run.check_case('wrong_top_port', value)
