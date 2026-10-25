# SPDX-FileCopyrightText: 2026 Hasan Melih Akbulut
# SPDX-License-Identifier: Apache-2.0
"""Failures in the tool/PDK smoke receipt cannot become physical passes."""
import importlib.util
import json
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
spec = importlib.util.spec_from_file_location('flow_smoke', ROOT/'scripts/check_flow_smoke.py')
smoke = importlib.util.module_from_spec(spec)
spec.loader.exec_module(smoke)


@pytest.mark.parametrize('change', ['pass', 'version', 'missing_tool', 'download',
                                  'wrong_pin', 'flow', 'missing_gds', 'empty_def'])
def test_record_requires_tools_exact_enabled_pin_and_real_views(tmp_path, monkeypatch, change):
    monkeypatch.setattr(smoke, 'ROOT', tmp_path)
    package = tmp_path/'package'; package.mkdir()
    (package/'pdk_hashes.yaml').write_text('ihp-sg13g2: '+40*'a'+'\n')
    binary = package/'tool'; binary.write_text('test fixture, not executable\n')
    monkeypatch.setattr(smoke.importlib.metadata, 'version', lambda _: 'wrong' if change == 'version' else '3.0.5')
    monkeypatch.setattr(smoke.importlib.util, 'find_spec', lambda _: type('Spec', (), {'origin': str(package/'__init__.py')}))
    monkeypatch.setattr(smoke.shutil, 'which', lambda tool: None if change == 'missing_tool' and tool == 'magic' else str(binary))
    out = tmp_path/'hw/soc/out/test'
    pdk = tmp_path/'hw/soc/tools/pdk'
    calls = []

    def run(command, cwd, log):
        calls.append(command)
        log.write_text('fixture log\n')
        if command[0] == 'ciel':
            if change == 'download':
                return {'returncode': 1}
            enabled = pdk/'ciel/ihp-sg13g2/versions'/((40*'b') if change == 'wrong_pin' else 40*'a')/'ihp-sg13g2'
            enabled.mkdir(parents=True)
            (pdk/'ihp-sg13g2').symlink_to(enabled)
        if '--run-example' in command:
            if change == 'flow':
                return {'returncode': 1}
            final = out/'spm/runs/BOOTSTRAP/final'; final.mkdir(parents=True)
            for suffix in ['gds', 'def', 'v']:
                if change == 'missing_gds' and suffix == 'gds':
                    continue
                (final/('spm.'+suffix)).write_text('' if change == 'empty_def' and suffix == 'def' else 'fixture view\n')
        return {'returncode': 0, 'command': command}

    monkeypatch.setattr(smoke, 'run_command', run)
    result = smoke.check(out, pdk)
    assert result == json.loads((out/'result.json').read_text())
    assert result['status'] == ('PASS' if change == 'pass' else 'FAIL')
    if change == 'pass':
        assert len(result['views']) == 3 and len(calls) == 5
        assert calls[-1][-2:] == ['--run-example', 'spm']
    elif change in ('version', 'missing_tool'):
        assert not calls
    elif change in ('download', 'wrong_pin'):
        assert not any('--run-example' in c for c in calls)


@pytest.mark.parametrize('text', ['', 'ihp-sg13g2: main\n', 'ihp-sg13g2: '+40*'a'+'\nihp-sg13g2: '+40*'b'])
def test_pin_rejects_missing_moving_and_duplicate_values(text):
    with pytest.raises(ValueError):
        smoke.pdk_pin(text)


def test_output_paths_preserve_existing_data_and_reject_symlink_escape(tmp_path):
    parent = tmp_path/'allowed'; parent.mkdir()
    old = parent/'old'; old.write_text('retained')
    with pytest.raises(ValueError):
        smoke.fresh_path(old, parent)
    assert old.read_text() == 'retained'
    (parent/'link').symlink_to(tmp_path)
    with pytest.raises(ValueError):
        smoke.fresh_path(parent/'link/outside', parent)
    with pytest.raises(ValueError):
        smoke.fresh_path(parent, parent)
