# SPDX-FileCopyrightText: 2026 Hasan Melih Akbulut
# SPDX-License-Identifier: Apache-2.0
"""Reject malformed or changed cloud input bundles before executing tools."""
import hashlib
import io
import json
from pathlib import Path
import sys
import tarfile

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "scripts"))
import run_chip_native_shard as runner


def archive(tmp_path, defect=None):
    payload = b"native-layout"
    name = "input/chip.gds"
    if defect == "traversal": name = "../chip.gds"
    if defect == "absolute": name = "/chip.gds"
    row = dict(bytes=len(payload), sha256=hashlib.sha256(payload).hexdigest())
    if defect == "hash": row["sha256"] = "0" * 64
    if defect == "size": row["bytes"] += 1
    inv = json.dumps({name: row}).encode()
    path = tmp_path / "bundle.tar"
    with tarfile.open(path, "w") as tar:
        entries = [("inventory.json", inv), (name, payload)]
        if defect == "duplicate": entries.append((name, payload))
        if defect == "unlisted": entries.append(("unlisted", b"x"))
        for n, data in entries:
            info = tarfile.TarInfo(n)
            info.size = len(data)
            if defect == "symlink" and n == name:
                info.type = tarfile.SYMTYPE
                info.linkname = "/tmp/foreign"
                info.size = 0
            tar.addfile(info, io.BytesIO(data))
    return path


def test_verified_bundle_roundtrip(tmp_path):
    inv = runner.restore(archive(tmp_path), tmp_path / "restored")
    assert (tmp_path / "restored/input/chip.gds").read_bytes() == b"native-layout"
    assert set(inv) == {"input/chip.gds"}


@pytest.mark.parametrize("defect", ["traversal", "absolute", "hash", "size", "duplicate", "unlisted", "symlink"])
def test_rejects_unsafe_or_changed_members(tmp_path, defect):
    with pytest.raises(ValueError):
        runner.restore(archive(tmp_path, defect), tmp_path / "restored")


def test_does_not_overwrite_existing_restoration(tmp_path):
    out = tmp_path / "restored"
    out.mkdir()
    with pytest.raises(FileExistsError): runner.restore(archive(tmp_path), out)


def test_rejects_missing_shards():
    with pytest.raises(ValueError, match="shard"):
        runner.validate_config(dict(commands={}, catalogs={}))


@pytest.mark.parametrize("defect", [None, "missing", "empty", "escape", "include"])
def test_native_runtime_dependencies_are_checked_before_execution(tmp_path, defect):
    deck = tmp_path / "tech/drc/main.drc"
    deck.parent.mkdir(parents=True)
    parameters = deck.parent / "values.json"
    if defect != "missing":
        parameters.write_text(json.dumps({"drc_rules": {} if defect == "empty" else {"width": 1}}))
    relative = "../../../foreign.json" if defect == "escape" else "values.json"
    text = "$drc_json = File.expand_path(File.join(script_dir, '" + relative + "'))\n"
    if defect == "include": text += "# %include missing.drc\n"
    deck.write_text(text)
    config = dict(commands={"beol": ["-r", "@ROOT@/tech/drc/main.drc"]})
    if defect is None:
        assert runner.validate_deck_dependencies(tmp_path, config) == 2
    else:
        with pytest.raises(ValueError): runner.validate_deck_dependencies(tmp_path, config)


@pytest.mark.parametrize("density", [None, 207])
def test_prepare_uses_selected_manifest_and_layout_density(tmp_path, monkeypatch, density):
    """A new layout must not inherit the previous chip's measured marker count."""
    manifest = tmp_path / "selected.json"
    manifest.write_text('{"selected": true}')
    output = tmp_path / "separate-campaign"
    monkeypatch.setattr(sys, "argv", ["runner", "--group", "antenna", "--prepare-only",
                                     "--manifest", str(manifest), "--output", str(output)])
    row = {"name": "selected.tar"}
    def validate(value):
        assert value == {"selected": True}
        return [row]
    def restore(path, bundle):
        assert path == output / "antenna/selected.tar"
        bundle.mkdir()
        (bundle / "chip.gds").write_bytes(b"selected-layout")
        (bundle / "config.json").write_text(json.dumps(dict(
            gds="chip.gds", gds_sha256="digest", scope="new layout",
            commands={"antenna": ["-r", "@ROOT@/native.drc"]},
            known_density_markers=density)))
        return {}
    monkeypatch.setattr(runner, "validate", validate)
    monkeypatch.setattr(runner, "fetch", lambda selected, out: None)
    monkeypatch.setattr(runner, "restore", restore)
    monkeypatch.setattr(runner, "validate_config", lambda config: None)
    monkeypatch.setattr(runner, "validate_deck_dependencies", lambda bundle, config: 84)
    monkeypatch.setattr(runner, "verify_tool", lambda app, arch: None)
    monkeypatch.setattr(runner, "digest", lambda path: "digest")
    runner.main()
    result = json.loads((output / "antenna/result.json").read_text())
    assert result["status"] == "PREPARED"
    assert result["known_density_markers"] == density
    assert str(manifest) in result["input_sha256"]


