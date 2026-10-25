#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0
"""Fresh physical/wire qualification of one isolated CDR v59 resistor arm."""
import argparse,ast,hashlib,json,os,shutil,subprocess,sys,tarfile,time,traceback
from pathlib import Path
import compare_cloud_routed_endpoints as reports
import ensure_cloud_tested_source_release as release
from run_cloud_tx_layout_repair import fetch,sha
from cloud_cdr500_input_access_v58_physical import derive
from generate_cdr500_resistor_v59 import ARMS,OLD,TOP,validate_summary
ROOT=Path(__file__).resolve().parents[1]
METHOD='scripts/cdr500-resistor-v59-physical-methods.json'
PIN='docs/evidence/cdr500-input-access-v58-physical-pass-20261024.json'
APP_SHA='d6a349ec65be11456e96c4981d35f63ca34d3c85daf79a51e1ccb907bb5d7466'
OUT=None
def identity(pin):
 run=release.api('actions/runs/'+str(pin['run']))
 assert run['id']==40096705004 and run['run_attempt']==1
 assert run['head_sha']==pin['source_head']=='9e7f3d3dd55ec452dfbb27520a73b67f5078067a'
 assert run['path']==pin['workflow']and run['status']=='completed'and run['conclusion']=='success'
 jobs=release.api('actions/runs/'+str(pin['run'])+'/attempts/1/jobs?per_page=100')
 hits=[j for j in jobs['jobs']if j['id']==120880372635]
 assert len(hits)==1 and hits[0]['name']==pin['job_name']=='native-physical-and-wires'
 assert hits[0]['status']=='completed'and hits[0]['conclusion']=='success'
 return dict(run=run['id'],attempt=1,source=run['head_sha'],job=hits[0]['id'],job_name=hits[0]['name'],conclusion='success')
def precreated(group,wait=False):
 tag,source=release.context(group,os.environ)
 for attempt in range(37 if wait else 1):
  info=release.api('releases/tags/'+tag,missing=True)
  if info is not None:return release.validate_release(info,release.api('git/ref/tags/'+tag),tag,source)
  if not wait or attempt==36:raise AssertionError('Exact-source release must be precreated')
  print('Waiting for exact-source evidence reservation before any native work',flush=True)
  time.sleep(5)
def physical_source(text,arm):
 a=ARMS[arm];targets=sorted('R'+t+'_'+n for t in a['tags']for n in a['names'])
 addition="\n    if name=='v59_old_length':\n        lines=text.splitlines(keepends=True);hits=[]\n        for i,line in enumerate(lines):\n            fields=line.split()\n            if fields and fields[0] in "+repr(targets)+":\n                assert line.count("+repr(' l='+format(a['new_length'],'g')+'u ')+")==1\n                lines[i]=line.replace("+repr(' l='+format(a['new_length'],'g')+'u ')+","+repr(' l='+format(a['old_length'],'g')+'u ')+");hits.append(fields[0])\n        assert sorted(hits)=="+repr(targets)+"\n        return ''.join(lines)\n"
 return derive(text,[
  ('nssoc_cdr_pd500_active_input_v57',TOP),
  ('def reference_fault(text, name):','def reference_fault(text, name):'+addition),
  ('            "lvs_flat",\n','            "lvs_flat",\n            "v59_old_length",\n'),
  ('if name in ("gain_gate_disconnected",','if name in ("v59_old_length", "gain_gate_disconnected",'),
 ])
def native(which):
 sys.path.insert(0,str(OUT/'methods'))
 module=__import__('cdr_v59_'+which);module.OUT=OUT;module.ROOT=ROOT
 getattr(module,'native'if which=='planes'else'recover')()
