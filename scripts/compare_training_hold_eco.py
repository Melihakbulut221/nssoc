import os,subprocess,json,hashlib,zipfile,re
from pathlib import Path
assert os.environ.get('GITHUB_ACTIONS')=='true'
p='repos/Melihakbulut221/nssoc/'
def api(s):return json.loads(subprocess.check_output(['gh','api',p+s]))
def archive(i,h,run,head):
 r=api('actions/runs/'+str(run));assert r['status']=='completed' and r['conclusion']=='success' and r['head_sha']==head
 m=api('actions/artifacts/'+str(i));assert m['workflow_run']['id']==run and m['workflow_run']['head_sha']==head and m['digest']=='sha256:'+h
 path=Path(str(i)+'.zip')
 with path.open('xb')as f:subprocess.run(['gh','api',p+'actions/artifacts/'+str(i)+'/zip'],stdout=f,check=True)
 with path.open('rb')as f:assert hashlib.file_digest(f,'sha256').hexdigest()==h
 return zipfile.ZipFile(path)
prior=archive(14132078627,'0ed233f5323f5cd384752bb90205d8ecfe989da42d936701151ea37183815c01',43639975405,'b6dfa2a1429d837d7f4d5e479897cf95dac06f87')
new=archive(14133434311,'b08e5099e538625c4cf30f58e231f62618c58aa6c962cf99f87417d4acfd8b5b',43644585495,'dea0de872cdbf0fa716d68b597033ac2ab23534f')
safe=archive(14134275067,'b84f9d66b6b988be6e0b8857ce4037c97752eaa39af00e0556085ed99c95517c',43644585495,'dea0de872cdbf0fa716d68b597033ac2ab23534f')
original=json.loads(prior.read('result.json'));candidate=json.loads(safe.read('result.json'));assert candidate['input_setup_hold_margin_50ps_passed'] and candidate['source_unchanged']
assert len(new.namelist())==len(set(new.namelist()))
odb=[n for n in new.namelist()if n.endswith('.odb')];assert len(odb)==1,odb
assert hashlib.sha256(new.read(odb[0])).hexdigest()==candidate['candidate_odb_sha256']
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
Path('out').mkdir();Path('out/comparison.json').write_text(json.dumps({'status':'MEASURED_WHOLE_CHIP_METRICS_NOT_SIGNOFF','producer_run':43644585495,'candidate_odb_sha256':candidate['candidate_odb_sha256'],'input_passed':True,'corners':rows,'regressions':regressions,'accepted':False,'scope':'Fresh existing native all-path metrics around two-cell ECO, placement RC only. Explicitly preserve remaining failures.'},indent=2))
print(json.dumps({'regressions':regressions,'candidate_odb_sha256':candidate['candidate_odb_sha256']}))
