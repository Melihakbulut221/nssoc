import os,json,hashlib,subprocess
from pathlib import Path
from cloud_core_only_postgrt import ROOT,sha,completed,archive,put
from bootstrap_flow import verify
OUT=ROOT/'hw/soc/out/core-only-six-buffer-next-inventory'
def main():
 assert os.environ.get('GITHUB_ACTIONS')=='true';OUT.mkdir(parents=True,exist_ok=False)
 r=dict(source_head=os.environ['GITHUB_SHA'],accepted=False,status='PREPARING')
 try:
  run=completed(44545302944,'99aea3abd3ac6622674556f6854995436d9c1d6b');assert run['run_attempt']==1
  z,m=archive(run,'core-only-regression-antenna-route-44545302944');assert m['id']==14543516160 and m['digest']=='sha256:44feb72eb6405fbafdf4e8c729ae81b87cdeb24e2f3d8c0ed89f8eb84399eecd'
  src=json.loads(z.read('result.json'));assert src['source_head']==run['head_sha']and src['sources_unchanged']and src['detailed_identity']['instances']==106672
  assert set(n for n in z.namelist()if not n.endswith('/')and n!='result.json')==set(src['outputs'])
  for n,h in src['outputs'].items():assert hashlib.sha256(z.read(n)).hexdigest()==h,n
  for key in ['route__drc_errors','antenna__violating__nets','antenna__violating__pins']:assert src['metrics'][key]==0
  source=Path(os.environ['RUNNER_TEMP'])/'clean-slew-inventory.odb';put(source,z.read('restored-status.odb'),'bd28f784aa3cad49b72197de70c394727ab0e72608610febd4c4e16dfc4a28bc')
  app=Path(os.environ['CLOUD_APPIMAGE']);verify(app,'x86_64');helper=ROOT/'scripts/inventory_six_buffer_next_native.py';h=sha(helper)
  env=dict(os.environ,NSSOC_INVENTORY_ODB=str(source),NSSOC_INVENTORY_REPORT=str(OUT/'inventory.json'))
  with (OUT/'inventory.log').open('w')as log:subprocess.run([str(app),'openroad','-exit','-python',str(helper)],env=env,stdout=log,stderr=subprocess.STDOUT,check=True)
  assert sha(helper)==h and sha(source)=='bd28f784aa3cad49b72197de70c394727ab0e72608610febd4c4e16dfc4a28bc'
  r.update(status='NATIVE_CRITICAL_LOAD_INVENTORY_COMPLETE_NOT_AN_ECO',sources_unchanged=True,source_artifact=m,helper_sha256=h)
 except BaseException as e:r.update(status='FAIL_OR_INCOMPLETE',error=repr(e));raise
 finally:r['outputs']={str(p.relative_to(OUT)):sha(p)for p in OUT.rglob('*')if p.is_file()and p.name!='result.json'};(OUT/'result.json').write_text(json.dumps(r,indent=2)+'\n')
if __name__=='__main__':main()
