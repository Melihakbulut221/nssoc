# SPDX-FileCopyrightText: 2026 Hasan Melih Akbulut
# SPDX-License-Identifier: Apache-2.0
"""Exercise the same manifest gate called by ci_local.sh and hosted CI."""
import copy
import json
from pathlib import Path
import subprocess
import sys

import pytest

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / 'scripts'))
import build_docs


@pytest.fixture(scope='module')
def built_site(tmp_path_factory):
    out = tmp_path_factory.mktemp('site-gate') / 'site'
    assert build_docs.build(out, 'builtin', True, True) == 0
    return out, json.loads((out / 'manifest.json').read_text())


def invoke(out):
    return subprocess.run([sys.executable, str(ROOT / 'scripts/ci_gate_docs.py'), str(out), 'builtin'],
                          cwd=ROOT, text=True, capture_output=True)


def test_actual_ci_manifest_gate_accepts_reachable_api_pages(built_site):
    out, manifest = built_site
    assert manifest['documents'] > len(build_docs.discover(ROOT))
    result = invoke(out)
    assert result.returncode == 0, result.stdout + result.stderr


@pytest.mark.parametrize('change', ['old_base_count', 'missing_pages', 'extra_page',
                                  'missing_link_report', 'stale_link_count', 'broken_report',
                                  'missing_assets', 'asset_hash', 'asset_escape', 'unresolved'])
def test_manifest_gate_rejects_incomplete_or_corrupted_publication(built_site, change):
    out, original = built_site
    manifest = copy.deepcopy(original)
    if change == 'old_base_count': manifest['documents'] = len(build_docs.discover(ROOT))
    elif change == 'missing_pages': manifest['pages'].pop()
    elif change == 'extra_page': manifest['pages'].append('invented.html')
    elif change == 'missing_link_report': del manifest['broken_local_links']
    elif change == 'stale_link_count': manifest['local_links_checked'] -= 1
    elif change == 'broken_report': manifest['broken_local_links'] = [{'page':'README.html','url':'missing'}]
    elif change == 'missing_assets': del manifest['assets']
    elif change == 'asset_hash': next(iter(manifest['assets'].values()))['sha256'] = '0'*64
    elif change == 'asset_escape': next(iter(manifest['assets'].values()))['output'] = '../outside'
    else: manifest['unresolved'] = [{'file':'README.md','line':1,'reference':'docs/99'}]
    path = out / 'manifest.json'
    try:
        path.write_text(json.dumps(manifest))
        result = invoke(out)
        assert result.returncode == 1 and 'FAIL:' in result.stdout, result.stdout + result.stderr
    finally:
        path.write_text(json.dumps(original))


def test_gate_rechecks_actual_html_even_with_a_clean_manifest(built_site):
    out, _ = built_site
    path = out / 'README.html'; original = path.read_bytes()
    try:
        path.write_bytes(original + b'<a href="missing-target.json">missing</a>')
        result = invoke(out)
        assert result.returncode == 1
        assert 'missing or escaping targets' in result.stdout
    finally:
        path.write_bytes(original)
