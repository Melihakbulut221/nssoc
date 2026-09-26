# SPDX-FileCopyrightText: 2026 Hasan Melih Akbulut
# SPDX-License-Identifier: Apache-2.0
import hashlib
import copy
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
    assert status["core_physical"]["timing_accepted"] is False
    assert status["core_physical"]["manufacturing_approval"] is False


@pytest.mark.parametrize("defect", ["failed", "skipped", "empty", "count", "dirty", "head", "boolean"])
def test_prepared_pytest_status_rejects_unearned_pass(defect):
    record = json.loads((ROOT / "docs/evidence/prepared-pytest-edc4e2d-20260926.json").read_text())
    if defect == "failed": record["failed"] = 1
    elif defect == "skipped": record["skipped"] = 1
    elif defect == "empty": record["collected"] = record["passed"] = 0
    elif defect == "count": record["passed"] -= 1
    elif defect == "dirty": record["final_source_status"] = "DIRTY"
    elif defect == "head": record["source_head"] = "latest"
    else: record["skipped"] = False
    with pytest.raises(ValueError): project_status.python_status(record)


@pytest.mark.parametrize("defect", ["main_markers", "incomplete_density", "antenna_error",
                                    "supplement_missing", "supplement_error", "lvs_count",
                                    "gds_binding", "gds_archive", "timing", "manufacturing"])
def test_physical_status_cannot_promote_failed_or_unbound_candidate(defect):
    record = json.loads((ROOT / "docs/evidence/sram-repaired-core-physical-20260926.json").read_text())
    physical = record["physical"]
    if defect == "main_markers": physical["main"]["markers"] = 1
    elif defect == "incomplete_density": physical["density"]["category_count"] -= 1
    elif defect == "antenna_error": physical["antenna"]["process_returncode"] = 1
    elif defect == "supplement_missing": physical["supplemental"].clear()
    elif defect == "supplement_error": physical["supplemental"][0]["measurement"]["status"] = "ERROR"
    elif defect == "lvs_count": physical["lvs"]["primitives_each"] -= 1
    elif defect == "gds_binding": physical["input_sha256"][physical["candidate_gds"]] = "0" * 64
    elif defect == "gds_archive": record["members"] = {n: h for n, h in record["members"].items() if not n.endswith(".gds")}
    elif defect == "timing": record["final_sta_accepted"] = True
    else: record["manufacturing_approval"] = True
    with pytest.raises(ValueError): project_status.core_physical_status(record)


def test_physical_status_preserves_failed_attempt_without_rejecting_independent_completed_checks():
    record = json.loads((ROOT / "docs/evidence/sram-repaired-core-physical-20260926.json").read_text())
    original = copy.deepcopy(record)
    assert record["physical"]["native_controller_status"] == "ERROR_OR_OPEN_PHYSICAL_GATE"
    assert project_status.core_physical_status(record)["lvs_primitives_each"] == 5129488
    assert record == original


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


def mbist_physical_fixture():
    """Synthetic receipt for rejection tests; never a measurement or public evidence."""
    digest = "a" * 64
    gds = "${REPOSITORY}/test-only.gds"
    audit = dict(status="PASS within comparison scope", reasons=[], extraction_diagnostics=[],
                 circuit_status_counts={"Match": 1}, circuits=[dict(
                     layout="soc_top", schematic="soc_top", status="Match",
                     layout_devices_recursive=5_000_001, schematic_devices_recursive=5_000_001)])
    lvs = dict(status="PASS_NEW_MBIST_CORE_FULL_TRANSISTOR_LVS_AND_DP_SWAP_REJECTED",
               manufacturing_approval=False, timing_acceptance=False,
               candidate_gds=gds, gds_sha256=digest, input_sha256={gds: digest},
               positive=audit, extraction_roundtrip=copy.deepcopy(audit),
               negative=dict(status="FAIL", reasons=["deliberate pin mismatch"], circuits=[
                   dict(layout="soc_top", status="Mismatch")]),
               mutation=dict(pins=["a2[0]", "a2[1]"], original_nets=["a0", "a1"]),
               steps=[dict(name=name, returncode=code) for name, code in [
                   ("positive", 0), ("positive-audit", 0), ("extracted-roundtrip", 0),
                   ("extracted-roundtrip-audit", 0), ("wrong-dp-address-audit", 1)]])
    drc = dict(status="PASS_NEW_LAYOUT_ALL_PHYSICAL_RULES", gds_sha256=digest,
               input_sha256={gds: digest}, manufacturing_approval=False, timing_acceptance=False,
               main=dict(status="PASS", markers=0, categories={}, category_count=560),
               steps=[dict(name=name, status="PASS", measurement=dict(
                   status="PASS", markers=0, categories={}, category_count=count,
                   process_returncode=0, report_sha256="b" * 64)) for name, count in
                   dict(density=7, antenna=31, feol_devices=52, geometry_pin_forbidden=20,
                        geometry_grid=161, geometry_angle=210, beol=117, supplemental_wide=11).items()])
    return dict(status="PASS_PUBLISHED_ETH_MBIST_CORE_PHYSICAL_ONLY", lvs=lvs, drc=drc,
                members={"test-only.gds": digest}, manufacturing_approval=False,
                final_sta_accepted=False, scope="Synthetic validator test only",
                logic=dict(status="PASS_WITHIN_LOCAL_EQUATION_SCOPE", returncode=0))


