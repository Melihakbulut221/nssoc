#!/usr/bin/env python3
# SPDX-FileCopyrightText: 2026 Hasan Melih Akbulut
# SPDX-License-Identifier: Apache-2.0
"""Native passive clock-transfer experiment on the full fixed bank wire network.

Every wire R/C is retained. Intrinsic devices are NOT instantiated in this wire-only
experiment. Four real emitter anchors per phase are ideal small-signal sources with
explicit 0/25/50-ohm source impedances; all other conductors are quiet at one actual
anchor each. Results are conditional loading measurements, not oscillator behavior.
"""
import argparse
import json
import math
import os
from pathlib import Path
import resource
import subprocess
import time

import build_pcie_bank_hybrid_v1 as hybrid

NG47_SHA = 'eaca52dad06845779fed4f50420a6a0cf4a32776e6a572432275f350002b87b8'
DRIVE_P = ['T0418', 'T0438', 'T0442', 'T0446']
DRIVE_N = ['T0414', 'T0426', 'T0430', 'T0434']
SENSE_PAIRS = [('T0053', 'T0057'), ('T0081', 'T0077'),
               ('T0149', 'T0153'), ('T0181', 'T0177'),
               ('T0233', 'T0237'), ('T0261', 'T0257'),
               ('T0321', 'T0325'), ('T0353', 'T0349')]
VECTORS = ['v(' + n + ')' for pair in SENSE_PAIRS for n in pair]
VECTORS += ['i(vdrive' + str(i) + ')' for i in range(8)]


def limits():
    resource.setrlimit(resource.RLIMIT_AS, (2 * 1024**3, 2 * 1024**3))
    resource.setrlimit(resource.RLIMIT_CORE, (0, 0))


def load_inputs(args):
    for name in ('anchors', 'wires'):
        hybrid.require(hybrid.pin(getattr(args, name))['sha256'] == hybrid.PINS[name], 'Frozen input changed')
    a = json.loads(args.anchors.read_text())
    labels = {r['label']: r for r in a['anchors']}
    # Actual named devices and terminal geometry, not matching conductor names.
    for names, ids, component in ((DRIVE_P, [105, 110, 111, 112], 118),
                                   (DRIVE_N, [104, 107, 108, 109], 117)):
        for n, device in zip(names, ids):
            row = labels[n]
            hybrid.require(row['detail']['device'] == device and row['detail']['terminal'] == 'E' and
                           row['detail']['model'] == 'npn13G2' and row['wire_component'] == component,
                           'Clock emitter source binding changed')
    for p, n in SENSE_PAIRS:
        for label, component in ((p, 118), (n, 117)):
            row = labels[label]
            hybrid.require(row['detail']['terminal'] == 'B' and row['detail']['model'] == 'npn13G2' and
                           row['wire_component'] == component, 'Sampler clock receiver binding changed')
    ports, records = hybrid.wire_records(args.wires.read_text())
    hybrid.require(set(ports) == set(labels), 'Wire actual anchor census')
    return a, records


def deck(anchors, resistance):
    hybrid.require(resistance in (0, 25, 50), 'Unsupported boundary impedance')
    quiet = {}
    for a in anchors['anchors']:
        quiet.setdefault(a['wire_component'], a['label'])
    hybrid.require(set(quiet) == set(range(1, 129)), 'Incomplete quiet boundary')
    lines = ['Full fixed wire matrix, passive boundary experiment',
             '.include "wire-elements.spice"', '.options reltol=1e-6 abstol=1e-14',
             'VCREF sub 0 0']
    for owner, n in sorted(quiet.items()):
        if owner not in (117, 118):
            lines.append(f'Vquiet{owner} {n} 0 0')
    for i, n in enumerate(DRIVE_P + DRIVE_N):
        voltage = 0.5 if i < 4 else -0.5
        phase = 0 if i < 4 else 180
        source = f'source{i}' if resistance else n
        lines.append(f'Vdrive{i} {source} 0 DC {voltage} AC 0.5 {phase}')
        if resistance:
            lines.append(f'Rsource{i} {source} {n} {resistance}')
    lines += ['.control', 'set wr_singlescale', 'set wr_vecnames', 'set numdgt=16',
              'save ' + ' '.join(VECTORS), 'op', 'wrdata dc.dat ' + ' '.join(VECTORS),
              'ac lin 3 1G 15G', 'wrdata ac.dat ' + ' '.join(VECTORS),
              'echo NSSOC_PASSIVE_WIRE_COMPLETE', 'quit', '.endc', '.end', '']
    return '\n'.join(lines)


