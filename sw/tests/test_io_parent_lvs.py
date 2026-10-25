# SPDX-FileCopyrightText: 2026 Hasan Melih Akbulut
# SPDX-License-Identifier: Apache-2.0
"""Immutable I/O inputs, native strictness, resource gates and audit failure paths."""
import hashlib
import io
import json
from pathlib import Path
import sys
import tarfile

import pytest

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "scripts"))
import run_io_parent_lvs as runner  # noqa: E402


def digest(data):
    return hashlib.sha256(data).hexdigest()


def archive_fixture(tmp_path, monkeypatch, fault=None):
    gds = b"synthetic bounded archive input, not a GDS acceptance fixture"
    proof = dict(status="BYTE_PRESERVED_HIERARCHY_SUBSET", roots=[runner.TOP],
                 output=dict(sha256=digest(gds), bytes=len(gds), cell_count=4),
                 cells={str(i): {} for i in range(4)})
    if fault == "wrong_top":
        proof["roots"] = ["OTHER"]
    if fault == "wrong_cell_count":
        proof["output"]["cell_count"] = 3
    data = {"io/gds": gds, "io/proof": json.dumps(proof).encode(),
            "io/cdl": b".GLOBAL sub!\n.SUBCKT child a b\n.ENDS child\n"}
    if fault == "missing_global":
        data["io/cdl"] = data["io/cdl"].replace(b".GLOBAL", b"*.GLOBAL")
    selected = {key: (name, digest(data[key])) for key, name in
                [("io/gds", "subset.gds"), ("io/proof", "subset-receipt.json"),
                 ("io/cdl", "schematic.cir")]}
    monkeypatch.setattr(runner, "MEMBERS", selected)
    data["unselected"] = b"also inventoried"
    inventory = {key: dict(bytes=len(value), sha256=digest(value)) for key, value in data.items()}
    if fault == "missing_member":
        del data["io/cdl"]
        del inventory["io/cdl"]
    if fault == "unselected_corrupt":
        data["unselected"] = b"also corrupted"
    if fault == "incomplete_inventory":
        del inventory["unselected"]
    if fault == "wrong_pinned_member":
        selected["io/gds"] = ("subset.gds", "0" * 64)
    data["members.json"] = json.dumps(inventory).encode()
    archive = tmp_path / "inputs.tar.gz"
    with tarfile.open(archive, "w:gz") as target:
        for key, value in data.items():
            item = tarfile.TarInfo(key)
            item.size = len(value)
            target.addfile(item, io.BytesIO(value))
        if fault == "duplicate":
            item = tarfile.TarInfo("io/gds")
            item.size = len(gds)
            target.addfile(item, io.BytesIO(gds))
        if fault in ("symlink", "traversal"):
            item = tarfile.TarInfo("bad" if fault == "symlink" else "../bad")
            if fault == "symlink":
                item.type = tarfile.SYMTYPE
                item.linkname = "/outside"
            target.addfile(item)
    monkeypatch.setattr(runner, "ASSET", dict(name=archive.name, bytes=archive.stat().st_size,
                                            sha256=runner.sha(archive)))
    if fault == "wrong_archive_hash":
        runner.ASSET["sha256"] = "0" * 64
    return archive


def test_selected_bytes_and_all_member_verification(tmp_path, monkeypatch):
    archive = archive_fixture(tmp_path, monkeypatch)
    destination = tmp_path / "selected"
    pins = runner.unpack_inputs(archive, destination)
    assert {path.name for path in destination.iterdir()} == {
        "subset.gds", "subset-receipt.json", "schematic.cir"}
    assert all(runner.sha(path) == expected for path, expected in pins.items())
    assert not (destination / "unselected").exists()
    with pytest.raises(FileExistsError):
        runner.unpack_inputs(archive, destination)
    assert all(runner.sha(path) == expected for path, expected in pins.items())


@pytest.mark.parametrize("fault", ["wrong_archive_hash", "wrong_pinned_member", "wrong_top",
                                   "wrong_cell_count", "missing_global", "missing_member",
                                   "unselected_corrupt", "incomplete_inventory", "duplicate",
                                   "symlink", "traversal"])
def test_rejects_untrusted_or_incomplete_archive_without_output(tmp_path, monkeypatch, fault):
    archive = archive_fixture(tmp_path, monkeypatch, fault)
    destination = tmp_path / "selected"
    with pytest.raises(ValueError):
        runner.unpack_inputs(archive, destination)
    assert not destination.exists()


