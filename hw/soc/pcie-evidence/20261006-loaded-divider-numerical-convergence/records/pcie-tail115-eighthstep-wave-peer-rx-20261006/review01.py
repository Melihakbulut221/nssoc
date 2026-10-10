# SPDX-FileCopyrightText: 2026 Hasan Melih Akbulut
# SPDX-License-Identifier: Apache-2.0
"""Independent streaming saved-wave readback, online HBT bounds and fixed anchors."""
import collections
import gzip
import hashlib
import json
import os
from pathlib import Path
import re
import resource
os.sched_setaffinity(0,{2})
resource.setrlimit(resource.RLIMIT_CORE,(0,0))
resource.setrlimit(resource.RLIMIT_AS,(2*1024**3,)*2)
import numpy as np

R=Path('/home/hasanmelih/Documents/ChatGPT/nnsoc');O=Path(__file__).resolve().parent
E=R/'hw/soc/out/pcie-vco-v6-divider-tail115-v1-eighthstep-20261006'
F=R/'sw/tests/fixtures/pcie_clock_div4_v10_tail115_v1_hybrid_v1'
inputs={}
def pin(p):
    p=Path(p)
    with p.open('rb') as f:v=dict(bytes=p.stat().st_size,sha256=hashlib.file_digest(f,'sha256').hexdigest())
    inputs[str(p)]=v;return v

def j(p):pin(p);return json.loads(Path(p).read_text())

comparison=j(E/'step-comparison01.json');policy=j(E/'numerical-policy01.json');numeric=j(E/'numerical-convergence01.json')
assert pin(E/'step-comparison01.json')==dict(bytes=336989,sha256='dfe151383aa5c717e47124b92c32a7feb0599cf20844a1dfe0cd5f4fb37e3598')
assert pin(E/'numerical-policy01.json')==dict(bytes=1391,sha256='0d9594b1c44ca5d10f894cca950bc7a9074ffa990e74e1c778e474d1eced4008')
assert pin(E/'numerical-convergence01.json')==dict(bytes=9611,sha256='4f3debe14000f6620784f8dc0646231700321929ff56227eabedfd9c73b98eef')
composition=j(F/'composition.json');binding=j(F/'source-native-bijection.json')
parent=R/'hw/soc/out/pcie-tail115-quarterstep-wave-peer-rx-20261006/review01.py';pin(parent)
prior_peer=j(parent.with_name('result.json'));assert prior_peer['findings']==[]


def crossings(t,v,level=0.0):
    out=[]
    for row in np.flatnonzero((v[:-1]<level)&(v[1:]>=level)):
        i=int(row);a,b=float(t[i]),float(t[i+1]);va,vb=float(v[i]),float(v[i+1])
        when=a+(b-a)*(level-va)/(vb-va)
        out.append(dict(time_s=when,rows=[i,i+1],times_s=[a,b],volts=[va,vb]))
    return out


