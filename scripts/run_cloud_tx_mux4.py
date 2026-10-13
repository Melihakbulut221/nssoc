#!/usr/bin/env python3
# SPDX-FileCopyrightText: 2026 Hasan Melih Akbulut
# SPDX-License-Identifier: Apache-2.0
"""Native 4:1 serializer tree; all stages loaded by actual next-stage devices.

Four 2Gb/s CMOS streams feed two 2:1 HBT muxes, then the existing final mux
and TX load at 8GT/s. Source clock phases and biases remain external ideal
sources; this is not a complete 32:1 serializer, clock tree, PHY or layout.
"""
import argparse
import gzip
import hashlib
import json
import os
from pathlib import Path
import re
import resource
import shutil
import subprocess
import tarfile
import time
import numpy as np

from cloud_tx_data_driver import original_bit_output_screen
from run_cloud_tx_operating_point import CONDITIONS, fetch, sha

ROOT = Path(__file__).resolve().parents[1]
UI, START, BITS = 125e-12, 2e-9, 256
STOP = START + UI * BITS
PRE = ROOT / 'hw/soc/analog/pcie/tx_mux2_hbt_cascade_v1.spice'
FRONT = ROOT / 'hw/soc/analog/pcie/tx_cmos_hv_resistive_input_v5.inc'
TX = ROOT / 'hw/soc/analog/pcie/tx_cml_rsil.spice'


def sequence():
    state, out = 0x5d, []
    for _ in range(BITS):
        out.append(state & 1)
        state = ((state << 1) | (((state >> 6) ^ (state >> 5)) & 1)) & 127
    return out


def pwl(values, cm, amplitude, period, origin, invert=False):
    def level(bit):
        return cm + amplitude * (1 if bool(bit) != invert else -1)
    points = [(0, 0), (1e-9, level(values[0]))]
    for index in range(1, len(values)):
        if values[index] != values[index - 1]:
            edge = origin + index * period
            if edge >= STOP:
                break
            assert edge > points[-1][0]
            points += [(edge, level(values[index - 1])), (edge + 10e-12, level(values[index]))]
    points.append((STOP, points[-1][1]))
    assert all(b[0] > a[0] for a, b in zip(points, points[1:]))
    return 'PWL(\n+ ' + '\n+ '.join(f'{t:.14g} {v:.14g}' for t, v in points) + ')'


def bind_devices(path, instance, ports, model_names):
    lines = path.read_text().splitlines()
    header = next(line.lower().split() for line in lines if line.lower().startswith('.subckt '))
    mapping = dict(zip(header[2:], ports, strict=True))
    def node(n):
        return mapping.get(n, instance + '.' + n)
    devices = {}
    for line in lines:
        f = line.lower().split()
        if len(f) > 5 and f[0].startswith('x') and f[5] in model_names:
            row = dict(model=f[5], terminals=[node(n) for n in f[1:5]])
            if f[5] == 'npn13g2':
                row['nx'] = int(next(v.split('=')[1] for v in f[6:] if v.startswith('nx=')))
                assert 1 <= row['nx'] <= 10
            devices[instance + '.' + f[0]] = row
    return header[1], devices


def prepare_inputs(inputs):
    spec = json.loads((ROOT / 'docs/evidence/pcie-tx-cloud-input-20261013.json').read_text())
    front = json.loads((ROOT / 'docs/evidence/pcie-cmos-data-driver-input-20261013.json').read_text())
    for name, record, dest in [('native', spec['receipt'], inputs),
                              ('frontend', front['receipt'], inputs / 'frontend')]:
        packed = inputs / (name + '.tar.gz')
        fetch(record['url'], record['sha256'], packed)
        assert packed.stat().st_size == record['bytes']
        with tarfile.open(packed) as archive:
            archive.extractall(dest, filter='data')
        packed.unlink()
        manifest = json.loads((dest / 'manifest.json').read_text())
        assert all(sha(dest / name) == record['sha256'] for name, record in manifest['files'].items())
    bundle = spec['method_archives'][1]
    member, expected = next((n, h) for n, h in bundle['members'].items() if n.endswith('mux54-compact01.spice'))
    packed = inputs / 'exact-final-stage.tar.gz'
    fetch(bundle['url'], bundle['sha256'], packed)
    with tarfile.open(packed) as archive:
        data = archive.extractfile(member).read()
    assert hashlib.sha256(data).hexdigest() == expected
    (inputs / 'mux54-compact01.spice').write_bytes(data)
    packed.unlink()
    assert sha(TX) == spec['tx_sha256']
    assert sha(os.environ['CLOUD_NGSPICE']) == spec['native_runtime']['executable_sha256']
    return spec


