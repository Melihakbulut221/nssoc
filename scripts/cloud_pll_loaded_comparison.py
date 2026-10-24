#!/usr/bin/env python3
# SPDX-FileCopyrightText: 2026 Hasan Melih Akbulut
# SPDX-License-Identifier: Apache-2.0
"""Compare all exact loaded tuning captures, including observed timestep sensitivity."""
import json,os
from pathlib import Path
import numpy as np
import cloud_pll_loaded_tuning as tuning
import compare_cloud_routed_endpoints as reports
from cloud_pll_terminal_diagnosis import crossing_times
from cloud_corrpre_banked_postcts import api,sha
ROOT=Path(__file__).resolve().parents[1]
OUT=ROOT/'cloud-pll-loaded-comparison'
RUN=39032380696
HEAD='6f4b02ea356e0a52394c70694da4b1d3454a6cd5'

def inspect(names,a):
    d={n:a[:,i] for i,n in enumerate(names)};t=d['time']
    signal={}
    # Fixed declared thresholds; no fitted digital threshold or phase oracle.
    for key in ('v(reference)','v(fb)','v(up)','v(down)'):
        y=d[key]
        signal[key]=dict(minimum_v=float(y.min()),maximum_v=float(y.max()),threshold_v=1.25,
            rises_s=crossing_times(t,y,1.25).tolist(),falls_s=crossing_times(t,-y,-1.25).tolist())
    return signal

def main():
    assert os.environ.get('GITHUB_ACTIONS')=='true';OUT.mkdir(exist_ok=False);reports.OUT=OUT
    r=dict(status='RESTORING',source_head=os.environ['GITHUB_SHA'],accepted=False,full_phy_accepted=False,
        acquisition_accepted=False,timestep_convergence_accepted=False,
        scope='Exact full50ns externally clamped C8 native captures: original measurements reproduced, fixed1.25V PFD edge observations and measured control-source current compared. No acquisition, transistor safety, noise/jitter, CDR or timestep-convergence qualification.')
    def save():(OUT/'result.json').write_text(json.dumps(r,indent=2)+'\n')
    save()
    try:
        assert sha(Path(tuning.__file__))=='e0c6bbd8b3803eb64d130084394449eca2f53fc5ba97ae30aecaef73c995aaf7'
        run=api('actions/runs/'+str(RUN));assert run['status']=='completed'and run['conclusion']=='success'and run['head_sha']==HEAD and run['run_attempt']==1
        receipt=json.loads((ROOT/'docs/evidence/pll-loaded-tuning-native-20261017.json').read_text())
        waves={};observations={};r['sources']={}
        for name,pin in receipt['cases'].items():
            dest=OUT/name
            original,proof=reports.restore_report('pll-loaded-tuning-'+name,RUN,pin['summary_sha256'],pin['parts_sha256'],dest,
                ('case/tuning.raw','case/bench.cir','case/native.log','case/op.raw'))
            assert original==pin['report'] and original['source_head']==HEAD and original['sources_unchanged']
            assert original['status']=='COMPLETE_NATIVE_LOADED_TUNING_POINT_NOT_PLL_ACQUISITION_OR_PHY_ACCEPTANCE'
            assert original['parent_sha256']==tuning.PARENT and original['native_off_flags_verified']==102
            assert not original['diagnostics'] and original['actual_stopped_clock_control_rejected']
            names,a,meta=tuning.pll.decode_prefix((dest/'case/tuning.raw').read_bytes())
            assert meta['header_matches_observed']and meta['payload_has_only_complete_rows']
            assert sha(dest/'case/tuning.raw')==original['capture']['sha256']
            target,step=tuning.CASES[name]
            measured=tuning.measure(names,a,target,step);assert measured==original['measurement']
            observations[name]=dict(measurement=measured,pfd_edges=inspect(names,a))
            r['sources'][name]=proof
            if name in ('center','center_half'):waves[name]=(names,a)
            save()
        comparison=[]
        for i in range(4):
            lo,c,hi,half=[observations[k]['measurement']['windows'][i]for k in ('low','center','high','center_half')]
            comparison.append(dict(interval_s=c['interval_s'],
                central_gain_hz_per_v=(hi['frequency_hz']-lo['frequency_hz'])/.02,
                center_half_frequency_difference_ppm=(half['frequency_hz']-c['frequency_hz'])/c['frequency_hz']*1e6,
                center_half_clamp_current_difference_a=half['signals']['i(vtune)']['mean']-c['signals']['i(vtune)']['mean']))
        n,a=waves['center'];m,b=waves['center_half'];ta=a[:,0];tb=b[:,0]
        difference={}
        for key in ('v(clkp)','v(clkn)','v(fb)','v(up)','v(down)','i(vtune)'):
            # Observational pointwise difference, never substitute the resampled
            # arrays for the native gate inputs or original edge measurements.
            delta=np.interp(ta,tb,b[:,m.index(key)])-a[:,n.index(key)]
            ix=ta>=10e-9;tt=ta[ix];dd=delta[ix]
            difference[key]=dict(maximum_absolute_difference=float(np.max(np.abs(dd))),
                time_weighted_absolute_difference=float(np.trapezoid(np.abs(dd),tt)/(tt[-1]-tt[0])))
        (OUT/'native-observations.json').write_text(json.dumps(observations,indent=2)+'\n')
        r.update(status='COMPLETE_EXACT_LOADED_TUNING_COMPARISON_NOT_CONVERGENCE_OR_PLL_ACCEPTANCE',
            original_measurements_reproduced=True,window_comparison=comparison,pointwise_differences=difference,
            pfd_edge_observations={k:v['pfd_edges']for k,v in observations.items()},
            original_acquisition_gates_unchanged=True)
    except BaseException as error:r.update(status='FAIL_OR_ERROR',error=repr(error));raise
    finally:
        r['outputs']={str(p.relative_to(OUT)):sha(p)for p in OUT.rglob('*')if p.is_file()and p!=OUT/'result.json'};save()
if __name__=='__main__':main()
