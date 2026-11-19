import os,json,hashlib,subprocess,re
from pathlib import Path
from cloud_core_only_postgrt import ROOT,sha,completed,archive,put
from bootstrap_flow import verify
OUT=ROOT/'hw/soc/out/core-only-combined-electrical-inventory'
def main():
 assert os.environ.get('GITHUB_ACTIONS')=='true';OUT.mkdir(parents=True,exist_ok=False)
 r=dict(source_head=os.environ['GITHUB_SHA'],accepted=False,status='PREPARING')
 try:
  run=completed(44446105491,'a537abf3e2f06e598cc785c2364e68b6c7df90f4');assert run['run_attempt']==1
  z,m=archive(run,'core-only-combined-timing-route-44446105491');assert m['id']==14493847778 and m['digest']=='sha256:ab94e7825565f4795e5cd9e905b2cfbfb333554e8f44e1c4270d03dcbb413300'
  src=json.loads(z.read('result.json'));assert src['source_head']==run['head_sha']and src['sources_unchanged']and src['detailed_identity']['instances']==106650
  assert set(n for n in z.namelist()if not n.endswith('/')and n!='result.json')==set(src['outputs'])
  for n,h in src['outputs'].items():assert hashlib.sha256(z.read(n)).hexdigest()==h,n
  for key in ['route__drc_errors','antenna__violating__nets','antenna__violating__pins']:assert src['metrics'][key]==0
  source=Path(os.environ['RUNNER_TEMP'])/'combined-critical-inventory.odb';put(source,z.read('restored-status.odb'),'81766779033ee0642d322a417e4e8f389807b7cb2d1d5ceb6cf1842915fb68ee')
  rr=completed(44452987978,'d8e622958c15b6c4afe8f7c24e27c6d79f5a7abd');assert rr['run_attempt']==1
  zz,mm=archive(rr,'core-only-combined-electrical-reports-44452987978');assert mm['id']==14496057491 and mm['digest']=='sha256:18d5eb5a4d9e14f0c03302607a6374d9493bc4c129e48aa1880f93079ec289d0'
  manifest=json.loads(zz.read('result.json'));assert manifest['source_head']==rr['head_sha'] and manifest['source_run']==44448236669
  assert set(n for n in zz.namelist()if not n.endswith('/')and n!='result.json')==set(manifest['outputs'])
  for n,h in manifest['outputs'].items():assert hashlib.sha256(zz.read(n)).hexdigest()==h,n
  violations=[];counts={}
  for n in manifest['outputs']:
   if not n.endswith('/checks.rpt'):continue
   corner=n.split('/')[-2];counts[corner]={k:0 for k in ['max slew','max fanout','max capacitance']};kind=None
   for line in zz.read(n).decode().splitlines():
    if line.strip()in counts[corner]:kind=line.strip();continue
    if line.startswith('==='):kind=None
    row=re.match(r'^(\S+)\s+(-?[\d.]+)\s+(-?[\d.]+)\s+(-?[\d.]+)\s+\(VIOLATED\)',line)
    if kind and row:
     pin,limit,actual,slack=row.groups();violations.append(dict(corner=corner,kind=kind,pin=pin,limit=float(limit),actual=float(actual),slack=float(slack)));counts[corner][kind]+=1
  assert counts=={'nom_slow_1p08V_125C':{'max slew':502,'max fanout':210,'max capacitance':52},'nom_typ_1p20V_25C':{'max slew':4,'max fanout':210,'max capacitance':54},'nom_fast_1p32V_m40C':{'max slew':0,'max fanout':210,'max capacitance':60}},counts
  (OUT/'violations.json').write_text(json.dumps(violations,indent=2)+'\n');r['source_report_artifact']=mm;r['counts']=counts
  app=Path(os.environ['CLOUD_APPIMAGE']);verify(app,'x86_64');helper=ROOT/'scripts/inventory_combined_electrical_native.py';h=sha(helper)
  env=dict(os.environ,NSSOC_INVENTORY_ODB=str(source),NSSOC_INVENTORY_REPORT=str(OUT/'inventory.json'),NSSOC_INVENTORY_VIOLATIONS=str(OUT/'violations.json'))
  with (OUT/'inventory.log').open('w')as log:subprocess.run([str(app),'openroad','-exit','-python',str(helper)],env=env,stdout=log,stderr=subprocess.STDOUT,check=True)
  assert sha(helper)==h and sha(source)=='81766779033ee0642d322a417e4e8f389807b7cb2d1d5ceb6cf1842915fb68ee'
  r.update(status='NATIVE_ELECTRICAL_LOAD_INVENTORY_COMPLETE_NOT_AN_ECO',sources_unchanged=True,source_artifact=m,helper_sha256=h)
 except BaseException as e:r.update(status='FAIL_OR_INCOMPLETE',error=repr(e));raise
 finally:r['outputs']={str(p.relative_to(OUT)):sha(p)for p in OUT.rglob('*')if p.is_file()and p.name!='result.json'};(OUT/'result.json').write_text(json.dumps(r,indent=2)+'\n')
if __name__=='__main__':main()
