# SPDX-FileCopyrightText: 2026 Hasan Melih Akbulut
# SPDX-License-Identifier: Apache-2.0
"""Reject wrong capacitance increments and topology even when totals look right."""

from pathlib import Path
import sys

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "scripts"))
from audit_magic_groundcap import audit
from patch_magic_groundcap_reader import patch

SOURCE = """scale 1000 1 0.5
node "g" 0 10 0 0 m1
node "d" 0 20 1 0 m1
substrate "s" 0 0 2 0 m1
cap "g" "d" 5
"""
BEFORE = """scale 1000 1 0.5
rnode "g" 0 2 0 0 0
rnode "g.t0" 0 3 1 0 0
rnode "d" 0 1 2 0 0
rnode "d" 0 1 3 0 0
rnode "d.t0" 0 3 4 0 0
rnode "s" 0 0 5 0 0
resist "g" "g.t0" 7
resist "d" "d.t0" 9
device msubckt sg13_lv_nmos 0 0 1 1 "s" "g.t0" 52 0 "d.t0" 260 100,20 "s" 260 100,20
"""
AFTER = (
    BEFORE.replace('"g" 0 2 ', '"g" 0 6 ')
    .replace('"g.t0" 0 3 ', '"g.t0" 0 9 ')
    .replace('"d" 0 1 ', '"d" 0 5 ')
    .replace('"d.t0" 0 3 ', '"d.t0" 0 15 ')
    .replace("g.t0", "g.t8")
    .replace("d.t0", "d.t9")
)


def test_named_alias_records_are_added_and_weighted_topology_is_bijective():
    result = audit(SOURCE, BEFORE, SOURCE, AFTER)
    assert (
        result["original_ground_total_af"] == result["distributed_increment_af"] == 30
    )
    assert result["duplicate_rnode_names"] == ["d"]
    assert result["renamed_nodes"] == 2
    assert not result["qualified_pex"] and not result["manufacturing_approval"]


@pytest.mark.parametrize(
    "old,new",
    [
        ('"g" "g.t8" 7', '"g" "g.t8" 8'),
        ('"g" "g.t8" 7', '"d" "g.t8" 7'),
        ('"g.t8" 52 0', '"d.t9" 52 0'),
        ('"d" 0 5 ', '"d" 0 1 '),
        ('"g.t8" 0 9 ', '"g.t8" 0 -9 '),
        ('"g.t8" 0 9 ', '"g.t8" 0 NaN '),
        ('"g.t8" 0 9 ', '"g.t8" 0 inf '),
        ("scale 1000 1 0.5", "scale 1000 2 0.5"),
        ("sg13_lv_nmos", "sg13_lv_pmos"),
        ('"g.t8"', '"wrong.t8"'),
    ],
)
def test_malformed_or_changed_extraction_rejected(old, new):
    assert old in AFTER
    with pytest.raises(ValueError):
        audit(SOURCE, BEFORE, SOURCE, AFTER.replace(old, new))


def test_equal_total_with_capacitance_moved_to_wrong_net_rejected():
    changed = AFTER.replace('"g" 0 6 ', '"g" 0 7 ').replace(
        '"d.t9" 0 15 ', '"d.t9" 0 14 '
    )
    with pytest.raises(ValueError, match="increment not conserved"):
        audit(SOURCE, BEFORE, SOURCE, changed)


def test_missing_patch_is_a_negative_control():
    with pytest.raises(ValueError, match="increment not conserved"):
        audit(SOURCE, BEFORE, SOURCE, BEFORE)


def test_changed_source_capacitance_rejected():
    with pytest.raises(ValueError, match="Source geometry"):
        audit(SOURCE, BEFORE, SOURCE.replace('"g" 0 10', '"g" 0 11'), AFTER)


def test_statement_order_and_coupling_orientation_are_irrelevant():
    result = audit(
        SOURCE,
        BEFORE,
        "\n".join(reversed(SOURCE.replace('"g" "d" 5', '"d" "g" 5').splitlines())),
        "\n".join(reversed(AFTER.splitlines())),
    )
    assert result["weighted_r_mos_topology_preserved"]


def test_spatial_metadata_change_does_not_silently_claim_spatial_proof():
    result = audit(
        SOURCE, BEFORE, SOURCE, AFTER.replace('"g.t8" 0 9 1 0', '"g.t8" 0 9 8 0')
    )
    assert len(result["changed_rnode_coordinate_records"]) == 1
    assert not result["spatial_capacitance_preservation_proven"]


def test_unredistributed_zero_ground_remains_explicit():
    before = BEFORE.replace('rnode "s" 0 0 5 0 0\n', "")
    after = AFTER.replace('rnode "s" 0 0 5 0 0\n', "")
    result = audit(SOURCE, before, SOURCE, after)
    assert result["retained_zero_cap_nodes_without_distribution"] == ["s"]


@pytest.mark.parametrize(
    "text", [b"", b"node = ResExtInitNode(entry);", b"wrong version"]
)
def test_patcher_refuses_unknown_source(text):
    with pytest.raises(ValueError, match="Unknown source version"):
        patch(text)
