#!/usr/bin/env python3
"""Qualify post-route identity guard on admitted native ECO; not routed signoff."""
import os,json,hashlib,subprocess,tempfile
from pathlib import Path
from bootstrap_flow import verify
from cloud_core_only_postgrt import ROOT,sha,completed,archive
OUT=ROOT/'hw/soc/out/core-only-route-identity-controls'
def main():
 assert os.environ.get('GITHUB_ACTIONS')=='true';OUT.mkdir(parents=True,exist_ok=False)
 r=dict(source_head=os.environ['GITHUB_SHA'],status='PREPARING',accepted=False,routed_candidate_checked=False)
 try:
  paths=[Path(__file__),ROOT/'scripts/audit_core_only_route_identity.py',ROOT/'scripts/qualify_core_only_route_identity_native.py',ROOT/'scripts/buffer_core_only_chip_controls.py']
  protected={str(p):sha(p)for p in paths}
  assert sha(paths[-1])=='b3f386082e1a4520d1fd88746d25510fcaf8d330ea29d92de02e5c5821bea700'
  app=Path(os.environ['CLOUD_APPIMAGE']);verify(app,'x86_64')
  run=completed(44332978563,'8412abee439a86f3821d6dae9d6220b78837754c');z,m=archive(run,'core-only-slew-margin-eco-44332978563')
  assert m['id']==14440182673 and m['digest']=='sha256:f560f6adb551cfb293557aa2fab3e2332c4ce42352d3faacacdcf664cc595849'
  source=json.loads(z.read('result.json'));assert source['sources_unchanged']and source['audit']['new_buffers']==6 and source['audit']['resized_cells']==0
  for p,h in source['outputs'].items():assert hashlib.sha256(z.read(p)).hexdigest()==h,p
  for p,h in source['protected_inputs'].items():
   rel=p.removeprefix('/home/runner/work/nssoc/nssoc/');assert not rel.startswith('/')
   if not rel.startswith('hw/soc/out/'):assert sha(ROOT/rel)==h,p
  name='core-eco-placed-unrouted.odb';assert source['outputs'][name]=='c1dfc3654fbd0849c494532fd60e80e23fe91611a97d180c7aba92e4e2fa5ab2'
  r['controls']=[]
  with tempfile.TemporaryDirectory(prefix='nssoc-identity-')as tmp:
   p=Path(tmp)/'source.odb';p.write_bytes(z.read(name))
   for mode in ['positive','power_open','clock_type','signal_rewire','instance_move','antenna_missing','port_type']:
    dst=OUT/(mode+'.json');env=dict(os.environ,NSSOC_CONTROL_BUFFER_OUT=str(OUT),NSSOC_ROUTE_IDENTITY_BEFORE=str(p),NSSOC_ROUTE_IDENTITY_FAULT=mode,NSSOC_ROUTE_IDENTITY_CONTROL_RESULT=str(dst))
    with (OUT/(mode+'.log')).open('w')as log:subprocess.run([str(app),'openroad','-exit','-python',str(paths[2])],env=env,stdout=log,stderr=subprocess.STDOUT,check=True)
    r['controls'].append(json.loads(dst.read_text()));print('Completed native identity control',mode,flush=True)
   assert sha(p)==source['outputs'][name]
  assert all(sha(p)==h for p,h in protected.items())
  r.update(status='PASS_NATIVE_ROUTE_IDENTITY_GUARD_CONTROLS_NOT_ROUTED_SIGNOFF',source_artifact=m,protected_inputs=protected,sources_unchanged=True)
 except BaseException as e:r.update(status='FAIL_OR_INCOMPLETE',error=repr(e));raise
 finally:
  r['outputs']={str(p.relative_to(OUT)):sha(p)for p in OUT.rglob('*')if p.is_file()and p.name!='result.json'};(OUT/'result.json').write_text(json.dumps(r,indent=2)+'\n')
if __name__=='__main__':main()
