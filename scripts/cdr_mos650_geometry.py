#!/usr/bin/env python3
"""Generate explicit model-range MOS geometry in the actual clock-metal parent.
Candidate generation only; full650 transistor LVS, full DRC and new RC remain mandatory.
"""
import ast,copy,hashlib,io,json,os,re,shutil,subprocess,sys,tarfile,traceback
from decimal import Decimal
from pathlib import Path,PurePosixPath
ROOT=Path(__file__).resolve().parents[1]
OUT=ROOT/"mos650-geometry";NATIVE=OUT/"native";DERIVED=OUT/"derived"
BRANCH="codex/cdr-mos650-geometry";REPO="Melihakbulut221/nssoc"
CFG="scripts/cdr-mos650-geometry-inputs.json"
PINS="scripts/cdr-mos650-geometry-pins.json"
PLAN="docs/evidence/cdr-mos650-original-electrical-plan.json"
IDENTITY="docs/evidence/clock-metal-new-native-identity.json"
MAP="docs/evidence/cdr-clock-access-domain-parent-map.json"
TOP="nssoc_cdr_pd500_resistor_v59"
FLAGS=dict(physical_acceptance=False,full_phy_accepted=False,final_timing_complete=False,
 matching_layout_verified=False,fresh_RC_for_modified_devices=False,electrical_accepted=False)
def need(ok,msg):
 if not ok:raise ValueError(msg)
def enc(d):return(json.dumps(d,sort_keys=True,indent=2,allow_nan=False)+"\n").encode()
def fp(p):
 p=Path(p)
 with p.open("rb")as f:return dict(bytes=p.stat().st_size,sha256=hashlib.file_digest(f,"sha256").hexdigest())
def save(name,d):
 p=DERIVED/name;p.parent.mkdir(parents=True,exist_ok=True)
 with p.open("xb")as f:f.write(enc(d))
def read(p):return json.loads(Path(p).read_bytes())
def api(path):return json.loads(subprocess.check_output(["gh","api","repos/"+REPO+"/"+path],timeout=180))
def gate():
 e=os.environ
 need(e.get("GITHUB_ACTIONS")=="true"and e.get("RUNNER_ENVIRONMENT")=="github-hosted","hosted only")
 need(e["GITHUB_REPOSITORY"]==REPO and e["GITHUB_REF"]=="refs/heads/"+BRANCH,"exact repository and branch")
 need(e["GITHUB_EVENT_NAME"]=="workflow_dispatch"and e["GITHUB_RUN_ATTEMPT"]=="1","first explicit run")
 need(e["APPROVED_SOURCE"]==e["GITHUB_SHA"]==subprocess.check_output(["git","rev-parse","HEAD"],text=True).strip(),"exact source")
 for n,p in read(ROOT/PINS)["files"].items():need(fp(ROOT/n)==p,"source pin "+n)
 return dict(source=e["GITHUB_SHA"],run=int(e["GITHUB_RUN_ID"]),attempt=1)
def um(v):
 need(isinstance(v,str)and re.fullmatch(r"\d+(?:\.\d+)?u",v)is not None,"explicit micrometre value")
 return Decimal(v[:-1])
def nm(v):
 x=um(v)*1000;need(x==int(x)and int(x)%5==0,"five nm primitive grid")
 return int(x)
