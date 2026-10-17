# SPDX-FileCopyrightText: 2026 Hasan Melih Akbulut
# SPDX-License-Identifier: Apache-2.0
"""Scoped native-RC reader and original-geometry audit regressions."""

import hashlib
from pathlib import Path
import sys

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "scripts"))
import check_magic_intrinsic_cap_retirement as check  # noqa: E402
import patch_magic_intrinsic_cap_retirement as patcher  # noqa: E402
from run_magic_intrinsic_cap_controls import case_text  # noqa: E402


@pytest.fixture
def files(tmp_path):
    ext, replacement, _, _ = case_text("retained_name")
    exported = ".subckt tiny A B\nR0 A B 0.05\nC0 A sub 6e-17\nC1 B sub 4e-17\n.ends\n"
    paths = [tmp_path / name for name in ("tiny.ext", "tiny.res.ext", "tiny.spice")]
    for path, content in zip(paths, (ext, replacement, exported)):
        path.write_text(content)
    return paths


def test_native_uncoupled_scoped_audit(files):
    result = check.audit(*files, baseline_spice=files[2])
    assert result["actual_matrix_af"] == {"B": {"B": 100}}
    assert result["qualified_pex"] is False


@pytest.mark.parametrize(
    "index,old,new,reason",
    [
        (0, "1000 1 0.5", "1000 2 0.5", "cscale"),
        (1, "1000 1 0.5", "1000 2 0.5", "cscale"),
        (0, "ngspice()", "other()", "style"),
        (0, "ihp-sg13g2", "other", "technology"),
        (0, 'equiv "B" "A"', 'equiv "A" "B"', "alias"),
        (0, 'equiv "B" "A"', 'equiv "B" "A"\nequiv "B" "A"', "alias"),
        (0, 'equiv "B" "A"', 'equiv "B" "A"\nuse child 0 0', "hierarchical"),
        (0, 'equiv "B" "A"', 'equiv "B" "A"\nmerge A B', "hierarchical"),
        (0, 'equiv "B" "A"', 'equiv "B" "A"\ncap "B" "A" 1', "coupling"),
        (0, 'node "B" 0 100', 'node "B" 0 -100', "intrinsic"),
        (1, 'subcap "B" -100', "", "exactly one"),
        (1, 'subcap "B" -100', 'subcap "B" -50', "amount"),
        (1, 'subcap "B" -100', 'subcap "B" -100\nsubcap "B" -100', "exactly one"),
        (1, 'subcap "B" -100', 'killnode "B"', "Unsupported"),
        (1, 'rnode "A" 0 60', 'rnode "A" 0 70', "Distributed"),
        (1, 'rnode "A" 0 60', 'rnode "C" 0 60', "terminal"),
        (2, ".subckt tiny A B", ".subckt tiny B A", "port"),
        (2, "R0 A B 0.05", "R0 A B 0.1", "resistance"),
        (2, "R0 A B 0.05", "R0 A C 0.05", "resistance"),
        (2, "C0 A sub 6e-17", "C0 A sub 16e-17", "Per-node"),
        (2, "C0 A sub 6e-17", "C0 A sub -6e-17", "Negative"),
        (2, "C0 A sub 6e-17", "C0 A sub nan", "nonfinite"),
        (2, "C0 A sub 6e-17", "C0 A sub inf", "nonfinite"),
        (2, "C1 B sub 4e-17", "C0 B sub 4e-17", "Duplicate"),
        (2, ".ends\n", "", "Missing"),
        (2, ".ends\n", ".ends\n.ends\n", "duplicate"),
        (2, ".ends\n", ".ends other\n", "Invalid"),
        (2, ".ends\n", ".ends\nC2 A sub 0\n", "outside"),
        (1, 'rnode "A" 0 60 0 0 0', 'rnode "A" 0 60 0 0', "arity"),
    ],
)
def test_mutations_rejected(files, index, old, new, reason):
    assert old in files[index].read_text()
    files[index].write_text(files[index].read_text().replace(old, new))
    with pytest.raises(ValueError, match=reason):
        check.audit(*files)


def test_negative_rnode_preserving_total_rejected(files):
    files[1].write_text(
        files[1]
        .read_text()
        .replace('"B" 0 40', '"B" 0 101')
        .replace('"A" 0 60', '"A" 0 -1')
    )
    with pytest.raises(ValueError, match="node capacitance"):
        check.audit(*files)


def test_changed_distribution_preserving_total_rejected(files):
    files[1].write_text(
        files[1]
        .read_text()
        .replace('"B" 0 40', '"B" 0 41')
        .replace('"A" 0 60', '"A" 0 59')
    )
    with pytest.raises(ValueError, match="Per-node"):
        check.audit(*files)


def test_disconnected_replacement_rejected(files):
    files[1].write_text(files[1].read_text().replace('resist "A" "B" 0.05\n', ""))
    files[2].write_text(files[2].read_text().replace("R0 A B 0.05\n", ""))
    with pytest.raises(ValueError, match="Disconnected"):
        check.audit(*files)


def test_repeated_rnode_is_additive(files):
    files[1].write_text(
        files[1]
        .read_text()
        .replace('rnode "A" 0 60 0 0 0', 'rnode "A" 0 30 0 0 0\nrnode "A" 0 30 0 0 0')
    )
    assert check.audit(*files)["distributed_intrinsic_af"] == {"B": 100}


def test_actual_coupling_requires_full_matrix():
    source = dict(
        caps={"B": 1182.59, "D": 1182.59},
        owner={"A": "B", "B": "B", "C": "D", "D": "D"},
        coupling=[("B", "D", 1168.76)],
    )
    netlist = dict(
        capacitors=[
            ("D", "B", 1168.76e-18),
            ("A", "sub", 1175.68e-18),
            ("B", "sub", 1175.68e-18),
            ("C", "sub", 1175.68e-18),
            ("D", "sub", 1175.68e-18),
        ]
    )
    want, actual = check.expected_matrix(source), check.matrix(source, netlist)
    assert check.close(want["B"]["D"], actual["B"]["D"])
    assert not check.close(want["B"]["B"], actual["B"]["B"])


def test_patch_unknown_source_rejected():
    for name in patcher.SOURCES:
        with pytest.raises(ValueError, match="Unknown exact"):
            patcher.patch(name, b"different upstream source")


@pytest.mark.parametrize(
    "name,raw",
    [
        ("resis.h", b"    float\t\tcapacitance;"),
        (
            "ResReadExt.c",
            b"    node->capacitance += MagAtof(argv[NODES_NODECAP]);\n\tnode->capacitance = 0;",
        ),
        ("ResPrint.c", b'    /* Create "rnode" entries for each subnode */'),
    ],
)
def test_exact_patch_and_reapply_rejected(monkeypatch, name, raw):
    monkeypatch.setitem(patcher.SOURCES, name, hashlib.sha256(raw).hexdigest())
    result = patcher.patch(name, raw)
    assert b"intrinsic_capacitance" in result
    with pytest.raises(ValueError, match="Unknown exact"):
        patcher.patch(name, result)


def test_duplicate_anchor_rejected(monkeypatch):
    raw = b"    float\t\tcapacitance;\n    float\t\tcapacitance;"
    monkeypatch.setitem(patcher.SOURCES, "resis.h", hashlib.sha256(raw).hexdigest())
    with pytest.raises(ValueError, match="anchor not unique"):
        patcher.patch("resis.h", raw)
