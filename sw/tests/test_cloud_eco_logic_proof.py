# SPDX-FileCopyrightText: 2026 Hasan Melih Akbulut
# SPDX-License-Identifier: Apache-2.0
"""Reject wrong producer, changed code and altered immutable proof inputs."""
import copy
import importlib.util
import json
from pathlib import Path
import stat
import sys
import zipfile

import pytest

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT/'scripts'))
try:
    SPEC = importlib.util.spec_from_file_location('cloud_eco', ROOT/'scripts/run_cloud_eco_logic_proof.py')
    ECO = importlib.util.module_from_spec(SPEC)
    SPEC.loader.exec_module(ECO)
finally:
    sys.path.pop(0)


def metadata():
    trial = copy.deepcopy(ECO.TRIALS['xor_36990647399'])
    run = dict(id=trial['run_id'], head_sha=trial['source_commit'], status='completed',
               conclusion='success', repository=dict(full_name=ECO.REPOSITORY))
    artifact = dict(id=trial['artifact_id'], name=trial['artifact_name'], expired=False,
                    size_in_bytes=trial['bytes'], digest='sha256:'+trial['sha256'],
                    workflow_run=dict(id=trial['run_id'], head_sha=trial['source_commit']))
    return trial, run, artifact


def test_exact_completed_producer_and_immutable_zip():
    ECO.validate_metadata(*metadata())


@pytest.mark.parametrize('mutation', ['run', 'source', 'incomplete', 'failed', 'repository',
                                     'artifact', 'digest', 'expired', 'size', 'producer'])
def test_metadata_mismatch_fails(mutation):
    trial, run, artifact = metadata()
    if mutation == 'run':
        run['id'] += 1
    elif mutation == 'source':
        run['head_sha'] = '0'*40
    elif mutation == 'incomplete':
        run['status'] = 'in_progress'
    elif mutation == 'failed':
        run['conclusion'] = 'failure'
    elif mutation == 'repository':
        run['repository']['full_name'] = 'wrong/repo'
    elif mutation == 'artifact':
        artifact['id'] += 1
    elif mutation == 'digest':
        artifact['digest'] = 'sha256:'+'0'*64
    elif mutation == 'expired':
        artifact['expired'] = True
    elif mutation == 'size':
        artifact['size_in_bytes'] += 1
    else:
        artifact['workflow_run']['head_sha'] = '0'*40
    with pytest.raises(ValueError):
        ECO.validate_metadata(trial, run, artifact)


@pytest.mark.parametrize('name,mode', [('../escape', 0), ('/absolute', 0),
                                     ('./alias', 0), ('link', stat.S_IFLNK | 0o777)])
def test_zip_unsafe_members_fail(tmp_path, name, mode):
    archive = tmp_path/'artifact.zip'
    with zipfile.ZipFile(archive, 'w') as sink:
        info = zipfile.ZipInfo(name)
        info.external_attr = mode << 16
        sink.writestr(info, 'data')
    with pytest.raises(ValueError):
        ECO.extract_zip(archive, tmp_path/'unpacked')
    assert not (tmp_path/'escape').exists()


def test_regular_zip_and_duplicate_rejection(tmp_path):
    archive = tmp_path/'ok.zip'
    with zipfile.ZipFile(archive, 'w') as sink:
        sink.writestr('methods/a.py', 'original')
    assert ECO.extract_zip(archive, tmp_path/'valid') == dict(files=1, expanded_bytes=8)
    with zipfile.ZipFile(archive, 'a') as sink, pytest.warns(UserWarning):
        sink.writestr('methods/a.py', 'changed')
    with pytest.raises(ValueError, match='duplicate'):
        ECO.extract_zip(archive, tmp_path/'duplicate')


def producer(tmp_path):
    trial = copy.deepcopy(ECO.TRIALS['xor_36990647399'])
    method = tmp_path/'methods'/trial['entrypoint']
    method.parent.mkdir(parents=True)
    method.write_text('original source\n')
    row = dict(github_source_commit=trial['source_commit'], diagnostic_kind=trial['kind'],
               manifest_sha256=ECO.MANIFEST_SHA, method_files={trial['entrypoint']: ECO.file_pin(method)})
    (tmp_path/'result.json').write_text(json.dumps(row))
    return trial, method


def test_producer_method_must_equal_original_git_blob(tmp_path, monkeypatch):
    trial, method = producer(tmp_path)
    monkeypatch.setattr(ECO, 'git_bytes', lambda commit, path: method.read_bytes())
    assert trial['entrypoint'] in ECO.verify_producer_sources(tmp_path, trial)
    monkeypatch.setattr(ECO, 'git_bytes', lambda commit, path: b'altered source\n')
    with pytest.raises(ValueError, match='exact producer Git blob'):
        ECO.verify_producer_sources(tmp_path, trial)


def test_uninventoried_dependency_cannot_be_executed(tmp_path, monkeypatch):
    trial, method = producer(tmp_path)
    monkeypatch.setattr(ECO, 'git_bytes', lambda commit, path: method.read_bytes())
    method.with_name('shadow.py').write_text('not captured source')
    with pytest.raises(ValueError, match='method tree'):
        ECO.verify_producer_sources(tmp_path, trial)


def bundle(tmp_path):
    manifest = dict(initial_state='state.json', config='config.json', files={})
    (tmp_path/'state.json').write_text(json.dumps(dict(nl='@BUNDLE@/'+ECO.BEFORE)))
    (tmp_path/'config.json').write_text(json.dumps(dict(STD_CELL_LIBRARY='sg13g2_stdcell', MACROS={
        name: dict(vh=['@BUNDLE@/'+ECO.MACRO]) for name in ['SP6TSRAM512x64', 'DP8TSRAMDP256x16']})))
    for name in (ECO.BEFORE, ECO.STANDARD, ECO.MACRO):
        p = tmp_path/name
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(name)
        manifest['files'][name] = ECO.file_pin(p)
    return manifest


def test_exact_unpowered_c10_and_macro_interfaces(tmp_path):
    manifest = bundle(tmp_path)
    assert ECO.bundle_inputs(tmp_path, manifest) == tuple(tmp_path/name for name in (ECO.BEFORE, ECO.STANDARD, ECO.MACRO))


@pytest.mark.parametrize('mutation', ['powered', 'macro_model', 'liberty'])
def test_input_substitution_fails(tmp_path, mutation):
    manifest = bundle(tmp_path)
    if mutation == 'powered':
        (tmp_path/'state.json').write_text(json.dumps(dict(nl='@BUNDLE@/'+ECO.BEFORE.replace('.nl.v', '.pnl.v'))))
    elif mutation == 'macro_model':
        config = json.loads((tmp_path/'config.json').read_text())
        config['MACROS']['SP6TSRAM512x64']['vh'] = ['@BUNDLE@/invented.v']
        (tmp_path/'config.json').write_text(json.dumps(config))
    else:
        (tmp_path/ECO.STANDARD).write_text('changed function')
    with pytest.raises(ValueError):
        ECO.bundle_inputs(tmp_path, manifest)


def test_full_work_is_cloud_only(tmp_path, monkeypatch):
    monkeypatch.delenv('GITHUB_ACTIONS', raising=False)
    with pytest.raises(ValueError, match='cloud-only'):
        ECO.run('xor_36990647399', tmp_path/'out', tmp_path/'work')
    assert not (tmp_path/'out').exists()
