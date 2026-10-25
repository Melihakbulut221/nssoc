# SPDX-FileCopyrightText: 2026 Hasan Melih Akbulut
# SPDX-License-Identifier: Apache-2.0
"""Portable site publication, checked at the emitted HTML boundary."""
import hashlib
import json
from pathlib import Path
import subprocess
import sys
from urllib.parse import unquote, urlsplit

import pytest

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / 'scripts'))
import build_docs as site


def make_repo(tmp_path, monkeypatch):
    root = tmp_path / 'repo'
    root.mkdir()
    # REUSE-IgnoreStart
    files = {
        'README.md': '# Start\n\n[API](api/README.md)\n[Proof](docs/evidence/result.json?download=1#status)\n![Map](docs/img/diagram.svg)\n[Licence](LICENSES.md)\n',
        'docs/00-index.md': '# Index\n\n[Home](../README.md)\n',
        'docs/01-test.md': '# Test\n\n[Root](../README.md)\n',
        'api/README.md': '# API\n\n[Home](../README.md)\n[Source](../src/example.py)\n',
        'docs/evidence/result.json': '{"status":"FAIL"}\n',
        'docs/img/diagram.svg': '<svg xmlns="http://www.w3.org/2000/svg"/>',
        'docs/img/diagram.svg.license': 'SPDX-License-Identifier: Apache-2.0\n',
        'src/example.py': '# SPDX-License-Identifier: Apache-2.0\nprint("example")\n',
        'LICENSES.md': '# Licences\n',
        'LICENSES/Apache-2.0.txt': 'fixture licence text\n',
        'REUSE.toml': 'version = 1\n',
    }
    # REUSE-IgnoreEnd
    for name, text in files.items():
        path = root / name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(text)
    subprocess.run(['git', 'init', '-q', str(root)], check=True)
    subprocess.run(['git', '-C', str(root), 'add', '.'], check=True)
    monkeypatch.setattr(site, 'REPO_ROOT', root)
    return root


def test_standalone_site_preserves_assets_api_cycles_licences_and_url_suffix(tmp_path, monkeypatch):
    root = make_repo(tmp_path, monkeypatch)
    out = tmp_path / 'site'
    assert site.build(out, 'builtin', True, True) == 0
    manifest = json.loads((out / 'manifest.json').read_text())
    assert manifest['documents'] == 5
    assert manifest['local_links_checked'] > 10
    assert manifest['broken_local_links'] == []
    for relative, row in manifest['assets'].items():
        data = (out / row['output']).read_bytes()
        assert data == (root / relative).read_bytes()
        assert hashlib.sha256(data).hexdigest() == row['sha256']
    for relative in ['docs/evidence/result.json', 'src/example.py', 'REUSE.toml',
                     'LICENSES.md', 'LICENSES/Apache-2.0.txt', 'docs/img/diagram.svg.license']:
        assert relative in manifest['assets']
    html = (out / 'README.html').read_text()
    assert 'files/docs/evidence/result.json?download=1#status' in html
    assert '<a href="source-' in html
    assert '<img src="files/docs/img/diagram.svg"' in html
    assert any('API</h1>' in p.read_text() for p in out.glob('source-*.html'))
    # Move the site away and remove its input tree: no dependency on checkout.
    subprocess.run(['mv', str(root), str(tmp_path / 'gone')], check=True)
    assert site.check_site_links(out)[1] == []


@pytest.mark.parametrize('kind', ['missing', 'untracked', 'outside', 'encoded_outside',
                                  'symlink_outside', 'symlink_inside', 'directory', 'oversize'])
