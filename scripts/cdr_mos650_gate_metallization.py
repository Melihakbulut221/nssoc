#!/usr/bin/env python3
"""Add local contacts and minimum-width M1 gate straps to qualified650 geometry."""
import hashlib,json,os,re,subprocess,sys,tarfile,traceback,shutil
from pathlib import Path,PurePosixPath
ROOT=Path(__file__).resolve().parents[1]
OUT=ROOT/"mos650-gate-metallization";NATIVE=OUT/"native";DERIVED=OUT/"derived"
CFG="scripts/cdr-mos650-gate-metallization-inputs.json";PINS="scripts/cdr-mos650-gate-metallization-pins.json"
REPO="Melihakbulut221/nssoc";BRANCH="codex/cdr-mos650-gate-metallization"
FLAGS=dict(gate_poly_RC_extracted=False,mim_intrinsic_composition_qualified=False,substrate_r_modeled=False,
 full_pex_qualified=False,electrical_accepted=False,full_phy_accepted=False,final_timing_complete=False)
def need(ok,msg):
 if not ok:raise ValueError(msg)
def read(p):return json.loads(Path(p).read_bytes())
def enc(d):return(json.dumps(d,sort_keys=True,indent=2,allow_nan=False)+"\n").encode()
def pin(p):
 p=Path(p)
 with p.open("rb")as f:return dict(bytes=p.stat().st_size,sha256=hashlib.file_digest(f,"sha256").hexdigest())
def save(n,d):
 p=DERIVED/n;p.parent.mkdir(parents=True,exist_ok=True)
 with p.open("xb")as f:f.write(enc(d))
def api(path):return json.loads(subprocess.check_output(["gh","api","repos/"+REPO+"/"+path],timeout=180))
def gate():
 e=os.environ
 need(e.get("GITHUB_ACTIONS")=="true"and e.get("RUNNER_ENVIRONMENT")=="github-hosted","hosted only")
 need(e["GITHUB_REPOSITORY"]==REPO and e["GITHUB_REF"]=="refs/heads/"+BRANCH,"owned branch")
 need(e["GITHUB_EVENT_NAME"]=="workflow_dispatch"and e["GITHUB_RUN_ATTEMPT"]=="1","first explicit dispatch")
 need(sys.flags.optimize==0 and e["GITHUB_SHA"]==e["APPROVED_SOURCE"]==subprocess.check_output(["git","rev-parse","HEAD"],text=True).strip(),"exact source and enabled assertions")
 for n,p in read(ROOT/PINS)["files"].items():need(pin(ROOT/n)==p,"source "+n)
 return dict(run=int(e["GITHUB_RUN_ID"]),source=e["GITHUB_SHA"],attempt=1)
def fetch(a,path):
 with path.open("xb")as f:subprocess.run(["gh","api","repos/"+REPO+"/releases/assets/"+str(a["id"]),"-H","Accept: application/octet-stream"],stdout=f,check=True,timeout=600)
 need(pin(path)=={k:a[k]for k in("bytes","sha256")},"whole asset content")
