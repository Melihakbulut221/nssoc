#!/usr/bin/env python3
# SPDX-FileCopyrightText: 2026 Hasan Melih Akbulut
# SPDX-License-Identifier: Apache-2.0
"""Compare source-bound compact and metal-RC captures on GitHub only.

Reports actual device voltages and currents without changing a waveform,
sampling phase, bit oracle or engineering acceptance criterion.
"""
import argparse
import gzip
import hashlib
import json
import os
from pathlib import Path
import shutil
import subprocess
import tarfile
import tempfile

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
START, STOP = 2e-9, 34e-9


def sha(path):
    with path.open('rb') as stream:
        return hashlib.file_digest(stream, 'sha256').hexdigest()


def stats(t, values):
    """Integrate over physical time, not the nonuniform simulator point count."""
    t, values = np.asarray(t), np.asarray(values)
    assert t.ndim == values.ndim == 1 and t.shape == values.shape
    assert np.isfinite(t).all() and np.isfinite(values).all()
    assert np.all(np.diff(t) > 0) and t[0] <= START < STOP <= t[-1]
    inside = (t > START) & (t < STOP)
    at = np.r_[START, t[inside], STOP]
    y = np.r_[np.interp(START, t, values), values[inside], np.interp(STOP, t, values)]
    return dict(minimum=float(y.min()), maximum=float(y.max()),
                time_mean=float(np.trapezoid(y, at) / (STOP - START)))


def source_bits_hash(record):
    candidates=[item['source_bits_sha256'] for item in
                (record.get('signals'),record.get('review',{}).get('signals')) if item is not None]
    assert candidates and len(set(candidates))==1
    return candidates[0]


