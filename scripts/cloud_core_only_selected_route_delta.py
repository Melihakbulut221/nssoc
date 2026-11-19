#!/usr/bin/env python3
"""Read-only physical shape comparison of rejected unaffected route changes."""
import os,json,hashlib,subprocess,io,zipfile
from pathlib import Path
from collections import Counter
ROOT=Path(__file__).resolve().parents[1];OUT=ROOT/'hw/soc/out/core-only-selected-route-delta'
def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def native():
 import odb
 from audit_native_signal_geometry_indexed import decoded_wire_shapes,qualify_native_decoder
 dbs=[];blocks=[]
 for name in ['before.odb','after.odb']:
  d=odb.dbDatabase.create();odb.read_db(d,str(OUT/name));dbs.append(d);blocks.append(d.getChip().getBlock())
 qualifications=[qualify_native_decoder(odb,b)for b in blocks]
 bad=json.loads((OUT/'preservation.json').read_text());rows=[]
 def shapes(n):
  if not n.getWire():return Counter()
  result=[]
  for kind,obj,g in decoded_wire_shapes(odb,n.getWire()):
   if kind=='rect':result.append((kind,obj.getName(),g.xMin(),g.yMin(),g.xMax(),g.yMax()))
   else:
    result.append((kind,obj.getName(),*g,tuple(sorted((box.getTechLayer().getName(),box.xMin(),box.yMin(),box.xMax(),box.yMax())for box in obj.getBoxes()))))
  return Counter(result)
 for name in bad['changed_unselected_nets']:
  left,right=[shapes(b.findNet(name))for b in blocks];removed=left-right;added=right-left
  rows.append(dict(net=name,is_clock=name in bad['changed_clock_nets'],same_shape_multiset=left==right,removed_count=sum(removed.values()),added_count=sum(added.values()),removed_examples=list(removed.items())[:3],added_examples=list(added.items())[:3]))
 assert len(rows)==33
 # A shifted shape is observably different; ordering alone is not.
 test=Counter({('rect','M2',0,0,10,10):1});assert test==Counter(list(test.elements())[::-1]);assert test!=Counter({('rect','M2',1,0,11,10):1})
 (OUT/'native-delta.json').write_text(json.dumps(dict(accepted=False,decoder_qualification=qualifications,changed_records=33,same_shape_records=sum(x['same_shape_multiset']for x in rows),different_shape_records=sum(not x['same_shape_multiset']for x in rows),rows=rows,scope='Exact shape multiset diagnosis, not geometric union equivalence or RC/DRC/LVS acceptance'),indent=2)+'\n')
def main():
 assert os.environ.get('GITHUB_ACTIONS')=='true';OUT.mkdir(parents=True,exist_ok=False);r=dict(source_head=os.environ['GITHUB_SHA'],accepted=False,status='PREPARING')
 try:
  from cloud_core_only_postgrt import api,archive,put
  run=api('actions/runs/44430646506');assert run['status']=='completed'and run['conclusion']=='failure'and run['run_attempt']==1 and run['head_sha']=='114ada1259666213fd98c6655b41eb6883e0e9d7'
  z,m=archive(run,'core-only-load-isolation-selected-route-44430646506');assert m['id']==14486519767 and m['digest']=='sha256:decf588129a86f60d12679e83a4982a070a099104e2fa62a3363c400bd1ea8f1'
  src=json.loads(z.read('result.json'));assert src['source_head']==run['head_sha']and src['status']=='FAIL_OR_INCOMPLETE'
  for n,h in src['outputs'].items():assert hashlib.sha256(z.read(n)).hexdigest()==h
  for source,target in [('candidate-partially-routed.odb','before.odb'),('soc_top.odb','after.odb'),('detailed-preservation/result.json','preservation.json')]:put(OUT/target,z.read(source),src['outputs'][source])
  assert sha(OUT/'before.odb')=='d0ff86380bdb3b5c37e47df89667e2aa25aa9a83f87239353242a1b94af1f2c4'and sha(OUT/'after.odb')=='3d5ace33b7e3fb91e515a393bdc788f29f7da60456900783531ea8873ce0103f'
  from bootstrap_flow import verify
  app=Path(os.environ['CLOUD_APPIMAGE']);verify(app,'x86_64');protected={str(p):sha(p)for p in [Path(__file__),OUT/'before.odb',OUT/'after.odb',ROOT/'scripts/audit_native_signal_geometry_indexed.py']}
  with (OUT/'native.log').open('w')as log:subprocess.run([str(app),'openroad','-exit','-python',str(Path(__file__).resolve())],env=dict(os.environ,NSSOC_ROUTE_DELTA_NATIVE='1'),stdout=log,stderr=subprocess.STDOUT,check=True)
  assert all(sha(p)==h for p,h in protected.items());r.update(status='UNSELECTED_ROUTE_SHAPE_DIAGNOSIS_ONLY',source_artifact=m,protected_inputs=protected,sources_unchanged=True,diagnosis=json.loads((OUT/'native-delta.json').read_text()))
 except BaseException as e:r.update(status='FAIL_OR_INCOMPLETE',error=repr(e));raise
 finally:r['outputs']={str(p.relative_to(OUT)):sha(p)for p in OUT.rglob('*')if p.is_file()and p!=OUT/'result.json'};(OUT/'result.json').write_text(json.dumps(r,indent=2)+'\n')
if __name__=='__main__':
 if os.environ.get('NSSOC_ROUTE_DELTA_NATIVE')=='1':native()
 else:main()