def validate_plan(plan,mapping):
 pairs={p["layout"]["id"]:p for p in mapping["pairs"]if p["layout"]["model"]=="sg13_lv_nmos"}
 need(len(plan)==len(pairs)==50 and {p["native_id"]for p in plan}==set(pairs),"all50 exact parent MOS")
 total=0;names=set()
 for p in plan:
  old=pairs[p["native_id"]]
  need(p["original_parameters"]==old["loaded_parameters"]and p["source_instance"]==old["loaded_instance"],"actual original parameters")
  need(p["units"]and sum(nm(u["parameters"]["w"])for u in p["units"])==nm(p["original_parameters"]["w"]),"exact total channel width")
  for u in p["units"]:
   q=u["parameters"];need(u["instance"]not in names,"unique unit");names.add(u["instance"])
   need(u["model"]=="sg13_lv_nmos"and q["ng"]==q["m"]=="1","explicit single-finger unit")
   need(8000<=nm(q["w"])<=9000 and q["l"]==p["original_parameters"]["l"],"model domain and original length")
   need([t["terminal"]for t in u["terminals"]]==["D","G","S","B"],"complete ordered terminals")
   for t in u["terminals"]:
    original=old["layout"]["terminals"][t["terminal"]]
    need((t["native_cluster"],t["native_net"])==(original["cluster"],original["name"]),"actual terminal owner")
   w=um(q["w"])
   need(Decimal(q["ad"][:-1])==Decimal(q["as"][:-1])==w*Decimal(".34")and q["ad"].endswith("p")and q["as"].endswith("p"),"per-unit diffusion areas")
   need(Decimal(q["pd"][:-1])==Decimal(q["ps"][:-1])==2*(w+Decimal(".34"))and q["pd"].endswith("u")and q["ps"].endswith("u"),"per-unit junction perimeters")
   total+=1
 need(total==200,"all200 proposed MOS")
 return dict(original_mos=50,proposed_mos=total,original_other_devices=450,proposed_total=650)
def controls():
 ctx=gate();plan=read(ROOT/PLAN)["plan"];mapping=read(ROOT/MAP)
 proof=validate_plan(plan,mapping);rejected=[]
 for label in ("missing-origin","duplicate-unit","wrong-length","wrong-owner","out-of-domain","wrong-total-width","stale-perimeter"):
  p=copy.deepcopy(plan);u=p[0]["units"][0]
  if label=="missing-origin":p.pop()
  elif label=="duplicate-unit":p[1]["units"][0]["instance"]=u["instance"]
  elif label=="wrong-length":u["parameters"]["l"]="0.5u"
  elif label=="wrong-owner":u["terminals"][0]["native_cluster"]+=10000
  elif label=="out-of-domain":u["parameters"]["w"]="11u"
  elif label=="wrong-total-width":u["parameters"]["w"]="8.005u"
  else:u["parameters"]["pd"]="999u"
  try:validate_plan(p,mapping)
  except ValueError:rejected.append(label)
  else:raise ValueError("missed invalid plan "+label)
 need(len(rejected)==7,"all input refusals")
 save("source-controls.json",dict(context=ctx,plan=proof,rejected=rejected,native_executed=False,**FLAGS))
 return plan,mapping
def fetch(a,p):
 p.parent.mkdir(parents=True,exist_ok=True)
 with p.open("xb")as f:subprocess.run(["gh","api","repos/"+REPO+"/releases/assets/"+str(a["id"]),"-H","Accept: application/octet-stream"],stdout=f,check=True,timeout=600)
 need(fp(p)=={k:a[k]for k in ("bytes","sha256")},"asset bytes")
def acquire(cfg):
 prod=cfg["producer"];r=api("actions/runs/"+str(prod["run"]));rel=api("releases/"+str(prod["release"]))
 need(r["head_sha"]==prod["source"]and r["conclusion"]=="success"and r["run_attempt"]==1,"actual freshRC producer")
 need(rel["target_commitish"]==prod["source"]and rel["tag_name"]==prod["tag"]and api("git/ref/tags/"+prod["tag"])["object"]["sha"]==prod["source"],"RC release source")
 live={a["name"]:a for a in rel["assets"]};need(set(live)==set(prod["assets"]),"all assets")
 for name,a in prod["assets"].items():
  need(live[name]["id"]==a["id"]and live[name]["size"]==a["bytes"]and live[name]["digest"]=="sha256:"+a["sha256"],"live asset")
  fetch(a,NATIVE/name)
 index=read(NATIVE/"complete-output-index.json")
 need(index["files"]==prod["complete_members"]and index["context"]==dict(source=prod["source"],run=prod["run"],attempt=1),"complete index")
 seen=set();selected={cfg["gds_path"]}
 with tarfile.open(NATIVE/"native-fresh-rc.tar.gz","r|gz")as tar:
  for m in tar:
   prefix=prod["archive_root"]+"/";need(m.isfile()and m.name.startswith(prefix),"regular indexed member")
   n=m.name[len(prefix):];need(n in index["files"]and n not in seen,"unique indexed member");seen.add(n)
   h=hashlib.sha256();size=0;dest=None
   if n in selected:dest=(NATIVE/"parent.gds").open("xb")
   stream=tar.extractfile(m)
   try:
    for b in iter(lambda:stream.read(1024*1024),b""):
     h.update(b);size+=len(b)
     if dest is not None:dest.write(b)
   finally:
    if dest is not None:dest.close()
   need(dict(bytes=size,sha256=h.hexdigest())==index["files"][n],"every archive member")
 need(seen==set(index["files"])and fp(NATIVE/"parent.gds")==cfg["candidate"],"complete parent acquisition")
 save("acquisition.json",dict(producer=prod["run"],source=prod["source"],members=len(seen),candidate=cfg["candidate"],**FLAGS))
