#!/usr/bin/env python3
# SPDX-FileCopyrightText: 2026 Hasan Melih Akbulut
# SPDX-License-Identifier: Apache-2.0
"""Check ngspice 42 completion, retaining explicitly recovered startup warnings.

The caller must separately validate waveform time coverage, values, stimuli,
models and any nondefault solver options. This does not qualify circuit timing.
"""
import re


def check(text, returncode, waveform_rows):
    if returncode != 0:
        raise ValueError(f"Simulator process failed: {returncode}")
    if type(waveform_rows) is not int or waveform_rows < 2:
        raise ValueError("Invalid waveform row count")
    lines = [line.strip() for line in text.splitlines() if line.strip()]
    if not lines or lines[-1] != "ngspice-42 done":
        raise ValueError("Missing supported simulator completion footer")
    rows = [i for i, line in enumerate(lines) if line.startswith("No. of Data Rows")]
    if len(rows) != 1 or not re.fullmatch(
            rf"No\. of Data Rows\s*:\s*{waveform_rows}", lines[rows[0]]):
        raise ValueError("Missing or inconsistent simulator row count")
    if rows[0] != len(lines) - 2:
        raise ValueError("Unexpected output after final data rows")
    starts = [i for i, s in enumerate(lines) if s == "Note: Starting dynamic gmin stepping"]
    ends = [i for i, s in enumerate(lines) if s == "Note: Dynamic gmin stepping completed"]
    initial = [i for i, s in enumerate(lines) if s == "Initial Transient Solution"]
    if len(initial) != 1 or initial[0] >= rows[0]:
        raise ValueError("Missing or repeated initial transient solution")
    if starts or ends:
        if len(starts) != 1 or len(ends) != 1 or not starts[0] < ends[0] < initial[0]:
            raise ValueError("Incomplete or misplaced dynamic gmin recovery")
    recovered = []
    for i, line in enumerate(lines):
        if re.match(r"Warning:\s+singular matrix:\s+check node \S+$", line):
            if not starts or not i < starts[0]:
                raise ValueError("Unrecovered or late singular matrix warning")
            recovered.append(line)
        elif re.search(r"warning:|error:|fatal|aborted|unknown model|timestep too small|"
                       r"out of memory|stepping failed|simulation interrupted", line, re.I):
            raise ValueError("Unresolved simulator diagnostic: " + line)
    if len(recovered) > 1:
        raise ValueError("Unexpected repeated singular matrix warnings")
    return {
        "status": "PASS_TRANSIENT_EXECUTION_ONLY",
        "waveform_rows": waveform_rows,
        "dynamic_gmin_recovered": bool(ends),
        "recovered_startup_warnings": recovered,
        "timing_accepted": False,
        "manufacturing_approval": False,
    }
