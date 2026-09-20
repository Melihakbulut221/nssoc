# SPDX-FileCopyrightText: 2026 Hasan Melih Akbulut
# SPDX-License-Identifier: Apache-2.0
"""A successful make exit alone cannot certify a fresh formal sweep."""
import importlib.util
import json
from pathlib import Path
import sys

import pytest

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "scripts"))
spec = importlib.util.spec_from_file_location("formal_sweep", ROOT / "scripts/check_formal_sweep.py")
sweep = importlib.util.module_from_spec(spec)
spec.loader.exec_module(sweep)


@pytest.fixture
def prepared(tmp_path, monkeypatch):
    for area in ("formal", "hw/soc/formal"):
        (tmp_path / area).mkdir(parents=True)
        (tmp_path / area / "demo.sby").write_text("[tasks]\nprove flags\ncover\n[options]\n")
    (tmp_path / "hw/soc/formal/sweep-policy.json").write_text(json.dumps({
        "excluded_jobs": {}, "excluded_tasks": {"demo.sby:cover": "explicit fixture exception"}}))
    gen = tmp_path / "hw/soc/gen"
    gen.mkdir()
    (gen / "ibex_register_file_ff.v").write_text("module fixture; endmodule\n")
    monkeypatch.setattr(sweep, "ROOT", tmp_path)
    def git_output(command, **kwargs):
        if "ls-files" in command:
            return b"formal/demo.sby\0hw/soc/formal/demo.sby\0hw/soc/formal/sweep-policy.json\0"
        return "a" * 40 + "\n"
    monkeypatch.setattr(sweep.subprocess, "check_output", git_output)
    monkeypatch.setattr(sys, "argv", ["check_formal_sweep.py"])
    return tmp_path


def test_new_task_is_mandatory_and_exception_remains_visible(prepared):
    expected, excluded = sweep.inventory(prepared)
    assert len(expected) == 3 and len(excluded) == 1
    p = prepared / "formal/demo.sby"
    p.write_text(p.read_text().replace("cover\n", "cover\nprove_new\n"))
    new, exclusions = sweep.inventory(prepared)
    assert "formal/demo_prove_new" in new
    assert exclusions == excluded


@pytest.mark.parametrize("defect", [None, "missing", "stale", "unchecked", "drift", "timeout"])
def test_full_sweep_rejects_incomplete_or_stale_results(prepared, monkeypatch, defect):
    expected, _ = sweep.inventory(prepared)
    def run(command, log, env, limit):
        log.write_text("fixture run\n")
        for path in expected:
            p = prepared / path
            if defect == "missing" and path == "formal/demo_cover": continue
            p.mkdir(exist_ok=True)
            (p / "status").write_text("PASS 0 0\n")
            (p / "logfile.txt").write_text("fixture proof\n")
        if defect == "drift": (prepared / "formal/demo.sby").write_text("changed")
        return dict(command=command, returncode=124 if defect == "timeout" else 0, elapsed_s=0)
    monkeypatch.setattr(sweep, "run", run)
    monkeypatch.setattr(sweep, "source_state", lambda p: defect if defect in ("stale", "unchecked") else "clean")
    if defect is None:
        sweep.main()
    else:
        with pytest.raises(RuntimeError): sweep.main()
    result = json.loads((prepared / "hw/soc/out/formal-sweep/result.json").read_text())
    assert result["passed"] is (defect is None)
    assert len(result["tasks"]) == 3 and len(result["exclusions"]) == 1
    if defect == "timeout":
        assert len(result["stages"]) == 2
        assert all(stage["returncode"] == 124 for stage in result["stages"])
    assert all("-k" in stage["command"] for stage in result["stages"])


def test_old_formal_output_is_rejected_before_execution(prepared, monkeypatch):
    old = prepared / "formal/demo_prove"
    old.mkdir()
    (old / "config.sby").write_text("old")
    monkeypatch.setattr(sweep, "run", lambda *args: pytest.fail("must not execute"))
    with pytest.raises(SystemExit) as error:
        sweep.main()
    assert error.value.code == 2
    assert not (prepared / "hw/soc/out/formal-sweep").exists()


def test_default_scrub_target_invokes_every_nonexcluded_declared_task():
    import re
    config=ROOT/'hw/soc/formal/regfile_scrub_abs.sby'
    required={row['task'] for row in sweep.inventory(ROOT)[0].values()
              if row['config']==str(config.relative_to(ROOT))}
    makefile=(ROOT/'hw/soc/formal/Makefile').read_text()
    selected=set(re.search(r'^REGFILESCRUB_TASKS := (.+)$',makefile,re.M).group(1).split())
    assert required==selected=={'prove','prove_pdr','cover','bmc'}
