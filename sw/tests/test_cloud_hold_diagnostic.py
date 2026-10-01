# SPDX-FileCopyrightText: 2026 Hasan Melih Akbulut
# SPDX-License-Identifier: Apache-2.0
"""Small cloud boundary controls; native chip tools run only in GitHub."""
import json
import gzip
from pathlib import Path
import sys

import pytest

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT/'scripts'))
import run_cloud_hold_diagnostic as diagnostic


def write(path, row):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(row)+'\n')


def source_tree(tmp_path):
    root = tmp_path/'repo'
    for name in diagnostic.SOURCES:
        path = root/name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text('pinned source '+name+'\n')
    return root


def test_method_copy_is_pinned_and_separate_from_original(tmp_path):
    root = source_tree(tmp_path)
    staged = tmp_path/'staged'
    pins = diagnostic.stage_methods(root, staged)
    diagnostic.validate_methods(staged, pins)
    original = root/diagnostic.SOURCES[0]
    original.write_text('later source edit')
    diagnostic.validate_methods(staged, pins)
    assert (staged/diagnostic.SOURCES[0]).read_text() != original.read_text()
    (staged/diagnostic.SOURCES[0]).chmod(0o644)
    (staged/diagnostic.SOURCES[0]).write_text('corrupt frozen source')
    with pytest.raises(ValueError, match='pinned'):
        diagnostic.validate_methods(staged, pins)


@pytest.mark.parametrize('fault', ['symlink', 'missing', 'extra', 'inventory'])
def test_methods_reject_incomplete_or_unsafe_source(tmp_path, fault):
    root = source_tree(tmp_path)
    if fault == 'symlink':
        path = root/diagnostic.SOURCES[0]
        path.unlink()
        path.symlink_to(root/diagnostic.SOURCES[1])
    if fault == 'missing':
        (root/diagnostic.SOURCES[0]).unlink()
    staged = tmp_path/'staged'
    if fault in ('symlink', 'missing'):
        with pytest.raises(ValueError):
            diagnostic.stage_methods(root, staged)
    else:
        pins = diagnostic.stage_methods(root, staged)
        if fault == 'extra':
            (staged/'surprise.py').write_text('extra')
        else:
            del pins[diagnostic.SOURCES[0]]
        with pytest.raises(ValueError):
            diagnostic.validate_methods(staged, pins)


def test_environment_keeps_runner_lifecycle_but_removes_other_recipes(monkeypatch):
    for key in ('NSSOC_HOLD_FAULT', 'NSSOC_TIMING_EXPERIMENT_PROFILE', 'NSSOC_CRITICAL_PLACEMENT_SCRIPT'):
        monkeypatch.setenv(key, 'stale')
    monkeypatch.setenv('RUNNER_TRACKING_ID', 'github-owned-job')
    env = diagnostic.clean_environment()
    assert not any(key.startswith(('NSSOC_HOLD_', 'NSSOC_TIMING_')) for key in env)
    assert 'NSSOC_CRITICAL_PLACEMENT_SCRIPT' not in env
    assert env['RUNNER_TRACKING_ID'] == 'github-owned-job'
    assert env['PYTHONDONTWRITEBYTECODE'] == '1'


def test_resource_guard_prevents_any_native_start_and_preserves_error(tmp_path, monkeypatch):
    manifest = ROOT/'docs/evidence/timing-cloud-input-20260930.json'
    monkeypatch.setattr(diagnostic.common, 'resource_sample', lambda _: dict(available_memory_bytes=423*1024**2, free_disk_bytes=604*1024**2))
    def forbidden(*args, **kwargs):
        raise AssertionError('Native/download must not start under resource guard')
    monkeypatch.setattr(diagnostic.common, 'download', forbidden)
    monkeypatch.setattr(diagnostic.subprocess, 'Popen', forbidden)
    with pytest.raises(ValueError, match='resource guard'):
        diagnostic.prepare(manifest, tmp_path/'output', tmp_path/'work')
    row = json.loads((tmp_path/'output/result.json').read_text())
    assert row['status'] == 'FAILED_PRESERVED'
    assert row['candidate_adopted'] is False and row['timing_accepted'] is False
    assert row['manufacturing_approval'] is False and row['native_elapsed_watchdog'] is False


