# SPDX-FileCopyrightText: 2026 Hasan Melih Akbulut
# SPDX-License-Identifier: Apache-2.0
"""Inventory reachability across pilot and all recursive SoC RTL sources.

This is a lexical inventory, not elaboration or a netlist assertion. Conditional
branches and alternate implementations are unioned: e.g. both soc_mem models
are retained. Dependencies are extracted per module, never per whole file.
Comments and strings cannot create graph edges. Parameter pruning and generated
third-party hierarchy are checked by actual simulation/synthesis elsewhere.

The locally authored Ibex register file is an explicit external entry selected
by ibex_sources.sh, because the Ibex parent is fetched/generated outside these
source trees. A separate test checks that boundary when its parent is present.
Unbuilt standalone experiments remain visible in hw/known-unbuilt.txt.
"""
import pathlib
import re

import pytest

ROOT = pathlib.Path(__file__).resolve().parents[2]
RTL = ROOT / "hw/rtl"
SOC_RTL = ROOT / "hw/soc/rtl"
LEDGER = ROOT / "hw/known-unbuilt.txt"
ROOTS = ("tt_um_melihakbulut_nssoc", "soc_top")
EXTERNAL_ENTRY_POINTS = ("ibex_register_file_ff",)
# Preserve token separation when stripping comments and quoted strings.
COMMENT_RE = re.compile(r'"(?:\\.|[^"\\])*"|//[^\n]*|/\*.*?\*/', re.S)
MODULE_RE = re.compile(r"\bmodule\s+([A-Za-z_]\w*)\b(.*?)\bendmodule\b", re.S)


def _sources():
    return sorted([*RTL.rglob("*.v"), *SOC_RTL.rglob("*.v"),
                   *SOC_RTL.rglob("*.v.in")])


def _modules(sources):
    out = {}
    for path, text in sources:
        body = COMMENT_RE.sub(" ", text)
        for match in MODULE_RE.finditer(body):
            out.setdefault(match[1], []).append((path, match[2]))
    return out


def _declared():
    return _modules((f, f.read_text()) for f in _sources())


def _instantiations(text, known):
    body = COMMENT_RE.sub(" ", text)
    return {name for name in known if re.search(
        r"(?<![\w.])" + re.escape(name)
        + r"\s*(?:#\s*\(|[A-Za-z_]\w*\s*\()", body)}


def _reachable(modules, roots):
    assert all(root in modules for root in roots), "missing inventory root"
    reached, pending = set(), list(roots)
    while pending:
        name = pending.pop()
        if name in reached:
            continue
        reached.add(name)
        for _, body in modules[name]:
            pending.extend(_instantiations(body, modules) - reached)
    return reached


def _ledger():
    entries = {}
    if not LEDGER.is_file():
        return entries
    for line in LEDGER.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line or line.startswith("#"):
            continue
        name, _, why = line.partition("\t")
        assert name.strip() not in entries, f"duplicate unbuilt row: {name}"
        entries[name.strip()] = why.strip()
    return entries


def test_every_hw_rtl_module_is_built_or_declared_unbuilt():
    modules = _declared()
    assert modules, "no RTL modules found"
    reachable = _reachable(modules, ROOTS + EXTERNAL_ENTRY_POINTS)
    ledger = _ledger()
    orphans = sorted(set(modules) - reachable)
    undeclared = sorted(set(orphans) - set(ledger))
    assert not undeclared, (
        "RTL modules missing from hw/known-unbuilt.txt: " + ", ".join(undeclared))
    assert not (set(ledger) & reachable), "stale unbuilt row names a reachable module"
    assert not (set(ledger) - set(modules)), "unbuilt row names an absent module"
    # The CAN bridge is used in the enabled product profile. Probe experiments
    # must not make it look reachable by sharing a source file with a root.
    assert "soc_apb_wb" in _reachable(modules, ("soc_top",))


def test_every_unbuilt_row_carries_a_reason():
    for name, why in _ledger().items():
        assert len(why) > 40, f"{name}: an unbuilt module needs a specific reason"


def test_module_boundaries_comments_and_duplicate_variants():
    modules = _modules([
        ("a.v", """module top; live u(); endmodule
          module unused; hidden u(); endmodule
          // module fake; commented u(); endmodule
          module live; /* hidden u(); */ endmodule
          module hidden; endmodule"""),
        ("variant.v", 'module live; other u(); endmodule module other; endmodule'),
    ])
    assert "fake" not in modules
    assert _reachable(modules, ("top",)) == {"top", "live", "other"}
    assert len(modules["live"]) == 2


def test_register_file_external_entry_contract():
    # Clean-clone inventory has no fetched Ibex. Its selected replacement is
    # an explicit external entry, not an invented soc_top instantiation.
    source = (ROOT / "hw/soc/flow/ibex_sources.sh").read_text()
    assert 'echo "$soc_dir/rtl/ibex_regfile_secded.v"' in source
    generated = ROOT / "hw/soc/gen/ibex_top.v"
    if not generated.exists():
        pytest.skip("generated Ibex absent; elaborate the prepared SoC to verify this boundary")
    modules = _modules([(generated, generated.read_text())])
    assert "ibex_register_file_ff" in _instantiations(
        modules["ibex_top"][0][1], {"ibex_register_file_ff"})
