import json,hashlib
from pathlib import Path
import pya
import cdr_mos650_metal_rc as source
out=Path('select-parent-binding');out.mkdir()
source.NATIVE=Path('select-parent-native');source.NATIVE.mkdir()
source.DERIVED=out
cfg=json.loads(Path(source.CFG).read_bytes())
parent=source.NATIVE/'parent'
# Preserve the qualified clock/gate-contact revision; never rebuild on original650.
import subprocess,zipfile,io
P='repos/Melihakbulut221/nssoc/'
def api(s):return json.loads(subprocess.check_output(['gh','api',P+s]))
run=api('actions/runs/43695046876');assert run['conclusion']=='success' and run['head_sha']=='7c253a13438932af701b33f6c9d6c76f2ddfa6b5' and run['run_attempt']==1
meta=api('actions/artifacts/14154400256');digest='c79134cba9fcd33d749903b93d9a71b940771c3da7266ad4b1ed4ff051600248'
assert meta['workflow_run']['id']==run['id'] and meta['digest']=='sha256:'+digest and not meta['expired']
blob=subprocess.check_output(['gh','api',P+'actions/artifacts/14154400256/zip']);assert hashlib.sha256(blob).hexdigest()==digest
z=zipfile.ZipFile(io.BytesIO(blob));assert len(z.namelist())==len(set(z.namelist()))
prefix='hw/soc/out/cloud-cdr-wire-shortcuts-physical/layout/'
for leaf in ['nssoc_cdr_pd500_resistor_v59.gds','schematic.cir']:
 dst=parent/'native/selected/layout'/leaf;dst.parent.mkdir(parents=True,exist_ok=True);dst.write_bytes(z.read(prefix+leaf))
assert hashlib.sha256((parent/'native/selected/layout/nssoc_cdr_pd500_resistor_v59.gds').read_bytes()).hexdigest()=='6023cf16271d3d49307b3967b056b4b11bfaa5534254dc89ba60f3dc21b6f82a'
(out/'current-parent-acquisition.json').write_text(json.dumps(dict(run=run['id'],head=run['head_sha'],artifact=meta['id'],archive_sha256=digest,current_clock_and_gate_revision_preserved=True),indent=2))

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

# Normalize only the three marker layers proven absent in the authentic parent.
for key in ['8/2','67/2','67/25']:assert details['parent'][key]==[]
for cell in b.each_cell():
 for layer,datatype in [(8,2),(67,2),(67,25)]:cell.shapes(b.layer(layer,datatype)).clear()
def regions(layout,cell):
 return {(layout.get_info(i).layer,layout.get_info(i).datatype):pya.Region(cell.begin_shapes_rec(i)).merged()for i in layout.layer_indexes()}
def equal(left,right):
 for k in set(left)|set(right):assert (left.get(k,pya.Region())^right.get(k,pya.Region())).is_empty(),k


# Current lower metals live outside primitive leaves. Prove their physical presence
# in the entire chip before replacing ONLY the four resistor primitive references.
top=g.top_cell();oldbbox=str(top.bbox());parent_inst=[x for x in top.each_inst()if x.cell.name==c.name];assert len(parent_inst)==1
pt=parent_inst[0].cplx_trans
original={x.cell_index():dict(shapes={str(g.get_info(i)):sorted(str(y)for y in x.each_shape(i))for i in g.layer_indexes()if not x.shapes(i).is_empty()},instances=[(y.cell.name,str(y.cplx_trans),y.na,y.nb,str(y.a),str(y.b))for y in x.each_inst()])for x in g.each_cell()}
variant=pya.Layout();variant.read('hw/soc/out/select-width-rwidth2/nssoc_cdr_select_feedforward_layout_v1_rwidth2_candidate.gds')
assert variant.dbu==g.dbu
for cc in variant.each_cell():
 for la,dt in [(8,2),(67,2),(67,25)]:cc.shapes(variant.layer(la,dt)).clear()
