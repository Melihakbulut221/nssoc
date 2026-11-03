#!/usr/bin/env python3
"""Extract full physical650 wire topology and intrinsic terminal metal references."""
import ast,copy,hashlib,json,os,subprocess,sys,tarfile,traceback
from pathlib import Path,PurePosixPath
from collections import Counter
import cdr_mos650_identity as identity
ROOT=Path(__file__).resolve().parents[1]
OUT=ROOT/"mos650-wires";NATIVE=OUT/"native";DERIVED=OUT/"derived"
CFG="scripts/cdr-mos650-wires-inputs.json";PINS="scripts/cdr-mos650-wires-pins.json"
TOP=identity.TOP;METALS=(8,10,30,50,67,126,134)
for k,v in dict(OUT=OUT,NATIVE=NATIVE,DERIVED=DERIVED,CFG=CFG,PINS=PINS,BRANCH="codex/cdr-mos650-gate-wires").items():setattr(identity,k,v)
need=identity.need;read=identity.read;enc=identity.enc;pin=identity.pin;save=identity.save;api=identity.api;gate=identity.gate
FLAGS=dict(wire_rc_extracted=False,gate_poly_RC_extracted=False,substrate_r_modeled=False,full_pex_qualified=False,electrical_accepted=False,full_phy_accepted=False,final_timing_complete=False)
ORIGIN="docs/evidence/cdr-v59-tail-exact-wire-methods-20261026/"
def source_controls():
 need(sys.flags.optimize==0,"assertions enabled")
 for n in ("probe01.py","locate01.py","anchors01.py","dedup01.py"):ast.parse((ROOT/ORIGIN/n).read_bytes())
 ast.parse((ROOT/"scripts/cdr_mos650_gate_anchors.py").read_bytes())
 wanted=identity.expected();need(len(wanted)==650,"complete independent650 plan")
 return wanted
def fetch_old_pins(cfg):
 prod=cfg["old_source_pins"];r=api("actions/runs/"+str(prod["run"]));rel=api("releases/"+str(prod["release"]))
 need(r["head_sha"]==prod["source"]and r["status"]=="completed"and r["conclusion"]=="success"and r["run_attempt"]==1,"old physical source qualification")
 need(rel["target_commitish"]==prod["source"]and rel["tag_name"]==prod["tag"]and api("git/ref/tags/"+prod["tag"])["object"]["sha"]==prod["source"],"old physical release identity")
 live={a["name"]:a for a in rel["assets"]};need(set(live)==set(prod["assets"]),"all old assets")
 dest=NATIVE/"old-source";dest.mkdir()
 for n,a in prod["assets"].items():
  need(live[n]["id"]==a["id"]and live[n]["size"]==a["bytes"]and live[n]["digest"]=="sha256:"+a["sha256"],"old source immutable assets")
  identity.fetch(a,dest/n)
 idx=read(dest/"complete-output-index.json");need(idx["context"]==dict(run=prod["run"],source=prod["source"],attempt=1),"old index context")
 need(idx["files"][prod["path"]]==prod["pin"],"exact independently qualified old source pin record")
 seen=set();result=None
 with tarfile.open(dest/prod["archive"],"r|gz")as tar:
  for m in tar:
   prefix=prod["archive_root"]+"/";need(m.isfile()and m.name.startswith(prefix),"regular old archive member")
   n=m.name[len(prefix):];need(n in idx["files"]and n not in seen and ".."not in PurePosixPath(n).parts,"unique safe member");seen.add(n)
   h=hashlib.sha256();size=0;parts=[];stream=tar.extractfile(m)
   for b in iter(lambda:stream.read(1024*1024),b""):
    size+=len(b);h.update(b)
    if n in(prod["path"],prod["gds_path"]):parts.append(b)
   need(dict(bytes=size,sha256=h.hexdigest())==idx["files"][n],"complete old archive authentication")
   if n==prod["path"]:result=json.loads(b"".join(parts))
   if n==prod["gds_path"]:
    (dest/"layout.gds").write_bytes(b"".join(parts))
    need(pin(dest/"layout.gds")==prod["gds_pin"],"complete qualified prior650 GDS")
 need(seen==set(idx["files"])and result is not None and pin(dest/"layout.gds")==prod["gds_pin"],"complete source extraction")
 save("old-source-acquisition.json",dict(producer=prod,members=len(seen),old_RC_reused=False,**FLAGS))
 return result
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
 need(hierarchy(g)==hierarchy(prior),"complete original physical hierarchy identity")
 need(annotations(g)==annotations(prior),"every original pin annotation and label retained")
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
    source="Qualified prior full drawing plus exact current intrinsic geometry and pin annotation identity; current conductor probes required")
  mapped[c.name]=row
 need(mapped and {c.split("$")[0]for c in mapped}==models-{"cmim"},"complete primitive source-pin coverage")
 result=dict(status="PASS_CURRENT650_PINS_REBOUND_AFTER_DECLARED_CONDUCTOR_FLATTENING",
  cells=mapped,primitive_checks=checks,all_original_pin_annotations_equal=True,all_original_hierarchy_equal=True,
  original_gds=cfg["old_source_pins"]["gds_pin"],target_gds_sha256=pin(NATIVE/"selected/layout"/(TOP+".gds"))["sha256"],
  target_geometry_edited=False,old_source_pins=cfg["old_source_pins"]["pin"],current_native_anchor_probes_required=True,**FLAGS)
 save("source-pins.json",result);return result

