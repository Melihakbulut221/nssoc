# SPDX-FileCopyrightText: 2026 Hasan Melih Akbulut
# SPDX-License-Identifier: Apache-2.0
"""Independent saved-source review; no production method or native execution."""
import ast
import hashlib
import json
import os
from pathlib import Path

C = Path(__file__).resolve().parent
B = C.parent
P = B / 'repair13-peer'


def pin(path):
    path = Path(path)
    with path.open('rb') as f:
        return {'bytes': path.stat().st_size, 'sha256': hashlib.file_digest(f, 'sha256').hexdigest()}


def j(path):
    return json.loads(Path(path).read_text())


def check_pin(row):
    assert pin(row['path']) == {k: row[k] for k in ('bytes', 'sha256')}


manifest = j(C / 'manifest.json')
assert len(manifest['inputs']) == 21
assert manifest['inputs'] == {p: pin(p) for p in manifest['inputs']}
assert manifest['route_inputs'] == {p: pin(p) for p in manifest['route_inputs']}
assert manifest['boot_id'] == Path('/proc/sys/kernel/random/boot_id').read_text().strip()
assert manifest['cpu'] == 8 and manifest['AS_bytes'] == int(2.5 * 1024**3)
assert manifest['scratch_entry_bytes'] == 1024**3
assert manifest['scratch_continuous_floor_bytes'] == 528 * 1024**2
assert manifest['outer_failure_grace_seconds'] == 15 > manifest['inner_RC_failure_grace_seconds'] == 5
assert manifest['healthy_elapsed_watchdog_seconds'] is None
assert manifest['no_existing_DRT_ownership_or_signals'] is True
assert manifest['stages'][2] == 'frozen independent saved-output review vs published RX12'
before_label = j(C / 'manifest-before-peer-label01.json')
assert before_label['stages'][2] == 'frozen independent saved-output review vs published RX11'
before_label['stages'][2] = manifest['stages'][2]
assert before_label == manifest

freeze = j(P / 'source-freeze.json')
assert freeze == {p: pin(p) for p in freeze}
bridges = j(P / 'source-bridge.json') + [j(C / 'source-bridge.json')]
assert len(bridges) == 3
checked = []
for bridge in bridges:
    check_pin(bridge['before'])
    check_pin(bridge['after'])
    old = Path(bridge['before']['path']).read_text()
    new = Path(bridge['after']['path']).read_text()
    assert ''.join(o['before'] for o in bridge['opcodes']) == old
    assert ''.join(o['after'] for o in bridge['opcodes']) == new
    assert all(o['before'] == o['after'] for o in bridge['opcodes'] if o['tag'] == 'equal')
    predicted = old.replace('repair12', 'repair13').replace('repair-12', 'repair-13').replace('RX12', 'RX13').replace('rx12', 'rx13')
    name = Path(bridge['after']['path']).name
    if name == 'review.py':
        predicted = predicted.replace('repair11-peer02', 'repair12-peer').replace('SS_setup_improvement_vs11_ns', 'SS_setup_improvement_vs12_ns')
    elif name == 'seal.py':
        predicted = predicted.replace('SS_setup_improvement_vs_published11_ns', 'SS_setup_improvement_vs_published12_ns').replace('SS_setup_improvement_vs11_ns', 'SS_setup_improvement_vs12_ns')
        predicted = predicted.replace('pcie-rx-repair11-finite-physical-validation', 'pcie-rx-repair12-finite-physical-validation').replace('prior-published/repair11/', 'prior-published/repair12/').replace('repair11-peer02', 'repair12-peer').replace('Earlier routed11 inputs', 'Earlier routed12 inputs')
    elif name == 'run.py':
        predicted = predicted.replace('WAITING_EXISTING_EXACT_RX13_DRT02', 'WAITING_EXISTING_EXACT_RX13_DRT01')
        needle = "    require(sorted(os.sched_getaffinity(0)) == [8], 'Controller CPU8')\n"
        predicted = predicted.replace(needle, needle + "    require(Path('/proc/sys/kernel/random/boot_id').read_text().strip() == manifest['boot_id'], 'Same recorded boot identity')\n")
        needle = "                    stage['returncode'] = owner.complete(process)\n"
        predicted = predicted.replace(needle, needle + "                    owner.check()\n                    require(shutil.disk_usage('/dev/shm').free >= FLOOR,\n                            '528MiB terminal scratch floor')\n")
        needle = '    return 0\n'
        predicted = predicted.replace(needle, "    # A stop delivered during final complete/save/context teardown must propagate.\n    try:\n        owner.check()\n    except BaseException as error:\n        record.update(status='FAILED_RETAINED_NO_DEPENDENT_BYPASS', error=repr(error))\n        save()\n        raise\n" + needle)
    else:
        raise AssertionError(name)
    assert predicted == new, name
    # Reverse the exact full bridge independently of the derivation method.
    reconstructed = ''.join(o['before'] for o in bridge['opcodes'])
    assert reconstructed.encode() == Path(bridge['before']['path']).read_bytes()
    ast.parse(new)
    checked.append({'before': bridge['before'], 'after': bridge['after'],
                    'full_bidirectional_bridge_and_independent_transform': True})

