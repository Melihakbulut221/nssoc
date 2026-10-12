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
HV_CIRCUIT = ROOT / 'hw/soc/analog/pcie/tx_cmos_hv_resistive_input_v2.inc'
LIGHT_CIRCUIT = ROOT / 'hw/soc/analog/pcie/tx_cmos_hv_resistive_input_v3.inc'
DIRECT_CIRCUIT = ROOT / 'hw/soc/analog/pcie/tx_cmos_hv_current_input_v4.inc'
SPEC = ROOT / 'docs/evidence/pcie-cmos-data-driver-input-20261013.json'
NAMES = ('ap', 'an', 'bp', 'bn')
VECTORS = ['v(dvdd)', 'i(vdvdd)'] + [v for n in NAMES for v in
           (f'v({n}0)', f'v(xad_{n}.drv)', f'v(xad_{n}.xbuf.net1)', f'v({n})')]


def sha(path):
    with Path(path).open('rb') as stream:
        return hashlib.file_digest(stream, 'sha256').hexdigest()


def original_bit_output_screen(t, positive, negative, bits, start, ui):
    """Compare final TX output to source bits, never to delayed mux inputs."""
    t, positive, negative = (np.asarray(x, dtype=float) for x in (t, positive, negative))
    bits = np.asarray(bits)
    assert t.ndim == 1 and len(t) >= 2 and positive.shape == negative.shape == t.shape
    assert np.isfinite(t).all() and np.isfinite(positive).all() and np.isfinite(negative).all()
    assert np.all(np.diff(t) > 0)
    assert bits.ndim == 1 and len(bits) and np.isin(bits, [0, 1]).all()
    assert np.isfinite(start) and np.isfinite(ui) and ui > 0
    phases = (.3, .5, .7)
    times = start + (np.arange(len(bits))[:, None] + np.asarray(phases)) * ui
    assert times.min() >= t[0] and times.max() <= t[-1], 'Incomplete original-bit output coverage'
    measured = np.interp(times, t, positive) - np.interp(times, t, negative)
    margins = measured * (2 * bits[:, None].astype(float) - 1)

    def counts(values):
        return dict(samples=int(values.size), minimum_margin_v=float(values.min()),
                    wrong_sign_samples=int((values <= 0).sum()),
                    below_100mv_samples=int((values < .1).sum()))

    return dict(**counts(margins), phases={str(p): counts(margins[:, i]) for i, p in enumerate(phases)},
                passed=bool((margins >= .1).all()),
                source_bits_sha256=hashlib.sha256(bytes(int(b) for b in bits)).hexdigest(),
                method='All original source bits at unchanged 0.3/0.5/0.7 UI; 100mV limit. No fitted latency, resampling phase adjustment, or actual-input-derived oracle.')


def half_cycle_launch(pwl, start, stop, ui):
    """Explicit prospective A-bank input contract; output oracle is untouched."""
    assert pwl.startswith('PWL(') and pwl.endswith(')')
    pairs = [tuple(map(float, line.lstrip('+ ').split())) for line in pwl[4:-1].splitlines() if line.strip()]
    assert all(len(pair) == 2 for pair in pairs)
    shifted = [(t - ui if start <= t < stop else t, v) for t, v in pairs]
    assert all(b[0] > a[0] for a, b in zip(shifted, shifted[1:]))
    return 'PWL(\n+ ' + '\n+ '.join(f'{t:.14g} {v:.14g}' for t, v in shifted) + ')'


def prepare(deck, inputs, native, mode, pwl, launch='coincident'):
    assert mode in ('cmos_resistive', 'cmos_no_pullup', 'cmos_hv_resistive', 'cmos_hv_no_pullup', 'cmos_hv_light', 'cmos_hv_direct')
    assert launch in ('coincident', 'inactive_half_cycle')
    hv = mode.startswith('cmos_hv_')
    direct = mode == 'cmos_hv_direct'
    circuit = DIRECT_CIRCUIT if direct else LIGHT_CIRCUIT if mode == 'cmos_hv_light' else HV_CIRCUIT if hv else CIRCUIT
    vectors = VECTORS + ([f'v(xad_{n}.sink)' for n in NAMES] if hv and not direct else [])
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
        # The HV common-source stage inverts. Complement the CMOS gate data
        # so that actual ap/an, bp/bn retain the original serial bit order.
        invert = (n[1] == 'n') != hv
        stimulus = pwl(values, .6, .6, 2 * native.UI, invert)
        if launch == 'inactive_half_cycle' and n[0] == 'a':
            stimulus = half_cycle_launch(stimulus, native.START, native.STOP, native.UI)
        source = f'V{n} {n}0 0 ' + stimulus
        deck, count = re.subn(r'(?ms)^V' + n + r' [^\n]+ PWL\(.*?\)', lambda _: source, deck)
        assert count == 1
        old = f'R{n} {n}0 {n} 25'
        assert deck.count(old) == 1
        rail = '0' if mode.endswith('no_pullup') else 'avdd'
        subckt = ('nssoc_tx_cmos_hv_current_input_v4' if direct else
                  'nssoc_tx_cmos_hv_resistive_input_v3' if mode == 'cmos_hv_light' else
                  'nssoc_tx_cmos_hv_resistive_input_v2' if hv else 'nssoc_tx_cmos_resistive_input_v1')
        deck = deck.replace(old, f'XAD_{n} {n}0 {n} {rail} dvdd 0 0 {subckt}')
    additions = [f'.include "{dest / "buf16.inc"}"', f'.include "{circuit}"',
                 f'.lib "{dest / "models/cornerMOSlv.lib"}" mos_tt',
                 'VDVDD dvdd 0 PWL(0 0 1n 1.2)']
    if hv:
        additions.append(f'.lib "{dest / "models/cornerMOShv.lib"}" mos_tt')
    deck = deck.replace('.control\n', '\n'.join(additions) + '\n.control\n' +
                        f'pre_osdi {dest / "psp103.osdi"}\npre_osdi {dest / "psp103_nqs.osdi"}\n' +
                        'save ' + ' '.join(vectors) + '\n', 1)
    deck = deck.replace('wrdata op.dat ', 'wrdata frontend-op.dat ' + ' '.join(vectors) + '\nwrdata op.dat ', 1)
    deck = deck.replace('wrdata wave.dat ', 'wrdata frontend-wave.dat ' + ' '.join(vectors) + '\nwrdata wave.dat ', 1)
    record = dict(mode=mode, source_sha256=sha(circuit), input_capsule_sha256=pin['sha256'],
        launch=launch, a_transition_advance_s=native.UI if launch == 'inactive_half_cycle' else 0,
        launch_scope='Prospective external gate-data availability contract, not an implemented upstream serializer/clock tree. A changes one serial UI before selection; B unchanged. Source bits and all final-output observation times unchanged.' if launch != 'coincident' else 'Historical coincident gate-data launch retained.',
        expected_devices=dict(lv_mos=16, hv_mos=16 if hv else 0, native_resistors=8 if direct else 12),
        prospective_screen=dict(mos_terminal_abs_limit_v=1.32, sampled_common_mode_v=[1.80, 2.05],
                                hv_mos_terminal_abs_limit_v=2.75 if hv else None,
                                minimum_sampled_differential_v=.15, input_source_rate_gbps=4.0),
        scope='Actual foundry CMOS data drivers and native passive network loaded by the final mux. Select clock still ideal. No complete serializer, rail-sink capability, independent rail startup, PVT, physical layout or foundry SOA claim.')
    return deck, record, [Path(__file__), circuit, SPEC]