def acquire(prod,dest,selector):
 r=api("actions/runs/"+str(prod["run"]));rel=api("releases/"+str(prod["release"]))
 need(r["head_sha"]==prod["source"]and r["status"]=="completed"and r["conclusion"]=="success"and r["run_attempt"]==1,"actual qualified producer")
 need(rel["target_commitish"]==prod["source"]and rel["tag_name"]==prod["tag"]and api("git/ref/tags/"+prod["tag"])["object"]["sha"]==prod["source"],"qualified release/tag identity")
 actual={a["name"]:a for a in rel["assets"]};need(set(actual)==set(prod["assets"]),"complete producer assets")
 cache=NATIVE/("producer-"+str(prod["run"]));cache.mkdir()
 for n,a in prod["assets"].items():
  need(actual[n]["id"]==a["id"]and actual[n]["size"]==a["bytes"]and actual[n]["digest"]=="sha256:"+a["sha256"],"immutable asset metadata")
  fetch(a,cache/n)
 index=read(cache/"complete-output-index.json")
 need(index["context"]==dict(run=prod["run"],source=prod["source"],attempt=1),"complete index context")
 selected={n:p for n,p in index["files"].items()if selector(n)}
 need(selected==prod["selected"],"complete independently bound selection")
 seen=set()
 with tarfile.open(cache/prod["archive"],"r|gz")as tar:
  for m in tar:
   prefix=prod["archive_root"]+"/";need(m.isfile()and m.name.startswith(prefix),"regular archive member")
   n=m.name[len(prefix):];path=PurePosixPath(n)
   need(n in index["files"]and n not in seen and not path.is_absolute()and ".."not in path.parts,"unique indexed member");seen.add(n)
   stream=tar.extractfile(m);h=hashlib.sha256();size=0;output=None
   if n in selected:
    p=dest/n;p.parent.mkdir(parents=True,exist_ok=True);output=p.open("xb")
   try:
    for b in iter(lambda:stream.read(1024*1024),b""):
     size+=len(b);h.update(b)
     if output:output.write(b)
   finally:
    if output:output.close();os.chmod(dest/n,m.mode&0o777)
   need(dict(bytes=size,sha256=h.hexdigest())==index["files"][n],"every indexed archive member authenticated")
 need(seen==set(index["files"]),"whole producer archive coverage")
 save("acquisition-"+str(prod["run"])+".json",dict(producer=prod,members=len(seen),selected=selected,**FLAGS))
 return selected
def publish():
 ctx=gate();tag="cloud-results-"+str(ctx["run"])+"-1-cdr-mos650-gate-metallization";rel=api("releases/tags/"+tag)
 need(rel["target_commitish"]==ctx["source"]and not rel["assets"]and api("git/ref/tags/"+tag)["object"]["sha"]==ctx["source"],"independent empty release")
 dest=OUT/"publication";dest.mkdir()
 paths=[p for p in OUT.rglob("*")if p.is_file()and dest not in p.parents]
 # The authenticated current view is preserved in its immutable producer release.
 rows={str(p.relative_to(OUT)):pin(p)for p in sorted(paths)}
 index=dest/"complete-output-index.json";index.write_bytes(enc(dict(context=ctx,files=rows,**FLAGS)))
 archive=dest/"native-gate-metallization.tar.gz"
 with tarfile.open(archive,"w:gz",compresslevel=1)as tar:
  for n in rows:tar.add(OUT/n,arcname="mos650-gate-metallization/"+n,recursive=False)
 for p in(index,archive):subprocess.run(["gh","release","upload",tag,str(p),"--repo",REPO],check=True,timeout=1200)
 assets=api("releases/"+str(rel["id"]))["assets"]
 for p in(index,archive):
  a=next(a for a in assets if a["name"]==p.name);need(a["size"]==p.stat().st_size and a["digest"]=="sha256:"+pin(p)["sha256"],"exact published output")
 save("publication.json",dict(release=rel["id"],assets=assets,**FLAGS))


def reserve():
 # GitHub's workflow token cannot create a new tag on this workflow-changing
 # source. The authorized dispatcher reserves it; this job only verifies it.
 import time
 ctx=gate();tag="cloud-results-"+str(ctx["run"])+"-1-cdr-mos650-gate-metallization"
 for attempt in range(31):
  query=subprocess.run(["gh","api","repos/"+REPO+"/releases/tags/"+tag],capture_output=True,text=True,timeout=60)
  if query.returncode==0:
   rel=json.loads(query.stdout)
   need(rel["target_commitish"]==ctx["source"]and not rel["assets"]and api("git/ref/tags/"+tag)["object"]["sha"]==ctx["source"],"exact empty release before native work")
   print(json.dumps(dict(release=rel["id"],tag=tag,context=ctx,external_reservation_verified=True)),flush=True)
   return
  need("HTTP 404"in query.stderr,"definitive release lookup")
  if attempt<30:time.sleep(4)
 raise ValueError("No exact-source release reservation arrived; native geometry not started")

