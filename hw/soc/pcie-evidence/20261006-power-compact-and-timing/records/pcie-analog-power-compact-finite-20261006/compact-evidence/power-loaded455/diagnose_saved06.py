# SPDX-FileCopyrightText: 2026 Hasan Melih Akbulut
# SPDX-License-Identifier: Apache-2.0
"""Descriptive saved-node diagnosis only; no gate or design mutation."""
import gzip,json,sys,hashlib
from pathlib import Path
import numpy as np
R=Path.cwd();B=Path(__file__).resolve().parent;P=Path('/dev/shm/nssoc-vco-v6-divider-power-v2-wire-06-01')
sys.path.insert(0,str(R/'scripts'))
import characterize_pcie_vco_v6_divider_power_v2_wire_v1 as m
result=json.loads((P/'result.json').read_text());comp=json.loads((m.DIVIDER/'composition.json').read_text());binding=json.loads((m.DIVIDER/'source-native-bijection.json').read_text())
by={x['native_id']:x for x in comp['records']}
with gzip.open(P/'wave.raw.gz','rb') as f:
 header,meta=m.life.tiny.parse_header(f,m.n.vectors(result['devices'],result['config']['extra_vectors']));blob=f.read()
width=len(meta['columns'])*8;assert blob[result['rows']*width:]==str(result['rows']).encode()
assert hashlib.sha256(header+blob).hexdigest()==result['raw_sha256']
data=dict(zip(m.stream.previous.data_names(meta['columns']),np.frombuffer(blob[:result['rows']*width],'<f8').reshape(result['rows'],-1).T));t=data['time'];mask=(t>=4e-9)&(t<=34e-9)
terms={};names={}
for item in binding['devices']:
 rec=by[item['native_id']]
 for old,node in zip(item['source_nets'],rec['terminals']):
  if node['node']=='BODY_SUBSTRATE':continue
  label='v(xchain.xdiv.'+node['node'].lower()+')'
  terms.setdefault(old,[]).append((item['source_name'],node['terminal'],label))
 names[item['source_name']]=item

def stat(values):return {'min':float(values[mask].min()),'max':float(values[mask].max()),'mean':float(values[mask].mean())}
pairs=[('VCO_PUBLIC','v(clkp)','v(clkn)')]
for name,a,b in [('FIRST_CLOCK','DIV__XFIRST__CKP','DIV__XFIRST__CKN'),('FIRST_MASTER','DIV__XFIRST__XCORE__MP','DIV__XFIRST__XCORE__MN'),('FIRST_OUTPUT','DIV__S1P','DIV__S1N'),('LIMITER_INPUT','DIV__BIP','DIV__BIN'),('LIMITER_OUTPUT','DIV__LP','DIV__LN'),('SECOND_CLOCK','DIV__CKP','DIV__CKN'),('SECOND_MASTER','DIV__XSECOND__MP','DIV__XSECOND__MN')]:pairs.append((name,terms[a][0][2],terms[b][0][2]))
pairs.append(('DIVIDER_PUBLIC','v(qp)','v(qn)'))
reports=[]
for name,a,b in pairs:
 va,vb=data[a],data[b];delta=va-vb;crossings=[x for x in m.n.common.crossings(t,delta,0) if 4e-9<=x<34e-9]
 reports.append({'name':name,'nodes':[a,b],'differential':stat(delta),'common_mode':stat((va+vb)/2),'rising_edges':len(crossings),'mean_frequency_hz':(len(crossings)-1)/(crossings[-1]-crossings[0]) if len(crossings)>1 else None})
# Largest voltage span between all actual distributed endpoints on each named
# conductor distinguishes wiring drops from the logical primitive topology.
conductor=[]
for name,refs in terms.items():
 values=np.stack([data[x[2]][mask] for x in refs]);spread=float((values.max(axis=0)-values.min(axis=0)).max())
 conductor.append({'logical_net':name,'terminals':len(refs),'max_endpoint_voltage_spread':spread,'minimum':float(values.min()),'maximum':float(values.max())})
conductor.sort(key=lambda x:x['max_endpoint_voltage_spread'],reverse=True)
failed=[]
for row in result['safety']['all_device_bounds']:
 if not row['passed']:
  ident=int(row['path'].split('xd')[-1]);item=next(x for x in binding['devices'] if x['native_id']==ident)
  failed.append(dict(row,source_name=item['source_name'],source_nets=item['source_nets']))
receipt={'status':'DESCRIPTIVE_COMPLETE_SAVED_WAVE_DIVIDER_DIAGNOSIS','native_status':result['status'],'changed_result_or_limits':False,'full_raw_sha256':result['raw_sha256'],'samples':result['rows'],'signal_pairs':reports,'largest_conductor_spreads':conductor[:15],'failed_declared_headroom_screens':failed,'scope':'Observed only. Pair witnesses use explicitly named actual intrinsic terminal endpoints; no idealized-wire rerun or foundry damage assertion.'}
(B/'saved-wave-diagnosis06.json').write_text(json.dumps(receipt,indent=2)+'\n')
for row in reports:print(row['name'],row['differential'],row['common_mode'],row['rising_edges'],row['mean_frequency_hz'])
print('largest conductor spans',conductor[:6])
