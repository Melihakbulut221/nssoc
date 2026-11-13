# SPDX-License-Identifier: Apache-2.0
import hashlib,json,pathlib,zipfile
import klayout.db as db
from audit_sram_independent_extraction import run,digest
out=pathlib.Path('out');out.mkdir(exist_ok=True)
assert digest('leaf.zip')=='35be261afbc97cb1b555e2678090caf4624424a47127aba3695e5411e8093b33'
assert digest('reference.zip')=='124f6a92fa56346b1c471efb84750878180ef0c8056b2c940c5c6fce0e41e29b'
with zipfile.ZipFile('reference.zip') as z:
 names=[n for n in z.namelist() if n.endswith('reference.spice')];assert len(names)==1
 raw=z.read(names[0]);assert hashlib.sha256(raw).hexdigest()=='64d041383d0ebee7b54dab0bc10d651d31262a2a41ccd15a9c0727dac06e0dd9'
pathlib.Path('reference.spice').write_bytes(raw)
n=db.Netlist();n.read('reference.spice',db.NetlistSpiceReader())
candidates=[c for c in n.each_circuit() if c.name.lower()=='dp8tcell'];assert len(candidates)==1
# Duplicate only the independent leaf into a standalone netlist using SPICE writer
# circuit selection by pruning all parents (no terminal aliases or extracted-derived reference).
leaf=candidates[0]
for c in list(n.each_circuit()):
 if c.name!=leaf.name:n.remove(c)
n.write('leaf-reference.spice',db.NetlistSpiceWriter())
raw=pathlib.Path('leaf-reference.spice').read_bytes()
with zipfile.ZipFile('leaf-reference.zip','w') as z:z.writestr('leaf-reference.spice',raw)
config={'expected_mos':8,'source_geometry_sha256':'c6a1be71d0439e88e2c08729345eb8d8001f773266cb7a8b939446e54999ff45'}
with zipfile.ZipFile('leaf.zip') as z:
 for mode,sha in [('CC','cbc7dca6e387a67db742336a5f232184ea30e044c18c33c0c5fd77b516c0d57d'),('RC','77b35e72ed46865efaaf440cecfad07c78e4468fc1dad193cc94f19651c94dde')]:
  names=[p for p in z.namelist() if p.startswith(mode+'/') and p.endswith('/DP8TCell_k25d_pex_netlist.spice')];assert len(names)==1
  config[mode.lower()]={'archive':'leaf.zip','archive_sha256':digest('leaf.zip'),'member':names[0],'member_sha256':sha}
config['reference']={'archive':'leaf-reference.zip','archive_sha256':digest('leaf-reference.zip'),'member':'leaf-reference.spice','member_sha256':hashlib.sha256(raw).hexdigest()}
r=run(config);(out/'actual-leaf-audit.json').write_text(json.dumps(r,indent=2))
assert r['status']=='FAIL_OR_INCONCLUSIVE',r
assert r['stages']['cc_rc_conservation']['passed'],r
assert r['stages']['independent_mos_topology']=={'passed':False,'error':'ValueError: Graph/pin inventory differs'},r
assert r['independent_inventory']['reference_mos']==r['independent_inventory']['extracted_mos']==8
(out/'boundary-regression.json').write_text(json.dumps({'status':'PASS_EXPECTED_INDEPENDENT_BODY_BOUNDARY_REJECTION','leaf_lvs':False,'macro_lvs':False,'manufacturing_approval':False},indent=2))
print('PASS_EXPECTED_INDEPENDENT_BODY_BOUNDARY_REJECTION')