def main():
 global OUT
 p=argparse.ArgumentParser();p.add_argument('--arm',choices=ARMS,required=True)
 p.add_argument('--native',choices=('planes','recover'));p.add_argument('--source-controls',action='store_true');a=p.parse_args()
 assert os.environ.get('GITHUB_ACTIONS')=='true'
 assert os.environ['GITHUB_RUN_ATTEMPT']=='1'
 OUT=ROOT/'hw/soc/out'/('cloud-cdr500-resistor-v59-'+a.arm)
 m=json.loads((ROOT/METHOD).read_text())
 for n,h in m['protected'].items():assert sha(ROOT/n)==h,n
 if a.source_controls:
  controls=[]
  for arm in ARMS:
   original=(ROOT/'hw/soc/flow/check_pcie_cdr_sampler_active_input_v57_parent.py').read_text()
   text,edits=physical_source(original,arm);assert len(edits)==4
   assert text.count('"v59_old_length",')==2 and "'v59_old_length'"in text
   # Corrupt the actual frozen derivation anchors, not a mirror of generated code.
   for i,(before,after)in enumerate((('def reference_fault(text, name):','def wrong_name(text, name):'),
    ('            "lvs_flat",\n','            "lvs_removed",\n'),
    ('if name in ("gain_gate_disconnected",','if name in ("different_fault",'))):
    assert original.count(before)==1
    try:physical_source(original.replace(before,after),arm)
    except AssertionError:controls.append(arm+'_'+str(i))
    else:raise AssertionError('Accepted missing original fault hook')
  assert len(controls)==6
  print(json.dumps(dict(status='PASS_CDR_V59_PHYSICAL_DERIVATION_CONTROLS',controls=controls,native_executed=False)));return
 assert m['physical_authorized'] is True
 if a.native:native(a.native);return
 assert m['authorized_scope']=='ONE_ISOLATED_ARM_FULL_NATIVE_PHYSICAL_AND_WIRES_NO_RC_OR_SIMULATION'
 group='cdr500-resistor-v59-'+a.arm
 release_proof=precreated(group,wait=True)
 OUT.mkdir(parents=True,exist_ok=False);reports.OUT=OUT
 r=dict(status='RUNNING',arm=a.arm,source_head=os.environ['GITHUB_SHA'],release=release_proof,
  accepted=False,full_phy_accepted=False,qualified_pex=False,wire_rc_extracted=False,loaded_simulation_started=False)
 def save():(OUT/'result.json').write_text(json.dumps(r,indent=2)+'\n')
 def run(command,label):
  log=OUT/(label+'.log')
  with log.open('w')as f:rc=subprocess.call(list(map(str,command)),cwd=ROOT,stdout=f,stderr=subprocess.STDOUT)
  r.setdefault('commands',[]).append(dict(label=label,returncode=rc,log_sha256=sha(log)));save()
  if rc:print(log.read_text(errors='replace')[-20000:],flush=True)
  assert rc==0,(label,rc)
 save()
 try:
  pin=json.loads((ROOT/PIN).read_text());validate_summary(pin['report'])
  r['original_source_identity']=identity(pin);save()
  selected=[n for n in pin['report']['outputs']if n.startswith('parent/')or n in('wire/probe01.py','wire/locate01.py','wire/anchors01.py','wire/dedup01.py')]
  prior,proof=reports.restore_report(pin['group'],pin['run'],pin['summary_sha256'],pin['parts_sha256'],OUT/'source',selected)
  assert prior==pin['report'];validate_summary(prior);r['physical_source']=proof;save()
  app=Path(os.environ['CLOUD_APPIMAGE']);assert sha(app)==APP_SHA
  spec=json.loads((ROOT/'docs/evidence/pcie-tx-layout-cloud-input-20261013.json').read_text())
  packed=OUT/'runtime.tar.gz';fetch(spec['receipt']['url'],spec['receipt']['sha256'],packed)
  with tarfile.open(packed)as tar:tar.extractall(ROOT,filter='data')
  packed.unlink()
  runtime=json.loads((ROOT/'manifest.json').read_text())
  assert all(sha(ROOT/n)==v['sha256']for n,v in runtime['files'].items())
  assert all(sha(ROOT/n)==h for n,h in m['protected'].items())
  run([app,'python',ROOT/'scripts/generate_cdr500_resistor_v59.py','--source',OUT/'source',
   '--summary',OUT/'source/result.json','--pdk',ROOT/'pdk','--out',OUT/'parent','--arm',a.arm],'native-generation')
  parent=OUT/'parent';layout=parent/'layout'
  delta=json.loads((parent/'resistor-replacement.json').read_text());r['candidate_delta']=delta
  assert delta['arm']==a.arm and delta['specification']==ARMS[a.arm]
  assert delta['replacement_native_devices']==4 and len(delta['changed_reference_names'])==4
  assert len(delta['controls'])==9 and len(delta['bridges'])==2
  assert delta['old_native_render_matches_actual_original']
  assert delta['all_other_original_cell_material_labels_instances_preserved']and delta['all_parent_routing_and_ports_preserved']
  assert delta['no_transistor_or_external_bias_or_clock_changes']
  assert not delta['physical_accepted']and not delta['electrical_accepted']
  methods=OUT/'methods';methods.mkdir();adapt={}
  text,changes=physical_source((ROOT/'hw/soc/flow/check_pcie_cdr_sampler_active_input_v57_parent.py').read_text(),a.arm)
  (methods/'check_physical.py').write_text(text)
  adapt['check_physical.py']=dict(source='hw/soc/flow/check_pcie_cdr_sampler_active_input_v57_parent.py',
   original_sha256=sha(ROOT/'hw/soc/flow/check_pcie_cdr_sampler_active_input_v57_parent.py'),
   generated_sha256=sha(methods/'check_physical.py'),reversible_changes=changes)
  sources={
   'cdr_v59_geometry.py':('scripts/check_cdr_sampler_active_input_v57_parent_geometry.py',[('nssoc_cdr_pd500_active_input_v57',TOP)]),
   'cdr_v59_planes.py':('scripts/cloud_cdr_sampler_active_input_v57_planes.py',[('nssoc_cdr_pd500_active_input_v57',TOP),('from check_cdr_sampler_active_input_v57_parent_geometry import check','from cdr_v59_geometry import check')]),
   'cdr_v59_recover.py':('scripts/cloud_cdr_sampler_active_input_v57_wire_inputs.py',[('nssoc_cdr_pd500_active_input_v57',TOP)]),
  }
  for name,(source,edits)in sources.items():
   text,changes=derive((ROOT/source).read_text(),edits);(methods/name).write_text(text)
   adapt[name]=dict(source=source,original_sha256=sha(ROOT/source),generated_sha256=sha(methods/name),reversible_changes=changes)
  r['method_adaptations']=adapt;save()
  run([sys.executable,methods/'check_physical.py','--layout',layout,'--out',parent/'physical','--app',app],'physical')
  physical=json.loads((parent/'physical/result.json').read_text());r['physical']=physical
  assert physical['status']=='PASS_NATIVE_PDK_CDR_PD500_DRC_LVS_AND_FAULT_CONTROLS'
  drc=physical['steps']['drc']['measurement'];assert drc['category_count']==560 and drc['markers']==0 and drc['status']=='PASS'
  assert len(physical['steps'])==16
  assert physical['steps']['v59_old_length']['status']=='REJECTED_EXPECTED_FAULT'
  assert all(v['status']=='REJECTED_EXPECTED_FAULT'for n,v in physical['steps'].items()if n not in('drc','lvs','lvs_flat'))
  for mode in('lvs','lvs_flat'):
   audit=physical['steps'][mode]['audit']
   assert audit['status']=='PASS within comparison scope'and audit['circuit_status_counts']=={'Match':1}and not audit['extraction_diagnostics']
   assert audit['circuits'][0]['layout_devices_recursive']==audit['circuits'][0]['schematic_devices_recursive']==500
  save()
  run([app,'python',Path(__file__),'--arm',a.arm,'--native','planes'],'fresh-native-planes')
  r['native_planes']=json.loads((OUT/'native-planes.json').read_text())
  assert r['native_planes']['status']=='PASS_PD500_NATIVE160_PLANES_51_NETS_19_FAULTS'
  assert len(r['native_planes']['controls'])==19 and len(r['native_planes']['parent_geometry']['controls'])==5
  wire=OUT/'wire';wire.mkdir();wm={}
  for name in('probe01.py','locate01.py','anchors01.py','dedup01.py'):
   original=OUT/'source/wire'/name;assert sha(original)==prior['outputs']['wire/'+name]
   if name=='dedup01.py':text=original.read_text();changes=[]
   else:text,changes=derive(original.read_text(),[(OLD,TOP)])
   if name=='probe01.py':assert 'if not ts:assert not area and not ps and n.cluster_id not in owners'in text
   (wire/name).write_text(text);wm[name]=dict(original_sha256=sha(original),generated_sha256=sha(wire/name),changes=changes)
  r['strict_wire_method_adaptations']=wm;save()
  run([app,'python',Path(__file__),'--arm',a.arm,'--native','recover'],'source-annotation-recovery')
  for name in wm:run([app,'python',wire/name],name)
  r['strict_wire_graph']=json.loads((wire/'native05/result.json').read_text())
  r['device_locations']=json.loads((wire/'device-locations01.json').read_text())
  r['anchors']=json.loads((wire/'anchors08.json').read_text())
  assert r['strict_wire_graph']['native_device_count']==500 and r['strict_wire_graph']['native_terminal_count']==1446
  assert r['strict_wire_graph']['wire_component_count']==113
  assert r['anchors']['logical_anchor_count']==978 and r['anchors']['public_ports']==25
  assert r['anchors']['dispositions']==dict(ACTUAL_TERMINAL_METAL_POINT_REFERENCE=953,RETAINED_INTRINSIC_BODY_NO_SUBSTRATE_RESISTANCE=493)
  assert all(sha(wire/n)==v['generated_sha256']for n,v in wm.items())
  assert all(sha(methods/n)==v['generated_sha256']for n,v in adapt.items())
  assert all(sha(OUT/'source'/n)==prior['outputs'][n]for n in selected)
  assert all(sha(ROOT/n)==h for n,h in m['protected'].items())
  assert all(sha(ROOT/n)==v['sha256']for n,v in runtime['files'].items())
  r.update(status='PASS_ISOLATED_CDR_V59_FULL_PHYSICAL_AND_STRICT_WIRES_REQUIRES_FRESH_MIM_RC',sources_unchanged=True)
 except BaseException as error:
  r.update(status='FAIL_CDR_V59_NATIVE_PHYSICAL_OR_STRICT_WIRES',error=repr(error),traceback=traceback.format_exc());raise
 finally:
  for name,path in [('layout',OUT/'parent/layout/result.json'),('physical',OUT/'parent/physical/result.json'),('candidate_delta',OUT/'parent/resistor-replacement.json')]:
   if path.exists():r[name]=json.loads(path.read_text())
  r['outputs']={str(p.relative_to(OUT)):sha(p)for p in OUT.rglob('*')if p.is_file()and p!=OUT/'result.json'};save()
if __name__=='__main__':main()
