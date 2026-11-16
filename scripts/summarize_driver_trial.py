import os,json,subprocess,hashlib,io,zipfile,pathlib,re
assert os.environ.get('GITHUB_ACTIONS')=='true'
P='repos/Melihakbulut221/nssoc/'
def api(s):return json.loads(subprocess.check_output(['gh','api',P+s]))
r=api('actions/runs/43778028957');assert r['head_sha']=='8b14f4b12f02b090ea852aaa9e18189ae032c0b0' and r['conclusion']=='success' and r['run_attempt']==1
m=api('actions/artifacts/14186982936');h='a2dbfc74b09c892cf7498193c0dc432767eabdab2a3b18698def81b5f74305f4';assert m['workflow_run']['id']==r['id'] and m['digest']=='sha256:'+h and not m['expired']
b=subprocess.check_output(['gh','api',P+'actions/artifacts/14186982936/zip']);assert hashlib.sha256(b).hexdigest()==h;z=zipfile.ZipFile(io.BytesIO(b));d=json.loads(z.read('result.json'))
assert d['source_head']==r['head_sha'] and d['sources_unchanged'] and d['returncode']==0
for n in z.namelist():
 if n!='result.json':assert hashlib.sha256(z.read(n)).hexdigest()==d['outputs'][n],n
out=pathlib.Path('diagnosis');out.mkdir();summary={k:v for k,v in d.items()if k!='outputs'};summary['source_artifact']=m['id'];summary['source_archive_sha256']=h;summary['result_sha256']=hashlib.sha256(z.read('result.json')).hexdigest();summary['paths']={}
for n in z.namelist():
 if '/targeted_' in n and n.endswith('.rpt'):
  t=z.read(n).decode();paths=[s for s in re.split(r'(?=Startpoint:)',t)if s.startswith('Startpoint:')];assert paths;summary['paths'][n]=paths
(out/'result.json').write_text(json.dumps(summary,indent=2));print(json.dumps({k:v for k,v in summary.items()if k not in ['paths','source_before']}))
