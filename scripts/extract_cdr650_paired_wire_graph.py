import hashlib,json,os,pathlib,subprocess,zipfile,traceback
import cdr_mos650_identity as identity
ROOT=pathlib.Path.cwd();OUT=ROOT/'paired-wire-graph';NATIVE=OUT/'native';DERIVED=OUT/'derived'
identity.OUT=OUT;identity.NATIVE=NATIVE;identity.DERIVED=DERIVED
identity.CFG='scripts/cdr-mos650-wires-inputs.json'
TOP=identity.TOP
PINS='scripts/cdr650-paired-wire-pins.json'
def gate():
 assert os.environ['GITHUB_ACTIONS']=='true' and os.environ['RUNNER_ENVIRONMENT']=='github-hosted'
 assert os.environ['GITHUB_REPOSITORY']=='Melihakbulut221/nssoc' and os.environ['GITHUB_REF']=='refs/heads/codex/cdr650-paired-wire-graph'
 assert os.environ['GITHUB_EVENT_NAME']=='workflow_dispatch' and os.environ['GITHUB_RUN_ATTEMPT']=='1'
 assert subprocess.check_output(['git','rev-parse','HEAD'],text=True).strip()==os.environ['GITHUB_SHA']
 for name,record in json.loads((ROOT/PINS).read_text())['files'].items():assert identity.pin(ROOT/name)==record,name
 return {'run':int(os.environ['GITHUB_RUN_ID']),'source':os.environ['GITHUB_SHA']}
def main():
 context=gate();DERIVED.mkdir(parents=True);NATIVE.mkdir()
 try:
  run=identity.api('actions/runs/43622190993');assert run['head_sha']=='8274b540b6223e6a9bd2c7aa7b3d2c5046b09a7f' and run['status']=='completed' and run['conclusion']=='success' and run['run_attempt']==1
  meta=identity.api('actions/artifacts/14124657803');assert meta['workflow_run']['id']==43622190993 and not meta['expired'] and meta['digest']=='sha256:bf981a5887f0fd69167f41e1ce6b8065662202d1fe9f8b2de201df210eb408ec'
  packed=NATIVE/'physical.zip'
  with packed.open('xb')as f:subprocess.run(['gh','api','repos/Melihakbulut221/nssoc/actions/artifacts/14124657803/zip'],stdout=f,check=True)
  assert identity.pin(packed)['sha256']=='bf981a5887f0fd69167f41e1ce6b8065662202d1fe9f8b2de201df210eb408ec'
  selected=NATIVE/'selected';prefix='hw/soc/out/cloud-cdr-wire-shortcuts-physical/'
  wanted=['layout/'+TOP+'.gds','layout/'+TOP+'.lef','layout/schematic.cir','layout/result.json','physical/result.json']
  wanted += ['physical/'+m+'/'+n for m in ['lvs','lvs_flat'] for n in ['result.lvsdb','deck.log','audit.json']]
  with zipfile.ZipFile(packed)as z:
   assert len(set(z.namelist()))==len(z.namelist())
   for name in wanted:
    key=prefix+name;assert key in z.namelist(),key
    info=z.getinfo(key);assert not info.is_dir() and (info.external_attr>>16)&0o170000!=0o120000
    dest=selected/name;dest.parent.mkdir(parents=True,exist_ok=True);dest.write_bytes(z.read(key))
  assert identity.pin(selected/'physical/result.json')['sha256']=='7fec2657806b39de1cf96815f469787aa66934e7b7f004755cbbbb071ac654bf'
  report=identity.read(selected/'physical/result.json');assert report['status']=='PASS_NATIVE_PDK_CDR_PD650_DRC_LVS_AND_FAULT_CONTROLS' and len(report['steps'])==16
  for name,row in report['steps'].items():assert row['status']==('PASS' if name in ['drc','lvs','lvs_flat'] else 'REJECTED_EXPECTED_FAULT')
  assert report['steps']['drc']['measurement']['category_count']==560 and report['steps']['drc']['measurement']['markers']==0
  for name in wanted:
   path=selected/name
   if name.startswith('layout/'):
    key='/home/runner/work/nssoc/nssoc/'+prefix+name;assert identity.pin(path)['sha256']==report['inputs'][key]
  for mode in ['lvs','lvs_flat']:
   for n in ['result.lvsdb','deck.log']:
    key='/home/runner/work/nssoc/nssoc/'+prefix+'physical/'+mode+'/'+n
    assert identity.pin(selected/'physical'/mode/n)==report['steps'][mode]['audit']['inputs'][key]
  assert identity.pin(selected/'layout'/ (TOP+'.gds'))['sha256']=='285760f3930a1cc142b45a3c43866202f1ea4694f468fb1603f286cb546cd514'
  expected=identity.expected();deep=identity.native_side('lvs',expected);flat=identity.native_side('lvs_flat',expected)
  # Extract the fresh actual metal/via connectivity, with complete native-LVS
  # geometric ownership checks. No former geometry/RC view is substituted.
  parent=NATIVE/'view/parent';wire=NATIVE/'view/wire';wire.mkdir(parents=True)
  for name in ['layout/'+TOP+'.gds','layout/result.json','physical/lvs_flat/result.lvsdb','physical/lvs_flat/audit.json']:
   dest=parent/name;dest.parent.mkdir(parents=True,exist_ok=True);dest.write_bytes((selected/name).read_bytes())
  original=ROOT/'docs/evidence/cdr-v59-tail-exact-wire-methods-20261026/probe01.py';text=original.read_text();assert text.count('sg13_lv_nmos=50')==1
  worker=wire/'probe01.py';worker.write_text(text.replace('sg13_lv_nmos=50','sg13_lv_nmos=200'))
  with (DERIVED/'probe.stdout').open('wb')as so,(DERIVED/'probe.stderr').open('wb')as se:
   code=subprocess.run([os.sys.executable,'-B',str(worker)],stdout=so,stderr=se,timeout=900).returncode
  assert code==0,'Fresh native conductor extraction failed'
  graph=identity.read(wire/'native05/result.json');assert graph['native_device_count']==650 and graph['native_terminal_count']==2046 and len(graph['native_ports'])==25 and graph['no_wire_geometry_change'] and graph['no_component_union_by_native_label']
  identity.save('wire-graph.json',graph)
  gate();identity.save('result.json',dict(status='PASS_PAIRED650_NATIVE_IDENTITIES_AND_FRESH_METAL_GRAPH_REQUIRES_TERMINAL_ANCHORS_AND_RC',context=context,devices=650,terminals=2046,ports=25,components=graph['wire_component_count'],source_physical_run=43622190993,gds_sha256=identity.pin(selected/'layout'/(TOP+'.gds'))['sha256'],old_RC_reused=False,wire_rc_extracted=False,full_phy_accepted=False,final_timing_complete=False,worker_source=identity.pin(original),worker_derived=identity.pin(worker)))
 except BaseException as exc:
  identity.save('failure.json',{'error':repr(exc),'traceback':traceback.format_exc(),'full_phy_accepted':False});raise
if __name__=='__main__':main()
