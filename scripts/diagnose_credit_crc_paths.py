import os,subprocess,json,hashlib,zipfile,io,re,collections,pathlib
assert os.environ.get('GITHUB_ACTIONS')=='true'
P='repos/Melihakbulut221/nssoc/'
def api(s):return json.loads(subprocess.check_output(['gh','api',P+s]))
r=api('actions/runs/43775507971');assert r['head_sha']=='2f200e0ff6f514d714afc8d39873e5137cccc6c0' and r['conclusion']=='success' and r['run_attempt']==1
m=api('actions/artifacts/14187296947');digest='19ca16464ff21421b6cdd151c8ebb2a95b654cd90c2a99ba7a08125bef07a1e7'
assert m['workflow_run']['id']==r['id'] and m['digest']=='sha256:'+digest and not m['expired']
b=subprocess.check_output(['gh','api',P+'actions/artifacts/14187296947/zip']);assert hashlib.sha256(b).hexdigest()==digest
z=zipfile.ZipFile(io.BytesIO(b));report=json.loads(z.read('result.json'))
assert report['source_head']==r['head_sha'] and report['sources_unchanged'] and report['returncode']==0
for name in z.namelist():
 if name!='result.json':assert hashlib.sha256(z.read(name)).hexdigest()==report['outputs'][name],name
out=pathlib.Path('path-diagnosis');out.mkdir()
result={'source_run':r['id'],'source_head':r['head_sha'],'source_artifact':m['id'],'archive_sha256':digest,'odb_sha256':report['repaired_odb_sha256'],'measurements':report['measurements'],'paths':{},'accepted':False,'scope':'Read-only authenticated placement-RC reports. No ECO, no routed timing acceptance.'}
for corner,data in report['measurements']['after'].items():
 folder=data['directory'];result['paths'][corner]={}
 for name in ['max.rpt','min.rpt','checks.rpt','violator_list.rpt']:
  raw=z.read(folder+'/'+name).decode();parts=re.split(r'(?=Startpoint:)',raw)
  if name in ('max.rpt','min.rpt'):
   paths=[v for v in parts if v.startswith('Startpoint:')]
   groups=collections.Counter()
   for v in paths:
    a=re.search(r'Startpoint: (.*)',v);e=re.search(r'Endpoint: (.*)',v)
    if a and e:groups[(a[1],e[1])]+=1
   result['paths'][corner][name]={'path_count':len(paths),'first_paths':paths[:3],'pairs':[[a,b,n]for (a,b),n in groups.most_common(20)]}
  else:result['paths'][corner][name]={'first_lines':raw.splitlines()[:100],'line_count':len(raw.splitlines())}
(out/'result.json').write_text(json.dumps(result,indent=2))
print(json.dumps(result,indent=2))
