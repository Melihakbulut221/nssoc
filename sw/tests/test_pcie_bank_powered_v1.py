# SPDX-FileCopyrightText: 2026 Hasan Melih Akbulut
# SPDX-License-Identifier: Apache-2.0
import ast
import gzip
import hashlib
import importlib.util
import os
from pathlib import Path
import sys
import threading

import pytest

SCRIPTS = Path(__file__).resolve().parents[2] / 'scripts'
sys.path.insert(0, str(SCRIPTS))
spec = importlib.util.spec_from_file_location('bank_powered_test', SCRIPTS / 'diagnose_pcie_bank_powered_v1.py')
d = importlib.util.module_from_spec(spec)
spec.loader.exec_module(d)


@pytest.mark.parametrize('lane', range(4))
def test_external_data_pair_is_complementary_with_fixed_common_mode(lane):
    p = [float(x) for x in d.input_wave(lane, True)[4:-1].split()]
    n = [float(x) for x in d.input_wave(lane, False)[4:-1].split()]
    assert p[0::2] == n[0::2]
    assert all(a < b for a, b in zip(p[0::2], p[2::2]))
    assert all(abs(a + b - 2.72) < 1e-14 for a, b in zip(p[3::2], n[3::2]))
    assert set(round(v, 2) for v in p[7::2]) == {1.28, 1.44}


def test_no_elapsed_timeout_or_forced_internal_state():
    tree = ast.parse(Path(d.__file__).read_text())
    calls = [n for n in ast.walk(tree) if isinstance(n, ast.Call)]
    assert all('timeout' not in {k.arg for k in n.keywords} for n in calls)
    assert not any(isinstance(n, ast.Constant) and isinstance(n.value, str) and
                   ('.nodeset' in n.value or '.ic ' in n.value or ' uic' in n.value) for n in ast.walk(tree))


def test_lossless_fifo_capture_without_full_raw_disk_copy(tmp_path):
    fifo = tmp_path / 'wave.fifo'; os.mkfifo(fifo)
    payload = b'time source\n' + b'0.001 1.0000000000000001\n' * 10000
    record = {}; output = tmp_path / 'wave.gz'
    reader = threading.Thread(target=d.stream_wave, args=(fifo, output, record))
    reader.start()
    with fifo.open('wb') as f:
        f.write(payload)
    reader.join()
    assert record['complete'] and record['raw_bytes'] == len(payload)
    assert record['raw_sha256'] == hashlib.sha256(payload).hexdigest()
    assert gzip.decompress(output.read_bytes()) == payload


def contract():
    return dict(vectors=['v(c)', 'v(e)', 'i(q)'],
                hbts=[dict(id=1, Nx=2, C='v(c)', E='v(e)', current='i(q)')],
                clock_inputs=[['v(c)', 'v(e)']], clock_drivers=[], sampler_outputs=[])


def write_wave(path, change=None):
    rows = [[i * 2e-12, 0.9, 0.1, 0.001] for i in range(2001)]
    if change == 'missing_end':
        rows.pop()
    elif change == 'time_gap':
        rows.pop(1500)
    elif change == 'time_reverse':
        rows[1300][0] = rows[1299][0]
    elif change == 'nan':
        rows[1200][1] = float('nan')
    elif change == 'missing_column':
        rows[1200].pop()
    elif change == 'vce_violation':
        rows[1500][1] = 1.8
    elif change == 'current_violation':
        rows[1500][3] = 0.02
    with gzip.open(path, 'wt') as f:
        f.write('time v(c) v(e) i(q)\n')
        for row in rows:
            f.write(' '.join(map(str, row)) + '\n')


def test_every_postsettling_sample_contributes_to_bounds(tmp_path):
    p = tmp_path / 'wave.gz'; write_wave(p)
    r = d.wave_measure(p, contract())
    assert r['samples'] == 2001 and r['active_samples'] == 1001
    assert r['min_vce'] == pytest.approx(0.8)
    assert r['peak_abs_current_per_emitter_a'] == pytest.approx(0.0005)
    assert r['signals'][0]['mean_frequency_hz'] is None  # No fake clock PASS.


@pytest.mark.parametrize('fault', ['missing_end', 'time_gap', 'time_reverse', 'nan', 'missing_column'])
def test_missing_or_corrupt_native_samples_fail_closed(tmp_path, fault):
    p = tmp_path / 'wave.gz'; write_wave(p, fault)
    with pytest.raises(ValueError):
        d.wave_measure(p, contract())


@pytest.mark.parametrize('fault,field,wanted', [('vce_violation', 'max_vce', 1.7),
                                               ('current_violation', 'peak_abs_current_per_emitter_a', 0.01)])
def test_bad_electrical_sample_is_preserved_not_reclassified_as_acceptance(tmp_path, fault, field, wanted):
    p = tmp_path / 'wave.gz'; write_wave(p, fault)
    r = d.wave_measure(p, contract())
    assert r[field] == pytest.approx(wanted)
    assert r['screen_bounds'] == dict(min_vce=0.4, max_vce=1.6, max_collector_current_per_emitter_a=0.003)
