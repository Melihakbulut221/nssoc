#!/usr/bin/env python3
"""Read-only native load/placement inventory for actual-RC critical gates."""
import os,json,hashlib,subprocess,io,zipfile
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];OUT=ROOT/'hw/soc/out/core-only-critical-load-inventory'
TARGETS=['nssoc_sta_i_'+str(n)for n in [2657,11771,14982,14419,14661,14660,14120,14487,59350,59362,59344,59359]]+['fanout'+str(n)for n in [525,489,435,495,529]]
def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def native():
 import odb
 p=OUT/'source.odb';before=sha(p);d=odb.dbDatabase.create();odb.read_db(d,str(p));b=d.getChip().getBlock();assert len(list(b.getInsts()))==106617
 rows=[]
 for name in TARGETS:
  i=b.findInst(name);assert i
  drivers=[t for t in i.getITerms()if str(t.getIoType())=='OUTPUT'and str(t.getSigType())=='SIGNAL'];assert len(drivers)==1
  t=drivers[0];n=t.getNet();assert n and not list(n.getBTerms());terms=[]
  for q in n.getITerms():
   inst=q.getInst();box=inst.getBBox()
   terms.append(dict(instance=inst.getName(),pin=q.getMTerm().getName(),master=inst.getMaster().getName(),io_type=str(q.getIoType()),signal_type=str(q.getSigType()),bbox_dbu=[box.xMin(),box.yMin(),box.xMax(),box.yMax()],orientation=str(inst.getOrient()),is_antenna=inst.getMaster().getName()=='sg13g2_antennanp'))
  assert sum(x['io_type']=='OUTPUT'for x in terms)==1
  rows.append(dict(driver=name+'/'+t.getMTerm().getName(),master=i.getMaster().getName(),net=n.getName(),net_type=str(n.getSigType()),terminals=sorted(terms,key=lambda x:(x['instance'],x['pin'])),diodes=sum(x['is_antenna']for x in terms),logic_loads=sum(x['io_type']=='INPUT'and not x['is_antenna']for x in terms)))
 assert sha(p)==before
 (OUT/'native-loads.json').write_text(json.dumps(dict(accepted=False,source_odb_sha256=before,sources_unchanged=True,dbu_per_um=b.getDbUnitsPerMicron(),targets=rows),indent=2)+'\n')
def main():
 assert os.environ.get('GITHUB_ACTIONS')=='true';OUT.mkdir(parents=True,exist_ok=False)
 r=dict(source_head=os.environ['GITHUB_SHA'],accepted=False,status='PREPARING')
 try:
  repo='repos/Melihakbulut221/nssoc'
  def api(p):return json.loads(subprocess.check_output(['gh','api',repo+'/'+p]))
  run=api('actions/runs/44420129432');assert run['head_sha']=='3e56fb282941bad19a74019ff73a65d41f058141'and run['run_attempt']==1 and run['status']=='completed'and run['conclusion']=='failure'
  aid=14482852777;digest='6ceddd39ed4711d1735da8e5be09b1ac79b56de71d6c3d7631561aa100a13e80';a=api('actions/artifacts/'+str(aid));assert a['workflow_run']['id']==run['id']and a['digest']=='sha256:'+digest
  data=subprocess.check_output(['gh','api',repo+'/actions/artifacts/'+str(aid)+'/zip']);assert hashlib.sha256(data).hexdigest()==digest;z=zipfile.ZipFile(io.BytesIO(data));src=json.loads(z.read('result.json'))
  assert src['source_head']==run['head_sha']and src['returncode']==0
  for n,h in src['outputs'].items():assert hashlib.sha256(z.read(n)).hexdigest()==h
  p=OUT/'source.odb';p.write_bytes(z.read('soc_top.odb'));assert sha(p)==src['routed_odb_sha256']=='0bccd439a9efe8b7463ae5d32f1ae42616c49872548bf6aabaaa35e3eb721eb5'
  from bootstrap_flow import verify
  app=Path(os.environ['CLOUD_APPIMAGE']);verify(app,'x86_64')
  with (OUT/'native.log').open('w')as log:subprocess.run([str(app),'openroad','-exit','-python',str(Path(__file__).resolve())],env=dict(os.environ,NSSOC_LOAD_NATIVE='1'),stdout=log,stderr=subprocess.STDOUT,check=True)
  r.update(status='NATIVE_CRITICAL_LOAD_INVENTORY_REQUIRES_ECO',source_binding=dict(run=run['id'],head=run['head_sha'],artifact=aid,digest=digest),inventory=json.loads((OUT/'native-loads.json').read_text()),script_sha256=sha(__file__))
 except BaseException as e:r.update(status='FAIL_OR_INCOMPLETE',error=repr(e));raise
 finally:
  r['outputs']={str(p.relative_to(OUT)):sha(p)for p in OUT.rglob('*')if p.is_file()and p.name!='result.json'};(OUT/'result.json').write_text(json.dumps(r,indent=2)+'\n')
if __name__=='__main__':
 if os.environ.get('NSSOC_LOAD_NATIVE')=='1':native()
 else:main()