def pdk(cfg):
 target=NATIVE/"runtime.tar.gz";fetch(cfg["runtime_receipt"],target)
 dest=NATIVE/"runtime";dest.mkdir()
 with tarfile.open(target)as tar:
  members=tar.getmembers();names=[m.name for m in members];need(len(names)==len(set(names)),"unique runtime members")
  manifest=json.loads(tar.extractfile("manifest.json").read());observed={}
  for m in members:
   n=PurePosixPath(m.name)
   need(not n.is_absolute()and ".."not in n.parts and str(n)==m.name.rstrip("/"),"runtime path")
   if m.isdir():continue
   need(m.isfile()and(m.name=="manifest.json"or m.name in manifest["files"]),"known regular runtime source")
   data=tar.extractfile(m).read()
   if m.name!="manifest.json":
    h=hashlib.sha256(data).hexdigest();need(h==manifest["files"][m.name]["sha256"],"runtime source hash");observed[m.name]=h
   q=dest/m.name;q.parent.mkdir(parents=True,exist_ok=True)
   with q.open("xb")as f:f.write(data)
 need(set(observed)==set(manifest["files"]),"all runtime source members")
 save("runtime-source.json",dict(receipt=cfg["runtime_receipt"],files=observed,**FLAGS))
 return dest/"pdk"

