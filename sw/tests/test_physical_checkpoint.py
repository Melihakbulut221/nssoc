# SPDX-FileCopyrightText: 2026 Hasan Melih Akbulut
# SPDX-License-Identifier: Apache-2.0
"""Physical restart files survive relocation; corrupt/incomplete copies fail."""
import importlib.util
import json
from pathlib import Path
import shutil

import pytest

SCRIPT = Path(__file__).resolve().parents[2] / 'scripts/collect_physical_checkpoint.py'
spec = importlib.util.spec_from_file_location('physical_checkpoint', SCRIPT)
collector = importlib.util.module_from_spec(spec)
spec.loader.exec_module(collector)


@pytest.fixture
def design(tmp_path):
    root = tmp_path/'project'
    run = root/'hw/soc/pnr/runs/example'
    first = run/'01-place'
    last = run/'02-route'
    first.mkdir(parents=True); last.mkdir()
    views = {}
    for kind in ['odb', 'nl', 'sdc', 'def']:
        path = first/f'design.{kind}'
        path.write_text(kind+' measured bytes\n')
        views[kind] = str(path)
    views['sdf'] = {'slow': views['def']}
    views['gds'] = None
    views['metrics'] = {'timing__setup__ws': -1.2, 'label': 'not signoff'}
    (first/'state_out.json').write_text(json.dumps(views))
    (last/'state_out.json').write_text(json.dumps(views))
    return root, run, root/'hw/soc/out/checkpoint', views


def test_capture_last_state_and_restore_after_relocation(design, tmp_path):
    root, run, out, views = design
    record = collector.capture(root, run, out)
    assert record['status'] == 'CAPTURED' and len(record['files']) == 4
    assert '02-route' in record['source_state']
    moved = tmp_path/'moved bundle with spaces'
    shutil.move(out, moved)
    shutil.rmtree(run)
    restored = json.loads(collector.restore(moved).read_text())
    assert restored['metrics'] == views['metrics'] and restored['gds'] is None
    for key in ['odb', 'nl', 'sdc', 'def']:
        assert Path(restored[key]).is_relative_to(moved)
        assert Path(restored[key]).read_text() == key+' measured bytes\n'
    assert restored['sdf']['slow'] == restored['def']
    with pytest.raises(ValueError, match='overwrite'):
        collector.restore(moved)


@pytest.mark.parametrize('mode', ['malformed', 'missing_odb', 'missing_file'])
def test_bad_latest_state_never_silently_falls_back(design, mode):
    root, run, out, views = design
    state = run/'02-route/state_out.json'
    if mode == 'malformed':
        state.write_text('{')
    elif mode == 'missing_odb':
        state.write_text(json.dumps({'nl': views['nl'], 'sdc': views['sdc']}))
    else:
        Path(views['odb']).unlink()
    with pytest.raises(ValueError):
        collector.capture(root, run, out)
    assert not out.exists()


def test_external_view_and_existing_output_rejected(design, tmp_path):
    root, run, out, views = design
    out.mkdir(parents=True)
    (out/'keep').write_text('old evidence')
    with pytest.raises(ValueError, match='fresh'):
        collector.capture(root, run, out)
    assert (out/'keep').read_text() == 'old evidence'
    path = Path(views['odb']); path.unlink()
    outside = tmp_path/'outside.odb'; outside.write_text('external file')
    path.symlink_to(outside)
    with pytest.raises(ValueError, match='external'):
        collector.capture(root, run, out.with_name('new'))
    assert outside.read_text() == 'external file'


def test_corrupt_view_or_state_rejected_on_restore(design):
    root, run, out, _ = design
    record = collector.capture(root, run, out)
    target = out/next(iter(record['files']))
    original = target.read_bytes(); target.write_bytes(b'corrupted')
    with pytest.raises(ValueError, match='digest'):
        collector.restore(out)
    assert not (out/'state.local.json').exists()
    target.write_bytes(original)
    (out/'state.relative.json').write_text('{}')
    with pytest.raises(ValueError, match='State digest'):
        collector.restore(out)


def test_mutation_during_copy_never_publishes_manifest(design, monkeypatch):
    root, run, out, views = design
    original = collector.shutil.copyfile

    def corrupt(src, dst):
        result = original(src, dst)
        if str(src) == views['odb']:
            Path(src).write_text('changed while copying')
        return result

    monkeypatch.setattr(collector.shutil, 'copyfile', corrupt)
    with pytest.raises(ValueError, match='changed'):
        collector.capture(root, run, out)
    assert not (out/'manifest.json').exists()


def test_output_or_run_outside_allowed_tree_rejected(design, tmp_path):
    root, run, out, _ = design
    with pytest.raises(ValueError, match='hw/soc/out'):
        collector.capture(root, run, tmp_path/'outside')
    with pytest.raises(ValueError, match='hw/soc/pnr/runs'):
        collector.capture(root, tmp_path, out)


def test_repository_metadata_is_not_a_physical_view(design):
    root, run, out, views = design
    metadata = root/'.git/config'
    metadata.parent.mkdir(); metadata.write_text('not a design output')
    views['odb'] = str(metadata)
    (run/'02-route/state_out.json').write_text(json.dumps(views))
    with pytest.raises(ValueError, match='external'):
        collector.capture(root, run, out)
    assert not out.exists()
