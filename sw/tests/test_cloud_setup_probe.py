# SPDX-FileCopyrightText: 2026 Hasan Melih Akbulut
# SPDX-License-Identifier: Apache-2.0
"""Probe lifecycle/schema negatives, without loading a chip or native runtime."""
from dataclasses import FrozenInstanceError, replace
import json
from pathlib import Path
import shutil
import subprocess
import sys
from types import ModuleType, SimpleNamespace

import pytest

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT/'scripts'))
import run_cloud_setup_probe as probe  # noqa: E402
from test_cloud_hold_diagnostic import complete_capture, repin_stage, stage_fixture, write  # noqa: E402

shared = probe.shared


def fixture(root):
    step = root/'01-openroad-resizertimingpostgrt'
    stages = []
    for name in probe.STAGES:
        stage = stage_fixture(step/name, name)
        stage.update(vertex_path_semantics_match=True,
                     native_global_tns_seconds_before=-7.500000000000001e-10,
                     native_global_tns_seconds_after=-7.500000000000001e-10)
        # Use the exact independently generated corner aggregate representation.
        stage['native_global_tns_seconds_before'] = min(c['native_tns_seconds_before'] for c in stage['corners'])
        stage['native_global_tns_seconds_after'] = min(c['native_tns_seconds_after'] for c in stage['corners'])
        (step/name/'placement.tsv').write_text('instance\tmaster\tx_dbu\ty_dbu\torientation\tstatus\n'
            + ''.join(f'cell{i}\tINV\t{i}\t0\tR0\tPLACED\n' for i in range(50)))
        write(step/name/'native.json', {k: v for k, v in stage.items() if k not in ('files', 'fingerprints')})
        repin_stage(step/name, stage)
        stages.append(stage)
    record = dict(schema=1, status='COMPLETE_DIAGNOSTIC_ONLY', stages=stages,
                  candidate_adopted=False, timing_accepted=False, manufacturing_approval=False, thresholds_changed=False,
                  provisional_stages=['after_repair_native'],
                  sram_macro_count=32, sram_placement_preserved=True,
                  repair_invocation=dict(command=probe.REPAIR_COMMAND, call_count=1, max_passes=2,
                      max_repairs_per_pass=4, max_iterations=1, allow_setup_violations=False,
                      effective_global_pass_budget=1, journal_boundary_workaround='max_passes_gt_max_iterations',
                      skip_last_gasp=True, skip_crit_vt_swap=True, native_setup_buffer_percentage_enforced=False,
                      initial_instance_count=50, actual_instance_count=50,
                      global_instance_growth_budget=20, actual_instance_growth=0,
                      started_ms=1000, finished_ms=1200, elapsed_ms=200,
                      granularity='One native pass, not four guaranteed total mutations.'))
    record['timing_metrics'] = {name: dict(recorded_ms=1250, setup_wns_seconds=-1e-9,
        hold_wns_seconds=-5e-10, setup_tns_seconds=-2e-9, hold_tns_seconds=-7.5e-10,
        setup_violating_endpoints=2, hold_violating_endpoints=2, slew_violations=0,
        capacitance_violations=0, instance_count=50) for name in probe.STAGES}
    record['buffer_budget'] = dict(initial_instance_count=50, global_buffer_budget=20,
        after_repair_instance_count=50, final_instance_count=50, maximum_observed_growth=0, within_budget=True)
    write(step/'setup-probe.json', record)
    write(step/'repair-invocation.json', record['repair_invocation'])
    command_marker = 'NSSOC_SETUP_HOLD_PROBE_REPAIR_COMMAND ' + ' '.join(probe.REPAIR_COMMAND)
    (step/'openroad-resizertimingpostgrt.log').write_text('\n'.join((probe.BEGIN_MARKER, command_marker, probe.END_MARKER, probe.COMPLETE_MARKER))+'\n')
    return step, record


def test_default_spec_keeps_the_original_method_inventory_and_validator():
    default = shared.diagnostic_spec()
    assert default.sources == shared.SOURCES
    assert default.entrypoint == 'scripts/run_cloud_hold_diagnostic.py'
    assert default.step == 'hw/soc/pnr/timing_hold_diagnostic_step.tcl'
    assert default.validator is shared.validate_diagnostic
    with pytest.raises(FrozenInstanceError):
        default.name = 'different'
    with pytest.raises(ValueError):
        replace(default, sources=list(default.sources))
    with pytest.raises(ValueError):
        replace(default, sources=default.sources[1:])


