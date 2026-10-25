# SPDX-FileCopyrightText: 2026 Hasan Melih Akbulut
# SPDX-License-Identifier: Apache-2.0
"""Pure input/source gates; native ownership/rotation controls run separately."""
import hashlib
import inspect
import json
from pathlib import Path
import sys
import zipfile

import pytest

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT/'scripts'))
sys.path.insert(0, str(ROOT/'hw/soc/flow'))
import run_io_tap_contact_probe as run  # noqa: E402
import io_tap_contact_probe as probe  # noqa: E402
from run_io_tap_mask_probe import ORDER  # noqa: E402


def sha(raw):
    return hashlib.sha256(raw).hexdigest()


@pytest.mark.parametrize('intervals,expected', [([(0, 160), (100, 260), (400, 560)], 420),
    ([(0, 300), (300, 500)], 500), ([(100, 200), (-100, 300), (400, 500)], 500),
    ([(0, 1)], 1)])
def test_projection_is_union_not_sum(intervals, expected):
    assert probe.projection_length(intervals) == expected


@pytest.mark.parametrize('intervals', [[], [(1, 1)], [(3, 2)], [(0.0, 10)]])
def test_invalid_projection_fails_closed(intervals):
    with pytest.raises(ValueError):
        probe.projection_length(intervals)


def fixture_archive(tmp_path, monkeypatch, fault=None):
    members = {'inputs/actual-adjacency.gds': b'fixture gds', 'flat/lvs.lvsdb.gz': b'fixture db',
               'inputs/schematic.cir': b'fixture ref'}
    members['inputs/boundary.json'] = json.dumps(dict(
        preservation=dict(status='PASS_ALL_POLYGONS_INSTANCES_AND_NON_BOUNDARY_TEXTS_PRESERVED'),
        wrapper_gds_sha256=sha(members['inputs/actual-adjacency.gds']))).encode()
    producer = dict(source_sha=run.PRODUCER_SHA, run_id='37000437137',
        status='COMPLETED_DIAGNOSTIC_BOUNDARY_COMPARISONS', lvs_accepted=False,
        qualified_deck_acceptance=False, cases=dict(flat=dict(native=dict(returncode=0),
        audit=dict(status='FAIL', extraction_diagnostics=[]))),
        output_sha256={name:sha(raw) for name, raw in members.items()})
    if fault == 'producer_source':
        producer['source_sha'] = '0'*40
    if fault == 'accepted':
        producer['lvs_accepted'] = True
    if fault == 'incomplete_comparison':
        producer['cases']['flat']['native']['returncode'] = 1
    if fault == 'extraction_error':
        producer['cases']['flat']['audit']['extraction_diagnostics'] = ['broken']
    if fault == 'missing_capture':
        producer['output_sha256'].pop('inputs/schematic.cir')
    if fault == 'capture_hash':
        producer['output_sha256']['inputs/schematic.cir'] = '0'*64
    members['result.json'] = json.dumps(producer).encode()
    selected = {name:(run.SELECTED[name][0],sha(raw)) for name,raw in members.items()}
    if fault == 'selected_hash':
        selected['inputs/actual-adjacency.gds'] = ('actual-adjacency.gds', '0'*64)
    if fault == 'unsafe':
        members['../unexpected'] = b'no'
    monkeypatch.setattr(run, 'SELECTED', selected)
    monkeypatch.setattr(run, 'ARCHIVE_MEMBERS', len(members))
    monkeypatch.setattr(run, 'ARCHIVE_EXPANDED', sum(map(len, members.values())))
    target = tmp_path/'capture.zip'
    with zipfile.ZipFile(target, 'w') as z:
        for name, raw in members.items():
            z.writestr(name, raw)
    monkeypatch.setattr(run, 'ASSET', dict(name=target.name, bytes=target.stat().st_size,
                                         sha256=sha(target.read_bytes())))
    return target


def test_captured_comparison_replays_without_acceptance(tmp_path, monkeypatch):
    archive = fixture_archive(tmp_path, monkeypatch)
    result = run.unpack(archive, tmp_path/'inputs')
    assert set(result) == set(run.SELECTED)
    assert (tmp_path/'inputs/actual-adjacency.gds').read_bytes() == b'fixture gds'


@pytest.mark.parametrize('fault', ['producer_source', 'accepted', 'incomplete_comparison',
    'extraction_error', 'missing_capture', 'capture_hash', 'selected_hash', 'unsafe'])
