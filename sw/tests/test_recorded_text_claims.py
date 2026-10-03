# SPDX-FileCopyrightText: 2026 Hasan Melih Akbulut
# SPDX-License-Identifier: Apache-2.0
"""A recovered log cannot conceal tampering or a changed live result."""
import hashlib
import importlib.util
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
spec = importlib.util.spec_from_file_location('recorded_text_claims', ROOT / 'paper/check_claims.py')
claims = importlib.util.module_from_spec(spec)
spec.loader.exec_module(claims)


@pytest.fixture
def isolated(tmp_path, monkeypatch):
    claim = next(c for c in claims.load(ROOT / 'paper/claims.yaml')
                 if c['id'] == 'decks.lvs_matches')
    blob = (ROOT / claim['recorded_file']).read_bytes()
    record = tmp_path / claim['recorded_file']
    record.parent.mkdir(parents=True)
    record.write_bytes(blob)
    monkeypatch.setattr(claims, 'ROOT', tmp_path)
    return claim, record


def test_original_lvs_stdout_reproduces_one_historical_match(isolated):
    claim, record = isolated
    assert hashlib.sha256(record.read_bytes()).hexdigest() == claim['recorded_sha256']
    state, detail = claims.check(claim)
    assert state == 'PASS'
    assert 'historical recorded log; not a new LVS run' in detail
    assert claims.check({**claim, 'value': 2})[0] == 'FAIL'


def test_changed_record_cannot_pass_even_with_same_match_count(isolated):
    claim, record = isolated
    record.write_bytes(record.read_bytes() + b'altered output\n')
    assert claims.check(claim) == ('FAIL', 'recorded text artifact digest mismatch')


def test_changed_live_log_is_not_hidden_by_successful_record(isolated, tmp_path):
    claim, record = isolated
    live = tmp_path / 'hw/soc/pnr/runs/s77lvs-b-blackbox/01-netgen-lvs/netgen-lvs.log'
    live.parent.mkdir(parents=True)
    live.write_text('Netlists do not match.\n')
    assert claims.check(claim) == ('FAIL', 'live text artifact differs from its recorded original')
    live.write_bytes(record.read_bytes())
    state, detail = claims.check(claim)
    assert state == 'PASS'
    assert 'historical recorded log' not in detail


def test_missing_committed_log_is_failure_not_absent_run_skip(isolated):
    claim, record = isolated
    record.unlink()
    assert claims.check(claim) == ('FAIL', 'recorded text artifact missing')
