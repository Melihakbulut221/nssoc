# SPDX-FileCopyrightText: 2026 Hasan Melih Akbulut
# SPDX-License-Identifier: Apache-2.0
"""A failed density report adds categories; missing execution must still fail."""
from pathlib import Path
import sys
import xml.etree.ElementTree as ET

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "hw/soc/flow"))
import check_ihp_density_coverage as density


@pytest.fixture
def sample(tmp_path):
    report, log = tmp_path / "drc.lyrdb", tmp_path / "run.log"
    root = ET.Element("report-database")
    ET.SubElement(root, "top-cell").text = "chip"
    cats = ET.SubElement(root, "categories")
    for name in density.SLITS:
        cat = ET.SubElement(cats, "category")
        ET.SubElement(cat, "name").text = name
    cells = ET.SubElement(root, "cells")
    ET.SubElement(ET.SubElement(cells, "cell"), "name").text = "chip"
    ET.SubElement(root, "items")
    log.write_text("\n".join("Executing rule " + name for name in density.RULES)
                   + "\nKLayout DRC run for density table completed in 1.0 seconds\n")
    ET.ElementTree(root).write(report)
    return report, log, root


def check(sample, code=0):
    report, log, root = sample
    ET.ElementTree(root).write(report)
    return density.validate_density_coverage(report, log, "chip", code)


def test_clean_report_has_seven_categories_but_37_executed_rules(sample):
    result = check(sample)
    assert (result["status"], result["category_count"], result["executed_rule_count"]) == ("PASS", 7, 37)


@pytest.mark.parametrize("name", ["AFil.g2", "M2.j", "M5Fil.h", "TM2.c", "DEN.BND.1"])
def test_conditional_violation_is_fail_not_controller_error(sample, name):
    root = sample[2]
    cat = ET.SubElement(root.find("categories"), "category")
    ET.SubElement(cat, "name").text = name
    item = ET.SubElement(root.find("items"), "item")
    ET.SubElement(item, "category").text = "'" + name + "'"
    ET.SubElement(item, "cell").text = "chip"
    ET.SubElement(item, "visited").text = "true"
    result = check(sample)
    assert (result["status"], result["markers"], result["category_count"]) == ("FAIL", 1, 8)


@pytest.mark.parametrize("defect", ["missing", "duplicate", "reorder", "completion", "early_completion", "error", "boundary"])
def test_incomplete_or_invalid_execution_is_rejected(sample, defect):
    log = sample[1]
    text = log.read_text()
    if defect == "missing": text = text.replace("Executing rule M2Fil.h\n", "")
    elif defect == "duplicate": text = "Executing rule AFil.g\n" + text
    elif defect == "reorder": text = text.replace("Executing rule AFil.g\nExecuting rule AFil.g1", "Executing rule AFil.g1\nExecuting rule AFil.g")
    elif defect == "completion": text = text[:text.index("KLayout DRC")]
    elif defect == "early_completion": text = text.splitlines()[-1] + "\n" + "\n".join(text.splitlines()[:-1])
    elif defect == "error": text += "ERROR: worker failed\n"
    elif defect == "boundary": text += "Shapes exist outside boundary.\n"
    log.write_text(text)
    with pytest.raises(ValueError): check(sample)


@pytest.mark.parametrize("code", [1, 124, -9])
def test_nonzero_exit_cannot_pass(sample, code):
    with pytest.raises(ValueError): check(sample, code)


@pytest.mark.parametrize("defect", ["missing_slit", "unknown", "empty_conditional", "unknown_marker"])
def test_invalid_report_is_rejected(sample, defect):
    root = sample[2]
    cats = root.find("categories")
    if defect == "missing_slit": cats.remove(cats[0])
    elif defect in ("unknown", "empty_conditional"):
        ET.SubElement(ET.SubElement(cats, "category"), "name").text = "bogus" if defect == "unknown" else "M2.j"
    else:
        item = ET.SubElement(root.find("items"), "item")
        ET.SubElement(item, "category").text = "'bogus'"
        ET.SubElement(item, "cell").text = "chip"
    with pytest.raises(ValueError): check(sample)
