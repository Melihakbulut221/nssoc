# SPDX-FileCopyrightText: 2026 Hasan Melih Akbulut
# SPDX-License-Identifier: Apache-2.0
import copy
import hashlib
import io
from pathlib import Path
import sys

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[2]/'scripts'))
import fetch_evidence_assets as assets


def manifest():
    return dict(release_tag='evidence-test', assets=[dict(name='wave.tar.xz', bytes=4,
        sha256=hashlib.sha256(b'data').hexdigest(), url=assets.PREFIX+'evidence-test/wave.tar.xz')])


@pytest.mark.parametrize('defect', ['traversal', 'url', 'sha', 'size', 'duplicate', 'empty'])
def test_asset_inventory_rejects_unsafe_or_ambiguous_identity(defect):
    record = manifest()
    if defect == 'traversal': record['assets'][0]['name'] = '../wave.tar.xz'
    elif defect == 'url': record['assets'][0]['url'] = 'https://example.org/wave.tar.xz'
    elif defect == 'sha': record['assets'][0]['sha256'] = 'latest'
    elif defect == 'size': record['assets'][0]['bytes'] = True
    elif defect == 'duplicate': record['assets'].append(copy.deepcopy(record['assets'][0]))
    else: record['assets'] = []
    with pytest.raises(ValueError): assets.validate(record)


@pytest.mark.parametrize('payload', [b'bad!', b'dat', b'data-extra'])
def test_corrupt_download_never_becomes_an_accepted_asset(tmp_path, monkeypatch, payload):
    row = assets.validate(manifest())[0]
    monkeypatch.setattr(assets, 'urlopen', lambda *a, **kw: io.BytesIO(payload))
    with pytest.raises(ValueError): assets.fetch(row, tmp_path)
    assert not (tmp_path/row['name']).exists()


def test_verified_asset_is_reused_without_network_and_corruption_is_not_overwritten(tmp_path, monkeypatch):
    row = assets.validate(manifest())[0]
    monkeypatch.setattr(assets, 'urlopen', lambda *a, **kw: io.BytesIO(b'data'))
    assets.fetch(row, tmp_path)
    def no_network(*args, **kwargs): raise AssertionError('Unexpected network access')
    monkeypatch.setattr(assets, 'urlopen', no_network)
    assets.fetch(row, tmp_path)
    (tmp_path/row['name']).write_bytes(b'bad!')
    with pytest.raises(ValueError): assets.fetch(row, tmp_path)
    assert (tmp_path/row['name']).read_bytes() == b'bad!'