def test_native_command_has_no_waivers_and_only_mode_differs(tmp_path):
    deep = runner.command(Path("tool"), Path("deck"), tmp_path, tmp_path / "case", "deep")
    flat = runner.command(Path("tool"), Path("deck"), tmp_path, tmp_path / "case", "flat")
    assert [(a, b) for a, b in zip(deep, flat, strict=True) if a != b] == [
        ("run_mode=deep", "run_mode=flat")]
    options = {value.split("=", 1)[0]: value.split("=", 1)[1] for value in deep[7::2]}
    assert options["disable_tap_extraction"] == "false"
    assert options["ignore_top_ports_mismatch"] == "false"
    assert set(options) == {"input", "schematic", "topcell", "report", "log", "target_netlist",
                            "run_mode", "thr", "disable_tap_extraction", "ignore_top_ports_mismatch"}
    with pytest.raises(ValueError):
        runner.command(Path("tool"), Path("deck"), tmp_path, tmp_path, "waive")


@pytest.mark.parametrize("kib,accepted", [(5 * 1024**2, True), (5 * 1024**2 - 1, False), (0, False)])
def test_resource_guard_does_not_lower_threshold(tmp_path, kib, accepted):
    meminfo = tmp_path / "meminfo"
    meminfo.write_text(f"MemTotal: 9999999 kB\nMemAvailable: {kib} kB\n")
    if accepted:
        assert runner.require_resources(meminfo) == kib * 1024
    else:
        with pytest.raises(ValueError, match="5 GiB"):
            runner.require_resources(meminfo)


def control_fixture(tmp_path, monkeypatch):
    monkeypatch.setattr(runner, "OUTPUT_ROOT", tmp_path)
    source = tmp_path / "native.py"
    source.write_text("pinned fixture")
    monkeypatch.setattr(runner, "CONTROL", source)
    app = tmp_path / "fixture-runtime"
    app.write_text("pinned runtime")
    monkeypatch.setattr(runner, "APP", app)
    monkeypatch.setattr(runner, "APP_SHA256", runner.sha(app))
    cases, outputs = {}, {}
    for name, expected in runner.CONTROL_CASES.items():
        directory = tmp_path / name
        directory.mkdir()
        files = {}
        for filename in runner.CONTROL_FILES:
            path = directory / filename
            path.write_text("bounded native evidence contract fixture")
            files[filename] = runner.sha(path)
            outputs[str(path)] = runner.sha(path)
        drains = 2 if name in ("same_name_open", "missing_via") else 1
        cases[name] = dict(actual_match=expected, expected_match=expected,
                          device_counts={"NMOS4": 2, "TAP": 1}, extraction_diagnostics=[],
                          hierarchical_circuits=["CHILD", "TOP"], tap_terminal_order=["TIE", "WELL"],
                          tap_parameters={"A": 0.75 if name == "wrong_tap_area" else 1.0,
                                          "P": 5.0 if name == "wrong_tap_perimeter" else 4.0},
                          distinct_drain_nets_after_parent_extraction=drains,
                          drain_cluster_ids=[1, 2 if drains == 2 else 1], files=files)
    value = dict(status="PASS_NATIVE_PARENT_CONTEXT_CONTROLS",
                 method_sha256={"sw/tests/io_parent_lvs_native.py": runner.sha(source)},
                 cases=cases,
                 input_sha256={str(source): runner.sha(source), str(app): runner.sha(app)},
                 output_sha256=outputs)
    return value


@pytest.mark.parametrize("fault", [None, "missing", "false_negative", "changed_source", "incomplete",
                                   "missing_pins", "changed_output", "extra_case", "missing_area_case",
                                   "lost_polarity", "fake_parent_connection", "extra_file", "missing_file",
                                   "corrupted_native_file", "wrong_runtime"])
