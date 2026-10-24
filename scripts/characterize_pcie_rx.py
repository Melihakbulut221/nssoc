#!/usr/bin/env python3
# SPDX-FileCopyrightText: 2026 Hasan Melih Akbulut
# SPDX-License-Identifier: Apache-2.0
"""Native HBT/rsil RX preamplifier screen, with no PHY or signoff acceptance."""
import argparse
from bisect import bisect_left
import gzip
import itertools
import json
import math
import os
from pathlib import Path
import resource
import shutil
import subprocess
import time

import characterize_pcie_tx as tx
import characterize_pcie_tx_rsil as resistor

ROOT = tx.ROOT
NETLIST = ROOT/'hw/soc/analog/pcie/rx_hbt_rsil.spice'
UI, START, BITS = tx.UI, tx.START, tx.BITS
STOP = START+BITS*UI
MEMORY_LIMIT = 2*1024**3
# Reused conservative TX engineering stress/margin limits, not PCI-SIG limits.
LIMITS = dict(min_margin_v=.1, min_vce_v=.4, max_vce_v=1.6,
              min_tail_collector_a=.0005, max_collector_a_per_emitter=.003)
VECTORS = ['v(ip)', 'v(inn)', 'v(op)', 'v(on)', 'v(xrx.tail)', 'v(ref)',
           'i(vdd)', 'i(vcm)', 'i(vp)', 'i(vn)',
           *[f'@q.xrx.x{name}.qnpn13g2[ic]' for name in ('tail', 'p', 'n', 'ref')],
           *[f'v(xrx.x{name}.dt)' for name in ('rp', 'rn', 'rtp', 'rtn')]]


def cases(quick=False):
    matrix = [('hbt_typ', 'res_typ', 27, 1.8)] if quick else itertools.product(
        ('hbt_typ', 'hbt_bcs', 'hbt_wcs'), ('res_typ', 'res_bcs', 'res_wcs'),
        (-40, 27, 125), (1.71, 1.8, 1.89))
    defaults = dict(vcm=1.36, reference_a=.0005, amplitude_v=.08, cap_f=100e-15,
                    step_s=1e-12, mode='prbs', fault=None)
    result = [dict(defaults, name=f'{h}_{r}_{t}_{v}', hbt=h, resistor=r, temp=t, supply=v)
              for h, r, t, v in matrix]
    nominal = dict(defaults, hbt='hbt_typ', resistor='res_typ', temp=27, supply=1.8)
    for name, changes in (
        ('alternating', dict(mode='alternating')),
        ('source_amplitude_60mV', dict(amplitude_v=.06)),
        ('source_amplitude_100mV', dict(amplitude_v=.10)),
        ('common_mode_1p30', dict(vcm=1.30)),
        ('common_mode_1p42', dict(vcm=1.42)),
        ('cold_common_mode_1p30', dict(vcm=1.30, hbt='hbt_wcs', temp=-40, supply=1.71)),
        ('hot_common_mode_1p42', dict(vcm=1.42, hbt='hbt_bcs', temp=125, supply=1.71)),
        ('load_150fF', dict(cap_f=150e-15)),
        ('half_timestep', dict(step_s=.5e-12)),
        ('no_bias', dict(reference_a=0, fault='no_bias')),
        ('swapped_output', dict(fault='swapped')),
        ('overload', dict(cap_f=100e-12, fault='overload')),
        ('tiny_input', dict(amplitude_v=.005, fault='tiny_input')),
        ('low_common_mode', dict(vcm=1.10, fault='low_common_mode')),
        ('clipped_overbias', dict(reference_a=.003, fault='clipped_overbias')),
    ):
        result.append(dict(nominal, name=name, **changes))
    return result


def sequence(case):
    return tx.prbs7(count=BITS) if case['mode'] == 'prbs' else [i % 2 for i in range(BITS)]


def stimulus(bits, case, inverted=False):
    def level(bit):
        return case['vcm']+case['amplitude_v']*(1 if bool(bit) != inverted else -1)
    points = [(0, level(bits[0]))]
    for i in range(1, len(bits)):
        if bits[i] != bits[i-1]:
            points.extend([(START+i*UI, level(bits[i-1])), (START+i*UI+10e-12, level(bits[i]))])
    points.append((STOP, level(bits[-1])))
    return 'PWL(\n+ '+'\n+ '.join(f'{t:.12g} {v:.12g}' for t, v in points)+')'


