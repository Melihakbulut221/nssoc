import subprocess,json,hashlib,zipfile,io,stat
from pathlib import Path,PurePosixPath
import cdr_mos650_identity as identity
P='repos/Melihakbulut221/nssoc/'
def api(s):return json.loads(subprocess.check_output(['gh','api',P+s]))
r=api('actions/runs/43743487912');assert r['conclusion']=='success' and r['head_sha']=='6c8c88198f2edb90ed3e649067adfed3ee72b3b5' and r['run_attempt']==1
m=api('actions/artifacts/14173716603');assert m['workflow_run']['id']==r['id'] and m['digest']=='sha256:6f80911d79459c0ba1cf1d0ca23d5e2c53a9e14660707c102c8fc710a511028f' and not m['expired']
b=subprocess.check_output(['gh','api',P+'actions/artifacts/14173716603/zip']);assert 'sha256:'+hashlib.sha256(b).hexdigest()==m['digest'];z=zipfile.ZipFile(io.BytesIO(b));assert len(z.namelist())==len(set(z.namelist()))
identity.NATIVE=Path('select650-identity-native');identity.NATIVE.mkdir();identity.DERIVED=Path('select650-identity');identity.DERIVED.mkdir()
base=identity.NATIVE/'selected/physical';base.mkdir(parents=True)
for info in z.infolist():
 n=PurePosixPath(info.filename);assert not n.is_absolute()and '..'not in n.parts and not stat.S_ISLNK(info.external_attr>>16)
 if info.is_dir():continue
 path=base/n;path.parent.mkdir(parents=True,exist_ok=True);path.write_bytes(z.read(info))
report=json.loads((base/'result.json').read_text());assert report['status']=='PASS_ACTUAL650_SELECT_WIDTH2_DRC_LVS_REQUIRES_FRESH_RC_AND_ELECTRICAL'
assert report['steps']['drc']['measurement']['markers']==0 and report['steps']['drc']['measurement']['category_count']==560
assert report['steps']['wrong_resistor']['status']=='REJECTED_EXPECTED_FAULT'
wanted=identity.expected();changes=[]
for name in ['SE_D0','SE_D1','SE_D3','SE_D4']:
 w=wanted[name];assert w['model']=='rppd'
 for k in ['layout_parameters','schematic_parameters']:assert w[k]['w']==1;w[k]['w']=2
 changes.append(name)
identity.save('reference-plan.json',dict(source_run=r['id'],artifact=m['id'],sha256=m['digest'][7:],changed_reference_names=changes,expected_devices=len(wanted),full_phy_accepted=False,fresh_rc=False))
for mode in ['lvs','lvs_flat']:identity.native_side(mode,wanted)
identity.save('result.json',dict(status='PASS_ACTUAL650_SELECT_WIDTH2_INDEPENDENT_NATIVE_IDENTITIES',devices=650,changed_reference_names=changes,full_phy_accepted=False,fresh_rc=False))
