import runpy,json,hashlib,subprocess,zipfile,io,shutil,ast
from pathlib import Path
ctx=runpy.run_path('scripts/bind_select650_source_pins.py')
root=Path('select650-wires').resolve();root.mkdir();wire=root/'view/wire';wire.mkdir(parents=True);parent=root/'view/parent';layout=parent/'layout';layout.mkdir(parents=True);physical=parent/'physical/lvs_flat';physical.mkdir(parents=True)
gds=layout/'nssoc_cdr_pd500_resistor_v59.gds';shutil.copyfile(ctx['gpath'],gds)
z=ctx['z'];physical.joinpath('result.lvsdb').write_bytes(z.read('lvs_flat/result.lvsdb'));physical.joinpath('audit.json').write_bytes(z.read('lvs_flat/audit.json'))
P='repos/Melihakbulut221/nssoc/'
def api(s):return json.loads(subprocess.check_output(['gh','api',P+s]))
pr=api('actions/runs/43858046204');assert pr['conclusion']=='success' and pr['head_sha']=='b192b6fc472d3e499d2cffc000c76570827a7bb3' and pr['run_attempt']==1
pm=api('actions/artifacts/14222565886');assert pm['workflow_run']['id']==pr['id'] and pm['digest']=='sha256:d10b7501ffbaa69a2469aecd1acd0067b3646363448fc18489b3e272c2621544' and not pm['expired']
pb=subprocess.check_output(['gh','api',P+'actions/artifacts/14222565886/zip']);assert 'sha256:'+hashlib.sha256(pb).hexdigest()==pm['digest'];pz=zipfile.ZipFile(io.BytesIO(pb))
proof=json.loads(pz.read('compact-result.json'));assert proof['serialized_pin_labels_verified']
assert hashlib.sha256(pz.read('compact-current650.gds')).hexdigest()==hashlib.sha256(gds.read_bytes()).hexdigest()=='1337c86e9bf28e68d93d3dcc2c80afc3040ecd7f21b32eb6b149896aa3490e11'
record=json.loads(pz.read('source-metadata.json'));labels=json.loads(pz.read('text-diagnostic.json'))
import klayout.db as db
source_labels={q['string']:q for q in labels['source']}
new_labels={q['string']:q for q in labels['serialized']}
assert len(source_labels)==len(new_labels)==len(record['ports'])==25 and set(record['ports'])==set(new_labels)==set(source_labels)
native=db.Layout();native.read(str(gds));top=native.top_cell();assert native.dbu==.001
metal=db.Region(top.begin_shapes_rec(native.layer(134,0))).merged()
for name,value in list(record['ports'].items()):
 old=source_labels[name];new=new_labels[name]
 assert old['layer']==new['layer']=='134/25' and old['x']==new['x']
 rect=db.DBox.from_s(value)
 assert abs(rect.center().x-old['x']*.001)<1e-9 and abs(rect.center().y-old['y']*.001)<1e-9
 moved=rect.transformed(db.DTrans(0,False,0,(new['y']-old['y'])*.001))
 assert abs(moved.center().x-new['x']*.001)<1e-9 and abs(moved.center().y-new['y']*.001)<1e-9
 assert (db.Region(moved.to_itype(native.dbu))-metal).is_empty(),('port outside native metal',name)
 record['ports'][name]=str(moved)
record['outputs']={gds.name:hashlib.sha256(gds.read_bytes()).hexdigest()}
record['scope']='Compact650 top ports rebound by verified serialized label displacement and actual metal enclosure. No electrical acceptance.'
record['physical_acceptance']=False;record['qualified_pex']=False;record['serial_phy_complete']=False
(layout/'result.json').write_text(json.dumps(record,indent=2))
shutil.copyfile(ctx['out']/'source-pins.json',wire/'source-pins.json')
P='repos/Melihakbulut221/nssoc/'
def api(s):return json.loads(subprocess.check_output(['gh','api',P+s]))
r=api('actions/runs/43858886164');assert r['conclusion']=='success'and r['head_sha']=='556dd5c9bc992e3df924039bf04c731d49e2b98e'and r['run_attempt']==1
m=api('actions/artifacts/14223215265');assert m['workflow_run']['id']==r['id']and m['digest']=='sha256:3c3e4373bbddf712150e445cacc58e0e6ffd4cc169c95eb691065cdedb6c0bbf'and not m['expired']
b=subprocess.check_output(['gh','api',P+'actions/artifacts/14223215265/zip']);assert 'sha256:'+hashlib.sha256(b).hexdigest()==m['digest'];ids=zipfile.ZipFile(io.BytesIO(b));flat=json.loads(ids.read('lvs_flat-identity.json'))
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