def test_native_controls_cannot_be_skipped_or_forged(tmp_path, monkeypatch, fault):
    value = control_fixture(tmp_path, monkeypatch)
    if fault == "missing":
        del value["cases"]["missing_via"]
    if fault == "false_negative":
        value["cases"]["wrong_tap_perimeter"]["actual_match"] = True
    if fault == "changed_source":
        value["method_sha256"]["sw/tests/io_parent_lvs_native.py"] = "0" * 64
    if fault == "incomplete":
        value["status"] = "RUNNING"
    if fault == "missing_pins":
        del value["output_sha256"]
    if fault == "changed_output":
        value["output_sha256"][str(runner.CONTROL)] = "0" * 64
    if fault == "extra_case":
        value["cases"]["unknown"] = {}
    if fault == "missing_area_case":
        del value["cases"]["wrong_tap_area"]
    if fault == "lost_polarity":
        value["cases"]["connected"]["tap_terminal_order"] = ["WELL", "TIE"]
    if fault == "fake_parent_connection":
        value["cases"]["missing_via"]["drain_cluster_ids"] = [1, 1]
    if fault == "extra_file":
        value["cases"]["connected"]["files"]["unknown"] = "0" * 64
    if fault == "missing_file":
        del value["cases"]["connected"]["files"]["hierarchy.l2n"]
    if fault == "corrupted_native_file":
        (tmp_path / "wrong_tap_perimeter" / "layout.gds").write_bytes(b"corrupted geometry")
    if fault == "wrong_runtime":
        value["input_sha256"][str(runner.APP)] = "0" * 64
    path = tmp_path / "controls.json"
    path.write_text(json.dumps(value))
    if fault:
        with pytest.raises(ValueError):
            runner.validate_controls(path)
    else:
        assert runner.validate_controls(path) == value


def audit_fixture(tmp_path, passed):
    case = tmp_path / "case"
    case.mkdir()
    (case / "lvs.lvsdb.gz").write_bytes(b"small fake container for audit-contract unit test")
    (case / "extracted.cir").write_text(".SUBCKT source\n.ENDS\n")
    deck = ("INFO : Congratulations! Netlists match." if passed else "ERROR : Netlists don't match")
    (case / "deck.log").write_text(deck)
    rows = [dict(layout=runner.TOP, schematic=runner.TOP.upper(),
                 status="Match" if passed else "NoMatch", layout_devices_recursive=3,
                 schematic_devices_recursive=3)]
    audit = runner.assess(rows, runner.TOP, deck)
    audit["inputs"] = {str(case / name): dict(bytes=(case / name).stat().st_size,
                                            sha256=runner.sha(case / name))
                       for name in ("lvs.lvsdb.gz", "deck.log")}
    (case / "audit.json").write_text(json.dumps(audit))
    return case, audit


@pytest.mark.parametrize("passed", [True, False])
def test_native_exit_zero_is_not_lvs_acceptance(tmp_path, passed):
    case, audit = audit_fixture(tmp_path, passed)
    result = runner.verdict(case, {"returncode": 0}, {"returncode": 0 if passed else 1})
    assert result == audit
    assert result["status"] == ("PASS within comparison scope" if passed else "FAIL")


@pytest.mark.parametrize("fault", ["failed_native", "wrong_audit_exit", "missing_db", "changed_db",
                                   "forged_success", "extraction_warning"])
def test_incomplete_or_changed_native_evidence_is_never_accepted(tmp_path, fault):
    case, audit = audit_fixture(tmp_path, True)
    native, auditor = {"returncode": 0}, {"returncode": 0}
    if fault == "failed_native":
        native["returncode"] = -6
    elif fault == "wrong_audit_exit":
        auditor["returncode"] = 2
    elif fault == "missing_db":
        (case / "lvs.lvsdb.gz").unlink()
    elif fault == "changed_db":
        (case / "lvs.lvsdb.gz").write_bytes(b"different database")
    else:
        if fault == "forged_success":
            audit["circuits"][0]["status"] = "Skipped"
        else:
            audit["extraction_diagnostics"] = [dict(severity="Warning", category="must-connect")]
        (case / "audit.json").write_text(json.dumps(audit))
    with pytest.raises(ValueError):
        runner.verdict(case, native, auditor)


def test_changed_source_pin_rejected(tmp_path):
    source = tmp_path / "source"
    source.write_bytes(b"before")
    pins = {str(source): runner.sha(source)}
    runner.check_pins(pins)
    source.write_bytes(b"after")
    with pytest.raises(ValueError, match="Source changed"):
        runner.check_pins(pins)


def test_control_paths_cannot_escape_project_or_receipt(tmp_path, monkeypatch):
    value = control_fixture(tmp_path, monkeypatch)
    receipt = tmp_path / "controls.json"
    receipt.write_text(json.dumps(value))
    monkeypatch.setattr(runner, "OUTPUT_ROOT", tmp_path / "different-root")
    with pytest.raises(ValueError, match="this project's"):
        runner.validate_controls(receipt)
    monkeypatch.setattr(runner, "OUTPUT_ROOT", tmp_path)
    target = tmp_path / "connected" / "layout.gds"
    target.unlink()
    target.symlink_to(tmp_path.parent / "outside-project")
    with pytest.raises(ValueError, match="escapes its receipt"):
        runner.validate_controls(receipt)
