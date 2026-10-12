# SPDX-FileCopyrightText: 2026 Hasan Melih Akbulut
# SPDX-License-Identifier: Apache-2.0
"""Verify real tar hard links and reject unsafe or incorrect restore targets."""
import hashlib
import importlib.util
import io
from pathlib import Path
import shutil
import tarfile
from unittest.mock import patch

import pytest

SCRIPT = Path(__file__).resolve().parents[2] / 'scripts/verify_cloud_output_restore.py'


@pytest.mark.parametrize('fault', [None, 'outside', 'forward', 'wrong_hash', 'wrong_size', 'symlink', 'duplicate'])
def test_tar_hardlink_content_contract(tmp_path, fault):
    spec = importlib.util.spec_from_file_location('restore', SCRIPT)
    m = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(m)
    first, second = 'hw/soc/out/first.raw', 'hw/soc/out/second.raw'
    data = b'one captured waveform, two original hardlinked paths'
    digest = hashlib.sha256(data).hexdigest()
    packed = tmp_path / 'archive.tar.gz'
    with tarfile.open(packed, 'w:gz') as tar:
        a = tarfile.TarInfo(first)
        a.mode, a.size = 0o640, len(data)
        tar.addfile(a, io.BytesIO(data))
        b = tarfile.TarInfo(first if fault == 'duplicate' else second)
        b.mode = 0o640
        b.type = tarfile.SYMTYPE if fault == 'symlink' else tarfile.LNKTYPE
        b.linkname = '../outside' if fault == 'outside' else 'hw/soc/out/unseen' if fault == 'forward' else first
        tar.addfile(b)
    archive_digest = hashlib.sha256(packed.read_bytes()).hexdigest()
    asset = dict(size=packed.stat().st_size, digest='sha256:' + archive_digest, browser_download_url='https://example.test/archive', name=packed.name)
    records = [dict(path=n, bytes=len(data), sha256=digest, mode=0o640) for n in (first, second)]
    if fault == 'wrong_hash':
        records[1]['sha256'] = '0' * 64
    if fault == 'wrong_size':
        records[1]['bytes'] += 1
    manifest = dict(format=1, encoding='tar-gzip', records=records,
                    parts=[dict(name=packed.name, bytes=asset['size'], sha256=archive_digest, url=asset['browser_download_url'])])
    with patch.object(m, 'download', side_effect=lambda a, p: shutil.copyfile(packed, p)):
        if fault:
            with pytest.raises(AssertionError):
                m.audit(manifest, {packed.name: asset}, tmp_path)
        else:
            assert m.audit(manifest, {packed.name: asset}, tmp_path) == dict(
                files=2, restored_logical_bytes=2 * len(data), verified_hardlinks=1)
