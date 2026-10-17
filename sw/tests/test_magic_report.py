# SPDX-FileCopyrightText: 2026 Hasan Melih Akbulut
# SPDX-License-Identifier: Apache-2.0
"""Reject incomplete physical evidence and preserve negative-coordinate boxes."""
import importlib.util
from pathlib import Path

import pytest

SPEC = importlib.util.spec_from_file_location(
    "classify_magic_drc", Path(__file__).resolve().parents[2] /
    "scripts/classify_magic_drc.py")
MAGIC = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(MAGIC)


def parse(tmp_path, text):
    report = tmp_path / "drc.magic.rpt"
    report.write_text(text)
    return MAGIC.parse_report(report)


def test_signed_boxes_keep_their_rule(tmp_path):
    got = parse(tmp_path, "soc_top\n---\nSpacing (Rule 1)\n---\n"
                " -0.225um -1.000um 0.000um 2.000um\n"
                "---\nEnclosure (Rule 2)\n---\n"
                " 10.000um 20.000um 11.000um 21.000um\n"
                "---\n[INFO] COUNT: 2\n[INFO] Should be divided by 3 or 4\n")
    assert got == [("Spacing (Rule 1)", -.225, -1., 0., 2.),
                   ("Enclosure (Rule 2)", 10., 20., 11., 21.)]


def test_completed_zero_report(tmp_path):
    assert parse(tmp_path, "soc_top\n---\n[INFO] COUNT: 0\n") == []


@pytest.mark.parametrize("text", [
    "", "soc_top\n---\n",  # Magic opens the report before doing the work.
    "soc_top\n---\nRule\n 1um 2um 3um 4um\n",  # Interrupted write.
    "soc_top\n---\nRule\n 1um 2um 3um 4um\n[INFO] COUNT: 2\n",
    "soc_top\n---\nRule\n 1um 2um 3um\n[INFO] COUNT: 0\n",
    "soc_top\n---\nRule\n 3um 2um 1um 4um\n[INFO] COUNT: 1\n",
    "soc_top\n---\n[INFO] COUNT: 0\n[INFO] COUNT: 0\n",
    "soc_top\n---\nRule\n[INFO] COUNT: 1\n 1um 2um 3um 4um\n",
])
def test_incomplete_or_corrupt_report_rejected(tmp_path, text):
    with pytest.raises(ValueError):
        parse(tmp_path, text)