@pytest.mark.parametrize('value', [-1, float('inf'), float('nan')])
def test_observer_rejects_invalid_duration(tmp_path, value):
    with pytest.raises(ValueError):
        diagnostic.wait(tmp_path, value)


def test_observer_stops_observing_not_worker(tmp_path, monkeypatch):
    write(tmp_path/'result.json', dict(status='RUNNING'))
    def forbidden(*args, **kwargs):
        raise AssertionError('Observers must not signal native work')
    monkeypatch.setattr(diagnostic.os, 'kill', forbidden)
    receipt = diagnostic.wait(tmp_path, 0, tmp_path/'github-output')
    assert receipt['terminal'] is False and receipt['worker_was_not_signaled'] is True
    assert (tmp_path/'github-output').read_text() == 'terminal=false\n'
    write(tmp_path/'result.json', dict(status='COMPLETE_DIAGNOSTIC_ONLY'))
    assert diagnostic.wait(tmp_path)['terminal'] is True


def test_failed_and_missing_workers_are_terminal(tmp_path):
    assert diagnostic.observation(tmp_path) == dict(status='NO_RESULT_INCOMPLETE', terminal=True)
    write(tmp_path/'result.json', dict(status='FAILED_PRESERVED'))
    assert diagnostic.observation(tmp_path)['terminal'] is True
    write(tmp_path/'result.json', dict(status='RUNNING'))
    write(tmp_path/'launch.json', dict(pid=9999999999, identity={'birth':'1'}))
    assert diagnostic.observation(tmp_path)['status'] == 'WORKER_GONE_INCOMPLETE'


@pytest.mark.parametrize('status', ['RUNNING', 'FAILED_PRESERVED', 'COMPLETE_DIAGNOSTIC_ONLY'])
def test_snapshots_have_all_report_rows_but_no_restart_database(tmp_path, status):
    output = tmp_path/'output'
    write(output/'result.json', dict(status=status))
    (output/'endpoints.tsv').write_text('all endpoint rows\n')
    (output/'chip.odb').write_bytes(b'not a published restart checkpoint')
    (output/'native.log').write_text('actual native log\n')
    (output/'result.json.tmp').write_text('partial atomic record')
    capture = tmp_path/'capture'
    row = diagnostic.capture(output, capture)
    assert row['complete_diagnostic_evidence'] is (status == 'COMPLETE_DIAGNOSTIC_ONLY')
    assert row['restart_checkpoint_accepted'] is False and row['candidate_adopted'] is False
    assert row['timing_accepted'] is False and row['manufacturing_approval'] is False
    assert set(row['files']) == {'result.json', 'endpoints.tsv', 'native.log'}
    assert (capture/'endpoints.tsv').read_text() == 'all endpoint rows\n'
    for name, pin in row['files'].items():
        diagnostic.common.verify_file(capture/name, pin)
    with pytest.raises(FileExistsError):
        diagnostic.capture(output, capture)


def test_snapshot_completion_race_is_explicitly_incomplete(tmp_path, monkeypatch):
    output = tmp_path/'output'
    write(output/'result.json', dict(status='COMPLETE_DIAGNOSTIC_ONLY'))
    monkeypatch.setattr(diagnostic, 'observation', lambda _: dict(status='RUNNING', terminal=False))
    row = diagnostic.capture(output, tmp_path/'capture')
    assert row['complete_diagnostic_evidence'] is False
    assert row['snapshot_is_atomic_across_files'] is False


def test_snapshot_rejects_symlink_or_nested_destination(tmp_path):
    output = tmp_path/'output'
    write(output/'result.json', dict(status='RUNNING'))
    with pytest.raises(ValueError, match='outside'):
        diagnostic.capture(output, output/'inside')
    (output/'escape').symlink_to('/proc/meminfo')
    with pytest.raises(ValueError, match='Symlink'):
        diagnostic.capture(output, tmp_path/'capture')


