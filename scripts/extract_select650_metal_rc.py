import subprocess,json,hashlib,zipfile,io,stat,shutil,sys
from pathlib import Path,PurePosixPath
import cdr_mos650_metal_rc as source
P='repos/Melihakbulut221/nssoc/'
def api(s):return json.loads(subprocess.check_output(['gh','api',P+s]))
r=api('actions/runs/43745619914');assert r['conclusion']=='success'and r['head_sha']=='7f645e94d625fc6d72cfd1466d90690d6e4611e4'and r['run_attempt']==1
m=api('actions/artifacts/14174291576');assert m['workflow_run']['id']==r['id']and m['digest']=='sha256:d418009bddee05317b07701341b820f56181dd1fcbf68215b09b6dbb2be0db5c'and not m['expired']
b=subprocess.check_output(['gh','api',P+'actions/artifacts/14174291576/zip']);assert 'sha256:'+hashlib.sha256(b).hexdigest()==m['digest'];z=zipfile.ZipFile(io.BytesIO(b));assert len(z.namelist())==len(set(z.namelist()))
view=Path('select650-wires').resolve();view.mkdir();protected={}
for info in z.infolist():
 n=PurePosixPath(info.filename);assert not n.is_absolute()and '..'not in n.parts and not stat.S_ISLNK(info.external_attr>>16)
 if info.is_dir():continue
 path=view/n;path.parent.mkdir(parents=True,exist_ok=True);data=z.read(info);path.write_bytes(data);protected[str(path)]=hashlib.sha256(data).hexdigest()
report=json.loads((view/'result.json').read_text());assert report['status']=='PASS_NEW_SELECT650_WIRE_GRAPH_AND_ALL_TERMINAL_ANCHORS'and(report['devices'],report['terminals'],report['components'],report['electrical_nets'],report['physical_anchors'])==(650,2046,113,114,1278)
source.OUT=Path('select650-metal-rc').resolve();source.OUT.mkdir();source.NATIVE=source.OUT/'native';source.NATIVE.mkdir();source.DERIVED=source.OUT/'derived';source.DERIVED.mkdir()
try:
 cfg=json.loads(Path(source.CFG).read_text());runtime=source.NATIVE/'runtime-parent';runtime.mkdir()
 source.acquire(cfg['runtime'],runtime,lambda n:n.startswith('wire-stage/magic-cloud/'))
 stage=source.NATIVE/'wire-stage';stage.mkdir();shutil.copytree(runtime/'wire-stage/magic-cloud',stage/'magic-cloud')
 wire=stage/'wire';wire.mkdir()
 for name in ['anchors08.json','native05/wires.gds','native05/wires.l2n','native05/result.json']:
  path=wire/name;path.parent.mkdir(parents=True,exist_ok=True);shutil.copyfile(view/'view/wire'/name,path)
 texts,changes=source.methods()
 for name,text in texts.items():(wire/name).write_text(text)
 parser=Path('hw/soc/out/pcie-magic-resis-terminals-v1-20261004/audit_pilot.py');parser.parent.mkdir(parents=True,exist_ok=True);shutil.copyfile('scripts/frozen_cdr_rc/audit_pilot.py',parser)
 source.save('input-binding.json',dict(source_run=r['id'],artifact=m['id'],archive_sha256=m['digest'][7:],methods=changes,old_RC_reused=False,full_phy_accepted=False))
 source.execute(['ldd',stage/'magic-cloud/runtime/lib/magic/tcl/tclmagic.so'],'runtime-linkage',60)
 assert b'not found'not in(source.NATIVE/'runtime-linkage.stdout').read_bytes()
 source.execute([sys.executable,'-B',wire/'run-rc01.py'],'native-extraction',3600)
 capture=json.loads((wire/'rc03/result.json').read_text());assert capture['returncode']==0 and capture['status']=='NATIVE_COMPLETE_AWAITING_RC_AUDIT'
 source.execute([sys.executable,'-B',wire/'audit-rc48.py',wire/'rc03',wire/'anchors08.json',wire/'audit.json'],'native-audit',3600)
 audit=json.loads((wire/'audit.json').read_text());assert audit['status']=='PASS_WIRE_GRAPH_AND_COLLAPSED_C_ONLY'
 source.execute([sys.executable,'-B',wire/'mutations48.py'],'native-fault-controls',3600)
 controls=json.loads((wire/'native-mutations01.json').read_text());assert controls['status']=='PASS_REAL_NATIVE_BASELINE_AND13_RAW_CORRUPTION_CONTROLS'and len(controls['cases'])==13
 assert all(hashlib.sha256(Path(path).read_bytes()).hexdigest()==h for path,h in protected.items())
 for name,value in [('capture.json',capture),('audit.json',audit),('native-controls.json',controls)]:source.save(name,value)
 source.save('result.json',dict(status='PASS_NEW_SELECT650_FRESH_METAL_VIA_RC_REQUIRES_INTRINSIC_AND_ELECTRICAL',actual_resistors=audit['actual_exported_resistors'],actual_capacitors=audit['actual_exported_capacitors'],metal_via_RC_extracted=True,full_pex_qualified=False,full_phy_accepted=False,source_run=r['id']))
except BaseException as error:
 source.save('failure.json',dict(error=repr(error),full_phy_accepted=False));raise
