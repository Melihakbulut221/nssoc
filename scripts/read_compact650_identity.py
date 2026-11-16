import subprocess,json,hashlib,zipfile,io,stat
from pathlib import Path,PurePosixPath
import cdr_mos650_identity as identity
P='repos/Melihakbulut221/nssoc/'
def api(s):return json.loads(subprocess.check_output(['gh','api',P+s]))
r=api('actions/runs/43858378437')
assert r['conclusion']=='success' and r['head_sha']=='6004bd73bdccd9582e9e303487a22c8c38ad59fd' and r['run_attempt']==1
items=api('actions/runs/43858378437/artifacts')['artifacts']
matches=[a for a in items if a['name']=='compact650-native-checks-43858378437']
assert len(matches)==1
m=matches[0]
assert m['workflow_run']['id']==r['id'] and m['workflow_run']['head_sha']==r['head_sha'] and not m['expired']
assert m['digest'].startswith('sha256:') and len(m['digest'])==71
b=subprocess.check_output(['gh','api',P+'actions/artifacts/'+str(m['id'])+'/zip'])
assert 'sha256:'+hashlib.sha256(b).hexdigest()==m['digest']
z=zipfile.ZipFile(io.BytesIO(b));assert len(z.namelist())==len(set(z.namelist()))
assert hashlib.sha256(z.read('compact-current650.cir')).hexdigest()=='1cef658f121e0ab0dc33a2c0cacd2dd564ff440413e4a0ab6a4b91de66fca239'
identity.NATIVE=Path('select650-identity-native');identity.NATIVE.mkdir();identity.DERIVED=Path('select650-identity');identity.DERIVED.mkdir()
base=identity.NATIVE/'selected/physical';base.mkdir(parents=True)
for info in z.infolist():
 n=PurePosixPath(info.filename);assert not n.is_absolute()and '..'not in n.parts and not stat.S_ISLNK(info.external_attr>>16)
 if info.is_dir():continue
 path=base/n;path.parent.mkdir(parents=True,exist_ok=True);path.write_bytes(z.read(info))
report=json.loads((base/'result.json').read_text());assert report['status']=='PASS_COMPACT650_DRC_LVS_REQUIRES_FRESH_RC_AND_ELECTRICAL'
assert report['steps']['drc']['measurement']['markers']==0 and report['steps']['drc']['measurement']['category_count']==560
assert report['steps']['wrong_resistor']['status']=='REJECTED_EXPECTED_FAULT'
wanted=identity.expected();changes=[]
for name in ['SE_D0','SE_D1','SE_D3','SE_D4']:
 w=wanted[name];assert w['model']=='rppd'
 for k in ['layout_parameters','schematic_parameters']:assert w[k]['w']==1;w[k]['w']=2
 changes.append(name)
identity.save('reference-plan.json',dict(source_run=r['id'],artifact=m['id'],sha256=m['digest'][7:],changed_reference_names=changes,expected_devices=len(wanted),full_phy_accepted=False,fresh_rc=False))
reports=[identity.native_side(mode,wanted) for mode in ['lvs','lvs_flat']]
def semantic(report):
 return {p['schematic']['expanded_name']:dict(model=p['layout']['model'],parameters=p['layout']['parameters'],source=p['original_source']) for p in report['pairs']}
assert semantic(reports[0])==semantic(reports[1])
assert all(v['terminal_count']==2046 and len(v['ports'])==25 for v in reports)
identity.save('result.json',dict(status='PASS_ACTUAL650_SELECT_WIDTH2_INDEPENDENT_NATIVE_IDENTITIES',devices=650,changed_reference_names=changes,full_phy_accepted=False,fresh_rc=False))

import shutil
view=identity.NATIVE/'view';wire=view/'wire';wire.mkdir(parents=True)
layout=view/'parent/layout';layout.mkdir(parents=True)
physical=view/'parent/physical/lvs_flat';physical.mkdir(parents=True)
gds=base/'compact-current650.gds';assert hashlib.sha256(gds.read_bytes()).hexdigest()=='1337c86e9bf28e68d93d3dcc2c80afc3040ecd7f21b32eb6b149896aa3490e11'
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
