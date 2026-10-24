# SPDX-FileCopyrightText: 2026 Hasan Melih Akbulut
# SPDX-License-Identifier: Apache-2.0
"""Ordered mapping and view-identity negative controls; no native LVS."""
import copy
from pathlib import Path
import sys

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "scripts"))
import io_tap_topology_audit as audit  # noqa: E402


CDL = """.subckt sg13g2_DCNDiode anode cathode guard
.ends
.subckt sg13g2_DCPDiode anode cathode guard
.ends
.subckt sg13g2_IOPadVss vdd vss iovdd iovss
XI1 iovss vss iovdd / sg13g2_DCNDiode
XI2 vss iovdd iovss / sg13g2_DCPDiode
.ends
"""
LEF = "MACRO sg13g2_IOPadVss\n" + "".join(
    f" PIN {pin}\n DIRECTION INOUT ;\n USE {role} ;\n END {pin}\n"
    for pin, role in audit.RAILS.items()) + "END sg13g2_IOPadVss\n"


def test_corrected_guard_reference_passes_only_topology_scope():
    result = audit.audit(CDL, LEF)
    assert result["reference_topology_matches"]
    assert not result["lvs_accepted"] and not result["physical_parent_connection_proven"]


def test_unrelated_library_preamble_and_zero_port_gallery_do_not_change_mapping():
    wrapper = ".PARAM\n.SUBCKT unrelated_gallery\n.ENDS\n" + CDL
    assert audit.audit(wrapper, LEF) == audit.audit(CDL, LEF)


def test_parameter_directive_inside_selected_cell_is_not_silently_removed():
    with pytest.raises(audit.ContractError):
        audit.audit(CDL.replace("XI1", ".PARAM n=2\nXI1"), LEF)


def test_duplicate_selected_cell_rejected():
    with pytest.raises(audit.ContractError):
        audit.audit(CDL + CDL, LEF)


def test_old_guard_connection_is_detected():
    result = audit.audit(CDL.replace("XI1 iovss vss iovdd", "XI1 iovss vss iovss"), LEF)
    assert not result["reference_topology_matches"]
    assert result["children"]["sg13g2_dcndiode"]["actual_map"]["guard"] == "iovss"


def test_diode_formal_permutation_without_rewiring_fails():
    bad = CDL.replace("sg13g2_DCNDiode anode cathode guard", "sg13g2_DCNDiode guard cathode anode")
    assert not audit.audit(bad, LEF)["reference_topology_matches"]
    fixed = bad.replace("XI1 iovss vss iovdd", "XI1 iovdd vss iovss")
    assert audit.audit(fixed, LEF)["reference_topology_matches"]


def test_parent_port_permutation_requires_caller_reorder():
    old = ["iovdd", "iovss", "vdd", "vss"]
    new = ["vdd", "vss", "iovdd", "iovss"]
    caller = ["IO_POWER", "IO_GROUND", "CORE_POWER", "CORE_GROUND"]
    original = audit.bind_call(old, caller)
    assert audit.bind_call(new, caller) != original
    indices = audit.migration_indices(old, new)
    assert indices == [2, 3, 0, 1]
    assert audit.bind_call(new, [caller[i] for i in indices]) == original


@pytest.mark.parametrize("bad", [CDL.replace("/ sg13g2_DCNDiode", "/ sg13g2_DCNDiode m=2"), CDL.replace("XI1 iovss vss iovdd", "XI1 iovss vss"), CDL.replace("XI2 vss iovdd iovss / sg13g2_DCPDiode\n", ""), CDL.replace("XI1 iovss vss iovdd / sg13g2_DCNDiode", "XI1 iovss vss iovdd / sg13g2_DCNDiode\nXI3 iovss vss iovdd / sg13g2_DCNDiode")])
def test_ambiguous_or_incomplete_instance_rejected(bad):
    with pytest.raises(audit.ContractError):
        audit.audit(bad, LEF)


@pytest.mark.parametrize("bad", [LEF.replace("PIN iovdd", "PIN wrong"), LEF.replace("USE POWER", "USE GROUND", 1), LEF.replace("DIRECTION INOUT", "DIRECTION INPUT", 1), LEF.replace("END iovdd", "END wrong"), LEF + LEF])
def test_bad_lef_interface_rejected(bad):
    with pytest.raises(audit.ContractError):
        audit.audit(CDL, bad)


def test_mixed_release_and_wrong_metadata_rejected(tmp_path):
    path = tmp_path / "view.gds"
    path.write_bytes(b"bounded synthetic view A, not physical GDS")
    sha = "a" * 40
    identity = audit.file_identity(path)
    relative = f"{audit.VIEW_BASE}/gds/sg13g2_io.gds"
    metadata = {"path": relative, "html_url": f"{audit.REPO}/blob/{sha}/{relative}",
                "sha": identity["git_blob_sha1"], "size": identity["bytes"]}
    assert audit.verify_view(path, metadata, sha, "gds") == identity
    wrong = copy.deepcopy(metadata)
    wrong["html_url"] = wrong["html_url"].replace(sha, "b" * 40)
    with pytest.raises(audit.ContractError):
        audit.verify_view(path, wrong, sha, "gds")
    path.write_bytes(b"bounded synthetic view B, not physical GDS")
    with pytest.raises(audit.ContractError):
        audit.verify_view(path, metadata, sha, "gds")


def test_duplicate_or_different_formal_sets_rejected():
    for old, new in [(["a", "a"], ["a", "a"]), (["a", "b"], ["a", "c"]), (["a", "b"], ["a", "b", "b"])]:
        with pytest.raises(audit.ContractError):
            audit.migration_indices(old, new)