def geometry(plan,mapping,pdkroot):
 sys.dont_write_bytecode=True
 source=pdkroot/"libs.tech/klayout/python";need(source.is_dir(),"actual pinned native PCell source")
 sys.path[:0]=[str(source),str(source/"pycell4klayout-api/source/python")]
 import pya
 import sg13g2_pycell_lib
 layout=pya.Layout();layout.read(str(NATIVE/"parent.gds"))
 need(layout.dbu==.001 and layout.cell(TOP)is not None,"actual parent top and grid")
 top=layout.cell(TOP);oldbbox=str(top.bbox());identity=read(ROOT/IDENTITY)
 original_m1_pin_annotations=pya.Region(top.begin_shapes_rec(layout.layer(8,2))).merged()
 paths={r["native_device"]:r["stable_path"]for r in identity["paths"]}
 observed={r["native_id"]:r for r in identity["locations"]["devices"]}
 need(len(paths)==len(observed)==500,"all original identities")
 def layer_key(info):return str(info.layer)+"/"+str(info.datatype)
 def all_shapes(cell):
  return {layer_key(layout.get_info(i)):pya.Region(cell.begin_shapes_rec(i)).merged()for i in layout.layer_indexes()}
 def compare(a,b,message):
  for k in set(a)|set(b):need((a.get(k,pya.Region())^b.get(k,pya.Region())).is_empty(),message+" "+k)
 def signature(cell,original_names=None):
  original_names={}if original_names is None else original_names
  shapes=[(layer_key(layout.get_info(i)),sorted(str(x)for x in cell.each_shape(i)))for i in layout.layer_indexes()if not cell.shapes(i).is_empty()]
  inst=sorted((original_names.get(x.cell.name,x.cell.name),str(x.cplx_trans),x.na,x.nb,str(x.a),str(x.b),x.prop_id)for x in cell.each_inst())
  return hashlib.sha256(enc(dict(shapes=shapes,instances=inst))).hexdigest()
 original_cells={c.cell_index():signature(c)for c in layout.each_cell()}
 targets=[];by_parent={};old_leaves=set()
 for p in plan:
  did=p["native_id"];row=observed[did];path=paths[did]
  need(row["model"]=="sg13_lv_nmos"and path["root"]==TOP,"native MOS path");cell=top
  for level in path["levels"]:
   need(cell.name==level["parent_cell"]and not level["is_regular_array"]and level["array_element"]==0,"single actual path")
   instances=list(cell.each_inst());ordinal=level["instance_ordinal"];need(ordinal<len(instances),"actual instance ordinal")
   inst=instances[ordinal]
   need(inst.cell.name==level["child_cell"]and str(inst.dcplx_trans)==level["dcplx_trans_um"],"actual child and transform")
   parent=cell;cell=inst.cell
  need(cell.name==path["leaf_cell"]and cell.name==row["pcell"]["cell"],"actual native leaf")
  need(round(row["parameters"]["W"]*1000)==nm(p["original_parameters"]["w"]),"actual original width")
  old_leaves.add(cell.cell_index());targets.append((p,row,parent,ordinal,cell,inst))
  if len(p["units"])>1:by_parent.setdefault(parent.cell_index(),{})[ordinal]=cell.name
 # Reject any PDK/runtime drift before changing actual parent instances.
 units={};old_shapes={};old_proof=[];reconstruction_differences=[]
 for p,row,parent,ordinal,cell,instance in targets:
  key=(p["original_parameters"]["w"],p["original_parameters"]["l"])
  if key not in units:
   native=layout.create_cell("nmos","SG13_dev",dict(w=key[0],l=key[1],ng=1))
   need(native is not None and native.cell_index()not in old_leaves,"fresh original PCell");units[key]=native
  a=all_shapes(cell);b=all_shapes(units[key]);old_shapes[cell.cell_index()]=a
  differences=[]
  for layer in sorted(set(a)|set(b)):
   ar=a.get(layer,pya.Region());br=b.get(layer,pya.Region());delta=(ar^br).merged()
   if not delta.is_empty():
    describe=lambda r:dict(area_dbu2=r.area(),bbox_dbu=str(r.bbox()),polygons=r.count())
    differences.append(dict(layer=layer,original=describe(ar),regenerated=describe(br),symmetric_difference=describe(delta),
      original_polygons=[str(p)for p in ar.each()],regenerated_polygons=[str(p)for p in br.each()]))
  if differences:reconstruction_differences.append(dict(native_id=p["native_id"],original_cell=cell.name,
      original_parameters=p["original_parameters"],differences=differences))
  old_proof.append(dict(native_id=p["native_id"],original_cell=cell.name,original_parameters=p["original_parameters"],native_PCell_geometry_equal=not differences))
 save("pcell-reconstruction.json",dict(devices=50,full_layer_differences=reconstruction_differences,
  candidate_modified=False,pdk_receipt=read(ROOT/CFG)["runtime_receipt"],**FLAGS))
 documented=read(ROOT/"docs/evidence/mos650-original-pcell-marker-differences.json")["full_layer_differences"]
 need(reconstruction_differences==documented and len(documented)==50,"exact observed marker-only differences; no fabrication or other annotation drift")
 for record in documented:
  need(len(record["differences"])==1 and record["differences"][0]["layer"]=="8/2","only documented internal M1 pin annotations")
  d=record["differences"][0];need(d["original"]==dict(area_dbu2=0,bbox_dbu="()",polygons=0)and not d["original_polygons"]and d["regenerated"]["polygons"]==2,"original annotations absent,exact regenerated pair")
 def pin_boxes(cell,layer):
  return sorted([x.bbox()for x in cell.each_shape(layout.layer(layer,2))if not x.is_text()],key=lambda b:(b.left,b.bottom))
 cache={};modifications=[];replaced={};reference_names={};new_unit_cells=set();new_wrapper_cells=set()
 for p,row,parent,ordinal,cell,instance in targets:
  if len(p["units"])==1:continue
  spec=[(u["parameters"]["w"],u["parameters"]["l"])for u in p["units"]];key=(cell.cell_index(),tuple(spec))
  if key not in cache:
   wrapper=layout.create_cell("nssoc_model_range_"+str(cell.cell_index()))
   need(wrapper is not None and wrapper.cell_index()not in original_cells,"new wrapper")
   oldg=pin_boxes(cell,5);native_original=units[(p["original_parameters"]["w"],p["original_parameters"]["l"])]
   oldm=pin_boxes(native_original,8);need(len(oldg)==1 and len(oldm)==2,"original gate and independently regenerated source/drain annotations")
   original_m1=pya.Region(cell.begin_shapes_rec(layout.layer(8,0))).merged()
   for box in oldm:need((pya.Region(box)-original_m1).is_empty(),"regenerated annotation is inside unchanged original physical M1")
   new_wrapper_cells.add(wrapper.cell_index())
   width=nm(p["original_parameters"]["w"]);gap=1000;y=-gap*(len(spec)-1);placements=[];gates=[];rails=[[],[]]
   for index,(w,l)in enumerate(spec):
    params=dict(w=w,l=l,ng=1);unit=layout.create_cell("nmos","SG13_dev",params)
    need(unit is not None and unit.cell_index()not in old_leaves,"fresh explicit native unit")
    new_unit_cells.add(unit.cell_index())
    gp=pin_boxes(unit,5);mp=pin_boxes(unit,8)
    need(len(gp)==1 and len(mp)==2 and gp[0].width()==oldg[0].width(),"unit terminal geometry")
    need(gp[0].height()==nm(w)+360 and gp[0].bottom==-180,"actual native unit width")
    trans=pya.Trans(0,y);wrapper.insert(pya.CellInstArray(unit.cell_index(),trans));gates.append(gp[0].transformed(trans))
    for j in (0,1):
     need((mp[j].left,mp[j].right)==(oldm[j].left,oldm[j].right),"same source/drain rail columns")
     rails[j].append(mp[j].transformed(trans))
    placements.append(dict(index=index,cell=unit.name,parameters=params,translation_dbu=[0,y]));y+=nm(w)+gap
   need(y-gap==width and gates[-1].top==oldg[0].top,"original top gate access retained")
   gate=pya.Box(oldg[0].left,gates[0].bottom,oldg[0].right,oldg[0].top)
   wrapper.shapes(layout.layer(5,0)).insert(gate);wrapper.shapes(layout.layer(5,2)).insert(gate)
   for boxes in rails:
    rail=pya.Box(boxes[0].left,min(b.bottom for b in boxes),boxes[0].right,max(b.top for b in boxes))
    wrapper.shapes(layout.layer(8,0)).insert(rail);wrapper.shapes(layout.layer(8,2)).insert(rail)
   cache[key]=(wrapper,placements)
  wrapper,placements=cache[key];target=(parent.cell_index(),ordinal)
  if target in replaced:need(replaced[target]==wrapper.cell_index(),"shared hierarchy has identical plan")
  else:
   need(instance.cell_index==cell.cell_index(),"original reference still present")
   instance.cell_index=wrapper.cell_index();replaced[target]=wrapper.cell_index()
   reference_names[wrapper.name]=cell.name
  modifications.append(dict(native_id=p["native_id"],path=paths[p["native_id"]],original_cell=cell.name,replacement_cell=wrapper.name,
    source_instance=p["source_instance"],units=placements,vertical_diffusion_gap_dbu=1000,old_top_access_retained=True))
 need(len(modifications)==42 and sum(len(p["units"])for p in plan)==200,"all required physical replacements")
 # Restore the observed parent convention: internal M1 pin annotations are absent.
 # Only datatype2 markers in newly created cells are removed; actual Metal1 remains.
 for idx in new_unit_cells|new_wrapper_cells:
  need(idx not in original_cells,"never remove original annotations")
  layout.cell(idx).shapes(layout.layer(8,2)).clear()
 need((pya.Region(top.begin_shapes_rec(layout.layer(8,2))).merged()^original_m1_pin_annotations).is_empty(),"all original public M1 annotations preserved exactly")
 for idx,digest in original_cells.items():need(signature(layout.cell(idx),reference_names)==digest,"every original shape and untargeted hierarchy reference unchanged")
 for p,row,parent,ordinal,cell,instance in targets:compare(old_shapes[cell.cell_index()],all_shapes(cell),"old primitive cells unchanged")
 need(str(top.bbox())==oldbbox,"unchanged macro bounds")
 before=all_shapes(top);out=NATIVE/"candidate-mos650.gds"
 options=pya.SaveLayoutOptions();options.select_cell(top.cell_index())
 # Physical GDS contains actual polygons, not executable PCell/library context.
 # Context would regenerate the PCell on read and restore deliberately absent pins.
 options.write_context_info=False;layout.write(str(out),options)
 reread=pya.Layout();reread.read(str(out));need(reread.dbu==layout.dbu and [c.name for c in reread.top_cells()]==[TOP],"serialized unique candidate top")
 after={layer_key(reread.get_info(i)):pya.Region(reread.cell(TOP).begin_shapes_rec(i)).merged()for i in reread.layer_indexes()}
 serialization=[]
 for key in sorted(set(before)|set(after)):
  a=before.get(key,pya.Region());b=after.get(key,pya.Region());delta=(a^b).merged()
  serialization.append(dict(layer=key,before_area_dbu2=a.area(),after_area_dbu2=b.area(),difference_area_dbu2=delta.area(),
   difference_polygons=[str(p)for p in delta.each()]))
 save("serialization.json",dict(write_context_info=False,layers=serialization,all_layers_equal=all(x["difference_area_dbu2"]==0 and not x["difference_polygons"]for x in serialization),**FLAGS))
 compare(before,after,"all serialized candidate polygons")
 need(all(not c.is_pcell_variant()and not c.is_library_cell()for c in reread.each_cell()),"physical stream has no regenerating PCell/library context")
 save("geometry-proposal.json",dict(original_pcell_reconstruction=old_proof,modifications=modifications,replaced_hierarchy_instances=len(replaced),
  candidate=fp(out),primitive_plan=dict(original_mos=50,explicit_mos=200,other_devices=450,total=650),
  eight_original_narrow_mos_unchanged=True,only_documented_internal_marker_normalization=True,all_serialized_polygons_equal=True,physical_stream_has_no_executable_pcell_context=True,all_original_public_m1_annotations_unchanged=True,all_original_shapes_and_untargeted_references_unchanged=True,macro_bbox=oldbbox,grid_dbu=5,
  native_transistor_extraction_executed=False,full_DRC_executed=False,**FLAGS))
 return fp(out)

