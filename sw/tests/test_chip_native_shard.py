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