def build(inputs, condition, fault='none'):
    bits = sequence()
    c = dict(temperature_c=27, supply_scale=1., core_scale=1., hbt='hbt_typ',
             resistor='res_typ', lv_corner='mos_tt', hv_corner='mos_tt', step_ps=.5)
    c.update(CONDITIONS[condition])
    frontend = inputs / 'frontend'
    final = inputs / 'mux54-compact01.spice'
    lines = ['NSSOC native full two-level 4:1 tree, unchanged source-bit oracle']
    for kind, corner, directory in [('HBT', c['hbt'], inputs / 'models'),
        ('RES', c['resistor'], inputs / 'models'), ('MOSlv', c['lv_corner'], frontend / 'models'),
        ('MOShv', c['hv_corner'], frontend / 'models')]:
        lines.append(f'.lib "{directory / ("corner" + kind + ".lib")}" {corner}')
    lines += [f'.include "{p}"' for p in (PRE, FRONT, TX, final, frontend / 'buf16.inc')]
    lines += [f'.temp {c["temperature_c"]}', '.options reltol=1e-4 abstol=1e-12']
    rails = {'avdd': 2.5*c['supply_scale'], 'tvdd': 1.8*c['supply_scale'], 'dvdd': 1.2*c['core_scale']}
    lines += [f'V{name} {name} 0 PWL(0 0 1n {v:.12g})' for name, v in rails.items()]
    hbt, mos = {}, {}
    for bank in range(4):
        for suffix, invert in [('p', True), ('n', False)]:
            name = f'd{bank}{suffix}'
            source = name + '0'
            gate_pwl = pwl(bits[bank::4], .6*c['core_scale'], .6*c['core_scale'],
                           4*UI, START + (bank-3)*UI, invert)
            lines.append(f'V{name} {source} 0 ' + gate_pwl)
            ports = [source, name, 'avdd', 'dvdd', '0', '0']
            subckt, found = bind_devices(FRONT, 'xad_'+name, ports, {'sg13_hv_nmos'})
            assert len(found) == 4
            mos.update(found)
            front_header = next(line.lower().split() for line in FRONT.read_text().splitlines()
                                if line.lower().startswith('.subckt '))
            portmap = dict(zip(front_header[2:], ports, strict=True))
            buf = next(line.lower().split() for line in FRONT.read_text().splitlines()
                       if line.lower().startswith('xbuf '))
            assert len(buf) == 6 and buf[-1] == 'sg13g2_buf_16'
            buf_ports = [portmap.get(n, 'xad_'+name+'.'+n) for n in buf[1:5]]
            _, found = bind_devices(frontend / 'buf16.inc', 'xad_'+name+'.xbuf',
                buf_ports, {'sg13_lv_nmos', 'sg13_lv_pmos'})
            assert len(found) == 4
            mos.update(found)
            lines.append('XAD_'+name+' '+' '.join(ports)+' '+subckt)
    # Actual port permutations implement interleaving, not an oracle permutation.
    stages = [
        (PRE, 'xprea', ['d0p','d0n','d2p','d2n','sap','san','ap','an','avdd','0','0','ra']),
        (PRE, 'xpreb', ['d1p','d1n','d3p','d3n','sbp','sbn','bp','bn','avdd','0','0','rb']),
    ]
    if fault == 'swap_pre_a_select':
        stages[0][2][4:6] = ['san', 'sap']
    formal = next(line.lower().split() for line in final.read_text().splitlines() if line.lower().startswith('.subckt '))
    public = dict(ap='ap',an='an',bp='bp',bn='bn',sp='sp',sn='sn',op='mp',on='mn',
                  avdd='avdd',avss='0',sub='0',iref='mr',wire_cref='0')
    stages += [(final, 'xmux', [public[p] for p in formal[2:]]),
               (TX, 'xtx', ['mp','mn','op','on','tvdd','0','0','tr'])]
    for path, instance, ports in stages:
        name, found = bind_devices(path, instance, ports, {'npn13g2'})
        assert len(found) == (4 if instance == 'xtx' else 19)
        hbt.update(found)
        lines.append(instance+' '+' '.join(ports)+' '+name)
    assert len(hbt) == 61 and len(mos) == 64
    for reference in ('ra', 'rb', 'mr'):
        bias = 0 if fault == 'disable_pre_b_bias' and reference == 'rb' else .0005
        lines.append(f'I{reference} avdd {reference} PWL(0 0 1n {bias})')
    lines.append('ITX tvdd tr PWL(0 0 1n .0015)')
    for name, origin, period in [('sa', START-UI, 2*UI), ('sb', START, 2*UI), ('s', START, UI)]:
        for suffix, invert in [('p',False),('n',True)]:
            key = name + suffix
            stimulus = pwl([int(i % 2 == 0) for i in range(BITS)], 1.23, .08, period, origin, invert)
            lines += [f'V{key} {key}0 0 '+stimulus, f'R{key} {key}0 {key} 25']
    lines += ['RLOAD op on 100','COP op 0 100f','CON on 0 100f']
    nodes = ({n for row in [*hbt.values(), *mos.values()] for n in row['terminals']} | set(rails)) - {'0'}
    nodes.update(f'd{i}{suffix}0' for i in range(4) for suffix in ('p','n'))
    vectors = ['v('+n+')' for n in sorted(nodes)] + ['i(v'+n+')' for n in rails]
    vectors += ['@q.'+n+'.qnpn13g2[ic]' for n in hbt]
    assert len(vectors) == len(set(vectors))
    lines += ['.control', f'pre_osdi {inputs / "r3_cmc.osdi"}',
              f'pre_osdi {frontend / "psp103.osdi"}', f'pre_osdi {frontend / "psp103_nqs.osdi"}',
              'set wr_singlescale', 'set wr_vecnames', 'set numdgt=16', 'save '+' '.join(vectors)]
    for name in hbt:
        device = 'q.' + name + '.qnpn13g2'
        lines += [f'alter @{device}[off] = 1', 'echo NSSOC_NATIVE_FLAG_BEGIN '+device,
                  'show '+device+' : off', 'echo NSSOC_NATIVE_FLAG_END']
    lines += ['op','wrdata op.dat '+' '.join(vectors),
              f'tran {c["step_ps"]*1e-12:.14g} {STOP:.14g} 0 {c["step_ps"]*1e-12:.14g}',
              'wrdata wave.dat '+' '.join(vectors), 'quit','.endc','.end']
    return '\n'.join(lines)+'\n', dict(condition=c, fault=fault, bits=bits, hbt=hbt, mos=mos,
        rails=rails, vectors=vectors, source_bits_sha256=hashlib.sha256(bytes(bits)).hexdigest())