def deck(case, models, osdi, ac=False):
    bits = sequence(case)
    lines = ['NSSOC native RX preamplifier screen',
             f'.lib "{models}/cornerHBT.lib" {case["hbt"]}',
             f'.lib "{models}/cornerRES.lib" {case["resistor"]}',
             '.include "rx_hbt_rsil.spice"', f'.temp {case["temp"]}',
             '.options reltol=1e-4 abstol=1e-12', f'VDD avdd 0 {case["supply"]}',
             f'VCM cm 0 {case["vcm"]}', f'IREF avdd ref {case["reference_a"]}']
    if ac:
        lines.extend([f'VP sp 0 DC {case["vcm"]} AC .5',
                      f'VN sn 0 DC {case["vcm"]} AC .5 180'])
    else:
        lines.extend(['VP sp 0 '+stimulus(bits, case), 'VN sn 0 '+stimulus(bits, case, True)])
    # External Thevenin source impedance is explicit; stimulus cannot hide RX loading.
    lines.extend(['RSP sp ip 50', 'RSN sn inn 50', f'CP op 0 {case["cap_f"]}',
                  f'CN on 0 {case["cap_f"]}'])
    output = 'on op' if case['fault'] == 'swapped' else 'op on'
    lines.append(f'XRX ip inn {output} avdd 0 0 ref cm nssoc_rx_hbt_rsil')
    if case['reference_a']:
        lines.append('.nodeset v(ref)=.85 v(xrx.tail)=.5 v(op)=1.65 v(on)=1.65')
    lines.extend(['.control', f'pre_osdi {osdi}', 'set wr_singlescale',
                  'set wr_vecnames', 'set numdgt=12'])
    if ac:
        lines.extend(['ac dec 40 1Meg 20Gig',
                      'let zd=(v(ip)-v(inn))/((i(vn)-i(vp))/2)',
                      'let gd=(v(op)-v(on))/(v(ip)-v(inn))',
                      'let zd_r=real(zd)', 'let zd_i=imag(zd)',
                      'let gd_r=real(gd)', 'let gd_i=imag(gd)',
                      'wrdata ac.dat zd_r zd_i gd_r gd_i'])
    else:
        lines.extend(['save '+' '.join(VECTORS),
                      f'tran {case["step_s"]:.12g} {STOP:.12g} 0 {case["step_s"]:.12g}',
                      'wrdata wave.dat '+' '.join(VECTORS)])
    return '\n'.join(lines+['quit', '.endc', '.end'])+'\n', bits


def read_table(path, header):
    with Path(path).open() as source:
        if next(source).split() != header:
            raise ValueError('Native waveform header differs')
        rows = [list(map(float, line.split())) for line in source if line.strip()]
    if len(rows) < 2 or any(len(row) != len(header) or not all(math.isfinite(x) for x in row) for row in rows):
        raise ValueError('Incomplete/nonfinite native waveform')
    return dict(zip(header, zip(*rows)))


def measure(path, case, bits):
    data = read_table(path, ['time', *VECTORS]); times = data['time']
    if (times[0] > 1e-15 or times[-1] < STOP-1e-15 or
            any(b <= a or b-a > case['step_s']*1.01 for a, b in zip(times, times[1:]))):
        raise ValueError('Incomplete time coverage or native timestep gap')
    begin = bisect_left(times, START)
    def active(name): return data[name][begin:]
    def signed_samples(p, n):
        diff = [a-b for a, b in zip(data[p], data[n])]
        return [tx.interpolate(times, diff, START+(i+phase)*UI)*(1 if bits[i] else -1)
                for i in range(16, BITS) for phase in (.3, .5, .7)]
    margin = signed_samples('v(op)', 'v(on)'); pad = signed_samples('v(ip)', 'v(inn)')
    tail = active('v(xrx.tail)')
    vces = [*tail, *active('v(ref)'),
            *[v-t for name in ('v(op)', 'v(on)') for v, t in zip(active(name), tail)]]
    currents = {name: active(f'@q.xrx.x{name}.qnpn13g2[ic]') for name in ('tail', 'p', 'n', 'ref')}
    def average(name):
        v = data[name]
        return sum((v[j]+v[j-1])*.5*(times[j]-times[j-1]) for j in range(begin+1, len(times)))/(times[-1]-times[begin])
    checks = dict(margin=min(margin) >= LIMITS['min_margin_v'],
                  vce_headroom=min(vces) >= LIMITS['min_vce_v'],
                  vce_maximum=max(vces) <= LIMITS['max_vce_v'],
                  active_tail_current=min(currents['tail']) >= LIMITS['min_tail_collector_a'],
                  current_density=all(max(abs(x) for x in values) < LIMITS['max_collector_a_per_emitter']*(1 if n == 'ref' else 4)
                                      for n, values in currents.items()),
                  input_within_rails=all(0 <= x <= case['supply'] for n in ('v(ip)', 'v(inn)') for x in active(n)))
    return dict(rows=len(times), samples=len(margin), sign_errors=sum(x <= 0 for x in margin),
                min_signed_margin_v=min(margin), max_signed_margin_v=max(margin),
                minimum_loaded_input_differential_v=min(pad), maximum_loaded_input_differential_v=max(pad),
                source_differential_level_v=2*case['amplitude_v'],
                min_vce_v=min(vces), max_vce_v=max(vces),
                tail_collector_min_a=min(currents['tail']), tail_collector_max_a=max(currents['tail']),
                peak_source_current_a=max(abs(x) for n in ('i(vp)', 'i(vn)') for x in active(n)),
                common_mode_supply_mean_a=-average('i(vcm)'),
                analog_supply_power_w=-average('i(vdd)')*case['supply'],
                common_mode_supply_power_w=-average('i(vcm)')*case['vcm'],
                max_native_resistor_temperature_rise_k=max(x for n in VECTORS if n.endswith('.dt)') for x in active(n)),
                checks=checks, screen_pass=all(checks.values()))