def read_case(record, directory):
    mode = record['prestage']
    tag = record['summary_url'].split('/download/')[1].split('/')[0]
    release = json.loads(subprocess.check_output([
        'gh', 'api', 'repos/Melihakbulut221/nssoc/releases/tags/' + tag]))
    name = record['summary_url'].rsplit('/', 1)[1].replace('.summary.json', '.tar.gz')
    asset = next(a for a in release['assets'] if a['name'] == name)
    packed = directory / 'source.tar.gz'
    subprocess.run(['curl', '--fail', '--location', '--retry', '4', '--silent',
                    '--show-error', asset['browser_download_url'], '-o', str(packed)], check=True)
    assert packed.stat().st_size == asset['size']
    assert asset['digest'] == 'sha256:' + sha(packed)
    wanted = {f'cloud-tx-mux4/{prefix}{name}': name for prefix, name in (
        ('', 'result.json'), ('native/', 'contract.json'), ('native/', 'wave.dat.gz'))}
    found = set()
    with tarfile.open(packed, 'r|gz') as archive:
        for member in archive:
            if member.name in wanted:
                assert member.isfile() and member.size < 2 * 1024**3 and member.name not in found
                with archive.extractfile(member) as src, (directory / wanted[member.name]).open('xb') as dst:
                    shutil.copyfileobj(src, dst)
                found.add(member.name)
    assert found == set(wanted)
    packed.unlink()
    assert sha(directory / 'result.json') == record['summary_sha256']
    result = json.loads((directory / 'result.json').read_text())
    contract = json.loads((directory / 'contract.json').read_text())
    assert contract['streams'] == 4 and contract['fault'] == 'none'
    for name in ('contract.json', 'wave.dat.gz'):
        assert sha(directory / name) == result['outputs']['native/' + name]
    assert result['raw_wave'] == record['raw_wave']
    assert hashlib.sha256(bytes(contract['bits'])).hexdigest() == source_bits_hash(record)
    raw_hash, size = hashlib.sha256(), 0
    with gzip.open(directory / 'wave.dat.gz', 'rb') as src:
        while block := src.read(1024**2):
            raw_hash.update(block)
            size += len(block)
    assert size == record['raw_wave']['bytes'] and raw_hash.hexdigest() == record['raw_wave']['sha256']
    nodes = {n for row in contract['hbt'].values() for n in row['terminals']} - {'0'}
    nodes |= {'avdd', 'tvdd', 'ap', 'an', 'bp', 'bn', 'ra', 'rb', 'mp', 'mn', 'mr', 'tr', 'sp', 'sn', 'op', 'on'}
    names = ['time'] + ['v(' + n + ')' for n in sorted(nodes)]
    names += ['@q.' + n + '.qnpn13g2[ic]' for n in contract['hbt']]
    names += [v for v in contract['vectors'] if v.startswith('i(v')]
    assert len(names) == len(set(names))
    with gzip.open(directory / 'wave.dat.gz', 'rt') as src:
        header = src.readline().split()
        assert header == ['time', *contract['vectors']]
        data = np.loadtxt(src, usecols=[header.index(n) for n in names])
    assert data.ndim == 2 and data.shape[1] == len(names) and np.isfinite(data).all()
    values = dict(zip(names, data.T, strict=True))
    t = values['time']
    assert t[0] == 0 and abs(t[-1] - STOP) < 1e-18 and np.all(np.diff(t) > 0)
    zero = np.zeros_like(t)
    def v(node):
        return zero if node == '0' else values['v(' + node + ')']
    devices = {}
    for name, row in contract['hbt'].items():
        c, b, e, sub = [v(n) for n in row['terminals']]
        current = values['@q.' + name + '.qnpn13g2[ic]']
        prior = result['review']['hbt_devices'][name]
        assert abs(float((c-e)[t >= START].min()) - prior['min_post_vce_v']) < 1e-9
        devices[name] = dict(terminals=row['terminals'], nx=row['nx'],
            collector_v=stats(t, c), base_v=stats(t, b), emitter_v=stats(t, e),
            vce_v=stats(t, c-e), vbe_v=stats(t, b-e),
            collector_current_a=stats(t, current), passed=prior['passed'])
    from analyze_cloud_tx_tree_wave import transition_table
    transitions=transition_table(t,v('sp')-v('sn'),v('mp')-v('mn'),v('op')-v('on'),contract['bits'])
    return dict(mode=mode, source_archive=dict(url=asset['browser_download_url'],
        sha256=asset['digest'].removeprefix('sha256:'), bytes=asset['size']),
        summary_sha256=record['summary_sha256'], raw_wave=record['raw_wave'],
        original_component_screen_passed=record['component_screen_passed'],
        contract_identity={k: contract[k] for k in ('streams', 'fault', 'bits', 'condition',
            'clock_bias', 'pre_bias', 'output_bias', 'final_drive', 'tree_plan')} |
            {'clock_reference':contract.get('clock_reference','baseline'),
             'clock_reference_sha256':contract.get('clock_reference_sha256'),
             'clock_feed_sha256':contract.get('clock_feed_sha256'),
             'clock_feed_subckt':contract.get('clock_feed_subckt')},
        physical_sources={key:{field:result[key].get(field) for field in ('profile','source','source_sha256')}
                          for key in ('physical_prestage_scope','physical_final_scope') if key in result},
        devices=devices, transitions=transitions,
        public_nodes={n: stats(t, v(n)) for n in sorted(nodes) if '.' not in n},
        feed_current_a={n: stats(t, values[n]) for n in names if n.startswith('i(v')})


def pair(compact, wire):
    assert compact['contract_identity'] == wire['contract_identity']
    assert compact.get('physical_sources') == wire.get('physical_sources')
    assert set(compact['devices']) == set(wire['devices'])
    devices = {}
    for name, first in compact['devices'].items():
        second = wire['devices'][name]
        assert first['nx'] == second['nx']
        devices[name] = dict(compact_terminals=first['terminals'], wire_terminals=second['terminals'],
            wire_minus_compact_time_mean={k: second[k]['time_mean'] - first[k]['time_mean']
                for k in ('collector_v', 'base_v', 'emitter_v', 'vce_v', 'vbe_v', 'collector_current_a')})
    return devices