def read_ac(path):
    lines = path.read_text().splitlines()
    expected = ['frequency'] + [name for n in VECTORS for name in (n, n)]
    hybrid.require(lines[0].split() == expected, 'AC vector order/complex width changed')
    data = []
    for line in lines[1:]:
        values = [float(v) for v in line.split()]
        hybrid.require(len(values) == len(expected) and all(math.isfinite(v) for v in values), 'Bad AC data')
        data.append((values[0], [complex(*values[i:i+2]) for i in range(1, len(values), 2)]))
    hybrid.require([f for f, _ in data] == [1e9, 8e9, 15e9], 'AC frequency coverage changed')
    return data


def read_dc(path):
    lines = path.read_text().splitlines()
    # ngspice OP scale is a voltage vector here, and can have either v-sweep or
    # the first saved vector as header; only the saved value positions are used.
    require = hybrid.require
    require(len(lines) == 2, 'Missing/extra DC rows')
    header = lines[0].split(); values = [float(v) for v in lines[1].split()]
    require(header[1:] == VECTORS and len(values) == 1 + len(VECTORS), 'DC vector order changed')
    require(all(math.isfinite(v) for v in values), 'Nonfinite DC')
    volts = values[1:17]
    require(all(abs(v - (0.5 if i % 2 == 0 else -0.5)) < 1e-8 for i, v in enumerate(volts)),
            'DC wire transfer failed')
    require(max(abs(v) for v in values[17:]) < 1e-10, 'Unexpected passive DC leakage')
    return dict(max_voltage_error=max(abs(v - (0.5 if i % 2 == 0 else -0.5)) for i, v in enumerate(volts)),
                max_drive_current_a=max(abs(v) for v in values[17:]))


