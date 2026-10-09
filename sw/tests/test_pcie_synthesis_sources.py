# SPDX-FileCopyrightText: 2026 Hasan Melih Akbulut
# SPDX-License-Identifier: Apache-2.0
import importlib.util
import json
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
spec = importlib.util.spec_from_file_location("source_guard", ROOT / "scripts/check_pcie_synthesis_sources.py")
guard = importlib.util.module_from_spec(spec)
spec.loader.exec_module(guard)


@pytest.fixture
def inputs(tmp_path):
    candidate = tmp_path / "candidate"
    candidate.mkdir()
    rtl = candidate / "credit.v"
    rtl.write_text("module credit(input a, output b); assign b = a; endmodule\n")
    canonical = tmp_path / "credit.v"
    canonical.write_text("module credit(input a, output b); assign b = ~a; endmodule\n")
    recipe = tmp_path / "run.ys"
    recipe.write_text(f"read_verilog -sv -defer -DSOC_SRAM_MBIST -I{candidate} {rtl}\n")
    proof = tmp_path / "proof.json"
    proof.write_text(json.dumps({"status": "PASS", "inputs": {str(rtl): guard.digest(rtl)}}))
    return candidate, rtl, canonical, recipe, proof


def test_explicit_candidate_and_proof(inputs):
    candidate, rtl, _, recipe, proof = inputs
    result = guard.check(recipe, candidate, ["credit.v"], [proof])
    assert result["sources"] == [str(rtl)]
    assert result["preprocessor_defines"] == ["SOC_SRAM_MBIST"]
    assert not result["timing_accepted"]


def test_rejects_original_canonical_credit_bug(inputs):
    candidate, rtl, canonical, recipe, proof = inputs
    recipe.write_text(recipe.read_text().replace(str(rtl), str(canonical)))
    with pytest.raises(ValueError, match="not selected exactly once"):
        guard.check(recipe, candidate, ["credit.v"], [proof])


def test_rejects_duplicate_module_input(inputs):
    candidate, rtl, canonical, recipe, proof = inputs
    recipe.write_text(recipe.read_text() + f"read_verilog {canonical}\n")
    with pytest.raises(ValueError, match="not selected exactly once"):
        guard.check(recipe, candidate, ["credit.v"], [proof])


def test_rejects_changed_proved_rtl(inputs):
    candidate, rtl, _, recipe, proof = inputs
    rtl.write_text(rtl.read_text().replace("b = a", "b = ~a"))
    with pytest.raises(ValueError, match="Proof input changed"):
        guard.check(recipe, candidate, ["credit.v"], [proof])


def test_rejects_shadowed_second_candidate(inputs):
    candidate, _, canonical, recipe, proof = inputs
    (candidate / "other.v").write_text("module other; endmodule\n")
    other = canonical.with_name("other.v")
    other.write_text("module other; endmodule\n")
    recipe.write_text(recipe.read_text() + f"read_verilog {other}\n")
    with pytest.raises(ValueError, match="shadows available candidate"):
        guard.check(recipe, candidate, ["credit.v"], [proof])
