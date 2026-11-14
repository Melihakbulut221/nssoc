# SPDX-License-Identifier: Apache-2.0
"""Prepare exact completed CRC route for namespaced SRAM streamout in cloud."""
import pathlib,json,zipfile,tarfile,io,hashlib,copy,os,shutil
P=pathlib.Path;root=P.cwd();assert os.environ.get('GITHUB_ACTIONS')=='true'
def sha(path):
 with P(path).open('rb') as f:return hashlib.file_digest(f,'sha256').hexdigest()
assert sha('routed.zip')=='0c61942e79e1c94aceedd757e5d4cc298af6cbbe90480612c72bfed2fcbf18b0'
assert sha('library.zip')=='647008a959be8601aeb762f5ba238c7864ad0bcde0ef807f3e1dcae3324d8d25'
assert sha('/mnt/s/pkg.tgz')=='822dab7067d901fa79dabffffff784baf5c9965f0a5091eba67acdc48b9956f4'
# Two sequential passes avoid repeated gzip rewinds; every written input verified.
import time
began=time.monotonic();contract=None
with tarfile.open('/mnt/s/pkg.tgz','r|gz') as t:
 for m in t:
  if m.isfile() and m.name.endswith('/input-contract.json'):
   assert contract is None;contract=json.loads(t.extractfile(m).read());prefix=str(P(m.name).parent)+'/files/'
assert contract is not None
expected={prefix+name:(name,row) for name,row in contract['input_files'].items()};restored={};total=0
with tarfile.open('/mnt/s/pkg.tgz','r|gz') as t:
 for m in t:
  if m.name not in expected:continue
  assert m.isfile();name,row=expected[m.name];rel=P(name);assert not rel.is_absolute() and '..' not in rel.parts and name not in restored
  dest=root/rel;dest.parent.mkdir(parents=True,exist_ok=True);digest=hashlib.sha256();size=0
  with t.extractfile(m) as src,dest.open('wb') as dst:
   while True:
    data=src.read(1024*1024)
    if not data:break
    digest.update(data);dst.write(data);size+=len(data)
  actual=digest.hexdigest();assert actual==row['sha256'] and size==m.size and sha(dest)==actual
  restored[name]=actual;total+=size
assert restored=={name:row['sha256'] for name,row in contract['input_files'].items()}
manifest_hash=hashlib.sha256(json.dumps(restored,sort_keys=True).encode()).hexdigest()
assert manifest_hash=='fe773024abb77b2c184be52ca26eb1028eba228e0a784cfdd78f4175e92f98d0' and len(restored)==5030 and total==1173231506
restore_proof={'method':'two sequential gzip passes','seconds':time.monotonic()-began,'files':len(restored),'bytes':total,'written_file_manifest_sha256':manifest_hash,'all_written_hashes_verified':True,'qualification_run':43598890723}
print(json.dumps(restore_proof),flush=True)
z=zipfile.ZipFile('routed.zip');names=[n for n in z.namelist() if n.endswith('routed.tgz')];assert len(names)==1
with z.open(names[0]) as src,open('/mnt/s/routed.tgz','wb') as dst:shutil.copyfileobj(src,dst,1024*1024)
with tarfile.open('/mnt/s/routed.tgz','r:gz') as t:
 for m in t.getmembers():
  dest=P('/')/m.name;assert dest.resolve().is_relative_to(root) and (m.isfile() or m.isdir())
 t.extractall('/',filter='data')
config_path=root/'hw/soc/out/impl-probe/prepared/config-routed.json';state_path=root/'hw/soc/out/impl-probe/routed-state.json'
original=json.loads(config_path.read_text());state=json.loads(state_path.read_text());changed=copy.deepcopy(original)
lib=root/'hw/soc/out/namespaced-sram-library';lib.mkdir(parents=True,exist_ok=False)
z=zipfile.ZipFile('library.zip')
for name in z.namelist():
 rel=P(name);assert not rel.is_absolute() and '..' not in rel.parts and len(rel.parts)==1
 (lib/rel).write_bytes(z.read(name))
manifest=json.loads((lib/'manifest.json').read_text());assert manifest['status']=='COLLISION_FREE_MACRO_LIBRARY_BUNDLE'
for name,row in manifest['files'].items():assert sha(lib/name)==row['sha256']
macro_changes={}
for kind,top,original_hash in [('dp','RM_IHPSG13_2P_256x16_c2_bm_bist','420b5223d14e2f873a2464849e3decbbec2b5b16b3c6a0f8cd2bb21b0d52365b'),('sp','RM_IHPSG13_1P_2048x64_c2_bm_bist','48be5102bf97e56daee4cda1f63eaf6e7bb3450a68d48a2825060b1172011d00')]:
 macro=changed['MACROS'][top];before=macro['gds'];assert isinstance(before,list) and len(before)==1 and sha(before[0])==original_hash
 replacement=[str(lib/(kind+'.gds'))];macro['gds']=replacement
 macro_changes[top]={'original_gds':before,'original_sha256':original_hash,'replacement_gds':replacement,'replacement_sha256':sha(replacement[0]),'instances':len(macro.get('instances',{}))}
undo=copy.deepcopy(changed)
for top,row in macro_changes.items():undo['MACROS'][top]['gds']=row['original_gds']
assert undo==original,'Non-GDS configuration field changed'
views={}
def collect(v):
 if isinstance(v,str) and P(v).is_absolute():
  assert P(v).is_file();views[v]={'bytes':P(v).stat().st_size,'sha256':sha(v)}
 elif isinstance(v,dict):
  for x in v.values():collect(x)
 elif isinstance(v,list):
  for x in v:collect(x)
for key,val in state.items():
 if key!='metrics':collect(val)
assert state.get('odb') and state.get('def'),'Exact completed routed ODB/DEF required'
assert any(state.get(k) for k in ['nl','pnl']),'Independent logical netlist view required for subsequent full-chip schematic'
out=root/'hw/soc/out/namespaced-streamout';out.mkdir(parents=True,exist_ok=False)
(out/'config.json').write_text(json.dumps(changed,indent=2));(out/'state.json').write_text(json.dumps(state,indent=2))
proof={'status':'PREPARED_COHERENT_ROUTED_STREAMOUT','restore':restore_proof,'source_route_run':43579643337,'source_route_native':14111958544,'original_config_sha256':sha(config_path),'candidate_config_sha256':sha(out/'config.json'),'state_sha256':sha(state_path),'macro_gds_changes':macro_changes,'all_other_configuration_fields_unchanged':True,'input_views':views,'state_view_keys':sorted(k for k in state if k!='metrics'),'source_metrics':state.get('metrics',{}),'full_chip_lvs_passed':False,'final_timing_complete':False,'manufacturing_approval':False,'scope':'Streamout qualification on prior completed CRC route, whose antenna/timing gates failed. Separate current legalized-diode route is untouched. Not a production candidate acceptance.'}
(out/'preflight.json').write_text(json.dumps(proof,indent=2));print(json.dumps({'status':proof['status'],'state_view_keys':proof['state_view_keys'],'macros':macro_changes}))