def read_wave(label,expected_rows,expected_result,expected_raw):
    N=Path(f'/dev/shm/nssoc-vco-v6-divider-tail115-v1-{label}-06-01')
    assert pin(N/'result.json')==expected_result
    assert pin(N/'wave.raw.gz')==expected_raw
    r=j(N/'result.json')
    assert r['rows']==expected_rows and r['values']==expected_rows*957
    assert r['status']=='PASS_NATIVE_LOADED_FEEDBACK_SCREEN'
    assert r['measurement']['passed'] and all(r['measurement']['checks'].values())
    assert r['safety']['passed'] and len(r['devices'])==455
    assert len(r['safety']['all_device_bounds'])==455 and all(x['passed'] for x in r['safety']['all_device_bounds'])
    assert r['config']['window_s']==[4e-9,34e-9]
    for p in (F/'composition.json',F/'source-native-bijection.json'):
        assert r['inputs'][str(p)]==pin(p)
    rawhash=hashlib.sha256();payloadhash=hashlib.sha256();rawbytes=0
    hbt=[d for d in r['devices'] if d['model']=='npn13g2'];assert len(hbt)==64
    bounds={d['path']:dict(path=d['path'],minimum_settled_vce=float('inf'),maximum_capture_vce=-float('inf'),minimum_row=None,minimum_time_s=None) for d in hbt}
    timing_names=['time','v(qp)','v(qn)','v(clkp)','v(clkn)','v(fb)','v(xchain.xfb.clk)','v(xchain.xfb.f0)','v(xchain.xfb.f1)','v(xchain.xfb.count)']
    kept={k:[] for k in timing_names}
    with gzip.open(N/'wave.raw.gz','rb') as f:
        lines=[]
        while True:
            line=f.readline(65536);assert line and len(line)<65536
            lines.append(line);rawhash.update(line);rawbytes+=len(line)
            assert rawbytes<65536
            if line==b'Binary:\n':break
        header=b''.join(lines)
        assert b'Flags: real\n' in header and int(re.search(rb'No\. Points: (\d+)',header)[1])==0
        n=int(re.search(rb'No\. Variables: (\d+)',header)[1]);assert n==957
        names=[]
        for line in header.split(b'Variables:\n')[1].split(b'Binary:\n')[0].splitlines():
            fields=line.decode('ascii').split();assert len(fields)==3 and int(fields[0])==len(names)
            names.append(fields[1])
        assert len(names)==len(set(names))==n
        ix={name:i for i,name in enumerate(names)}
        assert all(k in ix for k in timing_names)
        last_time=None
        for start in range(0,expected_rows,1024):
            take=min(1024,expected_rows-start);count=take*n*8
            data=f.read(count);assert len(data)==count
            rawhash.update(data);payloadhash.update(data);rawbytes+=len(data)
            a=np.frombuffer(data,dtype='<f8').reshape(take,n)
            assert np.isfinite(a).all()
            t=a[:,ix['time']];assert np.all(np.diff(t)>0)
            if last_time is not None:assert float(t[0])>last_time
            last_time=float(t[-1]);settled=np.flatnonzero((t>=4e-9)&(t<=34e-9))
            for k in timing_names:kept[k].append(a[:,ix[k]].copy())
            for d in hbt:
                c,_,e,_=d['nets'];vce=(a[:,ix['v('+c+')']] if c!='0' else np.zeros(take))-(a[:,ix['v('+e+')']] if e!='0' else np.zeros(take))
                out=bounds[d['path']];out['maximum_capture_vce']=max(out['maximum_capture_vce'],float(vce.max()))
                if len(settled):
                    loc=int(settled[int(np.argmin(vce[settled]))]);v=float(vce[loc])
                    if v<out['minimum_settled_vce']:
                        out.update(minimum_settled_vce=v,minimum_row=start+loc,minimum_time_s=float(t[loc]))
        trailer=f.read();assert trailer==str(expected_rows).encode()
        rawhash.update(trailer);rawbytes+=len(trailer)
    assert rawbytes==r['raw_bytes'] and rawhash.hexdigest()==r['raw_sha256']
    assert payloadhash.hexdigest()==r['payload_sha256']
    col={k:np.concatenate(v) for k,v in kept.items()};t=col['time']
    assert float(t[-1])==34e-9 and len(t)==expected_rows
    saved_bounds={d['path']:d for d in r['safety']['all_device_bounds']}
    for d in bounds.values():
        assert abs(d['minimum_settled_vce']-saved_bounds[d['path']]['min_settled_vce'])<1e-12
        assert abs(d['maximum_capture_vce']-saved_bounds[d['path']]['max_capture_vce'])<1e-12
        assert d['minimum_settled_vce']>=.4
    records={x['native_id']:x for x in composition['records']};devices={x['native_id']:x for x in binding['devices']}
    sources={x['source_name']:x for x in binding['devices']};actual={x['path']:x for x in r['devices']}
    assert len(records)==len(devices)==len(sources)==91 and set(records)==set(devices)
    bound=[];terms=metal=body=0
    for native_id,record in sorted(records.items()):
        source=devices[native_id];path=f'xchain.xdiv.xd{native_id:04d}';d=actual[path]
        assert record['model'].lower()==d['model']==source['model'].lower()
        assert {k.lower():v for k,v in record['simulator_parameters'].items()}==d['params']
        assert [x['terminal'] for x in record['terminals']]==source['terminal_order']
        assert len(source['source_nets'])==len(record['terminals'])==len(d['nets'])
        expected=[]
        for terminal in record['terminals']:
            node=terminal['node'];terms+=1
            if node=='BODY_SUBSTRATE':expected.append('div_body_substrate');body+=1;assert terminal['anchor'] is None
            else:expected.append('xchain.xdiv.'+node.lower());metal+=1;assert terminal['anchor'] is not None
        assert expected==d['nets'] and all('v('+net+')' in ix for net in expected)
        bound.append(dict(native_id=native_id,source_name=source['source_name'],actual_path=path,model=d['model'],params=d['params'],terminal_count=len(expected)))
    assert (terms,metal,body)==(283,198,85)
    for name,length in [('DIV__XFIRST__XCORE__XBIAS',12.7),('DIV__XSECOND__XBIAS',11.5),('DIV__XDP',8.0),('DIV__XDN',8.0)]:assert sources[name]['source_device']['length_um']==length
    for name in ['DIV__XCP','DIV__XCN']:assert records[sources[name]['native_id']]['simulator_parameters']=={'w':'24.0u','l':'24.0u'}
    all_edges={'vco':crossings(t,col['v(clkp)']-col['v(clkn)']),'cml':crossings(t,col['v(qp)']-col['v(qn)']),'feedback':crossings(t,col['v(fb)'],1.25)}
    for k,node in [('received','clk'),('fast0','f0'),('fast1','f1'),('count','count')]:all_edges[k]=crossings(t,col[f'v(xchain.xfb.{node})'],.6)
    edges={k:[e for e in v if 4e-9<=e['time_s']<34e-9] for k,v in all_edges.items()}
    times={k:[e['time_s'] for e in v] for k,v in edges.items()}
    for k in ('cml','feedback','received','fast0','fast1','count'):assert times[k]==r['measurement']['edge_times'][k]
    bucket=lambda fast,slow:[sum(a<=x<b for x in fast) for a,b in zip(slow[:-1],slow[1:])]
    counts={'native_hbt_div4':bucket(times['vco'],times['cml']),'whole_native_div80':bucket(times['vco'],times['feedback'])}
    assert counts==r['measurement']['actual_vco_period_counts'] and counts=={'native_hbt_div4':[4]*60,'whole_native_div80':[80,80]}
    ratios={fast+'_'+slow:bucket(times[fast],times[slow]) for fast,slow in [('cml','received'),('received','fast0'),('fast0','fast1'),('fast1','count'),('count','feedback'),('received','feedback')]}
    assert ratios==r['measurement']['edge_ratios']
    vt=[e['time_s'] for e in all_edges['vco']]
    before=sum(x<4e-9 for x in vt);assert before==policy['vco_before_window']==30
    first=min(range(len(vt)),key=lambda i:abs(vt[i]-times['cml'][0]));assert first==policy['first_cml_global_vco']==31
    fb_indices=[min(range(len(vt)),key=lambda i:abs(vt[i]-f)) for f in times['feedback']];assert fb_indices==policy['feedback_global_vco']==[86,166,246]
    settled_cml_index=next(i for i,e in enumerate(all_edges['cml']) if e['time_s']>=4e-9)
    previous_cml=all_edges['cml'][settled_cml_index-1]['time_s'];assert previous_cml<4e-9
    mapping=dict(vco_before_window=before,first_cml_nearest_global_vco=first,feedback_nearest_global_vco=fb_indices,previous_cml_s=previous_cml,first_cml_s=times['cml'][0],startup_cml_edges=settled_cml_index)
    assert [len(times[k]) for k in ('vco','cml','feedback')]==[244,61,3]
    assert times['vco']==vt[30:274]
    saved=next(x for x in comparison['captures'] if x['step_s']==r['config']['step_s'])
    assert mapping==saved['initial_mapping']
    for k in ('vco','cml','feedback'):assert times[k]==saved['numerical_edge_times'][k]
    boundaries=[]
    for i,c in enumerate(edges['cml']):
        glob=first+4*i;nearest=min(range(len(vt)),key=lambda k:abs(vt[k]-c['time_s']));assert glob==nearest
        v=all_edges['vco'][glob];phase=(c['time_s']-v['time_s'])*1e12
        old=saved['cml_boundaries'][i]
        assert c==old['cml_edge'] and v==old['nearest_vco_edge']
        assert old['fixed_vco_index']==glob-before and old['nearest_vco_index']==glob-before
        assert phase==old['fixed_phase_ps']==old['nearest_phase_ps']
        boundaries.append(dict(cml_index=i,cml=c,vco=v,absolute_vco_index=glob,phase_ps=phase))
    frequencies={k:(len(times[k])-1)/(times[k][-1]-times[k][0]) for k in ('vco','feedback')}
    for k,v in frequencies.items():assert abs(v-r['measurement'][k+'_frequency_hz'])<1e-3
    output=dict(capture=label,original_native_status=r['status'],rows=expected_rows,columns=n,finite_values=expected_rows*n,raw_bytes=rawbytes,raw_sha256=rawhash.hexdigest(),payload_sha256=payloadhash.hexdigest(),all64_HBT_VCE=list(bounds.values()),minimum_HBT_VCE=min(x['minimum_settled_vce'] for x in bounds.values()),source_native_simulator_binding=dict(devices=91,terminals=terms,metal_terminals=metal,body_terminals=body,records=bound),original_measurement_checks=r['measurement']['checks'],actual_vco_period_counts=counts,all_six_intermediate_ratios=ratios,initial_mapping=mapping,numerical_edge_times={k:times[k] for k in ('vco','cml','feedback')},frequencies_hz=frequencies,fixed_ordinal_advance=4,boundaries=boundaries)
    return output,r

