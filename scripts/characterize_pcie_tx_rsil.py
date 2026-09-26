#!/usr/bin/env python3
# SPDX-FileCopyrightText: 2026 Hasan Melih Akbulut
# SPDX-License-Identifier: Apache-2.0
"""Screen native resistor TX models; no PCIe, layout or lifetime acceptance."""
import argparse
import gzip
import itertools
import json
import math
from pathlib import Path
import subprocess

import characterize_pcie_tx as tx

RES_HASHES = {
    'ngspice/models/cornerRES.lib': '2c18502104146804444a567abfe7d00520752bf75426809f9d79f40198fe9c1e',
    'ngspice/models/resistors_mod.lib': '98fa5436f6df86dc1dd35e9f16383c4eba4c36d478d7eec203a0295dc1259e51',
    'verilog-a/r3_cmc/r3_cmc.va': '398746f45048a9e075913e85a982258b929c9042257339bf1fc47d7e25303551',
    'verilog-a/r3_cmc/r3_cmc_macros.include': '66e1bf0b43495a9c17454a1ac203171db5488edc7e19563f4f645389ba7eebb4',
}


def cases():
    result = []
    for case, resistor in itertools.product(tx.cases(False), ('res_typ', 'res_bcs', 'res_wcs')):
        # Cross every single-cell transistor corner with each resistor corner;
        # retain the original bank/load/negative/timestep tests at nominal RES.
        if resistor != 'res_typ' and not case['name'].startswith('hbt_'):
            continue
        result.append(dict(case, name=case['name']+'_'+resistor, resistor=resistor))
    return result


def load_vectors(case):
    result = []
    for lane in range(case['lanes']):
        prefix = 'xbank.x'+str(lane) if case['lanes'] == 4 else 'xlane'
        result.extend([f'i(v.{prefix}.vrp)', f'i(v.{prefix}.vrn)',
                       f'v({prefix}.xrp.dt)', f'v({prefix}.xrn.dt)'])
    return result


