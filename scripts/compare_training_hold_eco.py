import os,subprocess,json,hashlib,zipfile,re,time
from pathlib import Path
assert os.environ.get('GITHUB_ACTIONS')=='true'
p='repos/Melihakbulut221/nssoc/'
def api(s):return json.loads(subprocess.check_output(['gh','api',p+s]))
def archive(i,h,run,head):
 r=api('actions/runs/'+str(run));assert r['status']=='completed' and r['conclusion']=='success' and r['head_sha']==head
 m=api('actions/artifacts/'+str(i));assert not m['expired'];assert m['workflow_run']['id']==run and m['workflow_run']['head_sha']==head and m['digest']=='sha256:'+h
 path=Path(str(i)+'.zip')
 with path.open('xb')as f:subprocess.run(['gh','api',p+'actions/artifacts/'+str(i)+'/zip'],stdout=f,check=True)
 with path.open('rb')as f:assert hashlib.file_digest(f,'sha256').hexdigest()==h
 return zipfile.ZipFile(path)
# Wait for the exact producer; never infer completion from a missing artifact.
run=43648980039;head='95929ee677c79d9bab52f47c28f684eedb91795a'
deadline=time.monotonic()+2700
while True:
 r=api('actions/runs/'+str(run));assert r['head_sha']==head
 if r['status']=='completed':break
 assert time.monotonic()<deadline,'Producer pending; no impact result claimed'
 print('Waiting for exact RX physical ECO',run,r['status'],flush=True);time.sleep(45)
assert r['conclusion']=='success'
arts=api('actions/runs/'+str(run)+'/artifacts')['artifacts']
def producer(kind):
 matches=[x for x in arts if x['name']==f'rx-pcie-hold-eco-{kind}-{run}' and not x['expired']];assert len(matches)==1
 item=matches[0];assert item['digest'].startswith('sha256:')
 return archive(item['id'],item['digest'].split(':')[1],run,head)
prior=archive(14134996872,'e6893782d2385474b989299f52807ea4e4c11f4ffc06a6a366310fe3484d5832',43648005592,'f58d9ada2b6441b33ea8c27ff693e7a1e6c525f6')
new=producer('native');safe=producer('derived')
original={'measurements':{'after':{}}}
for label,corner in [('slow','nom_slow_1p08V_125C'),('typical','nom_typ_1p20V_25C'),('fast','nom_fast_1p32V_m40C')]:
 names=[n for n in prior.namelist()if n.endswith('-nssoc-input'+label+'/state_out.json')];assert len(names)==1
 state=json.loads(prior.read(names[0]));original['measurements']['after'][corner]={'metrics':{k:v for k,v in state['metrics'].items()if k.endswith('__corner:'+corner)}}
 assert not prior.read(names[0].rsplit('/',1)[0]+'/unpropagated.rpt').strip()
assert hashlib.sha256(prior.read('1-nssoc-trainingholdeco/soc_top.odb')).hexdigest()=='635f0e623eb202d845bde5a1f29f65466cf82f639dc2f7044aaabcac1451c203'
candidate=json.loads(safe.read('result.json'));assert candidate['source_unchanged']
assert candidate['source_odb_sha256']=='635f0e623eb202d845bde5a1f29f65466cf82f639dc2f7044aaabcac1451c203'
assert len(new.namelist())==len(set(new.namelist()))
odb=[n for n in new.namelist()if n.endswith('.odb')];assert set(odb)=={'1-nssoc-trainingholdeco/soc_top.odb','final/odb/soc_top.odb'},odb
assert all(hashlib.sha256(new.read(n)).hexdigest()==candidate['candidate_odb_sha256'] for n in odb)
rows={};regressions=[]
for label,corner in [('slow','nom_slow_1p08V_125C'),('typical','nom_typ_1p20V_25C'),('fast','nom_fast_1p32V_m40C')]:
 names=[n for n in new.namelist()if n.endswith('-nssoc-input'+label+'/state_out.json')];assert len(names)==1
 state=json.loads(new.read(names[0]));before=original['measurements']['after'][corner]['metrics'];after={k:v for k,v in state['metrics'].items()if k.endswith('__corner:'+corner)}
 differences={}
 for k,v in before.items():
  assert k in after,k
  if after[k]!=v:differences[k]={'before':v,'after':after[k]}
  if (('vio__count' in k or 'violation__count' in k)and after[k]>v)or (('__ws__'in k or '__tns__'in k)and after[k]<v-0.00001):regressions.append({'corner':corner,'metric':k,'before':v,'after':after[k]})
 folder=names[0].rsplit('/',1)[0];assert not new.read(folder+'/unpropagated.rpt').strip()
 rows[corner]={'before':before,'after':after,'differences':differences,'state_sha256':hashlib.sha256(new.read(names[0])).hexdigest()}
Path('out').mkdir();Path('out/comparison.json').write_text(json.dumps({'status':'MEASURED_WHOLE_CHIP_METRICS_NOT_SIGNOFF','producer_run':run,'producer_head':head,'producer_artifacts':arts,'candidate_odb_sha256':candidate['candidate_odb_sha256'],'all_forty_ios_passed':candidate['all_io_setup_hold_margin_50ps_passed'],'corners':rows,'regressions':regressions,'accepted':False,'scope':'Fresh existing native all-path metrics around fifty-eight-cell PCIe input ECO, placement RC only. Explicitly preserve remaining failures.'},indent=2))
print(json.dumps({'regressions':regressions,'candidate_odb_sha256':candidate['candidate_odb_sha256']}))
