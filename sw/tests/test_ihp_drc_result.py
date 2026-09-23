# SPDX-FileCopyrightText: 2026 Hasan Melih Akbulut
# SPDX-License-Identifier: Apache-2.0
"""A DRC process exit must never conceal violations or incomplete evidence."""
import importlib.util
import json
from pathlib import Path
import sys

import pytest

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "hw/soc/flow"))
try:
    spec = importlib.util.spec_from_file_location("check_ihp_drc", ROOT / "hw/soc/flow/check_ihp_drc.py")
    drc = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(drc)
finally:
    sys.path.pop(0)


def report(markers="", top="chip"):
    return f'''<report-database><top-cell>{top}</top-cell>
    <categories><category><name>M1.a</name></category></categories>
    <cells><cell><name>{top}</name></cell></cells><items>{markers}</items>
    </report-database>'''


MARKER = '''<item><category>'M1.a'</category><cell>chip</cell>
<visited>true</visited><waived>true</waived></item>'''


@pytest.mark.parametrize("returncode,markers,status", [
    (0, "", "PASS"), (0, MARKER * 2, "FAIL"), (1, "", "ERROR"),
    (-15, "", "ERROR"), (1, MARKER, "ERROR"),
])
def test_process_and_report_are_both_required(tmp_path, returncode, markers, status):
    (tmp_path / "drc.lyrdb").write_text(report(markers))
    result = drc.record_result(tmp_path, "chip", returncode, {})
    assert result["status"] == status
    assert result["markers"] == markers.count("<item>")
    assert result == json.loads((tmp_path / "result.json").read_text())


@pytest.mark.parametrize("contents", [
    None, "<report-database>", report(top="another_chip"),
    report().replace("<items></items>", ""),
    report().replace("<category><name>M1.a</name></category>", ""),
    report("<item><cell>chip</cell></item>"),
])
def test_missing_partial_or_wrong_report_is_error(tmp_path, contents):
    if contents is not None:
        (tmp_path / "drc.lyrdb").write_text(contents)
    result = drc.record_result(tmp_path, "chip", 0, {})
    assert result["status"] == "ERROR"
    assert result["error"]


def test_input_change_invalidates_even_a_clean_report(tmp_path):
    source = tmp_path / "input.gds"
    source.write_bytes(b"original geometry")
    expected = {source: drc.digest(source)}
    source.write_bytes(b"replacement geometry")
    (tmp_path / "drc.lyrdb").write_text(report())
    result = drc.record_result(tmp_path, "chip", 0, expected)
    assert result["status"] == "ERROR"
    assert "Input changed" in result["error"]


def test_separate_locked_decks_and_explicit_rule_coverage(tmp_path):
    main = tmp_path / "ihp-sg13g2.drc"
    antenna = tmp_path / "rule_decks/antenna.drc"
    density = tmp_path / "rule_decks/density.drc"
    locked = {main, antenna, density}
    selected, switches = drc.deck_options(main, locked, "main", "deep", False)
    assert selected == main
    assert "no_recommended=True" in switches
    selected, switches = drc.deck_options(main, locked, "main", "tiling", True)
    assert "run_mode=tiling" in switches
    assert "no_recommended=False" in switches
    selected, switches = drc.deck_options(main, locked, "density", "deep", False)
    assert selected == density
    assert "density_sanity=True" in switches
    assert "precheck_drc=False" in switches
    selected, switches = drc.deck_options(main, locked, "antenna", "deep", False)
    assert selected == antenna
    assert not any(value.startswith("no_recommended=") for value in switches)


@pytest.mark.parametrize("deck,mode,recommended,include_deck", [
    ("density", "tiling", False, True),
    ("antenna", "deep", True, True),
    ("density", "deep", True, True),
    ("antenna", "deep", False, False),
    ("main", "flat", False, True),
    ("unknown", "deep", False, True),
])
def test_reject_unlocked_or_misrepresented_deck_options(
        tmp_path, deck, mode, recommended, include_deck):
    main = tmp_path / "ihp-sg13g2.drc"
    locked = {main}
    if include_deck:
        locked.add(tmp_path / "rule_decks" / (deck + ".drc"))
    with pytest.raises(ValueError):
        drc.deck_options(main, locked, deck, mode, recommended)
