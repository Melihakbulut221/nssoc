#!/usr/bin/env python3
# SPDX-FileCopyrightText: 2026 Hasan Melih Akbulut
# SPDX-License-Identifier: Apache-2.0
"""Locate actual TX sample failures without changing the acceptance window."""
import argparse
import gzip
import hashlib
import json
from pathlib import Path
import tarfile

import numpy as np

from run_cloud_tx_layout_repair import ROOT, fetch, sha


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--variant', required=True)
    args = p.parse_args()
    spec = json.loads((ROOT / 'docs/evidence/pcie-tx-cloud-phase-input-20261013.json').read_text())
    receipt = spec['variants'][args.variant]
    out = ROOT / 'cloud-tx-phase-analysis'
    out.mkdir(exist_ok=False)
    archive = out / 'source.tar.gz'
    result = dict(status='RUNNING', variant=args.variant, source=receipt,
                  adopted=False, acceptance_window_changed=False,
                  scope='Read-only phase diagnosis of an existing failed native capture; no shifted-phase acceptance or PHY qualification.')
    try:
        fetch(receipt['url'], receipt['sha256'], archive)
        assert archive.stat().st_size == receipt['bytes']
        with tarfile.open(archive) as tar:
            tar.extractall(out, filter='data')
        archive.unlink()
        source = out / 'cloud-tx-operating-point'
        native = source / 'native'
        report = json.loads((native / 'result.json').read_text())
        independent = json.loads((source / 'independent-review.json').read_text())
        assert report['returncode'] == 0 and report['inputs_unchanged'] and report['compressed_readback_passed']
        assert all(sha(native / name) == digest for name, digest in report['outputs'].items())
        compressed = native / 'wave.dat.gz'
        h, size = hashlib.sha256(), 0
        with gzip.open(compressed, 'rb') as stream:
            while block := stream.read(1024 * 1024):
                h.update(block)
                size += len(block)
        assert dict(bytes=size, sha256=h.hexdigest()) == report['lossless_raw_wave']
        with gzip.open(compressed, 'rt') as stream:
            names = stream.readline().split()
            values = np.loadtxt(stream)
        assert values.shape[1] == len(names) and np.isfinite(values).all()
        d = dict(zip(names, values.T, strict=True))
        t = d['time']
        assert t[0] == 0 and abs(t[-1] - 34e-9) < 1e-18 and np.all(np.diff(t) > 0)
        start, ui = 2e-9, 125e-12
        phases = (.3, .5, .7)
        times = np.array([start + (bit + phase) * ui for bit in range(256) for phase in phases])
        v = lambda name, ts: np.interp(ts, t, d['v(' + name + ')'])
        selected = v('sp', times) > v('sn', times)
        expected = np.where(selected, v('ap', times) - v('an', times), v('bp', times) - v('bn', times))
        assert np.min(np.abs(expected)) > .1
        sign = np.sign(expected)
        signed = (v('op', times) - v('on', times)) * sign
        old = independent['signals']
        assert old['samples'] == len(signed) == 768
        assert old['minimum_margin_v'] == float(signed.min())
        assert old['wrong_sign_samples'] == int(np.sum(signed <= 0))
        result['original_gate_exactly_reproduced'] = old
        def stats(x):
            return dict(samples=len(x), minimum_signed_v=float(x.min()),
                        wrong_signs=int(np.sum(x <= 0)), below_100mv=int(np.sum(x < .1)))
        result['fixed_phase_groups'] = {str(phase): stats(signed[i::3]) for i, phase in enumerate(phases)}
        result['parity_groups'] = {str(parity): stats(signed.reshape(256, 3)[parity::2].flatten()) for parity in (0, 1)}
        bits = sign.reshape(256, 3)
        assert np.all(bits == bits[:, :1])
        signs = bits[:, 0]
        transitions = []
        mux_diff = d['v(mp)'] - d['v(mn)']
        tx_diff = d['v(op)'] - d['v(on)']
        for bit in range(1, 256):
            if signs[bit] == signs[bit - 1]:
                continue
            beginning = start + bit * ui
            sel = (t >= beginning) & (t < beginning + ui)
            tt = t[sel]
            row = dict(bit=bit, parity=bit % 2, direction=int(signs[bit]),
                       fixed_signed_samples_v=[float(x) for x in signed.reshape(256, 3)[bit]])
            for label, wave in (('mux', mux_diff), ('tx', tx_diff)):
                a = wave[sel] * signs[bit]
                for threshold in (0., .1):
                    crossings = np.flatnonzero((a[:-1] < threshold) & (a[1:] >= threshold))
                    ns = []
                    for i in crossings:
                        crossing = tt[i] + (threshold - a[i]) * (tt[i+1] - tt[i]) / (a[i+1] - a[i])
                        ns.append(float((crossing - beginning) * 1e12))
                    row[f'{label}_{threshold}_crossings_ps'] = ns
                row[label + '_start_signed_v'] = float(a[0])
            transitions.append(row)
        result['transitions'] = transitions
        # A separate latency diagnostic, never a replacement for the frozen gate.
        # Estimate one constant delay from the first64 bits; do not select an
        # optimum phase from the later evaluation samples or refit each bit.
        training = [r for r in transitions if r['bit'] < 64]
        assert len(training) >= 16
        assert all(len(r['tx_0.0_crossings_ps']) == 1 for r in training)
        delay_ps = float(np.median([r['tx_0.0_crossings_ps'][0] for r in training]))
        delay = delay_ps * 1e-12
        evaluation_bits = [i for i in range(64, 256)
                           if start + (i + max(phases)) * ui + delay <= t[-1]]
        assert len(evaluation_bits) >= 128
        evaluation_times = np.array([start + (i + phase) * ui + delay
                                     for i in evaluation_bits for phase in phases])
        reference = np.repeat(signs[evaluation_bits], len(phases))
        propagated = (v('op', evaluation_times) - v('on', evaluation_times)) * reference
        assert np.any(propagated > 0)
        # These controls show that a fixed delay cannot conceal a polarity
        # inversion or a complete bit slip; they do not qualify a CDR model.
        slip_bits = [i for i in evaluation_bits if start + (i + 1 + max(phases)) * ui + delay <= t[-1]]
        slip_times = np.array([start + (i + 1 + phase) * ui + delay for i in slip_bits for phase in phases])
        slipped = (v('op', slip_times) - v('on', slip_times)) * np.repeat(signs[slip_bits], len(phases))
        assert np.any(slipped <= 0) and np.any(-propagated <= 0)
        result['frozen_training_delay_diagnostic'] = dict(
            training_bit_range=[0, 63], training_transitions=len(training),
            constant_delay_ps=delay_ps, delay_refitted_on_evaluation=False,
            evaluation_bit_range=[min(evaluation_bits), max(evaluation_bits)],
            omitted_final_bits=[i for i in range(64, 256) if i not in evaluation_bits],
            statistics=stats(propagated),
            polarity_inversion_wrong_samples=int(np.sum(-propagated <= 0)),
            one_ui_slip_wrong_samples=int(np.sum(slipped <= 0)),
            source_referenced_gate_preserved=old,
            implements_reference_cdr=False, compliance_pattern=False,
            pci_sig_compliance=False, accepted=False,
            interpretation='Latency-versus-distortion diagnosis only. Fixed delay from disjoint training data is not a standards CDR, jitter/BER test, or a replacement acceptance gate.')
        result['delay_groups'] = {}
        for label in ('mux', 'tx'):
            for threshold in (0., .1):
                for parity in (0, 1):
                    rows = [r for r in transitions if r['parity'] == parity]
                    key = f'{label}_{threshold}_crossings_ps'
                    crossing = [r[key][0] for r in rows if r[key]]
                    result['delay_groups'][key + '_parity' + str(parity)] = dict(
                        transitions=len(rows), with_crossing=len(crossing),
                        minimum_ps=min(crossing) if crossing else None,
                        maximum_ps=max(crossing) if crossing else None,
                        median_ps=float(np.median(crossing)) if crossing else None)
        result['inputs'] = {str(q.relative_to(out)): sha(q) for q in
                            (native / 'result.json', compressed, native / 'bench.cir', source / 'independent-review.json')}
        result['status'] = 'COMPLETE_FIXED_PHASE_DIAGNOSTIC_NOT_ACCEPTANCE'
    except BaseException as error:
        result.update(status='FAIL_OR_ERROR', error=repr(error))
        raise
    finally:
        (out / 'result.json').write_text(json.dumps(result, indent=2) + '\n')
        print(json.dumps({k: v for k, v in result.items() if k not in ('transitions', 'inputs')}), flush=True)


if __name__ == '__main__':
    main()
