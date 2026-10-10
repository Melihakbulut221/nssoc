#!/usr/bin/env python3
# SPDX-FileCopyrightText: 2026 Hasan Melih Akbulut
# SPDX-License-Identifier: Apache-2.0
"""Seal only a closed full native table, preserving failed electrical results."""
from pathlib import Path
import gzip,hashlib,json,sys,tarfile
import numpy as np
R=Path.cwd();B=Path(__file__).resolve().parent
sys.path.insert(0,str(R/'scripts'))
import characterize_pcie_vco_v6_divider_compact_v2_wire_v1 as candidate
m=candidate.core
P=Path('/dev/shm/nssoc-vco-v6-divider-compact-v2-wire-06-01')

def pin(p):
    p=Path(p)
    with p.open('rb') as f:return dict(bytes=p.stat().st_size,sha256=hashlib.file_digest(f,'sha256').hexdigest())

controller=json.loads((B/'native06-controller.json').read_text())
assert controller['status']=='CLOSED_FINITE_NATIVE_RESULT'
launch=json.loads((B/'detached-launch.json').read_text())
identity=launch['controller']
stat=Path('/proc')/str(identity['pid'])/'stat'
if stat.exists():
    fields=stat.read_text().rsplit(') ',1)[1].split()
    assert fields[19]!=str(identity['start_ticks']) or fields[0]=='Z', 'Controller still live'
owner=json.loads((P/'owned-processes.json').read_text())
assert all(entry['status']=='REAPED_NO_LIVE_MEMBERS' for entry in owner['processes'])
r=json.loads((P/'result.json').read_text())
assert r['status'] in ('PASS_NATIVE_LOADED_FEEDBACK_SCREEN','FAIL_NATIVE_LOADED_FEEDBACK_SCREEN')
assert len(r['devices'])==455
frozen=json.loads((B/'source-freeze01.json').read_text())
assert all(pin(path)==value for path,value in frozen['pins'].items())
assert all(pin(path)==value for path,value in r['inputs'].items())
assert all(pin(P/path)==value for path,value in r['outputs'].items())
assert all(pin(P/path)==value for path,value in controller['outputs'].items())
with gzip.open(P/'wave.raw.gz','rb') as f:
    header,meta=m.life.tiny.parse_header(f,m.n.vectors(r['devices'],r['config']['extra_vectors']))
    body=f.read()
width=len(meta['columns'])*8
assert body[r['rows']*width:]==str(r['rows']).encode()
payload=body[:r['rows']*width]
assert hashlib.sha256(header+body).hexdigest()==r['raw_sha256']
assert hashlib.sha256(payload).hexdigest()==r['payload_sha256']
assert len(header)+len(body)==r['raw_bytes']
data=dict(zip(m.stream.previous.data_names(meta['columns']),np.frombuffer(payload,'<f8').reshape(r['rows'],-1).T))
assert all(np.isfinite(x).all() for x in data.values())
contacts=[row for row in r['devices'] if row['model'] in ('ptap1','ntap1')]
other=[row for row in r['devices'] if row not in contacts]
assert len(contacts)==31 and len(other)==424
safety=m.n.safety(data,other,r['config']['window_s'])
assert safety['all_device_bounds']==r['safety']['all_device_bounds'][:424]
assert safety['model_geometry_range_issues']==r['safety']['model_geometry_range_issues']
for row,reported in zip(contacts,r['safety']['all_device_bounds'][424:]):
    values=[data[f'v({x})'] if x!='0' else np.zeros(r['rows']) for x in row['nets']]
    actual=float(abs(values[0]-values[1]).max())
    assert reported['path']==row['path']
    assert reported['max_capture_terminal_difference']==actual
    assert reported['inferred_ohmic_peak_a']==actual/float(row['params']['r'])
assert m.n.validate_time_grid(data['time'],34e-9,5e-12)==r['time_grid']
assert m.measurement(data,r['config'])==r['measurement']
native=m.stream.previous.startup_proof(P,r)
assert all(r[k]==v for k,v in native.items())
review={'status':'PASS_COMPLETE_RAW_REPLAY_SOURCE_STATUS_UNCHANGED','native_status':r['status'],'native_result':pin(P/'result.json'),'columns':len(meta['columns']),'rows':r['rows'],'values':r['values'],'all455_device_screens_reproduced':True,'all_counts_measurements_reproduced':True,'all64_native_OFF_reproduced':True,'full_raw_sha256':r['raw_sha256'],'no_native_rerun':True}
(B/'review-06-01.json').write_text(json.dumps(review,indent=2)+'\n')
files={}
for root in [P,m.HYBRID,Path('/dev/shm/nssoc-div4-v7-compact-v2-wire-native-01'),Path('/dev/shm/nssoc-div4-v7-compact-v2-wire-rc-01')]:
    for path in root.rglob('*'):
        if path.is_file():files['native/'+root.name+'/'+str(path.relative_to(root))]=path
# Project methods and exact source fixtures only; never redistribute compiled
# runtime or upstream PDK model implementations. Their hashes stay in receipts.
for name in frozen['pins']:
    path=Path(name)
    if path.is_relative_to(R) and not path.is_relative_to(B) and '/tools/' not in str(path):files['project/'+str(path.relative_to(R))]=path
for path in B.rglob('*'):
    if not path.is_file() or path.suffix=='.pyc' or '__pycache__' in path.parts or path.name.startswith(('pcie-vco-v6-divider-compact-v2-wire-06-01','members-06-01','validation-06-01')):continue
    files['review/'+str(path.relative_to(B))]=path
for name in ('Apache-2.0','CERN-OHL-W-2.0','CC-BY-4.0'):files['licenses/'+name+'.txt']=R/'LICENSES'/(name+'.txt')
notices=B/'NOTICES.txt'
if not notices.exists():notices.write_text('Project methods Apache-2.0; circuit CERN-OHL-W-2.0; native evidence CC-BY-4.0. Copyright 2026 Hasan Melih Akbulut. PDK models and native binaries are not redistributed. Actual62 VCO +91 divider +302 CMOS feedback devices;1271R/1414C. Body-substrate and wire-capacitance reference ports remain separately exposed with explicit ideal grounded bench assumptions. No qualified PEX, RF/PVT/ESD, PLL, full PHY or chip qualification. All source and electrical failures remain visible.\n')
files['review/NOTICES.txt']=notices
members={name:pin(path) for name,path in files.items()}
cap=B/'pcie-vco-v6-divider-compact-v2-wire-06-01.tar.xz'
assert not cap.exists()
with tarfile.open(cap,'w:xz',preset=1,dereference=True) as arc:
    for name,path in files.items():arc.add(path,arcname=name,recursive=False)
seen={}
with tarfile.open(cap,'r|xz') as arc:
    for entry in arc:
        assert entry.isfile()
        seen[entry.name]={'bytes':entry.size,'sha256':hashlib.file_digest(arc.extractfile(entry),'sha256').hexdigest()}
assert seen==members
assert all(pin(path)==value for path,value in frozen['pins'].items())
(B/'members-06-01.json').write_text(json.dumps(members,indent=2)+'\n')
receipt={'status':'SEALED_ALL455_NATIVE_VALUES_FINITE_SCREEN','archive':{'path':str(cap),**pin(cap)},'members':len(members),'member_inventory':pin(B/'members-06-01.json'),'native_result':pin(P/'result.json'),'native_status':r['status'],'replay':pin(B/'review-06-01.json')}
(B/'validation-06-01.json').write_text(json.dumps(receipt,indent=2)+'\n')
print(json.dumps(receipt))
