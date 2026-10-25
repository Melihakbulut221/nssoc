#!/usr/bin/env python3
# SPDX-FileCopyrightText: 2026 Hasan Melih Akbulut
# SPDX-License-Identifier: Apache-2.0
"""Review the completed native 1us PLL capture without restarting or fitting it."""
import json,os,re
from pathlib import Path
import numpy as np
import compare_cloud_routed_endpoints as reports
import cloud_pll_vbic_acquisition as capture
import run_cloud_pll865_snapshot as pll
from route_cloud_newer_postcts import sha
ROOT=Path(__file__).resolve().parents[1];OUT=ROOT/'cloud-pll-terminal-diagnosis'
def crossing_times(t,y,threshold):
    assert len(t)==len(y) and np.all(np.isfinite(y)) and np.all(np.diff(t)>0)
    k=np.flatnonzero((y[:-1]<=threshold)&(y[1:]>threshold))
    # Linear crossing timestamps describe original bracketing samples only.
    # No waveform resampling, shifting, threshold adaptation or gate changes.
    return t[k]+(threshold-y[k])*(t[k+1]-t[k])/(y[k+1]-y[k])
def controls():
    t=np.array([0.,1.,2.,3.,4.]);y=np.array([0.,2.,0.,2.,0.])
    assert np.array_equal(crossing_times(t,y,1.),[.5,2.5])
    assert len(crossing_times(t,np.zeros(5),1.))==0
    for bt,by in [(t[::-1],y),(t,np.array([0.,2.,np.nan,2.,0.]))]:
        try:crossing_times(bt,by,1.)
        except AssertionError:pass
        else:raise AssertionError('Invalid waveform accepted')
    return dict(known_edges=True,constant_signal_is_zero_edges=True,nonfinite_and_reversed_time_rejected=True)
def main():
    assert os.environ.get('GITHUB_ACTIONS')=='true';OUT.mkdir(exist_ok=False);reports.OUT=OUT
    r=dict(status='RUNNING',source_head=os.environ['GITHUB_SHA'],accepted=False,acquisition_accepted=False,full_phy_accepted=False,no_new_native=True,scope='Immutable completed physical845 native 1us/34-probe capture. Reproduce frozen acquisition gates and diagnose actual sampled voltage ranges and fixed-threshold edges. Selected probes cannot prove full device safety or PVT/x4/PHY acceptance.')
    def save():(OUT/'result.json').write_text(json.dumps(r,indent=2)+'\n')
    save()
    try:
        r['controls']=dict(crossings=controls(),reader=pll.self_test(),acquisition=pll.acquisition_controls())
        selected=('case/actual-acquisition.raw','case/circuit.cir','case/actual-acquisition.cir','case/parent865.spice','case/op.raw','case/boots.log','cumulative-native.log')
        old,proof=reports.restore_report('pll-native-acquisition-continuation',38910378266,'6f8d58ce61d36a2ba9d1a6685c489606fd690f47ec4c5c762ab8d6eb333d0470','214dd0fbc2ff51a0a41c389176adc9a00c8d51b8749320d843d4317bffaae8bc',OUT/'source',selected);r['source']=proof
        assert old['source_head']=='892ebb2be94a654b0ff31b79d87604ff8a21bc1c' and old['stage']=='continuation'
        assert old['status']=='FAIL_OR_ERROR' and old['error']=='AssertionError()'
        assert old['native_exitcode']==0 and not old['diagnostics'] and old['prior_payload_unchanged'] and not old['checkpoint_saved']
        for path in ('scripts/review_pcie_pll_acquisition_v1.py','scripts/run_cloud_pll865_snapshot.py','scripts/cloud_pll_vbic_acquisition.py'):
            assert sha(ROOT/path)==old['method_hashes'][path],('Review method drift',path)
        case=OUT/'source/case';assert (case/'boots.log').read_text().splitlines()==['native-entrypoint']
        body=(case/'circuit.cir').read_text();assert body.count('.tran 3.125e-13 1e-06 0 3.125e-13')==1
        assert len(re.findall(r'(?m)^alter .*\[off\] = 1$',body))==102
        names,values,meta=capture.capture(case/'actual-acquisition.raw',old['preparation']['vectors']);assert meta==old['capture']
        data={n:values[:,i]for i,n in enumerate(names)};independent=pll.acquisition_analyzer()(data)
        assert independent==old['independent_acquisition'];assert not independent['passed']
        r.update(capture=meta,original_acquisition_reproduced=True,independent_acquisition=independent,native_simulation_completed=True,acquisition_failed=True,original_controller_report_failed=True)
        edges=np.asarray(independent['feedback_edges_s']);assert np.all(np.isfinite(edges)) and np.all(np.diff(edges)>0)
        if len(edges)>2:r['cycle_diagnosis']=pll.acquisition_cycle_diagnosis(data,independent)
        else:r['cycle_diagnosis']=dict(status='INSUFFICIENT_FEEDBACK_EDGES',feedback_edge_count=len(edges),cycles=[],reason='No invented cycles or frequency; original acquisition failure remains false.')
        t=data['time'];windows=[(0.,1e-6),(0.,10e-9),(10e-9,50e-9),(50e-9,100e-9),(100e-9,200e-9),(800e-9,900e-9),(900e-9,1e-6)]
        traces={n:v for n,v in data.items()if n!='time'}
        traces['differential_clock']=data['v(clkp)']-data['v(clkn)']
        traces['differential_q']=data['v(qp)']-data['v(qn)']
        traces['differential_q2']=data['v(xloop.qp2)']-data['v(xloop.qn2)']
        diagnostics={}
        for n,y in traces.items():
            threshold=0. if n.startswith('differential_')else 1.25
            ce=crossing_times(t,y,threshold);rows=[]
            for lo,hi in windows:
                ix=np.flatnonzero((t>=lo)&(t<=hi));assert len(ix)>1
                a,b=ix[0],ix[-1];tw=t[a:b+1];yw=y[a:b+1];es=ce[(ce>=lo)&(ce<hi)]
                rows.append(dict(interval_s=[lo,hi],actual_sample_interval_s=[float(tw[0]),float(tw[-1])],sample_count=len(ix),minimum_v=float(yw.min()),maximum_v=float(yw.max()),start_v=float(yw[0]),end_v=float(yw[-1]),time_mean_v=float(np.trapezoid(yw,tw)/(tw[-1]-tw[0])),rising_edge_count=len(es),first_edge_s=float(es[0])if len(es)else None,last_edge_s=float(es[-1])if len(es)else None,mean_edge_frequency_hz=float((len(es)-1)/(es[-1]-es[0]))if len(es)>1 else None))
            diagnostics[n]=dict(threshold_v=threshold,scope='Fixed diagnostic threshold, not acquisition acceptance or adaptive level recovery.',windows=rows)
        r['signals']=diagnostics
        r['bound_source_netlists']={p:(case/p).read_text()for p in ['parent865.spice','circuit.cir']}
        assert all(sha(OUT/'source'/p)==old['outputs'][p]for p in selected)
        r.update(status='COMPLETE_EXACT_PHYSICAL_PLL_CAPTURE_DIAGNOSIS_ACQUISITION_FAILED_NOT_PHY_ACCEPTANCE',source_unchanged=True)
    except BaseException as e:r.update(status='FAIL_OR_ERROR',error=repr(e));raise
    finally:
        r['outputs']={str(p.relative_to(OUT)):sha(p)for p in OUT.rglob('*')if p.is_file()and p!=OUT/'result.json'};save()
if __name__=='__main__':main()