def test_unpublishable_target_fails_without_a_success_manifest(tmp_path, monkeypatch, kind):
    root = make_repo(tmp_path, monkeypatch)
    target = 'secret.json'
    (root / target).write_text('private')
    if kind == 'missing':
        target = 'missing.json'
    elif kind in {'outside', 'encoded_outside'}:
        (tmp_path / 'secret.json').write_text('private')
        target = '../secret.json' if kind == 'outside' else '%2e%2e/secret.json'
    elif kind.startswith('symlink'):
        (root / 'link.json').symlink_to(tmp_path / 'secret.json' if kind.endswith('outside') else root / 'docs/evidence/result.json')
        (tmp_path / 'secret.json').write_text('private')
        subprocess.run(['git', '-C', str(root), 'add', 'link.json'], check=True)
        target = 'link.json'
    elif kind == 'directory':
        target = 'docs'
    elif kind == 'oversize':
        target = 'docs/evidence/result.json'
        monkeypatch.setattr(site, 'MAX_ASSET_BYTES', 1)
    (root / 'README.md').write_text(f'# Start\n[Target]({target})\n')
    out = tmp_path / 'site'
    assert site.build(out, 'builtin', True, True) == 2
    assert not (out / 'manifest.json').exists()
    assert not (out / 'files/secret.json').exists()


def test_code_links_and_remote_urls_are_neither_exported_nor_rewritten(tmp_path, monkeypatch):
    root = make_repo(tmp_path, monkeypatch)
    source = root / 'README.md'
    source.write_text('# Start\n\n`[Inline](missing.json)`\n\n````md\n[Example](missing.json)\n```\n[Still code](other.json)\n````\n\n[Remote](https://example.invalid/docs/01-test.md)\n![Remote](https://example.invalid/map.svg)\n')
    out = tmp_path / 'site'
    assert site.build(out, 'builtin', True, True) == 0
    html = (out / 'README.html').read_text()
    assert 'https://example.invalid/docs/01-test.md' in html
    assert 'https://example.invalid/map.svg' in html
    assert not (out / 'files/missing.json').exists()


def test_multiline_label_and_numbered_destination_are_not_nested(tmp_path, monkeypatch):
    root = make_repo(tmp_path, monkeypatch)
    (root / 'README.md').write_text('# Start\n\n[Multiline\nproof](docs/evidence/result.json)\n[docs/01](docs/01-test.md)\nBare docs/01.\n')
    out = tmp_path / 'site'
    assert site.build(out, 'builtin', True, True) == 0
    html = (out / 'README.html').read_text()
    assert '<a href="files/docs/evidence/result.json">Multiline proof</a>' in html
    assert '<a href="01-test.html">docs/01</a>' in html
    assert '[docs/01]' not in html


def test_rendered_link_check_detects_missing_and_escape_even_if_rewriter_misses_it(tmp_path):
    (tmp_path / 'index.html').write_text('<a href="missing.json">missing</a><img src="../secret.svg"><a href="https://example.invalid/a">remote</a>')
    count, errors = site.check_site_links(tmp_path)
    assert count == 2
    assert {r['url'] for r in errors} == {'missing.json', '../secret.svg'}


def test_output_cannot_replace_tracked_source_directory(tmp_path, monkeypatch):
    root = make_repo(tmp_path, monkeypatch)
    before = (root / 'docs/evidence/result.json').read_bytes()
    assert site.build(root / 'docs', 'builtin', True, True) == 2
    assert (root / 'docs/evidence/result.json').read_bytes() == before


def test_current_repository_site_has_no_missing_local_file(tmp_path):
    out = tmp_path / 'site'
    assert site.build(out, 'builtin', True, True) == 0
    manifest = json.loads((out / 'manifest.json').read_text())
    assert manifest['local_links_checked'] > 8000
    assert manifest['broken_local_links'] == []
    assert 'docs/evidence/soc-hal-20260921.json' in manifest['assets']
    # Independent inspection of actual output, beyond the generator manifest.
    for page in out.glob('*.html'):
        parser = site.PageLinks()
        parser.feed(page.read_text())
        for url in parser.urls:
            parts = urlsplit(url)
            if parts.scheme or parts.netloc or not parts.path:
                continue
            target = (page.parent / unquote(parts.path)).resolve()
            assert target.is_relative_to(out.resolve()) and target.is_file(), (page.name, url)
