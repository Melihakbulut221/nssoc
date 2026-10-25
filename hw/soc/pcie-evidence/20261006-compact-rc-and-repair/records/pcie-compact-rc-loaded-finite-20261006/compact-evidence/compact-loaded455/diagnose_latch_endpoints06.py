"""Actual saved transistor-terminal probes; descriptive only, no new simulation."""
from pathlib import Path
import json,gzip,hashlib,sys
import numpy as np
R=Path.cwd();B=Path(__file__).resolve().parent;P=Path('/dev/shm/nssoc-vco-v6-divider-compact-v2-wire-06-01');F=R/'sw/tests/fixtures/pcie_clock_div4_v7_compact_v2_hybrid_v1'
sys.path.insert(0,str(R/'scripts'));import characterize_pcie_vco_v6_divider_compact_v2_wire_v1 as m
j=json.loads((P/'result.json').read_text());c=json.loads((F/'composition.json').read_text());b=json.loads((F/'source-native-bijection.json').read_text());rows={x['native_id']:x for x in c['records']};byname={x['source_name']:x for x in b['devices']}
with gzip.open(P/'wave.raw.gz','rb')as f:h,meta=m.life.tiny.parse_header(f,m.n.vectors(j['devices'],j['config']['extra_vectors']));raw=f.read()
assert hashlib.sha256(h+raw).hexdigest()==j['raw_sha256'];width=len(meta['columns'])*8;assert raw[j['rows']*width:]==str(j['rows']).encode();a=np.frombuffer(raw[:j['rows']*width],'<f8').reshape(j['rows'],-1);d=dict(zip(m.stream.previous.data_names(meta['columns']),a.T));t=d['time'];mask=(t>=4e-9)&(t<=34e-9)
def val(name,terminal):
 row=rows[byname[name]['native_id']];z=next(x for x in row['terminals']if x['terminal']==terminal);label='v(xchain.xdiv.'+z['node'].lower()+')';return d[label],label
def stats(a):
 x=a[mask];return dict(min=float(x.min()),max=float(x.max()),mean=float(x.mean()))
result=[];clocks={}
for name in ['DIV__XFIRST__XCORE','DIV__XSECOND']:
 for side in ['XM','XS']:
  prefix=name+'__'+side;cs,csn=val(prefix+'__XCS','B');ch,chn=val(prefix+'__XCH','B');clock=cs-ch;clocks[(name,side)]=clock;hbts=[]
  for tail in ['XCS','XCH','XT','XDP','XDN','XLP','XLN']:
   n=prefix+'__'+tail;v={k:val(n,k) for k in ['C','B','E']};hbts.append(dict(source_name=n,nodes={k:z[1]for k,z in v.items()},VCE=stats(v['C'][0]-v['E'][0]),VBE=stats(v['B'][0]-v['E'][0]),VCB=stats(v['C'][0]-v['B'][0])))
  result.append(dict(latch=prefix,clock_nodes=[csn,chn],clock_differential=stats(clock),fraction_abs_clock_below26mV=float((abs(clock[mask])<.026).mean()),fraction_track_clock_above50mV=float((clock[mask]>.05).mean()),actual_HBT_terminals=hbts))
for name in ['DIV__XFIRST__XCORE','DIV__XSECOND']:
 p=clocks[(name,'XM')][mask];q=clocks[(name,'XS')][mask];print(name,'bothtrack50mV',float(((p>.05)&(q>.05)).mean()),'neithertrack50mV',float(((p<-.05)&(q<-.05)).mean()))
rec=dict(status='DESCRIPTIVE_SAVED_REAL_LATCH_CLOCK_AND_HBT_TERMINALS',source_native_status=j['status'],raw_sha256=j['raw_sha256'],result=result,scope='No native run, no thresholds or circuit changes; small-clock fractions are diagnosis, not new acceptance predicates. Every voltage is exact native intrinsic terminal node.')
(B/'latch-endpoints06.json').write_text(json.dumps(rec,indent=2)+'\n')
for x in result:
 print(x['latch'],x['clock_differential'],'smallclock',x['fraction_abs_clock_below26mV'])
 for h in x['actual_HBT_terminals']:print(h['source_name'],'VCE',h['VCE'],'VBE',h['VBE'])
