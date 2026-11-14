import copy,hashlib,json
from pathlib import Path
import klayout.db as db
from cdr_mos650_wires import ROOT,NATIVE,DERIVED,TOP,METALS,need,save,pin

def prove_band_relocation(g,prior,hierarchy,annotations,signature):
 baseline=db.Layout();baseline.read(str(NATIVE/'baseline.gds'))
 need(pin(NATIVE/'baseline.gds')['sha256']=='c335182048dc1696821ab875fb34447e5b5a9ba0f1a24d5d16d572680906c16c','exact pre-relocation650 baseline')
 need(hierarchy(baseline)==hierarchy(prior),'original baseline hierarchy matches qualified source pins')
 need(annotations(baseline)==annotations(prior),'original baseline annotations match qualified source pins')
 proof=json.loads((NATIVE/'paired-layout-proof.json').read_text())
 need(pin(NATIVE/'selected/layout'/(TOP+'.gds'))['sha256']==proof['candidate_gds_sha256']=='285760f3930a1cc142b45a3c43866202f1ea4694f468fb1603f286cb546cd514','exact new physical candidate')
 before=list(baseline.cell(TOP).each_inst());after=list(g.cell(TOP).each_inst())
 need(len(before)==40 and len(after)==16,'explicit top via flattening and16 retained macros')
 macros={n:i for n,i in enumerate(before) if i.cell.name.startswith('pd_child_')}
 need(set(macros)==set(range(16)),'complete source macro inventory')
 order=sorted(macros,key=lambda n:macros[n].bbox().bottom)
 need(order==proof['old_order'],'actual original band order')
 def check(translations,instances):
  wanted=[]
  for band,n in enumerate(order):
   inst=macros[n];tr=db.Trans(inst.trans);tr.disp=db.Vector(tr.disp.x,tr.disp.y+translations[str(band)])
   wanted.append((inst.cell.name,str(tr)))
  observed=[(inst.cell.name,str(inst.trans)) for inst in instances]
  need(len(observed)==16 and len(set(observed))==16 and sorted(observed)==sorted(wanted),'actual macro transforms match declared bands')
 check(proof['band_translations_y_dbu'],after)
 controls=[]
 bad=dict(proof['band_translations_y_dbu']);bad['6']+=5
 for name,d,instances in [('wrong actual macro translation',bad,after),('missing physical macro',proof['band_translations_y_dbu'],after[:-1])]:
  try:check(d,instances)
  except ValueError:controls.append(name)
  else:raise ValueError('accepted corrupt relocation '+name)
 # All reachable child definitions preserve complete local material and
 # local annotations; only parent transforms/routing/public pins changed.
 seen=set();checked=[]
 def walk(cell):
  if cell.name in seen:return
  seen.add(cell.name)
  old=baseline.cell(cell.name);need(old is not None,'original reachable child')
  need(signature(g,cell)==signature(baseline,old),'complete child local drawing unchanged')
  def notes(layout,c):
   rows=[]
   for li in layout.layer_indexes():
    info=layout.get_info(li)
    for shape in c.each_shape(li):
     if shape.is_text():rows.append((str(info),str(shape.text)))
    if info.datatype in (2,25):
     region=db.Region(c.begin_shapes_rec(li)).merged()
     if not region.is_empty():rows.append((str(info),sorted(x.to_s()for x in region.each())))
   return sorted(rows,key=lambda x:json.dumps(x,sort_keys=True))
  need(notes(g,cell)==notes(baseline,old),'complete local child pin annotation identity')
  checked.append(cell.name)
  for inst in cell.each_inst():walk(inst.cell)
 for inst in after:walk(inst.cell)
 need(checked,'nonempty complete retained child hierarchy')
 save('paired-pin-relocation.json',dict(original_top_instances=40,new_top_instances=16,checked_children=checked,controls=controls,original_top_hierarchy_unchanged=False,declared_macro_transforms_verified=True,complete_child_material_and_annotations_unchanged=True,full_phy_accepted=False))

