# SPDX-FileCopyrightText: 2026 Hasan Melih Akbulut
# SPDX-License-Identifier: Apache-2.0
"""Finite pair controls; synthetic traces never count as native acquisition."""
from copy import deepcopy
import json
import runpy
import sys
from pathlib import Path
import pytest

ROOT = Path(__file__).resolve().parents[2]
M = runpy.run_path(str(ROOT / 'scripts/compare_pcie_pll_acquisition_pair_v1.py'))


def edges(offset=250e-12, frequency=1e8):
    ref = [14e-9 + i/1e8 for i in range(99)]
    fb = [14e-9 + i/frequency + offset for i in range(99)]
    return dict(reference_edges_s=ref, feedback_edges_s=fb, reference_ordinals=list(range(99)))


def test_nonzero_static_phase_and_small_step_delta_pass():
    result = M['compare'](edges(), edges(offset=260e-12))
    assert result['passed']
    assert all(9e-12 < r['maximum_matched_phase_difference_s'] < 11e-12 for r in result['windows'])


def test_matched_phase_must_pass_even_when_both_spans_are_zero():
    result = M['compare'](edges(), edges(offset=301e-12))
    assert not result['passed']
    assert all(r['checks']['both_individual_windows_pass'] for r in result['windows'])
    assert all(not r['checks']['matched_phase_difference_50ps'] for r in result['windows'])


def test_individual_frequency_pass_does_not_imply_pair_pass():
    result = M['compare'](edges(frequency=1e8*(1+80e-6)), edges(frequency=1e8*(1-80e-6)))
    assert not result['passed']
    assert all(r['checks']['both_individual_windows_pass'] for r in result['windows'])
    assert all(not r['checks']['frequency_difference_100ppm'] for r in result['windows'])


@pytest.mark.parametrize('fault', ['nan','reverse','duplicate','slip','missing_window','wrong_ordinal','ambiguous'])
def test_malformed_actual_edge_census_fails_closed(fault):
    x = edges()
    if fault == 'nan':
        x['feedback_edges_s'][90] = float('nan')
    elif fault == 'reverse':
        x['feedback_edges_s'][89:91] = reversed(x['feedback_edges_s'][89:91])
    elif fault == 'duplicate':
        x['feedback_edges_s'][90] = x['feedback_edges_s'][89]
    elif fault == 'slip':
        del x['feedback_edges_s'][90]
        del x['reference_ordinals'][90]
    elif fault == 'missing_window':
        x['feedback_edges_s'] = x['feedback_edges_s'][:70]
        x['reference_ordinals'] = x['reference_ordinals'][:70]
    elif fault == 'wrong_ordinal':
        x['reference_ordinals'][90] -= 1
    elif fault == 'ambiguous':
        # Binary-exact midpoint gives equal distances, with no tie preference.
        x = dict(reference_edges_s=[0., 2., 4.], feedback_edges_s=[1., 3., 5.], reference_ordinals=[0,1,2])
    with pytest.raises(ValueError):
        M['compare'](edges(), x)


def test_pair_is_symmetric_and_preserves_inputs():
    a, b = edges(), edges(offset=251e-12)
    originals = deepcopy((a,b))
    assert M['compare'](a,b) == M['compare'](b,a)
    assert (a,b) == originals


def test_declared_fixed_windows_and_limits_remain_exact():
    assert M['WINDOWS'] == ((800e-9,900e-9),(900e-9,1e-6))
    assert M['FREQUENCY_LIMIT_PPM'] == 100
    assert M['PHASE_LIMIT_S'] == 50e-12


@pytest.mark.parametrize('fault', [None,'native_fail','replay_incomplete','one_device_failed','missing_device',
                                  'numerical_warning','raw_hash','payload_hash','source_omitted',
                                  'native_pin','source_bytes','output_bytes','row_count'])
def test_receipt_guards_reject_individual_mutations(tmp_path, fault):
    # Tiny explicit receipt fixtures exercise guards only, never native evidence.
    p = tmp_path / 'capture'
    p.mkdir()
    native = p / 'result.json'
    model = tmp_path / 'fixture-model.txt'
    model.write_text('synthetic guard fixture\n')
    output = p / 'fixture-output.txt'
    output.write_text('synthetic output fixture\n')
    reviewer = ROOT / 'scripts/review_pcie_pll_acquisition_v1.py'
    r = dict(status='PASS_NATIVE_STREAM_FINITE_SCREEN',
             safety=dict(passed=True,all_device_bounds=[dict(passed=True) for _ in range(539)]),
             devices=[{} for _ in range(539)], rows=2,values=4,columns=['time','fixture'],
             inputs={str(model):M['pin'](model)},outputs={output.name:M['pin'](output)},
             raw_sha256='raw',canonical_payload_sha256='payload',
             measurement=dict(passed=True),strict_numerical_diagnostics_pass=True)
    q = dict(status='PASS_LOSSLESS_AUTHOR_REPLAY_AND_INDEPENDENT_ACQUISITION_ARITHMETIC',
             native_authoritative_status=r['status'],all539_author_safety_records_exact=True,
             rows=2,values=4,canonical_payload_sha256='payload',full_raw_sha256='raw',
             independent=dict(passed=True),agreement=dict(all_predicates_exact=True),
             inputs={str(model):M['pin'](model),str(reviewer):M['pin'](reviewer)})
    if fault == 'native_fail':
        r['status'] = 'FAIL_NATIVE_STREAM_FINITE_SCREEN'
    elif fault == 'replay_incomplete':
        q['status'] = 'RUNNING'
    elif fault == 'one_device_failed':
        r['safety']['all_device_bounds'][0]['passed'] = False
    elif fault == 'missing_device':
        r['devices'].pop()
    elif fault == 'numerical_warning':
        r['strict_numerical_diagnostics_pass'] = False
    elif fault == 'raw_hash':
        q['full_raw_sha256'] = 'wrong'
    elif fault == 'payload_hash':
        q['canonical_payload_sha256'] = 'wrong'
    elif fault == 'source_omitted':
        del q['inputs'][str(model)]
    elif fault == 'row_count':
        r['rows'] = 3
    native.write_text(json.dumps(r))
    q['native_result'] = M['pin'](native)
    if fault == 'native_pin':
        q['native_result']['sha256'] = 'wrong'
    elif fault == 'source_bytes':
        model.write_text('changed')
    elif fault == 'output_bytes':
        output.write_text('changed')
    review = tmp_path / 'review.json'
    review.write_text(json.dumps(q))
    if fault is None:
        actual, _ = M['load_verified'](p,review)
        assert actual == r
    else:
        with pytest.raises(ValueError):
            M['load_verified'](p,review)


@pytest.mark.parametrize('status', ['PASS_FINITE_NOMINAL_TIMESTEP_SCREEN',
                                   'FAIL_FINITE_NOMINAL_TIMESTEP_SCREEN','RUNNING','ERROR'])
def test_cli_only_accepts_exact_complete_status(tmp_path, monkeypatch, status):
    result = dict(status=status,passed=True)
    monkeypatch.setitem(M['main'].__globals__,'run',lambda *args:result)
    out = tmp_path/'result.json'
    args = [sys.executable]
    for name in ['first','first-review','second','second-review','declaration']:
        args += ['--'+name,str(tmp_path/name)]
    args += ['--out',str(out)]
    monkeypatch.setattr(sys,'argv',args)
    assert M['main']() == (0 if status=='PASS_FINITE_NOMINAL_TIMESTEP_SCREEN' else 1)
    assert json.loads(out.read_text()) == result
