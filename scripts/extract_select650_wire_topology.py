import runpy,json,hashlib,subprocess,zipfile,io,shutil,ast
from pathlib import Path
ctx=runpy.run_path('scripts/bind_select650_source_pins.py')
root=Path('select650-wires').resolve();root.mkdir();wire=root/'view/wire';wire.mkdir(parents=True);parent=root/'view/parent';layout=parent/'layout';layout.mkdir(parents=True);physical=parent/'physical/lvs_flat';physical.mkdir(parents=True)
gds=layout/'nssoc_cdr_pd500_resistor_v59.gds';shutil.copyfile(ctx['gpath'],gds)
z=ctx['z'];physical.joinpath('result.lvsdb').write_bytes(z.read('lvs_flat/result.lvsdb'));physical.joinpath('audit.json').write_bytes(z.read('lvs_flat/audit.json'))
record=json.loads((ctx['parent']/'native/selected/layout/result.json').read_text());assert len(record['ports'])==25
record['outputs']={gds.name:hashlib.sha256(gds.read_bytes()).hexdigest()};record['scope']='Original unchanged top ports; candidate physical GDS explicitly rebound, not electrical acceptance.'
(layout/'result.json').write_text(json.dumps(record,indent=2))
shutil.copyfile(ctx['out']/'source-pins.json',wire/'source-pins.json')
P='repos/Melihakbulut221/nssoc/'
def api(s):return json.loads(subprocess.check_output(['gh','api',P+s]))
r=api('actions/runs/43744629838');assert r['conclusion']=='success'and r['head_sha']=='cde4577d1a34093cc3d8a07d612cf605095462e0'and r['run_attempt']==1
m=api('actions/artifacts/14172704736');assert m['workflow_run']['id']==r['id']and m['digest']=='sha256:2d4466696fd5df1c86267c2b90966aed66784af26cb72abf41d92a848e18403a'and not m['expired']
b=subprocess.check_output(['gh','api',P+'actions/artifacts/14172704736/zip']);assert 'sha256:'+hashlib.sha256(b).hexdigest()==m['digest'];ids=zipfile.ZipFile(io.BytesIO(b));flat=json.loads(ids.read('lvs_flat-identity.json'))
for n in ['device-locations01.json','pcell-inventory01.json']:(wire/n).write_bytes(ids.read(n))
assert hashlib.sha256(physical.joinpath('result.lvsdb').read_bytes()).hexdigest()==flat['lvsdb']['sha256']
origin=Path('docs/evidence/cdr-v59-tail-exact-wire-methods-20261026');derivations={}
for name in ['probe01.py','anchors01.py','dedup01.py']:
 s=(origin/name).read_text();h=hashlib.sha256(s.encode()).hexdigest()
 if name=='probe01.py':assert s.count('sg13_lv_nmos=50')==1;s=s.replace('sg13_lv_nmos=50','sg13_lv_nmos=200')
 if name=='anchors01.py':
  old='len(rows)==1446 and len(anchors)==978';assert s.count(old)==1;s=s.replace(old,'len(rows)==2046 and len(anchors)==1428')
  old='PASS_1446_NATIVE_TERMINALS_WITH_953_METAL_AND_493_BODY_REFERENCES';assert s.count(old)==1;s=s.replace(old,'PASS_2046_NATIVE_TERMINALS_WITH_1403_METAL_AND_643_BODY_REFERENCES')
 ast.parse(s);(wire/name).write_text(s);derivations[name]=dict(original_sha256=h,derived_sha256=hashlib.sha256(s.encode()).hexdigest())
 with(root/(name+'.stdout')).open('w')as so,(root/(name+'.stderr')).open('w')as se:subprocess.run(['python3','-B',str(wire/name)],stdout=so,stderr=se,check=True)
import cdr_mos650_wires as validate
graph=json.loads((wire/'native05/result.json').read_text());locations=json.loads((wire/'device-locations01.json').read_text());anchors=json.loads((wire/'anchors03.json').read_text());validate.validate_binding(graph,locations,anchors,flat)
unique=json.loads((wire/'anchors08.json').read_text())
assert unique['logical_anchor_count']==1428 and len(unique['logical_anchor_aliases'])==1428
(root/'result.json').write_text(json.dumps(dict(status='PASS_NEW_SELECT650_WIRE_GRAPH_AND_ALL_TERMINAL_ANCHORS',devices=650,terminals=2046,components=graph['wire_component_count'],electrical_nets=graph['native_electrical_net_count'],logical_anchors=1428,physical_anchors=unique['physical_anchor_count'],derivations=derivations,source_gds_sha256=hashlib.sha256(gds.read_bytes()).hexdigest(),wire_rc_extracted=False,full_phy_accepted=False),indent=2))