def reference(plan,mapping):
 plans={p["native_id"]:p for p in plan};lines=["* Original schematic plus explicit MOS units; requires independent native LVS.",
 ".subckt "+TOP+" "+" ".join(read(ROOT/CFG)["semantic_ports"])]
 names=set();counts={}
 def emit(prefix,name,nets,model,params):
  instance=prefix+name;need(instance.lower()not in names,"unique schematic name");names.add(instance.lower())
  need(all(isinstance(n,str)and not any(c.isspace()for c in n)for n in nets),"explicit original schematic nets")
  lines.append(" ".join([instance,*nets,model,*[k+"="+v for k,v in params.items()]]));counts[model]=counts.get(model,0)+1
 def number(v,suffix=""):return format(v,".12g")+suffix
 for pair in mapping["pairs"]:
  r=pair["schematic"];name=r["expanded_name"];t={k.upper():v["expanded_name"]for k,v in r["terminals"].items()};q=r["parameters"];m=r["model"]
  if m=="sg13_lv_nmos":
   for i,u in enumerate(plans[pair["layout"]["id"]]["units"]):emit("M",name+"_U"+str(i),[t[k]for k in ("D","G","S","B")],m,{k:u["parameters"][k]for k in ("w","l","ng","m")})
  elif m=="npn13g2":emit("Q",name,[t[k]for k in ("C","B","E","S")],"npn13G2",dict(Nx=number(q["Nx"]),we=number(q["we"],"u"),le=number(q["le"],"u"),m=number(q["m"])))
  elif m=="rppd":emit("R",name,[t[k]for k in ("RPPD_1","RPPD_2","RPPD_SUB")],m,{k:number(q[k],"u"if k in("w","l")else"")for k in ("w","l","b","m")})
  elif m=="cap_cmim":emit("C",name,[t[k]for k in ("MIM_TOP","MIM_BTM")],m,{k:number(q[k],"u")for k in ("w","l")})
  elif m=="ptap1":emit("R",name,[t[k]for k in ("TIE","WELL")],m,dict(A=number(q["A"],"p"),P=number(q["P"],"u")))
  else:raise ValueError("unexpected original device")
 need(counts==dict(sg13_lv_nmos=200,npn13G2=124,rppd=98,cap_cmim=7,ptap1=221),"complete independent schematic census")
 lines+=[".ends "+TOP,""];out=NATIVE/"schematic650.cir";out.write_text("\n".join(lines))
 save("reference-provenance.json",dict(original_mapping=fp(ROOT/MAP),original_electrical_plan=fp(ROOT/PLAN),
  source_schematic_correspondence_run=mapping["source_run"],counts=counts,reference=fp(out),
  reference_constructed_from_original_schematic_not_candidate_extraction=True,**FLAGS))
