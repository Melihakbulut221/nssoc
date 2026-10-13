# SPDX-FileCopyrightText: 2026 Hasan Melih Akbulut
# SPDX-License-Identifier: Apache-2.0
"""Final reconstruction must not silently omit an unfinished archive family."""
import importlib.util
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / 'scripts'))
spec = importlib.util.spec_from_file_location('finalize', ROOT / 'scripts/finish_cloud_output_migration.py')
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)


def test_both_finished_families_required():
    complete = {p.name: {'status': module.COMPLETE} for p in module.STATES}
    assert module.transfers_complete(complete)
    assert not module.transfers_complete({})
    for name in complete:
        partial = {key: dict(value) for key, value in complete.items()}
        partial[name]['status'] = 'RUNNING'
        assert not module.transfers_complete(partial)
        del partial[name]
        assert not module.transfers_complete(partial)
    assert not module.transfers_complete(dict(complete, unexpected={'status': module.COMPLETE}))


def test_recover_exact_request_and_reject_ambiguity(monkeypatch):
    import json
    rows = [{'databaseId': 100, 'displayTitle': 'cloud-output-restore unrelated'},
            {'databaseId': 200, 'displayTitle': 'cloud-output-restore ' + module.REQUEST}]
    monkeypatch.setattr(module.subprocess, 'check_output', lambda *args, **kwargs: json.dumps(rows))
    assert module.find_run() == 200
    rows.append(dict(rows[1], databaseId=300))
    import pytest
    with pytest.raises(RuntimeError, match='Ambiguous'):
        module.find_run()
    rows.clear()
    assert module.find_run() is None
