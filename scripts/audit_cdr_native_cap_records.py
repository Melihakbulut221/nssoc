"""Read native Magic capacitance and anchor records on hosted runner only."""
import hashlib,json,pathlib,tarfile,shlex
h=hashlib.sha256()
with open('metal.tgz','rb') as f:
 for b in iter(lambda:f.read(1048576),b''):h.update(b)
assert h.hexdigest()=='09c2185efebbdb7e60c0457d62c175d98d7bffca35e60bfe7c3f179f62ebbfb6'
targets=['T382_rppd_2','T383_rppd_2','T397_rppd_2','T398_rppd_2'];out={'accepted':False,'archive_sha256':h.hexdigest(),'scope':'Native extraction records and anchor provenance, not qualified capacitance or changed circuit','members':[],'records':{},'json_reports':{}}
def small(x,depth=0):
 if depth>4:return {'kind':type(x).__name__,'length':len(x) if hasattr(x,'__len__') else None}
 if isinstance(x,dict):return {k:small(v,depth+1) for k,v in list(x.items())[:50]}
 if isinstance(x,list):return {'length':len(x),'first': [small(v,depth+1) for v in x[:5]]}
 return x
with tarfile.open('metal.tgz','r|gz') as tar:
 for member in tar:
  n=member.name
  if '/mim-precise/' not in n:continue
  if n.endswith(('.ext','.json','.tech','.py')):out['members'].append({'name':n,'size':member.size})
  if n.endswith('.ext'):
   rows=[];counts={};matches=0
   for raw in tar.extractfile(member):
    line=raw.decode();tok=line.split();key=tok[0] if tok else ''
    counts[key]=counts.get(key,0)+1
    if any(t in line for t in targets):
     matches+=1
     if len(rows)<100:rows.append(line.rstrip())
   out['records'][n]={'record_counts':counts,'matching_count':matches,'first_100_matching':rows}
  if n.endswith('anchors08.json'):
   raw=tar.extractfile(member).read();d=json.loads(raw)
   out['json_reports'][n]={'sha256':hashlib.sha256(raw).hexdigest(),'keys':list(d),'selected_anchors':[r for r in d['anchors'] if any(t in json.dumps(r) for t in targets)]}
  if n.endswith('mim-audit.json'):
   raw=tar.extractfile(member).read();out['json_reports'][n]={'sha256':hashlib.sha256(raw).hexdigest(),'summary':small(json.loads(raw))}
assert out['records'] and out['json_reports']
pathlib.Path('out').mkdir();pathlib.Path('out/capacitor-native-records.json').write_text(json.dumps(out,indent=2))
