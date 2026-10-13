# SPDX-FileCopyrightText: 2026 Hasan Melih Akbulut
# SPDX-License-Identifier: Apache-2.0
"""Cleanup must preserve targets and reject replacements or scope escapes."""
import os
from pathlib import Path
import sys
import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / 'scripts'))
import clean_cloud_output_links as cleanup


def test_links_and_fifo_never_follow_targets(tmp_path):
    base = tmp_path / 'out'; base.mkdir()
    outside = tmp_path / 'source'; outside.mkdir()
    original = outside / 'keep'; original.write_text('original evidence')
    (base / 'dirlink').symlink_to(outside, target_is_directory=True)
    (base / 'filelink').symlink_to(original)
    os.mkfifo(base / 'stream.fifo')
    rows = cleanup.inventory(base)
    assert {r['kind'] for r in rows} == {'symlink', 'fifo'} and len(rows) == 3
    for row in rows:
        assert cleanup.remove_entry(base, row)
        assert not cleanup.remove_entry(base, row)
    assert original.read_text() == 'original evidence'


def test_replaced_link_is_preserved(tmp_path):
    path = tmp_path / 'link'; path.symlink_to('old')
    row = cleanup.record(path, tmp_path)
    path.unlink(); path.symlink_to('changed')
    with pytest.raises(ValueError, match='changed'):
        cleanup.remove_entry(tmp_path, row)
    assert os.readlink(path) == 'changed'


def test_regular_replacement_and_link_ancestor_rejected(tmp_path):
    parent = tmp_path / 'inner'; parent.mkdir()
    path = parent / 'link'; path.symlink_to('absent')
    row = cleanup.record(path, tmp_path)
    path.unlink(); path.write_text('new source')
    with pytest.raises(ValueError, match='Only'):
        cleanup.remove_entry(tmp_path, row)
    assert path.read_text() == 'new source'
    saved = tmp_path / 'saved'; parent.rename(saved)
    parent.symlink_to(saved, target_is_directory=True)
    with pytest.raises(ValueError, match='ancestor'):
        cleanup.remove_entry(tmp_path, row)


@pytest.mark.parametrize('name', ['../outside', '/tmp/outside', '.git/link', 'cloud-migration-state/link'])
def test_outside_and_protected_scopes_rejected(tmp_path, name):
    with pytest.raises(ValueError):
        cleanup.remove_entry(tmp_path, {'path': name})