run = (C / 'run.py').read_text()
review = (P / 'review.py').read_text()
seal = (P / 'seal.py').read_text()
tree = ast.parse(seal)
roots = ast.literal_eval(next(n.value for n in tree.body if isinstance(n, ast.Assign) and any(isinstance(t, ast.Name) and t.id == 'roots' for t in n.targets)))
assert roots == ['/dev/shm/nssoc-rx-prefetch-v2-postroute-repair-13', '/dev/shm/nssoc-rx-prefetch-v2-repair13-equivalence', '/dev/shm/nssoc-rx-prefetch-v2-repair13-physical-replay-01', '/dev/shm/nssoc-rx-prefetch-v2-repair13-drt-01', '/dev/shm/nssoc-rx-prefetch-v2-repair13-detailed-rc-01']
assert "assert directory.is_dir()" in seal
assert "assert actual == members" in seal
assert "assert members == {n: pin(p) for n, p in files.items()}" in seal
assert "originalgold expansion reused exactly from completedRX11" in seal
assert "old = B / 'repair12-peer/review.json'" in review
assert 'record.update(status=\'COMPLETE_RX13_FINITE_ROUTE_RC_REVIEW_PUBLICATION\'' in run
assert "and len(public['assets']) == 3" in run

controls = j(C / 'lifecycle-controls.json')
assert controls['status'] == 'PASS_THREE_ACTUAL_RX13_CONTINUATION_BOUNDARY_CONTROLS'
assert controls['source'] == pin(C / 'run.py')
assert controls['method'] == pin(C / 'check_lifecycle_boundaries.py')
assert controls['exact_production_stage_ast'] and controls['exact_production_post_context_try_ast']
assert [x['mode'] for x in controls['results']] == ['complete_signal', 'teardown_signal', 'stage_failure']
saved_control_files = {}
for row in controls['results']:
    directory = C / 'lifecycle-controls' / row['mode']
    assert j(directory / 'result.json') == row
    owner = j(directory / 'owner.json')
    assert owner['failure_grace_seconds'] == 15 and owner['elapsed_watchdog_seconds'] is None
    assert len(owner['processes']) == 1
    assert owner['processes'][0]['status'] == 'REAPED_NO_LIVE_MEMBERS'
    assert owner['processes'][0]['identity'] == row['record']['stages'][0]['identity']
    assert not row['remaining_members'] and row['terminal_guard_or_error_seen']
    if row['mode'] == 'teardown_signal':
        assert owner['status'] == 'HEALTHY' and owner['reason'] is None
        assert row['record']['status'] == 'FAILED_RETAINED_NO_DEPENDENT_BYPASS'
    else:
        assert owner['status'] == 'CANCELLED'
    for path in directory.iterdir():
        if path.is_file():
            saved_control_files[str(path)] = pin(path)
