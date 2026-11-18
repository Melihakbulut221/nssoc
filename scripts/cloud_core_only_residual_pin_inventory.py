#!/usr/bin/env python3
"""Cloud-only read-only investigation of remaining electrical route residuals."""
import os,json,hashlib,subprocess,tempfile
from pathlib import Path
from bootstrap_flow import verify
from cloud_core_only_postgrt import ROOT,sha,completed,archive
OUT=ROOT/'hw/soc/out/core-only-residual-pin-inventory'
def main():
 assert os.environ.get('GITHUB_ACTIONS')=='true';OUT.mkdir(parents=True,exist_ok=False)
 r=dict(source_head=os.environ['GITHUB_SHA'],status='PREPARING',accepted=False)
 try:
  run=completed(44323428899,'3d8c75c1f63dfa753f58617e391e28850aa603ef');z,m=archive(run,'core-only-residual-electrical-globalroute-44323428899')
  assert m['id']==14437435877 and m['digest']=='sha256:a335010597079f4fcc72495c622f759630788f2a1f1f453f24a4ba1f8dbe2291'
  result=json.loads(z.read('result.json'));assert result['sources_unchanged']and result['returncode']==0
  for p,h in result['outputs'].items():assert hashlib.sha256(z.read(p)).hexdigest()==h,p
  for p,h in result['protected_inputs'].items():
   prefix='/home/runner/work/nssoc/nssoc/';assert p.startswith(prefix);relative=p[len(prefix):]
   if not relative.startswith('hw/soc/out/'):assert sha(ROOT/relative)==h,p
  name='routing/1-nssoc-coreonlyglobalroute/soc_top.odb';assert result['outputs'][name]=='47d011298e5f32cb31dcec5fcead7c0640d070fb7fb16c872e99b9516dc21505'
  app=Path(os.environ['CLOUD_APPIMAGE']);verify(app,'x86_64');native=ROOT/'scripts/inspect_core_only_residual_pins.py';protected={str(p):sha(p)for p in [Path(__file__),native]}
  with tempfile.TemporaryDirectory(prefix='nssoc-pin-inventory-')as tmp:
   odb=Path(tmp)/'source.odb';odb.write_bytes(z.read(name));env=dict(os.environ,NSSOC_INVENTORY_ODB=str(odb),NSSOC_INVENTORY_OUT=str(OUT))
   with (OUT/'native.log').open('w')as log:subprocess.run([str(app),'openroad','-exit','-python',str(native)],env=env,stdout=log,stderr=subprocess.STDOUT,check=True)
   assert sha(odb)==result['outputs'][name]
  inventory=json.loads((OUT/'pin-inventory.json').read_text());assert inventory['source_odb_sha256']==result['outputs'][name]and inventory['read_only']
  for p in ['routing/2-nssoc-coreonlyroutedslow/max.rpt','routing/4-nssoc-coreonlyroutedfast/min.rpt']:(OUT/('slow-max.rpt'if 'slow' in p else 'fast-min.rpt')).write_bytes(z.read(p))
  assert all(sha(p)==h for p,h in protected.items());r.update(status='READ_ONLY_RESIDUAL_PIN_GEOMETRY_VERIFIED',sources_unchanged=True,protected_inputs=protected,source_artifact=m,corners=result['corners'],inventory=inventory)
 except BaseException as e:r.update(status='FAIL_OR_INCOMPLETE',error=repr(e));raise
 finally:
  r['outputs']={str(p.relative_to(OUT)):sha(p)for p in OUT.rglob('*')if p.is_file()and p.name!='result.json'};(OUT/'result.json').write_text(json.dumps(r,indent=2)+'\n')
if __name__=='__main__':main()