LOCAL_TAIL_STUDIES = {
    'local_tail_hot': (38402059863, 'kelvin_dense_wide'),
    'cascade16_local_tail_hot': (38402511999, 'cascade16_kelvin_dense_wide'),
}


def local_tail_records(evidence, study):
    run, profile = LOCAL_TAIL_STUDIES[study]
    selected = [r for r in evidence['completed_local_tail_comparison']['cases']
                if r['run'] == run and r['corner'] == 'hot_low']
    assert len(selected) == 2
    assert {r['prestage'] for r in selected} == {'physical_compact', 'physical_wire'}
    for r in selected:
        assert r['streams'] == 4 and r['condition'] == 'hot_low'
        assert r['prestage'] == 'physical_' + r['model']
        assert r['physical_prestage_scope']['profile'] == profile
        assert r['physical_final_scope']['profile'] == 'v8_kelvin_local_tail'
        assert r['physical_prestage_scope']['mode'] == r['prestage']
        assert r['physical_final_scope']['mode'] == r['prestage']
        assert r['raw_wave']['bytes'] > 0 and len(r['raw_wave']['sha256']) == 64
    assert len({source_bits_hash(r) for r in selected}) == 1
    return selected


SUPPLY_FEED_STUDIES = {
    'supply_feed_hot': 'hot_low',
    'supply_feed_cold': 'cold_high',
}


def supply_feed_records(evidence, study):
    corner = SUPPLY_FEED_STUDIES[study]
    selected = [r for r in evidence['combined_supply_feed_loaded_study']['cases']
                if r['corner'] == corner]
    assert len(selected) == 2
    assert {r['prestage'] for r in selected} == {'physical_compact', 'physical_wire'}
    for r in selected:
        assert r['run'] == 38417305677 and r['streams'] == 4
        assert r['condition'] == corner and r['clock_reference'] == 'offset75'
        assert r['prestage'] == 'physical_' + r['model']
        assert r['physical_prestage_scope']['profile'] == 'kelvin_supply_feed'
        assert r['physical_final_scope']['profile'] == 'v8_kelvin_local_supply'
        assert r['physical_prestage_scope']['mode'] == r['prestage']
        assert r['physical_final_scope']['mode'] == r['prestage']
        assert r['raw_wave']['bytes'] > 0 and len(r['raw_wave']['sha256']) == 64
    assert len({source_bits_hash(r) for r in selected}) == 1
    return selected



ROUTING_STUDIES = {
    'v8_shortrows_hot': (38474364222, 'cascade158_kelvin_supply_direct', 'v8_kelvin_low_selects_rows',
                         'pcie-v8-shortrows-loaded-rejection-20261014.json', 'hot_low', 'stiff65'),
    'v8_low_selects_hot': (38454526301, 'cascade158_kelvin_supply_direct', 'v8_kelvin_low_selects',
                          'pcie-final-v8-low-selects-hot-loaded-tree-20261013.json', 'hot_low', 'stiff65'),
    'v9_cascade158_hot': (38449433433, 'cascade158_kelvin_supply_direct', 'v9_kelvin_low_critical',
                         'pcie-final-v9-hot-loaded-tree-20261013.json', 'hot_low', 'stiff65'),
    'local_internal_hot': (38423088377, 'kelvin_supply_feed', 'v8_kelvin_local_internal',
                           'pcie-local-internal-hot-loaded-tree-20261013.json', 'hot_low', 'offset75'),
    'low_critical_hot': (38434462503, 'kelvin_supply_feed', 'v8_kelvin_low_critical',
                         'pcie-low-critical-hot-loaded-tree-20261013.json', 'hot_low', 'offset75'),
    'low_critical_cold': (38434462503, 'kelvin_supply_feed', 'v8_kelvin_low_critical',
                          'pcie-low-critical-cold-loaded-tree-20261013.json', 'cold_high', 'offset75'),
}


