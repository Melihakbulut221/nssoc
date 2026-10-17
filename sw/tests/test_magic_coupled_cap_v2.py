# SPDX-FileCopyrightText: 2026 Hasan Melih Akbulut
# SPDX-License-Identifier: Apache-2.0
"""The v2 matrix contract rejects coupling loss and hidden diagonal fitting."""

import hashlib
from pathlib import Path
import sys

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "scripts"))
import check_magic_coupled_cap_v2 as check  # noqa: E402
import patch_magic_coupled_cap_v2 as patcher  # noqa: E402


@pytest.fixture
def files(tmp_path):
    ext = '''version 8.3
tech ihp-sg13g2
style ngspice()
scale 1000 1 0.5
port "A" 1 0 0 0 4 m7
port "B" 2 20 0 20 4 m7
port "C" 3 0 6 0 10 m7
port "D" 4 20 6 20 10 m7
node "B" 0 100 20 0 m7 0 0
equiv "B" "A"
node "D" 0 200 20 6 m7 0 0
equiv "D" "C"
cap "B" "D" 50
substrate "sub!" 0 0 -100 -100 space 0 0
'''
    replacement = '''scale 1000 1 0.5
subcap "B" -100
subcap "D" -200
rnode "B" 0 50 20 0 0
rnode "A" 0 50 0 0 0
rnode "D" 0 100 20 6 0
rnode "C" 0 100 0 6 0
resist "A" "B" 0.05
resist "C" "D" 0.05
'''
    exported = '''.subckt tiny A B C D
R0 A B 0.05
R1 C D 0.05
C0 B D 5e-17
C1 A sub 5e-17
C2 B sub 5e-17
C3 C sub 1e-16
C4 D sub 1e-16
.ends
'''
    log = "NSSOC_V2_INTRINSIC_DISTRIBUTION B total=150 intrinsic=100\nNSSOC_V2_INTRINSIC_DISTRIBUTION D total=250 intrinsic=200\n"
    paths = [tmp_path / name for name in ("tiny.ext", "tiny.res.ext", "tiny.spice", "native.log", "baseline.ext", "baseline.spice")]
    for p, s in zip(paths, (ext, replacement, exported, log, ext, exported)):
        p.write_text(s)
    return paths


def test_full_mutual_matrix_pass(files):
    result = check.audit(*files)
    assert result["expected_matrix_af"] == {"B": {"B": 150, "D": -50}, "D": {"B": -50, "D": 250}}
    assert result["qualified_pex"] is False
    assert result["dynamic_rf_or_reduction_accuracy_validated"] is False


@pytest.mark.parametrize("index,old,new,reason", [
    (2, "C0 B D 5e-17\n", "", "mutual"),
    (2, "C0 B D 5e-17", "C0 B D 6e-17", "mutual"),
    (2, "C0 B D 5e-17", "C0 A D 5e-17", "anchor"),
    (2, "C0 B D 5e-17", "C0 B A 5e-17", "mutual"),
    (2, "C1 A sub 5e-17", "C1 A sub 7.5e-17", "Per-node"),
    (2, "C4 D sub 1e-16", "C3 D sub 1e-16", "Duplicate"),
    (2, ".ends", "", "Missing"),
    (2, "R0 A B 0.05", "R0 A B 0.06", "resistance"),
    (2, "tiny A B C D", "tiny A B D C", "Port"),
    (1, '"D" 0 100', '"D" 0 -1', "ground"),
    (1, '"D" 0 100', '"D" 0 nan', "ground"),
    (1, 'subcap "B" -100', 'subcap "B" -150', "retirement"),
    (1, 'subcap "B" -100', '', "exactly one"),
    (1, 'subcap "B" -100', 'killnode "B"', "Unsupported"),
    (1, 'scale 1000 1', 'scale 1000 2', "cscale"),
    (0, 'scale 1000 1', 'scale 1000 2', "cscale"),
    (0, 'cap "B" "D" 50', 'cap "B" "D" 49', "Original"),
    (0, 'node "B" 0 100', 'node "B" 0 101', "Original"),
    (0, 'equiv "B" "A"', 'equiv "A" "B"', "alias"),
    (3, 'D total=250', 'D total=200', "component"),
    (3, 'D total=250 intrinsic=200', 'D total=250 intrinsic=250', "component"),
    (3, 'NSSOC_V2_INTRINSIC_DISTRIBUTION D total=250 intrinsic=200\n', '', "branch"),
    (3, 'NSSOC_V2_INTRINSIC_DISTRIBUTION D total=250 intrinsic=200\n', 'NSSOC_V2_INTRINSIC_DISTRIBUTION B total=150 intrinsic=100\n', "branch"),
    (3, 'D total=250', 'D total=nan', "component"),
])
def test_mutations_rejected(files, index, old, new, reason):
    assert old in files[index].read_text()
    files[index].write_text(files[index].read_text().replace(old, new))
    with pytest.raises(ValueError, match=reason):
        check.audit(*files)


def test_loss_of_mutual_cannot_be_fitted_into_diagonal(files):
    text = files[2].read_text().replace("C0 B D 5e-17\n", "").replace("C2 B sub 5e-17", "C2 B sub 10e-17").replace("C4 D sub 1e-16", "C4 D sub 1.5e-16")
    files[2].write_text(text)
    with pytest.raises(ValueError, match="mutual"):
        check.audit(*files)


def test_changed_point_distribution_preserving_matrix_rejected(files):
    files[1].write_text(files[1].read_text().replace('"A" 0 50', '"A" 0 49').replace('"B" 0 50', '"B" 0 51'))
    with pytest.raises(ValueError, match="Per-node"):
        check.audit(*files)


def test_repeated_native_rnodes_still_add(files):
    files[1].write_text(files[1].read_text().replace('rnode "A" 0 50 0 0 0', 'rnode "A" 0 25 0 0 0\nrnode "A" 0 25 0 0 0'))
    assert check.audit(*files)["native_ground_points_af"]["A"] == 50


def test_source_patch_unknown_source_rejected():
    for name in patcher.SOURCES:
        with pytest.raises(ValueError, match="Unknown exact"):
            patcher.patch(name, b"modified source")


def test_old_method_mutation_rejected(tmp_path, monkeypatch):
    p = tmp_path / "old.py"
    p.write_text("changed")
    monkeypatch.setattr(patcher, "OLD_PATH", p)
    with pytest.raises(ValueError, match="Frozen"):
        patcher.old_method()
    monkeypatch.setattr(check, "V1", p)
    with pytest.raises(ValueError, match="Frozen"):
        check.old_method()


def test_component_gate_preserves_legacy_path(monkeypatch):
    raw = b"    (void) ResDistributeCapacitance(ResNodeList, resisdata->rg_nodecap);"
    monkeypatch.setitem(patcher.SOURCES, "ResSimple.c", hashlib.sha256(raw).hexdigest())
    result = patcher.patch("ResSimple.c", raw).decode()
    assert "(ResOpt_Simplify | ResOpt_DoLumpFile)) == 0" in result
    assert "== (ResOpt_DoExtFile | ResOpt_Signal)" in result
    assert result.count("ResDistributeCapacitance(ResNodeList, resisdata->rg_nodecap)") == 1
    assert result.count("ResDistributeCapacitance(ResNodeList, resisdata->rg_intrinsiccap)") == 1
    with pytest.raises(ValueError, match="Unknown exact"):
        patcher.patch("ResSimple.c", result.encode())