def resistors(cell):return {str(x.cplx_trans):x for x in cell.each_inst()if x.cell.name.split('$')[0]=='rppd'}
old=resistors(c);baseline=resistors(bt);new=resistors(variant.top_cell());assert len(old)==len(baseline)==len(new)==4 and set(old)==set(baseline)==set(new)
rename={};changes=[]
for key,inst in old.items():
 original_cell=inst.cell;reference=baseline[key].cell;candidate=new[key].cell
 assert not list(original_cell.each_inst())and not list(reference.each_inst())and not list(candidate.each_inst())
 cur=regions(g,original_cell);ref=regions(b,reference)
 for layer in set(cur)|set(ref):
  cr=cur.get(layer,pya.Region());rr=ref.get(layer,pya.Region())
  if layer!=(8,0):assert(cr^rr).is_empty(),('unexpected primitive difference',key,layer)
  else:
   assert cr.is_empty()and not rr.is_empty()
   physical=rr.transformed(inst.cplx_trans).transformed(pt)
   assert(physical-pya.Region(top.begin_shapes_rec(g.layer(*layer)))).is_empty(),'original primitive metal absent from top-level geometry'
 replacement=g.create_cell('rppd$select_width2_'+str(len(changes)));replacement.copy_tree(candidate)
 equal(regions(g,replacement),regions(variant,candidate));rename[replacement.name]=original_cell.name
 changes.append(dict(transform=key,old_cell=original_cell.name,new_cell=replacement.name))
 inst.cell_index=replacement.cell_index()
for idx,prior in original.items():
 cc=g.cell(idx)
 shapes={str(g.get_info(i)):sorted(str(y)for y in cc.each_shape(i))for i in g.layer_indexes()if not cc.shapes(i).is_empty()}
 instances=[(rename.get(y.cell.name,y.cell.name),str(y.cplx_trans),y.na,y.nb,str(y.a),str(y.b))for y in cc.each_inst()]
 assert shapes==prior['shapes']and instances==prior['instances'],'unrelated geometry or reference changed'
assert str(top.bbox())==oldbbox
before=regions(g,top)
options=pya.SaveLayoutOptions();options.select_cell(top.cell_index());options.write_context_info=False
gds=out/'candidate650-select-width2.gds';g.write(str(gds),options)
reread=pya.Layout();reread.read(str(gds));assert reread.dbu==g.dbu and [x.name for x in reread.top_cells()]==[top.name]
equal(before,regions(reread,reread.top_cell()))
(out/'primitive-replacement-proof.json').write_text(json.dumps(dict(changes=changes,all_original_shapes_retained=True,only_four_resistor_references_changed=True,original_M1_ownership_material_present=True,full_phy_accepted=False),indent=2))
from collections import Counter
leaves=[]
def census(cell):
 children=list(cell.each_inst())
 if not children:
  kind=cell.name.split('$')[0]
  if kind in ['npn13G2','rppd','ptap1','cmim','nmos']:leaves.append(kind)
 for child in children:
  assert not child.is_regular_array()
  census(child.cell)
census(reread.top_cell())
assert Counter(leaves)==dict(npn13G2=124,rppd=98,ptap1=221,cmim=7,nmos=200)
(out/'primitive-census.json').write_text(json.dumps(dict(physical_primitives=650,counts=dict(Counter(leaves)),hierarchy_preserved=True),indent=2))
assert all(not x.is_pcell_variant()and not x.is_library_cell()for x in reread.each_cell())
import re
reference=schematic
for name in ['RSE_D0','RSE_D1','RSE_D3','RSE_D4']:
 pattern=r'(?m)^('+name+r' .*? rppd )w=1u( .*)$'
 reference,count=re.subn(pattern,r'\1w=2u\2',reference);assert count==1
assert sum(x!=y for x,y in zip(schematic.splitlines(),reference.splitlines(),strict=True))==4
(out/'schematic650-select-width2.cir').write_text(reference)
(out/'geometry-proposal.json').write_text(json.dumps(dict(status='GENERATED_ACTUAL650_SELECT_WIDTH2_REQUIRES_FULL_LVS_DRC_FRESH_RC',parent_sha256=hashlib.sha256((parent/'native/selected/layout/nssoc_cdr_pd500_resistor_v59.gds').read_bytes()).hexdigest(),candidate_sha256=hashlib.sha256(gds.read_bytes()).hexdigest(),reference_sha256=hashlib.sha256(reference.encode()).hexdigest(),original_cells_preserved=True,only_four_resistor_references_replaced=True,normalized_marker_layers=['8/2','67/2','67/25'],serialization_regions_equal=True,full_phy_accepted=False,full_lvs_pass=False,full_drc_pass=False,fresh_rc=False),indent=2))
