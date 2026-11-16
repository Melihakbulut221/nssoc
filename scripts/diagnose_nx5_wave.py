import subprocess,json,hashlib,zipfile,pathlib,numpy as np
out=pathlib.Path('diagnosis');out.mkdir()
meta=json.loads(subprocess.check_output(['gh','api','repos/Melihakbulut221/nssoc/actions/artifacts/14195194079']))
expected='8534403fb68bae7c6a8025f8247fe95e751e07a952f4f393693e5cefb5c5e1b0'
assert not meta['expired'] and meta['workflow_run']['id']==43790692093 and meta['digest']=='sha256:'+expected
assert meta['workflow_run']['head_sha']=='b8185088e8abe7fa79f6b39e7576c6affde2d149'
archive=pathlib.Path('/tmp/native.zip')
with archive.open('wb')as f:subprocess.run(['gh','api','repos/Melihakbulut221/nssoc/actions/artifacts/14195194079/zip'],stdout=f,check=True)
with archive.open('rb')as f:assert hashlib.file_digest(f,'sha256').hexdigest()==expected
with zipfile.ZipFile(archive)as z:
 names=z.namelist();raw=[n for n in names if n.endswith('/wave.raw')];probes=[n for n in names if n.endswith('/loaded-n1-nominal_late.json') or n=='loaded-n1-nominal_late.json']
 assert len(raw)==len(probes)==1
 loaded=json.loads(z.read(probes[0]));bound=loaded['binding']
 assert loaded['sources_unchanged'] and loaded['returncode']==0 and loaded['data_passed'] is False
 target=pathlib.Path('/tmp/wave.raw')
 import shutil
 with z.open(raw[0])as src,target.open('wb')as dst:shutil.copyfileobj(src,dst)
with target.open('rb')as f:
 assert hashlib.file_digest(f,'sha256').hexdigest()=='bc68e0b62854356f53cf094144068bbe1ed55dcda973151f89443a6acfca36a9'
with target.open('rb')as f:
 rows=[]
 while True:
  line=f.readline();assert line;rows.append(line)
  if line==b'Binary:\n':break
 offset=f.tell()
header=b''.join(rows).decode();table=header.split('Variables:\n')[1].split('Binary:\n')[0]
names=[r.split()[1]for r in table.splitlines()];width=len(names);assert width==1791
m=np.memmap(target,dtype='<f8',mode='r',offset=offset).reshape(-1,width);assert len(m)==113490;t=m[:,0]
def v(n):
 n=bound['aliases'].get(n,n)
 return np.zeros(len(t))if n=='0'else m[:,names.index('v('+n+')')]
state=127;bits=[]
for _ in range(256):bits.append(state&1);state=((state<<1)|(((state>>6)^(state>>5))&1))&127
ui=125e-12;start=2e-9;indices=np.arange(1,256);current=np.array(bits)[indices];previous=np.array(bits)[indices-1]
expected={'a':current,'b':previous,'c':previous,'d':previous,'x':current^previous,'y':previous^previous}
result={'physical_geometry_matches':False,'scope':'Rejected 2800-ohm clock-bias exploratory divider with old RC. Diagnostic only: fixed original waveform, no changes to stimulus, expected bits, electrical gates or acceptance. Phase sweep locates delay; it does not qualify a shifted sampling window.','source_run':43790692093,'archive_sha256':expected if False else meta['digest'],'raw_sha256':'bc68e0b62854356f53cf094144068bbe1ed55dcda973151f89443a6acfca36a9','signals':{}}
for tag in 'abcdxy':
 p,n=('xpd.'+tag+'qp','xpd.'+tag+'qn')if tag in 'abcd'else(tag+'p',tag+'n')
 delta=v(p)-v(n);edges=start+(indices+(0 if tag=='b'else .5))*ui;sign=2*expected[tag]-1
 sweep=[]
 for phase in np.arange(0,1.501,.05):
  samples=np.interp(edges+phase*ui,t,delta)*sign
  sweep.append({'phase_ui':round(float(phase),2),'wrong':int((samples<=0).sum()),'below_100mv':int((samples<.1).sum()),'min_v':float(samples.min()),'median_v':float(np.median(samples))})
 result['signals'][tag]={'phase_sweep':sweep,'first_32_bits':expected[tag][:32].tolist(),'original_03_06_09_ui_signed_v':[[float(x)for x in np.interp(edges[:32]+ph*ui,t,delta)*sign[:32]]for ph in (.3,.6,.9)]}
