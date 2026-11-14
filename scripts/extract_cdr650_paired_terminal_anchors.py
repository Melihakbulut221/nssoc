import hashlib,json,os,pathlib,subprocess,zipfile,traceback
import cdr_mos650_identity as identity
import cdr_mos650_wires as wire
ROOT=pathlib.Path.cwd();OUT=ROOT/'paired-terminal-anchors';NATIVE=OUT/'native';DERIVED=OUT/'derived'
for module in (identity,wire):module.OUT=OUT;module.NATIVE=NATIVE;module.DERIVED=DERIVED
TOP=identity.TOP;PINS='scripts/cdr650-paired-anchors-pins.json'
def gate():
 assert os.environ['GITHUB_ACTIONS']=='true' and os.environ['RUNNER_ENVIRONMENT']=='github-hosted'
 assert os.environ['GITHUB_REPOSITORY']=='Melihakbulut221/nssoc' and os.environ['GITHUB_REF']=='refs/heads/codex/packed650-terminal-anchors'
 assert os.environ['GITHUB_EVENT_NAME']=='workflow_dispatch' and os.environ['GITHUB_RUN_ATTEMPT']=='1'
 assert subprocess.check_output(['git','rev-parse','HEAD'],text=True).strip()==os.environ['GITHUB_SHA']
 for name,record in json.loads((ROOT/PINS).read_text())['files'].items():assert identity.pin(ROOT/name)==record,name
 return {'run':int(os.environ['GITHUB_RUN_ID']),'source':os.environ['GITHUB_SHA']}
def archive(aid,digest,run,source):
 meta=identity.api('actions/artifacts/'+str(aid));assert meta['workflow_run']['id']==run and meta['workflow_run']['head_sha']==source and not meta['expired'] and meta['digest']=='sha256:'+digest
 path=NATIVE/(str(aid)+'.zip')
 with path.open('xb')as f:subprocess.run(['gh','api','repos/Melihakbulut221/nssoc/actions/artifacts/'+str(aid)+'/zip'],stdout=f,check=True)
 assert identity.pin(path)['sha256']==digest
 return zipfile.ZipFile(path)
def main():
 context=gate();DERIVED.mkdir(parents=True);NATIVE.mkdir()
 try:
  run=identity.api('actions/runs/43640446032');assert run['head_sha']=='4a72ade2fe5f938f1a1438c08c35b6f9c38c2f95' and run['status']=='completed' and run['conclusion']=='success'
  native=archive(14131638321,'2b3fb4f7f941846e2a2f69953e5be309129e8e5f1870252b3ce822e3ffb62dad',43640446032,run['head_sha'])
  safe=archive(14132415076,'4969908bb9422d864bb5ff3d17a2e61928a6f3f2a3f267904819a160f1159c59',43640446032,run['head_sha'])
  previous=json.loads(safe.read('result.json'));assert previous['devices']==650 and previous['terminals']==2046 and previous['ports']==25 and not previous['old_RC_reused']
  assert len(set(native.namelist()))==len(native.namelist())
  for name in native.namelist():
   if not name.startswith('selected/'):continue
   part=pathlib.PurePosixPath(name);assert not part.is_absolute() and '..' not in part.parts
   info=native.getinfo(name);assert not info.is_dir() and (info.external_attr>>16)&0o170000!=0o120000
   dest=NATIVE/name;dest.parent.mkdir(parents=True,exist_ok=True);dest.write_bytes(native.read(name))
  flat=json.loads(safe.read('lvs_flat-identity.json'));identity.validate(flat,identity.expected())
  assert identity.pin(NATIVE/'selected/physical/lvs_flat/result.lvsdb')==flat['lvsdb']
  assert identity.pin(NATIVE/'selected/layout'/(TOP+'.gds'))['sha256']==previous['gds_sha256']=='ecae8ae8e49beea391b1d2575da6f5ac9ea01180550ae65fc786ddc6fd9ee193'
  gen=archive(14131740193,'89585c334b2ae7f06b21e6851babe72ec11b5d1b4e0bee675c79090129193057',43639421390,'dbe212de5ae00036284f104d45742db443186f51')
  proof=archive(14130989352,'590ee5edefb5e0de9a0997fc8d92a06513e601670b045fbb8e0a2d4187e9de98',43639421390,'dbe212de5ae00036284f104d45742db443186f51')
  assert gen.read('candidate.gds')==(NATIVE/'selected/layout'/(TOP+'.gds')).read_bytes()
  (NATIVE/'baseline.gds').write_bytes(gen.read('source.gds'));(NATIVE/'paired-layout-proof.json').write_bytes(proof.read('paired-layout-proof.json'))
  cfg=identity.read(ROOT/'scripts/cdr-mos650-wires-inputs.json');old=wire.fetch_old_pins(cfg)
  import cdr650_paired_pin_provenance as provenance
  provenance.source_pins(cfg,flat,old)
  folder=wire.prepare_workers()
  for name in native.namelist():
   if not name.startswith('view/wire/native05/'):continue
   part=pathlib.PurePosixPath(name);assert '..'not in part.parts
   dest=NATIVE/name;dest.parent.mkdir(parents=True,exist_ok=True);dest.write_bytes(native.read(name))
  graph=identity.read(folder/'native05/result.json');assert graph==json.loads(safe.read('wire-graph.json'))
  for name,record in graph['outputs'].items():assert identity.pin(folder/'native05'/name)==record
  for name in ('locate01.py','anchors01.py','dedup01.py'):wire.run_worker(folder,name)
  locations=identity.read(folder/'device-locations01.json');anchors=identity.read(folder/'anchors03.json')
  wire.validate_binding(graph,locations,anchors,flat);wire.native_material_and_anchors(folder,flat);wire.fault_controls(graph,locations,anchors,flat)
  for name,source in [('device-locations.json','device-locations01.json'),('terminal-anchors.json','anchors03.json'),('unique-anchors.json','anchors08.json')]:identity.save(name,identity.read(folder/source))
  gate();identity.save('result.json',dict(status='PASS_PAIRED650_CURRENT_TERMINAL_AND_GATE_CONTACT_ANCHORS_REQUIRES_FRESH_RC',context=context,devices=650,terminals=2046,physical_anchors=len(anchors['anchors']),gate_contacts=anchors['physical_gate_contact_count'],source_graph_run=43640446032,gds_sha256=previous['gds_sha256'],old_RC_reused=False,wire_rc_extracted=False,full_phy_accepted=False,final_timing_complete=False))
 except BaseException as exc:
  identity.save('failure.json',{'error':repr(exc),'traceback':traceback.format_exc(),'full_phy_accepted':False});raise
if __name__=='__main__':main()
