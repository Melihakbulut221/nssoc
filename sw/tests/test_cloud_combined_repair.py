# SPDX-FileCopyrightText: 2026 Hasan Melih Akbulut
# SPDX-License-Identifier: Apache-2.0
"""Pure controls for cumulative budget, isolated export and replay acceptance."""
import copy
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys

import pytest

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT/'scripts'))
import run_cloud_combined_repair as repair
from test_cloud_targeted_hold import invocation_fixture
from test_cloud_hold_diagnostic import stage_fixture, repin_stage, write


def metrics(setup=-5., hold=-2., count=50):
    return dict(recorded_ms=1000, instance_count=count, setup_wns_seconds=setup*1e-9,
        setup_tns_seconds=-10e-9, hold_wns_seconds=hold*1e-9, hold_tns_seconds=-3e-9,
        setup_violating_endpoints=20, hold_violating_endpoints=20,
        slew_violations=0, capacitance_violations=1)


@pytest.mark.parametrize('fault', [None, 'historical-setup', 'historical-hold', 'fresh-count', 'fresh-tns',
                                 'electrical', 'no-setup-gain', 'no-hold-gain', 'reload'])
def test_original_guards_apply_to_reloaded_candidate_not_in_memory(fault):
    before = metrics()
    final = metrics(setup=-4., hold=-1.)
    values = dict(matched_before=before, after_hold=copy.deepcopy(final),
                  reload_first=copy.deepcopy(final), reload_repeat=final)
    source = dict(setup_wns_ns=-4.710829, hold_wns_ns=-1.840329)
    if fault == 'historical-setup': final['setup_wns_seconds'] = -4.9e-9
    if fault == 'historical-hold': final['hold_wns_seconds'] = -1.9e-9
    if fault == 'fresh-count': final['setup_violating_endpoints'] += 1
    if fault == 'fresh-tns': final['setup_tns_seconds'] -= 1e-9
    if fault == 'electrical': final['capacitance_violations'] += 1
    if fault == 'no-setup-gain': final['setup_wns_seconds'] = before['setup_wns_seconds']
    if fault == 'no-hold-gain': final['hold_wns_seconds'] = before['hold_wns_seconds']
    row = repair.guard_assessment(values, source, fault != 'reload')
    assert row['aggregate_estimate_guard_passed'] is (fault is None)
    assert row['candidate_adopted'] is False and row['timing_accepted'] is False
    assert row['zero_violations'] is False
    assert row['disposition'] == ('ISOLATED_IMPROVEMENT_REQUIRES_SIGNOFF' if fault is None else 'REJECTED_ISOLATED_CANDIDATE')


def tcl(script):
    result = subprocess.run(['/usr/bin/tclsh'], input=script, text=True, capture_output=True, check=True)
    assert not result.stderr, result.stderr
    return result.stdout.strip()


def test_cumulative_budget_cannot_reset_between_hold_batches():
    helper = ROOT/'hw/soc/pnr/timing_combined_repair_helpers.tcl'
    result = tcl(f'''source {{{helper}}}
puts [nssoc_combined_budget 100 40 125]
puts [nssoc_combined_budget 100 40 140]
puts [catch {{nssoc_combined_budget 100 40 141}}]
puts [catch {{nssoc_combined_budget 100 40 99}}]
''')
    assert result.splitlines() == ['15', '0', '1', '1']


@pytest.mark.parametrize('improve', [False, True])
def test_no_gain_stops_but_a_measured_gain_allows_next_bounded_pass(improve):
    before = metrics()
    after = copy.deepcopy(before)
    if improve: after['hold_wns_seconds'] += 1e-12
    assert repair.hold_progress(before, after) is improve
    helper = ROOT/'hw/soc/pnr/timing_combined_repair_helpers.tcl'
    def as_tcl(row): return '[dict create '+' '.join(f'{k} {v}' for k, v in row.items())+']'
    assert tcl(f'source {{{helper}}}\nputs [nssoc_combined_hold_progress {as_tcl(before)} {as_tcl(after)}]\n') == str(int(improve))


def batch_fixture(tmp_path):
    directory = tmp_path/'hold_batch_1'
    directory.mkdir()
    invocation, _, _, corners = invocation_fixture(directory)
    before = metrics()
    after = copy.deepcopy(before)
    row = dict(initial_instance_count=50, global_buffer_budget=20, setup_profile='setup_batch4',
        setup_call_count=1, hold_batch_limit=4, setup_started_ms=10, setup_finished_ms=20,
        hold_stop_reason='NO_HOLD_PROGRESS', hold_batches=[])
    batch = dict(index=1, before=before, after=after, started_ms=30, finished_ms=40,
                 **{k: invocation[k] for k in ('selection', 'result', 'selection_sha256', 'result_sha256')})
    row['hold_batches'] = [batch]
    (tmp_path/'after_setup-metrics.json').write_text(json.dumps(before))
    (tmp_path/'hold_batch_1-metrics.json').write_text(json.dumps(after))
    (directory/'invocation.json').write_text(json.dumps(batch))
    return row, batch, corners