def control_record(methods):
    return dict(status='PASS_NATIVE_HOLD_DIAGNOSTIC_CONTROLS',
                cases={name: {'passed':True} for name in ('complete_coverage','bad_coverage','corrupt_units','route_mutation')},
                method_sha256={name: methods[name]['sha256'] for name in diagnostic.SOURCES if name.endswith(('.tcl','hold_reproducibility_native.py'))})


@pytest.mark.parametrize('fault', [None, 'status', 'missing', 'failed', 'extra', 'source'])
def test_native_control_gate_requires_every_named_control(tmp_path, fault):
    root = source_tree(tmp_path)
    pins = diagnostic.stage_methods(root, tmp_path/'methods')
    row = native_control_fixture(tmp_path/'controls',pins)
    if fault == 'status': row['status'] = 'UNKNOWN'
    if fault == 'missing': del row['cases']['bad_coverage']
    if fault == 'failed': row['cases']['corrupt_units']['passed'] = False
    if fault == 'extra': row['cases']['not_native'] = {'passed':True}
    if fault == 'source': row['method_sha256'][next(iter(row['method_sha256']))] = '0'*64
    path = tmp_path/'controls/result.json'
    write(path, row)
    if fault is None:
        assert diagnostic.validate_controls(path, pins) == row
    else:
        with pytest.raises(ValueError):
            diagnostic.validate_controls(path, pins)


def test_control_failure_never_loads_full_design(tmp_path, monkeypatch):
    output = tmp_path/'output'
    write(output/'result.json', dict(status='PREPARED', work=str(tmp_path/'work'), method_files={}))
    manifest = dict(pdk_root='pdk')
    monkeypatch.setattr(diagnostic, 'verify_inputs', lambda *args: manifest)
    class Policy:
        @staticmethod
        def state_pins(path): return {}
    monkeypatch.setattr(diagnostic.common, 'load_policy', lambda *args: Policy())
    calls = []
    def fail_native(command, out, record, name, env):
        calls.append(name)
        raise RuntimeError('bad coverage negative control failed')
    monkeypatch.setattr(diagnostic, 'execute', fail_native)
    assert diagnostic.worker(output) == 1
    assert calls == ['native-controls']
    row = json.loads((output/'result.json').read_text())
    assert row['status'] == 'FAILED_PRESERVED' and 'coverage' in row['error']


def test_execute_passes_resource_limit_without_timeout_or_session_pipe(tmp_path, monkeypatch):
    calls = []
    monkeypatch.setattr(diagnostic.common, 'resource_sample', lambda _: dict(available_memory_bytes=10*diagnostic.GIB, free_disk_bytes=4*diagnostic.GIB))
    class Child:
        pid = 100
        returncode = 0
        @staticmethod
        def poll(): return 0
    def spawn(command, **kwargs):
        calls.append((command, kwargs))
        return Child()
    monkeypatch.setattr(diagnostic.subprocess, 'Popen', spawn)
    row = {}
    diagnostic.execute(['native','probe'], tmp_path, row, 'test-native', {})
    kwargs = calls[0][1]
    assert kwargs['preexec_fn'] is diagnostic.common.limits
    assert kwargs['stdin'] is diagnostic.subprocess.DEVNULL
    assert 'timeout' not in kwargs and kwargs['close_fds'] is True
    assert row['native_address_space_limit_bytes'] == 8*diagnostic.GIB