def test_capture_fault_rejected_before_output(tmp_path, monkeypatch, fault):
    archive = fixture_archive(tmp_path, monkeypatch, fault)
    with pytest.raises(ValueError):
        run.unpack(archive, tmp_path/'inputs')
    assert not (tmp_path/'inputs').exists()


def control_receipt():
    return dict(status='PASS_NATIVE_CONTACT_CONTROLS', klayout_version='0.30.7', actual_input_processed=False,
        cases={**{k:dict(expected_pass=v, actual_pass=v) for k,v in run.CONTROL_CASES.items()},
               'overlapping_projection':dict(expected_length_nm=420, actual_length_nm=420)})


def test_control_receipt_complete(tmp_path):
    path = tmp_path/'controls.json'; path.write_text(json.dumps(control_receipt()))
    assert run.check_controls(path)['status'] == 'PASS_NATIVE_CONTACT_CONTROLS'


@pytest.mark.parametrize('fault', ['split', 'wrong_net', 'rotation', 'exception', 'missing_enclosure',
                                  'missing_contact', 'wrong_transform', 'pruned_unrelated_contact', 'pruned_selected_contact', 'projection', 'runtime'])
def test_native_control_failures_stop_real_input(tmp_path, fault):
    row = control_receipt()
    if fault == 'projection':
        row['cases']['overlapping_projection']['actual_length_nm'] = 480
    elif fault == 'runtime':
        row['klayout_version'] = 'other'
    else:
        row['cases'][fault]['actual_pass'] = not row['cases'][fault]['actual_pass']
    path = tmp_path/'controls.json'; path.write_text(json.dumps(row))
    with pytest.raises(ValueError):
        run.check_controls(path)


def fake_deck(tmp_path):
    base = tmp_path/run.BASE; (base/'rule_decks').mkdir(parents=True)
    for name in (*ORDER, 'custom_classes'):
        (base/'rule_decks'/f'{name}.lvs').write_text('# fixture\n')
    (base/'sg13g2.lvs').write_text(''.join('  # %include rule_decks/'+n+'.lvs\n'
                                         for n in (*ORDER, 'devices_connections')))
    return base


def test_exact_order_original_includes_and_no_connectivity_mutation(tmp_path):
    base = fake_deck(tmp_path); text = run.program(tmp_path)
    positions = [text.index(str(base/'rule_decks'/f'{name}.lvs')) for name in ORDER]
    assert positions == sorted(positions)
    for forbidden in ('extract_devices(', 'compare(', 'connect(', 'connect_global(', 'connect_implicit(', 'schematic('):
        assert forbidden not in text
    assert "require 'logger'" in text and 'logger = Logger.new($stdout)' in text
    assert 'layer.data.each_merged' in text
    assert "source($input, 'ACTUAL_IO_ADJACENCY')" in text
    assert "whole = ['ptap1_tie', 'ptap1_sub', 'pwell'].include?(name)" in text


def test_reordered_derivation_rejected(tmp_path):
    base = fake_deck(tmp_path)
    path = base/'sg13g2.lvs'; text = path.read_text()
    text = text.replace('mos_derivations.lvs', 'TEMP.lvs', 1).replace('bjt_derivations.lvs', 'mos_derivations.lvs', 1).replace('TEMP.lvs', 'bjt_derivations.lvs', 1)
    path.write_text(text)
    with pytest.raises(ValueError):
        run.program(tmp_path)


def test_native_and_input_gates_precede_bound_interpretation():
    source = inspect.getsource(probe.inspect)
    assert source.index('mask does not reproduce captured native A/P') < source.index('interpreted_bound=dict(')
    assert source.index('membership = owned_contact(') < source.index('interpreted_bound=dict(')
    assert source.index('enclosure_gate(') < source.index('interpreted_bound=dict(')
    worker = inspect.getsource(run.run)
    assert worker.index('check_controls(') < worker.index('unpack(')
    assert worker.index('check_controls(') < worker.index('program(')
    assert 'interpreted_bound=None' in source
    assert '4.85 um equivalent square' in source


def test_workflow_is_scoped_and_keeps_failures():
    text = (ROOT/'.github/workflows/io-tap-contact-probe.yml').read_text()
    assert '      - .github/workflows/io-tap-contact-probe.yml' in text
    assert 'if: always()' in text
    assert 'cancel-in-progress: false' in text
    assert 'prepare_ihp_drc.py' in text and 'prepare_ihp_lvs.py' in text
