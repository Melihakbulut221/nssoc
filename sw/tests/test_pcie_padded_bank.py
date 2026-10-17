# SPDX-FileCopyrightText: 2026 Hasan Melih Akbulut
# SPDX-License-Identifier: Apache-2.0
"""Literal bank preservation, actual substrate contract and targeted physical faults."""

from pathlib import Path
import sys
import pytest

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "hw/soc/flow"))
import make_pcie_analog_bank as bank
import make_pcie_rx_cell_v2 as rx
import make_pcie_padded_bank as make
import check_pcie_padded_bank as check
from test_pcie_analog_bank import tx_reference


@pytest.fixture
def original():
    return bank.reference(
        tx_reference(),
        rx.physical_reference(
            (ROOT / "hw/soc/analog/pcie/rx_hbt_rsil_v2.spice").read_text()
        ),
    )


def test_all_original_devices_preserved_with_only_explicit_substrate_grounding(
    original,
):
    new = make.reference(original)
    oldlines = [l.split() for l in original.splitlines() if l.startswith(("Q", "R"))]
    newlines = [l.split() for l in new.splitlines() if l.startswith(("Q", "R"))]
    assert len(newlines) == len(oldlines) == 120
    for old, row in zip(oldlines, newlines):
        assert row == ["AVSS" if x == "BULK" else x for x in old]
    assert new.count("SUB AVSS ptap1 A=4p P=8u") == 64
    header = next(l for l in new.splitlines() if l.startswith(".subckt"))
    assert header.split()[1:] == [make.TOP, *bank.PORTS]
    assert "BULK" not in " ".join(" ".join(x) for x in newlines)


def test_thirtytwo_diodes_really_bind_sixteen_serial_nets(original):
    rows = [
        l.split() for l in make.reference(original).splitlines() if l.startswith("D")
    ]
    assert len(rows) == 32 and len({r[0] for r in rows}) == 32
    expected = {
        f"L{i}_{k}_{'OUT' if k == 'TX' else 'IN'}{p}"
        for i in range(4)
        for k in ("TX", "RX")
        for p in ("P", "N")
    }
    assert {r[2] for r in rows} == expected
    for n in expected:
        assert sorted((r[1], r[3], r[4], r[5]) for r in rows if r[2] == n) == [
            ("AVDD", "AVSS", "diodevdd_2kv", "m=1"),
            ("AVDD", "AVSS", "diodevss_2kv", "m=1"),
        ]


@pytest.mark.parametrize("args", [(4, "TX", "P"), (0, "RX", "X"), (0, "ADC", "P")])
def test_unknown_serial_branch_rejected(args):
    with pytest.raises(ValueError):
        make.serial_net(*args)


@pytest.mark.parametrize("fault", ["wrong_lane", "missing_tap", "wrong_diode"])
def test_reference_fault_binds_exactly_one_original_device(original, fault):
    text = make.reference(original)
    wrong = check.fault_reference(text, fault)
    assert wrong != text
    with pytest.raises(ValueError):
        check.fault_reference(wrong, fault)
    assert ".subckt " + make.TOP in wrong


@pytest.mark.parametrize(
    "fault", ["physical_offgrid", "physical_rail_short", "physical_bulk_short"]
)
def test_real_geometry_mutation_not_schematic_waiver(fault):
    code = check.mutation("/source.gds", "/wrong.gds", fault, {})
    assert "l.read('/source.gds')" in code and "l.write('/wrong.gds')" in code
    assert (
        "c.shapes" in code and "connect_global" not in code and "schematic" not in code
    )


def test_serial_open_binds_one_specific_actual_parent_via():
    v = dict(
        net="L2_RX_INP", bottom="TopMetal1", top="TopMetal2", center_um=[280.0, 1025.0]
    )
    code = check.mutation("/a", "/b", "physical_serial_open", dict(vias=[v]))
    assert "pya.DPoint(280.0,1025.0)" in code and "matches[0].delete()" in code
    for rows in ([], [v, v]):
        with pytest.raises(ValueError):
            check.mutation("/a", "/b", "physical_serial_open", dict(vias=rows))


def test_parent_contract_rejects_missing_original_device_or_port(original):
    with pytest.raises(ValueError):
        make.reference(original.replace(" SUB\n", "\n", 1))
    line = next(l for l in original.splitlines() if l.startswith("R0TX_TAP0"))
    with pytest.raises(ValueError):
        make.reference(original.replace(line + "\n", ""))


def test_unknown_mutation_rejected(original):
    with pytest.raises(ValueError):
        check.mutation("/a", "/b", "waive", {})
    with pytest.raises(ValueError):
        check.fault_reference(make.reference(original), "waive")