def test_probe_methods_are_additive_and_byte_pinned(tmp_path):
    root = tmp_path/'source'
    spec = probe.specification()
    for name in spec.sources:
        path = root/name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text('source '+name)
    staged = tmp_path/'methods'
    pins = shared.stage_methods(root, staged, spec.sources)
    shared.validate_methods(staged, pins, spec.sources)
    with pytest.raises(ValueError):
        shared.validate_methods(staged, pins)
    changed = staged/spec.step
    changed.chmod(0o644)
    changed.write_text('changed probe method')
    with pytest.raises(ValueError):
        shared.validate_methods(staged, pins, spec.sources)


def test_complete_probe_reconstructs_all_endpoint_pairs_without_acceptance(tmp_path):
    step, row = fixture(tmp_path)
    checked = probe.validate_diagnostic(step, row['stages'][0]['files']['constraints.sdc']['sha256'], ['fast', 'slow'])
    assert set(checked['full_endpoint_comparisons']) == {'native_repair_effect', 'legalization_and_rc_effect', 'setup_effect', 'cache_update_effect', 'setup_effect_after_cache_update'}
    for comparison in checked['full_endpoint_comparisons'].values():
        assert comparison['endpoint_count'] == 3 and comparison['endpoint_corner_count'] == 6
        assert comparison['changed_endpoint_corner_count'] == 0
    assert all(checked[k] is False for k in ('candidate_adopted', 'timing_accepted', 'manufacturing_approval', 'thresholds_changed'))


def test_native_tcl_uses_the_safe_journal_boundary_without_more_global_work():
    source = (ROOT/'hw/soc/pnr/timing_setup_hold_probe_step.tcl').read_text()
    # Execute the production Tcl command construction, without loading tools or
    # a design. This catches divergence between native argv and Python receipts.
    command = source[source.index('set repair_command [list '):source.index('set initial_instances ')]
    result = subprocess.run(['tclsh'], input=command+'\nforeach word $repair_command {puts $word}\n',
                            text=True, capture_output=True, check=True, timeout=5)
    argv = result.stdout.splitlines()
    assert argv == probe.REPAIR_COMMAND
    assert argv[argv.index('-max_iterations')+1] == '1'
    assert argv[argv.index('-max_passes')+1] == '2'
    assert argv[argv.index('-max_repairs_per_pass')+1] == '4'
    assert '-skip_last_gasp' in argv and '-skip_crit_vt_swap' in argv


@pytest.mark.parametrize('fault', ['old-unsafe-boundary', 'extra-global-pass', 'forged-effective-budget', 'missing-workaround'])
def test_repair_contract_rejects_unsafe_boundary_and_larger_effective_budget(tmp_path, fault):
    step, row = fixture(tmp_path)
    invocation = row['repair_invocation']
    invocation['command'] = list(invocation['command'])
    if fault == 'old-unsafe-boundary':
        invocation['max_passes'] = 1
        invocation['command'][invocation['command'].index('-max_passes')+1] = '1'
    if fault == 'extra-global-pass':
        invocation['max_iterations'] = 2
        invocation['command'][invocation['command'].index('-max_iterations')+1] = '2'
    if fault == 'forged-effective-budget':
        invocation['effective_global_pass_budget'] = 2
    if fault == 'missing-workaround':
        del invocation['journal_boundary_workaround']
    # Even internally consistent argv/log/receipt pairs must fail these bounds.
    log = '\n'.join((probe.BEGIN_MARKER,
        'NSSOC_SETUP_HOLD_PROBE_REPAIR_COMMAND '+' '.join(invocation['command']),
        probe.END_MARKER, probe.COMPLETE_MARKER))+'\n'
    with pytest.raises(ValueError):
        probe.validate_repair(row, log)


@pytest.mark.parametrize('fault', ['extra-call', 'passes', 'repairs', 'iterations', 'argv', 'permission', 'interval',
                                   'begin-missing', 'end-duplicate', 'marker-order', 'completion', 'stage', 'acceptance', 'sram'])
def test_probe_rejects_unbounded_or_incomplete_claims(tmp_path, fault):
    step, row = fixture(tmp_path)
    invocation = row['repair_invocation']
    if fault == 'extra-call': invocation['call_count'] = 2
    if fault == 'passes': invocation['max_passes'] = 3
    if fault == 'repairs': invocation['max_repairs_per_pass'] = 8
    if fault == 'iterations': invocation['max_iterations'] = 200
    if fault == 'argv': invocation['command'] = invocation['command'] + ['-allow_setup_violations']
    if fault == 'permission': invocation['allow_setup_violations'] = True
    if fault == 'interval': invocation['elapsed_ms'] = 201
    log = step/'openroad-resizertimingpostgrt.log'
    if fault == 'begin-missing': log.write_text(log.read_text().replace(probe.BEGIN_MARKER, ''))
    if fault == 'end-duplicate': log.write_text(log.read_text()+probe.END_MARKER+'\n')
    if fault == 'marker-order': log.write_text('\n'.join((probe.END_MARKER, probe.BEGIN_MARKER, probe.COMPLETE_MARKER)))
    if fault == 'completion': log.write_text(log.read_text().replace(probe.COMPLETE_MARKER, ''))
    if fault == 'stage': row['stages'].reverse()
    if fault == 'acceptance': row['candidate_adopted'] = True
    if fault == 'sram': row['sram_macro_count'] = 31
    write(step/'setup-probe.json', row)
    with pytest.raises(ValueError):
        probe.validate_diagnostic(step, row['stages'][0]['files']['constraints.sdc']['sha256'], ['fast', 'slow'])


