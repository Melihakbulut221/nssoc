#!/usr/bin/env python3
# SPDX-FileCopyrightText: 2026 Hasan Melih Akbulut
# SPDX-License-Identifier: Apache-2.0
"""Powered351-device diagnostic: ideal wires versus actual distributed wire RC.

No elapsed-time cancellation. Explicit external ideal BODY_ESD_RETURN/WIRE_CREF
sources are testbench assumptions, not physical substrate attachment or full PEX.
All351 intrinsic devices remain present; native VCO generates the sampler clock.
"""
import argparse
import gzip
import hashlib
import json
import math
import os
from pathlib import Path
import re
import resource
import signal
import subprocess
import threading
import time

import build_pcie_bank_hybrid_v1 as h

HYBRID_SHA = 'ab1dc586e39e3476309089fed2c16177e15d501c6ff76190b2522f52983f9cc4'
COMPOSITION_SHA = '3f33871ff7fca9c9c1175001d1bb21bfde7e9534dc8ec58a95b4663503403833'
METHOD_SHA = '0726938af9c2388c415d8c8d0776ecc0efc6d351a08a106fb8a6bdbf0a734a6a'
NG_SHA = 'eaca52dad06845779fed4f50420a6a0cf4a32776e6a572432275f350002b87b8'
STOP = 4e-9
STEP = 2e-12
BEGIN = 2e-9
# All newly owned wire/precision/hybrid scratch, excluding symlink targets and
# immutable shared source GDS/PDK/native tools. Explicit historical roots count.
OWN_ROOTS = [
    '/dev/shm/nssoc-magic-cap-precision-v3-build',
    '/dev/shm/nssoc-bank-wire-cap-precision-v3-01',
    '/dev/shm/nssoc-bank-wire-rc-actual-v1-01',
    '/dev/shm/nssoc-bank-wire-rc-v1-01', '/dev/shm/nssoc-bank-wire-rc-v1-02',
    '/dev/shm/nssoc-bank-wire-rc-geometry-v1', '/dev/shm/nssoc-bank-wire-port-loss-v1',
    '/dev/shm/nssoc-cap-precision-v3-regressions',
    '/dev/shm/nssoc-cap-precision-v3-regressions-recorded',
    '/dev/shm/nssoc-cap-precision-v3-mutants',
    '/dev/shm/nssoc-bank-hybrid-v1-01',
    '/dev/shm/nssoc-bank-wire-transfer-v1-01', '/dev/shm/nssoc-bank-wire-transfer-v1-02',
    '/dev/shm/nssoc-bank-wire-transfer-v1-final',
]


def sha(data):
    return hashlib.sha256(data).hexdigest()


def physical_to_ideal(composition, anchors):
    public = {a['wire_component']: a['detail']['name'] for a in anchors['anchors']
              if a['kind'] == 'PUBLIC_PORT_REFERENCE'}
    mapping = {}
    for a in anchors['anchors']:
        if a['kind'] != 'INTRINSIC_DEVICE_TERMINAL_REFERENCE':
            continue
        native = 'w_' + a['label']
        component = a['wire_component']
        mapping[native] = public.get(component, f'ideal_c{component:03d}')
    h.require(len(mapping) == 748, 'Ideal reference terminal census')
    nodes = {n for d in composition['records'] for n in [t['node'] for t in d['terminals']]}
    h.require(nodes - set(mapping) == {'BODY_ESD_RETURN', 'body_well_206'}, 'Unexpected nonmetal reference')
    return mapping


