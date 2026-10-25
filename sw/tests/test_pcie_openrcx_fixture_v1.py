# SPDX-FileCopyrightText: 2026 Hasan Melih Akbulut
# SPDX-License-Identifier: Apache-2.0
"""Finite export contract counterexamples against actual native fixture output."""

from pathlib import Path
import importlib.util
import pytest

ROOT = Path(__file__).resolve().parents[2]
spec = importlib.util.spec_from_file_location(
    "rcx_fixture", ROOT / "scripts/audit_pcie_openrcx_fixture_v1.py"
)
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)
NATIVE = '*SPEF "ieee 1481-1999"\n*DESIGN "nssoc_rcx_wire"\n*DATE "15:29:04 Sunday October 04, 2026"\n*VENDOR "The OpenROAD Project"\n*PROGRAM "OpenROAD"\n*VERSION "dcf36133a369abc8f3c5e5738cd4d82e4903c0e0"\n*DESIGN_FLOW "NAME_SCOPE LOCAL" "PIN_CAP NONE"\n*DIVIDER /\n*DELIMITER :\n*BUS_DELIMITER []\n*T_UNIT 1 NS\n*C_UNIT 1 PF\n*R_UNIT 1 OHM\n*L_UNIT 1 HENRY\n\n*NAME_MAP\n*1 wire\n*2 coupled\n\n*PORTS\nA I\nB O\nC I\nD O\n\n*D_NET *1 0.0172121\n*CONN\n*P B O\n*P A I\n*CAP\n1 B 0.00305109\n2 A 0.00305109\n3 B D 0.0111099\n*RES\n1 A B 44.088 \n*END\n\n*D_NET *2 0.0172121\n*CONN\n*P D O\n*P C I\n*CAP\n1 D 0.00305109\n2 C 0.00305109\n3 B D 0.0111099\n*RES\n1 C D 44.088 \n*END\n'
GEOMETRY = [
    {
        "net": "wire",
        "ports": ["A", "B"],
        "layer": "Metal2",
        "length_um": 100,
        "width_um": 0.2,
    },
    {
        "net": "coupled",
        "ports": ["C", "D"],
        "layer": "Metal2",
        "length_um": 100,
        "width_um": 0.2,
    },
]


def check(tmp_path, text):
    p = tmp_path / "wire.spef"
    p.write_text(text)
    return module.audit(p, GEOMETRY, coupling=True)


def test_actual_native_coupling_export(tmp_path):
    result = check(tmp_path, NATIVE)
    assert result["qualified_rc"] is False
    assert result["unique_coupling_edges"] == 1
    assert result["unique_coupling_pf"] == pytest.approx(0.0111099)
    assert result["nets"]["wire"]["resistance_ohm"] == pytest.approx(44.088)


@pytest.mark.parametrize(
    "before,after",
    [
        ("*R_UNIT 1 OHM", "*R_UNIT 1 KOHM"),
        ("*C_UNIT 1 PF", "*C_UNIT 1 FF"),
        ("*T_UNIT 1 NS", "*T_UNIT 1 PS"),
        ('"PIN_CAP NONE"', '"PIN_CAP INPUT"'),
        ("A I\nB O", "A I\nB I"),
        ("*2 coupled", "*2 wire"),
        ("*D_NET *1 0.0172121", "*D_NET *1 0.0182121"),
        ("1 A B 44.088", "1 A B 51.603"),
        ("1 A B 44.088", "1 A B 0"),
        ("1 A B 44.088", "1 A B nan"),
        ("1 A B 44.088", "1 A B inf"),
        ("1 A B 44.088", "1 A B -44.088"),
        ("1 A B 44.088", "1 A D 44.088"),
        ("2 A 0.00305109", "2 B 0.00305109"),
        ("3 B D 0.0111099", "3 B C 0.0111099"),
        ("3 B D 0.0111099", "3 B A 0.0111099"),
        ("3 B D 0.0111099", "3 B D 0"),
        ("3 B D 0.0111099", "3 B D 0.0121099"),
        ("*P A I", "*P D I"),
        ("*END", "*RES\n*END"),
    ],
)
def test_changed_units_geometry_connectivity_or_charge_rejected(
    tmp_path, before, after
):
    assert before in NATIVE
    with pytest.raises(ValueError):
        check(tmp_path, NATIVE.replace(before, after, 1))


def test_missing_net_and_truncated_output_rejected(tmp_path):
    for text in (NATIVE.split("*D_NET *2")[0], NATIVE.rsplit("*END", 1)[0]):
        with pytest.raises(ValueError):
            check(tmp_path, text)


def test_reciprocity_rejected_even_with_consistent_local_total(tmp_path):
    text = NATIVE.replace("*D_NET *1 0.0172121", "*D_NET *1 0.0182121").replace(
        "3 B D 0.0111099", "3 B D 0.0121099", 1
    )
    with pytest.raises(ValueError, match="reciprocity"):
        check(tmp_path, text)
