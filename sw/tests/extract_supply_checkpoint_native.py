#!/usr/bin/env python3
# SPDX-FileCopyrightText: 2026 Hasan Melih Akbulut
# SPDX-License-Identifier: Apache-2.0
"""Exercise native derivation and staged all-window audit on synthetic layouts."""
import argparse
from collections import Counter
import json
from pathlib import Path
import resource
import subprocess
import sys

resource.setrlimit(resource.RLIMIT_AS, (384*1024**2,)*2)
ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT/'scripts'))
import klayout.db as db  # noqa: E402
from extract_supply_checkpoint import derive, METALS, VIAS  # noqa: E402
from check_chip_supply_connectivity import sha  # noqa: E402
from supply_checkpoint_staged import prepare  # noqa: E402


def producer(d, case):
    d.mkdir(parents=True, exist_ok=False)
    layout = db.Layout()
    layout.dbu = .001
    top = layout.create_cell('TOP')
    windows = []
    for j, pin in enumerate(['vdd', 'vss', 'iovdd', 'iovss']):
        y = j*100
        for index, x in enumerate([0, 80]):
            if not (case == 'missing' and j == 0 and index == 1):
                top.shapes(layout.layer(8, 0)).insert(db.Box(x, y, x+20, y+60))
            windows.append(dict(instance='p'+str(index), master='CONTROL_PAD', pin=pin,
                                layer='Metal1', gds_layer=8, box_nm=[x, y, x+20, y+20]))
        if not (case == 'split' and j == 3):
            top.shapes(layout.layer(8, 22)).insert(db.Box(0, y+40, 100, y+60))
    if case == 'short':
        top.shapes(layout.layer(8, 0)).insert(db.Box(0, 0, 10, 160))
    gds = d/'control.gds'
    layout.write(str(gds))
    l = derive(db, gds, 'TOP')
    assert l.include_floating_subcircuits
    l.extract_netlist()
    pins = {str(gds): sha(gds), str(Path(__file__).resolve()): sha(Path(__file__))}
    plan = dict(status='PASS_IO_PORT_WINDOW_COVERAGE_ONLY', input_sha256=pins,
                io_instances=2, io_masters={'CONTROL_PAD': 2}, port_windows=8,
                windows_by_rail=dict(Counter(w['pin'] for w in windows)),
                windows_by_layer={'Metal1': 8}, windows=windows)
    (d/'plan.json').write_text(json.dumps(plan, indent=2)+'\n')
    try:
        prepare(db, l, d/'invalid-layer-contract',
                [dict(layer='metal8', box_dbu=windows[0]['box_nm'])], 'TOP', pins,
                checkpoint_layers=['metal10'])
    except ValueError as error:
        assert 'every probe layer' in str(error)
    else:
        raise AssertionError('Probe layer omitted from checkpoint contract')
    prepare(db, l, d/'checkpoint', [dict(layer='metal8', box_dbu=w['box_nm']) for w in windows],
            'TOP', pins, checkpoint_layers=['metal'+str(v) for v in METALS] + ['via'+str(v) for v in VIAS])


def cuts(output):
    layout = db.Layout()
    layout.dbu = .001
    top = layout.create_cell('TOP')
    for n in METALS:
        for dt, box in [(0, [0, 0, 30, 20]), (22, [25, 0, 40, 20]),
                        (24, [20, 0, 22, 20]), (29, [10, 0, 12, 20])]:
            top.shapes(layout.layer(n, dt)).insert(db.Box(*box))
    top.shapes(layout.layer(27, 0)).insert(db.Box(5, 0, 7, 20))
    top.shapes(layout.layer(36, 0)).insert(db.Box(2, 0, 4, 20))
    for n in VIAS:
        top.shapes(layout.layer(n, 0)).insert(db.Box(0, 0, 10, 20))
    path = output/'cuts.gds'
    layout.write(str(path))
    native = derive(db, path, 'TOP')
    for n in METALS:
        expected = db.Region(db.Box(0, 0, 40, 20))
        for box in [[20, 0, 22, 20], [10, 0, 12, 20]] + ([[5, 0, 7, 20]] if n in (126, 134) else []):
            expected -= db.Region(db.Box(*box))
        assert (native.layer_by_name('metal'+str(n)) ^ expected).is_empty(), n
    for n in VIAS:
        expected = db.Region(db.Box(0, 0, 10, 20))
        if n == 125:
            expected -= db.Region(db.Box(2, 0, 4, 20))
        assert (native.layer_by_name('via'+str(n)) ^ expected).is_empty(), n
    return dict(status='PASS_EXACT_SYNTHETIC_LAYER_BOOLEAN_CONTROLS', metals=7, vias=6,
                gds_sha256=sha(path))


def run(output):
    output.mkdir(parents=True, exist_ok=False)
    cases = dict(cuts=cuts(output))
    for case in ['connected', 'short', 'split', 'missing']:
        d = output/case
        with (output/(case+'.log')).open('w') as log:
            subprocess.run([sys.executable, __file__, str(d), '--produce', case],
                           stdout=log, stderr=subprocess.STDOUT, check=True)
            subprocess.run([sys.executable, str(ROOT/'scripts/supply_checkpoint_staged.py'),
                            '--checkpoint', str(d/'checkpoint'), '--prepared-sha256', sha(d/'checkpoint/prepared.json')],
                           stdout=log, stderr=subprocess.STDOUT, check=True)
            code = subprocess.run([sys.executable, str(ROOT/'scripts/audit_supply_checkpoint.py'),
                                   '--checkpoint', str(d/'checkpoint'), '--manifest-sha256', sha(d/'checkpoint/manifest.json'),
                                   '--plan', str(d/'plan.json'), '--plan-sha256', sha(d/'plan.json'),
                                   '--output', str(d/'audit.json')], stdout=log, stderr=subprocess.STDOUT).returncode
        result = json.loads((d/'audit.json').read_text())
        assert code == (0 if case == 'connected' else 1), (case, result)
        cases[case] = dict(exit_code=code, status=result['status'], errors=result['errors'],
                           audit_sha256=sha(d/'audit.json'))
    methods = [Path(__file__).resolve()] + [ROOT/'scripts'/n for n in (
        'extract_supply_checkpoint.py', 'supply_checkpoint_staged.py', 'supply_checkpoint.py',
        'audit_supply_checkpoint.py', 'check_chip_supply_connectivity.py',
        'probe_supply_components.py', 'plan_chip_supply_probes.py')]
    result = dict(status='PASS_EXTRACTION_STAGED_AUDIT_CONTROLS_ONLY', cases=cases,
                  input_sha256={str(p): sha(p) for p in methods},
                  full_chip_lvs_accepted=False, manufacturing_approval=False)
    (output/'result.json').write_text(json.dumps(result, indent=2)+'\n')
    print(result['status'])


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('output', type=Path)
    parser.add_argument('--produce', choices=['connected', 'short', 'split', 'missing'])
    args = parser.parse_args()
    if args.produce:
        producer(args.output, args.produce)
    else:
        run(args.output)
