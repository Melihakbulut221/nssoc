import json,subprocess,zipfile,hashlib,re
from pathlib import Path
P='repos/Melihakbulut221/nssoc/'
def acquire(aid,digest):
 meta=json.loads(subprocess.check_output(['gh','api',P+'actions/artifacts/'+str(aid)]))
 assert meta['workflow_run']['id']==43631139914 and meta['workflow_run']['head_sha']=='3e15b59941f5de46718a7fa94ed7426c0e4b85d6' and meta['digest']=='sha256:'+digest
 path=Path(str(aid)+'.zip')
 with path.open('xb') as f:subprocess.run(['gh','api',P+'actions/artifacts/'+str(aid)+'/zip'],stdout=f,check=True)
 assert hashlib.sha256(path.read_bytes()).hexdigest()==digest
 return zipfile.ZipFile(path)
native=acquire(14128122304,'a997c6d23fe7c5af22a5887830141297f09a3e253da12f86ca2dfde47ff68ae6')
safe=acquire(14127987571,'73154f72f8b9f946118c4fdbea2207a61a1a44167a69d4de1bf64f6cf3ffba39')
result={'source_run':43631139914,'source_head':'3e15b59941f5de46718a7fa94ed7426c0e4b85d6','cases':{}}
for label in ['baseline','cache']:
 raw=native.read(label+'.v');text=raw.decode()
 cells={n:(kind,body)for kind,n,body in re.findall(r'(?m)^  (sg13g2_\w+) (\S+) \(\n(.*?)\n  \);',text,re.S)}
 assert len(cells)>5000,len(cells)
 rows={}
 for name in safe.namelist():
  if name.startswith(label+'/') and name.endswith('.rpt'):
   report=safe.read(name).decode();paths=[]
   for block in report.split('Startpoint:')[1:]:
    start=block.split()[0];match=re.search(r'Endpoint: (\S+)',block);assert match
    end=match[1]
    aliases={}
    for cell in (start,end):
     assert cell in cells,(cell,label)
     kind,body=cells[cell];aliases[cell]={'type':kind,'ports':dict(re.findall(r'\.(\w+)\((.*?)\)',body))}
    paths.append({'start':start,'end':end,'aliases':aliases,'path':'Startpoint:'+block})
   rows[name]=paths[:5]
 result['cases'][label]={'netlist_sha256':hashlib.sha256(raw).hexdigest(),'paths':rows}
Path('out').mkdir();Path('out/critical-aliases.json').write_text(json.dumps(result,indent=2))
