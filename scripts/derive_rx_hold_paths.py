import os,json,subprocess,hashlib,zipfile,re
from pathlib import Path
assert os.environ.get('GITHUB_ACTIONS')=='true'
P='repos/Melihakbulut221/nssoc/'
def api(s):return json.loads(subprocess.check_output(['gh','api',P+s]))
run=43646555578;head='6a87c130412d272c700214201820da450f693fad';aid=14134159392
r=api(f'actions/runs/{run}');assert r['status']=='completed'and r['conclusion']=='success'and r['head_sha']==head
m=api(f'actions/artifacts/{aid}');expected='92d72fe95c41b068bc255e7f9f7a3b0e7abaa415990ec57e948ccc246e7b2e26'
assert not m['expired']and m['workflow_run']['id']==run and m['workflow_run']['head_sha']==head and m['digest']=='sha256:'+expected
p=Path('native.zip')
with p.open('xb')as f:subprocess.run(['gh','api',P+f'actions/artifacts/{aid}/zip'],stdout=f,check=True)
with p.open('rb')as f:assert hashlib.file_digest(f,'sha256').hexdigest()==expected
z=zipfile.ZipFile(p);assert len(z.namelist())==len(set(z.namelist()))
rows=[]
for n in z.namelist():
 if not n.endswith('.rpt') or not any(t in n for t in ['-nssoc-inputslow/','-nssoc-inputtypical/','-nssoc-inputfast/']):continue
 raw=z.read(n);text=raw.decode(errors='strict')
 if 'Startpoint:'not in text:continue
 sections=re.split(r'(?=Startpoint:)',text)
 paths=[v for v in sections if v.startswith('Startpoint:')and 'Path Type: min'in v]
 if not paths:continue
 rows.append({'report':n,'sha256':hashlib.sha256(raw).hexdigest(),'paths_in_report':len(paths),'first_three_paths':paths[:3]})
assert rows,'No actual min paths found'
Path('out').mkdir();Path('out/paths.json').write_text(json.dumps({'source_run':run,'source_head':head,'artifact_id':aid,'artifact_sha256':expected,'candidate_odb_sha256':'dce675ce9aab6a7833fcb55ded416540b392affb065521ef53e3ce9d33d1d54c','scope':'Derived actual native min paths after RX two-cell ECO; no new STA or signoff','reports':rows},indent=2))
print([(x['report'],x['paths_in_report'])for x in rows])
