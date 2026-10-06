# SPDX-FileCopyrightText: 2026 Hasan Melih Akbulut
# SPDX-License-Identifier: Apache-2.0
"""Independent worker controls; local HTTP/gh fixtures never contact GitHub."""
import json
import os
from pathlib import Path
import signal
import struct
import subprocess
import sys
import time
import errno
import inspect

import pytest

from test_pcie_native_publisher_v4 import upload_fixture, http_fixture

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / 'scripts'))
import durable_pcie_spool_v1 as local
import publish_pcie_local_spool_v2 as m
import publish_pcie_local_spool_v1 as original_worker


def test_complete_frozen_v1_bridge_changes_only_size_guard_and_description():
    old = Path(original_worker.__file__).read_text()
    assert local.pin(original_worker.__file__)['sha256'] == '081e53f08b33b4a841754d4021272fd3c4f7bacd2e2b444c8b6e2d479c44acb9'
    expected = old.replace('import shutil\n', 'import shutil\nimport stat\n', 1)
    expected = expected.replace('Independent bounded publisher of immutable locally committed PLL parts.',
                                'Independent publisher V2 with bounded full-tree retries for moving logs.', 1)
    expected = expected.replace(inspect.getsource(original_worker.guard),
                                inspect.getsource(m.evidence_bytes) + '\n\n' + inspect.getsource(m.guard), 1)
    assert Path(m.__file__).read_text() == expected


def race_scandir(monkeypatch, directory, *, operations, error=None):
    """Trigger a real filesystem move between enumeration and entry.stat()."""
    real = m.os.scandir
    events = []

    class Entry:
        def __init__(self, entry):
            self.entry = entry
            self.path = entry.path

        def __getattr__(self, name):
            return getattr(self.entry, name)

        def stat(self, **kwargs):
            if Path(self.path).name == 'stdout.bin' and len(events) < len(operations):
                operation = operations[len(events)]
                events.append(operation)
                operation(Path(self.path))
                if error is not None:
                    raise error
            return self.entry.stat(**kwargs)

    class Scan:
        def __init__(self, path):
            self.context = real(path)

        def __enter__(self):
            self.context.__enter__()
            return self

        def __iter__(self):
            return self

        def __next__(self):
            return Entry(next(self.context))

        def __exit__(self, *args):
            return self.context.__exit__(*args)

    monkeypatch.setattr(m.os, 'scandir', Scan)
    return events


@pytest.mark.parametrize('operation', ['rename', 'compress_unlink', 'remove_subtree'])
def test_actual_transient_stat_race_restarts_whole_tree(tmp_path, monkeypatch, operation):
    import gzip
    directory = tmp_path / 'publication'; directory.mkdir()
    command = directory / 'metadata'; command.mkdir()
    moving = command / 'stdout.bin'; moving.write_bytes(b'bounded transport metadata' * 80)
    (directory / 'retained.json').write_bytes(b'keep me')

    def move(path):
        if operation == 'rename':
            path.rename(path.with_suffix('.renamed'))
        elif operation == 'compress_unlink':
            path.with_suffix('.bin.gz').write_bytes(gzip.compress(path.read_bytes()))
            path.unlink()
        else:
            path.unlink(); path.parent.rmdir()

    events = race_scandir(monkeypatch, directory, operations=[move])
    used = m.guard(directory)
    assert len(events) == 1
    expected = sum(p.stat().st_size for p in directory.rglob('*') if p.is_file())
    assert used == expected and used >= len(b'keep me')


def test_race_rescan_still_refuses_actual_sparse_overcap(tmp_path, monkeypatch):
    moving = tmp_path / 'stdout.bin'; moving.write_bytes(b'log')
    with (tmp_path / 'filled').open('wb') as stream:
        stream.truncate(m.WORKER_CAP - m.TERMINAL_HEADROOM)
    race_scandir(monkeypatch, tmp_path, operations=[lambda p: p.rename(p.with_suffix('.retained'))])
    with pytest.raises(ValueError, match='evidence byte cap'):
        m.guard(tmp_path)


@pytest.mark.parametrize('error', [PermissionError(errno.EACCES, 'fixture permission'),
                                  OSError(errno.EIO, 'fixture input output')])
def test_other_stat_errors_remain_fatal_not_zero_bytes(tmp_path, monkeypatch, error):
    (tmp_path / 'stdout.bin').write_bytes(b'log')
    events = race_scandir(monkeypatch, tmp_path, operations=[lambda p: None], error=error)
    with pytest.raises(type(error)) as found:
        m.guard(tmp_path)
    assert found.value is error and len(events) == 1