result['clock_candidates']=[n for n in names if n.startswith('v(')and any(x in n.lower()for x in ('clk','clock','ckp','ckn'))]
# Diagnose comparator polarity/settling against its actually observed inputs.
result['actual_input_xor_checks']={}
for tag,left,right in [('x','a','d'),('y','c','d')]:
 delta=v(tag+'p')-v(tag+'n');left_delta=v('xpd.'+left+'qp')-v('xpd.'+left+'qn');right_delta=v('xpd.'+right+'qp')-v('xpd.'+right+'qn')
 points=start+(indices+.5+.75)*ui
 measured=np.interp(points,t,delta);checks=[]
 for delay_ps in range(0,126,5):
  ld=np.interp(points-delay_ps*1e-12,t,left_delta);rd=np.interp(points-delay_ps*1e-12,t,right_delta)
  valid=(np.abs(ld)>=.1)&(np.abs(rd)>=.1)
  xor=np.where(ld*rd<0,1.,-1.)
  signed=measured[valid]*xor[valid]
  checks.append({'delay_ps':delay_ps,'strong_input_pairs':int(valid.sum()),'wrong':int((signed<=0).sum()),'below100mv':int((signed<.1).sum()),'median_signed_v':float(np.median(signed))if len(signed)else None})
 result['actual_input_xor_checks'][tag]=checks
selected=['xp','xn','yp','yn','clkp','clkn','xpd.aqp','xpd.aqn','xpd.bqp','xpd.bqn','xpd.cqp','xpd.cqn','xpd.dqp','xpd.dqn','xpd.s0p','xpd.s0n','xpd.s1p','xpd.s1n']
result['selected_aliases']={n:bound['aliases'].get(n,n)for n in selected}
result['ports']=bound['ports']
watch=set(result['selected_aliases'].values())
result['connected_devices']={g:{name:dev for name,dev in group.items()if set(dev.get('nodes',[]))&watch}for g,group in bound['groups'].items()}
result['correction']='Previous diagnostic X A/B correlation was not direct physical comparator input; X uses retimed A/D, buffered as AD/S0. This does not alter original functional expected samples or acceptance gates.'
result['buffer_stage_checks']={}
for label,p,n,bits_expected in [('AD','adp','adn',current),('CD','cdp','cdn',previous),('S0','s0p','s0n',previous),('S1','s1p','s1n',previous)]:
 delta=v('xpd.'+p)-v('xpd.'+n);sign=2*bits_expected-1;measurements=[]
 for phase in (.3,.5,.6,.75,.9):
  vals=np.interp(start+(indices+.5+phase)*ui,t,delta)*sign
  measurements.append({'phase_ui':phase,'wrong':int((vals<=0).sum()),'below100mv':int((vals<.1).sum()),'min_signed_v':float(vals.min()),'median_signed_v':float(np.median(vals))})
 result['buffer_stage_checks'][label]=measurements
result['buffered_xor_checks']={}
for tag,left,right in [('x','ad','s0'),('y','cd','s1')]:
 delta=v(tag+'p')-v(tag+'n');ld=v('xpd.'+left+'p')-v('xpd.'+left+'n');rd=v('xpd.'+right+'p')-v('xpd.'+right+'n')
 points=start+(indices+.5+.75)*ui;measured=np.interp(points,t,delta);checks=[]
 for delay_ps in range(0,81,5):
  l=np.interp(points-delay_ps*1e-12,t,ld);rr=np.interp(points-delay_ps*1e-12,t,rd);valid=(np.abs(l)>=.1)&(np.abs(rr)>=.1);sign=np.where(l*rr<0,1.,-1.);signed=measured[valid]*sign[valid]
  checks.append({'delay_ps':delay_ps,'strong_input_pairs':int(valid.sum()),'wrong':int((signed<=0).sum()),'below100mv':int((signed<.1).sum()),'median_signed_v':float(np.median(signed))if len(signed)else None})
 result['buffered_xor_checks'][tag]=checks
