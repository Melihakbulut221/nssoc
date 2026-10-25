# SPDX-FileCopyrightText: 2026 Hasan Melih Akbulut
# SPDX-License-Identifier: Apache-2.0
"""Proof provenance must survive an explicit SBY output directory."""
import importlib.util
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
spec = importlib.util.spec_from_file_location("formal_source_state", ROOT / "scripts/formal_source_state.py")
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)


@pytest.mark.parametrize("change,expected", [
    (None, "clean"), ("// explanation\nwire x;\n", "comment"),
    ("wire y;\n", "stale"), ("deleted", "unchecked"),
])
def test_relocated_output_and_aliased_input(tmp_path, change, expected):
    origin = tmp_path / "project/formal/props.v"
    origin.parent.mkdir(parents=True)
    origin.write_text("wire x;\n")
    work = tmp_path / "results/elsewhere"
    (work / "src").mkdir(parents=True)
    saved = work / "src/included.v"
    saved.write_bytes(origin.read_bytes())
    (work / "config.sby").write_text("[files]\nincluded.v props.v\n")
    (work / "logfile.txt").write_text(f"SBY [work] Copy '{origin}' to '{saved}'.\n")
    if change == "deleted":
        origin.unlink()
    elif change is not None:
        origin.write_text(change)
    assert module.source_state(work) == expected


def test_a_same_named_file_is_not_source_provenance(tmp_path):
    work = tmp_path / "proof"
    (work / "src").mkdir(parents=True)
    (work / "src/foo.v").write_text("wire x;")
    (tmp_path / "foo.v").write_text("wire x;")
    (work / "config.sby").write_text("[files]\nfoo.v\n")
    (work / "logfile.txt").write_text("DONE (PASS, rc=0)\n")
    assert module.source_state(work) == "unchecked"


def test_no_files_is_not_a_verified_proof(tmp_path):
    (tmp_path / "config.sby").write_text("[files]\n")
    (tmp_path / "logfile.txt").write_text("")
    assert module.source_state(tmp_path) == "unchecked"