def prepare_workers():
 base=NATIVE/"view";parent=base/"parent";wire=base/"wire";wire.mkdir(parents=True)
 for n in ("layout/"+TOP+".gds","layout/result.json","physical/lvs_flat/result.lvsdb"):
  p=parent/n;p.parent.mkdir(parents=True,exist_ok=True);p.write_bytes((NATIVE/"selected"/n).read_bytes())
 q=read(NATIVE/"selected/physical/result.json")
 (parent/"physical/lvs_flat/audit.json").write_bytes(enc(q["steps"]["lvs_flat"]["audit"]))
 replacements={
  "probe01.py":[("sg13_lv_nmos=50","sg13_lv_nmos=200")],
  "locate01.py":[("==500","==650"),("ALL_500_DEVICES","ALL_650_DEVICES")],
  "anchors01.py":[("len(rows)==1446 and len(anchors)==978","len(rows)==2046 and len(anchors)==1428"),
                  ("PASS_1446_NATIVE_TERMINALS_WITH_953_METAL_AND_493_BODY_REFERENCES","PASS_2046_NATIVE_TERMINALS_WITH_1403_METAL_AND_643_BODY_REFERENCES")],
  "dedup01.py":[]}
 derivation={}
 for n,changes in replacements.items():
  old=(ROOT/ORIGIN/n).read_text();s=old;records=[]
  if n=="anchors01.py":
   s=(ROOT/"scripts/cdr_mos650_gate_anchors.py").read_text()
   changes=[]
   records.append(dict(source="scripts/cdr_mos650_gate_anchors.py",pin=pin(ROOT/"scripts/cdr_mos650_gate_anchors.py"),reason="explicit intrinsic gates and all physical gate contacts"))
  for before,after in changes:
   count=s.count(before);need(count>0,"explicit original worker substitution")
   s=s.replace(before,after);records.append(dict(before=before,after=after,count=count))
  ast.parse(s);(wire/n).write_text(s)
  derivation[n]=dict(original=pin(ROOT/ORIGIN/n),derived=pin(wire/n),changes=records)
 (wire/"source-pins.json").write_bytes((DERIVED/"source-pins.json").read_bytes())
 save("worker-derivation.json",dict(workers=derivation,actual650_reference_required=True,**FLAGS))
 return wire
def run_worker(wire,name):
 label=name.removesuffix(".py");so=NATIVE/(label+".stdout");se=NATIVE/(label+".stderr")
 with so.open("wb")as stdout,se.open("wb")as stderr:
  p=subprocess.run([sys.executable,"-B",str(wire/name)],stdout=stdout,stderr=stderr,timeout=900)
 (DERIVED/(label+".stdout")).write_bytes(so.read_bytes());(DERIVED/(label+".stderr")).write_bytes(se.read_bytes())
 save(label+"-command.json",dict(returncode=p.returncode,stdout=pin(so),stderr=pin(se),**FLAGS))
 need(p.returncode==0,"native "+name+" failed; full streams preserved")
