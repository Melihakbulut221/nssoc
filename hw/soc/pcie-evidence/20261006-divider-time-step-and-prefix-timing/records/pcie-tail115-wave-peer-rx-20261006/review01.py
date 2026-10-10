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

os.sched_setaffinity(0,{10})
resource.setrlimit(resource.RLIMIT_CORE,(0,0))
resource.setrlimit(resource.RLIMIT_AS,(2*1024**3,)*2)
import numpy as np

R=Path('/home/hasanmelih/Documents/ChatGPT/nnsoc')
O=Path(__file__).resolve().parent
N=Path('/dev/shm/nssoc-vco-v6-divider-tail115-v1-wire-06-01')
F=R/'sw/tests/fixtures/pcie_clock_div4_v10_tail115_v1_hybrid_v1'
E=R/'hw/soc/out/pcie-tail115-layout-wire-loaded-finite-20261006'


def pin(p):
    p=Path(p)
    with p.open('rb')as f:return dict(bytes=p.stat().st_size,sha256=hashlib.file_digest(f,'sha256').hexdigest())


def j(p):return json.loads(p.read_text())


inputs={str(p):pin(p)for p in [N/'result.json',N/'wave.raw.gz',F/'composition.json',
    F/'source-native-bijection.json',E/'event-boundary-diagnosis06.json',
    E/'diagnose_event_boundaries06.py',R/'hw/soc/out/pcie-bias8-wave-root-20261006/review01.py',Path(__file__)]}
assert inputs[str(N/'result.json')]==dict(bytes=426335,sha256='04f18138303887b2755c09b08afb47c2c5e6c830a40c810578f069f6ecfc2ab7')
assert inputs[str(N/'wave.raw.gz')]==dict(bytes=48558969,sha256='d9e004391d25273a08b8f86db7bcd5e7cf73a54c615e83c614fbae481520fe3c')
r=j(N/'result.json');diagnosis=j(E/'event-boundary-diagnosis06.json')
assert r['status']=='FAIL_NATIVE_LOADED_FEEDBACK_SCREEN' and r['measurement']['passed']is False
assert r['safety']['passed']is True and len(r['devices'])==455
raw=gzip.decompress((N/'wave.raw.gz').read_bytes())
assert len(raw)==r['raw_bytes']==52235634 and hashlib.sha256(raw).hexdigest()==r['raw_sha256']
header,payload=raw.split(b'Binary:\n',1)
assert b'Flags: real\n'in header and int(re.search(rb'No\. Points: (\d+)',header)[1])==0
n=int(re.search(rb'No\. Variables: (\d+)',header)[1]);assert n==957
names=[]
for line in header.split(b'Variables:\n')[1].splitlines():
    fields=line.decode('ascii').split();assert len(fields)==3 and int(fields[0])==len(names)
    names.append(fields[1])
assert len(names)==len(set(names))==n
rows,tail=divmod(len(payload),n*8)
assert rows==r['rows']==6817 and payload[rows*n*8:]==str(rows).encode() and tail==4
binary=payload[:rows*n*8]
assert hashlib.sha256(binary).hexdigest()==r['payload_sha256']
array=np.frombuffer(binary,dtype='<f8').reshape(rows,n)
assert array.size==r['values']==6523869 and np.isfinite(array).all()
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
assert ct==r['measurement']['edge_times']['cml'] and len(cml)==61 and len(vco)==243
counts=[sum(a<=v<b for v in vt)for a,b in zip(ct[:-1],ct[1:])]
assert counts==r['measurement']['actual_vco_period_counts']['native_hbt_div4']==diagnosis['counts']
assert collections.Counter(counts)=={4:59,3:1}
bad=[i for i,x in enumerate(counts)if x!=4];assert bad==[41]==diagnosis['bad_intervals']
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
assert boundaries[41]['phase_ps']>0 and boundaries[42]['phase_ps']<0
assert boundaries[41]['exact_same_sample_bracket'] and boundaries[42]['exact_same_sample_bracket']
assert all(abs(boundaries[i]['cml']['bracket_width_ps']-5)<1e-9 for i in (41,42))
checks=r['measurement']['checks'];assert [k for k,v in checks.items()if not v]==['native_hbt_div4']
assert all(pin(p)==h for p,h in inputs.items())
record=dict(status='PASS_INDEPENDENT_SAVED_TAIL115_RAW_RECOUNT_ORIGINAL_FUNCTIONAL_FAIL_RETAINED',
    original_native_status=r['status'],native_acceptance_changed=False,findings=[],
    inputs=inputs,full_raw_sha256=r['raw_sha256'],payload_sha256=r['payload_sha256'],
    rows=rows,columns=n,finite_values=int(array.size),all64_HBT_VCE=hbt,
    minimum_HBT_VCE=min(x['minimum_settled_vce']for x in hbt),
    source_native_simulator_binding=dict(devices=91,terminals=terms,metal_terminals=metal,body_terminals=body,records=bound),
    original_measurement_checks=checks,CML_edges=len(cml),VCO_edges=len(vco),
    CML_interval_counts=counts,interval_histogram=dict(collections.Counter(counts)),
    bad_intervals=bad,fixed_ordinal_advance=4,boundaries=boundaries,
    critical_boundary_summary=[boundaries[i]for i in (40,41,42,43)],
    diagnostic_comparison='All61 CML times, paired VCO times, exact saved bracketing voltages/times, fixed ordinal phases and original60 half-open counts reproduce Euclid saved diagnosis exactly.',
    interpretation='The single count3 interval begins24.425469885ns and ends24.919785412ns. Interpolated CML-minus-VCO phase changes from positive to negative within common5ps saved sample brackets. Fixed ordinal pairing advances4 everywhere and is diagnostic only. Brackets do not provide rigorous interpolation error bounds, and this recount is not a smaller-step convergence test. Original divide4 FAIL remains; no threshold, model, window or acceptance changes.',
    scope='Independent full saved raw hash/payload hash and every6,523,869 finite values; all64 HBT settled VCE and exact91intrinsic/283terminal simulator/source/native records recounted. Other455-device safety checks are retained producer claims, not independently requalified here. No native, EDA, control, plotting, publication or capture modification.')
with(O/'result.json').open('x')as f:json.dump(record,f,indent=2);f.write('\n')
print(json.dumps(dict(result=pin(O/'result.json'),finite_values=record['finite_values'],minimum_HBT_VCE=record['minimum_HBT_VCE'],
                     counts=record['interval_histogram'],phase41_ps=boundaries[41]['phase_ps'],phase42_ps=boundaries[42]['phase_ps'],
                     acceptance=r['status']),indent=2))
