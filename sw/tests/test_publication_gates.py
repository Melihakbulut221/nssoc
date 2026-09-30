# SPDX-FileCopyrightText: 2026 Hasan Melih Akbulut
# SPDX-License-Identifier: Apache-2.0
"""Negative controls for chapter reachability, measured text and PDF freshness."""
import hashlib
import importlib.util
import json
from pathlib import Path
import subprocess
import sys
import time
from types import SimpleNamespace

import pytest
import yaml

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT/'scripts'))
import check_publications as publications
import tex_lint

spec = importlib.util.spec_from_file_location('publication_claims', ROOT/'paper/check_claims.py')
claims = importlib.util.module_from_spec(spec)
spec.loader.exec_module(claims)


@pytest.fixture
def tex_project(tmp_path):
    (tmp_path/'main.tex').write_text('\\begin{document}\n\\input{chapter}\n\\end{document}\n')
    (tmp_path/'chapter.tex').write_text('Text \\label{one} \\ref{one}.\n')
    (tmp_path/'refs.bib').write_text('@book{real, title={Title}}\n')
    return tmp_path


def lint(directory):
    return subprocess.run([sys.executable, str(ROOT/'scripts/tex_lint.py'), str(directory/'main.tex')],
                          capture_output=True, text=True)


@pytest.mark.parametrize('text', ['\\ref{missing}', '\\cite{absent}', '\\label{same} \\label{same}', 'Text & broken'])
def test_chapter_errors_cannot_hide_in_main_file(tex_project, text):
    (tex_project/'chapter.tex').write_text(text+'\n')
    result = lint(tex_project)
    assert result.returncode == 1 and 'FAIL:' in result.stdout


@pytest.mark.parametrize('text', ['\\input{main}', '\\input{missing}', '\\input{../outside}', '\\input{\\computed}', '\\input chapter'])
def test_missing_cycles_escapes_and_computed_inputs_fail(tex_project, text):
    (tex_project/'chapter.tex').write_text(text+'\n')
    with pytest.raises((OSError, ValueError)):
        tex_lint.load_tex(tex_project/'main.tex')


def test_commented_input_and_labels_do_not_satisfy_references(tex_project):
    (tex_project/'chapter.tex').write_text('% \\input{absent}\n% \\label{fake}\n\\ref{fake}\n')
    result = lint(tex_project)
    assert 'has no' in result.stdout and 'No such file' not in result.stdout


def test_real_thesis_chapters_are_all_reached():
    text = tex_lint.load_tex(ROOT/'thesis/main.tex')
    assert text.count('\\chapter{') == 8
    assert '\\label{ch:phys}' in text


@pytest.fixture
def metric(tmp_path, monkeypatch):
    monkeypatch.setattr(claims, 'ROOT', tmp_path)
    (tmp_path/'metric.json').write_text('{"slack": -0.4350975258790219}')
    (tmp_path/'main.tex').write_text('Measured \\SI{-0.4351}{ns}.\n')
    return dict(check='tex_json', file='metric.json', tex='main.tex', key='slack', format='.4f',
                sha256=hashlib.sha256((tmp_path/'metric.json').read_bytes()).hexdigest(), literal=r'\SI{@VALUE@}{ns}')


def test_measured_number_matches_actual_printed_rounding(metric):
    assert claims.check(metric)[0] == 'PASS'


@pytest.mark.parametrize('defect', ['number', 'comment', 'digest', 'key', 'literal', 'format'])
def test_bad_metric_or_transcription_fails(metric, tmp_path, defect):
    if defect == 'number': (tmp_path/'main.tex').write_text(r'\SI{+0.4351}{ns}')
    elif defect == 'comment': (tmp_path/'main.tex').write_text('% '+(tmp_path/'main.tex').read_text())
    elif defect == 'digest': (tmp_path/'metric.json').write_text('{"slack": 0.4351}')
    elif defect == 'key': metric['key'] = 'missing'
    elif defect == 'literal': metric['literal'] = 'unbound value'
    else: metric['format'] = '.1000000f'
    assert claims.check(metric)[0] == 'FAIL'