def validate_binding(graph,locations,anchors,flat):
 expected={r["layout"]["id"]:r for r in flat["pairs"]}
 need(graph["native_device_count"]==650 and graph["native_terminal_count"]==2046,"fresh graph complete actual devices and terminals")
 need(graph["native_devices"]==dict(npn13G2=124,sg13_lv_nmos=200,rppd=98,cap_cmim=7,ptap1=221),"actual650 graph census")
 need(graph["no_component_union_by_native_label"]is True and graph["no_wire_geometry_change"]is True,"pure physical graph")
 need(len(locations["devices"])==650 and len({r["pcell"]["path"]for r in locations["devices"]})==650,"all unique physical instances")
 observed={}
 for n in graph["native_net_coverage"]:
  for t in n["device_terminals"]:
   key=(t["device"],t["terminal"].upper());need(key not in observed,"unique graph terminal");observed[key]=n["native_cluster"]
 wanted={(r["layout"]["id"],t):v["cluster"]for r in flat["pairs"]for t,v in r["layout"]["terminals"].items()}
 need(observed==wanted and len(wanted)==2046,"every graph terminal independently matches real650 LVS")
 for r in locations["devices"]:
  d=expected[r["native_id"]]["layout"]
  need(r["model"].lower()==d["model"]and r["parameters"]==d["parameters"],"every located physical primitive matches native650 identity")
 need(len(anchors["rows"])==2046 and len(anchors["anchors"])==1428,"all actual anchors and intrinsic body references")
 need(anchors["dispositions"]==dict(ACTUAL_TERMINAL_METAL_POINT_REFERENCE=1203,RETAINED_INTRINSIC_BODY_NO_SUBSTRATE_RESISTANCE=643,RETAINED_INTRINSIC_GATE_REQUIRES_POLY_RC=200),"complete dispositions")
 seen={}
 for r in anchors["rows"]:
  key=(r["device"],r["terminal"].upper());need(key not in seen and key in wanted,"unique actual anchor terminal")
  need(r["native_cluster"]==wanted[key],"actual anchor terminal ownership");seen[key]=r
 need(set(seen)==set(wanted),"no lost terminal")
 need(len([a for a in anchors["anchors"]if "public_port"in a["detail"]])==25,"all public anchors")
 for a in anchors["anchors"]:
  detail=a["detail"]
  if "public_port"in detail:
   p=next(p for p in flat["ports"]if p["name"]==detail["public_port"]);need(a["native_cluster"]==p["cluster"],"public anchor actual owner")
  elif "gate_contact"in detail:
   need(detail["devices"]and all(a["native_cluster"]==wanted[(d,"G")]for d in detail["devices"]),"every contact actual intrinsic gate owner")
  else:need(a["native_cluster"]==wanted[(detail["device"],detail["terminal"].upper())],"physical anchor native owner")

 gate_rows=[r for r in anchors["rows"]if r["model"]=="sg13_lv_nmos"and r["terminal"]=="G"]
 need(len(gate_rows)==200 and all(r["disposition"]=="RETAINED_INTRINSIC_GATE_REQUIRES_POLY_RC"and "point_dbu"not in r and "metal"not in r for r in gate_rows),"no intrinsic gate ideally collapsed onto metal")
 groups=anchors["gate_groups"];need(len(groups)==50 and len({r["group"]for r in groups})==50,"all50 actual gate-poly groups")
 members={};labels=set()
 for group in groups:
  need(group["devices"]and len(group["devices"])==len(group["contact_anchors"]),"one physical contact per unit count in actual current layout")
  for dev in group["devices"]:
   need(dev not in members and wanted[(dev,"G")]==group["native_cluster"],"unique intrinsic gate with actual native group owner")
   members[dev]=group["group"]
  for label in group["contact_anchors"]:
   need(label not in labels,"unique contact label");labels.add(label)
   a=next(a for a in anchors["anchors"]if a["label"]==label)
   need(a["detail"]["gate_group"]==group["group"]and a["detail"]["devices"]==group["devices"]and a["native_cluster"]==group["native_cluster"],"complete physical contact group ownership")
 need(len(members)==len(labels)==200 and {r["device"]:r["gate_group"]for r in gate_rows}==members,"complete200 intrinsic electrodes and200 real contacts")
 contacts=[a for a in anchors["anchors"]if "gate_contact"in a["detail"]]
 need({a["label"]for a in contacts}==labels and len({(a["metal"],*a["point_dbu"])for a in contacts})==200,"all distinct actual gate-contact metal points")

