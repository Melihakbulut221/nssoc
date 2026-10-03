# SPDX-FileCopyrightText: 2026 Hasan Melih Akbulut
# SPDX-License-Identifier: Apache-2.0
"""Negative controls for full hold endpoint comparison, not sampled reports."""
import copy
import importlib.util
import json
from pathlib import Path

import pytest

SPEC = importlib.util.spec_from_file_location(
    'hold_compare', Path(__file__).resolve().parents[2]/'scripts/compare_full_hold_endpoints.py')
M = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(M)
CORNERS = ['fast', 'slow']


def fixture(root, name='before', values=None):
    values = values or {'a': (-2e-9, -1e-9, -2e-9), 'b': (1e-9, 2e-9, 1e-9), 'u': (None, None, None)}
    directory = root/name
    directory.mkdir()
    def text(value):
        return 'UNCONSTRAINED' if value is None else format(value, '.17g')
    (directory/'constraints.sdc').write_text('create_clock -period 20 clk\n')
    (directory/'endpoints.tsv').write_text('endpoint\tglobal_vertex_slack_seconds\n'+''.join(
        f'{endpoint}\t{text(slacks[2])}\n' for endpoint, slacks in values.items()))
    (directory/'hold-endpoints.tsv').write_text('corner\tendpoint\tmin_rise_seconds\tmin_fall_seconds\tmin_seconds\n'+''.join(
        '\t'.join([corner, endpoint]+[text(x) for x in slacks])+'\n'
        for corner in CORNERS for endpoint, slacks in values.items()))
    finite = [v[2] for v in values.values() if v[2] is not None]
    negatives = [v for v in finite if v < 0]
    native = dict(name=name, endpoint_count=len(values), engine_endpoint_count=len(values),
                  exported_endpoint_count=len(values), negative_vertex_endpoints=len(negatives),
                  engine_negative_vertex_endpoints=len(negatives), all_endpoint_coverage=True,
                  vertex_path_semantics_match=True, time_unit_seconds=1e-9,
                  native_time_unit_seconds=M.NATIVE_NS, time_unit_representation=M.REPRESENTATION,
                  value_units='seconds', numeric_format='%.17g',
                  native_global_tns_seconds_before=sum(negatives), native_global_tns_seconds_after=sum(negatives),
                  corners=[dict(name=c, constrained_endpoints=len(finite), unrepresented_endpoints=len(values)-len(finite),
                                negative_path_endpoints=len(negatives), fixed_order_tns_seconds=sum(negatives),
                                native_wns_seconds=min(finite), native_tns_seconds_before=sum(negatives),
                                native_tns_seconds_after=sum(negatives)) for c in CORNERS])
    (directory/'native.json').write_text(json.dumps(native))
    stage = copy.deepcopy(native)
    stage['files'] = {p.name: M.file_pin(p) for p in directory.iterdir()}
    stage['fingerprints'] = {'constraints': stage['files']['constraints.sdc']['sha256']}
    return stage


def refresh(root, stage, filename):
    stage['files'][filename] = M.file_pin(root/stage['name']/filename)


def native_refresh(root, stage):
    (root/stage['name']/'native.json').write_text(json.dumps({k:v for k,v in stage.items() if k not in ('files', 'fingerprints')}))
    refresh(root, stage, 'native.json')


def load(root, stage):
    return M.load_stage(root, stage, CORNERS, stage['files']['constraints.sdc']['sha256'])


def test_complete_unchanged(tmp_path):
    before, after = fixture(tmp_path), fixture(tmp_path, 'after')
    result = M.compare(load(tmp_path, before), load(tmp_path, after))
    assert result['changed_endpoint_corner_count'] == 0
    assert result['endpoint_count'] == 3 and result['endpoint_corner_count'] == 6
    assert result['corners']['fast']['before']['unconstrained'] == 1
    assert result['candidate_adopted'] is result['thresholds_changed'] is False


def test_cancelling_tns_still_exposes_regression(tmp_path):
    original = {'a': (-3e-9, -3e-9, -3e-9), 'b': (-1e-9, -1e-9, -1e-9)}
    changed = {'a': (-2e-9, -2e-9, -2e-9), 'b': (-2e-9, -2e-9, -2e-9)}
    result = M.compare(load(tmp_path, fixture(tmp_path, values=original)),
                       load(tmp_path, fixture(tmp_path, 'after', changed)))
    assert result['corners']['fast']['fsum_delta_seconds'] == 0
    assert result['corners']['fast']['columns']['min']['regressed'] == 1
    assert result['corners']['fast']['columns']['min']['improved'] == 1
    assert len(result['all_changed_endpoint_corners']) == 4


def test_unconstrained_transition_is_not_improvement(tmp_path):
    before = fixture(tmp_path)
    after = fixture(tmp_path, 'after', {'a': (None,None,None), 'b': (1e-9,2e-9,1e-9), 'u': (-1e-9,-1e-9,-1e-9)})
    result = M.compare(load(tmp_path,before), load(tmp_path,after))
    counts = result['corners']['fast']['columns']['min']
    assert counts['finite_to_unconstrained'] == counts['unconstrained_to_finite'] == 1
    assert counts['improved'] == counts['regressed'] == 0


@pytest.mark.parametrize('fault', ['missing_row', 'duplicate_row', 'missing_corner', 'bad_min', 'nonfinite',
                                  'finite_omitted', 'unpublished_bytes', 'wrong_headers'])
