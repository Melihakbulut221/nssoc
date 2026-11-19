import os,json,hashlib,subprocess
from pathlib import Path
from cloud_core_only_postgrt import ROOT,sha,completed,archive,put
from bootstrap_flow import verify
OUT=ROOT/'hw/soc/out/core-only-resized-regression-inventory'
def main():
 assert os.environ.get('GITHUB_ACTIONS')=='true';OUT.mkdir(parents=True,exist_ok=False)
 r=dict(source_head=os.environ['GITHUB_SHA'],accepted=False,status='PREPARING')
 try:
  run=completed(44524545738,'c0ae24df469b3a3422b35c7ff9bcb99b38870b94');assert run['run_attempt']==1
  z,m=archive(run,'core-only-load-resize-antenna-neighbor-route-44524545738');assert m['id']==14531207616 and m['digest']=='sha256:3be91dc83fb3d6312ada57dbcb86dba41cf073099485b49591541ff693fd163b'
  src=json.loads(z.read('result.json'));assert src['source_head']==run['head_sha']and src['sources_unchanged']and src['detailed_identity']['instances']==106664
  assert set(n for n in z.namelist()if not n.endswith('/')and n!='result.json')==set(src['outputs'])
  for n,h in src['outputs'].items():assert hashlib.sha256(z.read(n)).hexdigest()==h,n
  for key in ['route__drc_errors','antenna__violating__nets','antenna__violating__pins']:assert src['metrics'][key]==0
  source=Path(os.environ['RUNNER_TEMP'])/'clean-slew-inventory.odb';put(source,z.read('restored-status.odb'),'171fa1a8f80a9eff594c169519b2fc216ff12ffd7c2e4ef150964ee0af26a1bb')
  app=Path(os.environ['CLOUD_APPIMAGE']);verify(app,'x86_64');helper=ROOT/'scripts/inventory_resized_regression_native.py';h=sha(helper)
  env=dict(os.environ,NSSOC_INVENTORY_ODB=str(source),NSSOC_INVENTORY_REPORT=str(OUT/'inventory.json'))
  with (OUT/'inventory.log').open('w')as log:subprocess.run([str(app),'openroad','-exit','-python',str(helper)],env=env,stdout=log,stderr=subprocess.STDOUT,check=True)
  assert sha(helper)==h and sha(source)=='171fa1a8f80a9eff594c169519b2fc216ff12ffd7c2e4ef150964ee0af26a1bb'
  r.update(status='NATIVE_CRITICAL_LOAD_INVENTORY_COMPLETE_NOT_AN_ECO',sources_unchanged=True,source_artifact=m,helper_sha256=h)
 except BaseException as e:r.update(status='FAIL_OR_INCOMPLETE',error=repr(e));raise
 finally:r['outputs']={str(p.relative_to(OUT)):sha(p)for p in OUT.rglob('*')if p.is_file()and p.name!='result.json'};(OUT/'result.json').write_text(json.dumps(r,indent=2)+'\n')
if __name__=='__main__':main()
