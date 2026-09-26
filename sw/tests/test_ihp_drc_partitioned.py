# SPDX-FileCopyrightText: 2026 Hasan Melih Akbulut
# SPDX-License-Identifier: Apache-2.0
"""Reject incomplete/tampered evidence when main DRC is split into processes."""
from copy import deepcopy
import importlib.util
from pathlib import Path
import sys

import pytest

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "hw/soc/flow"))
try:
    spec = importlib.util.spec_from_file_location(
        "drc_partitioned", ROOT / "hw/soc/flow/check_ihp_drc_partitioned.py")
    drc = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(drc)
finally:
    sys.path.pop(0)


@pytest.fixture
def clean(monkeypatch):
    inventories = {"feol_and_geometry": {"Act.a": "Minimum active width"},
                   "beol": {"M1.a": "Minimum metal width"}}
    combined = {**inventories["feol_and_geometry"], **inventories["beol"]}
    monkeypatch.setattr(drc, "CATALOGS", {
        **{name: drc.catalog_identity(cats) for name, cats in inventories.items()},
        "complete": drc.catalog_identity(combined),
    })
    return {name: {"category_inventory": cats,
                   "result": {"status": "PASS", "process_returncode": 0,
                              "markers": 0, "categories": {}, "category_count": 1}}
            for name, cats in inventories.items()}


def test_every_table_is_required(tmp_path):
    entry = tmp_path / "main.drc"
    includes, paths = [], set()
    for name, tables in drc.TABLES.items():
        for table in tables:
            kind = "beol" if name == "beol" else "feol"
            path = tmp_path / "rule_decks" / kind / (table + ".drc")
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(f"if TABLES.include?('{table}') || FEOL\nend\n")
            includes.append("# %include " + path.relative_to(tmp_path).as_posix())
            paths.add(path)
    entry.write_text("\n".join(includes))
    assert sum(map(len, drc.partition_tables(entry, paths).values())) == 37
    with pytest.raises(ValueError, match="not locked"):
        drc.partition_tables(entry, set())
    entry.write_text("\n".join(includes[:-1]))
    with pytest.raises(ValueError, match="inventory differs"):
        drc.partition_tables(entry, paths)
    entry.write_text("\n".join(includes + [includes[0]]))
    with pytest.raises(ValueError, match="duplicate"):
        drc.partition_tables(entry, paths)


def test_both_clean_parts_are_required(clean):
    assert drc.combine(clean)["status"] == "PASS"
    del clean["beol"]
    with pytest.raises(ValueError, match="Missing"):
        drc.combine(clean)


@pytest.mark.parametrize("group,category", [
    ("feol_and_geometry", "'Act.a'"), ("beol", "'M1.a'"),
])
def test_one_failing_group_fails_all_main(clean, group, category):
    clean[group]["result"].update(status="FAIL", markers=2, categories={category: 2})
    result = drc.combine(clean)
    assert result["status"] == "FAIL"
    assert result["markers"] == 2


@pytest.mark.parametrize("code", [1, -9, 124])
def test_tool_error_cannot_pass_with_zero_markers(clean, code):
    clean["beol"]["result"].update(status="ERROR", process_returncode=code)
    assert drc.combine(clean)["status"] == "ERROR"


def test_validation_error_cannot_pass_with_successful_tool(clean):
    clean["beol"]["result"].update(status="ERROR", error="changed input")
    assert drc.combine(clean)["status"] == "ERROR"


@pytest.mark.parametrize("update", [
    {"process_returncode": 1}, {"markers": 1}, {"category_count": 0},
    {"categories": {"'M1.a'": 1}}, {"categories": {"'M1.a'": -1}, "markers": -1},
    {"status": "FAIL", "categories": {"'unknown'": 1}, "markers": 1},
])
def test_inconsistent_saved_result_is_rejected(clean, update):
    clean["beol"]["result"].update(update)
    with pytest.raises(ValueError, match="Inconsistent"):
        drc.combine(clean)


