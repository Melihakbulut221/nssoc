# SPDX-FileCopyrightText: 2026 Hasan Melih Akbulut
# SPDX-License-Identifier: Apache-2.0
"""Independent full saved raw/terminal/edge recount, no producer imports."""
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

R=Path('/home/hasanmelih/Documents/ChatGPT/nnsoc')
O=Path(__file__).resolve().parent
N=Path('/dev/shm/nssoc-vco-v6-divider-tail115-v1-quarterstep-06-01')
F=R/'sw/tests/fixtures/pcie_clock_div4_v10_tail115_v1_hybrid_v1'
E=R/'hw/soc/out/pcie-vco-v6-divider-tail115-v1-quarterstep-20261006'


def pin(p):
    p=Path(p)
    with p.open('rb')as f:return dict(bytes=p.stat().st_size,sha256=hashlib.file_digest(f,'sha256').hexdigest())


def j(p):return json.loads(p.read_text())


inputs={str(p):pin(p)for p in [N/'result.json',N/'wave.raw.gz',F/'composition.json',
    F/'source-native-bijection.json',E/'step-comparison01.json',
    E/'compare_saved_steps01.py',R/'hw/soc/out/pcie-bias8-wave-root-20261006/review01.py',Path(__file__)]}
assert inputs[str(N/'result.json')]==dict(bytes=426389,sha256='765615872aa97b2cbd9849139d5870ae9fe69bc341a0478c84e79135e2d05a76')
assert inputs[str(N/'wave.raw.gz')]==dict(bytes=193621526,sha256='3e6061927055fae88f3e12e621d7fd8250bad41e094e44877ee4c09392eecd2e')
r=j(N/'result.json');comparison=j(E/'step-comparison01.json');saved=comparison['captures'][2]
assert saved['step_s']==1.25e-12
diagnosis=dict(counts=saved['bucket_counts'],bad_intervals=saved['bad_bucket_indices'],all_cml_boundaries=[])
for row in saved['cml_boundaries']:
    def adapt(e):
        return dict(time_s=e['time_s'],bracket_rows=e['rows'],bracket_s=e['times_s'],bracket_v=e['volts'],bracket_width_ps=(e['times_s'][1]-e['times_s'][0])*1e12)
    diagnosis['all_cml_boundaries'].append(dict(cml_edge=adapt(row['cml_edge']),nearest_vco_edge=adapt(row['nearest_vco_edge']),fixed_ordinal_vco_index=row['fixed_vco_index'],nearest_vco_index=row['nearest_vco_index'],fixed_ordinal_phase_ps=row['fixed_phase_ps'],nearest_phase_ps=row['nearest_phase_ps']))
assert r['status']=='PASS_NATIVE_LOADED_FEEDBACK_SCREEN' and r['measurement']['passed']is True
assert r['safety']['passed']is True and len(r['devices'])==455
raw=gzip.decompress((N/'wave.raw.gz').read_bytes())
assert len(raw)==r['raw_bytes']==208418035 and hashlib.sha256(raw).hexdigest()==r['raw_sha256']
header,payload=raw.split(b'Binary:\n',1)
assert b'Flags: real\n'in header and int(re.search(rb'No\. Points: (\d+)',header)[1])==0
n=int(re.search(rb'No\. Variables: (\d+)',header)[1]);assert n==957
names=[]
for line in header.split(b'Variables:\n')[1].splitlines():
    fields=line.decode('ascii').split();assert len(fields)==3 and int(fields[0])==len(names)
    names.append(fields[1])
assert len(names)==len(set(names))==n
rows,tail=divmod(len(payload),n*8)
assert rows==r['rows']==27217 and payload[rows*n*8:]==str(rows).encode() and tail==5
binary=payload[:rows*n*8]
assert hashlib.sha256(binary).hexdigest()==r['payload_sha256']
array=np.frombuffer(binary,dtype='<f8').reshape(rows,n)
assert array.size==r['values']==26046669 and np.isfinite(array).all()
col={name:array[:,i]for i,name in enumerate(names)}
t=col['time'];assert np.all(np.diff(t)>0) and float(t[-1])==34e-9
left,right=r['config']['window_s'];assert [left,right]==[4e-9,34e-9]
settled=(t>=left)&(t<=right)

# Bind all91 native records to all283 actual simulator terminal connections,
# including the85 body terminals kept separate from distributed metal.
for p in [F/'composition.json',F/'source-native-bijection.json']:
    assert r['inputs'][str(p)]==pin(p)
