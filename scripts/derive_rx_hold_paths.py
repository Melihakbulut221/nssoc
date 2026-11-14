import os,json,subprocess,hashlib,zipfile,re
from pathlib import Path
assert os.environ.get('GITHUB_ACTIONS')=='true'
P='repos/Melihakbulut221/nssoc/'
def api(s):return json.loads(subprocess.check_output(['gh','api',P+s]))
run=43653684598;head='49d8a9aa95863bc35fb87a448583b8c77f6b4896';aid=14137831182
r=api(f'actions/runs/{run}');assert r['status']=='completed'and r['conclusion']=='success'and r['head_sha']==head
m=api(f'actions/artifacts/{aid}');expected='1d8aa6f46257d545a933e33c0e764207a5ab26f42c00db75bcfc7e76dd38186a'
assert not m['expired']and m['workflow_run']['id']==run and m['workflow_run']['head_sha']==head and m['digest']=='sha256:'+expected
p=Path('native.zip')
with p.open('xb')as f:subprocess.run(['gh','api',P+f'actions/artifacts/{aid}/zip'],stdout=f,check=True)
with p.open('rb')as f:assert hashlib.file_digest(f,'sha256').hexdigest()==expected
z=zipfile.ZipFile(p);assert len(z.namelist())==len(set(z.namelist()))
assert hashlib.sha256(z.read('1-nssoc-trainingholdeco/soc_top.odb')).hexdigest()=='4f937eac00ff3936e6f6ed874db0af68cd92bd15ce9c31500a19c3b89db215d1'
rows={};hashes={}
for corner in ['slow','typical','fast']:
 rows[corner]={}
 for kind in ['min','max']:
  names=[n for n in z.namelist()if n.endswith('-nssoc-input'+corner+'/'+kind+'.rpt')];assert len(names)==1,names
  raw=z.read(names[0]);hashes[names[0]]=hashlib.sha256(raw).hexdigest();text=raw.decode()
  entries=[]
  for part in re.split(r'(?=Startpoint:)',text):
   if not part.startswith('Startpoint:'):continue
   start=re.search(r'^Startpoint: (\S+)',part,re.M);end=re.search(r'^Endpoint: (\S+)',part,re.M)
   slack=re.findall(r'([-+]?[0-9]+\.[0-9]+)\s+slack\s+\((MET|VIOLATED)\)',part)
   assert start and end and len(slack)==1 and 'Path Type: '+kind in part
   entries.append({'start':start[1],'end':end[1],'slack_ns':float(slack[0][0]),'path_text':part if kind=='min'and float(slack[0][0])<0 else None,'input':bool(re.search(r'^Startpoint:.*input port',part,re.M)),'output':bool(re.search(r'^Endpoint:.*output port',part,re.M))})
  assert entries
  rows[corner][kind]=entries
endpoints=sorted({v['end']for corner in rows.values()for v in corner['min']if v['slack_ns']<0})
paired=[]
for endpoint in endpoints:
 item={'endpoint':endpoint,'corners':{}}
 for corner,data in rows.items():
  minimum=[x for x in data['min']if x['end']==endpoint];maximum=[x for x in data['max']if x['end']==endpoint]
  item['corners'][corner]={'hold':min(minimum,key=lambda x:x['slack_ns'])if minimum else None,'setup':min(maximum,key=lambda x:x['slack_ns'])if maximum else None}
 paired.append(item)
Path('out').mkdir();Path('out/census.json').write_text(json.dumps({'source_run':run,'source_head':head,'artifact_id':aid,'artifact_sha256':expected,'report_hashes':hashes,'violating_endpoint_union':len(endpoints),'counts':{k:{t:len(v)for t,v in d.items()}for k,d in rows.items()},'endpoints':paired,'candidate_odb_sha256':'4f937eac00ff3936e6f6ed874db0af68cd92bd15ce9c31500a19c3b89db215d1','scope':'Existing combined SRAM feedback IO post-ECO all-path reports; worst setup at same endpoint is conservative but not a targeted input setup proof; missing paths remain unavailable; no new STA or signoff'},indent=2))
print('violating endpoint union',len(endpoints))
