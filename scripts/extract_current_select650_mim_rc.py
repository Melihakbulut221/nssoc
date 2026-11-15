import os,json,hashlib,subprocess,zipfile,io,stat,shutil,sys
from pathlib import Path,PurePosixPath
import cdr_mos650_metal_rc as source
source.NATIVE.mkdir(parents=True);source.DERIVED.mkdir(parents=True)
context=source.gate()
def archive(run,head,aid,digest):
 r=source.api('actions/runs/'+str(run));assert r['conclusion']=='success'and r['head_sha']==head and r['run_attempt']==1
 m=source.api('actions/artifacts/'+str(aid));assert m['workflow_run']['id']==run and m['workflow_run']['head_sha']==head and m['digest']=='sha256:'+digest and not m['expired']
 data=subprocess.check_output(['gh','api','repos/'+source.REPO+'/actions/artifacts/'+str(aid)+'/zip']);assert hashlib.sha256(data).hexdigest()==digest
 z=zipfile.ZipFile(io.BytesIO(data));assert len(z.namelist())==len(set(z.namelist()));return z
z=archive(43748923684,'e7aef3e3e4b3d7b2c93190649d0981cdee1b9bd5',14175890238,'5495ebccb905ede137d893a1d8a43b448dc988b370c0c58cdd03307ff2b63e4a')
restored=source.ROOT/'select650-wires';assert not restored.exists();restored.mkdir();protected={}
for info in z.infolist():
 n=PurePosixPath(info.filename);assert not n.is_absolute()and '..'not in n.parts and not stat.S_ISLNK(info.external_attr>>16)
 if info.is_dir():continue
 p=restored/n;p.parent.mkdir(parents=True,exist_ok=True);p.write_bytes(z.read(info));protected[str(p)]=source.pin(p)
r=source.read(restored/'result.json');assert r['devices']==650 and r['terminals']==2046 and r['physical_anchors']==1428 and r['source_gds_sha256']=='5f66ce0cb46acfb580b517ba02b10f66560ba4200d9cfbba0b633a839cc59c5a'
anchors=source.read(restored/'view/wire/anchors08.json');assert anchors['physical_gate_contact_count']==200 and not anchors['intrinsic_gate_metal_shortcuts']and len(anchors['gate_groups'])==50
for n,h in anchors['inputs'].items():
 p=Path(n);assert p.is_relative_to(restored)and source.pin(p)['sha256']==h
ids=archive(43748580179,'4602a2710cea2b2322cb035750dad9738d9583f4',14175207602,'0e41bbf406fb1518a17ee41e49814758ebd32ad9fc880e5adaaa864ae00630bc')
flat=json.loads(ids.read('lvs_flat-identity.json'));assert len(flat['pairs'])==650 and flat['terminal_count']==2046
assert source.pin(restored/'view/parent/physical/lvs_flat/result.lvsdb')==flat['lvsdb']
physical=source.ROOT/'paired-terminal-anchors';assert not physical.exists()
shutil.copytree(restored/'view',physical/'native/view');(physical/'derived').mkdir()
(physical/'derived/lvs_flat-identity.json').write_bytes(ids.read('lvs_flat-identity.json'))
selected={str(p.relative_to(physical)):source.pin(p)for p in physical.rglob('*')if p.is_file()}
cfg=source.read(source.ROOT/source.CFG);cfg['view']=dict(run=43748923684,source='e7aef3e3e4b3d7b2c93190649d0981cdee1b9bd5',selected=selected)
runtime=source.NATIVE/'runtime-parent';runtime.mkdir();source.acquire(cfg['runtime'],runtime,lambda n:n in cfg['runtime']['selected'])
for relative in ['wire-stage/magic-cloud/runtime/lib/magic/tcl/tclmagic.so','mim/precise/precision-runtime/lib/magic/tcl/tclmagic.so']:
 linked=subprocess.run(['ldd',str(runtime/relative)],text=True,capture_output=True,check=True)
 assert 'not found'not in linked.stdout+linked.stderr,(relative,linked.stdout,linked.stderr)
source.save('native-linkage.json',dict(both_pinned_magic_runtimes_resolved=True))
stage=source.NATIVE/'wire-stage';stage.mkdir();shutil.copytree(runtime/'wire-stage/magic-cloud',stage/'magic-cloud')
assert source.pin(stage/'magic-cloud/runtime/lib/magic/tcl/tclmagic.so')['sha256']=='e8f2d96121e704acee41e7a58c23feead887527e3bfc4f51da4d97aa8183970e'
parser=source.ROOT/'hw/soc/out/pcie-magic-resis-terminals-v1-20261004/audit_pilot.py';parser.parent.mkdir(parents=True,exist_ok=True);parser.write_bytes((source.ROOT/'scripts/frozen_cdr_rc/audit_pilot.py').read_bytes())
source.save('current-view-binding.json',dict(context=context,source_run=43748923684,source_gds_sha256=r['source_gds_sha256'],protected=protected,selected=selected,full_phy_accepted=False))
source.mim_extract(cfg,physical)
assert all(source.pin(p)==h for p,h in protected.items())
source.gate()
