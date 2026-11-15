import runpy,json,hashlib,subprocess,zipfile,io,shutil,ast
from pathlib import Path
ctx=runpy.run_path('scripts/bind_select650_source_pins.py')
root=Path('select650-wires').resolve();root.mkdir();wire=root/'view/wire';wire.mkdir(parents=True);parent=root/'view/parent';layout=parent/'layout';layout.mkdir(parents=True);physical=parent/'physical/lvs_flat';physical.mkdir(parents=True)
gds=layout/'nssoc_cdr_pd500_resistor_v59.gds';shutil.copyfile(ctx['gpath'],gds)
z=ctx['z'];physical.joinpath('result.lvsdb').write_bytes(z.read('lvs_flat/result.lvsdb'));physical.joinpath('audit.json').write_bytes(z.read('lvs_flat/audit.json'))
P='repos/Melihakbulut221/nssoc/'
def api(s):return json.loads(subprocess.check_output(['gh','api',P+s]))
pr=api('actions/runs/43695046876');assert pr['conclusion']=='success'and pr['head_sha']=='7c253a13438932af701b33f6c9d6c76f2ddfa6b5'and pr['run_attempt']==1
pm=api('actions/artifacts/14154400256');assert pm['workflow_run']['id']==pr['id']and pm['digest']=='sha256:c79134cba9fcd33d749903b93d9a71b940771c3da7266ad4b1ed4ff051600248'and not pm['expired']
pb=subprocess.check_output(['gh','api',P+'actions/artifacts/14154400256/zip']);assert 'sha256:'+hashlib.sha256(pb).hexdigest()==pm['digest'];pz=zipfile.ZipFile(io.BytesIO(pb))
record=json.loads(pz.read('hw/soc/out/cloud-cdr-wire-shortcuts-physical/layout/result.json'));assert len(record['ports'])==25
assert hashlib.sha256(pz.read('hw/soc/out/cloud-cdr-wire-shortcuts-physical/layout/nssoc_cdr_pd500_resistor_v59.gds')).hexdigest()=='6023cf16271d3d49307b3967b056b4b11bfaa5534254dc89ba60f3dc21b6f82a'

record['outputs']={gds.name:hashlib.sha256(gds.read_bytes()).hexdigest()};record['scope']='Current clock650 unchanged top ports; candidate physical GDS explicitly rebound, not electrical acceptance.'
(layout/'result.json').write_text(json.dumps(record,indent=2))
shutil.copyfile(ctx['out']/'source-pins.json',wire/'source-pins.json')
P='repos/Melihakbulut221/nssoc/'
def api(s):return json.loads(subprocess.check_output(['gh','api',P+s]))
r=api('actions/runs/43748580179');assert r['conclusion']=='success'and r['head_sha']=='4602a2710cea2b2322cb035750dad9738d9583f4'and r['run_attempt']==1
m=api('actions/artifacts/14175207602');assert m['workflow_run']['id']==r['id']and m['digest']=='sha256:0e41bbf406fb1518a17ee41e49814758ebd32ad9fc880e5adaaa864ae00630bc'and not m['expired']
b=subprocess.check_output(['gh','api',P+'actions/artifacts/14175207602/zip']);assert 'sha256:'+hashlib.sha256(b).hexdigest()==m['digest'];ids=zipfile.ZipFile(io.BytesIO(b));flat=json.loads(ids.read('lvs_flat-identity.json'))
for n in ['device-locations01.json','pcell-inventory01.json']:(wire/n).write_bytes(ids.read(n))
assert hashlib.sha256(physical.joinpath('result.lvsdb').read_bytes()).hexdigest()==flat['lvsdb']['sha256']
origin=Path('docs/evidence/cdr-v59-tail-exact-wire-methods-20261026');derivations={}
for name in ['probe01.py','anchors01.py','dedup01.py']:
 s=(origin/name).read_text();h=hashlib.sha256(s.encode()).hexdigest()
 if name=='probe01.py':assert s.count('sg13_lv_nmos=50')==1;s=s.replace('sg13_lv_nmos=50','sg13_lv_nmos=200')
 if name=='anchors01.py':s=Path('scripts/select650_current_gate_anchors.py').read_text()
 ast.parse(s);(wire/name).write_text(s);derivations[name]=dict(original_sha256=h,derived_sha256=hashlib.sha256(s.encode()).hexdigest())
 with(root/(name+'.stdout')).open('w')as so,(root/(name+'.stderr')).open('w')as se:subprocess.run(['python3','-B',str(wire/name)],stdout=so,stderr=se,check=True)
import select650_current_wire_checks as validate
graph=json.loads((wire/'native05/result.json').read_text());locations=json.loads((wire/'device-locations01.json').read_text());anchors=json.loads((wire/'anchors03.json').read_text());validate.validate_binding(graph,locations,anchors,flat)
validate.NATIVE=root;shutil.copytree(parent,root/'selected');validate.identity.DERIVED=root
validate.native_material_and_anchors(wire,flat)
unique=json.loads((wire/'anchors08.json').read_text())
assert unique['physical_anchor_count']==1428 and anchors['physical_gate_contact_count']==200 and not anchors['intrinsic_gate_metal_shortcuts']
assert unique['logical_anchor_count']==1428 and len(unique['logical_anchor_aliases'])==1428
(root/'result.json').write_text(json.dumps(dict(status='PASS_NEW_SELECT650_WIRE_GRAPH_AND_ALL_TERMINAL_ANCHORS',devices=650,terminals=2046,components=graph['wire_component_count'],electrical_nets=graph['native_electrical_net_count'],logical_anchors=1428,physical_anchors=unique['physical_anchor_count'],derivations=derivations,source_gds_sha256=hashlib.sha256(gds.read_bytes()).hexdigest(),wire_rc_extracted=False,full_phy_accepted=False),indent=2))
