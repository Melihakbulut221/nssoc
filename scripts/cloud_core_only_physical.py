import os,json,subprocess,hashlib,zipfile,tarfile,io
from pathlib import Path
from prepare_core_only_pnr import prepare
from bootstrap_flow import verify
ROOT=Path.cwd();OUT=ROOT/'hw/soc/out/core-only-placement';OUT.mkdir(parents=True)
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
 for p,h in report['source_binding']['before'].items():assert sha(ROOT/p)==h,p
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
 prep=OUT/'prepared';r['preparation']=prepare(root/'synthesis/soc_top.mapped.json',root/'synthesis/soc_top.netlist.v',prep)
 app=Path(os.environ['CLOUD_APPIMAGE']);verify(app,'x86_64')
 flow=ROOT/'hw/soc/pnr/pcie_interface_flow.py'
 config=json.loads((prep/'config.json').read_text())
 assert config['CLOCK_PORT']==['clk_i'] and config['CLOCK_PERIOD']==20 and config['TIME_DERATING_CONSTRAINT']==5.0
 assert len(r['preparation']['macros'])==4
 protected={str(p):sha(p)for p in [Path(__file__),ROOT/'scripts/prepare_core_only_pnr.py',flow,ROOT/'hw/soc/pnr/interface_flow.py',prep/'config.json',prep/'physical.sdc',prep/'state.json',root/'synthesis/soc_top.netlist.v']}
 r['protected_inputs']=protected;save()
 cmd=[str(app),'python',str(flow),'--flow','PacketInterfaces','--pdk-root',str(ROOT/'hw/soc/tools/ciel-corrpre'),'--pdk','ihp-sg13g2','--scl','sg13g2_stdcell','--force-run-dir',str(OUT/'run'),'--from','Yosys.JsonHeader','--to','OpenROAD.CTS','--with-initial-state',str(prep/'state.json')]
 for step in ['Yosys.Synthesis','Checker.YosysUnmappedCells','Checker.YosysSynthChecks','Checker.NetlistAssignStatements']:cmd+=['--skip',step]
 cmd.append(str(prep/'config.json'));(OUT/'run').mkdir()
 with (OUT/'native.log').open('w')as log:r['returncode']=subprocess.call(cmd,stdout=log,stderr=subprocess.STDOUT)
 assert r['returncode']==0 and all(sha(p)==h for p,h in protected.items())
 states=list((OUT/'run').glob('*-openroad-cts/state_out.json'));assert len(states)==1
 state=json.loads(states[0].read_text());r.update(status='CTS_COMPLETE_REQUIRES_NEW_BOOT_ROUTING_AND_SIGNOFF',cts_state=str(states[0].relative_to(OUT)),cts_odb_sha256=sha(state['odb']),sources_unchanged=True)
except BaseException as e:r.update(status='FAIL_OR_ERROR',error=repr(e));raise
finally:
 r['outputs']={str(p.relative_to(OUT)):sha(p)for p in OUT.rglob('*')if p.is_file()and p!=OUT/'result.json'};save()
