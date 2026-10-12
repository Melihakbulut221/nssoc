#!/usr/bin/env python3
# SPDX-FileCopyrightText: 2026 Hasan Melih Akbulut
# SPDX-License-Identifier: Apache-2.0
"""Real CMOS/resistor data interface experiment; unchanged downstream screens."""
import gzip
import hashlib
import json
from pathlib import Path
import re
import shutil
import subprocess
import tarfile
import numpy as np

ROOT = Path(__file__).resolve().parents[1]
CIRCUIT = ROOT / 'hw/soc/analog/pcie/tx_cmos_resistive_input_v1.inc'
SPEC = ROOT / 'docs/evidence/pcie-cmos-data-driver-input-20261013.json'
NAMES = ('ap', 'an', 'bp', 'bn')
VECTORS = ['v(dvdd)', 'i(vdvdd)'] + [v for n in NAMES for v in
           (f'v({n}0)', f'v(xad_{n}.drv)', f'v(xad_{n}.xbuf.net1)', f'v({n})')]


def sha(path):
    with Path(path).open('rb') as stream:
        return hashlib.file_digest(stream, 'sha256').hexdigest()


def prepare(deck, inputs, native, mode, pwl):
    assert mode in ('cmos_resistive', 'cmos_no_pullup')
    spec = json.loads(SPEC.read_text())
    pin = spec['receipt']
    packed = inputs / 'frontend.tar.gz'
    subprocess.run(['curl', '--fail', '--location', '--retry', '4', pin['url'], '-o', str(packed)], check=True)
    assert sha(packed) == pin['sha256'] and packed.stat().st_size == pin['bytes']
    dest = inputs / 'frontend'
    with tarfile.open(packed) as tar:
        tar.extractall(dest, filter='data')
    packed.unlink()
    manifest = json.loads((dest / 'manifest.json').read_text())
    assert all(sha(dest / n) == r['sha256'] for n, r in manifest['files'].items())
    assert sha(dest / 'psp103.osdi') == 'e4a50ec48e3fab3aa7af76f1d0816863c8aa06223e0efcded362ddadb49681a8'
    assert sha(dest / 'psp103_nqs.osdi') == '523382d47f1f747c991a938b2f93cc6d9bab27ebf44f708c4e995820dc0bee88'
    bits = native.sequence()
    for n in NAMES:
        values = bits[0::2] if n[0] == 'a' else bits[1::2]
        source = f'V{n} {n}0 0 ' + pwl(values, .6, .6, 2 * native.UI, n[1] == 'n')
        deck, count = re.subn(r'(?ms)^V' + n + r' [^\n]+ PWL\(.*?\)', lambda _: source, deck)
        assert count == 1
        old = f'R{n} {n}0 {n} 25'
        assert deck.count(old) == 1
        rail = 'avdd' if mode == 'cmos_resistive' else '0'
        deck = deck.replace(old, f'XAD_{n} {n}0 {n} {rail} dvdd 0 0 nssoc_tx_cmos_resistive_input_v1')
    additions = [f'.include "{dest / "buf16.inc"}"', f'.include "{CIRCUIT}"',
                 f'.lib "{dest / "models/cornerMOSlv.lib"}" mos_tt',
                 'VDVDD dvdd 0 PWL(0 0 1n 1.2)']
    deck = deck.replace('.control\n', '\n'.join(additions) + '\n.control\n' +
                        f'pre_osdi {dest / "psp103.osdi"}\npre_osdi {dest / "psp103_nqs.osdi"}\n' +
                        'save ' + ' '.join(VECTORS) + '\n', 1)
    deck = deck.replace('wrdata op.dat ', 'wrdata frontend-op.dat ' + ' '.join(VECTORS) + '\nwrdata op.dat ', 1)
    deck = deck.replace('wrdata wave.dat ', 'wrdata frontend-wave.dat ' + ' '.join(VECTORS) + '\nwrdata wave.dat ', 1)
    record = dict(mode=mode, source_sha256=sha(CIRCUIT), input_capsule_sha256=pin['sha256'],
        expected_devices=dict(mos=16, native_resistors=12),
        prospective_screen=dict(mos_terminal_abs_limit_v=1.32, sampled_common_mode_v=[1.80, 2.05],
                                minimum_sampled_differential_v=.15, input_source_rate_gbps=4.0),
        scope='Actual foundry CMOS data drivers and native passive network loaded by the final mux. Select clock still ideal. No complete serializer, rail-sink capability, independent rail startup, PVT, physical layout or foundry SOA claim.')
    return deck, record, [Path(__file__), CIRCUIT, SPEC]


