# SPDX-FileCopyrightText: 2026 Hasan Melih Akbulut
# SPDX-License-Identifier: Apache-2.0
"""Negative controls for chapter reachability, measured text and PDF freshness."""
import hashlib
import importlib.util
import json
from pathlib import Path
import subprocess
import sys

import pytest

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
