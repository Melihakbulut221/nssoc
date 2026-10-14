#!/usr/bin/env python3
# SPDX-FileCopyrightText: 2026 Hasan Melih Akbulut
# SPDX-License-Identifier: Apache-2.0
"""Native 4/8/16/32:1 trees with every next-stage transistor actually connected.

Input rate is 8Gb/s divided by stream count. The full source-bit oracle,
physical device bounds and observation phases are unchanged. Clock modulation
remains external; even a passing 32:1 tree is not a PLL/CDR, full PHY or layout.
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

# Independent device corners, using exactly the same circuit geometry and
# source-bit timing. Copy the shared base table without altering other studies.
CONDITIONS = dict(CONDITIONS)
# Check narrow hot-wire margin at half the original maximum step.
CONDITIONS['hot_low_quarter_step'] = dict(CONDITIONS['hot_low'], step_ps=.25)
for _hbt in ('typ', 'bcs', 'wcs'):
    for _res in ('typ', 'bcs', 'wcs'):
        if (_hbt, _res) != ('typ', 'typ'):
            CONDITIONS[f'hbt_{_hbt}_res_{_res}'] = dict(hbt='hbt_'+_hbt, resistor='res_'+_res)
for _base, _field, _value in (
    ('hot_low', 'resistor', 'res_bcs'), ('hot_low', 'hbt', 'hbt_bcs'),
    ('cold_high', 'resistor', 'res_wcs'), ('cold_high', 'hbt', 'hbt_wcs')):
    CONDITIONS[_base+'_'+_value] = dict(CONDITIONS[_base], **{_field: _value})

ROOT = Path(__file__).resolve().parents[1]
UI, START, BITS = 125e-12, 2e-9, 256
STOP = START + UI * BITS
PRE = ROOT / 'hw/soc/analog/pcie/tx_mux2_hbt_cascade_v1.spice'
FRONT = ROOT / 'hw/soc/analog/pcie/tx_cmos_hv_resistive_input_v5.inc'
TX = ROOT / 'hw/soc/analog/pcie/tx_cml_rsil.spice'
BIAS = ROOT / 'hw/soc/analog/pcie/tx_clock_common_bias_v1.spice'
FAST_FINAL = ROOT / 'hw/soc/analog/pcie/tx_mux2_hbt_passive_drive_v2.spice'
TAPPED_FINAL = ROOT / 'hw/soc/analog/pcie/tx_mux54_passive_drive_v3.spice'
GUARDED_FINAL = ROOT / 'hw/soc/analog/pcie/tx_mux54_passive_drive_v4.spice'
MARGIN_FINAL = ROOT / 'hw/soc/analog/pcie/tx_mux54_passive_drive_v5.spice'
PRE_BIASES = {'baseline':.0005,'plus10':.00055,'plus20':.0006}
PRE_BIAS_MODES = (*PRE_BIASES, 'native_res')
PRE_FEED = ROOT / 'hw/soc/analog/pcie/tx_pre_bias_res_v1.inc'
CLOCK_FEED = ROOT / 'hw/soc/analog/pcie/tx_clock_bias_feed_v1.inc'
OUTPUT_FEEDS = ROOT / 'hw/soc/analog/pcie/tx_output_bias_feeds_v1.inc'
CLOCK_REFERENCES = {'baseline': BIAS, 'offset75': ROOT / 'hw/soc/analog/pcie/tx_clock_common_bias_v2.spice',
                    'stiff65': ROOT / 'hw/soc/analog/pcie/tx_clock_common_bias_v3.spice'}
CLOCK_FEEDS = {'baseline': CLOCK_FEED, 'offset75': CLOCK_FEED,
               'stiff65': ROOT / 'hw/soc/analog/pcie/tx_clock_bias_feed_v2.spice'}
assert CLOCK_REFERENCES.keys() == CLOCK_FEEDS.keys()


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


def tree_plan(streams):
    assert streams in (4,8,16,32)
    def label(stride,offset):
        return ('a','b')[offset] if stride==2 else f'p{stride}_{offset}'
    nodes=[]
    stride=2
    while stride<streams:
        for offset in range(stride):
            name=label(stride,offset)
            inputs=[f'd{i}' if 2*stride==streams else label(2*stride,i)
                    for i in (offset,offset+stride)]
            nodes.append(dict(label=name,inputs=inputs,clock='s'+name,reference='r'+name,
                              stride=stride,offset=offset,origin=START+(offset-(stride.bit_length()-1))*UI))
        stride*=2
    clocks=[*(dict(name=n['clock'],origin=n['origin'],period=n['stride']*UI) for n in nodes[:2]),
            dict(name='s',origin=START,period=UI),
            *(dict(name=n['clock'],origin=n['origin'],period=n['stride']*UI) for n in nodes[2:])]
    return dict(streams=streams,nodes=nodes,clocks=clocks,
                launch_offset=streams//2+(streams.bit_length()-2))


def physical_spec_path(profile):
    if profile == 'cascade158_kelvin_supply_direct':
        return ROOT/'docs/evidence/pcie-cascade158-kelvin-supply-direct-composition-20261013.json'
    if profile == 'cascade16_kelvin_dense_wide':
        return ROOT/'docs/evidence/pcie-cascade16-kelvin-dense-wide-composition-20261013.json'
    assert profile in ('baseline','wide_access','supply_access','power_trunks','power_trunks_vias','kelvin_dense_wide','kelvin_supply_feed','kelvin_supply_direct')
    prefix={'baseline':'','wide_access':'wide-access-','supply_access':'supply-access-','power_trunks':'power-trunks-','power_trunks_vias':'power-vias-','kelvin_dense_wide':'kelvin-dense-wide-','kelvin_supply_feed':'kelvin-supply-feed-','kelvin_supply_direct':'kelvin-supply-direct-'}[profile]
    return ROOT/'docs/evidence'/('pcie-cascade14-'+prefix+'composition-20261013.json')


def physical_final_spec_path(profile):
    if profile in ('v6_kelvin_dense_wide','v7_kelvin_dense_wide','v8_kelvin_dense_wide','v8_kelvin_tail_paths','v8_kelvin_local_tail','v8_kelvin_local_return','v8_kelvin_local_supply','v8_kelvin_local_internal','v8_kelvin_compact_internal','v8_kelvin_low_internal','v8_kelvin_low_critical','v8_kelvin_low_selects','v8_kelvin_low_selects_m3','v8_kelvin_low_selects_rows','v8_kelvin_low_ports','v8_kelvin_low_ports_deep','v8_kelvin_low_ports_loads','v8_kelvin_low_ports_shunts','v8_kelvin_low_ports_loads_shunts','v8_kelvin_low_ports_loads_shunts_series','v9_kelvin_low_critical','v10_kelvin_low_critical','v10_kelvin_low_ports_loads_shunts_series'):
        version, geometry = profile.split('_',1)
        geometry = geometry.replace('_', '-')
        return ROOT/'docs/evidence'/f'pcie-final-{version}-{geometry}-composition-20261013.json'
    assert profile in ('power_trunks','interleaved','kelvin_return','kelvin_short','kelvin_short_vias','kelvin_dense','kelvin_dense_wide','kelvin_signal_trunks','kelvin_m3_10')
    middle={'power_trunks':'','interleaved':'interleaved-','kelvin_return':'kelvin-','kelvin_short':'kelvin-short-','kelvin_short_vias':'kelvin-short-vias-','kelvin_dense':'kelvin-dense-','kelvin_dense_wide':'kelvin-dense-wide-','kelvin_supply_feed':'kelvin-supply-feed-','kelvin_supply_direct':'kelvin-supply-direct-','kelvin_signal_trunks':'kelvin-signal-trunks-','kelvin_m3_10':'kelvin-m3-10-'}[profile]
    return ROOT/'docs/evidence'/('pcie-final-v5-'+middle+'composition-20261013.json')


def physical_final_circuit_profile(profile):
    physical_final_spec_path(profile)  # Reject unknown routing/circuit bindings.
    if profile in ('v6_kelvin_dense_wide','v7_kelvin_dense_wide','v8_kelvin_dense_wide','v8_kelvin_tail_paths','v8_kelvin_local_tail','v8_kelvin_local_return','v8_kelvin_local_supply','v8_kelvin_local_internal','v8_kelvin_compact_internal','v8_kelvin_low_internal','v8_kelvin_low_critical','v8_kelvin_low_selects','v8_kelvin_low_selects_m3','v8_kelvin_low_selects_rows','v8_kelvin_low_ports','v8_kelvin_low_ports_deep','v8_kelvin_low_ports_loads','v8_kelvin_low_ports_shunts','v8_kelvin_low_ports_loads_shunts','v8_kelvin_low_ports_loads_shunts_series','v9_kelvin_low_critical','v10_kelvin_low_critical','v10_kelvin_low_ports_loads_shunts_series'):
        return 'final_drive_'+profile.split('_',1)[0]
    return 'final_drive_v5'


def physical_macro(inputs, mode, spec_path, circuit_profile, folder):
    assert mode in ('physical_compact','physical_wire')
    spec=json.loads(spec_path.read_text())
    assert spec['status']=='PASS_SOURCE_BOUND_NATIVE_DEVICE_WIRE_COMPOSITION_REQUIRES_TRANSIENT'
    archive=inputs/(folder+'.tar.gz')
    fetch(spec['receipt']['url'],spec['receipt']['sha256'],archive)
    assert archive.stat().st_size==spec['receipt']['bytes']
    destination=inputs/folder;destination.mkdir()
    with tarfile.open(archive) as packed:
        raw=packed.extractfile('cloud-tx-layout-composition/result.json').read()
        assert hashlib.sha256(raw).hexdigest()==spec['summary_sha256']
        report=json.loads(raw)
        assert report['circuit_profile']==circuit_profile and report['outputs']==spec['outputs']
        if 'variant' in spec:
            assert report['variant']==spec['variant']
        (destination/'result.json').write_bytes(raw)
        for name,digest in spec['outputs'].items():
            assert name in ('mux54-wire01.spice','mux54-compact01.spice')
            data=packed.extractfile('cloud-tx-layout-composition/'+name).read()
            assert hashlib.sha256(data).hexdigest()==digest
            (destination/name).write_bytes(data)
    archive.unlink()
    return destination/('mux54-wire01.spice' if mode=='physical_wire' else 'mux54-compact01.spice')


def physical_prestage_circuit_profile(profile):
    physical_spec_path(profile)  # Validate the explicit source/geometry binding.
    return {'cascade16_kelvin_dense_wide':'cascade16',
            'cascade158_kelvin_supply_direct':'cascade158'}.get(profile,'cascade14')


def physical_prestage(inputs, mode, profile='baseline'):
    return physical_macro(inputs,mode,physical_spec_path(profile),
                          physical_prestage_circuit_profile(profile),'physical-prestage')


def rename_physical_top(text, new_name):
    """Namespace only the verified top, so two physical macros cannot collide."""
    lines=text.splitlines()
    headers=[i for i,line in enumerate(lines) if line.lower().startswith('.subckt ')]
    ends=[i for i,line in enumerate(lines) if line.lower().split()[:1]==['.ends']]
    assert len(headers)==len(ends)==1 and headers[0]<ends[0]
    header=lines[headers[0]].split();old_name=header[1]
    assert lines[ends[0]].split()[1:] in ([],[old_name])
    assert all(line.split()[-1:]!=[old_name] for line in lines[headers[0]+1:ends[0]] if line.strip() and not line.startswith('*'))
    header[1]=new_name
    lines[headers[0]]=' '.join(header);lines[ends[0]]='.ends '+new_name
    return '\n'.join(lines)+'\n'


def native_save_commands(vectors):
    # ngspice command-table limits: save LOTS=1000; wrdata NLOTS=10000.
    # Preserve existing small-capture decks byte-for-byte. Large trees need
    # bounded save commands, without omitting or reordering any observations.
    assert vectors and len(vectors)==len(set(vectors))
    assert len(vectors)+1 <= 10000, 'wrdata argument limit; never truncate capture'
    size=len(vectors) if len(vectors)<=1000 else 128
    return ['save '+' '.join(vectors[i:i+size]) for i in range(0,len(vectors),size)]


def build(inputs, condition, fault='none', clock_bias='ideal', final_drive='baseline', pre_bias='baseline', output_bias='ideal', streams=4, final_override=None, clock_reference='baseline'):
    plan=tree_plan(streams)
    assert clock_reference in CLOCK_REFERENCES
    assert clock_reference == 'baseline' or clock_bias == 'native_res'
    bias_path=CLOCK_REFERENCES[clock_reference]
    clock_feed_path=CLOCK_FEEDS[clock_reference]
    feed_header=next(line.lower().split() for line in clock_feed_path.read_text().splitlines()
                     if line.lower().startswith('.subckt '))
    assert feed_header[2:]==['avdd','cm','sub']
    clock_feed_subckt=feed_header[1]
    assert fault in ('none','swap_pre_a_select','disable_pre_b_bias','swap_leaf_select')
    references=[n['reference'] for n in plan['nodes']]
    assert output_bias in ('ideal','native_res')
    assert pre_bias in PRE_BIAS_MODES
    assert final_drive in ('baseline','double','double_taps','double_taps_guard','double_taps_margin')
    assert clock_bias in ('ideal','native_vbe','native_res')
    bits = sequence()
    c = dict(temperature_c=27, supply_scale=1., core_scale=1., hbt='hbt_typ',
             resistor='res_typ', lv_corner='mos_tt', hv_corner='mos_tt', step_ps=.5)
    c.update(CONDITIONS[condition])
    frontend = inputs / 'frontend'
    final = {'double':FAST_FINAL,'double_taps':TAPPED_FINAL,'double_taps_guard':GUARDED_FINAL,'double_taps_margin':MARGIN_FINAL}.get(final_drive,inputs / 'mux54-compact01.spice')
    if final_override is not None:
        assert final_drive=='double_taps_margin'
        final=final_override
    lines = [f'NSSOC native full {streams}:1 tree, unchanged source-bit oracle']
    for kind, corner, directory in [('HBT', c['hbt'], inputs / 'models'),
        ('RES', c['resistor'], inputs / 'models'), ('MOSlv', c['lv_corner'], frontend / 'models'),
        ('MOShv', c['hv_corner'], frontend / 'models')]:
        lines.append(f'.lib "{directory / ("corner" + kind + ".lib")}" {corner}')
    lines += [f'.include "{p}"' for p in (PRE, FRONT, TX, final, frontend / 'buf16.inc')]
    if pre_bias=='native_res':
        lines.append(f'.include "{PRE_FEED}"')
    if clock_bias!='ideal':
        lines.append(f'.include "{bias_path}"')
    if clock_bias=='native_res':
        lines.append(f'.include "{clock_feed_path}"')
    if output_bias=='native_res':
        lines.append(f'.include "{OUTPUT_FEEDS}"')
    lines += [f'.temp {c["temperature_c"]}', '.options reltol=1e-4 abstol=1e-12']
    rails = {'avdd': 2.5*c['supply_scale'], 'tvdd': 1.8*c['supply_scale'], 'dvdd': 1.2*c['core_scale']}
    lines += [f'V{name} {name} 0 PWL(0 0 1n {v:.12g})' for name, v in rails.items()]
    hbt, mos = {}, {}
    for bank in range(streams):
        for suffix, invert in [('p', True), ('n', False)]:
            name = f'd{bank}{suffix}'
            source = name + '0'
            gate_pwl = pwl(bits[bank::streams], .6*c['core_scale'], .6*c['core_scale'],
                           streams*UI, START + (bank-plan['launch_offset'])*UI, invert)
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
    stages=[]
    pre_formal=next(line.lower().split()[2:] for line in PRE.read_text().splitlines() if line.lower().startswith('.subckt '))
    required={'ap','an','bp','bn','sp','sn','op','on','avdd','avss','sub','iref'}
    assert len(pre_formal)==len(set(pre_formal)) and set(pre_formal) in (required,required|{'wire_cref'})
    for index,node in enumerate(plan['nodes']):
        a,b=node['inputs']
        public=dict(ap=a+'p',an=a+'n',bp=b+'p',bn=b+'n',sp=node['clock']+'p',sn=node['clock']+'n',
                    op=node['label']+'p',on=node['label']+'n',avdd='avdd',avss='0',sub='0',iref=node['reference'],wire_cref='0')
        if (fault=='swap_pre_a_select' and index==0) or (fault=='swap_leaf_select' and index==len(plan['nodes'])-1):
            public['sp'],public['sn']=public['sn'],public['sp']
        ports=[public[name] for name in pre_formal]
        stages.append((PRE,'xpre'+node['label'],ports))
    if fault == 'swap_leaf_select':
        # Corrupt an actual deepest-stage selector; source bits/clock phase and
        # output oracle remain untouched. In32:1 this is the15/31 leaf pair.
        assert all(name.startswith('d') for name in plan['nodes'][-1]['inputs'])
    formal = next(line.lower().split() for line in final.read_text().splitlines() if line.lower().startswith('.subckt '))
    assert len(formal[2:])==len(set(formal[2:])) and set(formal[2:]) in (required,required|{'wire_cref'})
    public = dict(ap='ap',an='an',bp='bp',bn='bn',sp='sp',sn='sn',op='mp',on='mn',
                  avdd='avdd',avss='0',sub='0',iref='mr',wire_cref='0')
    stages += [(final, 'xmux', [public[p] for p in formal[2:]]),
               (TX, 'xtx', ['mp','mn','op','on','tvdd','0','0','tr'])]
    for path, instance, ports in stages:
        name, found = bind_devices(path, instance, ports, {'npn13g2'})
        assert len(found) == (4 if instance == 'xtx' else 19)
        hbt.update(found)
        lines.append(instance+' '+' '.join(ports)+' '+name)
    assert len(hbt) == 19*(streams-1)+4 and len(mos) == 16*streams
    clock_refs=[]
    for group in range((len(plan['clocks'])+2)//3):
        suffix='' if group==0 else f'_g{group}'
        clock_refs.append(dict(node='clkbias'+suffix,feed='clkfeed'+suffix,probe='vclkbias_feed'+suffix))
        if clock_bias=='ideal':
            continue
        ports=[clock_refs[-1]['node'],'0','0']
        subckt,found=bind_devices(bias_path,'xclkbias'+suffix,ports,{'npn13g2'})
        assert len(found)==1
        hbt.update(found)
        lines.append('XCLKBIAS'+suffix+' '+' '.join(ports)+' '+subckt)
        if clock_bias=='native_res':
            lines += [f'Vclkbias_feed{suffix} avdd clkfeed{suffix} 0',
                      f'XCLKFEED{suffix} clkfeed{suffix} clkbias{suffix} 0 {clock_feed_subckt}']
        else:
            lines.append(f'ICLKBIAS{suffix} avdd clkbias{suffix} PWL(0 0 1n .00065)')
    for reference in [*references,'mr']:
        if reference=='mr' and output_bias=='native_res':
            lines += ['Vfinal_feed avdd finalfeed 0',
                      'XFINALFEED finalfeed mr 0 nssoc_tx_final_bias_feed_v1']
            continue
        if pre_bias=='native_res' and reference in references:
            # Zero-volt source is only a current probe, not a bias generator.
            lines.append(f'Vprebias_{reference} avdd prefeed_{reference} 0')
            if not (fault=='disable_pre_b_bias' and reference=='rb'):
                lines.append(f'XPREBIAS_{reference} prefeed_{reference} {reference} 0 nssoc_tx_pre_bias_res_v1')
            continue
        bias = 0 if fault == 'disable_pre_b_bias' and reference == 'rb' else .0005
        if reference in references and not (fault=='disable_pre_b_bias' and reference=='rb'):
            bias=PRE_BIASES[pre_bias]
        if reference=='mr' and final_drive in ('double','double_taps','double_taps_guard','double_taps_margin'):
            bias=.001
        lines.append(f'I{reference} avdd {reference} PWL(0 0 1n {bias})')
    if output_bias=='native_res':
        lines += ['Vtx_feed tvdd txfeed 0','XTXFEED txfeed tr 0 nssoc_tx_output_bias_feed_v1']
    else:
        lines.append('ITX tvdd tr PWL(0 0 1n .0015)')
    for index,clock in enumerate(plan['clocks']):
        name,origin,period=clock['name'],clock['origin'],clock['period']
        clock['reference']=clock_refs[index//3]['node']
        for suffix,invert in [('p',False),('n',True)]:
            key=name+suffix
            stimulus=pwl([int(i%2==0) for i in range(BITS)],1.23 if clock_bias=='ideal' else 0,.08,period,origin,invert)
            reference='0' if clock_bias=='ideal' else clock['reference']
            lines += [f'V{key} {key}0 {reference} '+stimulus,f'R{key} {key}0 {key} 25']
    lines += ['RLOAD op on 100','COP op 0 100f','CON on 0 100f']
    nodes = ({n for row in [*hbt.values(), *mos.values()] for n in row['terminals']} | set(rails)) - {'0'}
    # Extracted metal can separate every public pin from its HBT terminal.
    # Save real interface voltages explicitly, not just intrinsic device nodes.
    nodes.update(node for _,_,ports in stages for node in ports if node!='0')
    nodes.update(f'd{i}{suffix}0' for i in range(streams) for suffix in ('p','n'))
    vectors = ['v('+n+')' for n in sorted(nodes)] + ['i(v'+n+')' for n in rails]
    if pre_bias=='native_res':
        vectors += [f'i(vprebias_{reference})' for reference in references]
        vectors += [f'v(prefeed_{reference})' for reference in references]
    if clock_bias=='native_res':
        vectors += [vector for ref in clock_refs for vector in ('i('+ref['probe']+')','v('+ref['feed']+')')]
    if output_bias=='native_res':
        vectors += ['i(vfinal_feed)','v(finalfeed)','i(vtx_feed)','v(txfeed)']
    vectors += ['@q.'+n+'.qnpn13g2[ic]' for n in hbt]
    assert len(vectors) == len(set(vectors))
    lines += ['.control', f'pre_osdi {inputs / "r3_cmc.osdi"}',
              f'pre_osdi {frontend / "psp103.osdi"}', f'pre_osdi {frontend / "psp103_nqs.osdi"}',
              'set wr_singlescale', 'set wr_vecnames', 'set numdgt=16', *native_save_commands(vectors)]
    for name in hbt:
        device = 'q.' + name + '.qnpn13g2'
        lines += [f'alter @{device}[off] = 1', 'echo NSSOC_NATIVE_FLAG_BEGIN '+device,
                  'show '+device+' : off', 'echo NSSOC_NATIVE_FLAG_END']
    lines += ['op','wrdata op.dat '+' '.join(vectors),
              f'tran {c["step_ps"]*1e-12:.14g} {STOP:.14g} 0 {c["step_ps"]*1e-12:.14g}',
              'wrdata wave.dat '+' '.join(vectors), 'quit','.endc','.end']
    return '\n'.join(lines)+'\n', dict(condition=c, fault=fault, streams=streams, tree_plan=plan, references=references, clock_refs=clock_refs, clock_bias=clock_bias, clock_reference=clock_reference, clock_reference_sha256=sha(bias_path), clock_feed_sha256=sha(clock_feed_path), clock_feed_subckt=clock_feed_subckt, final_drive=final_drive, pre_bias=pre_bias, output_bias=output_bias, bits=bits, hbt=hbt, mos=mos,
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
    bias_current={}
    if contract.get('output_bias')=='native_res':
        for label,node,rail,probe in [('final_feed','finalfeed','avdd','vfinal_feed'),('tx_feed','txfeed','tvdd','vtx_feed')]:
            assert np.max(np.abs(volt(node)-volt(rail))) < 1e-12
            current=values[f'i({probe})'][active]
            bias_current[label]=dict(minimum=float(current.min()),median=float(np.median(current)),maximum=float(current.max()))
    if contract.get('clock_bias')=='native_res':
        for ref in contract.get('clock_refs',[dict(node='clkbias',feed='clkfeed',probe='vclkbias_feed')]):
            assert np.max(np.abs(volt(ref['feed'])-volt('avdd'))) < 1e-12
            current=values['i('+ref['probe']+')'][active]
            bias_current[ref['node']]=dict(minimum=float(current.min()),median=float(np.median(current)),maximum=float(current.max()))
    if contract.get('pre_bias')=='native_res':
        for reference in contract.get('references',['ra','rb']):
            assert np.max(np.abs(volt('prefeed_'+reference)-volt('avdd'))) < 1e-12
            current=values[f'i(vprebias_{reference})'][active]
            bias_current[reference]=dict(minimum=float(current.min()),median=float(np.median(current)),maximum=float(current.max()))
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
            prefix = ('a' if i%2==0 else 'b') if stage=='final' else (f'd{i%contract.get("streams",4)}' if stage=='cmos' else f'p{stage}_{i%stage}')
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
    stride=4
    while stride<contract.get('streams',4):
        interfaces['level_'+str(stride)]=interface(stride)
        stride*=2
    clocks={name:[float(((volt(name+'p')+volt(name+'n'))/2)[active].min()),float(((volt(name+'p')+volt(name+'n'))/2)[active].max())] for name in [c['name'] for c in contract.get('tree_plan',dict(clocks=[dict(name=n) for n in ('sa','sb','s')]))['clocks']]}
    return dict(native_bias_current_a=bias_current, prestage_native_bias_current_a={k:v for k,v in bias_current.items() if k in contract.get('references',['ra','rb'])},clock_common_mode_range_v=clocks,zero_source_op=True,rows=len(t),coverage_s=[float(t[0]),float(t[-1])],
        signals=signal,hbt_devices=devices,mos_devices=mos,interfaces=interfaces,
        failed_hbts={n:r for n,r in devices.items() if not r['passed']},
        failed_mos={n:r for n,r in mos.items() if not r['passed']},
        all_engineering_gates_passed=signal['passed'] and all(r['passed'] for r in interfaces.values()) and
                                   all(r['passed'] for r in [*devices.values(),*mos.values()]))


def main():
    global PRE, FRONT
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--streams',type=int,choices=(4,8,16,32),default=4)
    parser.add_argument('--condition',choices=tuple(CONDITIONS),default='nominal')
    parser.add_argument('--fault',choices=('none','swap_pre_a_select','disable_pre_b_bias','swap_leaf_select'),default='none')
    parser.add_argument('--prestage',choices=('divider9','divider14','physical_compact','physical_wire'),default='divider9')
    parser.add_argument('--physical-final-profile',choices=('power_trunks','interleaved','kelvin_return','kelvin_short','kelvin_short_vias','kelvin_dense','kelvin_dense_wide','kelvin_signal_trunks','kelvin_m3_10','v6_kelvin_dense_wide','v7_kelvin_dense_wide','v8_kelvin_dense_wide','v8_kelvin_tail_paths','v8_kelvin_local_tail','v8_kelvin_local_return','v8_kelvin_local_supply','v8_kelvin_local_internal','v8_kelvin_compact_internal','v8_kelvin_low_internal','v8_kelvin_low_critical','v8_kelvin_low_selects','v8_kelvin_low_selects_m3','v8_kelvin_low_selects_rows','v8_kelvin_low_ports','v8_kelvin_low_ports_deep','v8_kelvin_low_ports_loads','v8_kelvin_low_ports_shunts','v8_kelvin_low_ports_loads_shunts','v8_kelvin_low_ports_loads_shunts_series','v9_kelvin_low_critical','v10_kelvin_low_critical','v10_kelvin_low_ports_loads_shunts_series'),default='power_trunks')
    parser.add_argument('--physical-final',choices=('off','physical_compact','physical_wire'),default='off')
    parser.add_argument('--physical-profile',choices=('baseline','wide_access','supply_access','power_trunks','power_trunks_vias','kelvin_dense_wide','kelvin_supply_feed','kelvin_supply_direct','cascade16_kelvin_dense_wide','cascade158_kelvin_supply_direct'),default='baseline')
    parser.add_argument('--frontend',choices=('direct','damped','damped_strong'),default='direct')
    parser.add_argument('--clock-bias',choices=('ideal','native_vbe','native_res'),default='ideal')
    parser.add_argument('--clock-reference',choices=tuple(CLOCK_REFERENCES),default='baseline')
    parser.add_argument('--final-drive',choices=('baseline','double','double_taps','double_taps_guard','double_taps_margin'),default='baseline')
    parser.add_argument('--pre-bias',choices=PRE_BIAS_MODES,default='baseline')
    parser.add_argument('--output-bias',choices=('ideal','native_res'),default='ideal')
    parser.add_argument('--diagnostic-final-r', choices=('actual','all','supply','return','inputs','internal','bias','outputs'), default='actual')
    args=parser.parse_args()
    if args.diagnostic_final_r != 'actual':
        assert args.streams == 4 and args.condition == 'nominal' and args.fault == 'none'
        assert args.prestage == args.physical_final == 'physical_wire'
        assert args.physical_profile == 'power_trunks_vias' and args.physical_final_profile == 'kelvin_dense_wide'
    assert args.physical_profile=='baseline' or args.prestage.startswith('physical_')
    assert args.physical_final_profile=='power_trunks' or args.physical_final!='off'
    if args.prestage=='divider14':
        PRE=ROOT/'hw/soc/analog/pcie/tx_mux2_hbt_cascade_v2.spice'
    if args.frontend=='damped':
        FRONT=ROOT/'hw/soc/analog/pcie/tx_cmos_hv_resistive_input_v6.inc'
    if args.frontend=='damped_strong':
        FRONT=ROOT/'hw/soc/analog/pcie/tx_cmos_hv_resistive_input_v7.inc'
    out=ROOT/'cloud-tx-mux4';out.mkdir(exist_ok=False)
    inputs=out/'inputs';inputs.mkdir()
    run=out/'native';run.mkdir()
    result=dict(status='RUNNING',streams=args.streams,condition=args.condition,fault=args.fault,prestage=args.prestage,frontend=args.frontend,clock_bias=args.clock_bias,clock_reference=args.clock_reference,final_drive=args.final_drive,pre_bias=args.pre_bias,accepted=False,
        scope='Actual selectable4/8/16/32:1 transistor tree. Every actual HBT/MOS is bound and screened. Native clock common-mode references each drive at most three actual selector pairs. Differential clock phases remain external ideal sources; output_bias=native_res replaces final/TX reference currents with native resistor feeds. pre_bias=native_res replaces all prestage ideal currents; clock_bias=native_res also replaces the clock-reference ideal current with a real loaded resistor feed. Each input is8Gb/s divided by stream count; final8GT/s256-bit original oracle unchanged. Clock modulation is still externally imposed. No PLL/CDR, physical tree layout/PEX, ESD, jitter/BER or fullPHY acceptance.')
    try:
        prepare_inputs(inputs)
        if args.prestage.startswith('physical_'):
            assert args.final_drive in ('double_taps_guard','double_taps_margin')
            PRE=physical_prestage(inputs,args.prestage,args.physical_profile)
            physical_spec=physical_spec_path(args.physical_profile)
            counts=json.loads(physical_spec.read_text())['counts']
            result['physical_prestage_scope']=dict(mode=args.prestage,profile=args.physical_profile,instances=args.streams-2,
                circuit_profile=physical_prestage_circuit_profile(args.physical_profile),
                native_devices_per_instance=counts['devices'],substrate_contacts_per_instance=27,
                metal_resistors_per_instance=counts['R'] if args.prestage=='physical_wire' else 0,
                metal_capacitors_per_instance=counts['C'] if args.prestage=='physical_wire' else 0,
                source=str(physical_spec.relative_to(ROOT)),source_sha256=sha(physical_spec),
                intermacro_connections_ideal=True,assembled_tree_gds=False,
                qualified_substrate_resistance=False,qualified_rf_distribution=False)
        final_override=None
        if args.physical_final!='off':
            assert args.final_drive=='double_taps_margin'
            final_spec=physical_final_spec_path(args.physical_final_profile)
            final_circuit=physical_final_circuit_profile(args.physical_final_profile)
            original=physical_macro(inputs,args.physical_final,final_spec,final_circuit,'physical-final')
            final_override=original.with_name('namespaced-final.spice')
            final_text = original.read_text()
            if args.diagnostic_final_r != 'actual':
                from analyze_cloud_metal_resistance import reduce_conductor_class
                final_text, mutation = reduce_conductor_class(
                    original.with_name('mux54-compact01.spice').read_text(),
                    final_text, args.diagnostic_final_r)
                result['diagnostic_mutation'] = mutation
            final_override.write_text(rename_physical_top(final_text,'nssoc_physical_final_'+final_circuit.rsplit('_',1)[1]))
            counts=json.loads(final_spec.read_text())['counts']
            result['physical_final_scope']=dict(mode=args.physical_final,profile=args.physical_final_profile,circuit_profile=final_circuit,instances=1,
                source=str(final_spec.relative_to(ROOT)),source_sha256=sha(final_spec),
                original_model_sha256=sha(original),namespaced_model_sha256=sha(final_override),
                native_devices=counts['devices'],substrate_contacts=27,
                metal_resistors=counts['R'] if args.physical_final=='physical_wire' else 0,
                metal_capacitors=counts['C'] if args.physical_final=='physical_wire' else 0,
                intermacro_connections_ideal=True,assembled_tree_gds=False,
                qualified_substrate_resistance=False,qualified_rf_distribution=False)
        result['output_bias']=args.output_bias
        deck,contract=build(inputs,args.condition,args.fault,args.clock_bias,args.final_drive,args.pre_bias,args.output_bias,args.streams,final_override,clock_reference=args.clock_reference)

        (run/'bench.cir').write_text(deck)
        (run/'contract.json').write_text(json.dumps(contract,indent=2)+'\n')
        (run/'spinit').write_text('set num_threads=1\n')
        paths=[PRE,FRONT,TX,BIAS,CLOCK_REFERENCES[args.clock_reference],FAST_FINAL,TAPPED_FINAL,GUARDED_FINAL,MARGIN_FINAL,PRE_FEED,CLOCK_FEEDS[args.clock_reference],OUTPUT_FEEDS,Path(__file__),ROOT/'scripts/cloud_tx_data_driver.py',
               ROOT/'scripts/run_cloud_tx_operating_point.py',ROOT/'scripts/analyze_cloud_metal_resistance.py',Path(os.environ['CLOUD_NGSPICE']),
               *[p for p in inputs.rglob('*') if p.is_file()],run/'bench.cir',run/'contract.json',run/'spinit']
        result['inputs']={str(p):sha(p) for p in paths}
        def limits():
            # Larger physical trees exceeded the old four-GiB process cap.
            # Hosted public Linux runners provide sixteen GiB; retain headroom.
            resource.setrlimit(resource.RLIMIT_AS,((12 if args.streams==32 else 8 if args.streams==8 else 4)*1024**3,)*2)
            resource.setrlimit(resource.RLIMIT_FSIZE,((2 if args.streams==4 else 8)*1024**3,)*2)
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
            raise RuntimeError('Native serializer tree capture did not finish')
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
        if args.diagnostic_final_r != 'actual':
            result['diagnostic_screen_passed'] = result['component_screen_passed']
            result['component_screen_passed'] = False
            result['status'] = 'COMPLETE_ARTIFICIAL_R_SENSITIVITY_NOT_PHYSICAL_ACCEPTANCE'
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
