#!/usr/bin/env python3
# SPDX-FileCopyrightText: 2026 Hasan Melih Akbulut
# SPDX-License-Identifier: Apache-2.0
"""Reproduce both physical PLL captures and compare fixed, unshifted evidence."""
import gc,json,os,re
from pathlib import Path
import numpy as np
import compare_cloud_routed_endpoints as reports
import cloud_pll_vbic_acquisition as capture
import run_cloud_pll865_snapshot as pll
from cloud_pll_terminal_diagnosis import crossing_times,controls as crossing_controls
from review_cloud_pll_loop import records
from route_cloud_newer_postcts import sha
from cloud_pll_c8_native_cycle_review import observe
from check_pll_c8_half_loop_review_sources import check
ROOT=Path(__file__).resolve().parents[1]
OUT=ROOT/'cloud-pll-c8-half-loop-review'
SOURCES={
 'c8_half':dict(group='pll-c8-half-native-acquisition-initial',run=39078674197,
  head='efdac8be7756e543a0e4ebbde19b2f93a92b3dbd',
  summary='f4dc3f9e0bb63321e6b9fa13755334ddcd0ef97b356dbeb19187b34bd0d9dc36',
  parts='0d91ec2056e66c41649b32b4282dca9ec22a0ec1e25aaf928781a25555a4d0fd')}
SELECTED=('case/actual-acquisition.raw','case/circuit.cir','case/actual-acquisition.cir',
          'case/parent865.spice','case/op.raw','case/boots.log','cumulative-native.log')
METHODS=('scripts/review_pcie_pll_acquisition_v1.py','scripts/run_cloud_pll865_snapshot.py',
         'scripts/cloud_pll_vbic_acquisition.py')

def model_inventory(text):
    rows=records(text);public=rows[0][2:]
    assert len(public)==len(set(public))==18 and 'wire_cref'in public
    devices={};wires={};parent={}
    def root(n):
        parent.setdefault(n,n)
        while parent[n]!=n:parent[n]=parent[parent[n]];n=parent[n]
        return n
    for f in rows[1:-1]:
        if f[0][0].lower()=='x':
            at=next((i for i,v in enumerate(f)if '='in v),len(f))-1
            assert at>=3
            params=dict(p.split('=')for p in f[at+1:]);assert len(params)==len(f[at+1:])
            devices[f[0]]=dict(record=' '.join(f),model=f[at],nodes=f[1:at],parameters=params)
        else:
            assert len(f)==4
            value=float(f[3]);assert np.isfinite(value)and value>0
            wires[f[0]]=dict(record=' '.join(f),kind=f[0][0].upper(),nodes=f[1:3],value=value)
            if f[0][0].lower()=='r':parent[root(f[1])]=root(f[2])
    assert len(devices)==845
    for d in devices.values():
        d['public_ports_by_terminal']=[[p for p in public if root(p)==root(n)]for n in d['nodes']]
    return dict(devices=devices,wires=wires,ports=public,
                scope='Only measured resistor edges collapse for topology description; no resistance scaling or physical acceptance.')

def actual_windows(data):
    t=data['time'];result=[]
    for start in range(0,1000,100):
        lo,hi=start*1e-9,(start+100)*1e-9
        # Last endpoint is the exact original capture endpoint.
        if start==900:hi=1e-6
        ix=np.flatnonzero((t>=lo)&(t<=hi));assert len(ix)>2
        a,b=ix[0],ix[-1];tt=t[a:b+1];row=dict(interval_s=[lo,hi],actual_sample_interval_s=[float(tt[0]),float(tt[-1])],signals={})
        for name in ('v(vctrl)','v(up)','v(down)'):
            y=data[name][a:b+1]
            row['signals'][name]=dict(minimum_v=float(y.min()),maximum_v=float(y.max()),
                mean_v=float(np.trapezoid(y,tt)/(tt[-1]-tt[0])),start_v=float(y[0]),end_v=float(y[-1]))
        for name,y,threshold in [('clock',data['v(clkp)']-data['v(clkn)'],0.),
                                  ('feedback',data['v(fb)'],1.25)]:
            edges=crossing_times(t,y,threshold);e=edges[(edges>=lo)&(edges<hi)]
            row[name]=dict(edges=len(e),frequency_hz=float((len(e)-1)/(e[-1]-e[0]))if len(e)>1 else None,
                threshold_v=threshold,acceptance=False)
        result.append(row)
    return result