def native_material_and_anchors(wire,flat):
 import pya
 g=pya.Layout();g.read(str(NATIVE/"selected/layout"/(TOP+".gds")));top=g.cell(TOP)
 saved=pya.Layout();saved.read(str(wire/"native05/wires.gds"));st=saved.cell("pump_wires")
 layers=(*METALS,19,29,49,66,125,133);material={}
 for layer in layers:
  actual=pya.Region(top.begin_shapes_rec(g.layer(layer,0))).merged()
  copied=pya.Region(st.begin_shapes_rec(saved.layer(layer,0))).merged()
  need((actual^copied).is_empty(),"complete unchanged serialized conductor layer")
  material[str(layer)]=dict(area_dbu2=actual.area(),polygons=actual.count())
 l=pya.LayoutVsSchematic();l.read(str(NATIVE/"selected/physical/lvs_flat/result.lvsdb"))
 w=pya.LayoutToNetlist();w.read(str(wire/"native05/wires.l2n"))
 graph=read(wire/"native05/result.json");mapping={int(k):v for k,v in graph["native_layer_mapping"].items()}
 anchors=read(wire/"anchors03.json")
 for a in anchors["anchors"]:
  point=pya.Point(*a["point_dbu"]);metal=a["metal"]
  native=l.probe_net(l.layer_by_index(mapping[metal]),point);wire_net=w.probe_net(w.layer_by_name("gds_"+str(metal)),point)
  need(native is not None and wire_net is not None and native.cluster_id==a["native_cluster"]and wire_net.cluster_id==a["wire_component"],"every serialized physical anchor actual connectivity")
 # Preserve actual access poly separately. An ideal shared metal anchor does NOT
 # account for inter-unit gate-poly resistance. Fresh RC must model these paths.
 poly=pya.Region(top.begin_shapes_rec(g.layer(5,0))).merged();contacts=pya.Region(top.begin_shapes_rec(g.layer(6,0))).merged()
 circuit=l.netlist().top_circuit();gates=[]
 for d in circuit.each_device():
  if d.device_class().name!="sg13_lv_nmos":continue
  td=next(td for td in d.device_class().terminal_definitions()if td.name=="G")
  terminal=pya.Region()
  for r in l.shapes_of_terminal(d.terminal_ref(td.id())).values():terminal+=r
  access=poly.interacting(terminal);holes=contacts.inside(access)
  need(access.count()==1 and holes.count()>=1,"actual unique gate-poly path and complete contact set")
  owner=d.net_for_terminal(td.id()).cluster_id
  gid=hashlib.sha256(json.dumps(sorted(p.to_s()for p in access.each())).encode()).hexdigest()
  group=next(r for r in anchors["gate_groups"]if r["group"]==gid)
  need(d.id()in group["devices"]and owner==group["native_cluster"],"actual intrinsic electrode belongs to reported group")
  observed={str(p)for p in holes.each()}
  declared={a["detail"]["contact_polygon"]for a in anchors["anchors"]if a["label"]in group["contact_anchors"]}
  need(observed==declared and len(observed)==len(group["contact_anchors"]),"every real gate contact represented exactly once")
  gates.append(dict(device=d.id(),native_cluster=owner,gate_group=gid,terminal_polygons=[str(p)for p in terminal.each()],
   access_poly_polygons=[str(p)for p in access.each()],contact_polygons=[str(p)for p in holes.each()]))
 need(len(gates)==200,"all200 actual gate access paths")
 save("full-material-anchor-readback.json",dict(layers=material,physical_anchor_count=len(anchors["anchors"]),**FLAGS))
 save("gate-poly-access.json",dict(gates=gates,count=200,groups=anchors["gate_groups"],physical_contact_count=200,intrinsic_gate_metal_shortcuts=False,external_poly_resistance_required=True,**FLAGS))
def fault_controls(graph,locations,anchors,flat):
 # Remove an actual terminal-bearing partition, not an optional empty partition.
 bad=copy.deepcopy(graph);n=next(n for n in bad["native_net_coverage"]if n["device_terminals"]);n["device_terminals"].pop()
 cases=[("lost graph terminal",bad,locations,anchors)]
 wrong=copy.deepcopy(locations);wrong["devices"][0]["parameters"][next(iter(wrong["devices"][0]["parameters"]))]+=1
 cases.append(("changed physical primitive parameter",graph,wrong,anchors))
 wrong=copy.deepcopy(locations);wrong["devices"][-1]["pcell"]["path"]=wrong["devices"][0]["pcell"]["path"]
 cases.append(("duplicate physical instance",graph,wrong,anchors))
 wrong=copy.deepcopy(anchors);wrong["rows"][0]["native_cluster"]=-1
 cases.append(("wrong native terminal owner",graph,locations,wrong))
 wrong=copy.deepcopy(anchors);wrong["anchors"].pop()
 cases.append(("missing physical anchor",graph,locations,wrong))
 wrong=copy.deepcopy(anchors);wrong["gate_groups"].pop()
 cases.append(("missing physical gate-poly group",graph,locations,wrong))
 wrong=copy.deepcopy(anchors);wrong["gate_groups"][0]["contact_anchors"].pop()
 cases.append(("missing physical gate contact",graph,locations,wrong))
 wrong=copy.deepcopy(anchors)
 ga=[a for a in wrong["anchors"]if "gate_contact"in a["detail"]];ga[-1]["point_dbu"]=ga[0]["point_dbu"]
 cases.append(("duplicate physical gate-contact point",graph,locations,wrong))
 wrong=copy.deepcopy(anchors);next(r for r in wrong["rows"]if r["disposition"]=="RETAINED_INTRINSIC_GATE_REQUIRES_POLY_RC")["point_dbu"]=[0,0]
 cases.append(("intrinsic gate ideally collapsed onto metal",graph,locations,wrong))
 wrong=copy.deepcopy(anchors);wrong["gate_groups"][0]["devices"][0]=-1
 cases.append(("wrong intrinsic gate-group association",graph,locations,wrong))
 refused=[]
 for name,gr,lo,an in cases:
  try:validate_binding(gr,lo,an,flat)
  except (ValueError,KeyError,StopIteration):refused.append(name)
  else:raise ValueError("accepted corrupt actual graph "+name)
 save("actual-binding-controls.json",dict(refused=refused,count=len(refused),**FLAGS))
