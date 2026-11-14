import json,subprocess,zipfile,hashlib,re
from pathlib import Path
P='repos/Melihakbulut221/nssoc/'
def acquire(aid,digest):
 meta=json.loads(subprocess.check_output(['gh','api',P+'actions/artifacts/'+str(aid)]))
 assert meta['workflow_run']['id']==43629920068 and meta['workflow_run']['head_sha']=='d25b831d07ae9f3444fec0b78656bcd5c02bee37' and meta['digest']=='sha256:'+digest
 path=Path(str(aid)+'.zip')
 with path.open('xb') as f:subprocess.run(['gh','api',P+'actions/artifacts/'+str(aid)+'/zip'],stdout=f,check=True)
 assert hashlib.sha256(path.read_bytes()).hexdigest()==digest
 return zipfile.ZipFile(path)
native=acquire(14127781771,'edf8aa0e2ae849e0c45588d999e59a5d78948fe2241ef1c6b6518815f3cdb647')
safe=acquire(14128116163,'d4b08cdd44fcba4003dba77f8867e3f80115e778e176e766de6113dbcab4226f')
result={'source_run':43629920068,'source_head':'d25b831d07ae9f3444fec0b78656bcd5c02bee37','cases':{}}
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