def test_workflow_resource_and_progress_contract():
    import yaml
    workflow = yaml.load((ROOT/'.github/workflows/timing-hold-diagnostic.yml').read_text(), Loader=yaml.BaseLoader)
    assert set(workflow['on']) == {'push','workflow_dispatch'}
    assert workflow['on']['push']['paths'] == ['.github/workflows/timing-hold-diagnostic.yml']
    job = workflow['jobs']['diagnose']
    assert job['timeout-minutes'] == '360' and job['runs-on'] == 'ubuntu-22.04'
    assert '${{ runner.temp }}' not in json.dumps(job['env'])
    steps = job['steps']
    command = '\n'.join(step.get('run','') for step in steps)
    assert '--seconds 60' in command and '--seconds 9000' in command and '--seconds 7200' in command
    assert 'timeout ' not in command
    assert command.count(' start ') == 1
    assert 'docs/evidence/timing-cloud-input-20260930.json' in command
    uploads = [step for step in steps if step.get('uses','').startswith('actions/upload-artifact@')]
    assert len(uploads) == 4
    # The capture inventories the staged methods/.github/workflows source.
    # Default artifact handling would omit it and break the byte/hash closure.
    assert all(step['with'].get('include-hidden-files') == 'true' for step in uploads)
    assert all(step['with']['path'].startswith('hold-diagnostic-') for step in uploads)
    assert all(step.get('if') == 'always()' for step in steps if step.get('name','').startswith('Preserve outputs'))


def stage_fixture(directory, name, extra_corner=False):
    directory.mkdir(parents=True)
    for filename, text in {'constraints.sdc':'set_clock_uncertainty 0.1 [all_clocks]\n',
                           'connectivity.v':'module top; endmodule\n','placement.tsv':'cell\t1\t2\tR0\n',
                           'routes.txt':'net route segment 1 2 3 4\n'}.items():
        (directory/filename).write_text(text)
    (directory/'parasitics.tsv.gz').write_bytes(gzip.compress(b'full parasitic tuples\n', mtime=0))
    (directory/'endpoints.tsv').write_text('endpoint\tglobal_vertex_slack_seconds\na\t-5e-10\nb\t-2.5e-10\nc\tUNCONSTRAINED\n')
    table = 'corner\tendpoint\tmin_rise_seconds\tmin_fall_seconds\tmin_seconds\n'
    slacks = {'fast':[-5e-10, -2.5e-10], 'slow':[-3.75e-10, 2e-10]}
    if extra_corner: slacks['typical'] = [-4e-10,1e-10]
    corners = []
    for corner, values in slacks.items():
        total = 0.
        for endpoint, value in zip(('a','b'), values):
            table += f'{corner}\t{endpoint}\t{value:.17g}\tUNCONSTRAINED\t{value:.17g}\n'
            if value < 0: total += value
        table += f'{corner}\tc\tUNCONSTRAINED\tUNCONSTRAINED\tUNCONSTRAINED\n'
        corners.append(dict(name=corner, constrained_endpoints=2, unrepresented_endpoints=1,
                            negative_path_endpoints=sum(value < 0 for value in values),
                            native_tns_seconds_before=total, native_tns_seconds_after=total,
                            fixed_order_tns_seconds=total, native_wns_seconds=min(values)))
    (directory/'hold-endpoints.tsv').write_text(table)
    row = dict(name=name, endpoint_count=3, engine_endpoint_count=3, exported_endpoint_count=3,
               negative_vertex_endpoints=2, engine_negative_vertex_endpoints=2,
               corners=corners, all_endpoint_coverage=True, value_units='seconds',time_unit_seconds=1e-9,
               numeric_format='%.17g',raw_getters='SWIG Slack delayAsFloat -> Tcl double, SI seconds')
    write(directory/'native.json', row)
    repin_stage(directory, row)
    return row


def repin_stage(directory, row):
    row['files'] = diagnostic.file_inventory(directory)
    row['fingerprints'] = {name: row['files'][file]['sha256'] for name,file in diagnostic.FINGERPRINT_FILES.items()}


def diagnostic_fixture(tmp_path):
    step = tmp_path/'step'
    stages = [stage_fixture(step/name, name) for name in diagnostic.STAGES]
    row = dict(schema=1,status='COMPLETE_DIAGNOSTIC_ONLY', stages=stages,
               timing_accepted=False, candidate_adopted=False, manufacturing_approval=False,
               sram_macro_count=32, sram_placement_preserved=True)
    write(step/'hold-diagnostic.json', row)
    (step/'openroad-resizertimingpostgrt.log').write_text(diagnostic.COMPLETE_MARKER+'\n')
    return step, row