def config_with_density():
    base = "@ROOT@/hw/soc/tools/ihp-drc-5e6d592/ihp-sg13g2/libs.tech/klayout/tech/drc/rule_decks/density.drc"
    command = ["-b", "-zz", "-r", base]
    for value in ("input=@GDS@", "topcell=nssoc_chip", "report=@REPORT@", "threads=1",
                  "run_mode=deep", "precheck_drc=False", "no_recommended=False", "density_sanity=True"):
        command += ["-rd", value]
    config = dict(commands={name: [] for name in runner.BASE_GROUPS},
                  catalogs={name: {} for name in runner.BASE_GROUPS},
                  top="nssoc_chip", gds="input/chip.gds")
    config["commands"]["density"] = command
    for name, size in [("antenna", 31), ("supplemental_wide", 11)]:
        config["catalogs"][name] = {str(i): "native category" for i in range(size)}
    return config


@pytest.mark.parametrize("include_density", [True, False])
def test_optional_density_preserves_legacy_bundles(monkeypatch, include_density):
    config = config_with_density()
    monkeypatch.setattr(runner, "check_catalog", lambda name, cats: None)
    if not include_density:
        del config["commands"]["density"]
    runner.validate_config(config)


@pytest.mark.parametrize("defect", ["sanity", "mode", "recommended", "duplicate", "fixed_catalog", "missing_shard"])
def test_density_cannot_disable_checks_or_use_fixed_category_count(monkeypatch, defect):
    config = config_with_density()
    monkeypatch.setattr(runner, "check_catalog", lambda name, cats: None)
    command = config["commands"]["density"]
    if defect == "sanity": command[-1] = "density_sanity=False"
    elif defect == "mode": command[command.index("run_mode=deep")] = "run_mode=tiling"
    elif defect == "recommended": command[command.index("no_recommended=False")] = "no_recommended=True"
    elif defect == "duplicate": command += ["-rd", "density_sanity=True"]
    elif defect == "fixed_catalog": config["catalogs"]["density"] = {}
    else: del config["commands"]["beol"]
    with pytest.raises(ValueError): runner.validate_config(config)


def test_density_runner_uses_execution_coverage(tmp_path):
    import xml.etree.ElementTree as ET
    from check_ihp_density_coverage import RULES, SLITS
    root = ET.Element("report-database")
    ET.SubElement(root, "top-cell").text = "nssoc_chip"
    cats = ET.SubElement(root, "categories")
    for name in SLITS:
        ET.SubElement(ET.SubElement(cats, "category"), "name").text = name
    ET.SubElement(ET.SubElement(ET.SubElement(root, "cells"), "cell"), "name").text = "nssoc_chip"
    ET.SubElement(root, "items")
    ET.ElementTree(root).write(tmp_path / "drc.lyrdb")
    log = "\n".join("Executing rule " + rule for rule in RULES)
    log += "\nKLayout DRC run for density table completed in 1.0 seconds\n"
    (tmp_path / "run.log").write_text(log)
    result = runner.shard_coverage("density", dict(top="nssoc_chip"), tmp_path, 0)
    assert result["status"] == "PASS" and result["executed_rule_count"] == 37
    assert len(result["category_inventory"]) == 7
    (tmp_path / "run.log").write_text(log.replace("Executing rule M2.j\n", ""))
    with pytest.raises(ValueError, match="Incomplete"):
        runner.shard_coverage("density", dict(top="nssoc_chip"), tmp_path, 0)