@pytest.mark.parametrize('fault', [None, 'reset-budget', 'call-overrun', 'waive-setup', 'raw-pin', 'early-stop', 'receipt', 'target-order'])
def test_batch_receipts_preserve_native_guards_and_cumulative_limit(tmp_path, fault):
    row, batch, corners = batch_fixture(tmp_path)
    if fault == 'reset-budget': row['global_buffer_budget'] = 28
    if fault == 'call-overrun':
        batch['result']['calls'][0].update(actual_instance_count=71, actual_instance_growth=21)
    if fault == 'waive-setup': batch['selection']['allow_setup_violations'] = 1
    if fault == 'raw-pin': batch['selection_sha256'] = '0'*64
    if fault == 'early-stop': row['hold_stop_reason'] = 'FOUR_BATCH_LIMIT'
    if fault == 'target-order': batch['selection']['targets'].reverse()
    if fault != 'receipt':
        (tmp_path/'hold_batch_1/invocation.json').write_text(json.dumps(batch))
    else: batch['finished_ms'] += 1
    if fault is None:
        assert repair.validate_batches(tmp_path, row, corners)['hold_batches'] == 1
    else:
        with pytest.raises(ValueError): repair.validate_batches(tmp_path, row, corners)


def test_capture_includes_only_isolated_candidate_views_with_pins(tmp_path, monkeypatch):
    output, dest = tmp_path/'output', tmp_path/'capture'
    candidate = output/'run/01-openroad-resizertimingpostgrt/candidate'
    candidate.mkdir(parents=True)
    for name in repair.VIEW_NAMES: (candidate/name).write_bytes(b'isolated '+name.encode())
    monkeypatch.setattr(repair.shared, 'observation', lambda _: dict(status='COMPLETE_DIAGNOSTIC_ONLY'))
    row = repair.capture(output, dest)
    assert len(row['files']) == 4
    assert row['restart_checkpoint_accepted'] is False
    for name in repair.VIEW_NAMES:
        rel = f'run/01-openroad-resizertimingpostgrt/candidate/{name}'
        assert row['files'][rel]['sha256'] == repair.shared.common.sha(candidate/name)
        assert (dest/rel).read_bytes() == (candidate/name).read_bytes()


def test_capture_rejects_unexpected_view_and_symlink(tmp_path, monkeypatch):
    output, dest = tmp_path/'output', tmp_path/'capture'
    candidate = output/'run/01-openroad-resizertimingpostgrt/candidate'
    candidate.mkdir(parents=True)
    (candidate/'unknown.odb').write_bytes(b'unknown')
    monkeypatch.setattr(repair.shared, 'observation', lambda _: dict(status='COMPLETE_DIAGNOSTIC_ONLY'))
    with pytest.raises(ValueError, match='Unexpected candidate'): repair.capture(output, dest)


def test_methods_frozen_and_tcl_syntax_complete():
    assert repair.specification().sources == repair.SOURCES
    assert set(repair.targeted.SOURCES) < set(repair.SOURCES)
    for name in repair.SOURCES:
        assert (ROOT/name).is_file()
        if name.startswith('hw/soc/pnr/timing_combined'):
            output = tcl(f'set f [open {{{ROOT/name}}}]; set s [read $f]; close $f; puts [info complete $s]\n')
            assert output == '1'