def test_repeated_stat_churn_is_bounded_and_never_passes(tmp_path, monkeypatch):
    original = m.evidence_bytes
    attempts = []

    def churn(directory):
        attempts.append(directory)
        (Path(directory) / 'stdout.bin').write_bytes(b'recreated')
        return original(directory)

    monkeypatch.setattr(m, 'evidence_bytes', churn)
    events = race_scandir(monkeypatch, tmp_path, operations=[lambda p: p.unlink()] * 8)
    with pytest.raises(FileNotFoundError):
        m.guard(tmp_path)
    assert len(attempts) == len(events) == 4


def test_symlink_cannot_hide_bytes_outside_tree(tmp_path):
    directory = tmp_path / 'publication'; directory.mkdir()
    target = tmp_path / 'outside'; target.write_bytes(b'outside')
    (directory / 'log').symlink_to(target)
    with pytest.raises(ValueError, match='only regular files'):
        m.guard(directory)


def test_recovery_reconciles_existing_uploaded_asset_without_upload(tmp_path, monkeypatch):
    spool, queue = fixture(tmp_path)
    part = next((spool.root / 'committed').glob('*/*.xz'))
    asset = dict(id=1719, name=part.name, size=part.stat().st_size,
                 digest='sha256:' + local.pin(part)['sha256'], state='uploaded', browser_download_url='unused')
    before = {str(p.relative_to(spool.root)): local.pin(p) for p in spool.root.rglob('*') if p.is_file()}
    with http_fixture(part.read_bytes(), [{}]) as (url, calls):
        asset['browser_download_url'] = url
        state = upload_fixture(tmp_path, monkeypatch, part, asset, ['success'])
        prior = json.loads(state.read_text())
        prior['assets'] = [asset]
        state.write_text(json.dumps(prior))
        recovery = m.run(spool.root, tmp_path / 'recovery', local.pin(spool.root / 'configuration.json')['sha256'])
        assert recovery['status'] == 'PASS_ALL_COMPLETE_LOCAL_PARTS_PUBLIC'
        assert json.loads(state.read_text())['uploads'] == 0
        assert len(calls) == 1
    assert before == {str(p.relative_to(spool.root)): local.pin(p) for p in spool.root.rglob('*') if p.is_file()}


def fixture(tmp_path, *, complete=True):
    spool = local.Spool(tmp_path / 'ssd', 'independent-worker-fixture',
                        limits=local.Limits(reserve=4096, payload=1024**2, floor=4096, parts=16))
    spool.metadata('header.bin', b'header\n')
    queue = local.PartQueue(tmp_path / 'ram', spool.prefix, ['time', 'v(x)'],
                           spool, 3, True, 512 * 1024**2)
    if complete:
        finish(spool, queue)
    return spool, queue


def finish(spool, queue):
    for i in range(3):
        queue.append(struct.pack('<dd', i * 1.25e-12, .5))
    spool.metadata('trailer.bin', b'3')
    queue.finish()
    spool.terminal(dict(status='TEST_NATIVE_TERMINAL', returncode=0))


def publish_fixture(path, receipt, directory, *, error=None, fault=None):
    expected = local.pin(path)
    record = dict(status='PASS_IMMUTABLE_RELEASE_ROUNDTRIPS', explicit_stop=False,
                  files=[dict(path=str(path.resolve()), name=path.name, **expected)],
                  assets=[dict(name=path.name, asset_id=17, url='local-unit-only', **expected,
                               authenticated_roundtrip=True, anonymous_roundtrip=True)])
    if error:
        record.update(status='FAIL', error=error)
    if fault == 'source':
        path.write_bytes(b'corrupt')
    elif fault == 'roundtrip':
        record['assets'][0]['anonymous_roundtrip'] = False
    elif fault == 'declaredfile':
        record['files'][0]['path'] = 'different'
    elif fault == 'metadata':
        record['assets'][0]['sha256'] = '0' * 64
    receipt.write_bytes(local.encoded(record))
    return record


def test_worker_transient_then_success_retains_every_byte(tmp_path):
    spool, queue = fixture(tmp_path)
    before = {str(p.relative_to(spool.root)): local.pin(p) for p in spool.root.rglob('*') if p.is_file()}
    calls = []
    def publish(path, receipt, directory):
        calls.append(path)
        return publish_fixture(path, receipt, directory, error="TransportError('offline')" if len(calls) == 1 else None)
    result = m.run(spool.root, tmp_path / 'publication', local.pin(spool.root / 'configuration.json')['sha256'],
                   publish=publish, poll_seconds=.001, retry_seconds=.001)
    assert result['status'] == 'PASS_ALL_COMPLETE_LOCAL_PARTS_PUBLIC'
    assert [x['status'] for x in result['attempts']] == ['TRANSPORT_PENDING_LOCAL_BYTES_RETAINED', 'PUBLIC_VERIFIED']
    assert len(calls) == 2
    assert before == {str(p.relative_to(spool.root)): local.pin(p) for p in spool.root.rglob('*') if p.is_file()}


