import subprocess,json,hashlib,zipfile,io,stat
from pathlib import Path,PurePosixPath
import cdr_mos650_identity as identity
P='repos/Melihakbulut221/nssoc/'
def api(s):return json.loads(subprocess.check_output(['gh','api',P+s]))
r=api('actions/runs/43748270188');assert r['conclusion']=='success' and r['head_sha']=='4a37a0285be11fc7d424daa830887ec7bde5654b' and r['run_attempt']==1
m=api('actions/artifacts/14175765192');assert m['workflow_run']['id']==r['id'] and m['digest']=='sha256:a1381011a37b531184deedcca9e57e6bdba3ce18ac9d7a280ff0f00c1747504a' and not m['expired']
b=subprocess.check_output(['gh','api',P+'actions/artifacts/14175765192/zip']);assert 'sha256:'+hashlib.sha256(b).hexdigest()==m['digest'];z=zipfile.ZipFile(io.BytesIO(b));assert len(z.namelist())==len(set(z.namelist()))
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

import shutil
view=identity.NATIVE/'view';wire=view/'wire';wire.mkdir(parents=True)
layout=view/'parent/layout';layout.mkdir(parents=True)
physical=view/'parent/physical/lvs_flat';physical.mkdir(parents=True)
gds=base/'candidate650-select-width2.gds';assert hashlib.sha256(gds.read_bytes()).hexdigest()=='5f66ce0cb46acfb580b517ba02b10f66560ba4200d9cfbba0b633a839cc59c5a'
shutil.copyfile(gds,layout/'nssoc_cdr_pd500_resistor_v59.gds')
shutil.copyfile(base/'lvs_flat/result.lvsdb',physical/'result.lvsdb')
method=Path('docs/evidence/cdr-v59-tail-exact-wire-methods-20261026/locate01.py').read_text()
assert method.count('==500')==2 and method.count('ALL_500_DEVICES')==1
method=method.replace('==500','==650').replace('ALL_500_DEVICES','ALL_650_DEVICES')
(wire/'locate01.py').write_text(method)
with (identity.DERIVED/'locate.stdout').open('w')as so,(identity.DERIVED/'locate.stderr').open('w')as se:
 subprocess.run(['python3','-B',str(wire/'locate01.py')],stdout=so,stderr=se,check=True)
locations=json.loads((wire/'device-locations01.json').read_text())
flat=json.loads((identity.DERIVED/'lvs_flat-identity.json').read_text())
expected={row['layout']['id']:row['layout']for row in flat['pairs']}
assert len(locations['devices'])==650 and len({row['native_id']for row in locations['devices']})==650
for row in locations['devices']:
 want=expected[row['native_id']]
 assert row['model'].lower()==want['model'] and row['parameters']==want['parameters']
 for terminal in row['terminals']:assert terminal['native_cluster']==want['terminals'][terminal['name'].upper()]['cluster']
for name in ['device-locations01.json','pcell-inventory01.json']:shutil.copyfile(wire/name,identity.DERIVED/name)
identity.save('location-result.json',dict(status='PASS_650_UNIQUE_PRIMITIVE_ENCLOSURES_AND_INDEPENDENT_TERMINAL_OWNERS',devices=650,terminals=2046,full_phy_accepted=False,fresh_rc=False))