def test_child_restores_candidate_views_after_pinned_librelane_env_reset(tmp_path):
    """Execute the real child startup branch with pure Tcl I/O stand-ins.

    The runtime's io.tcl begins by sourcing _TCL_ENV_IN. Recreating that actual
    side effect catches accidental reuse of the original C10 rather than the
    intended child ODB/SDC, without invoking any native hardware tool.
    """
    common = tmp_path/'scripts/openroad/common'
    common.mkdir(parents=True)
    out = tmp_path/'evidence'
    out.mkdir()
    odb, sdc = tmp_path/'tiny.odb', tmp_path/'tiny.sdc'
    odb.write_bytes(b'pure fixture database')
    sdc.write_bytes(b'pure fixture ideal sdc')
    envfile = tmp_path/'_env.tcl'
    envfile.write_text('set ::env(CURRENT_ODB) original-c10.odb\n'
        'set ::env(_SDC_IN) original-c10.sdc\nset ::env(STEP_DIR) original-output\n')
    (common/'io.tcl').write_text('''source $::env(_TCL_ENV_IN)
namespace eval ord {proc get_db_block {} {return fixture_block}}
proc fixture_block {method} {return tiny}
proc read_current_odb {} {
  foreach key {CURRENT_ODB _SDC_IN STEP_DIR} {
    if {$::env($key) ne $::env(EXPECTED_$key)} {error "Child lost intended $key"}
  }
  if {$::env(OPENLANE_SDC_IDEAL_CLOCKS) != 1} {error "Tiny ideal mode lost"}
}
proc write_sdc {flag destination} {file copy $::env(_SDC_IN) $destination}
''')
    (common/'resizer.tcl').write_text('# Pure definitions only\n')
    env = os.environ.copy()
    env.update(SCRIPTS_DIR=str(tmp_path/'scripts'), _TCL_ENV_IN=str(envfile),
        NSSOC_HOLD_DIAGNOSTIC_HELPER=str(ROOT/'hw/soc/pnr/timing_hold_reproducibility.tcl'),
        NSSOC_TARGETED_METHOD_ROOT=str(ROOT), NSSOC_COMBINED_ROOT=str(out),
        NSSOC_COMBINED_RELOAD_STAGE='startup_control', NSSOC_COMBINED_PARENT_PID=str(os.getpid()),
        CURRENT_ODB=str(odb), _SDC_IN=str(sdc), STEP_DIR=str(out),
        EXPECTED_CURRENT_ODB=str(odb), EXPECTED__SDC_IN=str(sdc), EXPECTED_STEP_DIR=str(out),
        NSSOC_COMBINED_ODB_SHA=hashlib.sha256(odb.read_bytes()).hexdigest(),
        NSSOC_COMBINED_SDC_SHA=hashlib.sha256(sdc.read_bytes()).hexdigest(),
        NSSOC_TARGETED_ACTUAL_ELF_SHA256=hashlib.sha256(Path('/usr/bin/tclsh').resolve().read_bytes()).hexdigest())
    result = subprocess.run(['/usr/bin/tclsh', str(ROOT/'hw/soc/pnr/timing_combined_reload.tcl')],
        env=env, text=True, capture_output=True, check=True)
    assert result.stdout.strip() == 'NSSOC_COMBINED_STARTUP_CONTROL_PASS'
    receipt = json.loads((out/'startup-control.json').read_text())
    assert receipt['odb_sha256'] == env['NSSOC_COMBINED_ODB_SHA']
    assert (out/'startup-control.sdc').read_bytes() == sdc.read_bytes()


def full_fixture(output, monkeypatch):
    step = output/'run/01-openroad-resizertimingpostgrt'
    step.mkdir(parents=True)
    row, batch, corners = batch_fixture(step)
    stages = []
    for name in repair.STAGES:
        stage = stage_fixture(step/name, name)
        stage['vertex_path_semantics_match'] = True
        for phase in ('before', 'after'):
            stage[f'native_global_tns_seconds_{phase}'] = min(c[f'native_tns_seconds_{phase}'] for c in stage['corners'])
        (step/name/'placement.tsv').write_text('instance\tmaster\tx_dbu\ty_dbu\torientation\tstatus\n'+''.join(
            f'cell{i}\t'+('SP6TSRAM512x64' if i < 32 else 'INV')+f'\t{i}\t0\tR0\tPLACED\n' for i in range(50)))
        write(step/name/'native.json', {k: v for k, v in stage.items() if k not in ('files', 'fingerprints')})
        repin_stage(step/name, stage)
        write(step/f'{name}-stage.json', stage)
        stages.append(stage)
    values = {name: dict(metrics(), hold_violating_endpoints=2) for name in repair.STAGES}
    for name, value in values.items(): write(step/f'{name}-metrics.json', value)
    candidate = step/'candidate'
    candidate.mkdir()
    for name, data in {'soc_top.odb': b'fixture db', 'soc_top.def': b'fixture def',
                      'soc_top.sdc': (step/'after_hold/constraints.sdc').read_bytes(),
                      'soc_top.v': (step/'after_hold/connectivity.v').read_bytes()}.items():
        (candidate/name).write_bytes(data)
    candidate_pins = repair.shared.file_inventory(candidate)
    source_sdc = candidate_pins['soc_top.sdc']['sha256']
    controls = output/'native-controls/targeted'
    controls.mkdir(parents=True)
    (controls/'tiny-after.odb').write_bytes(b'fixture tiny')
    (controls/'after.sdc').write_bytes(b'fixture tiny sdc')
    (step/'startup-control.sdc').write_bytes(b'fixture tiny sdc')
    control = dict(status='PASS_TINY_INDEPENDENT_RELOAD', pid=2, parent_pid=1,
        executable_sha256=repair.targeted.NATIVE_IDENTITY['actual_elf']['sha256'],
        odb_sha256=repair.shared.common.sha(controls/'tiny-after.odb'),
        sdc_sha256=repair.shared.common.sha(controls/'after.sdc'))
    write(step/'startup-control.json', control)
    (step/'startup-control.log').write_text('NSSOC_COMBINED_STARTUP_CONTROL_PASS\n')
    processes = []
    for i, name in enumerate(repair.STAGES[-2:], 10):
        process = dict(pid=i, parent_pid=1, executable_sha256=control['executable_sha256'],
            odb_sha256=candidate_pins['soc_top.odb']['sha256'], sdc_sha256=source_sdc, repair_invocations=0)
        write(step/f'{name}-process.json', process)
        write(step/f'{name}-headroom.json', dict(available_kib=8000000, parent_rss_kib=3000000, required_kib=3750000))
        (step/f'{name}.log').write_text('NSSOC_COMBINED_INDEPENDENT_RELOAD_COMPLETE '+name+'\n')
        processes.append(process)
    row.update(schema=1, status='COMPLETE_DIAGNOSTIC_ONLY', candidate_adopted=False, timing_accepted=False,
        manufacturing_approval=False, thresholds_changed=False, source_checkpoint_preserved=True,
        estimated_global_route_only=True, sram_macro_count=32, sram_placement_preserved=True,
        matched_before_census={}, stages=stages, timing_metrics=values, candidate_files=candidate_pins,
        independent_reload_processes=processes)
    write(step/'combined-repair.json', row)
    write(output/'source-manifest.json', dict(selected_source_metrics=dict(setup_wns_ns=-4.710829, hold_wns_ns=-1.840329)))
    (step/'openroad-resizertimingpostgrt.log').write_text('\n'.join([repair.targeted.GATE,
        'NSSOC_COMBINED_STARTUP_CONTROL_PASS_BEFORE_C10_LOAD', 'NSSOC_COMBINED_SETUP_BATCH4_BEGIN',
        'NSSOC_COMBINED_SETUP_BATCH4_END', 'NSSOC_COMBINED_REPAIR_COMPLETE_NO_ADOPTION'])+'\n')
    monkeypatch.setattr(repair.targeted, 'validate_targeted_controls', lambda _: {'fixture': True})
    monkeypatch.setattr(repair.targeted, 'validate_baseline', lambda *args: {})
    monkeypatch.setattr(repair, 'validate_batches', lambda *args: {'fixture': True})
    return step, row, source_sdc