@pytest.mark.parametrize("inventory", [{}, {"M1.b": "Minimum metal width"},
                                       {"M1.a": "A relaxed rule description"}])
def test_missing_renamed_or_modified_category_is_rejected(clean, inventory):
    clean["beol"]["category_inventory"] = inventory
    with pytest.raises(ValueError, match="category inventory"):
        drc.combine(clean)


def test_duplicate_category_between_groups_is_rejected(clean, monkeypatch):
    clean["beol"]["category_inventory"] = deepcopy(clean["feol_and_geometry"]["category_inventory"])
    monkeypatch.setitem(drc.CATALOGS, "beol", drc.CATALOGS["feol_and_geometry"])
    with pytest.raises(ValueError, match="Duplicate"):
        drc.combine(clean)


def test_union_must_match_complete_deck_catalog(clean, monkeypatch):
    monkeypatch.setitem(drc.CATALOGS, "complete", (3, "a" * 64))
    with pytest.raises(ValueError, match="complete"):
        drc.combine(clean)


@pytest.mark.parametrize("category,cell", [("'absent'", "chip"), ("'M1.a'", "absent")])
def test_marker_cannot_escape_category_or_cell_inventory(tmp_path, category, cell):
    report = tmp_path / "drc.lyrdb"
    report.write_text(f"""<report-database><categories><category><name>M1.a</name>
        <description>width</description></category></categories>
        <cells><cell><name>chip</name></cell></cells><items><item>
        <category>{category}</category><cell>{cell}</cell></item></items></report-database>""")
    with pytest.raises(ValueError, match="unknown"):
        drc.read_categories(report)


def test_mutated_input_rejected(tmp_path):
    gds = tmp_path / "layout.gds"
    gds.write_bytes(b"original")
    expected = {gds: drc.digest(gds)}
    drc.verify_inputs(expected)
    gds.write_bytes(b"replacement")
    with pytest.raises(ValueError, match="Input changed"):
        drc.verify_inputs(expected)


@pytest.mark.parametrize("cells,reference", [
    ("<cell><name>macro</name><variant>1</variant></cell>", "macro:1"),
    ("<cell><name>macro</name><variant>1</variant></cell>"
     "<cell><name>macro</name><variant>2</variant></cell>", "macro:2"),
    ("<cell><name>macro</name></cell>"
     "<cell><name>macro</name><variant>1</variant></cell>", "macro"),
])
def test_declared_variant_cell_references_are_supported(tmp_path, cells, reference):
    report = tmp_path / "variants.lyrdb"
    text = f"""<report-database><categories><category><name>M3.e</name>
        <description>wide spacing</description></category></categories>
        <cells>{cells}</cells><items><item><category>'M3.e'</category>
        <cell>{reference}</cell></item></items></report-database>"""
    report.write_text(text)
    assert drc.read_categories(report) == {"M3.e": "wide spacing"}
    assert report.read_text() == text


@pytest.mark.parametrize("cells,reference,reason", [
    ("<cell><name>macro</name><variant>1</variant></cell>", "macro", "unknown"),
    ("<cell><name>macro</name><variant>1</variant></cell>", "macro:2", "unknown"),
    ("<cell><name>macro</name></cell>", "macro:1", "unknown"),
    ("<cell><name/></cell>", "", "Missing"),
    ("<cell><name>macro</name></cell>" * 2, "macro", "Duplicate"),
    ("<cell><name>macro</name><variant>1</variant></cell>" * 2,
     "macro:1", "Duplicate"),
])
def test_undeclared_and_duplicate_variant_identities_are_rejected(
        tmp_path, cells, reference, reason):
    report = tmp_path / "bad-variants.lyrdb"
    report.write_text(f"""<report-database><categories><category><name>M3.e</name>
        <description>wide spacing</description></category></categories>
        <cells>{cells}</cells><items><item><category>'M3.e'</category>
        <cell>{reference}</cell></item></items></report-database>""")
    with pytest.raises(ValueError, match=reason):
        drc.read_categories(report)