def release():
 ctx=gate();tag="cloud-results-"+str(ctx["run"])+"-1-cdr-mos650-geometry";r=api("releases/tags/"+tag)
 need(r["target_commitish"]==ctx["source"]and r["prerelease"]and not r["draft"]and api("git/ref/tags/"+tag)["object"]["sha"]==ctx["source"],"independent source release")
 return r
def publish():
 ctx=gate();rel=release();need(not rel["assets"],"empty independently reserved release")
 directory=OUT/"publication";directory.mkdir();rows={}
 for p in sorted(OUT.rglob("*")):
  need(not p.is_symlink(),"no output aliases")
  if p.is_file()and directory not in p.parents:rows[str(p.relative_to(OUT))]=fp(p)
 index=directory/"complete-output-index.json";index.write_bytes(enc(dict(context=ctx,files=rows,**FLAGS)))
 archive=directory/"native-mos650-geometry.tar.gz"
 with tarfile.open(archive,"w:gz",compresslevel=1)as tar:
  for n in rows:tar.add(OUT/n,arcname="mos650-geometry/"+n,recursive=False)
 for p in (index,archive):subprocess.run(["gh","release","upload",rel["tag_name"],str(p),"--repo",REPO],check=True,timeout=900)
 expected={p.name:fp(p)for p in(index,archive)};live=release()["assets"];need({a["name"]for a in live}==set(expected),"all native outputs published")
 for a in live:need(a["size"]==expected[a["name"]]["bytes"]and a["digest"]=="sha256:"+expected[a["name"]]["sha256"],"published output digest")
 save("publication.json",dict(release=rel["id"],assets=expected,native_payloads_cloud_only=True,**FLAGS))
def main():
 gate()
 if sys.argv[1:]==["--publish"]:publish();return
 OUT.mkdir();NATIVE.mkdir();DERIVED.mkdir()
 try:
  plan,mapping=controls()
  if sys.argv[1:]==["--controls"]:return
  need(sys.argv[1:]==["--generate"],"explicit generation")
  release();need(shutil.disk_usage(OUT).free>=2*1024**3,"native reserve")
  cfg=read(ROOT/CFG);acquire(cfg);root=pdk(cfg);candidate=geometry(plan,mapping,root);reference(plan,mapping);gate()
  save("result.json",dict(status="GENERATED_EXPLICIT_MODEL_RANGE_MOS650_REQUIRES_FULL_PHYSICAL_AND_FRESH_RC",
   context=gate(),candidate=candidate,native_geometry_executed=True,native_transistor_extraction_executed=False,**FLAGS))
 except BaseException as e:
  save("failure.json",dict(error=repr(e),traceback=traceback.format_exc(),**FLAGS));raise
if __name__=="__main__":main()
