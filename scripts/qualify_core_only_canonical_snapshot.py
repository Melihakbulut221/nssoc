#!/usr/bin/env python3
"""Inject native geometry/connectivity faults into the actual canonical snapshot helper."""
import os,sys,json,hashlib,subprocess,urllib.request,ast,struct
from pathlib import Path
ROOT=Path.cwd();OUT=ROOT/'hw/soc/out/core-only-canonical-native-controls'
def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def native():
 import odb
 source=ROOT/'scripts/canonicalize_core_only_timing_names.py'
 tree=ast.parse(source.read_text());nodes=[n for n in tree.body if isinstance(n,ast.FunctionDef)and n.name=='snapshot'];assert len(nodes)==1
 namespace=dict(json=json,hashlib=hashlib,struct=struct)
 exec(compile(ast.Module(body=nodes,type_ignores=[]),str(source),'exec'),namespace)
 snapshot=namespace['snapshot']
 d=odb.dbDatabase.create();odb.read_lef(d,str(OUT/'sg13g2_tech.lef'));odb.read_lef(d,str(OUT/'sg13g2_stdcell.lef'))
 chip=odb.dbChip.create(d,d.getTech());b=odb.dbBlock.create(chip,'canonical_fixture');master=d.findMaster('sg13g2_buf_1');assert master
 a=odb.dbInst.create(b,master,r'bad\instance$');z=odb.dbInst.create(b,master,'receiver')
 for i,x in [(a,10000),(z,20000)]:i.setLocation(x,10000);i.setPlacementStatus('PLACED')
 n=odb.dbNet.create(b,r'bad\net$');n.setSigType('SIGNAL');a.findITerm('X').connect(n);z.findITerm('A').connect(n)
 layer=b.getTech().findLayer('Metal2');assert layer
 def wire():
  w=odb.dbWire.create(n);e=odb.dbWireEncoder();e.begin(w);e.newPath(layer,'ROUTED');e.addPoint(10000,10000);e.addPoint(20000,10000);e.end()
 wire();before=snapshot(b,{},{});old_i=a.getName();old_n=n.getName();assert a.rename('safe_instance')and n.rename('safe_net')
 inv_i={'safe_instance':old_i};inv_n={'safe_net':old_n}
 assert snapshot(b,inv_i,inv_n)==before
 checks={'lossless_name_change':True}
 x,y=z.getLocation();z.setLocation(x+1,y);assert snapshot(b,inv_i,inv_n)!=before;z.setLocation(x,y);assert snapshot(b,inv_i,inv_n)==before;checks['one_dbu_instance_move_detected']=True
 z.findITerm('A').disconnect();assert snapshot(b,inv_i,inv_n)!=before;z.findITerm('A').connect(n);assert snapshot(b,inv_i,inv_n)==before;checks['terminal_disconnect_detected']=True
 odb.dbWire.destroy(n.getWire());assert snapshot(b,inv_i,inv_n)!=before;wire();assert snapshot(b,inv_i,inv_n)==before;checks['route_removal_detected']=True
 z.swapMaster(d.findMaster('sg13g2_buf_2'));assert snapshot(b,inv_i,inv_n)!=before;z.swapMaster(master);assert snapshot(b,inv_i,inv_n)==before;checks['master_change_detected']=True
 assert not a.rename(z.getName());assert snapshot(b,inv_i,inv_n)==before;checks['alias_collision_rejected']=True
 odb.write_db(d,str(OUT/'fixture.odb'));dd=odb.dbDatabase.create();odb.read_db(dd,str(OUT/'fixture.odb'));assert snapshot(dd.getChip().getBlock(),inv_i,inv_n)==before;checks['binary_roundtrip_unchanged']=True
 (OUT/'native-proof.json').write_text(json.dumps(dict(checks=checks,actual_helper_source_sha256=sha(source),accepted=False,scope='Small native fault-injection qualification; full design preservation requires separate output proof.'),indent=2)+'\n')
def main():
 assert os.environ.get('GITHUB_ACTIONS')=='true';OUT.mkdir(parents=True,exist_ok=False)
 r=dict(source_head=os.environ['GITHUB_SHA'],status='PREPARING',accepted=False)
 try:
  for name,digest in [('sg13g2_tech.lef','e3470344dfac5347b176fb3f8e0f0548d17a66b8f433626a8987dcb2ae4828b6'),('sg13g2_stdcell.lef','c7575039af0b124e1834c407bfb9ac7a2db576d1e3533d98474dad3fbc2af589')]:
   url='https://raw.githubusercontent.com/IHP-GmbH/IHP-Open-PDK/c4b8b4e5e7a05f375cca3815d51b3a37721fbf5c/ihp-sg13g2/libs.ref/sg13g2_stdcell/lef/'+name
   with urllib.request.urlopen(url,timeout=60)as response:data=response.read()
   assert hashlib.sha256(data).hexdigest()==digest;(OUT/name).write_bytes(data)
  from bootstrap_flow import verify
  app=Path(os.environ['CLOUD_APPIMAGE']);verify(app,'x86_64');source=ROOT/'scripts/canonicalize_core_only_timing_names.py'
  protected={str(p):sha(p)for p in [Path(__file__),source,*OUT.iterdir()]}
  with (OUT/'native.log').open('w')as log:subprocess.run([str(app),'openroad','-exit','-python',str(Path(__file__)),'--native'],stdout=log,stderr=subprocess.STDOUT,check=True)
  proof=json.loads((OUT/'native-proof.json').read_text());assert all(proof['checks'].values())and len(proof['checks'])==7
  assert all(sha(p)==h for p,h in protected.items());r.update(status='PASS_NATIVE_CANONICAL_SNAPSHOT_FAULT_CONTROLS',proof=proof,sources_unchanged=True,protected_inputs=protected)
 except BaseException as e:r.update(status='FAIL_OR_INCOMPLETE',error=repr(e));raise
 finally:
  r['outputs']={str(p.relative_to(OUT)):sha(p)for p in OUT.rglob('*')if p.is_file()and p.name!='result.json'}
  (OUT/'result.json').write_text(json.dumps(r,indent=2)+'\n')
if __name__=='__main__':
 if '--native'in sys.argv:native()
 else:main()