assert len(saved_control_files) == 9

observations = {}
for key in ('route_owner', 'route_native'):
    expected = manifest[key]
    proc = Path('/proc') / str(expected['pid'])
    if proc.exists():
        stat = (proc / 'stat').read_text().split(') ', 1)[1].split()
        assert stat[19] == str(expected['start_ticks'])
        assert sorted(os.sched_getaffinity(expected['pid'])) == [8]
        observations[key] = {'pid': expected['pid'], 'start_ticks': stat[19], 'state': stat[0], 'affinity': [8]}
    else:
        observations[key] = {'pid': expected['pid'], 'absent_at_readonly_observation': True}
live = j(Path(roots[3]) / 'result.json')
assert live['pid'] == manifest['route_native']['pid']
assert live['inputs'] == manifest['route_inputs']
record = {
    'status': 'PASS_SOURCE_ONLY_RX13_DURABLE_CONTINUATION', 'findings': [],
    'method': pin(__file__), 'manifest': pin(C / 'manifest.json'),
    'prior_manifest_label_preserved': pin(C / 'manifest-before-peer-label01.json'),
    'inputs_rehashed': manifest['inputs'], 'route_inputs_rehashed': len(manifest['route_inputs']),
    'source_bridges': checked, 'mandatory_native_roots': roots,
    'saved_boundary_controls': {'receipt': pin(C / 'lifecycle-controls.json'), 'method': controls['method'], 'raw_files': saved_control_files,
                                'observed_not_rerun': True,
                                'teardown_owner_last_saved_HEALTHY_limitation': 'The inner last owner receipt predates the delivered teardown signal; the exact production outer guard records FAILED_RETAINED and propagates Cancelled. No next stage can run.'},
    'route_readonly_observation': observations, 'route_status_at_review': live['status'],
    'review': [
        'Complete three source bridges reconstruct every before/after byte; independent narrow transforms yield exactly reviewed new sources. Correct new RX13 candidate/DRT01/RC01/proof/port paths throughout, prior timing comparison and published preservation RX12, original gold RX11 deliberately retained.',
        'Strict successful DRT receipt, zero router DRC, all frozen route input/output hashes and byte-identical proved candidate netlist precede fresh RC. The existing route owner/native are observed by birth identity and boot, never registered for signalling by this watcher.',
        'Frozen original ProcessOwner definitions selected by AST and exact source pin; CPU8, 2.5 GiB stage AS, 1 GiB entry and 528 MiB continuous/terminal floors. No healthy elapsed watchdog; own-stage failure grace 15 seconds permits inner RC 5-second cleanup. Explicit cancellation checked after completion and after context teardown.',
        'Actual saved three lifecycle controls use exact production stage and outer-tail AST, real child processes and completion/teardown SIGTERM or nonzero exit. Their saved outputs and nine raw files rehashed; no control/native rerun by reviewer.',
        'Saved native review rehashes DRT/RC inputs and outputs, scans all SPEF numeric values and 78 input-only CTS load connections, retained full graphs/proof binding/native program gzip and six port XML cases. Unchanged 4 ns constraints are compared exactly; negative timing remains a recorded FAIL and may still be preserved.',
        'Sealer requires all five native roots, all members before/after and streamed full archive readback, graph/program gzip checks, prior public RX12 bindings and unchanged source licences. Publication requires all three uniquely named immutable assets and authenticated/anonymous roundtrips through frozen publisher V3.'
    ],
    'limitations': ['Source-only prelaunch review, not completed route/RC evidence or timing acceptance.',
                    'No reviewed production method, simulation, extraction, route, proof, control or publication executed. Existing route observed only; no signal sent.',
                    'Nominal unqualified RC, full-chip foundry DRC/PDN and full PCIe PHY acceptance remain outside scope.']
}
out = C / 'source-only-peer-vco.json'
assert not out.exists()
out.write_text(json.dumps(record, indent=2) + '\n')
print(json.dumps({'path': str(out), **pin(out), 'status': record['status']}))
