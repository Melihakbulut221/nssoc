# SPDX-FileCopyrightText: 2026 Hasan Melih Akbulut
# SPDX-License-Identifier: Apache-2.0
"""Signed current convention controls from independent actual native clamp values."""

from pathlib import Path
import json
import sys
import numpy as np
import pytest

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "scripts"))
import characterize_pcie_pll_loop_v2 as m


@pytest.mark.parametrize(
    "p,n,clamp",
    [
        (6.820837044655643e-6, 1.3221966264011225e-5, -6.401100754053405e-6),
        (1.6347020074125096e-5, 6.664340642130337e-6, 9.682698482614007e-6),
    ],
)
def test_pinned_native_channel_means_match_independent_terminal_clamp(p, n, clamp):
    data = {
        "i(@n.probe.xpenable.nsg13_hv_pmos[ids])": np.array([p]),
        "i(@n.probe.xnenable.nsg13_hv_nmos[ids])": np.array([n]),
    }
    assert abs(m.channel_pump(data, "probe")[0] - clamp) < 50e-12
    assert abs(-p - n - clamp) > 1e-6


def test_frozen_v1_changed_source_rejected(monkeypatch):
    original = m.n.common.sha
    monkeypatch.setattr(
        m.n.common,
        "sha",
        lambda p: "0" * 64 if str(p) == str(m.base.__file__) else original(p),
    )
    with pytest.raises(AssertionError):
        m.verify()


def test_existing_loop_circuit_and_limits_stay_frozen():
    m.verify()
    c = m.base.config()
    assert c["step_s"] == 5e-12 and c["stop_s"] == 34e-9
    assert m.n is m.base.n
    assert "VCTRL" not in "\n".join(c["fixture"])


@pytest.mark.parametrize("fault", ["remove_source_inventory", "change_status"])
def test_mutated_native_receipt_rejected_before_inventory_trust(tmp_path, fault):
    original = {"status": "FAIL_NATIVE_FINITE_EXPERIMENT", "inputs": {"source": "pin"}}
    path = tmp_path / "result.json"
    path.write_text(json.dumps(original))
    expected = m.n.common.sha(path)
    if fault == "remove_source_inventory":
        original["inputs"] = {}
    else:
        original["status"] = "PASS_NATIVE_FINITE_EXPERIMENT"
    path.write_text(json.dumps(original))
    with pytest.raises(AssertionError):
        m.replay(tmp_path, tmp_path / "new.json", expected_result_sha=expected)
    assert not (tmp_path / "new.json").exists()
