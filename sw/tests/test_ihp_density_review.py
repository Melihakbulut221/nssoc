# SPDX-FileCopyrightText: 2026 Hasan Melih Akbulut
# SPDX-License-Identifier: Apache-2.0
"""Fail-closed controls against actual native zero-marker density evidence."""
import importlib.util
from pathlib import Path
import xml.etree.ElementTree as ET

import pytest

ROOT = Path(__file__).resolve().parents[2]
SPEC = importlib.util.spec_from_file_location("density_review", ROOT / "scripts/review_ihp_density.py")
review = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(review)
FIXTURE = ROOT / "sw/tests/fixtures/ihp_density_zero"
LOG = (FIXTURE / "run.log").read_text()
REPORT = (FIXTURE / "drc.lyrdb").read_bytes()


def test_complete_native_report_and_all_executed_rules():
    result = review.validate_report(LOG, REPORT, "soc_top")
    assert result["executed_rule_count"] == 37
    assert len(result["report_categories"]) == 7
    assert result["markers"] == 0
    assert result["global_density_percent"]["Metal2"] == 35.94


@pytest.mark.parametrize("needle", ["Executing rule AFil.g2", "Executing rule M3Fil.h",
                                    "Executing rule Slt.i_TM2", "KLayout DRC run for density table completed"])
def test_missing_execution_or_completion_rejected(needle):
    text = "\n".join(line for line in LOG.splitlines() if needle not in line)
    with pytest.raises(ValueError):
        review.validate_report(text, REPORT, "soc_top")


@pytest.mark.parametrize("extra", ["Executing rule AFil.g2\n", "Executing rule fake.rule\n",
                                   "ERROR: lost geometry\n"])
def test_duplicate_unknown_rule_and_native_error_rejected(extra):
    with pytest.raises(ValueError):
        review.validate_report(LOG + extra, REPORT, "soc_top")


@pytest.mark.parametrize("mutation", ["marker", "top", "category", "items"])
def test_report_corruptions_rejected(mutation):
    tree = ET.fromstring(REPORT)
    if mutation == "marker":
        ET.SubElement(tree.find("items"), "item")
    elif mutation == "top":
        tree.find("top-cell").text = "different_chip"
    elif mutation == "category":
        tree.find(".//category/name").text = "wrong_rule"
    else:
        tree.remove(tree.find("items"))
    with pytest.raises(ValueError):
        review.validate_report(LOG, ET.tostring(tree), "soc_top")


def test_global_summary_regression_rejected_even_with_zero_markers():
    assert "35.94%" in LOG
    with pytest.raises(ValueError):
        review.validate_report(LOG.replace("35.94%", "34.00%"), REPORT, "soc_top")