def review(label,spec):
    dest=OUT/label
    old,proof=reports.restore_report(spec['group'],spec['run'],spec['summary'],spec['parts'],dest,SELECTED)
    assert old['source_head']==spec['head'] and old['stage']=='initial'
    assert old['status']=='COMPLETE_ACTUAL_PHYSICAL845_ONE_US_NATIVE_CONTINUATION_NOT_PHY_ACCEPTANCE'
    assert old['full_capture'] and not old['original_gate_passed'] and not old['checkpoint_saved']
    assert old['native_exitcode']==0 and not old['diagnostics'] and old['prior_payload_unchanged'] and old['protected_inputs_unchanged']
    for path in METHODS:assert sha(ROOT/path)==old['method_hashes'][path],('Method drift',path)
    case=dest/'case';body=(case/'circuit.cir').read_text()
    assert (case/'boots.log').read_text().splitlines()==['native-entrypoint']
    assert body.count('.tran 1.5625e-13 1e-06 0 1.5625e-13')==1
    assert len(re.findall(r'(?m)^alter .*\[off\] = 1$',body))==102
    assert '.options reltol=1e-4 abstol=1e-12 klu'in body
    names,values,meta=capture.capture(case/'actual-acquisition.raw',old['preparation']['vectors'])
    assert meta==old['capture'] and meta['end_s']==1e-6
    data={n:values[:,i]for i,n in enumerate(names)}
    independent=pll.acquisition_analyzer()(data)
    assert independent==old['independent_acquisition'] and not independent['passed']
    cycles=pll.acquisition_cycle_diagnosis(data,independent)
    assert cycles==old['cycle_diagnosis']
    fixed=[w for w in independent['rolling_windows']if any(abs(w['interval_s'][0]-x)<1e-18 for x in (8e-7,9e-7))]
    assert len(fixed)==2 and [w['passed']for w in fixed]==[False,True]
    inv=model_inventory((case/'parent865.spice').read_text())
    verified={p:sha(dest/p)for p in SELECTED}
    assert all(v==old['outputs'][p]for p,v in verified.items())
    r=dict(source=proof,capture=meta,verified_source_files=verified,
           original_acquisition_reproduced=True,original_cycle_diagnosis_reproduced=True,
           acquisition_accepted=False,full_phy_accepted=False,required_windows=fixed,
           frequency_errors_ppm=[(w['frequency_hz']/1e8-1)*1e6 for w in fixed],
           cycles=cycles,windows=actual_windows(data),model_inventory=inv)
    r['native_cycle_review']=observe(data,cycles,inv,body)
    (OUT/(label+'-review.json')).write_text(json.dumps(r,indent=2)+'\n')
    del data,values;gc.collect()
    # Immutable original release retains every raw byte. Avoid redundant GB copies
    # in this derived report; exact checked source hashes and archive receipt remain.
    (case/'actual-acquisition.raw').unlink()
    return r

