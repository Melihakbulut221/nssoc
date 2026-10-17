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

import pytest

from test_pcie_native_publisher_v4 import upload_fixture, http_fixture

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / 'scripts'))
import durable_pcie_spool_v1 as local
import publish_pcie_local_spool_v1 as m


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
        command = [sys.executable, str(ROOT / 'scripts/publish_pcie_local_spool_v1.py'),
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