ref_native=Path('/dev/shm/nssoc-vco-v6-divider-tail115-v1-quarterstep-06-01/result.json')
ref_raw=ref_native.with_name('wave.raw.gz')
reference,rr=read_wave('quarterstep',27217,prior_peer['inputs'][str(ref_native)],prior_peer['inputs'][str(ref_raw)])
candidate,cr=read_wave('eighthstep',54417,dict(bytes=426392,sha256='03977b90f4877791934cf74b13274b3476f41ae790307f3c3005481ab6d709ff'),dict(bytes=386828885,sha256='104365fc79169ae95981e8489b1ae29cdb951258f45ae2d7c3a6a9aa9d95a88b'))
assert rr['devices']==cr['devices']
for k in ('fixture','roots','stop_s','window_s','vctrl'):assert rr['config'][k]==cr['config'][k]
assert rr['config']['step_s']==policy['reference_step_s']==1.25e-12 and cr['config']['step_s']==policy['candidate_step_s']==.625e-12
checks={'reference_mapping':True,'reference_native_functional':True,'candidate_mapping':True,'candidate_native_functional':True}
details={}
for k in ('vco','feedback'):
    ppm=abs(candidate['frequencies_hz'][k]/reference['frequencies_hz'][k]-1)*1e6
    details[k+'_frequency_delta_ppm']=ppm;checks[k+'_frequency_100ppm']=ppm<=policy['frequency_limit_ppm']
    assert abs(ppm-numeric['details'][k+'_frequency_delta_ppm'])<1e-6
