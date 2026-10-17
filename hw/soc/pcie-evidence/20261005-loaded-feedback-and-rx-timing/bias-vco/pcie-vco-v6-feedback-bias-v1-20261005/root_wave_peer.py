# SPDX-FileCopyrightText: 2026 Hasan Melih Akbulut
# SPDX-License-Identifier: Apache-2.0
"""Independent NumPy reductions of archived native values; no producer imports."""
from pathlib import Path
import argparse
import gzip
import hashlib
import json
import re
import tarfile
import numpy as np

B = Path(__file__).resolve().parent
p = argparse.ArgumentParser()
p.add_argument('case')
a = p.parse_args()
manifest = json.loads((B / f'members-{a.case}.json').read_text())
validation = json.loads((B / f'validation-{a.case}.json').read_text())
archive = Path(validation['archive']['path'])


def pin(path):
    with Path(path).open('rb') as f:
        return {'bytes': Path(path).stat().st_size, 'sha256': hashlib.file_digest(f, 'sha256').hexdigest()}


assert pin(archive) == {k: validation['archive'][k] for k in ('bytes', 'sha256')}
actual, saved = {}, {}
with tarfile.open(archive, 'r|xz') as t:
    for m in t:
        assert m.isfile() and m.name not in actual
        f = t.extractfile(m)
        if m.name.startswith(f'native/nssoc-vco-v6-feedback-bias-v1-{a.case}/') and m.name.endswith(('/result.json', '/wave.raw.gz', '/run.log')):
            data = f.read()
            saved[m.name.rsplit('/', 1)[1]] = data
            digest = hashlib.sha256(data).hexdigest()
        else:
            digest = hashlib.file_digest(f, 'sha256').hexdigest()
        actual[m.name] = {'bytes': m.size, 'sha256': digest}
expected = {n: {k: row[k] for k in ('bytes', 'sha256')} for n, row in manifest.items()}
assert actual == expected, set(actual) ^ set(expected)
r = json.loads(saved['result.json'])
raw = gzip.decompress(saved['wave.raw.gz'])
assert len(raw) == r['raw_bytes'] and hashlib.sha256(raw).hexdigest() == r['raw_sha256']
header, rest = raw.split(b'Binary:\n', 1)
lines = header.decode().split('Variables:\n', 1)[1].splitlines()
names = []
for i, line in enumerate(lines):
    fields = line.split()
    assert int(fields[0]) == i
    name = fields[1].lower()
    names.append(name[2:-1] if name.startswith('i(@') else name)
assert names == r['columns'] and len(names) == len(set(names)) == 786
size = r['rows'] * len(names) * 8
assert rest[size:] == str(r['rows']).encode()
assert hashlib.sha256(rest[:size]).hexdigest() == r['payload_sha256']
data = np.frombuffer(rest[:size], dtype='<f8').reshape(r['rows'], -1)
assert np.isfinite(data).all()
cols = dict(zip(names, data.T))
t = cols['time']
assert t[0] == 0 and abs(t[-1] - 34e-9) <= 16 * np.spacing(34e-9)
assert np.all(np.diff(t) > 0) and np.diff(t).max() <= 5e-12 * (1 + 1e-5)
active = (t >= 4e-9) & (t <= 34e-9)


def volts(node):
    return np.zeros(len(t)) if node == '0' else cols[f'v({node})']


def near(x, y):
    assert np.isclose(x, y, rtol=2e-13, atol=1e-18), (x, y)


