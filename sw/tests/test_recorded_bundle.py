# SPDX-FileCopyrightText: 2026 Hasan Melih Akbulut
# SPDX-License-Identifier: Apache-2.0
"""Original-byte recovery rejects changed records and unsafe tar members."""
import hashlib
import io
import json
import tarfile

import pytest
from evidence import recorded_bundle


def digest(data):
    return hashlib.sha256(data).hexdigest()


@pytest.fixture
def bundle(tmp_path):
    data = b'original physical evidence\n'
    notice = tmp_path / 'NOTICE.txt'
    notice.write_text('Source licence retained.\n')
    metadata = tmp_path / 'record.json'
    record = {'directories': ['run'],
              'files': {'run/report.txt': {'bytes': len(data), 'sha256': digest(data)}},
              'component_notices': {'file': notice.name, 'sha256': digest(notice.read_bytes())}}

    def write(members=None):
        archive = tmp_path / 'record.tar.gz'
        with tarfile.open(archive, 'w:gz') as stream:
            directory = tarfile.TarInfo('run')
            directory.type = tarfile.DIRTYPE
            stream.addfile(directory)
            for name, content, kind in members if members is not None else [('run/report.txt', data, 'file')]:
                member = tarfile.TarInfo(name)
                if kind == 'link':
                    member.type, member.linkname = tarfile.SYMTYPE, '../../outside'
                    stream.addfile(member)
                else:
                    member.size = len(content)
                    stream.addfile(member, io.BytesIO(content))
        record['archive'] = {'file': archive.name, 'bytes': archive.stat().st_size,
                             'sha256': digest(archive.read_bytes())}
        metadata.write_text(json.dumps(record))
    write()
    return metadata, record, data, write


def test_original_bytes_and_matching_live_copy(bundle, tmp_path):
    metadata, record, data, _ = bundle
    live = tmp_path / 'live/run'
    live.mkdir(parents=True)
    (live / 'report.txt').write_bytes(data)
    output = recorded_bundle(metadata, tmp_path / 'restore', tmp_path / 'live')
    assert (output / 'run/report.txt').read_bytes() == data


def test_live_drift_rejected(bundle, tmp_path):
    metadata, _, _, _ = bundle
    live = tmp_path / 'live/run'
    live.mkdir(parents=True)
    (live / 'report.txt').write_bytes(b'changed')
    with pytest.raises(AssertionError, match='Live artifact differs'):
        recorded_bundle(metadata, tmp_path / 'restore', tmp_path / 'live')
    assert not (tmp_path / 'restore').exists()


@pytest.mark.parametrize('case', ['missing', 'duplicate', 'traversal', 'symlink', 'extra', 'changed'])
def test_invalid_members_rejected_before_any_write(bundle, tmp_path, case):
    metadata, _, data, write = bundle
    member = ('run/report.txt', data, 'file')
    choices = {'missing': [], 'duplicate': [member, member],
               'traversal': [('../outside', data, 'file')],
               'symlink': [('run/report.txt', data, 'link')],
               'extra': [member, ('run/extra', data, 'file')],
               'changed': [('run/report.txt', b'X' * len(data), 'file')]}
    write(choices[case])
    with pytest.raises(AssertionError):
        recorded_bundle(metadata, tmp_path / 'restore', tmp_path / 'absent')
    assert not (tmp_path / 'restore').exists()
    assert not (tmp_path.parent / 'outside').exists()


@pytest.mark.parametrize('field', ['archive', 'component_notices'])
def test_digest_drift_rejected(bundle, tmp_path, field):
    metadata, record, _, _ = bundle
    record[field]['sha256'] = '0' * 64
    metadata.write_text(json.dumps(record))
    with pytest.raises(AssertionError):
        recorded_bundle(metadata, tmp_path / 'restore', tmp_path / 'absent')


def test_existing_output_not_overwritten(bundle, tmp_path):
    metadata, _, _, _ = bundle
    out = tmp_path / 'restore'
    out.mkdir()
    (out / 'keep').write_text('existing evidence')
    with pytest.raises(AssertionError, match='empty'):
        recorded_bundle(metadata, out, tmp_path / 'absent')
    assert (out / 'keep').read_text() == 'existing evidence'
