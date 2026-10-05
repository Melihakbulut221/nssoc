# SPDX-FileCopyrightText: 2026 Hasan Melih Akbulut
# SPDX-License-Identifier: Apache-2.0
"""Missing public-port observer regression; exact physical sources remain fixed."""

from pathlib import Path
import sys

import pytest

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "scripts"))
import characterize_pcie_vco_v6_feedback_v2 as m


@pytest.fixture(autouse=True)
def exact_public_inputs(monkeypatch):
    monkeypatch.setattr(
        m.previous, "HYBRID", Path(__file__).parent / "fixtures/pcie_vco_v6_feedback_v1"
    )


@pytest.mark.parametrize("vctrl", [0.6, 0.85])
def test_positive_config_circuit_and_every_observation_unchanged(vctrl):
    assert m.config(vctrl) == m.previous.config(vctrl)


def test_actual_disconnected_terminal_still_has_public_voltage_observation():
    before, rows, texts = m.previous.config(fault="disconnect_divider_clock")
    old = m.previous.n.vectors(rows, before["extra_vectors"])
    assert "v(clkn)" not in old  # Preserve the original actual capture failure.
    after, corrected_rows, corrected_texts = m.config(fault="disconnect_divider_clock")
    assert rows == corrected_rows and texts == corrected_texts
    assert after["extra_vectors"] == before["extra_vectors"] + ["v(clkn)"]
    assert {k: v for k, v in before.items() if k != "extra_vectors"} == {
        k: v for k, v in after.items() if k != "extra_vectors"
    }
    names = m.previous.n.vectors(rows, after["extra_vectors"])
    assert len(names) == len(set(names)) == 785
    m.previous.Meter(["time", *names], rows, after)


def test_wrong_modulus_is_not_silently_changed_by_observer_repair():
    assert m.config(fault="wrong_feedback_modulus") == m.previous.config(
        fault="wrong_feedback_modulus"
    )


def test_private_namespace_keeps_physics_resource_and_lifecycle_code_identical():
    assert m._scope is not vars(m.previous)
    for name in (
        "run",
        "run_native",
        "capture",
        "guard",
        "native_limit",
        "deck",
        "measurement",
    ):
        assert m._scope[name].__code__ is getattr(m.previous, name).__code__
    assert m._scope["Meter"] is m.previous.Meter
    assert m._scope["config"] is m.config
    assert m.previous.run.__globals__["config"] is m.previous.config
