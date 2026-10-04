# SPDX-FileCopyrightText: 2026 Hasan Melih Akbulut
# SPDX-License-Identifier: Apache-2.0
"""Source-bound external nettype guards must actually reject implicit wires."""

import hashlib
import importlib.util
import json
import os
import shutil
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
SPEC = importlib.util.spec_from_file_location(
    "frozen_soc_lint", ROOT / "scripts/check_soc_lint.py"
)
M = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(M)
def compiler_path():
    # Hosted source tests install Yosys on PATH; physical/lint runs use the
    # configured pinned suite. A missing actual compiler must still fail.
    suite = Path(os.environ.get("OSS_CAD_SUITE", ROOT / "hw/soc/tools/oss-cad-suite"))
    candidate = suite / "bin/yosys"
    return candidate if candidate.is_file() else Path(shutil.which("yosys") or "/missing/yosys")


YOSYS = compiler_path()


def fixture(root, text):
    p = root / "hw/soc/rtl/pcie/frozen.v"
    p.parent.mkdir(parents=True)
    p.write_text(text)
    manifest = root / "hw/soc/frozen-pcie-nettypes.json"
    manifest.write_text(
        json.dumps(
            {
                "sources": {
                    str(p.relative_to(root)): hashlib.sha256(p.read_bytes()).hexdigest()
                }
            }
        )
    )
    return p, manifest


def test_all_frozen_sources_are_actually_parsed_with_guard(tmp_path):
    assert YOSYS.is_file(), "Real pinned Yosys is required"
    r = M.guarded_frozen_nettypes(ROOT, tmp_path / "all", YOSYS)
    assert r["status"] == "PASS_FROZEN_SOURCES_PARSED_WITH_NO_IMPLICIT_NETS"
    assert len(r["sources"]) == 34 and r["sources_unchanged"]


@pytest.mark.parametrize("implicit", [False, True])
def test_real_compiler_distinguishes_implicit_wire(tmp_path, implicit):
    text = "module legacy(input a, output q); "
    text += "assign misspelled=a;assign q=misspelled;" if implicit else "assign q=a;"
    p, _ = fixture(tmp_path, text + "endmodule\n")
    assert M.frozen_nettype_sources(tmp_path)
    if implicit:
        with pytest.raises(RuntimeError, match="guarded compilation failed"):
            M.guarded_frozen_nettypes(tmp_path, tmp_path / "compile", YOSYS)
        log = (tmp_path / "compile/yosys.log").read_text()
        assert "misspelled" in log and "default_nettype" in log
    else:
        assert (
            M.guarded_frozen_nettypes(tmp_path, tmp_path / "compile", YOSYS)[
                "returncode"
            ]
            == 0
        )
    assert p.read_text() == text + "endmodule\n", "Original capture bytes changed"


def test_source_drift_is_rejected_before_guarded_compilation(tmp_path):
    p, _ = fixture(tmp_path, "module frozen;endmodule\n")
    p.write_text(p.read_text() + "// changed\n")
    with pytest.raises(ValueError, match="identity changed"):
        M.frozen_nettype_sources(tmp_path)


@pytest.mark.parametrize(
    "directive", ["`default_nettype wire", "`default_nettype none"]
)
def test_frozen_file_cannot_override_wrapper_scope(tmp_path, directive):
    fixture(tmp_path, directive + "\nmodule frozen;endmodule\n")
    with pytest.raises(ValueError, match="override external guard"):
        M.frozen_nettype_sources(tmp_path)


def test_unregistered_file_still_requires_in_file_guards(tmp_path):
    p, _ = fixture(tmp_path, "module frozen;endmodule\n")
    (p.parent / "new.v").write_text("module new;endmodule\n")
    (tmp_path / "hw/soc/rtl/soc_logic_boot_rom.v.in").write_text(
        "`default_nettype none\nmodule rom;endmodule\n`default_nettype wire\n"
    )
    assert M.nettype_errors(tmp_path) == ["hw/soc/rtl/pcie/new.v"]


def test_unavailable_compiler_is_failure_not_acceptance(tmp_path):
    fixture(tmp_path, "module frozen;endmodule\n")
    with pytest.raises(FileNotFoundError):
        M.guarded_frozen_nettypes(
            tmp_path, tmp_path / "compile", tmp_path / "absent-tool"
        )


def test_hosted_path_without_local_runtime_is_usable(tmp_path, monkeypatch):
    binary = tmp_path / "bin/yosys"
    binary.parent.mkdir()
    binary.write_text("#!/bin/sh\nexit 0\n")
    binary.chmod(0o755)
    monkeypatch.setenv("OSS_CAD_SUITE", str(tmp_path / "absent-suite"))
    monkeypatch.setenv("PATH", str(binary.parent))
    assert compiler_path() == binary