def test_mbist_status_accepts_complete_scoped_fixture_without_mutation():
    record = mbist_physical_fixture()
    original = copy.deepcopy(record)
    status = project_status.core_physical_status(record)
    assert status["ethernet_fifo_mbist"] is True
    assert status["manufacturing_approval"] is False
    assert status["timing_accepted"] is False
    assert record == original


@pytest.mark.parametrize("defect", [
    "different_gds", "unbound_lvs", "unarchived", "unfinished", "missing_group", "duplicate_group",
    "marker", "missing_categories", "bad_report", "process_error", "main_incomplete", "skipped_circuit",
    "unequal_devices", "duplicate_circuit", "roundtrip_drift", "missing_core", "empty_core",
    "accepted_fault", "unmutated_pins", "equal_nets", "bad_audit_exit", "logic_fail", "signoff",
])
def test_mbist_status_rejects_incomplete_or_false_acceptance(defect):
    r = mbist_physical_fixture()
    lvs, drc = r["lvs"], r["drc"]
    if defect == "different_gds": drc["gds_sha256"] = "0" * 64
    elif defect == "unbound_lvs": lvs["input_sha256"].clear()
    elif defect == "unarchived": r["members"].clear()
    elif defect == "unfinished": lvs["status"] = "RUNNING_positive"
    elif defect == "missing_group": drc["steps"].pop()
    elif defect == "duplicate_group": drc["steps"][-1] = drc["steps"][0]
    elif defect == "marker": drc["steps"][0]["measurement"]["markers"] = 1
    elif defect == "missing_categories": drc["steps"][0]["measurement"]["category_count"] -= 1
    elif defect == "bad_report": drc["steps"][0]["measurement"]["report_sha256"] = "missing"
    elif defect == "process_error": drc["steps"][0]["measurement"]["process_returncode"] = 1
    elif defect == "main_incomplete": drc["main"]["category_count"] -= 1
    elif defect == "skipped_circuit": lvs["positive"]["circuits"][0]["status"] = "Skipped"
    elif defect == "unequal_devices": lvs["positive"]["circuits"][0]["schematic_devices_recursive"] -= 1
    elif defect == "duplicate_circuit":
        lvs["positive"]["circuits"] *= 2
        lvs["positive"]["circuit_status_counts"]["Match"] = 2
    elif defect == "roundtrip_drift":
        c = lvs["extraction_roundtrip"]["circuits"][0]
        c["layout_devices_recursive"] = c["schematic_devices_recursive"] = 5_000_002
    elif defect in ("missing_core", "empty_core"):
        for key in ("positive", "extraction_roundtrip"):
            c = lvs[key]["circuits"][0]
            if defect == "missing_core": c["layout"] = c["schematic"] = "only_a_macro"
            else: c["layout_devices_recursive"] = c["schematic_devices_recursive"] = 0
    elif defect == "accepted_fault": lvs["negative"]["status"] = "PASS within comparison scope"
    elif defect == "unmutated_pins": lvs["mutation"]["pins"] = ["a1[0]", "a1[1]"]
    elif defect == "equal_nets": lvs["mutation"]["original_nets"] = ["a", "a"]
    elif defect == "bad_audit_exit": lvs["steps"][-1]["returncode"] = 0
    elif defect == "logic_fail": r["logic"]["returncode"] = 1
    else: r["manufacturing_approval"] = True
    with pytest.raises(ValueError): project_status.core_physical_status(r)
