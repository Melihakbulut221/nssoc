import hashlib,zipfile,tarfile,io,pathlib,json,collections,importlib.metadata
import klayout.db as kdb
P=pathlib.Path
assert importlib.metadata.version('klayout')=='0.30.13'
blob=P('native.zip').read_bytes();assert hashlib.sha256(blob).hexdigest()=='dd437de8cfc8f81ffe504a5555608eebf3b6f3d401ce9cd4c49d87e362e4e58c'
z=zipfile.ZipFile(io.BytesIO(blob));assert z.namelist()==['native-sp.tgz']
with tarfile.open(fileobj=io.BytesIO(z.read('native-sp.tgz')),mode='r:gz') as t:
 hits=[m for m in t.getmembers() if m.name.endswith('/RM_IHPSG13_1P_2048x64_c2_bm_bist.gds')];assert len(hits)==1
 gds=t.extractfile(hits[0]).read();cdl=t.extractfile('native/engineering-reference-v1.cdl').read()
 logs={m.name:{'sha256':hashlib.sha256(t.extractfile(m).read()).hexdigest(),'tail':t.extractfile(m).read().decode(errors='replace').splitlines()[-30:]} for m in t.getmembers() if m.isfile() and m.name in ['native/run.log','native/deck.log','native/command.json']}
 outputs=[m.name for m in t.getmembers() if m.isfile() and m.name in ['native/lvs.lvsdb','native/extracted.cir']]
assert hashlib.sha256(gds).hexdigest()=='48be5102bf97e56daee4cda1f63eaf6e7bb3450a68d48a2825060b1172011d00'
assert hashlib.sha256(cdl).hexdigest()=='3ef741993177dccaf1be29e34561c2b6d13d4c20dc75b00d6ab72b0a4a972a7c'
P('/tmp/macro.gds').write_bytes(gds);ly=kdb.Layout();ly.read('/tmp/macro.gds')
layout={}
for cell in ly.each_cell():
 children=collections.Counter()
 for inst in cell.each_inst():children[ly.cell(inst.cell_index).name]+=inst.size()
 layout[cell.name]={'children':dict(children)}
lines=[]
for line in cdl.decode().splitlines():
 line=line.strip()
 if not line or line.startswith('*'):continue
 if line.startswith('+'):assert lines;lines[-1]+=' '+line[1:]
 else:lines.append(line)
refs={};active=None
for line in lines:
 tok=line.split();key=tok[0].lower()
 if key=='.subckt':
  assert active is None;active=tok[1];assert active not in refs;refs[active]={'ports':len(tok)-2,'children':{},'direct_primitives':collections.Counter()}
 elif key=='.ends':active=None
 elif active:
  if key.startswith('x'):
   positional=[x for x in tok if '=' not in x];child=positional[-1];refs[active]['children'][child]=refs[active]['children'].get(child,0)+1
  elif key[0] in 'mrqc':refs[active]['direct_primitives'][key[0]]+=1
assert active is None
for row in refs.values():row['direct_primitives']=dict(row['direct_primitives'])
lnames={x.upper() for x in layout};rnames={x.upper() for x in refs}
r={'logs':logs,'final_outputs_present':outputs,'status':'HIERARCHY_INVENTORY_ONLY','accepted':False,'source_run':43566292104,'gds_sha256':hashlib.sha256(gds).hexdigest(),'reference_sha256':hashlib.sha256(cdl).hexdigest(),'layout_cells':layout,'reference_cells':refs,'layout_only_names':sorted(x for x in layout if x.upper() not in rnames),'reference_only_names':sorted(x for x in refs if x.upper() not in lnames),'scope':'Names and instance counts only from unchanged GDS and engineered reference before LVS alignment. No geometry coordinates, connectivity, hierarchy aliasing or acceptance changes. Similar cell names do not prove equivalence.'}
P('out').mkdir();P('out/hierarchy-inventory.json').write_text(json.dumps(r,indent=2))