def polygon(text,pya):
 raw=text.split(" props=")[0]
 need(raw.startswith("(")and raw.endswith(")"),"exact native polygon encoding")
 points=[pya.Point(*map(int,p.split(",")))for p in raw[1:-1].split(";")]
 return pya.Polygon(points)
def layer_regions(g,top,pya):
 return {(g.get_info(li).layer,g.get_info(li).datatype):pya.Region(top.begin_shapes_rec(li)).merged()for li in g.layer_indices()}
def structure(g):
 return {c.name:sorted((g.cell(i.cell_index).name,str(i.cplx_trans),i.na,i.nb,str(i.a),str(i.b))for i in c.each_inst())for c in g.each_cell()}
def texts(g):
 return sorted((c.name,g.get_info(li).layer,g.get_info(li).datatype,str(s.text))for c in g.each_cell()for li in g.layer_indices()for s in c.shapes(li).each()if s.is_text())
def max_uncontacted(intervals,contacts):
 maximum=0.
 for lo,hi in intervals:
  probes=[lo,hi]+[(a+b)/2 for a,b in zip(contacts,contacts[1:])if lo<=(a+b)/2<=hi]
  maximum=max(maximum,max(min(abs(p-c)for c in contacts)for p in probes))
 return maximum

def generate(cfg):
 import klayout.db as pya
 from importlib.metadata import version
 need(version("klayout")=="0.30.4.post1","pinned native geometry package")
 selected=NATIVE/"current";selected.mkdir()
 acquire(cfg["view"],selected,lambda n:n in cfg["view"]["selected"])
 gds=selected/"native/selected/layout/nssoc_cdr_pd500_resistor_v59.gds"
 need(pin(gds)==dict(bytes=1019324,sha256="17bcc6f9e98f5346e92f7c770f4212a012ab1718ba78432fd609e280ff5e0541"),"actual independently650 DRC LVS qualified GDS")
 g=pya.Layout();g.read(str(gds));need(g.dbu==.001 and len(g.top_cells())==1,"exact nm grid and top")
 top=g.top_cell();need(top.name=="nssoc_cdr_pd500_resistor_v59","actual macro")
 before=layer_regions(g,top,pya);hierarchy=structure(g);annotations=texts(g);bounds=top.bbox()
 poly=before[(5,0)];active=before[(1,0)]
 # Audit before ANY proposed mutation. A Via1 without any M1 cannot connect
 # its two intended metal layers; remove only the exact recorded whole cuts.
 initial_missing=before[(19,0)]-before[(8,0)]
 orphan_vias=pya.Region()
 for vp in before[(19,0)].each():
  if (pya.Region(vp)&before[(8,0)]).is_empty():orphan_vias.insert(vp)
 save("original-via1-coverage.json",dict(original_gds=pin(gds),original_missing_area_dbu2=initial_missing.area(),
  entirely_detached_cuts=orphan_vias.count(),entirely_detached_area_dbu2=orphan_vias.area(),
  cuts=[str(pg)for pg in orphan_vias.each()],measured_before_any_mutation=True,**FLAGS))
 need(orphan_vias.count()==96 and orphan_vias.area()==3465600 and(initial_missing^orphan_vias).is_empty(),
   "exact96 completely M1-detached input Via1 cuts; no partially attached cuts removed")

 native_lvs=pya.LayoutVsSchematic();native_lvs.read(str(selected/"native/selected/physical/lvs_flat/result.lvsdb"))
 physical_wires=pya.LayoutToNetlist();physical_wires.read(str(selected/"native/view/wire/native05/wires.l2n"))
 wire_graph=read(selected/"native/view/wire/native05/result.json")
 wire_m1=physical_wires.layer_by_name("gds_8")
 native_m1=native_lvs.layer_by_index(wire_graph["native_layer_mapping"]["8"])

 grouped={}
 for row in read(selected/"derived/gate-poly-access.json")["gates"]:
  key=json.dumps([row["access_poly_polygons"],row["contact_polygons"]],sort_keys=True)
  grouped.setdefault(key,[]).append(row)
 need(len(grouped)==50 and sum(map(len,grouped.values()))==200,"all physical gate groups")
 added={k:pya.Region()for k in((6,0),(8,0))}
 metal=dict(before);metal[(19,0)]=before[(19,0)]-orphan_vias
 removed_m1=pya.Region();removed_v1=orphan_vias.dup()
 extra_m1={};extra_m2={};relocations=[]
 native_devices={d.id():d for d in native_lvs.netlist().top_circuit().each_device()}
 wire_m2=physical_wires.layer_by_name("gds_10")
 plans=[]
 globals()["relocation_progress"]=dict(groups=plans,relocations=relocations)
 for rows in grouped.values():
  ids=[r["device"]for r in rows];need(len({r["native_cluster"]for r in rows})==1,"same native gate owner per actual poly group")
  path=pya.Region()
  for s in rows[0]["access_poly_polygons"]:path.insert(polygon(s,pya))
  contact=pya.Region()
  for s in rows[0]["contact_polygons"]:contact.insert(polygon(s,pya))
  need(path.count()==1 and contact.count()==1 and(path-poly).is_empty(),"bound existing poly/contact group")
  rec=dict(devices=ids,native_cluster=rows[0]["native_cluster"],gate_poly_area_dbu2=path.area(),
    nSD_overlap_dbu2=(path&before.get((7,0),pya.Region())).area(),
    pSD_overlap_dbu2=(path&before.get((14,0),pya.Region())).area(),
    salicide_block_overlap_dbu2=(path&before.get((28,0),pya.Region())).area())
  if len(rows)==1:
   rec["disposition"]="UNCHANGED_SINGLE_UNIT";plans.append(rec);continue
  boxes=[]
  for row in rows:
   need(len(row["terminal_polygons"])==1,"one physical gate electrode")
   pg=polygon(row["terminal_polygons"][0],pya);b=pg.bbox()
   need((pya.Region(pg)^pya.Region(b)).is_empty()and b.width()==300,"actual vertical300nm gate channel length")
   boxes.append(b)
  boxes.sort(key=lambda b:b.bottom)
  need(len({(b.left,b.right)for b in boxes})==1,"aligned actual poly stem")
  gx=(boxes[0].left+boxes[0].right)//2
  c=contact.bbox().center();need(c.x==gx,"original aligned top contact")
  intervals=[(b.bottom,b.top)for b in boxes]
  gaps=[(a.top+b.bottom)//2 for a,b in zip(boxes,boxes[1:])]
  need(all(b.bottom-a.top==500 for a,b in zip(boxes,boxes[1:])),"actual500nm unit gaps")
  cuts=pya.Region()
  for y in gaps:cuts.insert(pya.Box(gx-80,y-80,gx+80,y+80))
  need((cuts.sized(70)-poly).is_empty(),"complete70nm existing poly enclosure")
  need((cuts.sized(140)&active).is_empty(),"actual140nm gate-contact active clearance")
  need((cuts.sized(180)&before[(6,0)]).is_empty(),"existing contact clearance")
  allowed=before[(8,0)].interacting(contact)
  need(not allowed.is_empty(),"actual original metal gate attachment")
  # All exemption geometry comes from the exact already-qualified physical wire net,
  # not native labels or schematic aliases and not an inferred proximity bridge.
  wn=physical_wires.probe_net(wire_m1,c);ln=native_lvs.probe_net(native_m1,c)
  need(wn is not None and ln is not None and ln.cluster_id==rows[0]["native_cluster"],"actual gate contact physical and native owner")
  own_m1=physical_wires.shapes_of_net(wn,wire_m1,True).merged()
  need((own_m1-before[(8,0)]).is_empty()and(allowed-own_m1).is_empty(),"complete own physical M1 lies in exact GDS and contains original contact component")
  rec.update(actual_wire_component=wn.cluster_id,original_contact_m1_area_dbu2=allowed.area(),complete_same_gate_m1_area_dbu2=own_m1.area())
  ys=sorted(gaps+[c.y])
  m1=pya.Region(pya.Box(gx-80,min(ys)-130,gx+80,max(ys)+130))
  ds_owners=set()
  for row in rows:
   dev=native_devices[row["device"]]
   for td in dev.device_class().terminal_definitions():
    if td.name in("S","D"):ds_owners.add(dev.net_for_terminal(td.id()).cluster_id)
  original_vias=[]
  for vp in metal[(19,0)].interacting(m1.sized(400)).each():
   vb=vp.bbox();vc=vb.center()
   if vc.x==gx:continue
   pad=pya.Region(pya.Box(vb.left-50,vb.bottom-50,vb.right+50,vb.top+50))
   if (pad&m1.sized(180)).is_empty():continue
   need(vb.width()==190 and vb.height()==190 and(pya.Region(vp)^pya.Region(vb)).is_empty(),"actual standard source/drain Via1")
   need((pad-before[(8,0)]).is_empty(),"actual source/drain50nm M1 via enclosure")
   owner=native_lvs.probe_net(native_m1,vc);wire_owner=physical_wires.probe_net(wire_m1,vc)
   need(owner is not None and wire_owner is not None and owner.cluster_id in ds_owners,"actual original source/drain ownership")
   dx=min(0,gx-310-vb.right)if vc.x<gx else max(0,gx+310-vb.left)
   need(dx!=0 and abs(dx)<=500 and dx%5==0,"bounded actual source/drain cut displacement")
   nb=pya.Box(vb.left+dx,vb.bottom,vb.right+dx,vb.top)
   npad=pya.Region(pya.Box(nb.left-50,nb.bottom-50,nb.right+50,nb.top+50))
   original_vias.append((pya.Region(vp),pya.Region(nb),pad,npad,wire_owner,owner.cluster_id,dx))
  old_cuts=pya.Region();new_cuts=pya.Region();old_pads=pya.Region();new_pads=pya.Region()
  for ov,nv,op,np,wo,no,dx in original_vias:
   old_cuts+=ov;new_cuts+=nv;old_pads+=op;new_pads+=np
  if original_vias:
   need((old_cuts&removed_v1).is_empty(),"no physical via is moved twice")
   future_m1=(metal[(8,0)]-old_pads)+new_pads
   future_v1=(metal[(19,0)]-old_cuts)+new_cuts
   future_m2=metal[(10,0)]+new_pads
   need((before[(6,0)]-future_m1).is_empty(),"every original contact remains completely covered")
   need((new_cuts.sized(50)-future_m1).is_empty()and(new_cuts.sized(50)-future_m2).is_empty(),"relocated via enclosures")
   need((new_cuts&(metal[(19,0)]-old_cuts).sized(220)).is_empty(),"relocated vias preserve spacing to every remaining via")
   for ov,nv,op,np,wo,no,dx in original_vias:
    netid=wo.cluster_id
    own1=(physical_wires.shapes_of_net(wo,wire_m1,True)-removed_m1)+extra_m1.get(netid,pya.Region())
    own2=physical_wires.shapes_of_net(wo,wire_m2,True)+extra_m2.get(netid,pya.Region())
    need((np&(metal[(8,0)]-own1).sized(180)).is_empty(),"new source/drain M1 landing foreign-net spacing")
    need((np&(metal[(10,0)]-own2).sized(210)).is_empty(),"new source/drain M2 landing foreign-net spacing")
    need(not(np&own1).is_empty()and not(np&own2).is_empty(),"relocated landing overlaps same physical source/drain net on both layers")
    recmove=dict(gate_devices=ids,source_drain_native_owner=no,wire_component=netid,dx_dbu=dx,
      old_via=[str(p)for p in ov.each()],new_via=[str(p)for p in nv.each()],
      old_m1_landing=[str(p)for p in op.each()],new_m1_m2_landing=[str(p)for p in np.each()])
    relocations.append(recmove)
    extra_m1.setdefault(netid,pya.Region());extra_m1[netid]+=np
    extra_m2.setdefault(netid,pya.Region());extra_m2[netid]+=np
   removed_m1+=old_pads;removed_v1+=old_cuts
   metal[(8,0)]=future_m1.merged();metal[(19,0)]=future_v1.merged();metal[(10,0)]=future_m2.merged()
  corridor=pya.Region(pya.Box(gx-260,min(ys)-310,gx+260,max(ys)+310))
  own_gate_now=(own_m1-removed_m1)+extra_m1.get(wn.cluster_id,pya.Region())
  protrusions=(metal[(8,0)]-own_gate_now)&corridor
  if not protrusions.is_empty():
   # Prove every remaining metal sliver is one of this group's original S/D nets.
   original_part=protrusions&before[(8,0)]
   need((protrusions-original_part).is_empty(),"only original S/D bar protrusions trimmed")
   owners=[]
   for pg in original_part.each():
    points=[]
    for edge in pg.each_edge():
     q=edge.p1;r=edge.p2
     mx=(q.x+r.x)//2;my=(q.y+r.y)//2
     points.extend([pya.Point(mx+1,my),pya.Point(mx-1,my),pya.Point(mx,my+1),pya.Point(mx,my-1)])
    pt=next((pt for pt in points if pg.inside(pt)),None)
    need(pt is not None,"strict interior ownership sample")
    actual=native_lvs.probe_net(native_m1,pt)
    need(actual is not None and actual.cluster_id in ds_owners,"every trimmed conductor belongs to actual S/D")
    owners.append(actual.cluster_id)
   trimmed=metal[(8,0)]-protrusions
   need((before[(6,0)]-trimmed).is_empty(),"bar trimming retains every original Cont")
   missing=metal[(19,0)]-trimmed
   if not missing.is_empty():
    touched=metal[(19,0)].interacting(missing)
    roi=touched.sized(400)
    save("actual-via-coverage-failure.json",dict(gate_devices=ids,gate_x_dbu=gx,
      original_missing_area_dbu2=(before[(19,0)]-before[(8,0)]).area(),
      post_move_missing_area_dbu2=(metal[(19,0)]-metal[(8,0)]).area(),
      post_trim_missing_area_dbu2=missing.area(),
      original_missing=[str(pg)for pg in(before[(19,0)]-before[(8,0)]).each()],
      missing=[str(pg)for pg in missing.each()],actual_vias=[str(pg)for pg in touched.each()],
      original_m1=[str(pg)for pg in(before[(8,0)]&roi).each()],
      moved_m1=[str(pg)for pg in(metal[(8,0)]&roi).each()],
      trimmed_m1=[str(pg)for pg in(trimmed&roi).each()],
      removed_bar=[str(pg)for pg in(protrusions&roi).each()],
      source_drain_relocations=relocations,**FLAGS))
   need(missing.is_empty(),"bar trimming retains every actual Via1 cut")
   metal[(8,0)]=trimmed.merged();removed_m1+=protrusions
   rec["trimmed_source_drain_bar_protrusions"]=[str(pg)for pg in protrusions.each()]
   rec["trimmed_source_drain_native_owners"]=owners
  own_gate=(own_m1-removed_m1)+extra_m1.get(wn.cluster_id,pya.Region())
  foreign_m1=(metal[(8,0)]-own_gate)+added[(8,0)]
  blocked_m1=foreign_m1.sized(180)
  rec["relocated_source_drain_vias"]=len(original_vias)
  clashes=dict(m1_area=(m1&blocked_m1).area(),outside_macro_area=(m1-pya.Region(bounds)).area())
  attempts=[dict(bus_x_dbu=gx,strap_width_dbu=160,**clashes)]
  chosen=None if any(clashes.values())else m1
  rec.update(attempts=attempts,planned_contacts=len(gaps),old_max_gate_to_contact_um=.001*max_uncontacted(intervals,[c.y]),
    new_max_gate_to_contact_um=.001*max_uncontacted(intervals,ys))
  if chosen is None:
   rec["disposition"]="NO_CLEAR_M1_GATE_STRAP";plans.append(rec)
   # Derived clipped outlines expose actual obstacles without exporting a native layout.
   roi=pya.Region(pya.Box(gx-1200,boxes[0].top-500,gx+1200,boxes[1].bottom+500))
   rec["first_gap_obstacles"]={str(k):[str(pg)for pg in (v&roi).each()]for k,v in before.items()if k in((1,0),(5,0),(6,0),(8,0),(10,0),(19,0))}
   rec["first_gap_gate_x_dbu"]=gx;rec["first_gap_y_dbu"]=gaps[0]
   rec["whole_strap_spacing_intersections"]=[str(pg)for pg in(m1&blocked_m1).each()]
   rec["whole_strap_actual_foreign_m1"]=[str(pg)for pg in(foreign_m1&m1.sized(181)).each()]
   rec["whole_strap_actual_same_gate_m1"]=[str(pg)for pg in(own_m1&m1.sized(181)).each()]
   rec["whole_strap_original_contacts"]=[str(pg)for pg in(before[(6,0)]&m1.sized(600)).each()]
   print(json.dumps(dict(gate_devices=ids,status="REJECTED_ACTUAL_FULL_STRAP",clashes=clashes)),flush=True)
   continue
  m1=chosen
  need((cuts-m1).is_empty(),"complete contact coverage without prohibited lateral widening")
  for y in gaps:
   need((pya.Region(pya.Box(gx-80,y-130,gx+80,y+130))-m1).is_empty(),"50nm longitudinal contact endcaps")
  need(not (m1&allowed).is_empty(),"new strap attaches to original same-gate M1")
  for k,v in [((6,0),cuts),((8,0),m1)]:added[k]+=v;added[k].merge()
  rec.update(disposition="ADDED_LOCAL_CONTACTS_M1_GATE_STRAP",bus_x_dbu=gx,strap_width_dbu=160,via1_count=0,
   longitudinal_contact_endcap_dbu=50,foreign_m1_minimum_spacing_dbu=180)
  print(json.dumps(dict(gate_devices=ids,status=rec["disposition"],new_contacts=len(gaps))),flush=True)
  plans.append(rec)
 failed=[r for r in plans if r["disposition"]=="NO_CLEAR_M1_GATE_STRAP"]
 if failed:
  save("geometry-plan-failure.json",dict(groups=plans,failed_groups=len(failed),source_drain_via_relocations=relocations,**FLAGS))
  raise ValueError("No clear160nm M1 gate strap for "+str(len(failed))+" actual groups")
 need(sum(r.get("planned_contacts",0)for r in plans)==150 and len([r for r in plans if r["disposition"].startswith("ADDED")])==42,"all multi-unit groups repaired")
 for key,region in added.items():
  for pg in region.each():
   need(all(p.x%5==0 and p.y%5==0 for p in pg.each_point_hull()),"all new geometry5nm grid")
 for key in((8,0),(10,0),(19,0)):
  li=g.layer(*key)
  for cell in g.each_cell():
   shapes=cell.shapes(li)
   for shape in list(shapes.each()):
    if not shape.is_text():shapes.erase(shape)
  desired=(metal[key]+added.get(key,pya.Region())).merged()
  for pg in desired.each():
   need(all(p.x%5==0 and p.y%5==0 for p in pg.each_point_hull()),"all relocated conductor geometry5nm grid")
  top.shapes(li).insert(desired)
 top.shapes(g.layer(6,0)).insert(added[(6,0)])
 after=layer_regions(g,top,pya)
 for key,old in before.items():
  expected=(metal[key]+added.get(key,pya.Region())).merged()
  need((after[key]^expected).is_empty(),"only declared material changes "+str(key))
 deltas={str(k):dict(added_area_dbu2=(after[k]-old).area(),removed_area_dbu2=(old-after[k]).area())for k,old in before.items()}
 need(all(v["added_area_dbu2"]==0 and v["removed_area_dbu2"]==0 for k,v in deltas.items()if k not in("(6, 0)","(8, 0)","(10, 0)","(19, 0)")),"all original nonconductor and transistor geometry unchanged")
 save("source-drain-via-relocation.json",dict(relocations=relocations,count=len(relocations),material_deltas=deltas,removed_original_detached_via1_cuts=96,
  all_original_contacts_covered=True,all_original_device_geometry_retained=True,requires_full_DRC_LVS=True,**FLAGS))
 need(structure(g)==hierarchy and texts(g)==annotations,"unchanged complete hierarchy and text annotations")
 layout=NATIVE/"layout";layout.mkdir()
 target=layout/gds.name;opts=pya.SaveLayoutOptions();opts.write_context_info=False;g.write(str(target),opts)
 restored=pya.Layout();restored.read(str(target));rt=restored.top_cell();readback=layer_regions(restored,rt,pya)
 need(set(readback)==set(after)and restored.dbu==g.dbu and rt.bbox()==bounds,"full GDS material extent/grid roundtrip")
 for key in after:need((after[key]^readback[key]).is_empty(),"all material serialization equality "+str(key))
 need(structure(restored)==hierarchy and texts(restored)==annotations,"complete serialized hierarchy and labels")
 ref=selected/"native/selected/layout/schematic.cir";shutil.copyfile(ref,layout/"schematic.cir")
 parent=read(selected/"native/selected/layout/result.json")
 metadata=dict(parent,status="GENERATED_GATE_METAL_CANDIDATE_REQUIRES_FULL_DRC_LVS",candidate=pin(target),
  gate_metal_repair=dict(groups=plans,added_contacts=150,added_via1=sum(r.get("via1_count",0)for r in plans),
   physical_drc_lvs_qualified=False,RC_or_electrical_accepted=False))
 (layout/"result.json").write_bytes(enc(metadata))
 save("geometry-plan.json",dict(groups=plans,original_candidate=pin(gds),candidate=pin(target),independent_reference=pin(ref),
  added_contact_count=150,added_metal_bus_count=42,unchanged_single_unit_groups=8,
  all_layers_roundtrip_equal=True,all_original_geometry_retained=False,all_original_device_geometry_retained=True,source_drain_via_relocations=len(relocations),
  geometry_guards_are_not_full_DRC=True,**FLAGS))
 return pin(target)

def main():
 ctx=gate()
 if sys.argv[1:]==["--reserve"]:reserve();return
 if sys.argv[1:]==["--publish"]:publish();return
 OUT.mkdir();NATIVE.mkdir();DERIVED.mkdir()
 try:
  cfg=read(ROOT/CFG)
  if sys.argv[1:]==["--controls"]:
   need(cfg["view"]["run"]==41690238100,"current complete physical view")
   save("source-controls.json",dict(context=ctx,source_files_verified=True,**FLAGS));return
  need(sys.argv[1:]==["--extract"],"explicit cloud generation")
  candidate=generate(cfg);gate()
  save("result.json",dict(status="GENERATED_ACTUAL650_GATE_METAL_CANDIDATE_REQUIRES_INDEPENDENT_DRC_LVS",context=ctx,candidate=candidate,**FLAGS))
 except BaseException as e:
  if "relocation_progress"in globals():save("relocation-progress-failure.json",dict(globals()["relocation_progress"],**FLAGS))
  save("failure.json",dict(error_type=type(e).__name__,error=str(e),traceback=traceback.format_exc(),**FLAGS));raise
if __name__=="__main__":main()