composition=j(F/'composition.json');binding=j(F/'source-native-bijection.json')
records={x['native_id']:x for x in composition['records']}
devices={x['native_id']:x for x in binding['devices']}
source_devices={x['source_name']:x for x in binding['devices']}
actual={x['path']:x for x in r['devices']}
assert len(records)==len(devices)==len(source_devices)==91 and set(records)==set(devices)
bound=[];terms=metal=body=0
for native_id,record in sorted(records.items()):
    source=devices[native_id];path=f'xchain.xdiv.xd{native_id:04d}';a=actual[path]
    assert record['model'].lower()==a['model']==source['model'].lower()
    assert {k.lower():v for k,v in record['simulator_parameters'].items()}==a['params']
    assert [x['terminal']for x in record['terminals']]==source['terminal_order']
    assert len(source['source_nets'])==len(record['terminals'])==len(a['nets'])
    expected=[]
    for terminal in record['terminals']:
        node=terminal['node'];terms+=1
        if node=='BODY_SUBSTRATE':
            expected.append('div_body_substrate');body+=1;assert terminal['anchor']is None
        else:
            expected.append('xchain.xdiv.'+node.lower());metal+=1;assert terminal['anchor']is not None
    assert expected==a['nets']
    assert all('v('+net+')'in col for net in expected)
    bound.append(dict(native_id=native_id,source_name=source['source_name'],actual_path=path,
                      model=a['model'],params=a['params'],terminal_count=len(expected)))
assert (terms,metal,body)==(283,198,85)
for name,length in [('DIV__XFIRST__XCORE__XBIAS',12.7),('DIV__XSECOND__XBIAS',11.5),('DIV__XDP',8.0),('DIV__XDN',8.0)]:
    assert source_devices[name]['source_device']['length_um']==length
for name in ['DIV__XCP','DIV__XCN']:
    assert records[source_devices[name]['native_id']]['simulator_parameters']=={'w':'24.0u','l':'24.0u'}

# Recompute every saved HBT VCE minimum from raw voltages, not producer bounds.
hbt=[];saved={x['path']:x for x in r['safety']['all_device_bounds']}
for device in r['devices']:
    if device['model']!='npn13g2':continue
    c,_,e,_=device['nets']
    vce=(col['v('+c+')']if c!='0'else np.zeros(rows))-(col['v('+e+')']if e!='0'else np.zeros(rows))
    index=np.flatnonzero(settled)[int(np.argmin(vce[settled]))]
    minimum=float(vce[index]);maximum=float(vce.max())
    assert abs(minimum-saved[device['path']]['min_settled_vce'])<1e-12
    assert abs(maximum-saved[device['path']]['max_capture_vce'])<1e-12
    assert minimum>=.4
    hbt.append(dict(path=device['path'],minimum_settled_vce=minimum,
                    maximum_capture_vce=maximum,minimum_row=int(index),minimum_time_s=float(t[index])))
assert len(hbt)==64


def crossings(values):
    out=[]
    for i in np.flatnonzero((values[:-1]<0)&(values[1:]>=0)):
        i=int(i);a,b=float(t[i]),float(t[i+1]);va,vb=float(values[i]),float(values[i+1])
        when=a+(b-a)*(0-va)/(vb-va)
        if left<=when<right:
            out.append(dict(time_s=when,bracket_rows=[i,i+1],bracket_s=[a,b],
                            bracket_v=[va,vb],bracket_width_ps=(b-a)*1e12))
    return out


cml=crossings(col['v(qp)']-col['v(qn)'])
vco=crossings(col['v(clkp)']-col['v(clkn)'])
ct=[e['time_s']for e in cml];vt=[e['time_s']for e in vco]
assert ct==r['measurement']['edge_times']['cml'] and len(cml)==61 and len(vco)==244
counts=[sum(a<=v<b for v in vt)for a,b in zip(ct[:-1],ct[1:])]
assert counts==r['measurement']['actual_vco_period_counts']['native_hbt_div4']==diagnosis['counts']
assert collections.Counter(counts)=={4:60}
bad=[i for i,x in enumerate(counts)if x!=4];assert bad==[]==diagnosis['bad_intervals']
first=min(range(len(vt)),key=lambda i:abs(vt[i]-ct[0]))
ordinal=[first+4*i for i in range(len(ct))]
assert ordinal[-1]<len(vco) and all(b-a==4 for a,b in zip(ordinal[:-1],ordinal[1:]))
boundaries=[]
for i,(c,jj)in enumerate(zip(cml,ordinal)):
    nearest=min(range(len(vt)),key=lambda j:abs(vt[j]-c['time_s']))
    assert nearest==jj
    phase=(ct[i]-vt[jj])*1e12
    old=diagnosis['all_cml_boundaries'][i]
    for key in ('time_s','bracket_rows','bracket_s','bracket_v','bracket_width_ps'):
        assert c[key]==old['cml_edge'][key]
        assert vco[jj][key]==old['nearest_vco_edge'][key]
    assert old['fixed_ordinal_vco_index']==jj and old['nearest_vco_index']==nearest
    assert phase==old['fixed_ordinal_phase_ps']==old['nearest_phase_ps']
    boundaries.append(dict(cml_index=i,cml=c,vco=vco[jj],fixed_vco_index=jj,phase_ps=phase,
                           exact_same_sample_bracket=c['bracket_rows']==vco[jj]['bracket_rows'],
                           interval_count=counts[i]if i<len(counts)else None))
