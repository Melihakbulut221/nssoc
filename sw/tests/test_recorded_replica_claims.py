# SPDX-FileCopyrightText: 2026 Hasan Melih Akbulut
# SPDX-License-Identifier: Apache-2.0
"""The paper's placement claims must execute the original geometry measurement."""
import importlib.util
import json
from pathlib import Path
import subprocess
import sys

import pytest

ROOT = Path(__file__).resolve().parents[2]
spec = importlib.util.spec_from_file_location('recorded_paper_claims', ROOT / 'paper/check_claims.py')
claims = importlib.util.module_from_spec(spec)
spec.loader.exec_module(claims)


@pytest.fixture(scope='module')
def real_measurement():
    result = subprocess.run([sys.executable, 'scripts/measure_recorded_replicas.py'],
                            cwd=ROOT, text=True, capture_output=True, check=True)
    assert json.loads(result.stdout)['flops_per_replica'] == {
        'u_pilot.u_cfg_a': 55, 'u_pilot.u_cfg_b': 55, 'u_pilot.u_cfg_c': 55}
    return result


def test_all_six_paper_claims_rederive_the_original_placement(real_measurement, monkeypatch):
    selected = [c for c in claims.load(ROOT / 'paper/claims.yaml')
                if c['id'].startswith('replica.')]
    assert len(selected) == 6
    monkeypatch.setattr(claims, 'run', lambda command: real_measurement)
    for claim in selected:
        assert claim['cmd'] == 'python3 scripts/measure_recorded_replicas.py'
        assert not claim.get('needs_run_tree')
        state, detail = claims.check(claim)
        assert state == 'PASS', detail
        assert 'original signoff-6x2' in detail and 'not a current-layout' in detail
        wrong = {**claim, 'value': float(claim['value']) + 1}
        assert claims.check(wrong)[0] == 'FAIL'


@pytest.mark.parametrize('source', [None, '', 42])
def test_unqualified_measurement_cannot_pass(real_measurement, monkeypatch, source):
    data = json.loads(real_measurement.stdout)
    data['_recorded_scope'] = source
    monkeypatch.setattr(claims, 'run', lambda command: subprocess.CompletedProcess(
        command, 0, json.dumps(data), ''))
    claim = next(c for c in claims.load(ROOT / 'paper/claims.yaml')
                 if c['id'] == 'replica.min_c2c_um')
    assert claims.check(claim) == ('FAIL', 'measurement source missing from output')
