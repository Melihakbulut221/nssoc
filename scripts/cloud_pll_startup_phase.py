#!/usr/bin/env python3
# SPDX-FileCopyrightText: 2026 Hasan Melih Akbulut
# SPDX-License-Identifier: Apache-2.0
"""Trace existing physical PLL startup phase divergence without changing the bench."""
import json,os
from pathlib import Path
import numpy as np
import compare_cloud_routed_endpoints as reports
import cloud_pll_loaded_tuning as tuning
from cloud_pll_terminal_diagnosis import crossing_times,controls
from cloud_corrpre_banked_postcts import sha,api
ROOT=Path(__file__).resolve().parents[1];OUT=ROOT/'cloud-pll-startup-phase'
SUMMARY='1e4324be4257560a5ede48c502a340bb7446c636bfd24f9c6b691302897520ec';PARTS='1cf49f27f360bbc3144733172ab66102afe733478b0dbc8ff6399f36c894cdc5'

def observe(names,a):
    d={n:a[:,i]for i,n in enumerate(names)};t=d['time'];result={}
    # Both fixed rail thresholds are reported for each saved scalar voltage.
    # This is diagnosis, not automatic logic-level acceptance.
    for key in names:
        if key.startswith('v('):
            y=d[key];result[key]=dict(minimum_v=float(y.min()),maximum_v=float(y.max()),edges={})
            for threshold in (.6,1.25):
                rising=crossing_times(t,y,threshold);falling=crossing_times(t,-y,-threshold)
                result[key]['edges'][str(threshold)]=dict(rising_s=rising.tolist(),falling_s=falling.tolist())
    for p,n in [('v(clkp)','v(clkn)'),('v(qp)','v(qn)'),('v(xloop.qp2)','v(xloop.qn2)'),('v(xloop.bp)','v(xloop.bn)')]:
        assert p in d and n in d
        y=d[p]-d[n];result[p+'-'+n]=dict(minimum_v=float(y.min()),maximum_v=float(y.max()),edges={'0.0':dict(
            rising_s=crossing_times(t,y,0.).tolist(),falling_s=crossing_times(t,-y,0.).tolist())})
    return result

def main():
    assert os.environ.get('GITHUB_ACTIONS')=='true';OUT.mkdir(exist_ok=False);reports.OUT=OUT
    r=dict(status='RUNNING',source_head=os.environ['GITHUB_SHA'],accepted=False,full_phy_accepted=False,
        acquisition_accepted=False,timestep_convergence_accepted=False,
        scope='Read-only all34 saved voltage startup edge diagnosis on exact original50ns center/half captures. Fixed0.6/1.25V scalar and0V differential thresholds, ordinal comparison without phase alignment. No acquisition or physical change.')
    def save():(OUT/'result.json').write_text(json.dumps(r,indent=2)+'\n')
    save()
    try:
        r['crossing_controls']=controls()
        run=api('actions/runs/39035059640');assert run['status']=='completed'and run['conclusion']=='success'and run['head_sha']=='aab36dbbc0acfb513b3111cea9004f1368be190c'
        selected=['native-observations.json']+[case+'/'+name for case in ('center','center_half')for name in ('case/tuning.raw','case/bench.cir')]
        prior,proof=reports.restore_report('pll-loaded-comparison',39035059640,SUMMARY,PARTS,OUT/'source',selected)
        assert prior['original_measurements_reproduced']and prior['original_acquisition_gates_unchanged']
        r['source']=proof;records={}
        observations=json.loads((OUT/'source/native-observations.json').read_text())
        for case in ('center','center_half'):
            folder=OUT/'source'/case/'case';names,a,meta=tuning.pll.decode_prefix((folder/'tuning.raw').read_bytes())
            assert meta['header_matches_observed']and meta['payload_has_only_complete_rows']
            assert tuning.measure(names,a,*tuning.CASES[case])==observations[case]['measurement']
            records[case]=observe(names,a)
            r.setdefault('bench_sources',{})[case]=[l for l in (folder/'bench.cir').read_text().splitlines()if l[:1].upper()in ('V','I')]
        pairs={}
        for key,coarse in records['center'].items():
            half=records['center_half'][key];pairs[key]={}
            for threshold,c in coarse['edges'].items():
                pairs[key][threshold]={}
                for edge in ('rising_s','falling_s'):
                    a=np.array(c[edge]);b=np.array(half['edges'][threshold][edge]);n=min(len(a),len(b));delta=b[:n]-a[:n]
                    bad=np.flatnonzero(np.abs(delta)>50e-12)
                    pairs[key][threshold][edge]=dict(coarse_count=len(a),half_count=len(b),
                        first_coarse_s=float(a[0])if len(a)else None,first_half_s=float(b[0])if len(b)else None,
                        maximum_absolute_ordinal_difference_s=float(np.max(np.abs(delta)))if n else None,
                        first_over_50ps_ordinal=int(bad[0])if len(bad)else None,
                        first_over_50ps_coarse_s=float(a[bad[0]])if len(bad)else None,
                        first_over_50ps_half_s=float(b[bad[0]])if len(bad)else None)
        (OUT/'all-edges.json').write_text(json.dumps(records,indent=2)+'\n')
        r.update(status='COMPLETE_NATIVE_STARTUP_EDGE_DIAGNOSIS_NOT_REPAIR_OR_ACCEPTANCE',edge_comparison=pairs,
            diagnostic_difference_threshold_s=50e-12,phase_alignment_fitted=False,original_measurements_reproduced=True)
    except BaseException as error:r.update(status='FAIL_OR_ERROR',error=repr(error));raise
    finally:
        r['outputs']={str(p.relative_to(OUT)):sha(p)for p in OUT.rglob('*')if p.is_file()and p!=OUT/'result.json'};save()
if __name__=='__main__':main()