def circuit(composition, hybrid_text, mapping, mode):
    h.require(mode in ('intrinsic_only', 'distributed_wire'), 'Unsupported comparison mode')
    if mode == 'distributed_wire':
        return hybrid_text
    lines = ['* Deliberate ideal-wire reference; NO physical RC acceptance.',
             '.subckt nssoc_bank_hybrid_open_v1 ' + ' '.join(composition['ports'])]
    for d in composition['records']:
        tokens = d['line'].split(); count = len(d['terminals'])
        tokens[1:1 + count] = [mapping.get(n, n) for n in tokens[1:1 + count]]
        lines.append(' '.join(tokens))
    lines += ['.ends nssoc_bank_hybrid_open_v1', '']
    h.require(len(lines) == 355, 'Ideal reference dropped intrinsic device')
    return '\n'.join(lines)


def node_expression(node, ports, mapping, mode):
    if mode == 'intrinsic_only':
        node = mapping.get(node, node)
    return 'v(' + (node if node in ports else 'xbank.' + node) + ')'


def vector_contract(comp, mapping, mode):
    ports = comp['ports']
    hbts = []
    for d in comp['records']:
        if d['model'] != 'npn13G2':
            continue
        terms = {r['terminal']: r['node'] for r in d['terminals']}
        row = dict(id=d['native_id'], Nx=int(d['native_parameters']['Nx']),
                   current=f'@q.xbank.xd{d["native_id"]:04d}.qnpn13g2[ic]')
        row.update({name: node_expression(terms[name], ports, mapping, mode) for name in ('C', 'B', 'E')})
        hbts.append(row)
    pairs = [('T0053', 'T0057'), ('T0081', 'T0077'), ('T0149', 'T0153'), ('T0181', 'T0177'),
             ('T0233', 'T0237'), ('T0261', 'T0257'), ('T0321', 'T0325'), ('T0353', 'T0349')]
    def expr(label):
        return node_expression('w_' + label, ports, mapping, mode)
    clocks = [[expr(a), expr(b)] for a, b in pairs]
    drivers = [[expr(p), expr(n)] for p, n in [('T0418', 'T0414'), ('T0438', 'T0426'), ('T0442', 'T0430'), ('T0446', 'T0434')]]
    outputs = [[f'v(L{i}_SAMPLER_QP)', f'v(L{i}_SAMPLER_QN)'] for i in range(4)]
    vectors = sorted({v for d in hbts for v in (d['C'], d['B'], d['E'], d['current'])} |
                     {v for pair in clocks + drivers + outputs for v in pair} |
                     {f'v({p})' for p in ports} |
                     {'i(vs_avdd1v8)', 'i(vs_avdd2v3)', 'i(vs_avdd2v5)'})
    h.require(len(hbts) == 122, 'HBT bounds census')
    return dict(vectors=vectors, hbts=hbts, clock_inputs=clocks, clock_drivers=drivers, sampler_outputs=outputs)


def input_wave(lane, positive):
    # Explicit finite 8GT/s PRBS7 source, unrelated to the free-running VCO phase.
    seed = 0x5D ^ (lane << 1)
    points = [(0.0, 0.0), (1e-9, 1.36), (1.5e-9, 1.36)]
    old = 1.36
    for i in range(24):
        bit = seed & 1
        seed = ((seed << 1) | (((seed >> 6) ^ (seed >> 5)) & 1)) & 0x7F
        value = 1.36 + (0.08 if bit == positive else -0.08)
        at = 1.5e-9 + i * 125e-12
        if i:
            points.append((at, old))
        points.append((at + 5e-12, value)); old = value
    return 'PWL(' + ' '.join(f'{t:.14g} {v:.14g}' for t, v in points) + ')'


