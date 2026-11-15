import os,json,subprocess,hashlib,io,zipfile,pathlib,re
assert os.environ.get('GITHUB_ACTIONS')=='true'
P='repos/Melihakbulut221/nssoc/'
def api(s):return json.loads(subprocess.check_output(['gh','api',P+s]))
r=api('actions/runs/43776325443');assert r['head_sha']=='50475641846a50fcbb919ff9e218208079515008' and r['conclusion']=='success' and r['run_attempt']==1
m=api('actions/artifacts/14186344549');h='e6ef8008841e9d18436cb75f79326f3620b230b60a3b8b39df691d2f3a0e460e';assert m['workflow_run']['id']==r['id'] and m['digest']=='sha256:'+h and not m['expired']
b=subprocess.check_output(['gh','api',P+'actions/artifacts/14186344549/zip']);assert hashlib.sha256(b).hexdigest()==h;z=zipfile.ZipFile(io.BytesIO(b));d=json.loads(z.read('result.json'))
assert d['source_head']==r['head_sha'] and d['sources_unchanged'] and d['returncode']==0
for n in z.namelist():
 if n!='result.json':assert hashlib.sha256(z.read(n)).hexdigest()==d['outputs'][n],n
out=pathlib.Path('diagnosis');out.mkdir();summary={k:v for k,v in d.items()if k!='outputs'};summary['source_artifact']=m['id'];summary['source_archive_sha256']=h;summary['result_sha256']=hashlib.sha256(z.read('result.json')).hexdigest();summary['paths']={}
for n in z.namelist():
 if n.endswith(('/max.rpt','/min.rpt')):
  t=z.read(n).decode();paths=[s for s in re.split(r'(?=Startpoint:)',t)if s.startswith('Startpoint:')];summary['paths'][n]=paths[:2]
(out/'result.json').write_text(json.dumps(summary,indent=2));print(json.dumps({k:v for k,v in summary.items()if k not in ['paths','source_before']}))
