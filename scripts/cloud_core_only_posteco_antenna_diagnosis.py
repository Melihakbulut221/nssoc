#!/usr/bin/env python3
"""Inspect authenticated failed antenna candidate without modifying the ODB."""
import os,json,subprocess,zipfile,io,hashlib,re,stat
from pathlib import Path
from bootstrap_flow import verify
ROOT=Path(__file__).resolve().parents[1]
OUT=ROOT/'hw/soc/out/core-only-posteco-antenna-diagnosis'
def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def api(path):return json.loads(subprocess.check_output(['gh','api','repos/Melihakbulut221/nssoc/'+path]))
def main():
 assert os.environ.get('GITHUB_ACTIONS')=='true';OUT.mkdir(parents=True,exist_ok=False)
 r=dict(source_head=os.environ['GITHUB_SHA'],accepted=False,status='PREPARING',modified_database=False)
 try:
  run=api('actions/runs/44337630426');assert run['status']=='completed'and run['conclusion']=='failure'and run['head_sha']=='19924a826cfca054f30f19cdde091fbe6c744960'and run['run_attempt']==1
  meta=api('actions/artifacts/14463371089');digest='cd3c228a0ec3cb5a901b5da88ae20c8af1112c3ce1daf7a607fcb80327f11ce3';assert meta['digest']=='sha256:'+digest and meta['workflow_run']['id']==run['id']
  raw=subprocess.check_output(['gh','api','repos/Melihakbulut221/nssoc/actions/artifacts/14463371089/zip']);assert hashlib.sha256(raw).hexdigest()==digest
  z=zipfile.ZipFile(io.BytesIO(raw));source=json.loads(z.read('result.json'));assert source['source_head']==run['head_sha']and source['returncode']==0 and source['status']=='FAIL_OR_INCOMPLETE'
  base=Path(os.environ['RUNNER_TEMP'])/'posteco-antenna-input';base.mkdir();seen=set()
  for item in z.infolist():
   if item.is_dir()or item.filename=='result.json':continue
   name=item.filename;assert not Path(name).is_absolute()and '..'not in Path(name).parts and not stat.S_ISLNK(item.external_attr>>16)and name not in seen
   data=z.read(item);assert hashlib.sha256(data).hexdigest()==source['outputs'][name];p=base/name;p.parent.mkdir(parents=True,exist_ok=True);p.write_bytes(data);seen.add(name)
  assert seen==set(source['outputs'])
  assert source['routing_metrics']['values']['route__drc_errors']==0
  assert source['antenna_metrics']['values']['antenna__violating__nets']==363 and source['antenna_metrics']['values']['antenna__violating__pins']==399
  r['source_admission']=dict(run=run['id'],head=run['head_sha'],artifact=meta['id'],sha256=digest,verified_outputs=len(seen),routing_metrics=source['routing_metrics'],antenna_metrics=source['antenna_metrics'],identity=source['route_identity'],geometry=source['visible_geometry'])
  odb=base/'routing/1-nssoc-coreonlydetailedrouting/soc_top.odb';assert sha(odb)=='9f437215e21f8004390ba0bcfac397a6b9113fb1ab38e2a7abe4600e0f99f6b3'
  for name in ['antenna.rpt','antenna_summary.rpt']:(OUT/name).write_bytes((base/'routing/2-openroad-checkantennas/reports'/name).read_bytes())
  t=(OUT/'antenna.rpt').read_text();net=None;pin=None;layer=None;violations=[]
  for line in t.splitlines():
   if line.startswith('Net: '):net=line[5:].strip()
   elif line.strip().startswith('Pin:'):pin=line.strip()[4:].strip()
   elif line.strip().startswith('Layer:'):layer=line.strip()[6:].strip()
   elif '(VIOLATED)'in line:violations.append(dict(net=net,pin=pin,layer=layer,rule=line.strip()))
  assert len({v['net']for v in violations})==363 and len({(v['net'],v['pin'])for v in violations})==399
  r['violations']=violations;r['layers']={layer:sum(v['layer']==layer for v in violations)for layer in sorted({v['layer']for v in violations})}
  (OUT/'routing-config.json').write_bytes((base/'route-config.json').read_bytes())
  native_files=[p for p in base.rglob('*.tcl')if 'core_only_propagated_native'in p.name or 'clean_orphan_guides_drt'in p.name]
  for i,p in enumerate(native_files):(OUT/(str(i)+'-'+p.name)).write_bytes(p.read_bytes())
  probe=OUT/'native-commands.tcl';probe.write_text('foreach command {repair_antennas detailed_route global_route check_antennas set_routing_layers} { puts "NSSOC_COMMAND $command"; help $command }\nread_db $::env(NSSOC_DIAG_ODB)\nputs "NSSOC_DB_INSTANCES [llength [[ord::get_db_block] getInsts]]"\nputs "NSSOC_READ_ONLY_PROBE_COMPLETE"\n')
  app=Path(os.environ['CLOUD_APPIMAGE']);verify(app,'x86_64');protected={str(p):sha(p)for p in [Path(__file__),probe,odb]};r['protected_inputs']=protected
  with (OUT/'native-commands.log').open('w')as log:proc=subprocess.run([str(app),'openroad','-exit',str(probe)],env=dict(os.environ,NSSOC_DIAG_ODB=str(odb)),stdout=log,stderr=subprocess.STDOUT)
  text=(OUT/'native-commands.log').read_text();assert proc.returncode==0 and 'NSSOC_DB_INSTANCES 105251'in text and 'NSSOC_READ_ONLY_PROBE_COMPLETE'in text
  assert all(sha(p)==h for p,h in protected.items())
  r.update(status='ANTENNA_FAILURE_INSPECTED_REQUIRES_REPAIR_AND_SIGNOFF',sources_unchanged=True)
 except BaseException as error:r.update(status='FAIL_OR_INCOMPLETE',error=repr(error));raise
 finally:
  r['outputs']={str(p.relative_to(OUT)):sha(p)for p in OUT.rglob('*')if p.is_file()and p!=OUT/'result.json'}
  (OUT/'result.json').write_text(json.dumps(r,indent=2)+'\n')
if __name__=='__main__':main()
