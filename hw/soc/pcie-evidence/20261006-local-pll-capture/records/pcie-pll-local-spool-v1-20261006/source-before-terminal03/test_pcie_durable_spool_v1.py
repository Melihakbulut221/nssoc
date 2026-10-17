# SPDX-FileCopyrightText: 2026 Hasan Melih Akbulut
# SPDX-License-Identifier: Apache-2.0
"""Actual local file/byte/crash-boundary controls; no native or network calls."""
import hashlib
import json
import lzma
from pathlib import Path
import struct
import sys

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / 'scripts'))
import durable_pcie_spool_v1 as m


def make(tmp_path, monkeypatch=None, **limits):
    selected = dict(reserve=4096, payload=1024**2, floor=4096, parts=16)
    selected.update(limits)
    spool = m.Spool(tmp_path / 'ssd', 'spool-test-unique', limits=m.Limits(
        **selected))
    spool.metadata('header.bin', b'actual-header\n')
    queue = m.PartQueue(tmp_path / 'ram', spool.prefix, ['time', 'v(test)'],
                        spool, 3, True, 512 * 1024**2)
    return spool, queue


def samples(count=8):
    return [struct.pack('<dd', i / 10, (-1)**i * 1.25) for i in range(count)]


def finish(spool, queue, rows=8):
    for sample in samples(rows):
        queue.append(sample)
    spool.metadata('trailer.bin', str(rows).encode())
    return queue.finish()


def test_real_lossless_parts_and_terminal_reservation(tmp_path):
    spool, queue = make(tmp_path)
    assert (spool.root / 'reservation.bin').stat().st_blocks * 512 >= 4096
    ledger = finish(spool, queue)
    assert ledger['status'] == 'LOCAL_CAPTURE_COMPLETE'
    assert ledger['public_verified'] is False
    assert [p['rows'] for p in ledger['parts']] == [3, 3, 2]
    combined = b''.join(m.check_row(spool.root, ledger, p, i, p['first_row'], raw=True)
                        for i, p in enumerate(ledger['parts']))
    assert combined == b''.join(samples())
    assert hashlib.sha256(combined).hexdigest() == ledger['payload_sha256']
    assert json.loads((queue.root / 'parts.json').read_text()) == ledger
    native = dict(status='TEST_NATIVE_TERMINAL', returncode=0)
    terminal = spool.terminal(native)
    assert terminal['result'] == native and not terminal['public_verified']
    assert not (spool.root / 'reservation.bin').exists()
    assert len(list((spool.root / 'committed').iterdir())) == 3
    spool.close()


def test_no_network_or_reclaim_after_completed_parts(tmp_path, monkeypatch):
    import socket
    monkeypatch.setattr(socket, 'socket', lambda *a, **k: pytest.fail('Network in producer'))
    spool, queue = make(tmp_path)
    finish(spool, queue)
    assert len(list((spool.root / 'committed').glob('*/*.xz'))) == 3
    assert not list(spool.root.glob('*publication*'))


def test_duplicate_spool_never_replaces(tmp_path):
    spool, queue = make(tmp_path)
    original = m.pin(spool.root / 'configuration.json')
    with pytest.raises(FileExistsError):
        m.Spool(spool.root, spool.prefix, limits=spool.limits)
    assert m.pin(spool.root / 'configuration.json') == original


@pytest.mark.parametrize('kind', ['part', 'row', 'order', 'trailer', 'rawhash'])
def test_actual_corruption_rejected_retained(tmp_path, kind):
    spool, queue = make(tmp_path)
    ledger = finish(spool, queue)
    row = ledger['parts'][0]
    directory = spool.root / 'committed/00000'
    if kind == 'part':
        path = directory / row['name']
        path.write_bytes(path.read_bytes() + b'corrupt')
    elif kind == 'row':
        path = directory / 'record.json'
        altered = dict(row, first_row=1)
        path.write_bytes(m.encoded(altered))
    elif kind == 'order':
        ledger['parts'][0]['index'] = 1
        (spool.root / 'parts.json').write_bytes(m.encoded(ledger))
    elif kind == 'trailer':
        (spool.root / 'trailer.bin').write_bytes(b'7')
    else:
        ledger['payload_sha256'] = '0' * 64
        (spool.root / 'parts.json').write_bytes(m.encoded(ledger))
    with pytest.raises(ValueError):
        m.inspect_spool(spool.root, raw=True)
    assert (spool.root / 'reservation.bin').exists()
    assert len(list((spool.root / 'committed').glob('*/*.xz'))) == 3