def review(run, native):
    op = np.loadtxt(run / 'frontend-op.dat', skiprows=1)
    assert op.size == len(VECTORS) + 1 and np.isfinite(op).all() and np.max(np.abs(op)) <= 1e-10
    wave = run / 'frontend-wave.dat'
    data = np.loadtxt(wave, skiprows=1)
    assert data.shape[1] == len(VECTORS) + 1 and np.isfinite(data).all()
    t = data[:, 0]
    assert np.all(np.diff(t) > 0) and t[0] == 0 and t[-1] >= native.STOP - 1e-15
    v = dict(zip(VECTORS, data[:, 1:].T, strict=True))
    dvdd = v['v(dvdd)']
    devices = {}
    for name in NAMES:
        gate, drv, internal = (v[f'v({name}0)'], v[f'v(xad_{name}.drv)'], v[f'v(xad_{name}.xbuf.net1)'])
        for label, drain, control, source in [('XN1', internal, gate, 0), ('XN0', drv, internal, 0),
                                              ('XP1', drv, internal, dvdd), ('XP0', internal, gate, dvdd)]:
            peaks = {k: float(np.max(np.abs(a - b))) for k, a, b in
                     [('vds', drain, source), ('vgs', control, source), ('vgd', control, drain)]}
            devices[f'xad_{name}.xbuf.{label}'] = dict(peaks=peaks, passed=max(peaks.values()) <= 1.32)
    bits = native.sequence()
    observations = []
    for port, values in [('a', bits[0::2]), ('b', bits[1::2])]:
        p, n = v[f'v({port}p)'], v[f'v({port}n)']
        for i, bit in enumerate(values):
            for phase in (.3, .5, .7):
                time = native.START + (i + phase) * 2 * native.UI
                positive, negative = np.interp(time, t, p), np.interp(time, t, n)
                observations.append(((positive - negative) * (1 if bit else -1), (positive + negative) / 2))
    margins, common = np.asarray(observations).T
    active = t >= native.START
    current = v['i(vdvdd)']
    report = dict(status='MEASURED_NATIVE_CMOS_DATA_DRIVER_NOT_PHY_ACCEPTANCE', zero_source_op=True,
        devices=devices, samples=len(margins), minimum_margin_v=float(margins.min()),
        wrong_sign_samples=int((margins <= 0).sum()), below_150mv_samples=int((margins < .15).sum()),
        common_mode_range_v=[float(common.min()), float(common.max())],
        common_mode_outside_target_samples=int(((common < 1.8) | (common > 2.05)).sum()),
        mean_cmos_supply_power_w=float(np.trapezoid(-dvdd[active] * current[active], t[active]) / (t[-1] - t[active][0])),
        peak_reverse_supply_current_a=float(max(0, current.max())),
        reverse_supply_charge_c=float(np.trapezoid(np.maximum(current, 0), t)),
        note='Engineering terminal-voltage screen only. Native model convergence and downstream HBT/signal screens remain separate. Reverse rail current is reported, not presumed supportable by a real regulator.')
    report['engineering_screen_passed'] = (all(d['passed'] for d in devices.values()) and
        report['below_150mv_samples'] == report['common_mode_outside_target_samples'] == 0)
    raw_pin = dict(sha256=sha(wave), bytes=wave.stat().st_size)
    packed = wave.with_suffix('.dat.gz')
    with wave.open('rb') as src, gzip.open(packed, 'xb', compresslevel=1) as dst:
        shutil.copyfileobj(src, dst)
    with gzip.open(packed, 'rb') as src:
        digest = hashlib.file_digest(src, 'sha256').hexdigest()
    assert digest == raw_pin['sha256']
    report['lossless_raw_wave'] = raw_pin
    report['packed_sha256'] = sha(packed)
    wave.unlink()
    (run / 'frontend-review.json').write_text(json.dumps(report, indent=2) + '\n')
    return report
