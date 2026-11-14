import json,subprocess,hashlib,zipfile
from pathlib import Path
P='repos/Melihakbulut221/nssoc/'
OUT=Path('out');OUT.mkdir()
def api(s):return json.loads(subprocess.check_output(['gh','api',P+s],timeout=60))
inputs=[(43633451595, '2c515a0bfb946ef244cc9e94e2f6af8a7e22e2fe', 14129917895, '2f7429aa34519372129c4a272e381799bfee5a37aefc5b07495b9901e493110b')]
for run,head,aid,digest in inputs:
 r=api('actions/runs/'+str(run));assert r['status']=='completed'and r['head_sha']==head
 meta=api('actions/artifacts/'+str(aid));assert meta['workflow_run']['id']==run and meta['workflow_run']['head_sha']==head and meta['digest']=='sha256:'+digest and not meta['expired']
 path=Path(str(aid)+'.zip')
 with path.open('xb')as f:subprocess.run(['gh','api',P+'actions/artifacts/'+str(aid)+'/zip'],stdout=f,check=True,timeout=300)
 with path.open('rb')as f:assert hashlib.file_digest(f,'sha256').hexdigest()==digest
 z=zipfile.ZipFile(path);data={'run':run,'head':head,'run_conclusion':r['conclusion'],'artifact':aid,'archive_sha256':digest,'members':z.namelist(),'json_reports':{},'path_excerpts':{},'accepted':False}
 for name in z.namelist():
  if name.endswith('/')or name.endswith('config.json'):continue
  if name.endswith('.json'):
   raw=z.read(name);j=json.loads(raw)
   if name.endswith('state_in.json'):continue
   if name.endswith('state_out.json'):j={'metrics':j.get('metrics',{})}
   elif isinstance(j,dict):j={k:v for k,v in j.items()if k not in ('outputs','protected_inputs','placement_source','current_boot_source_revalidation','source_hashes')}
   data['json_reports'][name]={'source_sha256':hashlib.sha256(raw).hexdigest(),'value':j}
  elif Path(name).name in ('max.rpt','min.rpt','summary.rpt','antenna.rpt'):
   raw=z.read(name);data['path_excerpts'][name]={'source_sha256':hashlib.sha256(raw).hexdigest(),'text':'\n'.join(raw.decode().splitlines()[:240])}
 # Count every reported path without truncating to the first path excerpt.
 data['reported_path_groups']={}
 import re
 for name in z.namelist():
  if not (name.endswith('/max.rpt') or name.endswith('/min.rpt')):continue
  groups={}
  for block in z.read(name).decode().split('Startpoint:')[1:]:
   g=re.search(r'Path Group: (.+)',block)
   slack=re.search(r'([-+0-9.]+)\s+slack \((?:VIOLATED|MET)\)',block)
   if not g or not slack:continue
   value=float(slack.group(1));key=g.group(1).strip()
   entry=groups.setdefault(key,dict(reported=0,violating=0,worst_slack=None,worst_path=None))
   entry['reported']+=1;entry['violating']+=int(value<0)
   if entry['worst_slack'] is None or value<entry['worst_slack']:
    entry['worst_slack']=value;entry['worst_path']='Startpoint:'+block
  data['reported_path_groups'][name]=groups
 (OUT/(str(aid)+'.json')).write_text(json.dumps(data,indent=2)+'\n')

# Bind worst after-repair endpoints to the exact independently revalidated mapping.
import io,tarfile,collections
valid=api('actions/runs/43631950511');assert valid['conclusion']=='success'and valid['head_sha']=='a238c421772e0f1ccd8a8e4ef64e7d5aad1cb894'
meta=api('actions/artifacts/14128012721');assert meta['workflow_run']['id']==43630345267 and meta['workflow_run']['head_sha']=='bdd7cc588490425ff98c4718ea8986ecc06a128a'
b=subprocess.check_output(['gh','api',P+'actions/artifacts/14128012721/zip']);assert hashlib.sha256(b).hexdigest()=='d32dd9bb9e0cc1d25f34e29cfbec4bb71908bef7bcaaa577327719602dcd3570'
nz=zipfile.ZipFile(io.BytesIO(b));tar=tarfile.open(fileobj=io.BytesIO(nz.read('build.tgz')),mode='r:gz')
found=[]
for member in tar:
 if member.isfile()and member.name.endswith('soc_top.mapped.json'):
  raw=tar.extractfile(member).read();assert hashlib.sha256(raw).hexdigest()=='1c03ec19a0f8afc2384d92f8974be6cce48ff189e7e1a06e138a69f8754dd8f9';found.append(json.loads(raw))
assert len(found)==1
m=found[0]['modules']['soc_top'];cells=m['cells'];netnames=m['netnames']
def norm(n):return n.replace('\\','').replace('\\','')
# Report formatting may escape a Verilog identifier's backslash multiple times.
def canonical(n):return n.replace(chr(92),'')
lookup=collections.defaultdict(list)
for n in cells:lookup[canonical(n)].append(n)
targets={}
for name,groups in data['reported_path_groups'].items():
 if 'after'not in name:continue
 for group,row in groups.items():
  block=row['worst_path']
  for side in ['Startpoint','Endpoint']:
   match=re.search(side+r':\s*(\S+)',block);assert match
   targets.setdefault(match[1],[]).append({'report':name,'group':group,'side':side,'slack':row['worst_slack']})
rows=[]
for requested,uses in targets.items():
 matches=lookup.get(canonical(requested),[])
 assert len(matches)<=1,(requested,matches)
 if not matches:
  rows.append({'requested':requested,'uses':uses,'status':'TOP_PORT_OR_POST_MAPPING_CELL_NOT_IN_ORIGINAL_NETLIST'});continue
 n=matches[0];c=cells[n];pins={}
 for pin,bits in c['connections'].items():
  aliases=[]
  for net,v in netnames.items():
   if net.startswith('$'):continue
   for i,bit in enumerate(v['bits']):
    if isinstance(bit,int)and bit in bits:aliases.append({'net':net,'index':i+v.get('offset',0),'bit':bit})
  pins[pin]={'bits':bits,'rtl_aliases':aliases}
 rows.append({'requested':requested,'cell':n,'original_mapped_type':c['type'],'src':c.get('attributes',{}).get('src'),'pins':pins,'uses':uses,'status':'EXACT_ORIGINAL_MAPPING_ALIAS_NOT_POST_ECO_MASTER_CLAIM'})
(OUT/'critical-mapping.json').write_text(json.dumps({'timing_run':43633451595,'mapping_producer':43630345267,'mapping_validation':43631950511,'mapped_sha256':'1c03ec19a0f8afc2384d92f8974be6cce48ff189e7e1a06e138a69f8754dd8f9','targets':rows,'accepted':False},indent=2))