def test_checked_in_thesis_is_bound_to_its_sources():
    publications.check_freshness()


@pytest.mark.parametrize('defect', ['source', 'pdf', 'missing_document', 'failed', 'missing_bibliography'])
def test_freshness_rejects_source_or_output_drift(tmp_path, monkeypatch, defect):
    (tmp_path/'docs/evidence').mkdir(parents=True)
    (tmp_path/'thesis').mkdir()
    (tmp_path/'thesis/main.pdf').write_bytes(b'fixture PDF identity, not a build')
    (tmp_path/'thesis/main.bbl').write_bytes(b'fixture bibliography identity')
    inventory = {'source.tex': '123'}
    monkeypatch.setattr(publications, 'inputs', lambda root, name: inventory)
    record = dict(status='PASS', documents={name: {'inputs': dict(inventory)} for name in publications.DOCUMENTS},
                  tracked_thesis={name: publications.sha(tmp_path/'thesis'/name)
                                  for name in ('main.pdf', 'main.bbl')})
    (tmp_path/publications.RECEIPT).write_text(json.dumps(record))
    publications.check_freshness(tmp_path)  # Each mutation starts from a valid receipt.
    if defect == 'source': inventory['source.tex'] = 'changed'
    elif defect == 'pdf': (tmp_path/'thesis/main.pdf').write_bytes(b'stale')
    elif defect == 'missing_document': record['documents'].pop('paper-soc')
    elif defect == 'missing_bibliography': record['tracked_thesis'].pop('main.bbl')
    else: record['status'] = 'FAIL'
    (tmp_path/publications.RECEIPT).write_text(json.dumps(record))
    with pytest.raises(ValueError): publications.check_freshness(tmp_path)


def test_build_cannot_reuse_stale_output(tmp_path):
    out = tmp_path/'hw/soc/out/existing'
    out.mkdir(parents=True)
    (out/'main.pdf').write_bytes(b'keep this old evidence')
    with pytest.raises(ValueError, match='existing'):
        publications.build(tmp_path, out)
    assert (out/'main.pdf').read_bytes() == b'keep this old evidence'


def publication_workflow():
    return yaml.safe_load((ROOT/'.github/workflows/publications.yml').read_text())


def warmup_code():
    steps = publication_workflow()['jobs']['manuscripts']['steps']
    warmup = next(step for step in steps if step.get('name', '').startswith('Warm dependencies'))
    return warmup['run'].split("python3 - <<'PY'\n", 1)[1].rsplit('\nPY', 1)[0]


@pytest.fixture
def warmup_project(tmp_path, monkeypatch):
    tool = tmp_path/'hw/soc/tools/publications/tectonic'
    tool.parent.mkdir(parents=True)
    tool.write_bytes(b'fixture engine identity; no native compilation claim')
    for name in publications.DOCUMENTS:
        (tmp_path/name/'chapters').mkdir(parents=True)
        (tmp_path/name/'main.tex').write_text('fixture '+name)
        (tmp_path/name/'chapters/one.tex').write_text('included source '+name)
        (tmp_path/name/'refs.bib').write_text('fixture bibliography')
    (tmp_path/'thesis/main.pdf').write_bytes(b'preserve accepted output')

    def inventory(root, name):
        return {str(path.relative_to(root)): publications.sha(path)
                for path in sorted((root/name).rglob('*'))
                if path.suffix in ('.tex', '.bib')}

    monkeypatch.chdir(tmp_path)
    monkeypatch.setenv('TECTONIC_CACHE_DIR', str(tmp_path/'.cache/tectonic'))
    monkeypatch.setattr(publications, 'inputs', inventory)
    return tmp_path


def execute_warmup():
    with pytest.raises(SystemExit) as completed:
        exec(compile(warmup_code(), '<publication dependency warmup>', 'exec'), {})
    return completed.value.code


