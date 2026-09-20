# SPDX-FileCopyrightText: 2026 Hasan Melih Akbulut
# SPDX-License-Identifier: Apache-2.0
"""The interface flow must retain the upstream router and apply cleanup once."""
import importlib.util
from pathlib import Path
import shutil
import subprocess
import sys
from types import ModuleType, SimpleNamespace

import pytest

ROOT = Path(__file__).resolve().parents[2]


@pytest.fixture
def flow(tmp_path, monkeypatch):
    """Stub only LibreLane's class registry, not the script transformation."""
    script = tmp_path / "upstream.tcl"
    script.write_text("set before 1\nread_current_odb\n\nset after 2\n")

    class DetailedRouting:
        def get_script_path(self):
            return str(script)

    cts = type("PostCTS", (), {})
    grt = type("PostGRT", (), {})
    openroad = SimpleNamespace(ResizerTimingPostCTS=cts, ResizerTimingPostGRT=grt,
                               DetailedRouting=DetailedRouting)
    classic = type("Classic", (), {"Steps": [cts, grt, DetailedRouting], "gating_config_vars": {}})
    registry = SimpleNamespace(factory=SimpleNamespace(register=lambda: lambda cls: cls))
    for name, attrs in {
        "librelane": {"__path__": []},
        "librelane.flows": {"Flow": registry, "__path__": []},
        "librelane.flows.classic": {"Classic": classic},
        "librelane.steps": {"OpenROAD": openroad},
    }.items():
        module = ModuleType(name)
        module.__dict__.update(attrs)
        monkeypatch.setitem(sys.modules, name, module)
    spec = importlib.util.spec_from_file_location("tested_interface_flow", ROOT / "hw/soc/pnr/interface_flow.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    instance = module.CleanOrphanGuides()
    instance.step_dir = tmp_path
    return module, instance, script


def test_upstream_body_preserved_with_one_cleanup_after_database_read(flow):
    module, instance, script = flow
    original = script.read_text()
    output = Path(instance.get_script_path()).read_text()
    start = original.index("read_current_odb\n") + len("read_current_odb\n")
    added_and_tail = output[start:].splitlines(keepends=True)
    assert added_and_tail[0].startswith('source "')
    assert added_and_tail[1] == 'puts "REMOVED_ORPHAN_GUIDES [prune_orphan_guides [ord::get_db_block]]"\n'
    assert output[:start] + "".join(added_and_tail[2:]) == original
    assert sum(step is module.CleanOrphanGuides for step in module.Interfaces.Steps) == 1


@pytest.mark.parametrize("text", ["# no database load\n", "read_current_odb\nread_current_odb\n"])
def test_template_drift_fails_before_a_router_script_is_written(flow, text):
    _, instance, script = flow
    script.write_text(text)
    with pytest.raises(RuntimeError, match="Unsupported LibreLane routing script"):
        instance.get_script_path()
    assert not (Path(instance.step_dir) / "clean_orphan_guides_drt.tcl").exists()


def test_missing_cleanup_dependency_rejected(flow, tmp_path, monkeypatch):
    module, instance, _ = flow
    monkeypatch.setattr(module, "__file__", str(tmp_path / "missing/pnr/interface_flow.py"))
    with pytest.raises(RuntimeError, match="Missing guide cleanup script"):
        instance.get_script_path()


def test_literal_helper_path_is_not_tcl_substitution(flow, tmp_path, monkeypatch):
    tclsh = shutil.which("tclsh")
    if not tclsh:
        pytest.skip("tclsh is required to execute the generated flow script")
    module, instance, _ = flow
    # A literal path containing Tcl metacharacters must not execute commands
    # or expand variables. The fake helper exposes whether source succeeded.
    soc = tmp_path / 'space $missing[error unexpected]"\\literal'
    helper = soc / "flow/prune_orphan_guides.tcl"
    helper.parent.mkdir(parents=True)
    helper.write_text("proc prune_orphan_guides {block} {return 7}\n")
    monkeypatch.setattr(module, "__file__", str(soc / "pnr/interface_flow.py"))
    script = Path(instance.get_script_path()).read_text()
    script = 'proc read_current_odb {} {}\nnamespace eval ord {proc get_db_block {} {return block}}\n' + script
    script += 'puts "BODY_RETAINED $before $after"\n'
    result = subprocess.run([tclsh], input=script, capture_output=True, text=True)
    assert result.returncode == 0 and not result.stderr, result.stderr
    assert "REMOVED_ORPHAN_GUIDES 7" in result.stdout
    assert "BODY_RETAINED 1 2" in result.stdout
