# SPDX-FileCopyrightText: 2026 Hasan Melih Akbulut
# SPDX-License-Identifier: Apache-2.0
"""Actual V1/V2/V3/V4/V5 forwarding witnesses and counterexamples."""
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import pytest

ROOT = Path(__file__).resolve().parents[2]
SOURCE = ROOT / "hw/soc/rtl/pcie/soc_pcie_gen3_dllp_consumer_v5.v"
NONADJ = "nonadjacent_same_ids_and_zero_keep_gaps"
FAULTS = [
    ("no_forward", "if(body_write[previous] &&", "if(1'b0 &&", NONADJ),
    ("only_immediate_forward", "if(body_write[previous] &&", "if(previous==body_lane-1 && body_write[previous] &&", NONADJ),
    ("first_writer_scatter", "for(scatter_lane=0;scatter_lane<4;scatter_lane=scatter_lane+1)",
     "for(scatter_lane=3;scatter_lane>=0;scatter_lane=scatter_lane-1)", NONADJ),
    ("earliest_forward", "for(previous=0;previous<body_lane;previous=previous+1)",
     "for(previous=body_lane-1;previous>=0;previous=previous-1)", "latest_earlier_same_id_for_four_lane_tlp"),
    ("sticky_error_lost", "}=incoming_context;", "}=incoming_context;local_entry_error=0;", "prior_lane_error_survives_later_valid_same_id"),
]


def run(tmp, mutation=None, case=None):
    cmd = [sys.executable, str(ROOT / "scripts/check_pcie_gen3_dllp_consumer_forwarding_v5.py"),
           "--out", str(tmp / "capture"), "--iverilog-dir", str(Path(shutil.which("iverilog")).parent)]
    if mutation:
        before, after = mutation
        text = SOURCE.read_text()
        assert text.count(before) == 1
        p = tmp / "mutant.v"
        p.write_text(text.replace(before, after))
        cmd += ["--rtl", str(p)]
    if case:
        cmd += ["--test", case]
    with (tmp / "launch.log").open("w") as log:
        p = subprocess.run(cmd, cwd=ROOT, env={**os.environ, "PYTHONDONTWRITEBYTECODE": "1"}, stdout=log, stderr=subprocess.STDOUT)
    return p, json.loads((tmp / "capture/result.json").read_text()), (tmp / "capture/simulation.log").read_text()


def test_actual_three_forwarding_witnesses(tmp_path):
    p, r, log = run(tmp_path)
    assert p.returncode == 0 and r["tests"] == dict(passed=3, failed=0, skipped=0)
    assert "Public v1/v2/v3/v4/v5 mismatch" not in log


@pytest.mark.parametrize("name,before,after,case", FAULTS, ids=[x[0] for x in FAULTS])
def test_actual_forwarding_and_scatter_faults_rejected(tmp_path, name, before, after, case):
    p, r, log = run(tmp_path, (before, after), case)
    assert p.returncode != 0 and r["status"] == "FAIL"
    assert "Public v1/v2/v3/v4/v5 mismatch" in log, "Compile or unrelated assertion is not equivalence rejection"