def deck(comp, contract, models, osdis):
    lines = ['Full351-device bank powered diagnostic, explicit ideal external body references']
    lines += [f'.lib "{models}/corner{k}.lib" {c}' for k, c in
              [('HBT', 'hbt_typ'), ('RES', 'res_typ'), ('MOShv', 'mos_tt'), ('CAP', 'cap_typ')]]
    lines += [f'.include "{models}/sg13g2_esd.lib"', '.include "bank.spice"', '.temp 27',
              '.options reltol=1e-4 abstol=1e-12']
    rails = dict(AVDD1V8=1.8, AVDD2V3=2.3, AVDD2V5=2.5, ESD_VDD=2.5,
                 AVSS=0, SUB=0, ESD_RETURN=0, BODY_ESD_RETURN=0, WIRE_CREF=0, VCTRL=0.85)
    bound = set(rails)
    for name, v in rails.items():
        lines.append(f'Vs_{name.lower()} {name} 0 PWL(0 0 1n {v})')
    for lane in range(4):
        prefix = f'L{lane}_'
        for kind, current, supply in [('TX', 0.0015, 'AVDD1V8'), ('RX', 0.00075, 'AVDD1V8'), ('SAMPLER', 0.0005, 'AVDD2V5')]:
            name = prefix + kind + '_IREF'; bound.add(name)
            lines.append(f'I_{name} {supply} {name} PWL(0 0 1n {current})')
        for suffix, value in [('TX_INP', 1.51), ('TX_INN', 1.21), ('RX_VCM', 1.36)]:
            name = prefix + suffix; bound.add(name)
            lines.append(f'V_{name} {name} 0 PWL(0 0 1n {value})')
        for suffix, sign in [('RX_INP', True), ('RX_INN', False)]:
            name = prefix + suffix; bound.add(name)
            lines += [f'V_{name} source_{name} 0 ' + input_wave(lane, sign), f'RS_{name} source_{name} {name} 50']
        for suffix in ('SAMPLER_QP', 'SAMPLER_QN'):
            name = prefix + suffix; bound.add(name)
            lines.append(f'CLOAD_{name} {name} 0 150f')
        for suffix in ('TX_OUTP', 'TX_OUTN'):
            bound.add(prefix + suffix)  # External open; native ESD and wire remain.
    h.require(bound == set(comp['ports']), 'External source/load contract incomplete')
    lines += ['XBANK ' + ' '.join(comp['ports']) + ' nssoc_bank_hybrid_open_v1', '.control']
    lines += ['pre_osdi ' + str(p) for p in osdis]
    for bjt in contract['hbts']:
        qname = f'q.xbank.xd{bjt["id"]:04d}.qnpn13g2'
        lines += [f'alter @{qname}[off]=1', f'echo NSSOC_FLAG_BEGIN {qname}', f'show {qname} : off', 'echo NSSOC_FLAG_END']
    vectors = contract['vectors']
    lines += ['set wr_singlescale', 'set wr_vecnames', 'set numdgt=16']
    lines += ['save ' + ' '.join(vectors[i:i+40]) for i in range(0, len(vectors), 40)]
    lines += ['op', 'wrdata initial-op.dat ' + ' '.join(vectors),
              f'tran {STEP:.14g} {STOP:.14g} 0 {STEP:.14g}',
              'wrdata wave.fifo ' + ' '.join(vectors), 'echo NSSOC_POWERED_BANK_COMPLETE', 'quit', '.endc', '.end', '']
    return '\n'.join(lines)


def limits():
    resource.setrlimit(resource.RLIMIT_AS, (2 * 1024**3,) * 2)
    resource.setrlimit(resource.RLIMIT_CORE, (0, 0))


def regular_size(root):
    return sum(p.stat().st_size for p in root.rglob('*') if p.is_file() and not p.is_symlink()) if root.exists() else 0


def owned_size(out):
    return sum(regular_size(Path(p)) for p in set(OWN_ROOTS + [str(out)]))


def shared_free():
    stat = os.statvfs('/dev/shm')
    return stat.f_bavail * stat.f_frsize


def stream_wave(fifo, compressed, record):
    digest = hashlib.sha256(); raw_bytes = 0
    try:
        with fifo.open('rb', buffering=0) as src, gzip.open(compressed, 'wb', compresslevel=6) as dst:
            while chunk := src.read(65536):
                digest.update(chunk); raw_bytes += len(chunk); dst.write(chunk)
                record.update(raw_bytes=raw_bytes)
        record.update(complete=True, raw_sha256=digest.hexdigest(), compressed=h.pin(compressed))
    except Exception as error:
        record['error'] = repr(error)