assert all(b['phase_ps']>0 for b in boundaries)
assert all(abs(b['cml']['bracket_width_ps']-1.25)<1e-9 for b in boundaries)
checks=r['measurement']['checks'];assert [k for k,v in checks.items()if not v]==[]
prior_path=R/'hw/soc/out/pcie-tail115-halfstep-wave-peer-rx-20261006/result.json'
inputs[str(prior_path)]=pin(prior_path)
prior=j(prior_path);assert prior['findings']==[]
prior_native_path=Path('/dev/shm/nssoc-vco-v6-divider-tail115-v1-halfstep-06-01/result.json')
assert pin(prior_native_path)==prior['inputs'][str(prior_native_path)]
frequency=(len(vt)-1)/(vt[-1]-vt[0]);prior_frequency=j(prior_native_path)['measurement']['vco_frequency_hz']
assert abs(frequency-r['measurement']['vco_frequency_hz'])<1e-3
ppm=(frequency/prior_frequency-1)*1e6
assert 1078<ppm<1080
assert all(pin(p)==h for p,h in inputs.items())
record=dict(status='PASS_INDEPENDENT_SAVED_TAIL115_QUARTERSTEP_RAW_RECOUNT_FINITE_POINT_SCREEN',
    original_native_status=r['status'],native_acceptance_changed=False,findings=[],
    inputs=inputs,full_raw_sha256=r['raw_sha256'],payload_sha256=r['payload_sha256'],
    rows=rows,columns=n,finite_values=int(array.size),all64_HBT_VCE=hbt,
    minimum_HBT_VCE=min(x['minimum_settled_vce']for x in hbt),
    source_native_simulator_binding=dict(devices=91,terminals=terms,metal_terminals=metal,body_terminals=body,records=bound),
    original_measurement_checks=checks,vco_frequency_hz=frequency,prior_2p5ps_vco_frequency_hz=prior_frequency,frequency_change_ppm=ppm,numerical_convergence_claim=False,CML_edges=len(cml),VCO_edges=len(vco),
    CML_interval_counts=counts,interval_histogram=dict(collections.Counter(counts)),
    bad_intervals=bad,fixed_ordinal_advance=4,boundaries=boundaries,
    critical_boundary_summary=[boundaries[i]for i in (57,58,59,60)],
    diagnostic_comparison='All61 CML times, paired VCO times, exact saved bracketing voltages/times, fixed ordinal phases and original60 half-open counts reproduce Euclid saved diagnosis exactly.',
    interpretation='All60 half-open counts are4 at1.25ps; every paired CML-minus-VCO phase is positive, ranging about0.06059 to1.50264ps. Fixed ordinal pairing advances4 everywhere and is diagnostic only. Brackets do not provide rigorous interpolation error bounds, and the VCO frequency changed by about1079ppm versus2.5ps, so numerical convergence is not established. Original divide4 and whole-loop finite point screens pass; this saved recount changes no threshold, model, window or physical acceptance.',
    scope='Independent full saved raw hash/payload hash and every26,046,669 finite values; all64 HBT settled VCE and exact91intrinsic/283terminal simulator/source/native records recounted. Other455-device safety checks are retained producer claims, not independently requalified here. No native, EDA, control, plotting, publication or capture modification.')
with(O/'result.json').open('x')as f:json.dump(record,f,indent=2);f.write('\n')
print(json.dumps(dict(result=pin(O/'result.json'),finite_values=record['finite_values'],minimum_HBT_VCE=record['minimum_HBT_VCE'],
                     counts=record['interval_histogram'],phase58_ps=boundaries[58]['phase_ps'],phase59_ps=boundaries[59]['phase_ps'],
                     acceptance=r['status']),indent=2))