@pytest.mark.parametrize('field', tuple(shared.FINGERPRINT_FILES))
def test_cache_only_boundary_cannot_hide_physical_or_constraint_mutation(tmp_path, field):
    step, row = fixture(tmp_path)
    stage = row['stages'][-1]
    (step/stage['name']/shared.FINGERPRINT_FILES[field]).write_bytes(b'changed physical state')
    repin_stage(step/stage['name'], stage)
    write(step/'setup-probe.json', row)
    with pytest.raises(ValueError):
        probe.validate_diagnostic(step, row['stages'][0]['files']['constraints.sdc']['sha256'], ['fast', 'slow'])


@pytest.mark.parametrize('fault', ['budget', 'count', 'provisional', 'last-gasp', 'crit-vt', 'percentage', 'raw-invocation'])
def test_probe_rejects_hidden_extra_work_or_forged_growth_receipts(tmp_path, fault):
    step, row = fixture(tmp_path)
    if fault == 'budget': row['buffer_budget']['maximum_observed_growth'] = 1
    if fault == 'count': row['timing_metrics']['after_setup']['instance_count'] = 72
    if fault == 'provisional': row['provisional_stages'] = []
    if fault == 'last-gasp': row['repair_invocation']['skip_last_gasp'] = False
    if fault == 'crit-vt': row['repair_invocation']['skip_crit_vt_swap'] = False
    if fault == 'percentage': row['repair_invocation']['native_setup_buffer_percentage_enforced'] = True
    if fault == 'raw-invocation':
        write(step/'repair-invocation.json', {'call_count': 2})
    write(step/'setup-probe.json', row)
    with pytest.raises(ValueError):
        probe.validate_diagnostic(step, row['stages'][0]['files']['constraints.sdc']['sha256'], ['fast', 'slow'])


def test_workflow_uses_new_entrypoint_and_preserves_native_progress():
    import yaml
    path = ROOT/'.github/workflows/timing-setup-probe.yml'
    workflow = yaml.safe_load(path.read_text())
    job = workflow['jobs']['diagnose']
    assert job['timeout-minutes'] == 360 and workflow['concurrency']['cancel-in-progress'] is False
    steps = job['steps']
    commands = '\n'.join(step.get('run', '') for step in steps)
    assert commands.count(' start ') == 1
    assert 'scripts/run_cloud_hold_diagnostic.py' not in commands
    assert 'scripts/run_cloud_setup_probe.py' in commands
    assert '--seconds 9000' in commands and '--seconds 7200' in commands
    assert 'timeout ' not in commands
    uploads = [step for step in steps if step.get('uses', '').startswith('actions/upload-artifact@')]
    assert len(uploads) == 4 and all(step['with']['include-hidden-files'] is True for step in uploads)


def test_resource_guard_applies_before_probe_download_or_spawn(tmp_path, monkeypatch):
    monkeypatch.setattr(shared.common, 'resource_sample', lambda _: dict(available_memory_bytes=662*1024**2, free_disk_bytes=456*1024**2))
    def forbidden(*args, **kwargs):
        raise AssertionError('Resource guard must precede any download/native process')
    monkeypatch.setattr(shared.common, 'download', forbidden)
    monkeypatch.setattr(shared.subprocess, 'Popen', forbidden)
    with pytest.raises(ValueError, match='resource guard'):
        shared.prepare(ROOT/'docs/evidence/timing-cloud-input-20260930.json', tmp_path/'out', tmp_path/'work', probe.specification())
    assert json.loads((tmp_path/'out/result.json').read_text())['diagnostic_kind'] == 'setup_hold_probe'