def test_dependency_warmup_uses_exact_scratch_inputs_and_shared_budget(warmup_project, monkeypatch):
    root = warmup_project
    ticks = iter([0, 10, 110, 210, 310, 320])
    monkeypatch.setattr(time, 'monotonic', lambda: next(ticks))
    calls = []

    def engine(command, **kwargs):
        directory = kwargs['cwd']
        name = directory.name
        for path, digest in publications.inputs(root, name).items():
            assert publications.sha(directory.parent/path) == digest
        assert directory != root/name
        assert kwargs['env']['SOURCE_DATE_EPOCH'] == '1789776000'
        kwargs['stdout'].write('downloaded dependency fixture\n')
        (directory/'main.pdf').write_bytes(b'preliminary, never accepted')
        calls.append((command, kwargs['timeout']))
        return SimpleNamespace(returncode=0)

    monkeypatch.setattr(subprocess, 'run', engine)
    assert execute_warmup() == 0
    record = json.loads((root/'hw/soc/out/publication-cache-warmup/result.json').read_text())
    assert record['status'] == 'PASS' and record['accepted_deliverables'] is False
    assert record['scope'] == 'CACHE_PREPARATION_ONLY'
    assert [timeout for _, timeout in calls] == [890, 790, 690, 590]
    assert len(calls) == 4 and all(command[1:4] == ['-X', 'compile', 'main.tex'] for command, _ in calls)
    assert (root/'thesis/main.pdf').read_bytes() == b'preserve accepted output'
    assert not (root/'hw/soc/out/publications').exists()


@pytest.mark.parametrize('failure', ['latex_error', 'timeout', 'source_change'])
def test_warmup_never_retries_or_accepts_failed_preparation(warmup_project, monkeypatch, failure):
    root = warmup_project
    calls = []

    def engine(command, **kwargs):
        calls.append(command)
        kwargs['stdout'].write('preserved native diagnostic\n')
        if failure == 'timeout':
            raise subprocess.TimeoutExpired(command, kwargs['timeout'])
        if failure == 'source_change':
            (root/'paper-soc/main.tex').write_text('changed during preparation')
        return SimpleNamespace(returncode=2 if failure == 'latex_error' else 0)

    monkeypatch.setattr(subprocess, 'run', engine)
    assert execute_warmup() == 1
    out = root/'hw/soc/out/publication-cache-warmup'
    record = json.loads((out/'result.json').read_text())
    assert record['status'] == 'FAIL' and not record['accepted_deliverables']
    assert len(calls) == (4 if failure == 'source_change' else 1)
    row = record['documents']['paper-soc']
    assert row['log_sha256'] == publications.sha(out/'paper-soc.log')
    assert (out/'paper-soc.log').read_text() == 'preserved native diagnostic\n'
    if failure == 'timeout':
        assert row['timed_out'] and row['returncode'] is None
    assert not (root/'hw/soc/out/publications').exists()


def test_warmup_refuses_existing_evidence(warmup_project, monkeypatch):
    out = warmup_project/'hw/soc/out/publication-cache-warmup'
    out.mkdir(parents=True)
    (out/'result.json').write_text('preserve previous failure')
    monkeypatch.setattr(subprocess, 'run', lambda *args, **kwargs: pytest.fail('Engine must not run'))
    with pytest.raises(FileExistsError):
        execute_warmup()
    assert (out/'result.json').read_text() == 'preserve previous failure'


def test_workflow_cache_and_warmup_never_replace_final_validation():
    job = publication_workflow()['jobs']['manuscripts']
    steps = job['steps']
    cache = next(step for step in steps if step.get('name', '').startswith('Restore Tectonic'))
    final = next(step for step in steps if step.get('name', '').startswith('Verify tracked freshness'))
    upload = next(step for step in steps if step.get('name', '').startswith('Retain PDFs'))
    assert cache['with']['path'] == '.cache/tectonic'
    assert 'hw/soc/out' not in cache['with']['path']
    assert final['run'].splitlines() == [
        'python3 scripts/check_publications.py --check',
        'python3 scripts/check_publications.py --out hw/soc/out/publications '
        '--tectonic "$PWD/hw/soc/tools/publications/tectonic" --compare-thesis']
    assert 'continue-on-error' not in final
    assert upload['if'] == 'always()'
    assert 'publication-cache-warmup/result.json' in upload['with']['path']
    assert job['timeout-minutes'] == 45
