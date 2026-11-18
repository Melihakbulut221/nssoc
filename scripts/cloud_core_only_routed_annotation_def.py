#!/usr/bin/env python3
"""Reclassify verified extracted core evidence without rerunning RCX or STA."""
import os,json,hashlib,subprocess
from pathlib import Path
from bootstrap_flow import verify
from cloud_core_only_postgrt import ROOT,sha,completed,archive,current_path,restore_mapping,restore_cts,qualify_sources
from cloud_core_only_clock_probe import restore_cts8
from cloud_core_only_clock_refine import restore_clock_split,restore_previous
from cloud_core_only_detailed_route import restore_refinement
from cloud_core_only_routed_extraction import restore_route,CORNERS
OUT=ROOT/'hw/soc/out/core-only-routed-annotation-def'
def main():
 assert os.environ.get('GITHUB_ACTIONS')=='true';OUT.mkdir(parents=True,exist_ok=False)
 r=dict(source_head=os.environ['GITHUB_SHA'],status='PREPARING',accepted=False,extraction_repeated=False,timing_repeated=False)
 try:
  qualify_sources();restore_mapping();_,_,config,_=restore_cts();restore_cts8(config);restore_clock_split();restore_previous();restore_refinement();_,_,initial=restore_route()
  # This producer failed only during annotation classification, after native RCX/STA.
  from cloud_core_only_postgrt import api
  run=api('actions/runs/44303529050');assert run['status']=='completed'and run['conclusion']=='failure'and run['head_sha']=='20bedd917c6f98bf6afeea1ee991d2ca4c4f03ea'
  z,m=archive(run,'core-only-routed-extraction-native-44303529050');assert m['id']==14427169742 and m['digest']=='sha256:a3b97b431600c7b068d4e904fb587adb7ab784ada4113c2bf0988fe124f982ab'
  zz,sm=archive(run,'core-only-routed-extraction-summary-44303529050');assert sm['id']==14428375522 and sm['digest']=='sha256:074b5910799da127485928512e1fc7e4f33067ff682c02f40c8dbb4caa279031'
  assert z.read('result.json')==zz.read('result.json');producer=json.loads(z.read('result.json'))
  assert producer['returncode']==0 and producer['status']=='FAIL_OR_INCOMPLETE'and 'audit_core_only_route_annotation.py'in producer['error']
  for p,h in producer['outputs'].items():assert hashlib.sha256(z.read(p)).hexdigest()==h
  r.update(producer_artifact=m,producer_summary=sm,producer_error=producer['error'],fresh_corners=producer['fresh_corners'])
  entries=list(producer['nominal_spef_proof']['spefs'].values());assert len(entries)==1
  entry=entries[0];prefix='/hw/soc/out/core-only-routed-extraction/';rel=entry['path'].split(prefix)[1]
  spef=OUT/'soc_top.nom.spef';spef.write_bytes(z.read(rel));assert sha(spef)==entry['sha256']
  odb=current_path(json.loads(initial.read_text())['odb']);script=ROOT/'scripts/audit_core_only_route_annotation.py'
  protected={str(p):sha(p)for p in [Path(__file__),script,odb,spef]}
  app=Path(os.environ['CLOUD_APPIMAGE']);verify(app,'x86_64');r['corners']={}
  for corner in CORNERS:
   p=producer['fresh_corners'][corner];log=OUT/(corner+'.sta.log');log.write_bytes(z.read(p['sta_log']));assert sha(log)==p['sta_log_sha256'];protected[str(log)]=sha(log)
   output=OUT/(corner+'.annotation.json');manifest=OUT/(corner+'.inputs.json')
   spec={k:dict(path=str(path),sha256=sha(path))for k,path in [('odb',odb),('spef',spef),('sta_log',log)]};spec['output']=str(output);manifest.write_text(json.dumps(spec,indent=2)+'\n');protected[str(manifest)]=sha(manifest)
   with (OUT/(corner+'.audit.log')).open('w')as f:subprocess.run([str(app),'openroad','-exit','-python',str(script)],env=dict(os.environ,NSSOC_CORE_ANNOTATION_INPUTS=str(manifest)),stdout=f,stderr=subprocess.STDOUT,check=True)
   a=json.loads(output.read_text());assert a['inputs_unchanged'];r['corners'][corner]={k:v for k,v in a.items()if k!='drivers'}
  assert all(sha(p)==h for p,h in protected.items());r.update(status='SOURCE_BOUND_ANNOTATION_CLASSIFICATION_COMPLETE_NOT_COVERAGE_SIGNOFF',sources_unchanged=True,protected_inputs=protected)
 except BaseException as e:r.update(status='FAIL_OR_INCOMPLETE',error=repr(e));raise
 finally:
  r['outputs']={str(p.relative_to(OUT)):sha(p)for p in OUT.rglob('*')if p.is_file()and p.name!='result.json'}
  (OUT/'result.json').write_text(json.dumps(r,indent=2)+'\n')
if __name__=='__main__':main()