def review(run, contract):
    vectors = contract['vectors']
    op = np.loadtxt(run/'op.dat', skiprows=1)
    assert op.size == len(vectors)+1 and np.isfinite(op).all() and abs(op).max() <= 1e-10
    with (run/'wave.dat').open() as stream:
        assert stream.readline().split() == ['time', *vectors]
        data = np.loadtxt(stream)
    assert data.shape[1] == len(vectors)+1 and np.isfinite(data).all()
    t = data[:,0]
    assert t[0] == 0 and abs(t[-1]-STOP) < 1e-18 and np.all(np.diff(t)>0)
    values = dict(zip(vectors, data[:,1:].T, strict=True))
    zeros = np.zeros_like(t)
    def volt(node):
        return zeros if node == '0' else values['v('+node+')']
    for name, expected in contract['rails'].items():
        assert np.max(np.abs(volt(name)-expected*np.clip(t/1e-9,0,1))) < 1e-9
    active = t >= START
    devices = {}
    for name, row in contract['hbt'].items():
        c,b,e,_ = (volt(n) for n in row['terminals'])
        ce, be, current = c-e, b-e, values['@q.'+name+'.qnpn13g2[ic]']/row['nx']
        r = dict(min_post_vce_v=float(ce[active].min()),max_post_vce_v=float(ce[active].max()),
                 max_whole_abs_vce_v=float(abs(ce).max()),max_whole_abs_vbe_v=float(abs(be).max()),
                 max_whole_abs_ic_per_emitter_a=float(abs(current).max()))
        r['passed'] = r['min_post_vce_v'] >= .4 and r['max_whole_abs_vce_v'] <= 1.6 and r['max_whole_abs_vbe_v'] <= 1 and r['max_whole_abs_ic_per_emitter_a'] <= .003
        devices[name] = r
    mos = {}
    for name,row in contract['mos'].items():
        d,g,s,b = (volt(n) for n in row['terminals'])
        limit = 2.75 if row['model'].startswith('sg13_hv_') else 1.32
        peaks = {label:float(abs(v).max()) for label,v in [('vds',d-s),('vgs',g-s),('vgd',g-d)]}
        mos[name] = dict(peaks=peaks, limit_v=limit, passed=max(peaks.values())<=limit)
    def interface(stage):
        samples = []
        for i,bit in enumerate(contract['bits']):
            prefix = ('a' if i%2==0 else 'b') if stage=='final' else f'd{i%4}'
            for phase in (.3,.5,.7):
                at = START+(i+phase)*UI
                p,n = (np.interp(at,t,volt(prefix+suffix)) for suffix in ('p','n'))
                samples.append(((p-n)*(2*bit-1),(p+n)/2))
        margin,cm = np.asarray(samples).T
        return dict(samples=len(samples),minimum_margin_v=float(margin.min()),
            wrong_sign_samples=int((margin<=0).sum()),below_150mv_samples=int((margin<.15).sum()),
            common_mode_range_v=[float(cm.min()),float(cm.max())],
            passed=bool((margin>=.15).all() and (cm>=1.8).all() and (cm<=2.05).all()))
    signal = original_bit_output_screen(t,volt('op'),volt('on'),contract['bits'],START,UI)
    interfaces = {name:interface(name) for name in ('cmos', 'final')}
    return dict(zero_source_op=True,rows=len(t),coverage_s=[float(t[0]),float(t[-1])],
        signals=signal,hbt_devices=devices,mos_devices=mos,interfaces=interfaces,
        failed_hbts={n:r for n,r in devices.items() if not r['passed']},
        failed_mos={n:r for n,r in mos.items() if not r['passed']},
        all_engineering_gates_passed=signal['passed'] and all(r['passed'] for r in interfaces.values()) and
                                   all(r['passed'] for r in [*devices.values(),*mos.values()]))


