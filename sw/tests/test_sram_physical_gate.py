# SPDX-FileCopyrightText: 2026 Hasan Melih Akbulut
# SPDX-License-Identifier: Apache-2.0
"""Incomplete or unsuccessful independent decks cannot yield a green exit."""
import hashlib
import json
from pathlib import Path
import subprocess
import sys

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / 'hw/soc/flow'))
import check_sram_core_physical as gate


@pytest.mark.parametrize('cases,expected', [
    ([(0, 'PASS')]*3, 0),
    ([(1, 'FAIL'), (0, 'PASS'), (0, 'PASS')], 1),
    ([(0, 'PASS'), (2, 'ERROR'), (0, 'PASS')], 1),
    ([(0, 'PASS'), (0, 'PASS'), (1, 'PASS')], 1),
])
def test_all_decks_and_processes_required(tmp_path, monkeypatch, cases, expected):
    scripts = tmp_path/'hw/soc/flow'
    scripts.mkdir(parents=True)
    for name in ['check_sram_core_physical.py', 'check_ihp_drc.py',
                 'check_ihp_drc_partitioned.py', 'prepare_ihp_drc.py', 'bounded_process.py']:
        (scripts/name).write_text('test source')
    (tmp_path/'hw/soc/pnr').mkdir()
    (tmp_path/'hw/soc/pnr/ihp-drc.lock.json').write_text('{}')
    (tmp_path/'hw/soc/out').mkdir()
    gds = tmp_path/'source.gds'
    gds.write_bytes(b'synthetic gate input')
    receipt = tmp_path/'receipt.json'
    receipt.write_text(json.dumps(dict(status='PASS_BOUND_FULL_CHIP_SRAM_INTEGRATION_LVS',
        final_views={'klayout_gds': {'sha256': hashlib.sha256(gds.read_bytes()).hexdigest()}})))
    monkeypatch.setattr(gate, '__file__', str(scripts/'check_sram_core_physical.py'))
    monkeypatch.setattr(sys, 'argv', ['gate', '--gds', str(gds), '--receipt', str(receipt),
                                    '--tag', 'synthetic'])
    results = iter(cases)

    def simulated_deck(command, **kwargs):
        code, status = next(results)
        tag = command[command.index('--tag')+1]
        folder = tmp_path/'hw/soc/out'/tag
        folder.mkdir()
        (folder/'result.json').write_text(json.dumps({'status': status}))
        return subprocess.CompletedProcess(command, code)

    monkeypatch.setattr(gate, 'bounded_run', simulated_deck)
    with pytest.raises(SystemExit) as result:
        gate.main()
    assert result.value.code == expected
    recorded = json.loads((tmp_path/'hw/soc/out/synthetic/result.json').read_text())
    assert len(recorded['cases']) == 3
    assert recorded['manufacturing_acceptance'] is False
    assert (recorded['status'] == 'PASS_ALL_THREE_PHYSICAL_DECKS') == (expected == 0)
