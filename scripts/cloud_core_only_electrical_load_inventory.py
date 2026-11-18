#!/usr/bin/env python3
"""Authenticate actual routed estimates before read-only native load diagnosis."""
import os,json,hashlib,subprocess
from pathlib import Path
from cloud_core_only_postgrt import ROOT,completed,archive,sha
from bootstrap_flow import verify
OUT=ROOT/'hw/soc/out/core-only-electrical-load-inventory'
def main():
 assert os.environ.get('GITHUB_ACTIONS')=='true';OUT.mkdir(parents=True,exist_ok=False)
 r=dict(source_head=os.environ['GITHUB_SHA'],status='PREPARING',accepted=False)
 try:
  run=completed(44311633615,'52ebe8043d3ea6a7d456ebd6d667efa254ae7fa0');z,meta=archive(run,'core-only-targeted-globalroute-native-44311633615')
  assert meta['id']==14431177283 and meta['digest']=='sha256:aff919c915ad3b35daf62ea6108bde346f55b448af75478fc6f55e0a4ff1c355'
  zz,sm=archive(run,'core-only-targeted-globalroute-summary-44311633615');assert sm['id']==14431611206 and sm['digest']=='sha256:27b74cc4fac1b4ff1bceeda2cfbb63b30e01c1fd929fb4b41c3d937e25aa5e43'
  assert z.read('result.json')==zz.read('result.json');source=json.loads(z.read('result.json'));assert source['sources_unchanged']and source['returncode']==0
  for n,h in source['outputs'].items():assert hashlib.sha256(z.read(n)).hexdigest()==h
  state=json.loads(z.read(source['output_state']));prefix='/home/runner/work/nssoc/nssoc/hw/soc/out/core-only-targeted-globalroute/'
  assert state['odb'].startswith(prefix);name=state['odb'][len(prefix):];assert name in source['outputs']
  (OUT/'source.odb').write_bytes(z.read(name));(OUT/'checks.rpt').write_bytes(z.read('routing/2-nssoc-coreonlyroutedslow/checks.rpt'))
  script=ROOT/'scripts/audit_core_only_electrical_loads.py';protected={str(p):sha(p)for p in [Path(__file__),script,OUT/'source.odb',OUT/'checks.rpt']}
  app=Path(os.environ['CLOUD_APPIMAGE']);verify(app,'x86_64')
  with (OUT/'native.log').open('w')as log:subprocess.run([str(app),'openroad','-exit','-python',str(script)],env=dict(os.environ,NSSOC_CORE_LOAD_AUDIT_OUT=str(OUT)),stdout=log,stderr=subprocess.STDOUT,check=True)
  audit=json.loads((OUT/'load-inventory.json').read_text());assert audit['source_unchanged']and not audit['waivers_applied']
  assert all(sha(p)==h for p,h in protected.items());r.update(status='NATIVE_LOAD_INVENTORY_COMPLETE_NO_ELECTRICAL_WAIVERS',source_artifact=meta,source_summary=sm,protected_inputs=protected,sources_unchanged=True,drivers=audit['violating_drivers'])
 except BaseException as e:r.update(status='FAIL_OR_INCOMPLETE',error=repr(e));raise
 finally:
  r['outputs']={str(p.relative_to(OUT)):sha(p)for p in OUT.rglob('*')if p.is_file()and p.name!='result.json'}
  (OUT/'result.json').write_text(json.dumps(r,indent=2)+'\n')
if __name__=='__main__':main()
