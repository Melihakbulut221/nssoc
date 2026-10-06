# SPDX-FileCopyrightText: 2026 Hasan Melih Akbulut
# SPDX-License-Identifier: Apache-2.0
"""Reject waived prerequisites and mismatched experiments before any EDA work."""
import ast
import copy
import importlib.util
import json
import os
from pathlib import Path
import signal
import sys

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / 'scripts'))
import run_npu_eco_physical as flow  # noqa: E402


def fixture(tmp_path, monkeypatch):
    original, factored = tmp_path / 'original.v', tmp_path / 'factored.v'
    original.write_text('synthetic original input\n')
    factored.write_text('synthetic factored input\n')
    pins = {'original': flow.pin(original), 'factored': flow.pin(factored)}
    monkeypatch.setattr(flow, 'NETLISTS', pins)
    return {'status': 'READY_FOR_REVIEWED_PHYSICAL_EXPERIMENT_ONLY',
            'mapped_bridge': {'matched_original': pins['original'], 'physical_input': pins['factored'],
                              'matched_original_path': str(original), 'physical_input_path': str(factored)},
            'strict_boot': {'firmware_checks': 28, 'vendor_eco_netlist': flow.readiness.FACTORED},
            'binary_relation': {'counts': {'total': 34321}}}


@pytest.mark.parametrize('variant', flow.VARIANTS)
def test_exact_input_selected(tmp_path, monkeypatch, variant):
    gate = fixture(tmp_path, monkeypatch)
    assert flow.pin(flow.require_gate(gate, variant)) == flow.NETLISTS[variant]


@pytest.mark.parametrize('fault', ['blocked', 'boot_pending', 'wrong_source', 'missing_equation',
                                  'wrong_map', 'file_changed', 'old_candidate'])
def test_unready_candidate_rejected(tmp_path, monkeypatch, fault):
    gate = fixture(tmp_path, monkeypatch)
    variant = 'factored'
    if fault == 'blocked':
        gate['status'] = 'BLOCKED'
    elif fault == 'boot_pending':
        gate['strict_boot']['firmware_checks'] = 24
    elif fault == 'wrong_source':
        gate['strict_boot']['vendor_eco_netlist'] = flow.readiness.PAIR['candidate']
    elif fault == 'missing_equation':
        gate['binary_relation']['counts']['total'] = 34320
    elif fault == 'wrong_map':
        gate['mapped_bridge']['physical_input'] = gate['mapped_bridge']['matched_original']
    elif fault == 'file_changed':
        Path(gate['mapped_bridge']['physical_input_path']).write_text('mutated\n')
    else:
        variant = 'candidate'
    with pytest.raises(ValueError):
        flow.require_gate(gate, variant)


def test_blocked_full_entry_preserves_failure_and_does_not_create_physical_work(tmp_path, monkeypatch):
    # Run the real entry point and source capture, but prohibit every native stage.
    monkeypatch.setattr(flow.readiness, 'check', lambda **k: {'status': 'BLOCKED', 'blocker': 'pending actual boot'})
    def unexpected(*args, **kwargs):
        pytest.fail('Native preparation reached before strict boot')
    monkeypatch.setattr(flow, 'execute', unexpected)
    monkeypatch.setattr(flow, 'resources', unexpected)
    monkeypatch.setattr(flow, 'verify_bundle', unexpected)
    output, work = tmp_path / 'output', tmp_path / 'work'
    with pytest.raises(ValueError, match='pending actual boot'):
        flow.run('factored', output, work, tmp_path / 'bundle', tmp_path / 'runtime',
                 boot_archive=None, boot_run=None, boot_artifact=None)
    row = json.loads((output / 'result.json').read_text())
    assert row['status'] == 'FAILED_PRESERVED' and not work.exists()
    assert row['preserved_old_boot_failure']['unresolved'] is True
    assert row['timing_accepted'] is row['candidate_adopted'] is row['manufacturing_approval'] is False
    assert 'native_identity' not in row and 'execution' not in row


@pytest.mark.parametrize('memory,disk,ok', [(9, 3, True), (8, 3, False), (9, 2, False)])
def test_reserves_checked_before_native(tmp_path, monkeypatch, memory, disk, ok):
    sample = {'available_memory_bytes': memory * flow.common.GIB, 'free_disk_bytes': disk * flow.common.GIB}
    monkeypatch.setattr(flow.common, 'resource_sample', lambda directory: sample)
    if ok:
        assert flow.resources(tmp_path) == sample
    else:
        with pytest.raises(ValueError, match='reserve'):
            flow.resources(tmp_path)


@pytest.mark.parametrize('exitcode', [0, 7])
def test_actual_owned_control_child_preserves_returncode_and_signal_handlers(tmp_path, monkeypatch, exitcode):
    # Small Python child only; this does not claim an OpenROAD experiment.
    monkeypatch.setattr(flow, 'resources', lambda directory: {'control_fixture': True})
    prior = {s: signal.getsignal(s) for s in (signal.SIGINT, signal.SIGTERM)}
    record = {}
    result = flow.execute([sys.executable, '-c', f'print("owned control"); raise SystemExit({exitcode})'], tmp_path, record)
    assert result['returncode'] == exitcode
    assert (tmp_path / 'fresh-physical.log').read_text() == 'owned control\n'
    assert flow.owned.identity(record['native_identity']['pid']) is None
    assert {s: signal.getsignal(s) for s in prior} == prior