def publish():
 ctx=gate();tag="cloud-results-"+str(ctx["run"])+"-1-cdr-mos650-wires";rel=api("releases/tags/"+tag)
 need(rel["target_commitish"]==ctx["source"]and not rel["assets"]and api("git/ref/tags/"+tag)["object"]["sha"]==ctx["source"],"independent empty release")
 dest=OUT/"publication";dest.mkdir()
 rows={str(p.relative_to(OUT)):pin(p)for p in sorted(OUT.rglob("*"))if p.is_file()and dest not in p.parents}
 idx=dest/"complete-output-index.json";idx.write_bytes(enc(dict(context=ctx,files=rows,**FLAGS)))
 archive=dest/"native-wires.tar.gz"
 with tarfile.open(archive,"w:gz",compresslevel=1)as tar:
  for n in rows:tar.add(OUT/n,arcname="mos650-wires/"+n,recursive=False)
 for p in (idx,archive):subprocess.run(["gh","release","upload",tag,str(p),"--repo",identity.REPO],check=True,timeout=600)
 assets=api("releases/"+str(rel["id"]))["assets"]
 for p in (idx,archive):
  a=next(a for a in assets if a["name"]==p.name);need(a["size"]==p.stat().st_size and a["digest"]=="sha256:"+pin(p)["sha256"],"complete uploaded evidence")
 save("publication.json",dict(release=rel["id"],assets=assets,**FLAGS))
def main():
 ctx=gate()
 if sys.argv[1:]==["--publish"]:publish();return
 OUT.mkdir();NATIVE.mkdir();DERIVED.mkdir()
 try:
  wanted=source_controls();save("source-controls.json",dict(context=ctx,independent_devices=len(wanted),**FLAGS))
  if sys.argv[1:]==["--controls"]:return
  need(sys.argv[1:]==["--extract"],"explicit extraction")
  cfg=read(ROOT/CFG);identity.acquire(cfg["physical"])
  deep=identity.native_side("lvs",wanted);flat=identity.native_side("lvs_flat",wanted)
  old=fetch_old_pins(cfg);source_pins(cfg,flat,old);wire=prepare_workers()
  for name in ("probe01.py","locate01.py","anchors01.py","dedup01.py"):run_worker(wire,name)
  graph=read(wire/"native05/result.json");locations=read(wire/"device-locations01.json");anchors=read(wire/"anchors03.json")
  validate_binding(graph,locations,anchors,flat);native_material_and_anchors(wire,flat);fault_controls(graph,locations,anchors,flat)
  for name,path in [("wire-graph.json",wire/"native05/result.json"),("device-locations.json",wire/"device-locations01.json"),("terminal-anchors.json",wire/"anchors03.json"),("unique-anchors.json",wire/"anchors08.json")]:save(name,read(path))
  gate();save("result.json",dict(status="PASS_CURRENT650_WIRES_200_GATE_CONTACTS_AND_SEPARATE_INTRINSIC_ELECTRODES_REQUIRES_RC",
   context=ctx,devices=650,terminals=2046,anchors=1428,components=graph["wire_component_count"],
   electrical_nets=graph["native_electrical_net_count"],physical_ports=25,gate_poly_paths=200,physical_gate_contacts=200,intrinsic_gate_metal_shortcuts=False,physical_run=cfg["physical"]["run"],**FLAGS))
 except BaseException as e:
  save("failure.json",dict(error=repr(e),traceback=traceback.format_exc(),**FLAGS));raise
if __name__=="__main__":main()
