# SPDX-FileCopyrightText: 2026 Hasan Melih Akbulut
# SPDX-License-Identifier: Apache-2.0
import hashlib
import json
from pathlib import Path
import subprocess
import sys

import pytest
import yaml

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "scripts"))
import build_docs
import project_status


def test_project_status_is_source_bound_and_matches_readme():
    result = subprocess.run([sys.executable, "scripts/project_status.py"], cwd=ROOT,
                            capture_output=True, text=True)
    assert result.returncode == 0, result.stdout + result.stderr
    status = project_status.derive()
    assert status["python"]["failures"] == 0
    assert status["native_boot"]["status"] == "PASS"
    native = json.loads((ROOT / status["sources"]["native_boot"]).read_text())
    prior = json.loads((ROOT / native["prior_failure"]).read_text())
    assert any(run["status"] == "FAIL" for run in prior["runs"])
    assert status["native_boot"]["profiles"] == ["base", "full"]
    assert native["acceptance"]["checks"] == 28
    assert status["physical"]["setup_ns"] < 0
    assert status["ram"]["negative_rejected"]


@pytest.mark.parametrize("defect", ["missing", "duplicate", "failed", "changed", "different_head"])
def test_native_status_rejects_incomplete_profile_acceptance(defect):
    record = json.loads((ROOT / "docs/evidence/native-recovery-completed-20260921.json").read_text())
    if defect == "missing": record["runs"].pop()
    elif defect == "duplicate": record["runs"][1] = record["runs"][0]
    elif defect == "failed": record["runs"][0]["result"]["passed"] = False
    elif defect == "changed": record["runs"][0]["result"]["sources_unchanged"] = False
    else: record["runs"][0]["head"] = "0" * 40
    with pytest.raises(ValueError): project_status.native_status(record)


@pytest.mark.parametrize("defect", ["missing", "removed", "stale", "failed", "changed", "empty"])
def test_formal_status_rejects_stale_or_nonpassing_tasks(defect):
    record = json.loads((ROOT / "docs/evidence/formal-sweep-completed-20260921.json").read_text())
    result = record["runs"][0]["result"]
    task = next(iter(result["tasks"].values()))
    if defect == "missing": task["status"] = "MISSING"
    elif defect == "removed": result["tasks"].pop(next(iter(result["tasks"])))
    elif defect == "stale": task["source_state"] = "stale"
    elif defect == "failed": result["passed"] = False
    elif defect == "changed": result["sources_unchanged"] = False
    else: result["tasks"].clear()
    with pytest.raises(ValueError): project_status.formal_status(record)


def test_readme_migration_preserves_every_original_byte():
    record = json.loads((ROOT / "docs/evidence/readme-migration-20260920.json").read_text())
    archive = (ROOT / record["archive"]).read_bytes()
    marker = record["archive_body_marker"].encode()
    assert archive.count(marker) == 1
    original = archive.split(marker, 1)[1]
    assert len(original) == record["original_bytes"]
    assert hashlib.sha256(original).hexdigest() == record["original_sha256"]
    assert len((ROOT / "README.md").read_text().splitlines()) <= 125


def test_citation_identifies_repository_without_inventing_release():
    citation = yaml.safe_load((ROOT / "CITATION.cff").read_text())
    assert citation["cff-version"] == "1.2.0"
    assert citation["authors"] == [{"family-names": "Akbulut", "given-names": "Hasan Melih"}]
    assert citation["repository-code"] == "https://github.com/Melihakbulut221/nssoc"
    assert not {"doi", "version", "date-released"}.intersection(citation)


def test_image_asset_is_copied_and_rendered(tmp_path):
    source = tmp_path / "source"
    source.mkdir()
    (source / "diagram.svg").write_text('<svg xmlns="http://www.w3.org/2000/svg"/>')
    out = tmp_path / "site"
    out.mkdir()
    doc = build_docs.Document(path=source / "README.md", rel="README.md", slug="README", number=None)
    doc.resolved = '![A & B](diagram.svg)\n![Remote](https://example.com/remote.png)\n'
    rendered = build_docs.copy_document_images(doc, out, source)
    assert "https://example.com/remote.png" in rendered
    assets = list((out / "assets").glob("*.svg"))
    assert len(assets) == 1 and assets[0].read_bytes() == (source / "diagram.svg").read_bytes()
    html = build_docs.inline_html(rendered)
    assert '<img src="assets/' in html and 'alt="A &amp; B"' in html
    assert '<a href="assets/' not in html


def test_document_image_cannot_export_an_outside_file(tmp_path):
    root = tmp_path / "repo"
    root.mkdir()
    out = root / "site"
    out.mkdir()
    (tmp_path / "outside.svg").write_text("outside")
    doc = build_docs.Document(path=root / "README.md", rel="README.md", slug="README", number=None)
    doc.resolved = "![Outside](../outside.svg)"
    with pytest.raises(ValueError, match="escapes repository"):
        build_docs.copy_document_images(doc, out, root)
    assert not list(out.iterdir())


def test_markdown_comments_hidden_but_fenced_example_preserved():
    text = '<!-- project-status:start -->\nVisible\n\n```html\n<!-- example -->\n```\n'
    html = build_docs.render_markdown(text, [])
    assert "project-status" not in html
    assert "&lt;!-- example --&gt;" in html
    assert "Visible" in html


@pytest.mark.parametrize("extensions,expected", [
    ("+tex_math_dollars\n+pipe_tables\n", "gfm-tex_math_dollars"),
    ("+tex_math_dollars\n-tex_math_gfm\n", "gfm-tex_math_dollars-tex_math_gfm"),
    ("+pipe_tables\n", "gfm"),
])
def test_pandoc_reader_uses_only_installed_extensions(monkeypatch, extensions, expected):
    build_docs.pandoc_input_format.cache_clear()
    def run(command, **kwargs):
        assert command == ["pandoc", "--list-extensions=gfm"]
        return subprocess.CompletedProcess(command, 0, extensions, "")
    monkeypatch.setattr(build_docs.subprocess, "run", run)
    try:
        assert build_docs.pandoc_input_format() == expected
    finally:
        build_docs.pandoc_input_format.cache_clear()


def test_failed_pandoc_cannot_claim_a_successful_pandoc_site(tmp_path, monkeypatch):
    monkeypatch.setattr(build_docs.shutil, "which", lambda name: "/fixture/pandoc")
    monkeypatch.setattr(build_docs, "run_pandoc", lambda *args: None)
    assert build_docs.build(tmp_path / "site", "pandoc", False, True) == 2
    assert not (tmp_path / "site/manifest.json").exists()
