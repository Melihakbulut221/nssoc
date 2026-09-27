#!/usr/bin/env python3
# SPDX-FileCopyrightText: 2026 Hasan Melih Akbulut
# SPDX-License-Identifier: Apache-2.0
"""Validate execution coverage of the locked 5e6d592 density deck.

Its seven slit categories always exist; other categories are emitted only for
violations. A constant report-category count cannot establish rule coverage.
Callers must separately pin the upstream deck/parameters and input geometry.
"""
from collections import Counter
from pathlib import Path
import re

from check_ihp_drc import read_report
from check_ihp_drc_partitioned import read_categories


SLITS = tuple("Slt.i_" + metal for metal in ("M1", "M2", "M3", "M4", "M5", "TM1", "TM2"))
RULES = (
    "AFil.g", "AFil.g1", "AFil.g2", "AFil.g3", "GFil.g",
    *(f"M{metal}.{limit}" for metal in range(1, 6) for limit in ("j", "k")),
    *(f"M{metal}Fil.{limit}" for metal in range(1, 6) for limit in ("h", "k")),
    "TM1.c", "TM1.d", "TM2.c", "TM2.d", "LBE.i", *SLITS,
)
BOUNDARY = {"DEN.BND.1", "DEN.BND.2", "DEN.BND.3"}


def validate_density_coverage(report, log, top, returncode):
    """Require all 37 rule execution records without suppressing any marker."""
    text = Path(log).read_text()
    if returncode != 0 or re.search(
        r"\b(?:ERROR|FATAL)\b|std::bad_alloc|std::bad_array_new_length|"
        r"out of memory|cannot allocate memory|segmentation fault|"
        r"terminate called|Traceback \(most recent call last\)|"
        r"Shapes exist outside boundary\.", text, re.IGNORECASE
    ):
        raise ValueError("Density execution or boundary normalization failed")
    executed = re.findall(r"Executing rule ([A-Za-z0-9_.]+)\s*$", text, re.M)
    if executed != list(RULES):
        raise ValueError("Incomplete, duplicate or reordered density rule execution")
    completion = re.findall(
        r"KLayout DRC run for density table completed in [0-9.]+ seconds", text)
    if len(completion) != 1 or text.rfind(completion[0]) < text.rfind("Executing rule"):
        raise ValueError("Missing final density completion record")
    inventory = read_categories(report)
    if not set(SLITS) <= inventory.keys() or not inventory.keys() <= set(RULES) | BOUNDARY:
        raise ValueError("Missing slit or unknown density report category")
    measurement = read_report(report, top)
    counts = Counter({name.strip("'"): count for name, count in measurement["categories"].items()})
    # Native custom categories are created only when an item is emitted.
    if any(counts[name] == 0 for name in inventory.keys() - set(SLITS)):
        raise ValueError("Empty conditional density category")
    return dict(status="FAIL" if measurement["markers"] else "PASS",
                process_returncode=returncode, **measurement,
                executed_rules=executed, executed_rule_count=len(executed),
                category_inventory=inventory)
