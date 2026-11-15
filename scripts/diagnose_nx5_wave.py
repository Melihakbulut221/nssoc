import subprocess,json,hashlib,zipfile,pathlib,numpy as np
out=pathlib.Path('diagnosis');out.mkdir()
meta=json.loads(subprocess.check_output(['gh','api','repos/Melihakbulut221/nssoc/actions/artifacts/14183830682']))
expected='27992461e56b6e44e266d38d7fc3af0614288a1febec3627fcba0c172e5f7866'
assert not meta['expired'] and meta['workflow_run']['id']==43759760309 and meta['digest']=='sha256:'+expected
archive=pathlib.Path('/tmp/native.zip')
with archive.open('wb')as f:subprocess.run(['gh','api','repos/Melihakbulut221/nssoc/actions/artifacts/14183830682/zip'],stdout=f,check=True)
with archive.open('rb')as f:assert hashlib.file_digest(f,'sha256').hexdigest()==expected
with zipfile.ZipFile(archive)as z:
 names=z.namelist();raw=[n for n in names if n.endswith('/wave.raw')];probes=[n for n in names if n.endswith('/composition-n1/probes.json')]
 assert len(raw)==len(probes)==1
 bound=json.loads(z.read(probes[0]))
 target=pathlib.Path('/tmp/wave.raw')
 import shutil
 with z.open(raw[0])as src,target.open('wb')as dst:shutil.copyfileobj(src,dst)
with target.open('rb')as f:
 assert hashlib.file_digest(f,'sha256').hexdigest()=='87d364e61bf291a55989ecdbd19da1430c29594dbf6afe88e793f9a8ad2b2d5d'
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
result={'scope':'Diagnostic only: fixed original waveform, no changes to stimulus, expected bits, electrical gates or acceptance. Phase sweep locates delay; it does not qualify a shifted sampling window.','source_run':43759760309,'archive_sha256':expected if False else meta['digest'],'raw_sha256':'87d364e61bf291a55989ecdbd19da1430c29594dbf6afe88e793f9a8ad2b2d5d','signals':{}}
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
for tag,left,right in [('x','a','b'),('y','c','d')]:
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
(out/'wave-diagnosis.json').write_text(json.dumps(result,indent=2))
print(json.dumps({k:min(v['phase_sweep'],key=lambda x:(x['wrong'],x['below_100mv']))for k,v in result['signals'].items()}))