@pytest.mark.parametrize('kind', ['default', 'probe'])
def test_native_entry_selects_only_requested_tcl_step(tmp_path, monkeypatch, kind):
    registered = []
    class Factory:
        @staticmethod
        def register():
            def register(cls):
                registered.append(cls)
                return cls
            return register
    class Target:
        id = 'OpenROAD.ResizerTimingPostGRT'
    class Classic:
        Steps = [Target]
    class State:
        save_snapshot = staticmethod(lambda *args: None)
    modules = {name: ModuleType(name) for name in ('librelane', 'librelane.flows', 'librelane.flows.classic',
               'librelane.state', 'librelane.steps', 'librelane.__main__')}
    modules['librelane.flows'].Flow = SimpleNamespace(factory=Factory())
    modules['librelane.flows.classic'].Classic = Classic
    modules['librelane.state'].State = State
    modules['librelane.steps'].OpenROAD = SimpleNamespace(ResizerTimingPostGRT=Target)
    called = []
    modules['librelane.__main__'].cli = lambda: called.append(True)
    for name, module in modules.items():
        monkeypatch.setitem(sys.modules, name, module)
    monkeypatch.setattr(sys, 'argv', ['entrypoint.py', '_native_flow'])
    spec = None if kind == 'default' else probe.specification()
    shared.native_flow(spec)
    native_step = registered[0].Steps[0]()
    assert native_step.outputs == []
    assert native_step.get_script_path() == str(ROOT/shared.diagnostic_spec(spec).step)
    assert called == [True] and '_native_flow' not in sys.argv


def test_worker_uses_probe_entry_but_original_control_step(tmp_path, monkeypatch):
    output = tmp_path/'out'
    source_sdc = tmp_path/'source.sdc'
    source_sdc.write_text('source SDC')
    write(output/'result.json', dict(status='PREPARED', work=str(tmp_path/'work'), method_files={}, diagnostic_kind='setup_hold_probe'))
    write(output/'prepared/state.json', {'sdc': str(source_sdc)})
    write(output/'source-config.json', {'PNR_CORNERS': ['fast', 'slow']})
    (output/'native-controls').mkdir()
    calls = []
    def inputs(out, row, spec):
        assert spec.name == 'setup_hold_probe'
        return {'pdk_root': 'pdk', 'pdk': 'ihp-sg13g2'}
    monkeypatch.setattr(shared, 'verify_inputs', inputs)
    monkeypatch.setattr(shared.common, 'load_policy', lambda *args: SimpleNamespace(state_pins=lambda path: {}, verify_pins=lambda pins: None))
    monkeypatch.setattr(shared, 'validate_controls', lambda *args: {'cases': 'original four controls'})
    def execute(command, out, row, name, env):
        calls.append(command)
        if name == 'native-diagnostic':
            (out/'run/01-openroad-resizertimingpostgrt').mkdir(parents=True)
    monkeypatch.setattr(shared, 'execute', execute)
    validated = []
    spec = replace(probe.specification(), validator=lambda *args: validated.append(args) or {'checked': True})
    assert shared.worker(output, spec) == 0
    assert 'sw/tests/hold_reproducibility_native.py' in calls[0][2]
    assert calls[0][calls[0].index('--step')+1].endswith('timing_hold_diagnostic_step.tcl')
    assert calls[1][2].endswith('scripts/run_cloud_setup_probe.py') and '_native_flow' in calls[1]
    assert len(validated) == 1
    assert json.loads((output/'result.json').read_text())['status'] == 'COMPLETE_DIAGNOSTIC_ONLY'


def probe_capture(tmp_path):
    output = complete_capture(tmp_path/'old')
    (output/'capture.json').unlink()
    shutil.rmtree(output/'run')  # Only this test's synthetic temporary fixture.
    step, native = fixture(output/'run')
    row = json.loads((output/'result.json').read_text())
    for name in probe.SOURCES:
        path = output/'methods'/name
        if not path.exists():
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text('new probe fixture source '+name)
    row['method_files'] = shared.file_inventory(output/'methods')
    row['diagnostic_kind'] = 'setup_hold_probe'
    row['diagnostic'] = probe.validate_diagnostic(step, row['sdc_sha256'], ['fast', 'slow'])
    row['output_files'] = shared.file_inventory(output/'run')
    write(output/'result.json', row)
    destination = tmp_path/'probe-capture'
    shared.capture(output, destination)
    return destination


@pytest.mark.parametrize('fault', [None, 'method', 'kind', 'control'])
def test_probe_capture_replays_new_method_inventory_and_original_native_gate(tmp_path, fault):
    output = probe_capture(tmp_path)
    if fault == 'method':
        (output/'methods/hw/soc/pnr/timing_setup_hold_probe_step.tcl').write_text('corrupt probe')
    if fault == 'kind':
        row = json.loads((output/'result.json').read_text())
        row['diagnostic_kind'] = 'hold_readback'
        write(output/'result.json', row)
    if fault == 'control':
        (output/'native-controls/native.log').write_text('corrupt gate')
    if fault is None:
        assert shared.validate_capture(output, spec=probe.specification())['diagnostic_kind'] == 'setup_hold_probe'
        with pytest.raises(ValueError, match='kind'):
            shared.validate_capture(output)
    else:
        with pytest.raises(ValueError):
            shared.validate_capture(output, spec=probe.specification())