def test_complete_stage_reconstructs_all_endpoint_corner_counts_and_reductions(tmp_path):
    row = stage_fixture(tmp_path/'stage','same_state_repeat')
    checked = diagnostic.validate_stage(tmp_path/'stage', row, row['files']['constraints.sdc']['sha256'])
    assert checked['endpoint_count'] == 3 and checked['negative_vertex_endpoints'] == 2
    assert checked['reductions']['fast']['exported_negative_endpoints'] == 2
    assert checked['reductions']['slow']['exported_negative_endpoints'] == 1
    assert checked['reductions']['fast']['native_minus_fixed_seconds'] == 0


@pytest.mark.parametrize('fault', ['missing-row','duplicate-row','extra-row','corner-row','corner-missing','nan',
                                  'units','format','count','negative','corner-count','sum','minimum','fingerprint','hash'])
def test_stage_rejects_incomplete_census_wrong_units_or_forged_counts(tmp_path, fault):
    directory = tmp_path/'stage'
    row = stage_fixture(directory,'matched_before')
    path = directory/'hold-endpoints.tsv'
    text = path.read_text()
    if fault == 'missing-row': path.write_text('\n'.join(text.splitlines()[:-1])+'\n')
    if fault == 'duplicate-row': path.write_text(text+text.splitlines()[1]+'\n')
    if fault == 'extra-row': path.write_text(text+'fast\tz\t0\t0\t0\n')
    if fault == 'corner-row': path.write_text(text.replace('fast\ta','unknown\ta'))
    if fault == 'corner-missing': row['corners'].pop()
    if fault == 'nan': path.write_text(text.replace('UNCONSTRAINED','nan',1))
    if fault == 'units': row['time_unit_seconds'] = 1
    if fault == 'format': row['numeric_format'] = '%.6g'
    if fault == 'count': row['exported_endpoint_count'] = 2
    if fault == 'negative': row['engine_negative_vertex_endpoints'] = 1
    if fault == 'corner-count': row['corners'][0]['constrained_endpoints'] = 1
    if fault == 'sum': row['corners'][0]['fixed_order_tns_seconds'] = -100
    if fault == 'minimum': path.write_text(text.replace('fast\ta\t-5.0000000000000003e-10\tUNCONSTRAINED\t-5.0000000000000003e-10','fast\ta\t0\t0\t-1'))
    repin_stage(directory,row)
    if fault == 'fingerprint': row['fingerprints']['routing'] = '0'*64
    if fault == 'hash': path.write_text(text+'unrecorded corruption')
    with pytest.raises(ValueError):
        diagnostic.validate_stage(directory,row,row['files']['constraints.sdc']['sha256'])


def test_all_noop_stages_can_report_precision_drift_without_waiving_guard(tmp_path):
    step, row = diagnostic_fixture(tmp_path)
    row['stages'][3]['corners'][0]['native_tns_seconds_after'] -= 1e-14
    stage = row['stages'][3]
    write(step/stage['name']/'native.json', {key:value for key,value in stage.items() if key not in ('files','fingerprints')})
    repin_stage(step/stage['name'],stage)
    write(step/'hold-diagnostic.json', row)
    checked = diagnostic.validate_diagnostic(step,row['stages'][0]['files']['constraints.sdc']['sha256'],['fast','slow'])
    assert checked['independently_checked_stages']['same_state_repeat']['reductions']['fast']['native_minus_fixed_seconds'] < 0
    assert checked['thresholds_changed'] is False
    assert all(checked[key] is False for key in ('timing_accepted','candidate_adopted','manufacturing_approval'))