def test_bad_tables_rejected(tmp_path, fault):
    stage = fixture(tmp_path)
    path = tmp_path/'before/hold-endpoints.tsv'
    lines = path.read_text().splitlines()
    if fault == 'missing_row':
        lines.pop()
    elif fault == 'duplicate_row':
        lines.append(lines[1])
    elif fault == 'missing_corner':
        lines = [line for line in lines if not line.startswith('slow\t')]
    elif fault == 'bad_min':
        parts=lines[1].split('\t'); parts[-1]='0'; lines[1]='\t'.join(parts)
    elif fault == 'nonfinite':
        lines[1]=lines[1].replace('-2.0000000000000001e-09', 'nan')
    elif fault == 'finite_omitted':
        lines=[line if '\ta\t' not in line else '\t'.join(line.split('\t')[:2]+['UNCONSTRAINED']*3) for line in lines]
    elif fault == 'unpublished_bytes':
        lines.append('')
    elif fault == 'wrong_headers':
        lines[0]=lines[0].replace('min_rise_seconds', 'min_rise_ns')
    path.write_text('\n'.join(lines)+'\n')
    if fault != 'unpublished_bytes':
        refresh(tmp_path, stage, path.name)
    with pytest.raises(ValueError):
        load(tmp_path, stage)


@pytest.mark.parametrize('fault', ['units', 'native_units', 'representation', 'count', 'negative_count',
                                  'corner_count', 'sum', 'native_record', 'constraints'])
def test_bad_receipts_rejected(tmp_path, fault):
    stage = fixture(tmp_path)
    if fault == 'units': stage['time_unit_seconds'] = 1
    elif fault == 'native_units': stage['native_time_unit_seconds'] = 1e-9
    elif fault == 'representation': stage['time_unit_representation'] = 'unknown'
    elif fault == 'count': stage['engine_endpoint_count'] += 1
    elif fault == 'negative_count': stage['engine_negative_vertex_endpoints'] = 0
    elif fault == 'corner_count': stage['corners'].pop()
    elif fault == 'sum': stage['corners'][0]['fixed_order_tns_seconds'] = 0
    elif fault == 'native_record': stage['endpoint_count'] += 1
    elif fault == 'constraints': stage['fingerprints']['constraints'] = '0'*64
    if fault != 'native_record': native_refresh(tmp_path, stage)
    with pytest.raises(ValueError): load(tmp_path, stage)


def test_different_identity_rejected(tmp_path):
    before = load(tmp_path, fixture(tmp_path))
    after = load(tmp_path, fixture(tmp_path, 'after', {'new': (-2e-9,-1e-9,-2e-9)}))
    with pytest.raises(ValueError, match='identities changed'): M.compare(before, after)


def test_native_tns_roundoff_is_reported_without_acceptance(tmp_path):
    stage = fixture(tmp_path)
    for corner in stage['corners']: corner['native_tns_seconds_after'] -= 1e-15
    stage['native_global_tns_seconds_after'] -= 1e-15
    native_refresh(tmp_path, stage)
    after = load(tmp_path, stage)
    result = M.compare(after, after)
    assert result['corners']['fast']['after']['native_tns_after_seconds'] != result['corners']['fast']['after']['fsum_seconds']
    assert result['timing_accepted'] is False


def test_changed_endpoint_cli_persistence_reconstructs_exactly(tmp_path, monkeypatch):
    """Exercise the saved-result boundary that a nonempty native comparison hit."""
    before = fixture(tmp_path)
    after = fixture(tmp_path, 'after', {
        'a': (-3e-9, -1e-9, -3e-9),  # Real regression, no rounding/tolerance waiver.
        'b': (2e-9, 3e-9, 2e-9),
        'u': (-1e-9, None, -1e-9),  # Preserve JSON null and missing-path meaning.
    })
    receipt = tmp_path/'stages.json'
    receipt.write_text(json.dumps({'stages': [before, after]}))
    config = tmp_path/'config.json'
    config.write_text(json.dumps({'PNR_CORNERS': CORNERS}))
    output = tmp_path/'comparison.json'
    monkeypatch.setattr('sys.argv', [
        'compare_full_hold_endpoints.py', '--before-root', str(tmp_path),
        '--before-receipt', str(receipt), '--before-stage', 'before',
        '--after-root', str(tmp_path), '--after-receipt', str(receipt), '--after-stage', 'after',
        '--config', str(config), '--expected-sdc-sha256', before['files']['constraints.sdc']['sha256'],
        '--output', str(output)])
    M.main()
    saved = json.loads(output.read_text())
    saved_inputs = saved.pop('source_inputs')
    assert saved_inputs == {'before_receipt': M.file_pin(receipt),
                            'after_receipt': M.file_pin(receipt), 'config': M.file_pin(config)}
    # Reopen the producer receipt; do not reuse only in-memory fixture rows.
    native = json.loads(receipt.read_text())['stages']
    reconstructed = M.compare(load(tmp_path, native[0]), load(tmp_path, native[1]))
    assert saved == reconstructed
    assert saved['changed_endpoint_corner_count'] == 6
    assert saved['corners']['fast']['columns']['min']['regressed'] == 1
    assert saved['corners']['fast']['columns']['min']['unconstrained_to_finite'] == 1
    assert saved['all_changed_endpoint_corners'][-1]['before_seconds'] == [None, None, None]
    assert saved['thresholds_changed'] is saved['candidate_adopted'] is False


def test_persisted_identity_change_still_rejected(tmp_path):
    before = fixture(tmp_path)
    after = fixture(tmp_path, 'after', {
        'different_a': (-2e-9, -1e-9, -2e-9), 'b': (1e-9, 2e-9, 1e-9), 'u': (None, None, None)})
    receipt = tmp_path/'identity-change.json'
    receipt.write_text(json.dumps([before, after]))
    restored = json.loads(receipt.read_text())
    # Counts, corner coverage, pins and values match; identity mismatch must fail.
    with pytest.raises(ValueError, match='identities changed'):
        M.compare(load(tmp_path, restored[0]), load(tmp_path, restored[1]))
