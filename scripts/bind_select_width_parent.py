import json,hashlib
from pathlib import Path
import pya
import cdr_mos650_metal_rc as source
out=Path('select-parent-binding');out.mkdir()
source.NATIVE=Path('select-parent-native');source.NATIVE.mkdir()
source.DERIVED=out
cfg=json.loads(Path(source.CFG).read_bytes())
parent=source.NATIVE/'parent'
source.acquire(cfg['view'],parent,lambda n:n.startswith(('native/view/','native/selected/','derived/')))
g=pya.Layout();g.read(str(parent/'native/selected/layout/nssoc_cdr_pd500_resistor_v59.gds'))
b=pya.Layout();b.read('hw/soc/out/select-width-baseline/nssoc_cdr_select_feedforward_layout_v1.gds')
bt=b.top_cell();assert g.dbu==b.dbu==.001
matches=[];candidates=[];paths=[]
for c in g.each_cell():
 if 'select' not in c.name.lower():continue
 layers={(i.layer,i.datatype)for i in b.layer_infos()}|{(i.layer,i.datatype)for i in g.layer_infos()}
 differences=[]
 for layer,datatype in sorted(layers):
  left=pya.Region(c.begin_shapes_rec(g.layer(layer,datatype))).merged()
  right=pya.Region(bt.begin_shapes_rec(b.layer(layer,datatype))).merged()
  delta=(left^right).merged()
  if not delta.is_empty():differences.append(dict(layer=layer,datatype=datatype,area=delta.area(),bbox=str(delta.bbox())))
 row=dict(name=c.name,bbox=str(c.bbox()),differences=differences)
 candidates.append(row)
 if not differences:matches.append(c.name)
def visit(c,path):
 for i,inst in enumerate(c.each_inst()):
  step=dict(parent=c.name,ordinal=i,child=inst.cell.name,transform=str(inst.dcplx_trans),array=inst.is_regular_array())
  if inst.cell.name in [x['name']for x in candidates]:paths.append(path+[step])
  visit(inst.cell,path+[step])
visit(g.top_cell(),[])
assert candidates and paths,'No physical select cell found; inspect parent before changing geometry'
(out/'binding.json').write_text(json.dumps(dict(status='READ_ONLY_SELECT_PARENT_GEOMETRY_COMPARISON',parent_gds_sha256=hashlib.sha256((parent/'native/selected/layout/nssoc_cdr_pd500_resistor_v59.gds').read_bytes()).hexdigest(),baseline_gds_sha256=hashlib.sha256(Path('hw/soc/out/select-width-baseline/nssoc_cdr_select_feedforward_layout_v1.gds').read_bytes()).hexdigest(),candidates=candidates,exact_matches=matches,paths=paths,geometry_modified=False,full_phy_accepted=False),indent=2))

c=g.cell('pd_child_rc_select');assert c is not None
details={}
for label,layout,cell in [('parent',g,c),('baseline',b,bt)]:
 markers={}
 for layer,datatype in [(8,2),(67,2),(67,25)]:
  it=cell.begin_shapes_rec(layout.layer(layer,datatype));shapes=[]
  while not it.at_end():
   shape=it.shape()
   shapes.append(dict(shape=str(shape),transform=str(it.trans())))
   it.next()
  markers[str(layer)+'/'+str(datatype)]=shapes
 details[label]=markers
schematic=(parent/'native/selected/layout/schematic.cir').read_text()
lines=[line for line in schematic.splitlines() if 'SE_D' in line.upper()]
assert lines,'Expected select passive schematic names absent'
(out/'integration-inputs.json').write_text(json.dumps(dict(markers=details,schematic_select_lines=lines,schematic_sha256=hashlib.sha256(schematic.encode()).hexdigest()),indent=2))
