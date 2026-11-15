import subprocess,json,hashlib,zipfile,io,stat,shutil
from pathlib import Path,PurePosixPath
import cdr_mos650_wires as source
P='repos/Melihakbulut221/nssoc/'
def api(s):return json.loads(subprocess.check_output(['gh','api',P+s]))
r=api('actions/runs/43745619914');assert r['conclusion']=='success'and r['head_sha']=='7f645e94d625fc6d72cfd1466d90690d6e4611e4'and r['run_attempt']==1
m=api('actions/artifacts/14174291576');assert m['workflow_run']['id']==r['id']and m['digest']=='sha256:d418009bddee05317b07701341b820f56181dd1fcbf68215b09b6dbb2be0db5c'and not m['expired']
b=subprocess.check_output(['gh','api',P+'actions/artifacts/14174291576/zip']);assert 'sha256:'+hashlib.sha256(b).hexdigest()==m['digest'];z=zipfile.ZipFile(io.BytesIO(b));assert len(z.namelist())==len(set(z.namelist()))
root=Path('select650-gate-native').resolve();root.mkdir();view=root/'restored';view.mkdir();protected={}
for info in z.infolist():
 n=PurePosixPath(info.filename);assert not n.is_absolute()and '..'not in n.parts and not stat.S_ISLNK(info.external_attr>>16)
 if info.is_dir():continue
 path=view/n;path.parent.mkdir(parents=True,exist_ok=True);data=z.read(info);path.write_bytes(data);protected[str(path)]=hashlib.sha256(data).hexdigest()
source.NATIVE=root;shutil.copytree(view/'view/parent',root/'selected')
out=Path('select650-gate-access');out.mkdir();source.identity.DERIVED=out
source.native_material_and_anchors(view/'view/wire',None)
assert all(hashlib.sha256(Path(p).read_bytes()).hexdigest()==h for p,h in protected.items())
gates=json.loads((out/'gate-poly-access.json').read_text());assert gates['count']==200 and len({g['device']for g in gates['gates']})==200
(out/'result.json').write_text(json.dumps(dict(status='PASS_CURRENT650_SERIALIZED_MATERIAL_AND_GATE_ACCESS_READBACK',source_run=r['id'],artifact=m['id'],source_gds_sha256=hashlib.sha256((root/'selected/layout/nssoc_cdr_pd500_resistor_v59.gds').read_bytes()).hexdigest(),actual_gates=200,gate_poly_RC_extracted=False,full_phy_accepted=False),indent=2))

# Work on a separate copy: the authenticated producer archive remains immutable.
working=root/'contact-view';shutil.copytree(view/'view',working)
method=Path('scripts/select650_physical_gate_contacts_method.py')
assert hashlib.sha256(method.read_bytes()).hexdigest()=='26796d78961d5873b84f21fc6084e8f309645bdda38c96f9db833e5fc8997a1b'
worker=working/'wire/physical_gate_contacts.py';worker.write_bytes(method.read_bytes())
p=subprocess.run(['python3','-B',str(worker)],capture_output=True,text=True,timeout=600)
(out/'contacts.stdout').write_text(p.stdout);(out/'contacts.stderr').write_text(p.stderr)
assert p.returncode==0, 'physical gate contact extraction failed; inspect native diagnostics'
anchors=json.loads((working/'wire/anchors03.json').read_text())
assert anchors['physical_gate_contact_count']==200 and not anchors['intrinsic_gate_metal_shortcuts']
assert len(anchors['rows'])==2046 and len(anchors['anchors'])==1428 and len(anchors['gate_groups'])==50
assert all(hashlib.sha256(Path(p).read_bytes()).hexdigest()==h for p,h in protected.items())
shutil.copy2(working/'wire/anchors03.json',out/'physical-gate-anchors.json')
(out/'contact-result.json').write_text(json.dumps(dict(status='PASS_CURRENT650_PHYSICAL_GATE_CONTACT_ANCHORS',source_run=r['id'],source_gds_sha256=hashlib.sha256((working/'parent/layout/nssoc_cdr_pd500_resistor_v59.gds').read_bytes()).hexdigest(),method_sha256='26796d78961d5873b84f21fc6084e8f309645bdda38c96f9db833e5fc8997a1b',actual_gate_contacts=200,gate_groups=50,physical_anchors=1428,metal_rc_regeneration_required=True,gate_poly_RC_extracted=False,full_phy_accepted=False),indent=2))