@pytest.mark.parametrize('fault', ['route','parasitics','placement','netlist','constraints','stage','corner','macro','acceptance','marker'])
def test_full_diagnostic_rejects_mutation_and_incomplete_proof(tmp_path,fault):
    step, row = diagnostic_fixture(tmp_path)
    expected_sdc = row['stages'][0]['files']['constraints.sdc']['sha256']
    if fault in diagnostic.FINGERPRINT_FILES:
        stage = row['stages'][3]
        directory = step/stage['name']
        (directory/diagnostic.FINGERPRINT_FILES[fault]).write_bytes(b'different')
        repin_stage(directory,stage)
    if fault == 'route':
        stage = row['stages'][3]
        (step/stage['name']/'routes.txt').write_text('physically different routing')
        repin_stage(step/stage['name'],stage)
    if fault == 'stage': row['stages'].pop()
    if fault == 'macro': row['sram_macro_count'] = 31
    if fault == 'acceptance': row['timing_accepted'] = True
    if fault == 'marker': (step/'openroad-resizertimingpostgrt.log').write_text('incomplete')
    write(step/'hold-diagnostic.json',row)
    with pytest.raises(ValueError):
        diagnostic.validate_diagnostic(step,expected_sdc,['fast'] if fault == 'corner' else ['fast','slow'])


def test_capture_rejects_complete_result_inside_partial_snapshot(tmp_path):
    output = tmp_path/'output'
    write(output/'result.json', dict(status='RUNNING'))
    destination = tmp_path/'snapshot'
    diagnostic.capture(output,destination)
    write(destination/'result.json', dict(status='COMPLETE_DIAGNOSTIC_ONLY'))
    with pytest.raises(ValueError,match='Partial'):
        diagnostic.validate_capture(destination)


def complete_capture(tmp_path):
    output = tmp_path/'output'
    run = output/'run'
    step, native = diagnostic_fixture(run)
    target = run/'01-openroad-resizertimingpostgrt'
    step.rename(target)
    source_sdc_sha = native['stages'][0]['files']['constraints.sdc']['sha256']
    row = dict(status='COMPLETE_DIAGNOSTIC_ONLY', candidate_adopted=False,timing_accepted=False,manufacturing_approval=False,
               selected_source_metrics=dict(setup_wns_ns=-4.710829,hold_wns_ns=-1.840329),
               runtime_sha256=diagnostic.common.RUNTIME_SHA256, sdc_sha256=source_sdc_sha,
               native_runs={name:{'returncode':0} for name in ('native-controls','native-diagnostic')})
    source = source_tree(tmp_path)
    row['method_files'] = diagnostic.stage_methods(source,output/'methods')
    write(output/'source-state.json',{'sdc':'@BUNDLE@/views/source.sdc'})
    write(output/'source-config.json',{'PNR_CORNERS':['fast','slow']})
    def pin(path):
        return dict(bytes=path.stat().st_size,sha256=diagnostic.common.sha(path))
    tiny = {'bytes':0,'sha256':'0'*64}
    files = {'config.json':pin(output/'source-config.json'),'state.json':pin(output/'source-state.json'),
             'source.log':tiny,'pdk/ihp-sg13g2/config.tcl':tiny,
             'views/source.sdc':pin(target/native['stages'][0]['name']/'constraints.sdc')}
    files.update({'methods/'+name:tiny for name in diagnostic.common.METHODS})
    manifest = dict(schema=1,pdk='ihp-sg13g2',pdk_root='pdk',methods_dir='methods',config='config.json',initial_state='state.json',
                    source_log='source.log',files=files,selected_source_metrics=row['selected_source_metrics'],
                    archive=dict(url='https://github.com/owner/repo/releases/download/v1/input.tar.gz',**tiny),
                    runtime=dict(url='https://github.com/librelane/librelane/releases/download/3.0.5/runtime.AppImage',
                                 bytes=diagnostic.common.RUNTIME_BYTES,sha256=diagnostic.common.RUNTIME_SHA256))
    write(output/'source-manifest.json',manifest)
    row['manifest_sha256'] = diagnostic.common.sha(output/'source-manifest.json')
    row['bundle_sha256'] = manifest['archive']['sha256']
    controls = output/'native-controls'
    control = native_control_fixture(controls,row['method_files'])
    write(controls/'result.json',control)
    row['control_output_files'] = diagnostic.file_inventory(controls)
    row['diagnostic'] = diagnostic.validate_diagnostic(target,source_sdc_sha,['fast','slow'])
    row['output_files'] = diagnostic.file_inventory(run)
    write(output/'result.json',row)
    destination = tmp_path/'capture'
    diagnostic.capture(output,destination)
    return destination