def test_interruption_between_spawn_and_assignment_cleans_exact_child(tmp_path, monkeypatch):
    monkeypatch.setattr(flow, 'resources', lambda directory: {'control_fixture': True})
    original = flow.owned.owned_popen
    children = []

    def pending_term(*args, **kwargs):
        child = original(*args, **kwargs)
        children.append(child)
        os.kill(os.getpid(), signal.SIGTERM)
        return child

    monkeypatch.setattr(flow.owned, 'owned_popen', pending_term)
    prior = {s: signal.getsignal(s) for s in (signal.SIGINT, signal.SIGTERM)}
    with pytest.raises(InterruptedError, match='signal'):
        flow.execute([sys.executable, '-c', 'import time; time.sleep(60)'], tmp_path, {})
    assert len(children) == 1 and children[0].returncode is not None
    assert flow.owned.identity(children[0].pid) is None
    assert {s: signal.getsignal(s) for s in prior} == prior


def test_original_guards_still_closed_and_constraints_unchanged():
    assert flow.physical.PROOF_BINDING is None and flow.physical.BOOT_FAILURE['unresolved'] is True
    for name, sha in {**flow.physical.PINS, **flow.ADDITIONAL_PINS}.items():
        assert flow.common.sha(flow.ROOT / name) == sha
    with pytest.raises(ValueError, match='independently accepted'):
        flow.physical.require_execution_ready()


def test_native_limits_only_address_space_core_and_failure_cleanup():
    tree = ast.parse(Path(flow.__file__).read_text())
    execute = next(n for n in tree.body if isinstance(n, ast.FunctionDef) and n.name == 'execute')
    calls = [n for n in ast.walk(execute) if isinstance(n, ast.Call)]
    assert not any(any(k.arg == 'timeout' for k in n.keywords) for n in calls)
    assert not any(isinstance(n.func, ast.Attribute) and n.func.attr in {'kill', 'terminate', 'killpg'} for n in calls)
    cleanups = [n for n in calls if isinstance(n.func, ast.Attribute) and n.func.attr == 'stop_failed_group']
    assert len(cleanups) == 1
    assert any(cleanups[0] in list(ast.walk(h)) for n in ast.walk(execute)
               if isinstance(n, ast.Try) for h in n.handlers)


def test_captured_process_helper_is_exact_reviewed_implementation():
    source = flow.ROOT / 'hw/soc/pcie-evidence/20261006-compact-rc-and-repair/records/pcie-gen3-transmit-v4-repair-20261005/owned_lifecycle05.py'
    assert source.read_bytes() == Path(flow.owned.__file__).read_bytes()


def test_unchanged_fresh_configuration_rejects_unrelated_change():
    cfg = {'CLOCK_PERIOD': 20, 'CLOCK_PORT': ['clk_i', 'eth_rx_clk_i', 'eth_tx_clk_i'],
           'PNR_SDC_FILE': '/same.sdc', 'SIGNOFF_SDC_FILE': '/same.sdc', 'VERILOG_FILES': ['/old.v'],
           'MACROS': {m: {'instances': {m + str(i): {} for i in range(16)}}
                      for m in ('SP6TSRAM512x64', 'DP8TSRAMDP256x16')}, 'PL_TARGET_DENSITY_PCT': 40}
    source = copy.deepcopy(cfg)
    macros = {n: m for m, row in cfg['MACROS'].items() for n in row['instances']}
    changed = flow.physical.fresh_config(cfg, Path('/factored.v'), Path('/same.def'), macros)
    assert cfg == source
    assert all(changed[k] == v for k, v in cfg.items() if k != 'VERILOG_FILES')
    cfg['CLOCK_PERIOD'] = 25
    with pytest.raises(ValueError, match='clock'):
        flow.physical.fresh_config(cfg, Path('/factored.v'), Path('/same.def'), macros)


@pytest.mark.parametrize('fault', [None, 'template_pin_box', 'template_orientation', 'missing_template'])
def test_saved_template_is_independent_of_final_geometry(tmp_path, monkeypatch, fault):
    spec = importlib.util.spec_from_file_location('old_physical_fixture',
                                                flow.ROOT / 'sw/tests/test_cloud_alu_physical.py')
    fixtures = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(fixtures)
    cfg = fixtures.config()
    native = tmp_path / 'native-template'
    native.mkdir()
    fixtures.geometry(native, cfg)
    final = tmp_path / 'capture'
    final.mkdir()
    fixtures.geometry(final, cfg)
    expected = flow.capture_template(native, tmp_path)
    original = flow.physical.geometry_check
    monkeypatch.setattr(flow.physical, 'geometry_check',
                        lambda directory, config: original(directory, config, fixtures.witness(config)))
    if fault == 'template_pin_box':
        path = tmp_path / 'capture-template/signal-pins.tsv'
        path.write_text(path.read_text().replace('\t0\t0\t50\t50\t', '\t1\t0\t51\t50\t', 1))
    elif fault == 'template_orientation':
        path = tmp_path / 'capture-template/macros.tsv'
        path.write_text(path.read_text().replace('\tR0\t', '\tMX\t', 1))
    elif fault == 'missing_template':
        (tmp_path / 'capture-template/signal-pins.tsv').unlink()
    if fault:
        with pytest.raises((ValueError, FileNotFoundError)):
            flow.verify_saved_geometry(tmp_path, cfg, expected)
    else:
        assert flow.verify_saved_geometry(tmp_path, cfg, expected) == expected
