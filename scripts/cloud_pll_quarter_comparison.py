#!/usr/bin/env python3
# SPDX-FileCopyrightText: 2026 Hasan Melih Akbulut
# SPDX-License-Identifier: Apache-2.0
"""Compare three immutable native PLL timestep captures without phase fitting."""
import json,os,re
from pathlib import Path
import numpy as np
import cloud_pll_loaded_tuning as tuning
import cloud_pll_loaded_refinement as refinement
import cloud_pll_startup_phase as startup
import compare_cloud_routed_endpoints as reports
from cloud_pll_terminal_diagnosis import controls
from cloud_corrpre_banked_postcts import api,sha
ROOT=Path(__file__).resolve().parents[1];OUT=ROOT/'cloud-pll-quarter-comparison'
QUARTER_RUN=39035550686
QUARTER_HEAD='e7d90c31abed67e2c746a6f81ba4dd791b12a4a5'
QUARTER_SUMMARY='8b49905de051096b467c6029e27cd7179ee56602eb7fd3b13ae0d2bb7f35ef25'
QUARTER_PARTS='ea4f79f45282af85a82eae96b26b93b93435f6af46fa6dd6ec8c4afc516642a1'

def paired_edges(first,second):
    result={}
    assert set(first)==set(second)
    for key,a in first.items():
        result[key]={}
        for threshold,c in a['edges'].items():
            result[key][threshold]={}
            for edge in ('rising_s','falling_s'):
                x=np.asarray(c[edge]);y=np.asarray(second[key]['edges'][threshold][edge])
                n=min(len(x),len(y));delta=y[:n]-x[:n]
                bad=np.flatnonzero(np.abs(delta)>50e-12)
                result[key][threshold][edge]=dict(first_count=len(x),second_count=len(y),
                    equal_edge_counts=len(x)==len(y),paired_ordinals=n,
                    maximum_absolute_ordinal_difference_s=float(np.max(np.abs(delta)))if n else None,
                    first_over_50ps_ordinal=int(bad[0])if len(bad)else None,
                    first_over_50ps_first_s=float(x[bad[0]])if len(bad)else None,
                    first_over_50ps_second_s=float(y[bad[0]])if len(bad)else None)
    return result

