#!/usr/bin/env python3
# SPDX-FileCopyrightText: 2026 Hasan Melih Akbulut
# SPDX-License-Identifier: Apache-2.0
"""Require real fixed-design loaded screens before the new core wire trajectory."""
import json,os,subprocess
from pathlib import Path
from run_cloud_tx_layout_repair import fetch,sha
ROOT=Path(__file__).resolve().parents[1]
def main():
    assert os.environ.get('GITHUB_ACTIONS')=='true'
    receipt=json.loads((ROOT/'docs/evidence/tx-tree32-return64-screen-pass-20261017.json').read_text())
    out=ROOT/'return64-prerequisites';out.mkdir(exist_ok=False);seen=set()
    run=json.loads(subprocess.check_output(['gh','api','repos/Melihakbulut221/nssoc/actions/runs/39028091844']))
    assert run['status']=='completed'and run['conclusion']=='success'
    assert run['head_sha']=='5838ada791fe7354ebbac9acdbeded62099f8aa0'
    assert run['path']=='.github/workflows/tx-tree32-return64-wave-cloud.yml'
    assert receipt['source_run']==39028091844
    for case in receipt['cases']:
        key=(case['condition'],case['fault']);assert key not in seen;seen.add(key)
        path=out/(case['condition']+'-'+case['fault']+'.json');fetch(case['url'],case['sha256'],path)
        report=json.loads(path.read_text());r=report['review']
        assert report['status']=='COMPLETE_ACTUAL_FULL32_PHYSICAL_NATIVE_WAVEFORM_NOT_PHY_ACCEPTANCE'
        assert report['source_head']==case['source_head']=='5838ada791fe7354ebbac9acdbeded62099f8aa0'
        assert report['mode']=='compact'and report['condition']==case['condition']and report['fault']==case['fault']
        assert report['source_unchanged']and not report['diagnostics']and report['native_off_flags_count']==604
        assert report['placement_pitch']=='tight'and report['variant']=='budget_high3_trim'
        assert report['return_rail']=='wide64'and r['zero_source_op']
        assert report['source']['return_rail']['profile']=='wide64'and report['source']['return_rail']['trunk_and_bus_width_um']==64.
        assert report['core_counts']==dict(devices=1674,R=114909,C=76614)
        assert report['model_sha256']=='ce2b1f68486b000d1574ac202acaac2853b6ce4ea9f123f67ddedc6eebf711c2'
        assert report['source']['source_run']==39027347884
        assert report['source']['sha256']=='e93ebe2716f476b152fdc11ce08aed9382f6ac0e9ff996f26943d501362d1a67'
        assert report['native_binding']==dict(actual_input_legs=124,actual_data_bases=372,hbt_count=604,mos_count=512,public_data_pins=64,all_interface_probes_are_bound_terminals=True)
        assert len(r['hbt_devices'])==604 and len(r['mos_devices'])==512 and not r['failed_hbts']and not r['failed_mos']
        assert report['physical_clock_binding']['clock_variants']==['l5p7']+['l6p25']*10
        assert len(report['physical_clock_binding']['controls'])==44 and all(x['rejected']for x in report['physical_clock_binding']['controls'])
        assert r['signals']['source_bits_sha256']=='5dd4496031f00ffea20c2af8cd828d95a868960129829389125dc5055bdb6825'
        assert r['signals']['samples']==768
        if case['fault']=='none':assert report['electrical_screen_passed']and r['all_engineering_gates_passed']
        else:
            assert report['actual_leaf_fault_rejected_by_original_bits']and not report['electrical_screen_passed']
            assert r['signals']['wrong_sign_samples']==27
            assert all(x['wrong_sign_samples']==9 for x in r['signals']['phases'].values())
        for relative in ('scripts/cloud_tx_tree32_wave.py','scripts/bind_tx_tree32_interfaces.py','scripts/cloud_tx_tree32_clock_adapter.py','scripts/cloud_tx_tree32_firstclock.py','scripts/run_cloud_tx_mux4.py','scripts/cloud_tx_stream.py'):
            matches=[v for k,v in report['protected_inputs'].items()if k.endswith('/'+relative)]
            assert matches==[sha(ROOT/relative)],('Loaded screen method changed',relative)
    assert seen=={('nominal','none'),('hot_low','none'),('cold_high','none'),('nominal','swap_leaf_select')}
    print('PASS_EXACT_RETURN64_COMPACT_PREREQUISITES_NOT_CORE_WIRE_OR_PHY_ACCEPTANCE')
if __name__=='__main__':main()