def compare(a,b):
    changes={}
    for category in ('devices','wires'):
        left=a['model_inventory'][category];right=b['model_inventory'][category]
        changes[category]=dict(removed={k:left[k]for k in left.keys()-right.keys()},
            added={k:right[k]for k in right.keys()-left.keys()},
            changed={k:dict(before=left[k],after=right[k])for k in left.keys()&right.keys()if left[k]!=right[k]},
            unchanged=sum(left[k]==right[k]for k in left.keys()&right.keys()))
    assert a['model_inventory']['ports']==b['model_inventory']['ports']
    rows=[]
    for x,y in zip(a['required_windows'],b['required_windows']):
        assert x['interval_s']==y['interval_s']
        rows.append(dict(interval_s=x['interval_s'],c9_frequency_error_ppm=(x['frequency_hz']/1e8-1)*1e6,
            c8_frequency_error_ppm=(y['frequency_hz']/1e8-1)*1e6,
            c8_minus_c9_frequency_hz=y['frequency_hz']-x['frequency_hz'],
            c9_phase_span_s=x['phase_span_s'],c8_phase_span_s=y['phase_span_s'],
            both_original_gates_pass=x['passed']and y['passed']))
    pairs=[]
    for x,y in zip(a['cycles']['cycles'],b['cycles']['cycles']):
        assert x['feedback_edge_ordinal']==y['feedback_edge_ordinal']
        pairs.append(dict(ordinal=x['feedback_edge_ordinal'],c9_interval_s=x['interval_s'],c8_interval_s=y['interval_s'],
            c9_clock_count=x['differential_clock_rising_edges'],c8_clock_count=y['differential_clock_rising_edges'],
            c9_feedback_period_s=x['feedback_period_s'],c8_feedback_period_s=y['feedback_period_s'],
            c9_vctrl=x['v(vctrl)'],c8_vctrl=y['v(vctrl)'],
            c9_up=x['v(up)'],c8_up=y['v(up)'],c9_down=x['v(down)'],c8_down=y['v(down)']))
    assert len(pairs)==len(a['cycles']['cycles'])==len(b['cycles']['cycles'])
    return dict(required_windows=rows,cycle_pairs=pairs,exact_model_deltas=changes,
        scope='Unshifted original windows and matching feedback ordinals. UP/DOWN duty is not charge-pump current. Correlation does not isolate capacitor causality; full model deltas retained. No target fit or new simulation.')

def main():
    assert os.environ.get('GITHUB_ACTIONS')=='true'
    check()
    OUT.mkdir(exist_ok=False);reports.OUT=OUT
    r=dict(status='RUNNING',source_head=os.environ['GITHUB_SHA'],no_new_native_simulation=True,
           accepted=False,acquisition_accepted=False,full_phy_accepted=False,qualified_pex=False)
    def save():(OUT/'result.json').write_text(json.dumps(r,indent=2)+'\n')
    save()
    try:
        r['controls']=dict(crossings=crossing_controls(),reader=pll.self_test(),
                           acquisition=pll.acquisition_controls(),cycles=pll.acquisition_cycle_controls())
        r['method_hashes']={p:sha(ROOT/p)for p in (*METHODS,'scripts/cloud_pll_c8_native_cycle_review.py','scripts/cloud_pll_c8_half_loop_review.py')}
        cases={}
        for label,spec in SOURCES.items():
            cases[label]=review(label,spec)
            r[label]={k:cases[label][k]for k in ('source','capture','verified_source_files','original_acquisition_reproduced','original_cycle_diagnosis_reproduced','frequency_errors_ppm')}
            save()
        r['native_cycle_review']=cases['c8_half']['native_cycle_review']
        assert all(sha(ROOT/p)==h for p,h in r['method_hashes'].items())
        check()
        r.update(status='COMPLETE_PINNED_HALF_STEP_PLL_LOOP_REVIEW_ORIGINAL_GATES_REMAIN_FAILED',
                 source_unchanged=True,original_full_captures_retained_in_source_releases=True)
    except BaseException as e:r.update(status='FAIL_OR_ERROR',error=repr(e));raise
    finally:
        r['outputs']={str(p.relative_to(OUT)):sha(p)for p in OUT.rglob('*')if p.is_file()and p!=OUT/'result.json'}
        save()
if __name__=='__main__':main()
