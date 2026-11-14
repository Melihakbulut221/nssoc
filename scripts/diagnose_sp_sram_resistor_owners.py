# SPDX-License-Identifier: Apache-2.0
"""Aggregate original CDL/GDS resistor ownership in cloud; never LVS acceptance."""
import pathlib,zipfile,tarfile,io,hashlib,json,collections,re
import klayout.db as db
P=pathlib.Path
payload=P('pkg.tgz').read_bytes()
assert hashlib.sha256(payload).hexdigest()=='822dab7067d901fa79dabffffff784baf5c9965f0a5091eba67acdc48b9956f4'
with tarfile.open(fileobj=io.BytesIO(payload),mode='r:gz') as t:
 contracts=[m for m in t.getmembers() if m.isfile() and m.name.endswith('/input-contract.json')];assert len(contracts)==1
 contract=json.loads(t.extractfile(contracts[0]).read());prefix=str(P(contracts[0].name).parent)+'/files/'
 def get(suffix):
  names=[n for n in contract['input_files'] if n.endswith(suffix)];assert len(names)==1
  name=names[0];data=t.extractfile(prefix+name).read();assert hashlib.sha256(data).hexdigest()==contract['input_files'][name]['sha256'];return data
 gds=get('/RM_IHPSG13_1P_2048x64_c2_bm_bist.gds');cdl=get('/RM_IHPSG13_1P_2048x64_c2_bm_bist.cdl')
assert hashlib.sha256(gds).hexdigest()=='48be5102bf97e56daee4cda1f63eaf6e7bb3450a68d48a2825060b1172011d00'
assert hashlib.sha256(cdl).hexdigest()=='734647f8383209c7e08fc8e66a2914a3acaa33e1848b9ff33b6a4a2ed3c2ec61'
logical=[]
for line in cdl.decode().splitlines():
 line=line.strip()
 if not line or line.startswith('*'):continue
 if line.startswith('+'):
  assert logical;logical[-1]+=' '+line[1:].strip()
 else:logical.append(line)
cells={};current=None
for line in logical:
 tokens=line.split()
 if tokens[0].lower()=='.subckt':
  current=tokens[1].casefold();assert current not in cells
  cells[current]={'name':tokens[1],'resistors':[],'children':collections.Counter()}
 elif tokens[0].lower()=='.ends':current=None
 elif current is not None:
  if tokens[0][0].lower()=='r' and re.search(r'\blvsres\b',line,re.I):
   params={k.lower():v for k,v in re.findall(r'\b(W|L|WIDTH|LENGTH|M|S|LAYER)\s*=\s*([^\s]+)',line,re.I)}
   cells[current]['resistors'].append({'instance':tokens[0],'parameters':params})
  elif tokens[0][0].lower()=='x':
   plain=line.split('=',1)[0].split()
   # No instance parameters are expected; reject rather than silently infer model.
   assert '=' not in line,'Parameterized X instance requires explicit parser'
   model=plain[-1].casefold();cells[current]['children'][model]+=1
assert current is None
missing=collections.Counter()
def inventory(name,active):
 if name not in cells:missing[name]+=1;return collections.Counter()
 assert name not in active;active=active|{name};c=cells[name]
 count=collections.Counter({name:len(c['resistors'])}) if c['resistors'] else collections.Counter()
 for child,n in c['children'].items():
  for k,v in inventory(child,active).items():count[k]+=n*v
 return count
topname='RM_IHPSG13_1P_2048x64_c2_bm_bist';expanded=inventory(topname.casefold(),set())
P('original.gds').write_bytes(gds);layout=db.Layout();layout.read('original.gds')
byname={c.name.casefold():c for c in layout.each_cell()};assert len(byname)==layout.cells()
def geometry(cell):
 rows=[]
 for number,metal in [(8,'metal1'),(10,'metal2'),(30,'metal3')]:
  def reg(dt):
   idx=layout.find_layer(number,dt)
   return db.Region(cell.begin_shapes_rec(idx)) if idx is not None else db.Region()
  res=(((reg(0)+reg(22))-reg(24))&reg(29)).merged();counts=collections.Counter();nonrect=0
  for poly in res.each():
   box=poly.bbox();nonrect+=int(box.area()!=poly.area())
   dims=tuple(sorted((round(box.width()*layout.dbu,12),round(box.height()*layout.dbu,12))));counts[dims]+=1
  if counts:rows.append({'metal':metal,'nonrectangular':nonrect,'dimensions':[{'width_um':k[0],'length_um':k[1],'count':v} for k,v in sorted(counts.items())]})
 return rows
owners=[]
for name,total in sorted(expanded.items()):
 c=cells[name];cell=byname.get(name);geo=geometry(cell) if cell is not None else None
 owners.append({'cell':c['name'],'direct_reference_resistors':len(c['resistors']),'expanded_reference_resistors_in_top':total,
  'instance_parameters':c['resistors'],'direct_child_types':dict(c['children']),
  'matching_gds_cell':cell.name if cell is not None else None,'recursive_geometry':geo})
r={'scope':'Original hierarchical cell resistor ownership and dimensions only. No netlist, geometry coordinates or connections exported. Not a reference correction, connectivity proof or LVS acceptance.',
 'input_release_asset':663146895,'source_sha':__import__('os').environ['GITHUB_SHA'],'gds_sha256':hashlib.sha256(gds).hexdigest(),'cdl_sha256':hashlib.sha256(cdl).hexdigest(),
 'expanded_reference_resistor_count':sum(expanded.values()),'unresolved_child_types':dict(missing),'owners':owners,'top_geometry':None,'top_geometry_scope':'Whole-macro polygon expansion intentionally not computed; owner-cell geometry and marker leaves inspected only','production_accepted':False}
# Original GDS hierarchy does not necessarily retain CDL subcircuit names.
# Export only ownership/count metadata to locate the physical owners first.
r['layout_cell_names']=sorted(c.name for c in layout.each_cell())
r['layout_marker_owners']=[]
for cell in layout.each_cell():
 local={}
 for number,metal in [(8,'metal1'),(10,'metal2'),(30,'metal3')]:
  idx=layout.find_layer(number,29)
  if idx is not None:
   count=sum(1 for shape in cell.shapes(idx).each() if shape.is_box() or shape.is_polygon() or shape.is_path())
   if count:local[metal]=count
 if local:r['layout_marker_owners'].append({'cell':cell.name,'local_marker_shapes':local,'recursive_geometry':geometry(cell)})
P('out').mkdir();P('out/resistor-owners.json').write_text(json.dumps(r,indent=2))
assert not missing,'Unresolved reference child circuits'
assert sum(expanded.values())>0,'No original generic LVSRES inventory discovered'
assert topname.casefold() in byname,'Original physical macro top missing'
print(json.dumps({'reference_resistors':sum(expanded.values()),'owner_cells':len(owners)}))