def main():
    global PRE, FRONT
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--condition',choices=tuple(CONDITIONS),default='nominal')
    parser.add_argument('--fault',choices=('none','swap_pre_a_select','disable_pre_b_bias'),default='none')
    parser.add_argument('--prestage',choices=('divider9','divider14'),default='divider9')
    parser.add_argument('--frontend',choices=('direct','damped'),default='direct')
    args=parser.parse_args()
    if args.prestage=='divider14':
        PRE=ROOT/'hw/soc/analog/pcie/tx_mux2_hbt_cascade_v2.spice'
    if args.frontend=='damped':
        FRONT=ROOT/'hw/soc/analog/pcie/tx_cmos_hv_resistive_input_v6.inc'
    out=ROOT/'cloud-tx-mux4';out.mkdir(exist_ok=False)
    inputs=out/'inputs';inputs.mkdir()
    run=out/'native';run.mkdir()
    result=dict(status='RUNNING',condition=args.condition,fault=args.fault,prestage=args.prestage,frontend=args.frontend,accepted=False,
        scope='Actual 61-HBT/64-MOS two-level 4:1 schematic, ideal external clock phases and reference currents. Four synchronous2Gb/s sources; final8GT/s 256-bit original oracle unchanged. No upstream32:1 tree, PLL/CDR, physical layout, PEX, ESD, jitter/BER or full PHY acceptance.')
    try:
        prepare_inputs(inputs)
        deck,contract=build(inputs,args.condition,args.fault)
        (run/'bench.cir').write_text(deck)
        (run/'contract.json').write_text(json.dumps(contract,indent=2)+'\n')
        (run/'spinit').write_text('set num_threads=1\n')
        paths=[PRE,FRONT,TX,Path(__file__),ROOT/'scripts/cloud_tx_data_driver.py',
               ROOT/'scripts/run_cloud_tx_operating_point.py',Path(os.environ['CLOUD_NGSPICE']),
               *[p for p in inputs.rglob('*') if p.is_file()],run/'bench.cir',run/'contract.json',run/'spinit']
        result['inputs']={str(p):sha(p) for p in paths}
        def limits():
            resource.setrlimit(resource.RLIMIT_AS,(4*1024**3,)*2)
            resource.setrlimit(resource.RLIMIT_FSIZE,(2*1024**3,)*2)
            resource.setrlimit(resource.RLIMIT_CORE,(0,0))
            os.sched_setaffinity(0,{min(os.sched_getaffinity(0))})
        env={k:v for k,v in os.environ.items() if k not in ('LD_PRELOAD','PYTHONPATH','PYTHONHOME','GH_TOKEN','GITHUB_TOKEN')}
        env.update(SPICE_SCRIPTS=str(run),RAYON_NUM_THREADS='1',OMP_NUM_THREADS='1')
        started=time.monotonic()
        with (run/'run.log').open('w') as log:
            code=subprocess.call([os.environ['CLOUD_NGSPICE'],'-n','-b','bench.cir'],cwd=run,env=env,
                                 stdout=log,stderr=subprocess.STDOUT,preexec_fn=limits)
        log=(run/'run.log').read_text(errors='replace')
        result.update(returncode=code,elapsed_s=time.monotonic()-started,
            diagnostics=[line for line in log.splitlines() if any(w in line.lower() for w in ('warning','error','nan','singular','stepping','too small','jmax','vmax'))])
        if code or not (run/'wave.dat').exists():
            print(log[-12000:],flush=True)
            raise RuntimeError('Native4:1 tree capture did not finish')
        flags=re.findall(r'(?ms)^NSSOC_NATIVE_FLAG_BEGIN (\S+)\n(.*?)^NSSOC_NATIVE_FLAG_END\s*$',log)
        assert [x[0] for x in flags]==['q.'+n+'.qnpn13g2' for n in contract['hbt']]
        assert all(re.findall(r'(?m)^\s*off\s+([01])\s*$',body)==['1'] for name,body in flags)
        result['review']=review(run,contract)
        assert all(sha(p)==digest for p,digest in result['inputs'].items())
        raw=run/'wave.dat';packed=run/'wave.dat.gz'
        result['raw_wave']=dict(bytes=raw.stat().st_size,sha256=sha(raw))
        with raw.open('rb') as src,gzip.open(packed,'xb',compresslevel=1) as dst: shutil.copyfileobj(src,dst)
        with gzip.open(packed,'rb') as src: assert hashlib.file_digest(src,'sha256').hexdigest()==result['raw_wave']['sha256']
        raw.unlink()
        result['native_off_flags_count']=len(flags)
        result['status']='COMPLETE_NATIVE_TREE_STUDY_NOT_PHY_ACCEPTANCE'
        result['component_screen_passed']=result['review']['all_engineering_gates_passed'] and not result['diagnostics']
        if args.fault!='none':
            result['fault_rejected_by_original_bits']=not result['review']['signals']['passed']
            assert result['fault_rejected_by_original_bits'], 'Actual stage fault escaped source-bit screen'
    except BaseException as error:
        result.update(status='FAIL_OR_ERROR',error=repr(error));raise
    finally:
        result['outputs']={str(p.relative_to(out)):sha(p) for p in run.rglob('*') if p.is_file()}
        (out/'result.json').write_text(json.dumps(result,indent=2)+'\n')
        print(json.dumps(result),flush=True)


if __name__=='__main__':
    main()