@pytest.mark.parametrize('boundary', ['data_write', 'record_write', 'data_fsync',
                                     'rename', 'committed_dir_fsync', 'ledger_write',
                                     'ledger_replace', 'mirror_write'])
def test_actual_failed_commit_boundary_retains_bytes(tmp_path, monkeypatch, boundary):
    spool, queue = make(tmp_path)
    old_write, old_rename, old_fsync = m.fresh_bytes, m.os.rename, m.fsync_dir
    old_replace = m.os.replace

    def write(path, data):
        path = Path(path)
        selected = ((boundary == 'data_write' and path.suffix == '.xz')
                    or (boundary == 'record_write' and path.name == 'record.json')
                    or (boundary == 'ledger_write' and path == spool.root / 'parts.json.pending')
                    or (boundary == 'mirror_write' and path == queue.root / 'parts.json.pending'))
        if selected:
            old_write(path, data[:max(1, len(data) // 2)])
            raise OSError('Actual retained injected partial write')
        return old_write(path, data)

    def rename(source, destination):
        if boundary == 'rename':
            raise OSError('Before commit directory rename')
        return old_rename(source, destination)

    def sync(path):
        path = Path(path)
        if ((boundary == 'data_fsync' and path.parent.name == 'staging')
                or (boundary == 'committed_dir_fsync' and path.name == 'committed')):
            raise OSError('Actual directory fsync failure')
        return old_fsync(path)

    def replace(source, destination):
        if boundary == 'ledger_replace' and Path(destination) == spool.root / 'parts.json':
            raise OSError('Before canonical ledger replacement')
        return old_replace(source, destination)

    monkeypatch.setattr(m, 'fresh_bytes', write)
    monkeypatch.setattr(m.os, 'rename', rename)
    monkeypatch.setattr(m, 'fsync_dir', sync)
    monkeypatch.setattr(m.os, 'replace', replace)
    with pytest.raises(OSError):
        for sample in samples(3):
            queue.append(sample)
    assert bytes(queue.pending) == b''.join(samples(3))
    observed = m.inspect_spool(spool.root, raw=True)
    assert observed['ledger']['status'] == 'CAPTURING_LOCAL'
    if boundary == 'mirror_write':
        assert observed['rows'] == 3 and not observed['committed_orphans']
    elif boundary in ('committed_dir_fsync', 'ledger_write', 'ledger_replace'):
        assert observed['rows'] == 0 and observed['committed_orphans'] == ['00000']
    else:
        assert observed['rows'] == 0 and observed['staging'] == ['00000']
    assert (spool.root / 'reservation.bin').exists()


def test_real_short_os_write_completes_exact_bytes(tmp_path, monkeypatch):
    original = m.os.write
    monkeypatch.setattr(m.os, 'write', lambda fd, data: original(fd, data[:3]))
    path = tmp_path / 'bytes'
    m.fresh_bytes(path, b'1234567890abcdef')
    assert path.read_bytes() == b'1234567890abcdef'


def test_zero_write_fails_with_prefix_retained(tmp_path, monkeypatch):
    original = m.os.write
    calls = []
    def partial(fd, data):
        calls.append(len(data))
        return original(fd, data[:3]) if len(calls) == 1 else 0
    monkeypatch.setattr(m.os, 'write', partial)
    path = tmp_path / 'bytes'
    with pytest.raises(ValueError, match='Incomplete durable write'):
        m.fresh_bytes(path, b'123456789')
    assert path.read_bytes() == b'123'


def test_floor_and_cap_prevent_commit(tmp_path, monkeypatch):
    spool, queue = make(tmp_path)
    usage = m.shutil.disk_usage(spool.root)
    monkeypatch.setattr(m.shutil, 'disk_usage', lambda path: usage._replace(free=0))
    with pytest.raises(ValueError, match='free floor'):
        for sample in samples(3):
            queue.append(sample)
    assert bytes(queue.pending) == b''.join(samples(3))
    assert not list((spool.root / 'committed').iterdir())
    monkeypatch.undo()
    m.fresh_bytes(spool.root / 'fill', b'X' * spool.limits.payload)
    with pytest.raises(ValueError, match='payload and metadata cap'):
        queue.flush()


def test_part_count_cap_and_duplicate_name(tmp_path):
    spool, queue = make(tmp_path, parts=1)
    for sample in samples(3):
        queue.append(sample)
    with pytest.raises(ValueError, match='part count cap'):
        for sample in samples(3):
            queue.append(sample)
    assert m.inspect_spool(spool.root)['rows'] == 3


def test_existing_committed_directory_rejected(tmp_path):
    spool, queue = make(tmp_path)
    (spool.root / 'committed/00000').mkdir()
    with pytest.raises(ValueError, match='Never replace committed part'):
        for sample in samples(3):
            queue.append(sample)
    assert m.inspect_spool(spool.root)['committed_orphans'] == ['00000']


def test_wrong_trailer_prevents_complete_status(tmp_path):
    spool, queue = make(tmp_path)
    for sample in samples(3):
        queue.append(sample)
    spool.metadata('trailer.bin', b'4')
    with pytest.raises(ValueError, match='native count trailer'):
        queue.finish()
    assert m.inspect_spool(spool.root)['ledger']['status'] == 'CAPTURING_LOCAL'


def test_no_partial_row_or_duplicate_metadata(tmp_path):
    spool, queue = make(tmp_path)
    with pytest.raises(ValueError, match='Complete native frame'):
        queue.append(b'partial')
    with pytest.raises(FileExistsError):
        spool.metadata('header.bin', b'replacement')
    assert (spool.root / 'header.bin').read_bytes() == b'actual-header\n'


def test_raw_corruption_even_if_compressed_metadata_redefined(tmp_path):
    spool, queue = make(tmp_path)
    ledger = finish(spool, queue)
    row = ledger['parts'][0]
    path = spool.root / 'committed/00000' / row['name']
    path.write_bytes(lzma.compress(b'X' * row['uncompressed_bytes'], preset=1))
    row.update(m.pin(path))
    (path.parent / 'record.json').write_bytes(m.encoded(row))
    (spool.root / 'parts.json').write_bytes(m.encoded(ledger))
    with pytest.raises(ValueError, match='uncompressed part'):
        m.inspect_spool(spool.root, raw=True)


def test_terminal_native_raw_and_partial_tail_durable_copy(tmp_path):
    spool, queue = make(tmp_path)
    for sample in samples(4):
        queue.append(sample)
    native = tmp_path / 'native'
    (native / 'capture').mkdir(parents=True)
    (native / 'run.log').write_bytes(b'original stopped native diagnostics\n')
    (native / 'capture/unpublished-tail.bin').write_bytes(queue.pending)
    (native / 'capture/unparsed-tail.bin').write_bytes(b'partial-frame')
    result = dict(status='ERROR_NATIVE_OR_STREAM_CAPTURE', error='explicit fixture stop')
    (native / 'result.json').write_bytes(m.encoded(result))
    terminal = spool.terminal(result, native_root=native)
    assert terminal['result']['status'] == 'ERROR_NATIVE_OR_STREAM_CAPTURE'
    assert len(terminal['native_capture']) == 4
    for name, expected in terminal['native_capture'].items():
        assert m.pin(spool.root / 'native-terminal-capture' / name) == expected == m.pin(native / name)
    assert (spool.root / 'native-terminal-capture/capture/unpublished-tail.bin').read_bytes() == samples(4)[-1]
    assert not (spool.root / 'reservation.bin').exists()


def test_terminal_corrupt_source_keeps_reservation(tmp_path):
    spool, queue = make(tmp_path)
    finish(spool, queue)
    part = next((spool.root / 'committed').glob('*/*.xz'))
    part.write_bytes(b'corrupt')
    with pytest.raises(ValueError, match='retained compressed'):
        spool.terminal(dict(status='TEST_NATIVE_TERMINAL'))
    assert (spool.root / 'reservation.bin').exists()
    assert not (spool.root / 'native-terminal.json').exists()


def test_terminal_native_symlink_rejected_without_reclaim(tmp_path):
    spool, queue = make(tmp_path)
    finish(spool, queue)
    native = tmp_path / 'native'
    native.mkdir()
    (native / 'link').symlink_to(spool.root / 'header.bin')
    with pytest.raises(ValueError, match='no symlink'):
        spool.terminal(dict(status='TEST_NATIVE_TERMINAL'), native_root=native)
    assert (spool.root / 'reservation.bin').exists()


def test_actual_near_cap_terminal_inventory_rejected_before_write(tmp_path):
    spool, queue = make(tmp_path, payload=20000)
    for sample in samples(3):
        queue.append(sample)
    used = spool.check()
    result = dict(status='TEST_NATIVE_TERMINAL', retained_diagnostic='x' *
                  (spool.limits.payload - used + 1))
    with pytest.raises(ValueError, match='payload and metadata cap'):
        spool.terminal(result)
    assert not (spool.root / 'native-terminal.json').exists()
    assert (spool.root / 'reservation.bin').exists()
    assert spool.check() == used
    assert m.inspect_spool(spool.root, raw=True)['rows'] == 3