@pytest.mark.parametrize('error', ["IntegrityError('bad byte')", "RuntimeError('HTTP 401')",
                                  "ValueError('duplicate')", "TransportError(__import__('os'))",
                                  "Some.TransportError('offline')"])
def test_nontransport_or_ambiguous_error_no_retry(tmp_path, error):
    spool, queue = fixture(tmp_path)
    calls = []
    def publish(path, receipt, directory):
        calls.append(path)
        return publish_fixture(path, receipt, directory, error=error)
    with pytest.raises(ValueError, match='Non-transport'):
        m.run(spool.root, tmp_path / 'publication', local.pin(spool.root / 'configuration.json')['sha256'], publish=publish)
    assert len(calls) == 1 and local.inspect_spool(spool.root, raw=True)['rows'] == 3


@pytest.mark.parametrize('fault', ['source', 'roundtrip', 'declaredfile', 'metadata'])
def test_real_modified_part_or_success_receipt_rejected(tmp_path, fault):
    spool, queue = fixture(tmp_path)
    calls = []
    def publish(path, receipt, directory):
        calls.append(path)
        return publish_fixture(path, receipt, directory, fault=fault)
    with pytest.raises(ValueError):
        m.run(spool.root, tmp_path / 'publication', local.pin(spool.root / 'configuration.json')['sha256'], publish=publish)
    assert len(calls) == 1 and len(list((spool.root / 'committed').glob('*/*.xz'))) == 1


def test_finite_offline_budget_does_not_mutate_native_capture(tmp_path):
    spool, queue = fixture(tmp_path)
    expected = local.pin(spool.root / 'native-terminal.json')
    def publish(path, receipt, directory):
        return publish_fixture(path, receipt, directory, error="TransportError('offline')")
    with pytest.raises(ValueError, match='Finite publication attempt'):
        m.run(spool.root, tmp_path / 'publication', local.pin(spool.root / 'configuration.json')['sha256'],
              publish=publish, retry_seconds=.001, max_receipts=2)
    result = json.loads((tmp_path / 'publication/publication.json').read_text())
    assert len(result['attempts']) == 2
    assert local.pin(spool.root / 'native-terminal.json') == expected


def test_configuration_pin_refuses_any_publication(tmp_path):
    spool, queue = fixture(tmp_path)
    with pytest.raises(ValueError, match='Externally bound'):
        m.run(spool.root, tmp_path / 'publication', '0' * 64,
              publish=lambda *a: pytest.fail('No publication before source gate'))
    assert not (tmp_path / 'publication').exists()


@pytest.mark.parametrize('resource', ['operative_budget', 'shared_floor'])
def test_terminal_error_record_survives_operative_resource_guard(tmp_path, monkeypatch, resource):
    spool, queue = fixture(tmp_path)
    original = m.guard
    injected = []
    usage = m.shutil.disk_usage(tmp_path)
    if resource == 'shared_floor':
        monkeypatch.setattr(m.shutil, 'disk_usage', lambda path: usage._replace(free=m.SSD_FLOOR - 1))
    def guard(directory, *, extra=0, terminal=False):
        if resource == 'operative_budget' and not injected:
            injected.append(resource)
            with (Path(directory) / 'actual-near-cap').open('wb') as stream:
                stream.truncate(m.WORKER_CAP - m.TERMINAL_HEADROOM + 1)
        return original(directory, extra=extra, terminal=terminal)
    monkeypatch.setattr(m, 'guard', guard)
    with pytest.raises(ValueError, match='Publication (evidence byte cap|SSD free floor)'):
        m.run(spool.root, tmp_path / 'publication', local.pin(spool.root / 'configuration.json')['sha256'],
              publish=lambda *a: pytest.fail('No transfer after resource refusal'))
    receipt = json.loads((tmp_path / 'publication/publication.json').read_text())
    assert receipt['status'] == 'ERROR_INDEPENDENT_PUBLICATION_LOCAL_SOURCE_RETAINED'
    expected = 'evidence byte cap' if resource == 'operative_budget' else 'SSD free floor'
    assert expected in receipt['error'] and receipt['attempts'] == []