def wave_measure(path, contract):
    columns = ['time', *contract['vectors']]
    index = {n: i for i, n in enumerate(columns)}
    peak = [[math.inf, -math.inf] for _ in contract['clock_inputs'] + contract['clock_drivers'] + contract['sampler_outputs']]
    pairs = contract['clock_inputs'] + contract['clock_drivers'] + contract['sampler_outputs']
    crossings = [[] for _ in pairs]
    bjt_bounds = {d['id']: dict(min_vce=math.inf, max_vce=-math.inf, peak_abs_current_per_emitter_a=0.0) for d in contract['hbts']}
    previous = None; samples = 0; active = 0; first = None; last = None; max_gap = 0
    with gzip.open(path, 'rt') as file:
        h.require(file.readline().split() == columns, 'Wave vector order/identity differs')
        for line in file:
            row = [float(v) for v in line.split()]
            h.require(len(row) == len(columns) and all(math.isfinite(v) for v in row), 'Nonfinite/incomplete waveform')
            t = row[0]; samples += 1; first = t if first is None else first
            if previous is not None:
                h.require(t > last, 'Wave time order')
                max_gap = max(max_gap, t-last)
                h.require(t-last <= STEP * (1+1e-8), 'Native timestep gap exceeds recipe')
            if t >= BEGIN:
                active += 1
                for j, (a, b) in enumerate(pairs):
                    value = row[index[a]] - row[index[b]]
                    peak[j][0] = min(peak[j][0], value); peak[j][1] = max(peak[j][1], value)
                    if previous is not None and last >= BEGIN:
                        old = previous[index[a]] - previous[index[b]]
                        if old <= 0 < value:
                            crossings[j].append(last + (t-last)*(-old)/(value-old))
                for d in contract['hbts']:
                    vce = row[index[d['C']]] - row[index[d['E']]]; bound = bjt_bounds[d['id']]
                    bound['min_vce'] = min(bound['min_vce'], vce); bound['max_vce'] = max(bound['max_vce'], vce)
                    bound['peak_abs_current_per_emitter_a'] = max(bound['peak_abs_current_per_emitter_a'], abs(row[index[d['current']]])/d['Nx'])
            previous, last = row, t
    h.require(first is not None and first <= 1e-12 and last >= STOP * (1-1e-8) and active > 900, 'Incomplete waveform time coverage')
    signals = []
    for pair, extrema, edges in zip(pairs, peak, crossings):
        periods = [b-a for a,b in zip(edges,edges[1:])]
        signals.append(dict(vectors=pair,minimum_differential_v=extrema[0],maximum_differential_v=extrema[1],
                            rising_edges=len(edges),mean_frequency_hz=len(periods)/sum(periods) if periods else None,
                            rising_edge_times=edges))
    return dict(samples=samples,active_samples=active,time_start=first,time_end=last,max_time_gap=max_gap,
                operating_window_start_s=BEGIN,signals=signals,
                hbt_bounds=bjt_bounds,min_vce=min(b['min_vce'] for b in bjt_bounds.values()),
                max_vce=max(b['max_vce'] for b in bjt_bounds.values()),
                peak_abs_current_per_emitter_a=max(b['peak_abs_current_per_emitter_a'] for b in bjt_bounds.values()),
                screen_bounds=dict(min_vce=0.4,max_vce=1.6,max_collector_current_per_emitter_a=0.003),
                scope='Finite4ns diagnostic with2ns post-startup bounds; no synchronous-bit/BER/CDR or full-PVT acceptance')