@pytest.mark.parametrize('fault',[None,'missing-table','extra-file','changed-source','truncation','claim','control-file'])
def test_final_artifact_is_verified_independently_with_complete_closure(tmp_path,fault):
    capture = complete_capture(tmp_path)
    if fault == 'missing-table': next((capture/'run').rglob('endpoints.tsv')).unlink()
    if fault == 'extra-file': (capture/'unlisted').write_text('extra')
    if fault == 'changed-source': (capture/'source-config.json').write_text('{}')
    if fault == 'truncation':
        row = json.loads((capture/'capture.json').read_text())
        row['files']['result.json']['source_truncated_during_copy'] = True
        write(capture/'capture.json',row)
    if fault == 'claim':
        row = json.loads((capture/'result.json').read_text())
        row['timing_accepted'] = True
        write(capture/'result.json',row)
    if fault == 'control-file': (capture/'native-controls/native.log').write_text('different native control')
    if fault is None:
        assert diagnostic.validate_capture(capture)['status'] == 'COMPLETE_DIAGNOSTIC_ONLY'
    else:
        with pytest.raises(ValueError): diagnostic.validate_capture(capture)


def test_full_row_census_cannot_hide_native_negative_endpoint_as_unconstrained(tmp_path):
    directory = tmp_path/'stage'
    row = stage_fixture(directory,'matched_before')
    path = directory/'hold-endpoints.tsv'
    lines = path.read_text().splitlines()
    for index,line in enumerate(lines):
        fields = line.split('\t')
        if len(fields) == 5 and fields[1] == 'a':
            lines[index] = '\t'.join(fields[:2]+['UNCONSTRAINED']*3)
    path.write_text('\n'.join(lines)+'\n')
    # Maliciously keep all row counts and native export hashes internally consistent.
    for corner in row['corners']:
        corner['constrained_endpoints'] = 1
        corner['unrepresented_endpoints'] = 2
        corner['negative_path_endpoints'] -= 1
        corner['fixed_order_tns_seconds'] = -2.5e-10 if corner['name'] == 'fast' else 0.
    write(directory/'native.json',{key:value for key,value in row.items() if key not in ('files','fingerprints')})
    repin_stage(directory,row)
    with pytest.raises(ValueError,match='global-vs-PathEnd'):
        diagnostic.validate_stage(directory,row,row['files']['constraints.sdc']['sha256'])


def test_capture_preserves_tiny_native_control_liberty_and_geometry(tmp_path):
    output = tmp_path/'output'
    write(output/'result.json',dict(status='RUNNING'))
    controls = output/'native-controls'
    controls.mkdir()
    for name in ('tiny.lib','tiny.def','tiny.odb'):
        (controls/name).write_bytes(b'tiny reproducible native fixture')
    (output/'chip.odb').write_bytes(b'not accepted checkpoint')
    row = diagnostic.capture(output,tmp_path/'snapshot')
    assert all('native-controls/'+name in row['files'] for name in ('tiny.lib','tiny.def','tiny.odb'))
    assert 'chip.odb' not in row['files']


def native_control_fixture(root,pins):
    root.mkdir()
    row = control_record(pins)
    (root/'native.log').write_text('native controls actually emitted evidence')
    stages = [stage_fixture(root/'native'/name,name,extra_corner=True)
              for name in ('original','repeat','arrivals','full_update','rerouted_mutation')]
    (root/'native/rerouted_mutation/routes.txt').write_text('deliberately changed native route')
    repin_stage(root/'native/rerouted_mutation',stages[-1])
    write(root/'native/fixture.json',dict(status='PASS_NATIVE_HOLD_FIXTURE_NATIVE_ONLY',cases=row['cases'],stages=stages))
    row['files'] = diagnostic.file_inventory(root)
    return row
