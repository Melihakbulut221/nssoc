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

    cts = type("PostCTS", (DetailedRouting,), {})
    grt = type("PostGRT", (DetailedRouting,), {})
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


@pytest.mark.parametrize('step_name', ['BoundedPostCTS', 'BoundedPostGRT'])
@pytest.mark.parametrize('derate', ['5', '5.0'])
def test_native_resizer_rejects_truncation_before_database_load(flow, step_name, derate, tclsh):
    module, _, script = flow
    original = ('proc read_current_odb {} {puts DATABASE_READ}\n'
                'read_current_odb\nset setup_args {}\nlappend setup_args -setup\n'
                'puts "ARGS $setup_args"\n')
    script.write_text(original)
    step = getattr(module, step_name)()
    step.step_dir = script.parent
    output = Path(step.get_script_path())
    runner = script.parent / 'run_guarded.tcl'
    runner.write_text(f'set ::env(TIME_DERATING_CONSTRAINT) {derate}\n' + output.read_text())
    result = subprocess.run([tclsh, str(runner)], capture_output=True, text=True)
    if derate == '5':
        assert result.returncode != 0
        assert 'loses precision' in result.stderr
        assert 'DATABASE_READ' not in result.stdout
    else:
        assert result.returncode == 0, result.stderr
        assert 'early=0.95 late=1.05' in result.stdout
        assert 'DATABASE_READ' in result.stdout
        assert 'ARGS -setup -max_iterations 600' in result.stdout
    assert script.read_text() == original


@pytest.mark.parametrize('selection,code', [('project', 74), ('override', 75),
                                          ('fallback', 73), ('missing-override', 127)])
def test_direct_layout_preparation_selects_python_before_any_synthesis(tmp_path, selection, code):
    import os
    # Run the actual shell entrypoint in an isolated project. The selected
    # interpreter records its arguments then deliberately stops preparation;
    # neither synthesis nor layout can run in this test.
    script = tmp_path / 'hw/soc/flow/implement_interfaces.sh'
    script.parent.mkdir(parents=True)
    shutil.copyfile(ROOT / 'hw/soc/flow/implement_interfaces.sh', script)
    project_python = tmp_path / '.venv/bin/python'
    fallback_python = tmp_path / 'bin/python3'
    override_python = tmp_path / 'explicit-python'
    for path, status in [(fallback_python, 73), (project_python, 74), (override_python, 75)]:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text('#!/bin/sh\nprintf "%s\\n" "$@" > "$NSSOC_TEST_PY_LOG"\nexit '+str(status)+'\n')
        path.chmod(0o755)
    env = {k: v for k, v in os.environ.items() if k not in ('PYTHON', 'INTERFACE_PYTHON')}
    log = tmp_path / 'interpreter.log'
    env.update(PATH=str(fallback_python.parent)+os.pathsep+env['PATH'],
               SOC_INTERFACE_PROFILE='full', NSSOC_TEST_PY_LOG=str(log))
    if selection == 'fallback': project_python.unlink()
    elif selection == 'override': env['INTERFACE_PYTHON'] = str(override_python)
    elif selection == 'missing-override': env['INTERFACE_PYTHON'] = str(tmp_path/'absent-python')
    result = subprocess.run(['bash', str(script), 'python-contract'], env=env,
                            capture_output=True, text=True)
    assert result.returncode == code, result.stdout + result.stderr
    assert not (tmp_path/'hw/soc/out/python-contract.inputs.json').exists()
    if selection == 'missing-override':
        assert not log.exists()
    else:
        assert log.read_text().splitlines() == [str(script.parent/'prepare_interfaces.py'),
                                               '--profile', 'full']