def audit_native(root, contract):
    log = (root/'native.log').read_text()
    h.require(log.count('NSSOC_POWERED_BANK_COMPLETE') == 1, 'Missing native completion')
    sections = re.findall(r'NSSOC_FLAG_BEGIN (\S+)\n(.*?)NSSOC_FLAG_END', log, re.S)
    expected = [f'q.xbank.xd{d["id"]:04d}.qnpn13g2' for d in contract['hbts']]
    h.require([n for n,_ in sections] == expected, 'Native OFF flag census')
    for name, block in sections:
        h.require(re.findall(r'^\s*off\s+(\S+)\s*$', block, re.M) == ['1'], 'Native OFF flag value')
        h.require(re.findall(r'^\s*device\s+(\S+)\s*$', block, re.M) == [name[:21]], 'Native OFF device identity')
    initial = (root/'initial-op.dat').read_text().splitlines()
    h.require(len(initial) == 2 and initial[0].split()[1:] == contract['vectors'], 'Initial OP vector coverage')
    values = [float(v) for v in initial[1].split()]
    h.require(len(values) == len(contract['vectors'])+1 and all(math.isfinite(v) and abs(v)<1e-10 for v in values), 'Initial zero OP failed')
    diagnostics = [line for line in log.splitlines() if re.search(r'warning|error|failed|singular|timestep too small|nan',line,re.I)]
    return dict(initial_op_max_abs=max(map(abs,values)),native_off_flags=len(expected),numerical_diagnostics=diagnostics,
                numerical_clean=not diagnostics,metrics=wave_measure(root/'wave.dat.gz',contract))


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    for name in ('hybrid', 'composition', 'anchors', 'model_receipt', 'ngspice', 'pdk', 'osdi_root', 'out'):
        ap.add_argument('--'+name.replace('_','-'),type=Path,required=True)
    args = ap.parse_args()
    for path,digest in [(args.hybrid,HYBRID_SHA),(args.composition,COMPOSITION_SHA),(args.anchors,h.PINS['anchors']),
                        (Path(h.__file__),METHOD_SHA),(args.ngspice,NG_SHA)]:
        h.require(h.pin(path)['sha256']==digest,'Frozen powered input changed: '+str(path))
    receipt=json.loads(args.model_receipt.read_text());models=args.pdk/'libs.tech/ngspice/models'
    osdis=[args.osdi_root/n for n in ('r3_cmc.osdi','psp103.osdi','psp103_nqs.osdi')]
    for path in [*models.glob('*.lib'),*osdis]:
        h.require(str(path) in receipt['inputs'] and h.pin(path)==receipt['inputs'][str(path)],'Native model/OSDI changed')
    args.out.mkdir(parents=True,exist_ok=False)
    comp=json.loads(args.composition.read_text());anchors=json.loads(args.anchors.read_text());mapping=physical_to_ideal(comp,anchors)
    inputs={str(p):h.pin(p) for p in [Path(__file__),Path(h.__file__),args.hybrid,args.composition,args.anchors,args.model_receipt,args.ngspice,*models.glob('*.lib'),*osdis]}
    record=dict(status='RUNNING',inputs=inputs,cases=[],elapsed_cancellation=False,full_pex_qualified=False,
                body_reference_assumption='BODY_ESD_RETURN and WIRE_CREF independently held at ideal0V externally; no inferred internal body-to-metal link',
                internal_well_reference='Native two-terminal PMOS B / ntap WELL identity remains internal and finite-contact fed',
                comparison='All351 devices in both cases; ideal-wire reference deliberately removes all wireR/C, distributed case retains each exact32855R/16215C',
                external_source_contract=dict(AVDD1V8=1.8,AVDD2V3=2.3,AVDD2V5=2.5,ESD_VDD=2.5,VCTRL=0.85,
                    rx_vcm=1.36,rx_source_amplitude_each=0.08,rx_source_ohm_each=50,rx_iref_a=0.00075,
                    sampler_iref_a=0.0005,sampler_load_each_f=150e-15,tx_iref_a=0.0015,tx_inputs=[1.51,1.21],
                    ramp_s=1e-9,clock='actual native VCO, no external periodic clock',prbs='24 finitePRBS7 source bits at8GT/s, free phase relative to VCO'))
    def save():
        (args.out/'result.json').write_text(json.dumps(record,indent=2)+'\n')
    save()
    for mode in ('intrinsic_only','distributed_wire'):
        h.require(shared_free()>512*1024**2 and owned_size(args.out)<80*1024**2,'Resource reserve unavailable before native case')
        root=args.out/mode;root.mkdir();contract=vector_contract(comp,mapping,mode)
        (root/'contract.json').write_text(json.dumps(contract,indent=2)+'\n')
        (root/'bank.spice').write_text(circuit(comp,args.hybrid.read_text(),mapping,mode))
        (root/'bench.cir').write_text(deck(comp,contract,models,osdis))
        (root/'spinit').write_text('* Exact model OSDIs loaded explicitly by this private diagnostic.\n')
        fifo=root/'wave.fifo';os.mkfifo(fifo);stream={}
        reader=threading.Thread(target=stream_wave,args=(fifo,root/'wave.dat.gz',stream),daemon=True);reader.start()
        env={k:v for k,v in os.environ.items() if k not in ('GH_TOKEN','GITHUB_TOKEN')};env['SPICE_SCRIPTS']=str(root.resolve());env['OMP_NUM_THREADS']='1'
        row=dict(mode=mode,status='RUNNING',stream=stream,resources=[]);record['cases'].append(row);start=time.monotonic();reason=None
        with (root/'native.log').open('w') as log:
            proc=subprocess.Popen([str(args.ngspice.resolve()),'-n','-b','bench.cir'],cwd=root,env=env,preexec_fn=limits,
                                  stdout=log,stderr=subprocess.STDOUT,start_new_session=True)
            row['pid']=proc.pid;save()
            while proc.poll() is None:
                free=shared_free();size=owned_size(args.out)
                row['resources'].append(dict(elapsed_s=time.monotonic()-start,shared_free=free,own_scratch=size,stream_raw_bytes=stream.get('raw_bytes',0)))
                if free<512*1024**2:reason='SHARED_512MIB_RESERVE'
                elif size>80*1024**2:reason='OWN_80MIB_SCRATCH_LIMIT'
                if reason:
                    os.killpg(proc.pid,signal.SIGTERM);proc.wait();break
                save();time.sleep(2)
        # If native aborted before opening the FIFO, release the waiting collector.
        if reader.is_alive() and not stream.get('raw_bytes'):
            fd=os.open(fifo,os.O_WRONLY);os.close(fd)
        reader.join();fifo.unlink()
        row.update(returncode=proc.returncode,elapsed_seconds=time.monotonic()-start,resource_stop=reason)
        try:
            h.require(proc.returncode==0 and reason is None,'Native process/resource failure')
            h.require(stream.get('complete') is True and not stream.get('error'),'Incomplete lossless waveform stream')
            row['audit']=audit_native(root,contract)
            row['status']='COMPLETE_DIAGNOSTIC_NOT_ACCEPTANCE'
        except Exception as error:
            row.update(status='FAIL_PRESERVED',error=type(error).__name__+': '+str(error))
        row['outputs']={p.name:h.pin(p) for p in root.iterdir() if p.is_file()}
        save()
        if reason:break
    h.require(all(h.pin(p)==value for p,value in inputs.items()),'Powered source/runtime/model changed')
    record['status']='COMPLETE_PAIRED_DIAGNOSTIC_NOT_ACCEPTANCE' if len(record['cases'])==2 and all(c['status']=='COMPLETE_DIAGNOSTIC_NOT_ACCEPTANCE' for c in record['cases']) else 'FAIL_PRESERVED'
    save();print(record['status'])
    if record['status']=='FAIL_PRESERVED':raise SystemExit(1)


if __name__=='__main__':
    main()
