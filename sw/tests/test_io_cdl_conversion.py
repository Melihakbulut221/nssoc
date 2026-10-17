# SPDX-FileCopyrightText: 2026 Hasan Melih Akbulut
# SPDX-License-Identifier: Apache-2.0
"""I/O dialect conversion preserves devices and rejects ambiguous tap calls."""
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "hw/soc/flow"))
from normalize_io_cdl import normalize  # noqa: E402

TAP = "XR2 vss sub! / ptap1 r=22.472 A=24.01p Perim=19.6u w=4.9u l=4.9u\n"
RESISTOR = ("RR0 a b 6.768K $SUB=iovdd $[res_rppd] m=1 l=12.9u w=500n\n"
            "+ ps=180n b=0\n")


def test_conversion_retains_nodes_parameters_and_continuations():
    text = ".PARAM\n.SUBCKT pad a b\n" + TAP + RESISTOR + ".ENDS\n"
    result, changes = normalize(text)
    expected = text.replace(".PARAM\n", "").replace("XR2", "R2")
    expected = expected.replace("$[res_rppd]", "$[rppd]")
    assert result == expected
    assert [x["reason"] for x in changes] == ["empty_parameter_declaration",
                                             "native_tap_device_prefix",
                                             "native_rppd_model_spelling"]
    assert normalize(result) == (result, [])


@pytest.mark.parametrize("broken", [
    TAP.replace("ptap1", "unknown"),
    TAP.replace("XR2", "XM2"),
    TAP.replace("l=4.9u", "w=4.9u"),
    TAP.replace("A=24.01p", "A=nan"),
    TAP.replace("w=4.9u", "w={process}"),
    TAP.replace("/ ptap1", "extra / ptap1"),
    RESISTOR.replace("$SUB=iovdd", "$SUB="),
])
def test_unsupported_dialect_fails_closed(broken):
    with pytest.raises(ValueError):
        normalize(broken)


def test_unrelated_devices_comments_and_real_parameters_are_not_rewritten():
    text = (".PARAM value=1\n* resistor model $[res_rppd]\n"
            "X1 a b / inverter\nM1 d g s b sg13_lv_nmos w=1u l=130n\n")
    assert normalize(text) == (text, [])