def test_actual_sparse_near_cap_and_terminal_reserved_headroom(tmp_path):
    directory = tmp_path / 'evidence'; directory.mkdir()
    with (directory / 'filled').open('wb') as stream:
        stream.truncate(m.WORKER_CAP - m.TERMINAL_HEADROOM + 1)
    with pytest.raises(ValueError, match='evidence byte cap'):
        m.guard(directory)
    assert m.guard(directory, extra=1024, terminal=True) < m.WORKER_CAP
    with pytest.raises(ValueError, match='evidence byte cap'):
        m.guard(directory, extra=m.TERMINAL_HEADROOM, terminal=True)


def wait_until(predicate, process, log, seconds=12):
    deadline = time.monotonic() + seconds
    while time.monotonic() < deadline:
        if predicate():
            return
        if process.poll() is not None:
            pytest.fail(Path(log).read_text())
        time.sleep(.01)
    process.kill()
    process.wait()
    pytest.fail('Bounded actual fixture did not reach intended boundary')


@pytest.mark.parametrize('phase', ['upload', 'backoff'])
def test_actual_offline_worker_stop_leaves_native_complete_then_late_recovery(tmp_path, monkeypatch, phase):
    spool, queue = fixture(tmp_path, complete=False)
    # Freeze the expected compression before producer writes it, solely for the
    # fake local gh server; the actual worker still consumes committed bytes.
    import lzma
    payload = b''.join(struct.pack('<dd', i * 1.25e-12, .5) for i in range(3))
    source = tmp_path / 'fixture-source.xz'; source.write_bytes(lzma.compress(payload, preset=1))
    asset = dict(id=1717, name=spool.prefix + '-part00000.bin.xz', size=source.stat().st_size,
                 digest='sha256:' + local.pin(source)['sha256'], state='uploaded', browser_download_url='unused')
    with http_fixture(source.read_bytes(), [{}]) as (url, http_calls):
        asset['browser_download_url'] = url
        state = upload_fixture(tmp_path, monkeypatch, source, asset,
                               ['timeout_absent' if phase == 'upload' else 'transient_absent'])
        out = tmp_path / 'publication'
        command = [sys.executable, str(ROOT / 'scripts/publish_pcie_local_spool_v2.py'),
                   '--spool', str(spool.root), '--out', str(out), '--configuration-sha',
                   local.pin(spool.root / 'configuration.json')['sha256']]
        logfile = tmp_path / 'worker.log'
        with logfile.open('wb') as log:
            worker = subprocess.Popen(command, stdin=subprocess.DEVNULL, stdout=log, stderr=subprocess.STDOUT,
                                      start_new_session=True, close_fds=True)
            wait_until(lambda: (out / 'publication.json').exists(), worker, logfile)
            finish(spool, queue)
            native_pin = local.pin(spool.root / 'native-terminal.json')
            if phase == 'upload':
                wait_until(lambda: json.loads(state.read_text())['uploads'] == 1, worker, logfile)
            else:
                def pending():
                    record = json.loads((out / 'publication.json').read_text())
                    return record['attempts'] and record['attempts'][0]['status'] == 'TRANSPORT_PENDING_LOCAL_BYTES_RETAINED'
                wait_until(pending, worker, logfile, 15)
            started = time.monotonic(); worker.send_signal(signal.SIGTERM)
            assert worker.wait(timeout=8) != 0 and time.monotonic() - started < 6
        result = json.loads((out / 'publication.json').read_text())
        assert result['explicit_stop'] and result['status'] == 'ERROR_INDEPENDENT_PUBLICATION_LOCAL_SOURCE_RETAINED'
        assert local.pin(spool.root / 'native-terminal.json') == native_pin
        assert local.inspect_spool(spool.root, raw=True)['ledger']['status'] == 'LOCAL_CAPTURE_COMPLETE'
        for owner_path in out.rglob('*owner*.json'):
            owner = json.loads(owner_path.read_text())
            if 'processes' in owner:
                for process in owner['processes']:
                    assert not any(x['state'] != 'Z' for x in m.life.group_members(process['process_group']))
        # Restore connectivity and use a fresh independent worker. It reuses
        # exactly the retained source; no native run or capture append occurs.
        config = tmp_path / 'upload-config.json'
        updated = json.loads(config.read_text()); updated['modes'] = ['success']
        config.write_text(json.dumps(updated))
        recovery = m.run(spool.root, tmp_path / 'recovered-publication',
                         local.pin(spool.root / 'configuration.json')['sha256'])
        assert recovery['status'] == 'PASS_ALL_COMPLETE_LOCAL_PARTS_PUBLIC'
        assert len(http_calls) == 1
        assert local.pin(spool.root / 'native-terminal.json') == native_pin
        assert recovery['assets'][0]['asset']['authenticated_roundtrip']
        assert recovery['assets'][0]['asset']['anonymous_roundtrip']