def review(run, native, mode):
    hv = mode.startswith('cmos_hv_')
    direct = mode == 'cmos_hv_direct'
    vectors = VECTORS + ([f'v(xad_{n}.sink)' for n in NAMES] if hv and not direct else [])
    op = np.loadtxt(run / 'frontend-op.dat', skiprows=1)
    assert op.size == len(vectors) + 1 and np.isfinite(op).all() and np.max(np.abs(op)) <= 1e-10
    wave = run / 'frontend-wave.dat'
    data = np.loadtxt(wave, skiprows=1)
    assert data.shape[1] == len(vectors) + 1 and np.isfinite(data).all()
    t = data[:, 0]
    assert np.all(np.diff(t) > 0) and t[0] == 0 and t[-1] >= native.STOP - 1e-15
    v = dict(zip(vectors, data[:, 1:].T, strict=True))
    dvdd = v['v(dvdd)']
    devices = {}
    for name in NAMES:
        gate, drv, internal = (v[f'v({name}0)'], v[f'v(xad_{name}.drv)'], v[f'v(xad_{name}.xbuf.net1)'])
        for label, drain, control, source in [('XN1', internal, gate, 0), ('XN0', drv, internal, 0),
                                              ('XP1', drv, internal, dvdd), ('XP0', internal, gate, dvdd)]:
            peaks = {k: float(np.max(np.abs(a - b))) for k, a, b in
                     [('vds', drain, source), ('vgs', control, source), ('vgd', control, drain)]}
            devices[f'xad_{name}.xbuf.{label}'] = dict(peaks=peaks, passed=max(peaks.values()) <= 1.32)
        if hv:
            sink = v[f'v({name})'] if direct else v[f'v(xad_{name}.sink)']
            peaks = dict(vds=float(np.max(np.abs(sink))), vgs=float(np.max(np.abs(drv))),
                         vgd=float(np.max(np.abs(drv - sink))))
            for index in range(4):
                devices[f'xad_{name}.XHV_{index}'] = dict(peaks=peaks, passed=max(peaks.values()) <= 2.75)
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
        active_input_ranges_v={n: [float(v[f'v({n})'][active].min()), float(v[f'v({n})'][active].max())] for n in NAMES},
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
    final_wave = run / 'wave.dat'
    with final_wave.open() as stream:
        header = stream.readline().split()
    assert header.count('v(op)') == header.count('v(on)') == 1
    outputs = np.loadtxt(final_wave, skiprows=1, usecols=(0, header.index('v(op)'), header.index('v(on)')))
    report['original_bit_output'] = original_bit_output_screen(
        outputs[:, 0], outputs[:, 1], outputs[:, 2], bits, native.START, native.UI)
    selected = []
    for i, bit in enumerate(bits):
        port = 'a' if i % 2 == 0 else 'b'
        for phase in (.3, .5, .7):
            time = native.START + (i + phase) * native.UI
            p, n = (np.interp(time, t, v[f'v({port}{suffix})']) for suffix in ('p', 'n'))
            selected.append(((p - n) * (1 if bit else -1), (p + n) / 2))
    chosen_margin, chosen_cm = np.asarray(selected).T
    report['selected_input_source_bits'] = dict(samples=len(selected), minimum_margin_v=float(chosen_margin.min()),
        wrong_sign_samples=int((chosen_margin <= 0).sum()), below_150mv_samples=int((chosen_margin < .15).sum()),
        common_mode_range_v=[float(chosen_cm.min()), float(chosen_cm.max())],
        note='Original source bits while each input is selected. Legacy half-rate sample screen is retained separately above, including unselected time slots.')
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
