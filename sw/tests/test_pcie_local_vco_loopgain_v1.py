# SPDX-FileCopyrightText: 2026 Hasan Melih Akbulut
# SPDX-License-Identifier: Apache-2.0
"""Actual diagnostic boundaries, DC safety, and native AC table failures."""

import math
from pathlib import Path
import sys

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "scripts"))
import diagnose_pcie_local_vco_loopgain_v1 as m

IDS = {"P0": 1, "N0": 2, "P1": 3, "N1": 4}


def node(name, term):
    return name + "_" + term


SOURCE = "\n".join(
    [
        ".subckt test AVDD AVSS BODY",
        "XD0001 P0_C P0_B P0_E BODY npn13G2 Nx=2",
        "XD0002 N0_C N0_B N0_E BODY npn13G2 Nx=2",
        "XD0003 P1_C P1_B P1_E BODY npn13G2 Nx=2",
        "XD0004 N1_C N1_B N1_E BODY npn13G2 Nx=2",
        "R1 P0_C P1_B 43.1",
        "C1 P0_C N0_C 1.1e-14",
        ".ends test",
        "",
    ]
)


@pytest.mark.parametrize("kind", m.KINDS)
def test_real_break_recovers_exact_original_intrinsic_body_and_wire_graph(kind):
    actual, changes = m.topology(SOURCE, IDS, node, kind)
    m.verify_topology(SOURCE, actual, changes, kind, node)
    if kind == "intact":
        assert not changes
    else:
        assert [c["device"] for c in changes] == ["P0", "N0"]
        assert "R1 P0_C P1_B 43.1" in actual and "C1 P0_C N0_C 1.1e-14" in actual
        assert actual.count(" BODY npn13G2 Nx=2") == 4
        assert len(changes) == 2


@pytest.mark.parametrize(
    "old,new",
    [
        ("43.1", "42.1"),
        ("1.1e-14", "1.2e-14"),
        (" BODY npn13G2", " AVSS npn13G2"),
        ("XD0003 P1_C", "XD0003 P0_C"),
        ("Nx=2", "Nx=4"),
        ("VDIAG_P diag_P_drive 0 DC 0 AC 0.5", "VDIAG_P diag_P_drive 0 DC 0.1 AC 0.5"),
        ("LDIAG_P P0_B diag_P_base 1", "LDIAG_P P0_B diag_P_base 10"),
        ("CDIAG_N diag_N_base diag_N_drive", "CDIAG_N diag_N_base BODY"),
    ],
)
def test_unchanged_devices_wires_bodies_and_explicit_boundary_are_enforced(old, new):
    actual, changes = m.topology(SOURCE, IDS, node, "break")
    assert old in actual
    with pytest.raises(ValueError):
        m.verify_topology(SOURCE, actual.replace(old, new, 1), changes, "break", node)


def test_missing_and_extra_native_device_reject():
    actual, changes = m.topology(SOURCE, IDS, node, "break")
    for bad in [
        actual.replace("R1 P0_C P1_B 43.1\n", ""),
        actual.replace(".ends", "RX P0_C N0_C 1\n.ends"),
    ]:
        with pytest.raises(ValueError):
            m.verify_topology(SOURCE, bad, changes, "break", node)


def write_ac(path, fault=None):
    lines = ["frequency v(p) v(p)"]
    for i in range(289):
        f = 1e7 * 4000 ** (i / 288)
        if fault == "off_grid" and i == 100:
            f *= 1.00001
        if fault == "backward" and i == 100:
            f = 1e7
        if fault == "missing" and i == 100:
            continue
        v = "nan" if fault == "nan" and i == 50 else "1"
        lines.append(f"{f:.17g} {v} 0")
    if fault == "column":
        lines[0] = "frequency v(wrong) v(wrong)"
    path.write_text("\n".join(lines) + "\n")


def test_native_endpoint_roundoff_keeps_all289_grid_points(tmp_path):
    p = tmp_path / "ac.dat"
    write_ac(p)
    text = p.read_text().splitlines()
    text[-1] = "40000000000.000595 1 0"
    p.write_text("\n".join(text) + "\n")
    assert len(m.read_table(p, ["v(p)"], True)) == 289


@pytest.mark.parametrize("fault", ["off_grid", "backward", "missing", "nan", "column"])
def test_actual_grid_nonfinite_incomplete_and_wrong_signal_fail(tmp_path, fault):
    p = tmp_path / "ac.dat"
    write_ac(p, fault)
    with pytest.raises(ValueError):
        m.read_table(p, ["v(p)"], True)


def contract():
    return dict(
        hbts=[
            dict(id=i, Nx=2, C=f"v(c{i})", E=f"v(e{i})", current=f"i(q{i})")
            for i in range(30)
        ]
    )


def test_dc_all_thirty_devices_not_average():
    c = contract()
    v = {
        k: value
        for d in c["hbts"]
        for k, value in [(d["C"], 1.2), (d["E"], 0.4), (d["current"], 0.004)]
    }
    assert m.op_screen(v, c)["all30_dc_bounds_pass"]
    for key, value in [("v(c29)", 0.799), ("v(c29)", 2.001), ("i(q29)", 0.00601)]:
        bad = dict(v)
        bad[key] = value
        r = m.op_screen(bad, c)
        assert not r["all30_dc_bounds_pass"]
        assert len([x for x in r["hbts"] if not x["pass_bounds"]]) == 1
    with pytest.raises(ValueError, match="census"):
        m.op_screen(v, dict(hbts=c["hbts"][:-1]))


def test_actual_complex_return_and_conditional_zero_phase_interpolation():
    rows = []
    for freq, imag in [(7e9, 0.2), (8e9, -0.2)]:
        values = [0j] * 20
        values[0] = 1 + 1j * imag
        values[3] = -1 - 1j * imag
        values[-2] = 0.5
        values[-1] = -0.5
        values[6] = values[12] = 0.1
        values[9] = values[15] = -0.1
        rows.append((freq, values))
    r = m.ac_measure(rows)
    x = r["zero_imaginary_crossings"][0]
    assert (
        x["frequency_hz"] == 7.5e9
        and x["return_real"] == 2
        and x["positive_feedback_phase"]
    )
    assert r["conditional_only"]
    assert math.isclose(r["samples"][0]["gain"], abs(2 + 0.4j))
    rows[0][1][-2] = 0
    rows[0][1][-1] = 0
    with pytest.raises(ValueError, match="drive collapsed"):
        m.ac_measure(rows)
