# SPDX-License-Identifier: Apache-2.0
"""Build a collision-free two-macro library from strict native LVS passes."""
import pathlib,json,hashlib,zipfile,tarfile,io
import klayout.db as db
from namespace_sram_macro import geometry,cards
P=pathlib.Path
configs={
 'dp':{'native':'1b536d31758f4abf1fb7af4700a59fd64d891e41044ec1f1230da02b84a324c1','derived':'9e33da59fb0b406e08dfeb288309b84caf70df6bd94050e005d7c394e0ee62dc','matches':26,'top':'RM_IHPSG13_2P_256x16_c2_bm_bist'},
 'sp':{'native':'13b66b4e31ad144bd9d47e5a209845027b76d23ff3dc1183d94a45de104bf4f3','derived':'ce9bcb8420b47b618b912c57e74fb6d37a4de27fcf92817770e5877bdc12d8c2','matches':25,'top':'RM_IHPSG13_1P_2048x64_c2_bm_bist'}}
P('out').mkdir();bundle=P('bundle');bundle.mkdir()
expected_cells={};definitions={};libraries={};inputs={};dbu=None
for kind,cfg in configs.items():
 for role in ['native','derived']:
  raw=P(kind+'-'+role+'.zip').read_bytes();assert hashlib.sha256(raw).hexdigest()==cfg[role]
  if role=='derived':
   z=zipfile.ZipFile(io.BytesIO(raw));audit=json.loads(z.read('derived/audit.json'));proof=json.loads(z.read('derived/namespace-proof.json'));result=json.loads(z.read('derived/bounded-result.json'))
   assert audit['status']=='PASS within comparison scope' and audit['circuit_status_counts']=={'Match':cfg['matches']} and not audit['reasons'] and not audit['extraction_diagnostics']
   assert result['returncode']==result['audit_returncode']==0 and result['comparison_passed_within_diagnostic_scope']
   assert proof['reversible_all_records'] and proof['top_ports_unchanged'] and proof['physical_geometry_and_instances_unchanged_after_roundtrip']
 # Independently locate the exact proven physical and reference files.
 z=zipfile.ZipFile(kind+'-native.zip');assert z.namelist()==['namespaced-native.tgz']
 with tarfile.open(fileobj=io.BytesIO(z.read('namespaced-native.tgz')),mode='r:gz') as t:
  reference=t.extractfile('native/engineering-reference-v1.cdl').read();assert hashlib.sha256(reference).hexdigest()==proof['namespaced_reference_sha256']
  candidates=[]
  for m in t.getmembers():
   if m.isfile() and m.name.lower().endswith('.gds'):
    value=t.extractfile(m).read()
    if hashlib.sha256(value).hexdigest()==proof['namespaced_gds_sha256']:candidates.append(value)
  assert candidates and all(v==candidates[0] for v in candidates)
 (bundle/(kind+'.gds')).write_bytes(candidates[0]);(bundle/(kind+'.cdl')).write_bytes(reference)
 layout=db.Layout();layout.read(str(bundle/(kind+'.gds')));snapshot=geometry(layout)
 if dbu is None:dbu=snapshot['dbu']
 assert dbu==snapshot['dbu'] and not expected_cells.keys()&snapshot['cells'].keys()
 expected_cells.update(snapshot['cells'])
 records=cards(reference.decode());names=[r[1] for r in records if r[0]=='.SUBCKT'];assert len(names)==145 and len(set(names))==145 and not definitions.keys()&set(names)
 definitions.update({n:kind for n in names});libraries[kind]=records
 assert {r[0] for r in records if r[0].startswith('.')}-{'.SUBCKT','.ENDS'}==set(),'Unexpected external directive must be reconciled explicitly'
 inputs[kind]={'top':cfg['top'],'proof':proof,'strict_audit':audit,'archive_sha256':cfg['native'],'derived_sha256':cfg['derived']}
merged=db.Layout()
for kind in configs:merged.read(str(bundle/(kind+'.gds')))
assert geometry(merged)=={'dbu':dbu,'cells':expected_cells}
merged.write(str(bundle/'sram-namespaced.gds'));roundtrip=db.Layout();roundtrip.read(str(bundle/'sram-namespaced.gds'));assert geometry(roundtrip)=={'dbu':dbu,'cells':expected_cells}
combined='* Engineering SRAM library; not foundry signoff\n'+'\n'.join(' '.join(row) for kind in ['dp','sp'] for row in libraries[kind])+'\n'
assert cards(combined)==libraries['dp']+libraries['sp'];assert len(definitions)==290
# All hierarchy calls resolve to a unique retained definition; nodes/values untouched.
for kind,records in libraries.items():
 for row in records:
  if row[0].startswith('X'):
   hits=[token for token in row[1:] if token in definitions];assert len(hits)==1 and definitions[hits[0]]==kind,(kind,row[0],hits)
(bundle/'sram-engineering.cdl').write_text(combined)
# Separate library-top definition counts must not be mistaken for a full-chip LVS run.
manifest={'status':'COLLISION_FREE_MACRO_LIBRARY_BUNDLE','source_run':43596487748,'source_sha':'5a68106d6043c9ad3f8f644bb4eff6492b281b1e','reference_definitions':290,'physical_cells':len(expected_cells),'macro_top_names':[cfg['top'] for cfg in configs.values()],'all_reference_calls_unique_and_within_own_macro_library':True,'complete_physical_geometry_and_instance_roundtrip_unchanged':True,'inputs':inputs,'files':{f.name:{'sha256':hashlib.sha256(f.read_bytes()).hexdigest(),'bytes':f.stat().st_size} for f in bundle.iterdir()},'full_chip_lvs_passed':False,'manufacturing_approval':False,'scope':'Both namespaced macro LVS passes plus lossless library merge. Original macro top interfaces unchanged; no LEF, Liberty or timing change. Engineering references still differ from original vendor resistor definitions. Main-chip assembly and full-chip LVS pending.'}
(bundle/'manifest.json').write_text(json.dumps(manifest,indent=2));P('out/macro-library-bundle.json').write_text(json.dumps(manifest,indent=2))
print(json.dumps({'status':manifest['status'],'reference_definitions':290,'physical_cells':len(expected_cells)}))
