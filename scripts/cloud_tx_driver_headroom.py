#!/usr/bin/env python3
# SPDX-FileCopyrightText: 2026 Hasan Melih Akbulut
# SPDX-License-Identifier: Apache-2.0
"""Replay every original engineering gate and locate actual HBT headroom minima."""
import argparse
import json
import os
import shutil
from pathlib import Path
import numpy as np
import compare_cloud_routed_endpoints as reports
import run_cloud_tx_mux4 as tree
from cloud_tx_stream import read_streamed_wave
from route_cloud_newer_postcts import sha

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / 'cloud-tx-driver-headroom'
WORK = ROOT / 'cloud-tx-driver-headroom-input'
SOURCES = {
    'intrinsic': (38878882117, 'tx-driver-loaded-intrinsic',
        'b68db7ae2195f1b73348ff8c0f64693737c3dc1f76c741ea8a95c5c775abc693',
        '363a9cee990a45720aebaea030ff7b017dd9edce31fd95b5cc313ea11fae67cd'),
    'physical': (38910247036, 'tx-driver-localpins-loaded-wire',
        '0ba488d996b9cd251bf9ec457a22cb78fbe425aa4927f3af6e15c85ee9f0a5f8',
        '76ace5c3a12760d727371b42fb20b1cdcffa1020ca2e4183c91b8df72c522da8'),
    'half_r': (38924911243, 'tx-driver-localpins-sensitivity-wire_half_r',
        'a3a010495682de359ff5207901491856ac35c51cfc96904c1ca0552327100578',
        'a75ac25d63a33ce98574936619d4a01e21473dcb3b8a4e6108a19116a619bce4'),
    'half_c': (38924911243, 'tx-driver-localpins-sensitivity-wire_half_c',
        'cfdc6891f6409fa7107f1c669cfcf84fe34eebe7dcc8e19541ffe816453f1691',
        '6b95487668efd0a31b2e8b12a61d8ac271dbcb8e283aa7c99abbb6bb5e4fd363')
}
BINDING = 'fixtures/assembled-core/hw/soc/out/cloud-tx-tree-assembly/binding96/binding01.json'

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--case', choices=tuple(SOURCES), required=True)
    args = parser.parse_args()
    assert os.environ.get('GITHUB_ACTIONS') == 'true'
    OUT.mkdir()
    WORK.mkdir()
    reports.OUT = WORK
    result = dict(status='RUNNING', source_head=os.environ['GITHUB_SHA'], case=args.case,
        accepted=False, physical_change=False, full_serial_phy_complete=False,
        scope='Read-only replay of original full34ns native capture. Every published output/interface/HBT/MOS gate must reproduce exactly. HBT worst samples locate headroom loss; no altered source, voltage, sampling phase, device limit or acceptance claim.')
    def save():
        (OUT/'result.json').write_text(json.dumps(result, indent=2)+'\n')
    save()
    try:
        run, group, summary, parts = SOURCES[args.case]
        published, proof = reports.restore_report(group, run, summary, parts, WORK/'source',
            ('native/wave.raw','native/contract.json','native/op.dat',BINDING))
        result['source'] = proof
        assert published['review']['zero_source_op'] and not published['diagnostics']
        native = WORK/'source/native'
        contract = json.loads((native/'contract.json').read_text())
        assert len(contract['hbt']) == 62
        repeated = tree.review(native, contract)
        assert repeated == published['review'], 'Original full engineering review did not reproduce'
        result['all_original_engineering_fields_reproduced'] = True
        result['original_component_screen_passed'] = published['component_screen_passed']
        result['original_diagnostic_screen_passed'] = published.get('diagnostic_screen_passed')
        result['review'] = {k: repeated[k] for k in ('rows','coverage_s','signals','interfaces',
            'failed_hbts','failed_mos','all_engineering_gates_passed')}
        t, values, transport = read_streamed_wave(native/'wave.raw', contract['vectors'],
            tree.STOP, contract['condition']['step_ps']*1e-12)
        zero = np.zeros_like(t)
        def voltage(node):
            return zero if node == '0' else values['v('+node+')']
        active = np.flatnonzero(t >= tree.START)
        worst = {}
        for name, row in contract['hbt'].items():
            c, b, e, body = [voltage(n) for n in row['terminals']]
            ce = c - e
            sample = int(active[np.argmin(ce[active])])
            assert float(ce[sample]) == repeated['hbt_devices'][name]['min_post_vce_v']
            bad = active[ce[active] < .4]
            intervals = []
            if len(bad):
                groups = np.split(bad, np.flatnonzero(np.diff(bad)>1)+1)
                intervals = [dict(first_sample=int(g[0]), last_sample=int(g[-1]),
                    first_time_s=float(t[g[0]]), last_time_s=float(t[g[-1]]),
                    minimum_vce_v=float(ce[g].min()), native_samples=len(g)) for g in groups]
            worst[name] = dict(terminals=row['terminals'], emitter_count=row['nx'],
                minimum_vce_v=float(ce[sample]), sample=sample, time_s=float(t[sample]),
                collector_v=float(c[sample]), base_v=float(b[sample]),
                emitter_v=float(e[sample]), body_v=float(body[sample]),
                ic_per_emitter_a=float(values['@q.'+name+'.qnpn13g2[ic]'][sample]/row['nx']),
                below_limit_sample_count=len(bad), below_limit_native_runs=intervals,
                interface_snapshot={n:float(voltage(n)[sample]) for n in
                    ('d0p','d0n','d1p','d1n','d2p','d2n','d3p','d3n','sap','san','sbp','sbn',
                     'sp','sn','mp','mn','avdd','dvdd')})
        result['hbt_worst_samples'] = worst
        result['capture'] = {k:v for k,v in transport.items() if k != 'logical_vector_order'}
        result['native_interval_interpretation'] = 'Contiguous saved samples below0.4V, not fitted crossing times or an interpolated waveform.'
        # The raw reader must reject a contract missing a real current probe.
        corrupt = list(contract['vectors'])
        corrupt.remove(next(v for v in corrupt if v.startswith('@q.')))
        try:
            read_streamed_wave(native/'wave.raw', corrupt, tree.STOP,
                contract['condition']['step_ps']*1e-12)
        except AssertionError:
            result['missing_current_probe_control'] = 'REJECTED'
        else:
            raise AssertionError('Missing native current probe was accepted')
        binding = WORK/'source'/BINDING
        assert sha(binding) == 'f54124fa051b49a32f0c3837ef8f771e6cda3ea9aba18417ba5cc932e856c3b9'
        shutil.copyfile(binding, OUT/'actual-tree-binding.json')
        data = json.loads(binding.read_text())
        result['binding_shape'] = {k:dict(type=type(v).__name__, count=len(v) if isinstance(v,(list,dict)) else None) for k,v in data.items()}
        assert all(sha(WORK/'source'/n) == v['sha256'] for n,v in proof['restore']['selected_files'].items())
        result.update(status='COMPLETE_EXACT_CAPTURE_REPLAY_AND_HBT_MINIMA_NOT_PHY_ACCEPTANCE',
                      source_unchanged=True)
        print(json.dumps(dict(case=args.case, status=result['status'],
            hbt_failures=len(repeated['failed_hbts']),
            minima={n:dict(vce=v['minimum_vce_v'],time_s=v['time_s'],collector_v=v['collector_v'],
                emitter_v=v['emitter_v']) for n,v in worst.items() if n in repeated['failed_hbts']},
            binding_shape=result['binding_shape']),indent=2),flush=True)
    except BaseException as error:
        result.update(status='FAIL_OR_ERROR', error=repr(error))
        raise
    finally:
        result['outputs'] = {str(p.relative_to(OUT)):sha(p) for p in OUT.rglob('*') if p.is_file() and p != OUT/'result.json'}
        save()

if __name__ == '__main__':
    main()