def routing_records(evidence, study):
    run, prestage_profile, final_profile, _, corner, clock_reference = ROUTING_STUDIES[study]
    records = evidence['cases']
    assert len(records) == 2
    assert {r['prestage'] for r in records} == {'physical_compact', 'physical_wire'}
    for r in records:
        assert r['run'] == run and r['streams'] == 4
        assert r['condition'] == corner and r['clock_reference'] == clock_reference
        assert r['physical_prestage_scope']['profile'] == prestage_profile
        assert r['physical_final_scope']['profile'] == final_profile
        assert r['physical_prestage_scope']['mode'] == r['prestage']
        assert r['physical_final_scope']['mode'] == r['prestage']
        assert r['raw_wave']['bytes'] > 0 and len(r['raw_wave']['sha256']) == 64
        assert len(r['summary_sha256']) == 64
    assert len({source_bits_hash(r) for r in records}) == 1
    return records


def main():
    if os.environ.get('GITHUB_ACTIONS') != 'true':
        raise RuntimeError('Full native waveform analysis runs only on GitHub')
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--study',choices=('prestage_only','both_power','both_interleaved','both_kelvin','both_dense','v8_nominal','dense_v8_hot',*LOCAL_TAIL_STUDIES,*SUPPLY_FEED_STUDIES,*ROUTING_STUDIES),default='prestage_only')
    args=parser.parse_args()
    evidence_path=ROOT/'docs/evidence'/dict(
        prestage_only='pcie-physical-prestage-tree-20261013.json',
        both_power='pcie-both-physical-macros-loaded-tree-20261013.json',
        both_interleaved='pcie-interleaved-macros-loaded-tree-20261013.json',
        both_kelvin='pcie-kelvin-macros-loaded-tree-20261013.json',
        both_dense='pcie-kelvin-dense-loaded-tree-20261013.json',
        v8_nominal='pcie-v8-nominal-loaded-tree-20261013.json',
        dense_v8_hot='pcie-dense-v8-hot-loaded-tree-20261013.json',
        **{key:value[3] for key,value in ROUTING_STUDIES.items()},
        **{key:'cloud-closure-continuation-20261013.json' for key in (*LOCAL_TAIL_STUDIES,*SUPPLY_FEED_STUDIES)})[args.study]
    out = Path('cloud-physical-tree-diagnosis')
    out.mkdir(exist_ok=False)
    result = dict(status='RUNNING', adopted=False, study=args.study, evidence=str(evidence_path.relative_to(ROOT)), evidence_sha256=sha(evidence_path),
        scope='Read-only full-wave voltage/current comparison. Intermacro connections remain ideal; the source-bound case records identify which macros include actual metal RC. TX driver remains schematic. No new acceptance or RF/substrate extraction qualification.')
    try:
        evidence = json.loads(evidence_path.read_text())
        if args.study in ROUTING_STUDIES:
            records = routing_records(evidence,args.study)
        elif args.study in SUPPLY_FEED_STUDIES:
            records = supply_feed_records(evidence,args.study)
        else:
            records = local_tail_records(evidence,args.study) if args.study in LOCAL_TAIL_STUDIES else evidence['cases']
        cases = {}
        for mode in ('physical_compact', 'physical_wire'):
            record = next(r for r in records if r['streams'] == 4 and r['prestage'] == mode)
            with tempfile.TemporaryDirectory() as tmp:
                cases[mode] = read_case(record, Path(tmp))
            result['cases'] = cases
            (out / 'result.json').write_text(json.dumps(result, indent=2) + '\n')
        result['paired_devices'] = pair(cases['physical_compact'], cases['physical_wire'])
        result['status'] = 'COMPLETE_SOURCE_BOUND_PHYSICAL_TREE_COMPARISON_NOT_ACCEPTANCE'
    except Exception as exc:
        result.update(status='FAIL_DIAGNOSIS', error=repr(exc))
        raise
    finally:
        (out / 'result.json').write_text(json.dumps(result, indent=2) + '\n')


if __name__ == '__main__':
    main()