bounds = {x['path']: x for x in r['safety']['all_device_bounds']}
assert len(bounds) == len(r['devices']) == 437
measured = []
for device in r['devices']:
    path, model, nets = (device[k] for k in ('path', 'model', 'nets'))
    old = bounds[path]
    assert model == old['model']
    row = {'path': path, 'model': model}
    if model == 'npn13g2':
        vce = volts(nets[0]) - volts(nets[2])
        nx = int(device['params']['nx'])
        assert 1 <= nx <= 10
        row.update(min_settled_vce=float(vce[active].min()), max_capture_vce=float(vce.max()), max_capture_ic_per_nx=float(np.abs(cols[f'@q.{path}.qnpn13g2[ic]']).max()) / nx)
        row['passed'] = row['min_settled_vce'] >= .4 and row['max_capture_vce'] <= 1.6 and row['max_capture_ic_per_nx'] <= .003
    elif model.startswith('sg13_'):
        params = device['params']
        assert params['w'].endswith('u') and params['l'].endswith('u')
        w, length = float(params['w'][:-1]), float(params['l'][:-1])
        lv = '_lv_' in model
        assert params['ng'] == params['m'] == '1'
        assert (.15 if lv else .3) <= w <= 10
        assert (.13 if lv else .4 if 'pmos' in model else .45) <= length <= 10
        terminals = np.stack([volts(n) for n in nets])
        span = float((terminals.max(axis=0) - terminals.min(axis=0)).max())
        amps = float(np.abs(cols[f'@n.{path}.n{model}[ids]']).max()) / w
        row.update(max_capture_terminal_difference=span, max_capture_drain_per_um=amps, voltage_limit=1.5 if lv else 3.3)
        row['passed'] = span <= row['voltage_limit'] and amps <= .002
    else:
        assert model in ('rppd', 'cap_cmim', 'ntap1', 'ptap1')
        span = float(np.abs(volts(nets[0]) - volts(nets[1])).max())
        row.update(max_capture_terminal_difference=span, voltage_limit=3.3, passed=span <= 3.3)
        if model in ('ntap1', 'ptap1'):
            row.update(inferred_ohmic_peak_a=span / float(device['params']['r']), contact_current_qualified=False)
    for k, v in row.items():
        if isinstance(v, float):
            near(v, old[k])
        else:
            assert v == old[k], (path, k)
    measured.append(row)
assert all(x['passed'] for x in measured) == r['safety']['passed']


def crossings(y, level):
    idx = np.flatnonzero((y[:-1] < level) & (y[1:] >= level))
    x = t[idx] + (level - y[idx]) / (y[idx + 1] - y[idx]) * (t[idx + 1] - t[idx])
    return x[(x >= 4e-9) & (x < 34e-9)]


osc = crossings(cols['v(clkp)'] - cols['v(clkn)'], 0)
q = crossings(cols['v(qp)'] - cols['v(qn)'], 0)
fb = crossings(cols['v(fb)'], 1.25)
periods = {}
for name, edges in [('native_hbt_div4', q), ('whole_native_div80', fb)]:
    counts = [int(np.sum((osc >= x) & (osc < y))) for x, y in zip(edges[:-1], edges[1:])]
    assert counts == r['measurement']['actual_vco_period_counts'][name]
    periods[name] = counts
frequencies = {}
for name, edges in [('vco_frequency_hz', osc), ('feedback_frequency_hz', fb)]:
    hz = float(1 / np.mean(np.diff(edges))) if len(edges) >= 2 else None
    if hz is not None:
        near(hz, r['measurement'][name])
    else:
        assert r['measurement'][name] is None
    frequencies[name] = hz
cycles = []
diff = cols['v(clkp)'] - cols['v(clkn)']
for x, y in zip(osc[:-1], osc[1:]):
    values = diff[(t >= x) & (t <= y)]
    cycles.append({'start_s': float(x), 'end_s': float(y), 'minimum_v': float(values.min()), 'maximum_v': float(values.max())})
flags = re.findall(r'NSSOC_NATIVE_FLAG_BEGIN ([^\s]+)(.*?)NSSOC_NATIVE_FLAG_END', saved['run.log'].decode(), flags=re.S)
assert len(flags) == len({x[0] for x in flags}) == 64
for name, body in flags:
    assert re.search(r'^\s*off\s+1\s*$', body, flags=re.M), (name, body[-200:])
out = {'status': 'PASS_INDEPENDENT_ALL_RAW_VALUES_AND_437_DEVICE_REDUCTION', 'method': pin(__file__), 'case': a.case, 'archive': {'path': str(archive), **pin(archive)}, 'members_rehashed': len(actual), 'raw_sha256': hashlib.sha256(raw).hexdigest(), 'rows': len(t), 'columns': len(names), 'values': data.size, 'all_device_bounds': measured, 'native_off_flags': len(flags), 'frequencies': frequencies, 'actual_period_counts': periods, 'complete_cycles': cycles, 'all_complete_cycles_signed300mV': all(c['minimum_v'] <= -.3 and c['maximum_v'] >= .3 for c in cycles), 'source_native_status_unchanged': r['status'], 'scope': 'Independent arithmetic over every archived binary sample, exact native graph records, declared finite electrical screens and real clock edge counts. No producer measurement imports, no native rerun, no new foundry SOA/contact-current/PEX/PVT/thermal/closed-PLL/mainchip acceptance.'}
(B / f'root-wave-peer-{a.case}.json').write_text(json.dumps(out, indent=2) + '\n')
print(out['status'], len(measured), len(cycles), frequencies)
