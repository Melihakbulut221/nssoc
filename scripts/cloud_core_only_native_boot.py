import os,json,subprocess,hashlib,zipfile,tarfile,io,base64
from pathlib import Path
ROOT=Path.cwd();OUT=ROOT/'hw/soc/out/core-only-native-boot';OUT.mkdir(parents=True)
REPO='repos/Melihakbulut221/nssoc/'
def api(p):return json.loads(subprocess.check_output(['gh','api',REPO+p]))
def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
r=dict(source_head=os.environ['GITHUB_SHA'],accepted=False,final_timing_complete=False,mapped_boot_passed=False,status='RUNNING')
def save():(OUT/'result.json').write_text(json.dumps(r,indent=2))
try:
 assert os.environ.get('GITHUB_ACTIONS')=='true'
 run=api('actions/runs/44238569057')
 assert run['head_sha']=='bfb1fcc1bcd1d2def770ac26bd978767b0466e32' and run['run_attempt']==1 and run['status']=='completed' and run['conclusion']=='success'
 artifacts=api('actions/runs/44238569057/artifacts')['artifacts']
 def archive(prefix):
  rows=[a for a in artifacts if a['name']==prefix+'44238569057'];assert len(rows)==1
  a=rows[0];assert not a['expired'] and a['workflow_run']['id']==run['id'] and a['workflow_run']['head_sha']==run['head_sha']
  b=subprocess.check_output(['gh','api',REPO+'actions/artifacts/'+str(a['id'])+'/zip'])
  assert a['digest']=='sha256:'+hashlib.sha256(b).hexdigest()
  z=zipfile.ZipFile(io.BytesIO(b));assert len(z.namelist())==len(set(z.namelist()));return z,a
 mapped,ma=archive('core-only-mainchip-mapping-');native,na=archive('core-only-mainchip-source-native-')
 report=json.loads(mapped.read('mapping.json'))
 assert report['source_head']==run['head_sha'] and report['status']=='MAPPED_CORE_ONLY_REQUIRES_MAPPED_BOOT_AND_PHYSICAL_SIGNOFF'
 assert not report['accepted'] and not report['pcie_present'] and not report['ethernet_present']
 assert report['macros']=={'RM_IHPSG13_1P_2048x64_c2_bm_bist':4}
 assert report['source_binding']['all_files_unchanged']
 reviewed_harness={'hw/soc/flow/sim_logic_boot_gl.py','hw/soc/tb/tb_soc_logic_boot_gl.v'}
 deltas={}
 for p,h in report['source_binding']['before'].items():
  if p in reviewed_harness:
   original=base64.b64decode(api('contents/'+p+'?ref='+run['head_sha'])['content'])
   assert hashlib.sha256(original).hexdigest()==h,p
   deltas[p]=dict(producer_sha256=h,boot_harness_sha256=sha(ROOT/p))
  else:assert sha(ROOT/p)==h,p
 assert set(deltas)==reviewed_harness
 r['reviewed_test_harness_delta']=deltas
 assert native.namelist()==['build.tgz']
 root=Path('hw/soc/out/core-only-mainchip');seen=set()
 with tarfile.open(fileobj=io.BytesIO(native.read('build.tgz'))) as tar:
  for member in tar:
   p=Path(member.name);assert not p.is_absolute() and '..'not in p.parts and (p==root or root in p.parents)
   if member.isdir():continue
   assert member.isfile();name=str(p.relative_to(root));assert name not in seen and name in report['outputs'];seen.add(name)
   b=tar.extractfile(member).read();assert hashlib.sha256(b).hexdigest()==report['outputs'][name]
   assert not p.exists();p.parent.mkdir(parents=True,exist_ok=True);p.write_bytes(b)
 assert seen==set(report['outputs'])
 r['source_binding']=dict(run=run['id'],head=run['head_sha'],artifacts=[ma,na],netlist_sha256=report['outputs']['synthesis/soc_top.netlist.v'])
 qualification=api('actions/runs/44239505985')
 assert qualification['status']=='completed' and qualification['conclusion']=='success' and qualification['head_sha']=='603c4d763128a3c238363c7d15e153eccff565e4' and qualification['run_attempt']==1
 for p in ['hw/soc/flow/sim_logic_boot_gl.py','hw/soc/tb/tb_soc_logic_boot_gl.v','hw/soc/tb/mapped_system_mbist_boot_monitor.v','scripts/qualify_system_mbist_monitor.py','sw/tests/test_logic_boot_gl.py']:
  qualified=base64.b64decode(api('contents/'+p+'?ref='+qualification['head_sha'])['content'])
  assert hashlib.sha256(qualified).hexdigest()==sha(ROOT/p),p
 r['qualification_run']=qualification['id'];save()
 subprocess.run(['python3','hw/soc/flow/prepare_ihp_native_boot.py'],check=True)
 cmd=['python3','hw/soc/flow/sim_logic_boot_gl.py','--simulator','iverilog','--cycles','4000000','--timeout','14400','--pcie-profile','off','--mbist-profile','system-only','--nm','/usr/bin/riscv64-linux-gnu-nm','--synthesis',str(root/'synthesis'),'--firmware',str(root/'rtl'),'--pdk',str(ROOT/'hw/soc/tools/ihp-native-boot-c4b8b4e/ihp-sg13g2'),'--output',str(OUT/'simulation')]
 with (OUT/'native.log').open('w')as log:r['returncode']=subprocess.call(cmd,stdout=log,stderr=subprocess.STDOUT)
 result=json.loads((OUT/'simulation/result.json').read_text())
 r['boot_result']=result
 assert r['returncode']==0 and result['passed'] and result['sources_unchanged']
 r.update(status='PASS_NATIVE_FUNCTIONAL_BOOT_REQUIRES_PHYSICAL_TIMING_AND_SIGNOFF',mapped_boot_passed=True)
except BaseException as e:r.update(status='FAIL_OR_ERROR',error=repr(e));raise
finally:
 r['outputs']={str(p.relative_to(OUT)):sha(p)for p in OUT.rglob('*')if p.is_file()and p!=OUT/'result.json'};save()