def source_pins(cfg,flat,old):
 import pya
 g=pya.Layout();g.read(str(NATIVE/"selected/layout"/(TOP+".gds")))
 prior=pya.Layout();prior.read(str(NATIVE/"old-source/layout.gds"))
 need(g.dbu==prior.dbu==.001,"exact current and qualified prior geometry grid")
 def signature(layout,cell,exclude=()):
  drawing=[]
  for i in layout.layer_indexes():
   info=layout.get_info(i)
   if (info.layer,info.datatype)in exclude:continue
   if info.layer in METALS and info.datatype in(2,25):continue
   region=pya.Region(cell.begin_shapes_rec(i)).merged()
   if not region.is_empty():drawing.append((info.layer,info.datatype,sorted(p.to_s()for p in region.each())))
  need(drawing,"nonempty primitive drawing")
  return hashlib.sha256(json.dumps(sorted(drawing),separators=(",",":")).encode()).hexdigest()
 def hierarchy(layout):
  return {c.name:sorted((i.cell.name,str(i.cplx_trans),i.na,i.nb,str(i.a),str(i.b))for i in c.each_inst())for c in layout.each_cell()}
 def annotations(layout):
  rows=[]
  for c in layout.each_cell():
   for li in layout.layer_indices():
    info=layout.get_info(li)
    for s in c.each_shape(li):
     if s.is_text():rows.append((c.name,info.layer,info.datatype,str(s.text)))
    if info.datatype in(2,25):
     r=pya.Region(c.begin_shapes_rec(li)).merged()
     if not r.is_empty():rows.append((c.name,info.layer,info.datatype,sorted(p.to_s()for p in r.each())))
  return sorted(rows,key=lambda r:json.dumps(r,sort_keys=True))
 prove_band_relocation(g,prior,hierarchy,annotations,signature)
 need(old["status"]=="PASS_ACTUAL650_SOURCE_PINS_ON_IDENTICAL_PRIMITIVE_DRAWINGS","qualified original650 primitive pin provenance")
 reachable=set()
 def visit(c):
  if c.cell_index()in reachable:return
  reachable.add(c.cell_index())
  for inst in c.each_inst():
   need(not inst.is_regular_array(),"explicit hierarchy");visit(inst.cell)
 visit(g.cell(TOP))
 models={"npn13G2","rppd","ptap1","cmim","nmos"};mapped={};checks=[]
 for idx in reachable:
  c=g.cell(idx);kind=c.name.split("$")[0]
  if kind not in models or list(c.each_inst()):continue
  oldcell=prior.cell(c.name);need(oldcell is not None,"same independently qualified primitive cell")
  before=signature(prior,oldcell);after=signature(g,c)
  intrinsic=signature(g,c,((8,0),(10,0),(19,0)))
  need(intrinsic==signature(prior,oldcell,((8,0),(10,0),(19,0))),"exact intrinsic material unchanged, not just parameters")
  checks.append(dict(cell=c.name,original_drawing_sha256=before,current_drawing_sha256=after,unchanged_nonrelocated_material_sha256=intrinsic))
  if kind=="cmim":continue
  need(c.name in old["cells"],"every actual prior primitive had independently qualified pins")
  row=copy.deepcopy(old["cells"][c.name])
  need(row["drawing_sha256"]==before,"old pin record bound to full original primitive drawing")
  row.update(cell=c.name,drawing_sha256=after,original_drawing_sha256=before,
    source="Qualified prior primitive drawing and intrinsic geometry; explicit whole-band translation and primitive annotation checks; current native conductor probes required")
  mapped[c.name]=row
 need(mapped and {c.split("$")[0]for c in mapped}==models-{"cmim"},"complete primitive source-pin coverage")
 result=dict(status="PASS_PAIRED650_PRIMITIVE_PINS_REBOUND_AFTER_VERIFIED_BAND_TRANSLATION",
  cells=mapped,primitive_checks=checks,all_primitive_pin_annotations_equal=True,all_original_hierarchy_equal=False,declared_band_relocation_verified=True,
  original_gds=cfg["old_source_pins"]["gds_pin"],target_gds_sha256=pin(NATIVE/"selected/layout"/(TOP+".gds"))["sha256"],
  target_geometry_edited=False,old_source_pins=cfg["old_source_pins"]["pin"],current_native_anchor_probes_required=True,**FLAGS)
 save("source-pins.json",result);return result