for k in ('vco','cml','feedback'):
    a,b=reference['numerical_edge_times'][k],candidate['numerical_edge_times'][k]
    assert len(a)==len(b)==policy['edge_counts'][k]
    delta=[(y-x)*1e12 for x,y in zip(a,b,strict=True)]
    assert delta==numeric['details'][k+'_unaligned_delta_ps']
    details[k+'_unaligned_delta_ps']=delta
    checks[k+'_edge_census']=True;checks[k+'_max_unaligned_phase_50ps']=max(map(abs,delta))<=policy['phase_limit_ps']
assert checks==numeric['checks']
assert [k for k,v in checks.items() if not v]==['vco_frequency_100ppm','feedback_frequency_100ppm']
assert numeric['status']=='FAIL_FINITE_OPEN_LOOP_NUMERICAL_SCREEN'
pin(Path(__file__))
for p,q in list(inputs.items()):assert pin(p)==q
record=dict(status='PASS_INDEPENDENT_SAVED_TAIL115_EIGHTHSTEP_STREAMING_RECOUNT_NUMERICAL_FAIL_RETAINED',findings=[],inputs=inputs,reference=reference,candidate=candidate,original_native_acceptance_changed=False,numerical=dict(status=numeric['status'],checks=checks,details=details,maximum_unaligned_phase_ps={k:max(map(abs,details[k+'_unaligned_delta_ps'])) for k in ('vco','cml','feedback')},frequency_threshold_ppm=100,phase_threshold_ps=50,phase_alignment_or_shift_search=False),maximum_resident_kib=resource.getrusage(resource.RUSAGE_SELF).ru_maxrss,scope='Independent bounded1024-row streaming read of both complete raw captures; all78,123,738 finitevalues/fullraw/payload/terminal hashes,64HBT bounds for each, exact91device/283terminal simulator binding, every reported interval/ratio and all predeclared absolute ordinal anchors. Original455 electrical screens outside the independently recomputed HBT subset remain saved producer claims. No producer import, native, EDA, controls, publication, plotting or capture/source edits; original finitefunctional PASS and supplementary frequency FAIL both retained.')
with (O/'result.json').open('x') as f:json.dump(record,f,indent=2);f.write('\n')
print(json.dumps(dict(status=record['status'],result=pin(O/'result.json'),finite_values=candidate['finite_values'],minimum_HBT_VCE=candidate['minimum_HBT_VCE'],frequencies_hz=candidate['frequencies_hz'],max_phase_ps=record['numerical']['maximum_unaligned_phase_ps'],numeric_status=numeric['status'],maximum_resident_kib=record['maximum_resident_kib']),indent=2))
