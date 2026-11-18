#!/usr/bin/env python3
import json,os,subprocess,hashlib,zipfile,io
from pathlib import Path
from bootstrap_flow import verify
ROOT=Path(__file__).resolve().parents[1];OUT=ROOT/'hw/soc/out/core-only-antenna-power-contact'
def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def api(p):return json.loads(subprocess.check_output(['gh','api','repos/Melihakbulut221/nssoc/'+p]))
def main():
 assert os.environ.get('GITHUB_ACTIONS')=='true';OUT.mkdir(parents=True,exist_ok=False);r=dict(source_head=os.environ['GITHUB_SHA'],accepted=False,status='PREPARING')
 try:
  run=api('actions/runs/44382891924');assert run['conclusion']=='success'and run['head_sha']=='508bb46d0366363d7e79a001ab8a68b230f4fd96'and run['run_attempt']==1
  digest='d5864cb7b9575155444b2ca063010f889c9203ab7bf1a8867b86dba19254c4b3';meta=api('actions/artifacts/14464567635');assert meta['digest']=='sha256:'+digest and meta['workflow_run']['id']==run['id']
  raw=subprocess.check_output(['gh','api','repos/Melihakbulut221/nssoc/actions/artifacts/14464567635/zip']);assert hashlib.sha256(raw).hexdigest()==digest
  z=zipfile.ZipFile(io.BytesIO(raw));prefix='core-only-posteco-antenna-reaudit/';src=json.loads(z.read(prefix+'result.json'));assert src['sources_unchanged']and src['status']=='DIODES_INSERTED_AND_IDENTITY_AUDITED_REQUIRES_DETAILED_ROUTING_AND_SIGNOFF'
  for n,h in src['outputs'].items():assert hashlib.sha256(z.read(prefix+n)).hexdigest()==h
  tmp=Path(os.environ['RUNNER_TEMP'])/'antenna-power-contact';tmp.mkdir();odb=tmp/'candidate.odb';odb.write_bytes(z.read(prefix+'core-antennas-inserted-unrouted.odb'));assert sha(odb)=='2147b6df67feac28691ca76defdd7d3cafd4df1c00a74c0043fcd55f47767750'
  inv=tmp/'inventory.json';inv.write_bytes(z.read(prefix+'insertion-audit.json'));script=ROOT/'scripts/audit_antenna_power_contact.py';protected={str(p):sha(p)for p in [Path(__file__),script,inv,odb]}
  r.update(protected_inputs=protected,source_admission=dict(run=run['id'],artifact=meta['id'],digest=digest,verified_outputs=len(src['outputs'])))
  app=Path(os.environ['CLOUD_APPIMAGE']);verify(app,'x86_64')
  with (OUT/'native.log').open('w')as log:proc=subprocess.run([str(app),'openroad','-exit','-python',str(script)],env=dict(os.environ,ANTENNA_POWER_ODB=str(odb),ANTENNA_POWER_REPORT=str(OUT/'power-contact.json'),ANTENNA_POWER_INVENTORY=str(inv)),stdout=log,stderr=subprocess.STDOUT)
  r['returncode']=proc.returncode;assert proc.returncode==0
  assert all(sha(p)==h for p,h in protected.items());r.update(status='ADDED_DIODE_LOCAL_POWER_CONTACT_VERIFIED_NOT_FULL_PDN_SIGNOFF',sources_unchanged=True)
 except BaseException as e:r.update(status='FAIL_OR_INCOMPLETE',error=repr(e));raise
 finally:r['outputs']={str(p.relative_to(OUT)):sha(p)for p in OUT.rglob('*')if p.is_file()and p!=OUT/'result.json'};(OUT/'result.json').write_text(json.dumps(r,indent=2)+'\n')
if __name__=='__main__':main()
