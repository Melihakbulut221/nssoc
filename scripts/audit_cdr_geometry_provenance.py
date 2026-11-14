"""Cloud-only provenance audit; no changed circuit or acceptance gates."""
import hashlib,json,zipfile,pathlib
h=hashlib.sha256()
with open('native.zip','rb') as f:
 for block in iter(lambda:f.read(1048576),b''):h.update(block)
assert h.hexdigest()=='d5e62c25486ba447781a5e4cdc12c00b303e890fb3cb51de1c8cdf77f32d1615'
def bounded(x,depth=0):
 if depth>7:return {'type':type(x).__name__,'length':len(x) if hasattr(x,'__len__') else None}
 if isinstance(x,dict):return {k:bounded(v,depth+1) for k,v in list(x.items())[:100]}
 if isinstance(x,list):return {'length':len(x),'first_items':[bounded(v,depth+1) for v in x[:12]]}
 if isinstance(x,str) and len(x)>2000:return x[:2000]+' [TRUNCATED]'
 return x
out={'accepted':False,'scope':'Read-only geometry/extraction provenance, not a simulation or PHY qualification','native_sha256':h.hexdigest(),'reports':{}}
with zipfile.ZipFile('native.zip') as z:
 for suffix in ['composition-n1/contract.json','current-wire/derived/result.json','current-wire/derived/gate-poly-access.json','gate-reduction/derived/physical-gate-port-reduction.json','derived/loaded-n1-nominal_late.json']:
  names=[n for n in z.namelist() if n.endswith(suffix)];assert len(names)==1,(suffix,names)
  raw=z.read(names[0]);data=json.loads(raw)
  if suffix.endswith('loaded-n1-nominal_late.json'):data={k:v for k,v in data.items() if k in ['protected_inputs','source_head','native_options','diagnostics','readback_controls','scope']}
  out['reports'][suffix]={'sha256':hashlib.sha256(raw).hexdigest(),'summary':bounded(data)}
 names=[n for n in z.namelist() if n.endswith('composition-n1/model.cir')];assert len(names)==1
 lines=z.read(names[0]).decode().splitlines()
 out['selected_capacitor_records']=[l for l in lines if l.split() and l.split()[0].upper() in ['C8237','C8243','C238','C8251','C823']]
 assert len(out['selected_capacitor_records'])==5
 out['geometry_members']=[{'path':i.filename,'size':i.file_size} for i in z.infolist() if i.filename.endswith(('.gds','.oas'))]
pathlib.Path('out').mkdir(exist_ok=True)
pathlib.Path('out/geometry-provenance.json').write_text(json.dumps(out,indent=2))