def load_measure(path, case):
    with path.open() as source:
        header = next(source).split()
        rows = [list(map(float, line.split())) for line in source if line.strip()]
    if (header != ['time', *load_vectors(case)] or len(rows) < 2 or
            any(len(row) != len(header) or not all(math.isfinite(x) for x in row)
                for row in rows)):
        raise ValueError('Incomplete or nonfinite native resistor monitor data')
    times = [row[0] for row in rows]
    if (times[0] > 1e-15 or times[-1] < tx.START+tx.BITS*tx.UI-1e-15 or
            any(b <= a or b-a > 1.01e-12 for a, b in zip(times, times[1:]))):
        raise ValueError('Incomplete native resistor monitor time coverage')
    active = [row for row in rows if row[0] >= tx.START]
    return [dict(peak_absolute_branch_current_a=max(abs(row[1+4*i+j]) for row in active for j in (0, 1)),
                 maximum_model_temperature_rise_k=max(row[1+4*i+j] for row in active for j in (2, 3)))
            for i in range(case['lanes'])]


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ('pdk', 'ngspice', 'openvaf', 'out'):
        parser.add_argument('--'+name, required=True, type=Path)
    parser.add_argument('--reference-current-a', type=float, default=.0015)
    args = parser.parse_args()
    if not math.isfinite(args.reference_current_a) or args.reference_current_a <= 0:
        parser.error('Reference current must be finite and positive')
    out = args.out.resolve()
    if out.exists() or not out.is_relative_to(tx.ROOT/'hw/soc/out'):
        parser.error('Use a fresh output directory under hw/soc/out')
    tech = args.pdk.resolve()/'libs.tech'
    models = tech/'ngspice/models'
    for rel, digest in RES_HASHES.items():
        if tx.sha(tech/rel) != digest:
            parser.error('Resistor model revision mismatch: '+rel)
    for name, digest in tx.MODEL_HASHES.items():
        if tx.sha(models/name) != digest:
            parser.error('HBT model revision mismatch: '+name)
    design = [tx.DESIGN/name for name in ('tx_cml_rsil.spice', 'tx_bank4_rsil.spice')]
    inputs = [*design, Path(__file__).resolve(), Path(tx.__file__),
              *[tech/p for p in RES_HASHES], *[models/p for p in tx.MODEL_HASHES],
              args.openvaf.resolve(), args.ngspice.resolve()]
    hashes = {str(p): tx.sha(p) for p in inputs}
    out.mkdir(parents=True)
    record = dict(status='RUNNING', scope='Native three-terminal self-heating rsil/HBT pre-layout screen; external ideal predriver/reference/termination. No contact-current, extracted-layout, PHY or manufacturing acceptance.',
                  input_sha256=hashes, pdk_reference_revision=tx.PDK_REV,
                  geometry=dict(width_m=10e-6, length_m=70.215e-6),
                  reference_current_a=args.reference_current_a,
                  manufacturing_approval=False, physical_qualification=False, cases=[])

    def save():
        temp = out/'result.tmp'
        temp.write_text(json.dumps(record, indent=2)+'\n')
        temp.replace(out/'result.json')

    try:
        save()
        osdi = out/'r3_cmc.osdi'
        cmd = [str(args.openvaf.resolve()), str(tech/'verilog-a/r3_cmc/r3_cmc.va'), '-o', str(osdi)]
        record['compile_command'] = cmd
        with (out/'compile.log').open('x') as log:
            process = subprocess.run(cmd, stdout=log, stderr=subprocess.STDOUT, timeout=120)
        if process.returncode or not osdi.is_file():
            raise RuntimeError('Native resistor model compilation failed')
        record['osdi_sha256'] = tx.sha(osdi)
        record['compile_warnings'] = [s for s in (out/'compile.log').read_text().splitlines() if 'warning' in s.lower()]
        for case in cases():
            directory = out/case['name']
            directory.mkdir()
            for p in design:
                (directory/p.name).write_bytes(p.read_bytes())
            text, sequence = tx.deck(case, models)
            if case['fault'] != 'no_bias':
                for lane in range(case['lanes']):
                    old = f'IREF{lane} avdd ref{lane} 0.002'
                    if text.count(old) != 1:
                        raise RuntimeError('Unexpected reference-current stimulus')
                    text = text.replace(old, f'IREF{lane} avdd ref{lane} {args.reference_current_a:.12g}')
            for old in ('tx_cml', 'tx_bank4'):
                text = text.replace(old, old+'_rsil')
            text = text.replace('.temp ', f'.lib "{models}/cornerRES.lib" {case["resistor"]}\n.temp ')
            text = text.replace('.control', f'.control\npre_osdi {osdi}')
            vectors = ' '.join(load_vectors(case))
            text = text.replace('save v(avdd)', 'save '+vectors+' v(avdd)')
            text = text.replace('\nquit', '\nwrdata loads.dat '+vectors+'\nquit')
            (directory/'bench.cir').write_text(text)
            cmd = [str(args.ngspice.resolve()), '-n', '-b', 'bench.cir']
            with (directory/'run.log').open('x') as log:
                process = subprocess.run(cmd, cwd=directory, stdout=log, stderr=subprocess.STDOUT, timeout=180)
            log = (directory/'run.log').read_text()
            entry = dict(case, command=cmd, returncode=process.returncode)
            record['cases'].append(entry)
            if process.returncode or any(s in log.lower() for s in ('error', 'aborted', 'timestep too small')):
                raise RuntimeError('Simulation failed: '+case['name'])
            entry['warnings'] = [s for s in log.splitlines() if any(w in s.lower() for w in ('warning', 'nan', 'stepping'))]
            entry['measurement'] = tx.measure(directory/'wave.dat', case, sequence)
            entry['loads'] = load_measure(directory/'loads.dat', case)
            entry['expected_screen_pass'] = case['fault'] is None
            entry['accepted_screen'] = entry['measurement']['screen_pass'] == entry['expected_screen_pass']
            entry['output_sha256'] = {p.name: tx.sha(p) for p in directory.iterdir() if p.is_file()}
            for name in ('wave.dat', 'loads.dat'):
                wave = directory/name
                with wave.open('rb') as src, gzip.open(str(wave)+'.gz', 'wb') as dst:
                    for chunk in iter(lambda: src.read(1024*1024), b''):
                        dst.write(chunk)
                entry['output_sha256'][name+'.gz'] = tx.sha(Path(str(wave)+'.gz'))
                wave.unlink()
            save()
            print(case['name'], 'ACCEPTED_SCREEN' if entry['accepted_screen'] else 'FAILED_SCREEN', flush=True)
        if any(tx.sha(Path(p)) != digest for p, digest in hashes.items()):
            raise RuntimeError('Characterization inputs changed')
        record['sources_unchanged'] = True
        measured = {c['name']: c['measurement'] for c in record['cases']}
        baseline, half = measured['hbt_typ_27_1.8_res_typ'], measured['half_timestep_res_typ']
        margin_delta = abs(baseline['lanes'][0]['min_signed_margin_v']-half['lanes'][0]['min_signed_margin_v'])
        power_delta = abs(baseline['analog_supply_power_w']/half['analog_supply_power_w']-1)
        record['timestep_sensitivity'] = dict(margin_difference_v=margin_delta,
            power_relative_difference=power_delta, screen_pass=margin_delta < .001 and power_delta < .002,
            scope='Two numerical steps, not extrapolated convergence or process qualification')
        success = all(c['accepted_screen'] for c in record['cases']) and record['timestep_sensitivity']['screen_pass']
        record['status'] = 'REVIEW_NATIVE_RESISTOR_SCREEN' if success else 'FAIL_NATIVE_RESISTOR_SCREEN'
    except BaseException as exc:
        record.update(status='ERROR', error=repr(exc))
        raise
    finally:
        save()
    return 2 if record['status'].startswith('REVIEW') else 1


if __name__ == '__main__':
    raise SystemExit(main())
