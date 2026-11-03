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
for k,v in dict(OUT=OUT,NATIVE=NATIVE,DERIVED=DERIVED,CFG=CFG,PINS=PINS,BRANCH="codex/cdr-mos650-wires").items():setattr(identity,k,v)
need=identity.need;read=identity.read;enc=identity.enc;pin=identity.pin;save=identity.save;api=identity.api;gate=identity.gate
FLAGS=dict(wire_rc_extracted=False,gate_poly_RC_extracted=False,substrate_r_modeled=False,full_pex_qualified=False,electrical_accepted=False,full_phy_accepted=False,final_timing_complete=False)
ORIGIN="docs/evidence/cdr-v59-tail-exact-wire-methods-20261026/"
def source_controls():
 need(sys.flags.optimize==0,"assertions enabled")
 for n in ("probe01.py","locate01.py","anchors01.py","dedup01.py"):ast.parse((ROOT/ORIGIN/n).read_bytes())
 wanted=identity.expected();need(len(wanted)==650,"complete independent650 plan")
 return wanted
def fetch_old_pins(cfg):
 prod=cfg["old_source_pins"];r=api("actions/runs/"+str(prod["run"]));rel=api("releases/"+str(prod["release"]))
 need(r["head_sha"]==prod["source"]and r["conclusion"]=="success"and r["run_attempt"]==1,"old physical source qualification")
 need(rel["target_commitish"]==prod["source"]and rel["tag_name"]==prod["tag"]and api("git/ref/tags/"+prod["tag"])["object"]["sha"]==prod["source"],"old physical release identity")
 live={a["name"]:a for a in rel["assets"]};need(set(live)==set(prod["assets"]),"all old assets")
 dest=NATIVE/"old-source";dest.mkdir()
 for n,a in prod["assets"].items():
  need(live[n]["id"]==a["id"]and live[n]["size"]==a["bytes"]and live[n]["digest"]=="sha256:"+a["sha256"],"old source immutable assets")
  identity.fetch(a,dest/n)
 idx=read(dest/"complete-output-index.json");need(idx["context"]==dict(run=prod["run"],source=prod["source"],attempt=1),"old index context")
 need(idx["files"][prod["path"]]==prod["pin"],"exact independently qualified old source pin record")
 seen=set();result=None
 with tarfile.open(dest/"native-fresh-rc.tar.gz","r|gz")as tar:
  for m in tar:
   prefix="wire-shortcuts-fresh-rc/";need(m.isfile()and m.name.startswith(prefix),"regular old archive member")
   n=m.name[len(prefix):];need(n in idx["files"]and n not in seen and ".."not in PurePosixPath(n).parts,"unique safe member");seen.add(n)
   h=hashlib.sha256();size=0;parts=[];stream=tar.extractfile(m)
   for b in iter(lambda:stream.read(1024*1024),b""):
    size+=len(b);h.update(b)
    if n==prod["path"]:parts.append(b)
   need(dict(bytes=size,sha256=h.hexdigest())==idx["files"][n],"complete old archive authentication")
   if n==prod["path"]:result=json.loads(b"".join(parts))
 need(seen==set(idx["files"])and result is not None,"complete source extraction")
 save("old-source-acquisition.json",dict(producer=prod,members=len(seen),old_RC_reused=False,**FLAGS))
 return result