def measure_ac(path):
    data = read_table(path, ['frequency', 'zd_r', 'zd_i', 'gd_r', 'gd_i'])
    f = data['frequency']
    if f[0] > 1e6 or f[-1] < 19e9 or any(b <= a for a, b in zip(f, f[1:])):
        raise ValueError('Incomplete native AC frequency coverage')
    def at(freq):
        return {key: tx.interpolate(f, values, freq) for key, values in data.items() if key != 'frequency'}
    return dict(rows=len(f), balanced_input_dc_operating_point=True,
                low_frequency_impedance_ohm=dict(real=data['zd_r'][0], imag=data['zd_i'][0]),
                at_4GHz=at(4e9), at_8GHz=at(8e9),
                scope='Small-signal balanced-bias input impedance and gain, including native transistor/resistor capacitance. No pad/package/channel extraction or PCIe return-loss qualification.')


def resource_limit():
    resource.setrlimit(resource.RLIMIT_AS, (MEMORY_LIMIT, MEMORY_LIMIT))
    resource.setrlimit(resource.RLIMIT_CORE, (0, 0))
    os.sched_setaffinity(0, {min(os.sched_getaffinity(0))})


def execute(command, cwd, log):
    env = {k: v for k, v in os.environ.items() if k not in ('GH_TOKEN', 'GITHUB_TOKEN', 'LD_PRELOAD')}
    env.update(RAYON_NUM_THREADS='1', OMP_NUM_THREADS='1')
    start = time.monotonic()
    with log.open('x') as stream:
        p = subprocess.run(command, cwd=cwd, env=env, stdout=stream, stderr=subprocess.STDOUT,
                           preexec_fn=resource_limit, timeout=180)
    text = log.read_text()
    if p.returncode or any(x in text.lower() for x in ('error', 'aborted', 'timestep too small')):
        raise RuntimeError('Native process failed; inspect '+str(log))
    return dict(command=list(map(str, command)), returncode=p.returncode, elapsed_seconds=time.monotonic()-start,
                address_space_limit_bytes=MEMORY_LIMIT, cpu_affinity_count=1,
                warnings=[s for s in text.splitlines() if any(w in s.lower() for w in ('warning', 'stepping', 'spinit'))])


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    for name in ('pdk', 'ngspice', 'openvaf', 'out'): ap.add_argument('--'+name, type=Path, required=True)
    ap.add_argument('--quick', action='store_true')
    args = ap.parse_args(); out = args.out.resolve()
    if out.exists() or not (out.is_relative_to(Path('/dev/shm')) or out.is_relative_to(ROOT/'hw/soc/out')):
        ap.error('Use a fresh /dev/shm or project-output directory')
    tech = args.pdk.resolve()/'libs.tech'; models = tech/'ngspice/models'
    expected = {**{str(models/n): h for n, h in tx.MODEL_HASHES.items()},
                **{str(tech/n): h for n, h in resistor.RES_HASHES.items()}}
    if any(tx.sha(Path(p)) != h for p, h in expected.items()): ap.error('Foundry model revision mismatch')
    inputs = [NETLIST, Path(__file__).resolve(), Path(tx.__file__), Path(resistor.__file__),
              *map(Path, expected), args.ngspice.resolve(), args.openvaf.resolve()]
    pins = {str(p): tx.sha(p) for p in inputs}; out.mkdir(parents=True)
    record = dict(status='RUNNING', source_sha256=pins, pdk_revision=tx.PDK_REV, quick=args.quick,
                  limits=LIMITS, ui_s=UI, bits=BITS, cases=[], ac_cases=[],
                  assumptions=dict(vcm_v=1.36, ideal_reference_a=.0005, source_impedance_each_ohm=50,
                    output_load_each_f=100e-15, substrate_model_node_v=0,
                    simulated_physical_substrate_tap_rc=False, clock_or_slicer_present=False),
                  scope='Foundry-model four-HBT/four-rsil continuous-time RX preamplifier. Native self-heating resistors; ideal external bias/reference and source. No pad/ESD, offset/noise/jitter/BER, CTLE, slicer, CDR, PLL, lane bonding, PEX or PHY qualification.',
                  pcie_compliance=False, physical_qualification=False, manufacturing_approval=False)
    def save():
        p=out/'result.tmp';p.write_text(json.dumps(record, indent=2)+'\n');p.replace(out/'result.json')
    try:
        save(); osdi=out/'r3_cmc.osdi'
        record['compile']=execute([str(args.openvaf.resolve()), str(tech/'verilog-a/r3_cmc/r3_cmc.va'), '-o', str(osdi)], out, out/'compile.log')
        record['osdi_sha256']=tx.sha(osdi)
        selected=cases(args.quick)
        for case in selected:
            dest=out/case['name'];dest.mkdir();shutil.copyfile(NETLIST, dest/NETLIST.name)
            text,bits=deck(case, models, osdi);(dest/'bench.cir').write_text(text)
            entry=dict(case=case);record['cases'].append(entry);save()
            entry['execution']=execute([str(args.ngspice.resolve()), '-n', '-b', 'bench.cir'], dest, dest/'run.log')
            entry['measurement']=measure(dest/'wave.dat', case, bits)
            entry['expected_screen_pass']=case['fault'] is None
            entry['expected_outcome_observed']=entry['measurement']['screen_pass']==entry['expected_screen_pass']
            entry['wave_sha256']=tx.sha(dest/'wave.dat')
            with (dest/'wave.dat').open('rb') as src, gzip.open(dest/'wave.dat.gz', 'wb', compresslevel=1) as dst: shutil.copyfileobj(src,dst)
            (dest/'wave.dat').unlink()
            entry['output_sha256']={p.name:tx.sha(p) for p in dest.iterdir() if p.is_file()};save()
            print(case['name'], 'EXPECTED' if entry['expected_outcome_observed'] else 'UNEXPECTED',
                  entry['measurement']['min_signed_margin_v'], entry['measurement']['min_vce_v'], flush=True)
        # Independent balanced-bias AC decks: all nine HBT/resistor pairs at nominal V/T.
        ac_specs = [('hbt_typ','res_typ')] if args.quick else itertools.product(
            ('hbt_typ','hbt_bcs','hbt_wcs'),('res_typ','res_bcs','res_wcs'))
        for hbt,res in ac_specs:
            case=dict(selected[0],hbt=hbt,resistor=res,temp=27,supply=1.8)
            dest=out/('ac_'+hbt+'_'+res);dest.mkdir();shutil.copyfile(NETLIST,dest/NETLIST.name)
            text,_=deck(case,models,osdi,ac=True);(dest/'bench.cir').write_text(text)
            execution=execute([str(args.ngspice.resolve()),'-n','-b','bench.cir'],dest,dest/'run.log')
            record['ac_cases'].append(dict(case=case,execution=execution,measurement=measure_ac(dest/'ac.dat'),
                output_sha256={p.name:tx.sha(p) for p in dest.iterdir() if p.is_file()}));save()
        measured={x['case']['name']:x['measurement'] for x in record['cases']}
        base=measured['hbt_typ_res_typ_27_1.8'];half=measured['half_timestep']
        delta=abs(base['min_signed_margin_v']-half['min_signed_margin_v'])
        power=abs(base['analog_supply_power_w']/half['analog_supply_power_w']-1)
        record['timestep_sensitivity']=dict(margin_difference_v=delta,power_relative_difference=power,
            screen_pass=delta<.001 and power<.002,scope='Two numerical steps, not extrapolated convergence.')
        if any(tx.sha(Path(p))!=h for p,h in pins.items()):raise RuntimeError('Input bytes changed during simulation')
        record['source_bytes_unchanged']=True
        passed=all(x['expected_outcome_observed'] for x in record['cases']) and record['timestep_sensitivity']['screen_pass']
        record['status']='PASS_RX_PREAMP_SCREEN_ONLY' if passed else 'FAIL_RX_PREAMP_SCREEN'
        record['complete_pvt_cross_product']=not args.quick
    except BaseException as exc:
        record.update(status='ERROR_PRESERVED',error=repr(exc));raise
    finally:save()
    return 0 if record['status']=='PASS_RX_PREAMP_SCREEN_ONLY' else 1


if __name__=='__main__': raise SystemExit(main())