@pytest.mark.parametrize('fault', [None, 'same-process', 'odb-pin', 'native-pin', 'tiny-pin', 'tiny-marker',
    'replay-repair', 'missing-view', 'extra-view', 'headroom', 'macro', 'replay-route'])
def test_full_independent_reload_evidence_and_export_closure(tmp_path, monkeypatch, fault):
    step, row, source_sdc = full_fixture(tmp_path, monkeypatch)
    process = row['independent_reload_processes'][1]
    if fault == 'same-process': process['pid'] = row['independent_reload_processes'][0]['pid']
    if fault == 'odb-pin': process['odb_sha256'] = '0'*64
    if fault == 'native-pin': process['executable_sha256'] = '0'*64
    if fault == 'tiny-pin': (step/'startup-control.sdc').write_text('wrong')
    if fault == 'tiny-marker': (step/'startup-control.log').write_text('missing')
    if fault == 'replay-repair': process['repair_invocations'] = 1
    if fault == 'missing-view': (step/'candidate/soc_top.odb').unlink()
    if fault == 'extra-view': (step/'candidate/extra.txt').write_text('extra')
    if fault == 'headroom': write(step/'reload_repeat-headroom.json', dict(available_kib=100, parent_rss_kib=3000000, required_kib=3750000))
    if fault in ('macro', 'replay-route'):
        stage = row['stages'][-1]
        path = step/'reload_repeat'/('placement.tsv' if fault == 'macro' else 'routes.txt')
        path.write_text(path.read_text().replace('cell0\tSP6TSRAM512x64\t0', 'cell0\tSP6TSRAM512x64\t99') if fault == 'macro' else 'different route')
        repin_stage(step/'reload_repeat', stage)
        write(step/'reload_repeat-stage.json', stage)
    write(step/'reload_repeat-process.json', process)
    write(step/'combined-repair.json', row)
    if fault not in (None, 'replay-route'):
        with pytest.raises((ValueError, FileNotFoundError)):
            repair.validate_diagnostic(step, source_sdc, ['fast', 'slow'])
    else:
        result = repair.validate_diagnostic(step, source_sdc, ['fast', 'slow'])
        assert result['candidate_exported'] is True and result['candidate_adopted'] is False
        assert result['aggregate_guard_assessment']['exact_reload_repeatable'] is (fault is None)
        assert result['aggregate_guard_assessment']['disposition'] == 'REJECTED_ISOLATED_CANDIDATE'
        assert json.loads(json.dumps(result)) == result