def source_pins(cfg,flat,old):
 import pya
 original=identity.original
 original.NATIVE=NATIVE/"pcell-runtime";original.NATIVE.mkdir()
 original.DERIVED=DERIVED
 pdk=original.pdk(dict(runtime_receipt=cfg["runtime_receipt"]))
 source=pdk/"libs.tech/klayout/python";sys.path[:0]=[str(source),str(source/"pycell4klayout-api/source/python")]
 import sg13g2_pycell_lib
 g=pya.Layout();g.read(str(NATIVE/"selected/layout"/(TOP+".gds")))
 need(g.dbu==.001,"physical DBU")
 def signature(layout,cell):
  drawing=[]
  for i in layout.layer_indexes():
   info=layout.get_info(i)
   if info.layer in METALS and info.datatype in(2,25):continue
   r=pya.Region(cell.begin_shapes_rec(i)).merged()
   if not r.is_empty():drawing.append((info.layer,info.datatype,sorted(p.to_s()for p in r.each())))
  need(drawing,"nonempty primitive drawing")
  return hashlib.sha256(json.dumps(sorted(drawing),separators=(",",":")).encode()).hexdigest()
 sources={}
 for row in old["cells"].values():
  kind=row["cell"].split("$")[0];key=(kind,row["drawing_sha256"])
  if key in sources:need(sources[key]["pins"]==row["pins"],"consistent old identical drawing pins")
  else:sources[key]=row
 lib=pya.Layout();specs=sorted({(r["layout"]["parameters"]["W"],r["layout"]["parameters"]["L"])for r in flat["pairs"]if r["layout"]["model"]=="sg13_lv_nmos"})
 regenerated=[]
 for w,l in specs:
  cell=lib.create_cell("nmos","SG13_dev",dict(w=format(w,".12g")+"u",l=format(l,".12g")+"u",ng=1))
  need(cell is not None,"native explicit unit PCell")
  pins=sorted([m,[s.box.left,s.box.bottom,s.box.right,s.box.top]]for m in METALS for s in cell.each_shape(lib.layer(m,2))if s.is_box())
  need(pins,"actual native MOS source/drain pin annotations")
  key=("nmos",signature(lib,cell))
  row=dict(source="pinned native IHP PCell",cell=cell.name,pins=pins,drawing_sha256=key[1],parameters=dict(w_um=w,l_um=l,ng=1))
  if key in sources:need(sources[key]["pins"]==pins,"regenerated original pin consistency")
  sources[key]=row;regenerated.append(row)
 reachable=set()
 def visit(c):
  if c.cell_index()in reachable:return
  reachable.add(c.cell_index())
  for inst in c.each_inst():need(not inst.is_regular_array(),"explicit actual hierarchy");visit(inst.cell)
 visit(g.cell(TOP));models={"npn13G2","rppd","ptap1","cmim","nmos"};mapped={};required={}
 for idx in reachable:
  c=g.cell(idx);kind=c.name.split("$")[0]
  if kind not in models or list(c.each_inst()):continue
  key=(kind,signature(g,c));required[c.name]=key
  if kind=="cmim":continue
  need(key in sources,"actual primitive drawing has independently bound source pins: "+c.name)
  mapped[c.name]=sources[key]
 need(mapped and {c.split("$")[0]for c in mapped}==models-{"cmim"},"all primitive classes")
 need(set(mapped)=={n for n,k in required.items()if k[0]!="cmim"},"every reachable physical primitive")
 result=dict(status="PASS_ACTUAL650_SOURCE_PINS_ON_IDENTICAL_PRIMITIVE_DRAWINGS",cells=mapped,
 target_gds_sha256=pin(NATIVE/"selected/layout"/(TOP+".gds"))["sha256"],target_geometry_edited=False,
 native_regenerated_MOS=regenerated,reachable_cell_count=len(reachable),old_source_pins=cfg["old_source_pins"]["pin"],**FLAGS)
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
 need(anchors["dispositions"]==dict(ACTUAL_TERMINAL_METAL_POINT_REFERENCE=1403,RETAINED_INTRINSIC_BODY_NO_SUBSTRATE_RESISTANCE=643),"complete dispositions")
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
  else:need(a["native_cluster"]==wanted[(detail["device"],detail["terminal"].upper())],"physical anchor native owner")
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
  need(access.count()==1 and holes.count()==1,"actual unique gate-poly path and contact")
  owner=d.net_for_terminal(td.id()).cluster_id
  gates.append(dict(device=d.id(),native_cluster=owner,terminal_polygons=[str(p)for p in terminal.each()],
   access_poly_polygons=[str(p)for p in access.each()],contact_polygons=[str(p)for p in holes.each()]))
 need(len(gates)==200,"all200 actual gate access paths")
 save("full-material-anchor-readback.json",dict(layers=material,physical_anchor_count=len(anchors["anchors"]),**FLAGS))
 save("gate-poly-access.json",dict(gates=gates,count=200,external_poly_resistance_required=True,**FLAGS))
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
  gate();save("result.json",dict(status="PASS_ACTUAL650_WIRE_TOPOLOGY_AND_TERMINAL_REFERENCES_REQUIRES_METAL_AND_GATE_POLY_RC",
   context=ctx,devices=650,terminals=2046,anchors=1428,components=graph["wire_component_count"],
   electrical_nets=graph["native_electrical_net_count"],physical_ports=25,gate_poly_paths=200,**FLAGS))
 except BaseException as e:
  save("failure.json",dict(error=repr(e),traceback=traceback.format_exc(),**FLAGS));raise
if __name__=="__main__":main()
