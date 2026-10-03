# SPDX-FileCopyrightText: 2026 Hasan Melih Akbulut
# SPDX-License-Identifier: Apache-2.0
"""Exercise Make's real dependency graph and the actual thesis source archive."""
import os
from pathlib import Path
import re
import shutil
import subprocess
import tarfile
import time

import pytest

ROOT = Path(__file__).resolve().parents[2]
pytestmark = pytest.mark.skipif(shutil.which('make') is None or shutil.which('tar') is None,
                                reason='make and tar required for distribution checks')


def checkout(tmp_path):
    dest = tmp_path/'thesis'
    shutil.copytree(ROOT/'thesis', dest, ignore=shutil.ignore_patterns('*.log','*.aux','*.out','arxiv.tar.gz'))
    # A known fresh output is a fixture, not a PDF build/quality claim.
    now = time.time()
    for path in dest.rglob('*'):
        if path.is_file():
            os.utime(path, (now-30, now-30))
    os.utime(dest/'main.pdf', (now-10, now-10))
    return dest, now


@pytest.mark.parametrize('dependency', ['chapters/arch.tex','figures/layout_blocks.pdf','Makefile'])
def test_chapter_figure_and_recipe_edits_require_rebuild(tmp_path, dependency):
    dest, now = checkout(tmp_path)
    command = ['make','-n','main.pdf','TECTONIC=tectonic-for-test']
    before = subprocess.run(command,cwd=dest,capture_output=True,text=True,check=True)
    assert ' -X compile ' not in before.stdout
    os.utime(dest/dependency,(now-5,now-5))
    after = subprocess.run(command,cwd=dest,capture_output=True,text=True,check=True)
    assert 'tectonic-for-test -X compile main.tex' in after.stdout


def test_archive_contains_every_literal_tex_input_and_graphic(tmp_path):
    dest, _ = checkout(tmp_path)
    subprocess.run(['make','arxiv'],cwd=dest,capture_output=True,text=True,check=True)
    with tarfile.open(dest/'arxiv.tar.gz') as archive:
        names = set(archive.getnames())
        pending = ['main.tex']
        seen = set()
        while pending:
            name = pending.pop()
            if name in seen:
                continue
            seen.add(name)
            assert name in names
            text = archive.extractfile(name).read().decode()
            for target in re.findall(r'\\input\{([^}]+)\}',text):
                pending.append(target if target.endswith('.tex') else target+'.tex')
            for target in re.findall(r'\\includegraphics(?:\[[^]]*\])?\{([^}]+)\}',text):
                assert target in names, 'Missing figure: '+target
                assert archive.extractfile(target).read() == (dest/target).read_bytes()
        assert len(seen)==9  # Main plus eight current chapters.
        assert 'main.bbl' in names
        for name in names:
            assert archive.extractfile(name).read() == (dest/name).read_bytes()
