import os,json,hashlib,subprocess
from pathlib import Path
from cloud_core_only_postgrt import ROOT,sha,completed,archive,put
from bootstrap_flow import verify
OUT=ROOT/'hw/soc/out/core-only-loadsplit-all-violations-inventory'
def main():
 assert os.environ.get('GITHUB_ACTIONS')=='true';OUT.mkdir(parents=True,exist_ok=False)
 r=dict(source_head=os.environ['GITHUB_SHA'],accepted=False,status='PREPARING')
 try:
  run=completed(44562378599,'d800be2ea61e39adef89e58c075591d77f71773e');assert run['run_attempt']==1
  z,m=archive(run,'core-only-loadsplit-neighbor-route-44562378599');assert m['id']==14549769828 and m['digest']=='sha256:f11b5b5f3affd565311424f68028f32613ecc68c35d313bf6f914e5b3d1a3f39'
  src=json.loads(z.read('result.json'));assert src['source_head']==run['head_sha']and src['sources_unchanged']and src['detailed_identity']['instances']==106693
  assert set(n for n in z.namelist()if not n.endswith('/')and n!='result.json')==set(src['outputs'])
  for n,h in src['outputs'].items():assert hashlib.sha256(z.read(n)).hexdigest()==h,n
  for key in ['route__drc_errors','antenna__violating__nets','antenna__violating__pins']:assert src['metrics'][key]==0
  source=Path(os.environ['RUNNER_TEMP'])/'clean-slew-inventory.odb';put(source,z.read('restored-status.odb'),'12a48d839091ba5c4fea76a193fea75fcc5f2f38621b1df809cb3df5bd51e458')
  dz,dm=archive(completed(44570529195,'4753cbe3fc7b357bbefd14d6d2ee5d706fad8179'),'core-only-loadsplit-electrical-delta-44570529195')
  assert dm['id']==14552649545 and dm['digest']=='sha256:69e213a43b5117fbc7e5915c3983059808060fdaf6ed930e29b42cce50cfccc8'
  delta=json.loads(dz.read('result.json'));assert delta['source_head']=='4753cbe3fc7b357bbefd14d6d2ee5d706fad8179'
  assert set(n for n in dz.namelist()if not n.endswith('/')and n!='result.json')==set(delta['outputs'])
  for n,h in delta['outputs'].items():assert hashlib.sha256(dz.read(n)).hexdigest()==h,n
  assert delta['sources']['after']['views']['odb_sha256']==sha(source)
  pins={}
  for corner in delta['corners']:
   rows=json.loads(dz.read(corner+'.json'))['after']
   for section,values in rows.items():
    for pin,metrics in values.items():pins.setdefault(pin,[]).append(dict(corner=corner,section=section,metrics=metrics))
  assert len(pins)>424
  (OUT/'violating-pins.json').write_text(json.dumps(pins,indent=2)+'\n')
  r['delta_artifact']=dm;r['unique_violating_pins']=len(pins)
  app=Path(os.environ['CLOUD_APPIMAGE']);verify(app,'x86_64');helper=ROOT/'scripts/inventory_loadsplit_all_violations_native.py';h=sha(helper)
  env=dict(os.environ,NSSOC_INVENTORY_ODB=str(source),NSSOC_INVENTORY_REPORT=str(OUT/'inventory.json'),NSSOC_INVENTORY_PINS=str(OUT/'violating-pins.json'))
  with (OUT/'inventory.log').open('w')as log:subprocess.run([str(app),'openroad','-exit','-python',str(helper)],env=env,stdout=log,stderr=subprocess.STDOUT,check=True)
  assert sha(helper)==h and sha(source)=='12a48d839091ba5c4fea76a193fea75fcc5f2f38621b1df809cb3df5bd51e458'
  r.update(status='NATIVE_CRITICAL_LOAD_INVENTORY_COMPLETE_NOT_AN_ECO',sources_unchanged=True,source_artifact=m,helper_sha256=h)
 except BaseException as e:r.update(status='FAIL_OR_INCOMPLETE',error=repr(e));raise
 finally:r['outputs']={str(p.relative_to(OUT)):sha(p)for p in OUT.rglob('*')if p.is_file()and p.name!='result.json'};(OUT/'result.json').write_text(json.dumps(r,indent=2)+'\n')
if __name__=='__main__':main()