result['divider_base_checks']={}
for label,ip,inn,bits_expected in [('UA',273,274,current),('UC',294,297,previous),('US0',295,299,previous),('US1',296,298,previous)]:
 p=bound['groups']['npn13g2']['xpd.xd'+str(ip).zfill(4)];n=bound['groups']['npn13g2']['xpd.xd'+str(inn).zfill(4)]
 assert p['native_id']==ip and n['native_id']==inn
 vp=v(p['nodes'][1]);vn=v(n['nodes'][1]);delta=vp-vn;sign=2*bits_expected-1;measurements=[]
 for phase in (.3,.5,.6,.75,.9):
  points=start+(indices+.5+phase)*ui;vals=np.interp(points,t,delta)*sign;cm=np.interp(points,t,(vp+vn)/2)
  measurements.append({'phase_ui':phase,'wrong':int((vals<=0).sum()),'below100mv':int((vals<.1).sum()),'min_signed_v':float(vals.min()),'median_signed_v':float(np.median(vals)),'commonmode_min_v':float(cm.min()),'commonmode_max_v':float(cm.max())})
 result['divider_base_checks'][label]={'positive_device':ip,'negative_device':inn,'positive_node':p['nodes'][1],'negative_node':n['nodes'][1],'samples':measurements}

# Read-only latency localization on native samples. Censor within one UI;
# ten-ps stability rejects a momentary crossing. This is NOT a new gate.
stage_specs={}
for key,bitkey in [('a','a'),('c','c'),('d','d')]:
 stage_specs[key]=(v('xpd.'+key+'qp')-v('xpd.'+key+'qn'),expected[bitkey])
for key,bitkey in [('UA','a'),('UC','c'),('US0','d'),('US1','d')]:
 item=result['divider_base_checks'][key]
 stage_specs[key]=(v(item['positive_node'])-v(item['negative_node']),expected[bitkey])
for key,pin,bitkey in [('AD','ad','a'),('CD','cd','c'),('S0','s0','d'),('S1','s1','d')]:
 stage_specs[key]=(v('xpd.'+pin+'p')-v('xpd.'+pin+'n'),expected[bitkey])
latencies={};records={}
def stats(values):
 return dict(count=len(values),minimum_ps=float(np.min(values)) if values else None,
  median_ps=float(np.median(values)) if values else None,
  p95_ps=float(np.percentile(values,95)) if values else None,
  maximum_ps=float(np.max(values)) if values else None)
for key,(delta,bitvalues) in stage_specs.items():
 for threshold in [0.,.1]:
  label=key+('@zero'if threshold==0 else'@100mv');rows=[];times={}
  for k in range(1,len(indices)):
   if bitvalues[k]==bitvalues[k-1]:continue
   edge=start+(indices[k]+.5)*ui
   lo=int(np.searchsorted(t,edge));hi=int(np.searchsorted(t,edge+ui))
   sign=2*int(bitvalues[k])-1;signed=delta[lo:hi]*sign
   valid=signed>0 if threshold==0 else signed>=threshold;hit=None
   for j in np.flatnonzero(valid):
    end=int(np.searchsorted(t,t[lo+j]+10e-12,side='left'))-lo
    if end>=len(valid):break
    if np.all(valid[j:end+1]):hit=float(t[lo+j]);break
   rows.append(dict(bit_index=int(indices[k]),settled_native_time_s=hit,
    latency_ps=(hit-edge)*1e12 if hit is not None else None))
   if hit is not None:times[int(indices[k])]=hit
  records[label]=rows;latencies[label]=dict(transitions=len(rows),missing_before_one_ui=sum(x['latency_ps']is None for x in rows),**stats([x['latency_ps']for x in rows if x['latency_ps']is not None]))
increments={}
for left,right in [('a','UA'),('UA','AD'),('c','UC'),('UC','CD'),('d','US0'),('US0','S0'),('d','US1'),('US1','S1')]:
 for suffix in ['@zero','@100mv']:
  a={x['bit_index']:x['settled_native_time_s']for x in records[left+suffix]if x['settled_native_time_s']is not None}
  b={x['bit_index']:x['settled_native_time_s']for x in records[right+suffix]if x['settled_native_time_s']is not None}
  increments[left+'->'+right+suffix]=stats([(b[k]-a[k])*1e12 for k in sorted(set(a)&set(b))])
result['stage_latency']=dict(scope='Transition-only native-sample first crossing sustained ten ps, censored at one UI after original clock edge. Paired increments can be negative; missing crossings excluded and counted. Not physical acceptance, not shifted sample gates.',
 native_sample_only=True,stability_ps=10,censor_ui=1,summary=latencies,paired_increment=increments,per_transition=records)

(out/'wave-diagnosis.json').write_text(json.dumps(result,indent=2))
print(json.dumps({k:min(v['phase_sweep'],key=lambda x:(x['wrong'],x['below_100mv']))for k,v in result['signals'].items()}))
