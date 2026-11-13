# SPDX-License-Identifier: Apache-2.0
import hashlib,json,pathlib,tarfile,zipfile
out=pathlib.Path('out');out.mkdir(exist_ok=True)
r={'status':'ERROR','full_chip_lvs':False,'manufacturing_approval':False,'scope':'Inventory and byte identity of package SRAM GDS and routed configuration paths. No inferred geometry equivalence from filenames.'}
def digest(p):
 with open(p,'rb') as f:return hashlib.file_digest(f,'sha256').hexdigest()
try:
 assert digest('pkg.tgz')=='822dab7067d901fa79dabffffff784baf5c9965f0a5091eba67acdc48b9956f4'
 assert digest('routed.zip')=='cf6a83685c33cdf4083786f0ab136ef1ea2666b44476521228aed5eed73d0855'
 with zipfile.ZipFile('routed.zip') as z:
  names=[n for n in z.namelist() if n.endswith('routed.tgz')];assert len(names)==1
  with z.open(names[0]) as stream, open('routed.tgz','wb') as f:
   import shutil;shutil.copyfileobj(stream,f)
 with tarfile.open('routed.tgz','r:gz') as t:
  members=[m for m in t if m.isfile() and m.name.endswith('/prepared/config-routed.json')];assert len(members)==1
  raw=t.extractfile(members[0]).read();config=json.loads(raw);r['routed_config_sha256']=hashlib.sha256(raw).hexdigest()
  macros=config.get('MACROS',{});r['routed_macros']={name:{k:v for k,v in val.items() if k in ['gds','lef','instances']} for name,val in macros.items()}
  r['routed_extra_gds']=config.get('EXTRA_GDS_FILES',[])
 with tarfile.open('pkg.tgz','r:gz') as t:
  members=t.getmembers();contracts=[m for m in members if m.isfile() and m.name.endswith('/input-contract.json')];assert len(contracts)==1
  contract=json.loads(t.extractfile(contracts[0]).read());prefix=str(pathlib.PurePosixPath(contracts[0].name).parent)+'/files/'
  indexed={m.name:m for m in members};records=[]
  for name,info in contract['input_files'].items():
   if not name.lower().endswith('.gds') or not any(x in name.lower() for x in ['sram','dp8t','rm_ihp']):continue
   member=indexed[prefix+name]
   with t.extractfile(member) as f:actual=hashlib.file_digest(f,'sha256').hexdigest()
   assert actual==info['sha256']
   records.append({'path':name,'sha256':actual,'bytes':member.size,'identical_to_verified_dp_gds':actual=='c6a1be71d0439e88e2c08729345eb8d8001f773266cb7a8b939446e54999ff45'})
  r['package_sram_gds']=records
 assert r['package_sram_gds'],'no SRAM geometry in package inventory'
 r['status']='INVENTORIED_PACKAGE_SRAM_AND_ROUTED_PATHS'
except Exception as e:r['error']=type(e).__name__+': '+str(e)
(out/'geometry-binding-inventory.json').write_text(json.dumps(r,indent=2));print(json.dumps(r));raise SystemExit(0 if r['status'].startswith('INVENTORIED_') else 1)