def measure(root):
    log = (root / 'native.log').read_text()
    hybrid.require(log.count('NSSOC_PASSIVE_WIRE_COMPLETE') == 1 and
                   not any(s in log.lower() for s in ('fatal', 'error', 'singular', 'warning', 'failed', 'timestep too small')),
                   'Native incomplete/error/warning')
    data = read_ac(root / 'ac.dat')
    result = []
    for frequency, values in data:
        pairs = []
        for i in range(8):
            value = values[2*i] - values[2*i+1]
            phase = math.atan2(value.imag, value.real)
            pairs.append(dict(pair=i, p=SENSE_PAIRS[i][0], n=SENSE_PAIRS[i][1],
                              differential_gain=abs(value), phase_deg=math.degrees(phase),
                              phase_delay_ps=-phase / (2 * math.pi * frequency) * 1e12))
        # Half-differential voltage magnitude=0.5V per phase. Currents sum only
        # actual four physical source anchors; quiet conductor sources are separate.
        current_p = -sum(values[16:20]); current_n = -sum(values[20:24])
        yp, yn = current_p / 0.5, current_n / -0.5
        result.append(dict(frequency_hz=frequency, pairs=pairs,
                           source_admittance_p=[yp.real, yp.imag], source_admittance_n=[yn.real, yn.imag],
                           equivalent_input_capacitance_p_f=yp.imag / (2 * math.pi * frequency),
                           equivalent_input_capacitance_n_f=yn.imag / (2 * math.pi * frequency)))
    return dict(dc=read_dc(root / 'dc.dat'), ac=result)


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    for name in ('anchors', 'wires', 'ngspice', 'out'):
        ap.add_argument('--' + name, type=Path, required=True)
    args = ap.parse_args()
    anchors, records = load_inputs(args)
    native_pin = hybrid.pin(args.ngspice)
    hybrid.require(native_pin['sha256'] == NG47_SHA, 'Pinned ngspice47 executable changed')
    hybrid.require(os.statvfs('/dev/shm').f_bavail * os.statvfs('/dev/shm').f_frsize > 512 * 1024**2,
                   'Shared scratch reserve unavailable')
    args.out.mkdir(parents=True, exist_ok=False)
    shared = args.out / 'wire-elements.spice'
    shared.write_text('\n'.join(' '.join(row) for row in records) + '\n')
    init = args.out / 'config'; init.mkdir()
    (init / 'spinit').write_text('* Project passive R/C experiment. No external code models required.\n')
    environment = {k: v for k, v in os.environ.items() if k not in ('GH_TOKEN', 'GITHUB_TOKEN')}
    environment['SPICE_SCRIPTS'] = str(init.resolve())
    environment['OMP_NUM_THREADS'] = '1'
    result = dict(status='RUNNING_PASSIVE_BOUNDARY_EXPERIMENT', cases=[], intrinsic_devices_simulated=0,
                  full_351_device_hybrid_simulated=False, full_pex_qualified=False,
                  boundary_assumptions=dict(wire_cap_reference='explicit ideal AC/DC ground',
                    quiet_conductors='126 nonclock conductors held at one actual terminal each',
                    clock_sources='four emitter anchors per phase, synchronous +/-0.5V AC, independent ideal source impedances',
                    sampler_inputs='no intrinsic transistor input junction admittance',
                    exclusions='substrate spreading, device-wire coupling, oscillator waveform, RF, ESD stress'),
                  inputs={str(p): hybrid.pin(p) for p in [Path(__file__), Path(hybrid.__file__), args.anchors, args.wires, args.ngspice]})
    for resistance in (0, 25, 50):
        work = args.out / f'ohm{resistance}'; work.mkdir()
        (work / 'wire-elements.spice').symlink_to('../wire-elements.spice')
        bench = work / 'bench.cir'; bench.write_text(deck(anchors, resistance))
        start = time.monotonic()
        row = dict(source_resistance_each_ohm=resistance)
        result['cases'].append(row)
        try:
            with (work / 'native.log').open('w') as log:
                process = subprocess.run([str(args.ngspice.resolve()), '-n', '-b', bench.name], cwd=work,
                                         stdout=log, stderr=subprocess.STDOUT, timeout=55,
                                         preexec_fn=limits, env=environment)
            row['returncode'] = process.returncode
            hybrid.require(process.returncode == 0, 'Native process failed')
            row['metrics'] = measure(work)
        except Exception as error:
            result['status'] = 'FAIL_NATIVE_PASSIVE_BOUNDARY_EXPERIMENT'
            row['error'] = type(error).__name__ + ': ' + str(error)
            raise
        finally:
            row['elapsed_seconds'] = time.monotonic() - start
            row['outputs'] = {p.name: hybrid.pin(p) for p in work.iterdir() if p.is_file() and not p.is_symlink()}
            (args.out / 'result.json').write_text(json.dumps(result, indent=2) + '\n')
    hybrid.require(hybrid.pin(args.ngspice) == native_pin, 'Runtime changed during native run')
    hybrid.require(all(hybrid.pin(p) == pin for p, pin in result['inputs'].items()), 'Input or method changed during native run')
    result['status'] = 'PASS_NATIVE_PASSIVE_WIRE_MEASUREMENT_NOT_BANK_FUNCTIONAL_ACCEPTANCE'
    result['outputs'] = {shared.name: hybrid.pin(shared), 'config/spinit': hybrid.pin(init / 'spinit')}
    (args.out / 'result.json').write_text(json.dumps(result, indent=2) + '\n')
    print(result['status'])


if __name__ == '__main__':
    main()
