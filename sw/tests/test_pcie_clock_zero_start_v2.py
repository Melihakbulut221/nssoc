# SPDX-FileCopyrightText: 2026 Hasan Melih Akbulut
# SPDX-License-Identifier: Apache-2.0
"""The VCO startup revision may not change physical sources or device equations."""

from pathlib import Path
import re
import sys

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "scripts"))
import diagnose_pcie_clock_zero_start_v2 as new  # noqa: E402


def original():
    return new.old.deck(
        new.old.cases()[0],
        Path("/models"),
        [Path("/r3.osdi"), Path("/psp.osdi"), Path("/pspnqs.osdi")],
    )


def test_current_frozen_source_and_circuit():
    assert new.old.sha(Path(new.old.__file__)) == new.METHOD_SHA
    assert new.old.sha(new.old.CIRCUIT) == new.CIRCUIT_SHA
    assert new.old.sha(Path(new.startup.__file__)) == new.STARTUP_SHA


def test_all_original_physical_statements_and_transient_remain_exact():
    before = original()
    after = new.transform(before)
    for prefix in (
        "VDD ",
        "VCTRL ",
        "XOSC ",
        "CLOAD",
        ".options",
        ".include",
        ".lib",
        ".temp",
        "tran ",
        "save ",
        "wrdata wave.dat",
    ):
        assert [line for line in before.splitlines() if line.startswith(prefix)] == [
            line for line in after.splitlines() if line.startswith(prefix)
        ]
    assert len(re.findall(r"^alter @q\.", after, re.M)) == 18
    assert len(re.findall(r"^op$", after, re.M)) == 1
    assert not re.search(r"(?im)^\.ic\b|\buic\b|^\.nodeset", after)


@pytest.mark.parametrize(
    "change",
    [
        lambda s: s.replace("PWL(0 0", "PWL(0 1", 1),
        lambda s: s.replace("reltol=1e-4", "reltol=1e-2"),
        lambda s: s + "\n.ic v(clkp)=1\n",
        lambda s: s.replace("tran ", "tran uic ", 1),
        lambda s: s + "\nalter @q.foo[off]=1\n",
    ],
)
def test_changed_initial_conditions_fail_closed(change):
    with pytest.raises(ValueError):
        new.transform(change(original()))


def flags(value="1"):
    return "".join(
        f"NSSOC_CLOCK_FLAG_BEGIN {name}\n VBIC: native\n device {name:.21}\n off {value}\nNSSOC_CLOCK_FLAG_END\n"
        for name in new.identities()
    )


def test_exact_native_flag_readback():
    assert len(new.read_flags(flags())) == 18


@pytest.mark.parametrize(
    "mutate",
    [
        lambda t: t.replace("off 1", "off 0", 1),
        lambda t: t + t,
        lambda t: t.replace("NSSOC_CLOCK_FLAG_BEGIN", "NSSOC_FLAG_BEGIN", 1),
        lambda t: t.replace(
            "device q.xosc.xp0.qnpn13g2", "device q.xosc.xn0.qnpn13g2", 1
        ),
    ],
)
def test_wrong_or_missing_flag_rejected(mutate):
    with pytest.raises(ValueError):
        new.read_flags(mutate(flags()))


def test_no_original_corner_or_negative_control_removed():
    cases = new.old.cases(False)
    assert len(cases) == 72
    assert len([c for c in cases if c["name"] in new.PILOT]) == 9
    assert {c["fault"] for c in cases if c["fault"]} == {
        "no_bias",
        "no_feedback",
        "same_clock",
        "overload",
    }
    assert new.old.LIMITS["min_vce_v"] == 0.4
