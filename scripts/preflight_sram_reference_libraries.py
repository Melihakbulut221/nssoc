# SPDX-License-Identifier: Apache-2.0
"""Cloud-only preflight of the two verified engineering SRAM reference libraries."""
import hashlib,json,zipfile,tarfile,io,pathlib
import klayout.db as db
P=pathlib.Path
layouts={}
gds_hashes={'dp':'420b5223d14e2f873a2464849e3decbbec2b5b16b3c6a0f8cd2bb21b0d52365b','sp':'48be5102bf97e56daee4cda1f63eaf6e7bb3450a68d48a2825060b1172011d00'}
configs={
 'dp':('bff8640c1efc79d3877f3ececa08d369d5c80bbc81556c13284e540566aa260e','1b8f2b6d11af2956fa0caf074b8329bf2e49722a4c5ce954c2119ad9ae4992b0'),
 'sp':('0f1064d309dfe7e2e91d448e10ebc0f3234f046f9858fc67f94903cb8a76ece6','3ef741993177dccaf1be29e34561c2b6d13d4c20dc75b00d6ab72b0a4a972a7c')}
libs={};evidence={}
for kind,(archive_hash,reference_hash) in configs.items():
 raw=P(kind+'.zip').read_bytes();assert hashlib.sha256(raw).hexdigest()==archive_hash
 z=zipfile.ZipFile(io.BytesIO(raw));assert z.namelist()==['bounded-native.tgz']
 with tarfile.open(fileobj=io.BytesIO(z.read('bounded-native.tgz')),mode='r:gz') as t:
  raw=t.extractfile('native/engineering-reference-v1.cdl').read()
  candidates=[]
  for member in t.getmembers():
   if member.isfile() and member.name.lower().endswith('.gds'):
    data=t.extractfile(member).read()
    if hashlib.sha256(data).hexdigest()==gds_hashes[kind]:candidates.append(data)
  assert candidates and all(b==candidates[0] for b in candidates)
  P(kind+'.gds').write_bytes(candidates[0]);layout=db.Layout();layout.read(kind+'.gds');layouts[kind]=layout

 assert hashlib.sha256(raw).hexdigest()==reference_hash
 cells={};current=None;records=[];outside=[]
 for line in raw.decode().splitlines():
  line=line.strip()
  if not line or line.startswith('*'):continue
  tokens=line.upper().split()
  if tokens[0]=='.SUBCKT':
   assert current is None and len(tokens)>2
   current=tokens[1];assert current not in cells;records=[tokens]
  elif tokens[0]=='.ENDS':
   assert current is not None
   assert len(tokens)==1 or tokens[1]==current
   cells[current]=records;current=None;records=[]
  elif current is not None:
   if tokens[0]=='+':assert records;records[-1]+=tokens[1:]
   else:records.append(tokens)
  else:outside.append(tokens)
 assert current is None and cells
 libs[kind]=cells
 evidence[kind]={'reference_sha256':reference_hash,'cell_count':len(cells),'cells':{n:{'sha256':hashlib.sha256(json.dumps(rows).encode()).hexdigest(),'ports':len(rows[0])-2,'records':len(rows)-1} for n,rows in cells.items()},'outside_directive_types':sorted({r[0] for r in outside})}
common=sorted(libs['sp'].keys()&libs['dp'].keys());identical=[];different=[]
for name in common:
 (identical if libs['sp'][name]==libs['dp'][name] else different).append(name)
geometry={}
for name in common:
 geometry[name]={}
 for kind,layout in layouts.items():
  hits=[c for c in layout.each_cell() if c.name.upper()==name];assert len(hits)==1,(kind,name)
  c=hits[0];layers=[];canonical=[]
  for li in layout.layer_indexes():
   info=layout.get_info(li);shapes=sorted(shape.to_s() for shape in c.shapes(li).each())
   if shapes:
    layers.append({'layer':info.layer,'datatype':info.datatype,'shape_count':len(shapes)})
    canonical.append((info.layer,info.datatype,shapes))
  instances=sorted((layout.cell(i.cell_index).name,i.to_s()) for i in c.each_inst())
  geometry[name][kind]={'dbu':layout.dbu,'bbox_dbu':c.bbox().to_s(),'layers':layers,'instances':len(instances),'direct_geometry_sha256':hashlib.sha256(json.dumps([sorted(canonical),instances]).encode()).hexdigest()}
 geometry[name]['same_direct_geometry']=geometry[name]['dp']['dbu']==geometry[name]['sp']['dbu'] and geometry[name]['dp']['direct_geometry_sha256']==geometry[name]['sp']['direct_geometry_sha256']
reference_differences={name:{kind:libs[kind][name] for kind in ['dp','sp']} for name in different}
r={'status':'REFERENCE_LIBRARY_COLLISION_PREFLIGHT','accepted':False,'full_chip_lvs_passed':False,'manufacturing_approval':False,'libraries':evidence,'common_cell_geometry':geometry,'reference_difference_records':reference_differences,'identical_shared_cells':identical,'different_shared_cells':different,'scope':'Pinned original GDS direct shared-cell geometry and case/whitespace/continuation-normalized subcircuit records; geometry hashes include labels and are not electrical equivalence proof; differing definitions cannot be merged by name. No geometry or circuit edits, no electrical equivalence claim.'}
P('out').mkdir();P('out/reference-library-preflight.json').write_text(json.dumps(r,indent=2))
print(json.dumps({'common':len(common),'identical':len(identical),'different':different}))