def main():
    assert os.environ.get('GITHUB_ACTIONS')=='true';OUT.mkdir(exist_ok=False);reports.OUT=OUT
    r=dict(status='RESTORING',source_head=os.environ['GITHUB_SHA'],accepted=False,
        acquisition_accepted=False,full_phy_accepted=False,timestep_convergence_accepted=False,
        scope='Exact 50ns clamped physical C8 captures at original/half/quarter steps. Reproduce native measurements and compare every saved voltage edge ordinal without phase fitting. Descriptive evidence only; no closed-loop acquisition, PVT, transistor-safety or numerical-convergence qualification.')
    def save():(OUT/'result.json').write_text(json.dumps(r,indent=2)+'\n')
    save()
    try:
        for module,digest in [(tuning,'e0c6bbd8b3803eb64d130084394449eca2f53fc5ba97ae30aecaef73c995aaf7'),
            (refinement,'c7bd2877a3c831e720be94512a50e10f70d0cf5649bc86dcc485bf973ab30f8a'),
            (startup,'561676ddc84b55bb8d45fc1cebc5bd1e44254664d889f03684edd1a217f13a93')]:
            assert sha(Path(module.__file__))==digest,'Frozen reader changed'
        r['crossing_controls']=controls()
        receipt=json.loads((ROOT/'docs/evidence/pll-loaded-tuning-native-20261017.json').read_text())
        pins={name:dict(run=39032380696,head='6f4b02ea356e0a52394c70694da4b1d3454a6cd5',group='pll-loaded-tuning-'+name,
                summary=receipt['cases'][name]['summary_sha256'],parts=receipt['cases'][name]['parts_sha256'])for name in ('center','center_half')}
        pins['center_quarter']=dict(run=QUARTER_RUN,head=QUARTER_HEAD,group='pll-loaded-refinement-center_quarter',summary=QUARTER_SUMMARY,parts=QUARTER_PARTS)
        waves={};records={};measurements={};benches={};r['sources']={}
        for name,pin in pins.items():
            run=api('actions/runs/'+str(pin['run']));assert run['status']=='completed'and run['conclusion']=='success'and run['head_sha']==pin['head']and run['run_attempt']==1
            dest=OUT/name
            original,proof=reports.restore_report(pin['group'],pin['run'],pin['summary'],pin['parts'],dest,
                ('case/tuning.raw','case/bench.cir','case/native.log','case/op.raw','case/parent865.spice'))
            assert original['status']=='COMPLETE_NATIVE_LOADED_TUNING_POINT_NOT_PLL_ACQUISITION_OR_PHY_ACCEPTANCE'
            assert original['source_head']==pin['head']and original['sources_unchanged']and original['native_off_flags_verified']==102
            assert original['actual_stopped_clock_control_rejected']and not original['diagnostics']
            assert original['parent_sha256']==tuning.PARENT==sha(dest/'case/parent865.spice')
            for path in ('case/tuning.raw','case/bench.cir','case/native.log','case/op.raw','case/parent865.spice'):
                assert sha(dest/path)==original['outputs'][path],path
            module=refinement if name=='center_quarter'else tuning
            target,step=module.CASES[name]
            names,a,meta=tuning.pll.decode_prefix((dest/'case/tuning.raw').read_bytes())
            assert meta['header_matches_observed']and meta['payload_has_only_complete_rows']
            assert sha(dest/'case/tuning.raw')==original['capture']['sha256']
            measured=module.measure(names,a,target,step);assert measured==original['measurement']
            body=(dest/'case/bench.cir').read_text();tran=original['bench_changes']['transient']
            assert body.splitlines().count(tran)==1
            benches[name]=body.replace(tran,'__ONLY_DECLARED_TIMESTEP_DIFFERENCE__')
            waves[name]=(names,a);records[name]=startup.observe(names,a);measurements[name]=measured
            r['sources'][name]=proof;save()
        assert len(set(benches.values()))==1,'Uncontrolled paired bench difference beyond timestep'
        comparisons={}
        for first,second in [('center','center_half'),('center_half','center_quarter')]:
            window=[]
            for a,b in zip(measurements[first]['windows'],measurements[second]['windows'],strict=True):
                assert a['interval_s']==b['interval_s']
                window.append(dict(interval_s=a['interval_s'],first_frequency_hz=a['frequency_hz'],second_frequency_hz=b['frequency_hz'],
                    frequency_difference_ppm=(b['frequency_hz']-a['frequency_hz'])/a['frequency_hz']*1e6,
                    first_mean_clamp_current_a=a['signals']['i(vtune)']['mean'],second_mean_clamp_current_a=b['signals']['i(vtune)']['mean'],
                    mean_clamp_current_difference_a=b['signals']['i(vtune)']['mean']-a['signals']['i(vtune)']['mean']))
            n,a=waves[first];m,b=waves[second];ta=a[:,0];tb=b[:,0];difference={}
            for key in ('v(clkp)','v(clkn)','v(fb)','v(up)','v(down)','i(vtune)'):
                delta=np.interp(ta,tb,b[:,m.index(key)])-a[:,n.index(key)]
                ix=ta>=10e-9;tt=ta[ix];dd=delta[ix]
                difference[key]=dict(maximum_absolute_difference=float(np.max(np.abs(dd))),
                    time_weighted_absolute_difference=float(np.trapezoid(np.abs(dd),tt)/(tt[-1]-tt[0])))
            comparisons[first+'__'+second]=dict(windows=window,edge_ordinals=paired_edges(records[first],records[second]),
                pointwise_differences=difference)
        # Prove ordinal diagnosis exposes an actual dropped edge, rather than
        # silently accepting a shorter matched prefix as converged.
        key='v(xloop.qp2)-v(xloop.qn2)';mutated=json.loads(json.dumps(records['center_quarter']))
        edge=mutated[key]['edges']['0.0']['rising_s'];assert len(edge)>2;edge.pop(1)
        corrupt=paired_edges(records['center_quarter'],mutated)[key]['0.0']['rising_s']
        assert not corrupt['equal_edge_counts']and corrupt['first_over_50ps_ordinal']is not None
        (OUT/'all-edges.json').write_text(json.dumps(records,indent=2)+'\n')
        r.update(status='COMPLETE_NATIVE_THREE_STEP_COMPARISON_NOT_PLL_ACQUISITION_OR_CONVERGENCE_ACCEPTANCE',
            original_measurements_reproduced=True,only_timestep_changed=True,phase_alignment_fitted=False,
            original_acquisition_gates_unchanged=True,actual_dropped_edge_control_detected=True,
            measurements=measurements,comparisons=comparisons,diagnostic_difference_threshold_s=50e-12)
    except BaseException as error:r.update(status='FAIL_OR_ERROR',error=repr(error));raise
    finally:
        r['outputs']={str(p.relative_to(OUT)):sha(p)for p in OUT.rglob('*')if p.is_file()and p!=OUT/'result.json'};save()
if __name__=='__main__':main()