@pytest.mark.parametrize('boundary', ['before_inner_enter', 'after_inner_exit'])
def test_actual_signal_at_owner_handoff_prevents_late_transfer(tmp_path, monkeypatch, boundary):
    spool, queue = fixture(tmp_path)
    part = next((spool.root / 'committed').glob('*/*.xz'))
    asset = dict(id=1718, name=part.name, size=part.stat().st_size,
                 digest='sha256:' + local.pin(part)['sha256'], state='uploaded', browser_download_url='unused')
    original_enter, original_exit = m.life.ProcessOwner.__enter__, m.life.ProcessOwner.__exit__
    injected = []
    def enter(owner):
        if boundary == 'before_inner_enter' and not injected:
            injected.append(boundary); os.kill(os.getpid(), signal.SIGTERM)
        return original_enter(owner)
    def leave(owner, *args):
        result = original_exit(owner, *args)
        if boundary == 'after_inner_exit' and not injected:
            injected.append(boundary); os.kill(os.getpid(), signal.SIGTERM)
        return result
    monkeypatch.setattr(m.life.ProcessOwner, '__enter__', enter)
    monkeypatch.setattr(m.life.ProcessOwner, '__exit__', leave)
    with http_fixture(part.read_bytes(), [{}]) as (url, calls):
        asset['browser_download_url'] = url
        state = upload_fixture(tmp_path, monkeypatch, part, asset, ['success'])
        with pytest.raises(m.life.Cancelled, match='owner handoff'):
            m.run(spool.root, tmp_path / 'publication', local.pin(spool.root / 'configuration.json')['sha256'])
        outcome = json.loads((tmp_path / 'publication/publication.json').read_text())
        owner = json.loads(next((tmp_path / 'publication').glob('*.owner.json')).read_text())
        assert outcome['explicit_stop'] and len(outcome['attempts']) == 1 and outcome['assets'] == []
        assert len(owner['processes']) == (0 if boundary == 'before_inner_enter' else 1)
        assert json.loads(state.read_text())['uploads'] == (0 if boundary == 'before_inner_enter' else 1)
        assert len(calls) == (0 if boundary == 'before_inner_enter' else 1)
        for process in owner['processes']:
            assert not any(x['state'] != 'Z' for x in m.life.group_members(process['process_group']))


@pytest.mark.parametrize('ledger', ['absent', 'invalid'])
def test_invalid_native_terminal_stops_worker_before_wait_or_transfer(tmp_path, ledger):
    spool = local.Spool(tmp_path / 'ssd', 'invalid-native-terminal-fixture',
                        limits=local.Limits(reserve=4096, payload=1024**2, floor=4096, parts=16))
    if ledger == 'invalid':
        (spool.root / 'parts.json').write_bytes(b'{invalid ledger')
    native = tmp_path / 'native'; native.mkdir()
    original = dict(status='ERROR_NATIVE_OR_STREAM_CAPTURE', error='actual fixture preheader failure')
    (native / 'result.json').write_bytes(local.encoded(original))
    (native / 'run.log').write_bytes(b'preserved original native failure')
    with pytest.raises((FileNotFoundError, json.JSONDecodeError)):
        spool.terminal(original, native_root=native)
    before = {str(p.relative_to(spool.root)): local.pin(p) for p in spool.root.rglob('*') if p.is_file()}
    with pytest.raises(ValueError, match='Native terminal local manifest or retention failed'):
        m.run(spool.root, tmp_path / 'publication', local.pin(spool.root / 'configuration.json')['sha256'],
              publish=lambda *a: pytest.fail('No transfer of invalid terminal stream'))
    outcome = json.loads((tmp_path / 'publication/publication.json').read_text())
    assert outcome['status'] == 'ERROR_INDEPENDENT_PUBLICATION_LOCAL_SOURCE_RETAINED'
    assert outcome['attempts'] == [] and outcome['assets'] == []
    assert outcome['native_terminal_failure']['sha256'] == local.pin(spool.root / 'native-terminal-invalid.json')['sha256']
    assert before == {str(p.relative_to(spool.root)): local.pin(p) for p in spool.root.rglob('*') if p.is_file()}
