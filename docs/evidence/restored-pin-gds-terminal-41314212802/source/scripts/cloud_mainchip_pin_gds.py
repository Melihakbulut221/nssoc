#!/usr/bin/env python3
"""Cloud-only actual ODB pin/LEF/GDS correspondence. Never modifies layout or accepts a chip."""
import ast,base64,gc,hashlib,importlib.metadata,json,os,re,resource,subprocess,sys,tarfile,traceback,urllib.request
from collections import defaultdict
from fractions import Fraction
from pathlib import Path,PurePosixPath
import klayout.db as k
import zstandard
import cloud_mainchip_connectivity_diagnosis as base
ROOT=Path(__file__).resolve().parents[1]
OUT=ROOT/"pin-gds-evidence"
NATIVE=ROOT/"pin-gds-native"
MANIFEST="scripts/mainchip-pin-gds-pins.json"
PROOF="docs/evidence/restored-pin-metal-diagnosis-41312549409/derived/"
REPO="repos/Melihakbulut221/nssoc/"
FLAGS=dict(physical_acceptance=False,timing_accepted=False,full_phy_accepted=False,layout_modified=False,original_connectivity_gate_modified=False)
METALS=("Metal1","Metal2","Metal3","Metal4","Metal5","TopMetal1","TopMetal2")
ORIENT={"R0":(0,False),"R90":(1,False),"R180":(2,False),"R270":(3,False),
 "MX":(0,True),"MY":(2,True),"MXR90":(1,True),"MYR90":(3,True)}
def enc(v):return (json.dumps(v,sort_keys=True,indent=2,allow_nan=False)+"\n").encode()
def digest(b):return dict(bytes=len(b),sha256=hashlib.sha256(b).hexdigest())
def fp(p):
 with p.open("rb")as f:return dict(bytes=p.stat().st_size,sha256=hashlib.file_digest(f,"sha256").hexdigest())
def save(name,v):
 p=OUT/name;p.parent.mkdir(parents=True,exist_ok=True);p.write_bytes(enc(v))
def api(path,repo=REPO):return json.loads(subprocess.check_output(["gh","api",repo+path]))
def source_gate():
 assert os.environ.get("GITHUB_ACTIONS")=="true"and os.environ["GITHUB_RUN_ATTEMPT"]=="1"
 assert os.environ["GITHUB_REPOSITORY"]=="Melihakbulut221/nssoc"and os.environ["GITHUB_EVENT_NAME"]=="workflow_dispatch"
 assert os.environ["GITHUB_REF"]=="refs/heads/codex/mainchip-pin-gds"
 assert subprocess.check_output(["git","rev-parse","HEAD"],text=True).strip()==os.environ["GITHUB_SHA"]
 assert importlib.metadata.version("klayout")=="0.30.2"and importlib.metadata.version("zstandard")=="0.23.0"
 pins=json.loads((ROOT/MANIFEST).read_bytes())
 for n,p in pins.items():assert fp(ROOT/n)==p,("source",n)
 return pins
def exact_int(v):
 f=Fraction(str(v))
 assert f.denominator==1,"noninteger geometry conversion"
 return f.numerator
def coord(v,dbu):return exact_int(Fraction(v)*dbu)
def box(v):
 assert len(v)==4 and all(type(x)is int for x in v)and v[0]<v[2]and v[1]<v[3]
 return k.Box(*v)
def region_rects(rects):
 r=k.Region()
 for v in rects:r.insert(box(v))
 return r.merged()
def equal(a,b):return (a^b).is_empty()
def transform(orientation,origin):
 assert orientation in ORIENT and len(origin)==2 and all(type(x)is int for x in origin)
 rot,mirror=ORIENT[orientation]
 return k.Trans(rot,mirror,*origin)
def layer_map(text):
 rows={}
 for raw in text.splitlines():
  fields=raw.split("#",1)[0].split()
  if len(fields)==4 and fields[0]in METALS and "NET"in fields[1].split(","):
   name,types,layer,datatype=fields
   assert name not in rows and "LEFPIN"in types.split(",")
   rows[name]=[int(layer),int(datatype)]
 assert set(rows)==set(METALS)and all(v[1]==0 for v in rows.values())
 return rows
def parse_lef(text,dbu,needed):
 result={}
 for m in re.finditer(r"(?m)^\s*MACRO\s+(\S+)\s*$",text):
  name=m.group(1)
  if name not in needed:continue
  end=re.search(r"(?m)^\s*END\s+"+re.escape(name)+r"\s*$",text[m.end():])
  assert end is not None,"unclosed macro"
  body=text[m.end():m.end()+end.start()]
  size=re.search(r"\bSIZE\s+(\S+)\s+BY\s+(\S+)\s*;",body);assert size
  origin=re.search(r"\bORIGIN\s+(\S+)\s+(\S+)\s*;",body)
  origin=[coord(v,dbu)for v in origin.groups()]if origin else[0,0]
  assert origin==[0,0],"nonzero LEF origin requires explicit qualification"
  pins={}
  for p in re.finditer(r"(?m)^\s*PIN\s+(\S+)\s*$",body):
   pname=p.group(1);pend=re.search(r"(?m)^\s*END\s+"+re.escape(pname)+r"\s*$",body[p.end():]);assert pend
   pb=body[p.end():p.end()+pend.start()];layer=None;regions={};geometries=[]
   for stmt in pb.split(";"):
    for match in re.finditer(r"(?m)^\s*(LAYER|RECT|POLYGON|PATH|VIA)\s+([\s\S]+)",stmt):
     kind,values=match.groups();tokens=values.split()
     if kind=="LAYER":
      assert len(tokens)==1 and tokens[0]in METALS,"unsupported LEF layer"
      layer=tokens[0];continue
     assert layer is not None and kind in ["RECT","POLYGON"],"unsupported LEF pin geometry"
     points=[coord(v,dbu)for v in tokens]
     if kind=="RECT":
      assert len(points)==4
      shape=box(points)
     else:
      assert len(points)>=6 and len(points)%2==0
      shape=k.Polygon([k.Point(points[i],points[i+1])for i in range(0,len(points),2)])
     regions.setdefault(layer,k.Region()).insert(shape);geometries.append(dict(kind=kind,layer=layer,coordinates=points))
   assert regions and pname not in pins
   pins[pname]=dict(regions={n:r.merged()for n,r in regions.items()},geometries=geometries)
  assert pins and name not in result
  result[name]=dict(size=[coord(v,dbu)for v in size.groups()],pins=pins,origin=origin)
 return result
def controls():
 base.OUT=OUT;base.controls()
 prior=json.loads((OUT/"controls.json").read_bytes());assert prior["count"]==23
 passed=[]
 points={"R0":(2,3),"R90":(-3,2),"R180":(-2,-3),"R270":(3,-2),"MX":(2,-3),"MY":(-2,3),"MXR90":(3,2),"MYR90":(-3,-2)}
 for name,(x,y)in points.items():
  got=transform(name,[11,17])*k.Point(2,3)
  assert (got.x,got.y)==(x+11,y+17);passed.append("pinned OpenDB origin/orientation "+name)
 outer=region_rects([[0,0,10,10]]);hole=region_rects([[4,4,6,6]])
 assert not (outer-(outer-hole)).is_empty();passed.append("GDS metal hole cannot be hidden by its bounding box")
 assert (region_rects([[1,1,3,3]])-outer).is_empty();passed.append("full polygon containment")
 assert not (region_rects([[9,1,11,3]])-outer).is_empty();passed.append("partially missing GDS metal rejected")
 assert not equal(outer,region_rects([[0,0,9,10]]));passed.append("one database unit pin mismatch detected")
 assert equal(region_rects([[0,0,5,10],[5,0,10,10]]),outer);passed.append("rectangular decomposition compared by exact region")
 sample="MACRO cell\n SIZE 1 BY 2 ;\n PIN A\n PORT\n LAYER Metal1 ;\n RECT 0 0 0.5 1 ;\n POLYGON 0.5 0 1 0 1 1 0.5 1 ;\n END\n END A\nEND cell\n"
 parsed=parse_lef(sample,1000,{"cell"})
 assert parsed["cell"]["size"]==[1000,2000]and equal(parsed["cell"]["pins"]["A"]["regions"]["Metal1"],region_rects([[0,0,1000,1000]]))
 passed.append("LEF RECT and POLYGON exact decimal conversion")
 for label,action in [
  ("fractional database unit",lambda:coord("0.0005",1000)),
  ("unknown orientation",lambda:transform("guess",[0,0])),
  ("boolean origin",lambda:transform("R0",[True,0])),
  ("unsupported LEF PATH",lambda:parse_lef(sample.replace("RECT 0 0 0.5 1","PATH 0 0 0.5 1"),1000,{"cell"})),
  ("nonzero LEF origin",lambda:parse_lef(sample.replace(" SIZE"," ORIGIN 0.1 0 ;\n SIZE"),1000,{"cell"}))]:
  try:action()
  except (AssertionError,ValueError):passed.append("reject "+label)
  else:raise AssertionError(label)
 mapping="\n".join(n+" NET,SPNET,PIN,LEFPIN,VIA "+str(i+1)+" 0"for i,n in enumerate(METALS))
 assert len(layer_map(mapping))==7;passed.append("drawing map is parsed from actual pinned PDK text")
 try:layer_map(mapping.replace(" 0"," 2",1))
 except AssertionError:passed.append("pin marker layer cannot replace drawing metal")
 else:raise AssertionError("accepted pin-purpose metal")
 try:layer_map(mapping+"\nMetal1 NET,LEFPIN 8 0")
 except AssertionError:passed.append("duplicate drawing map refused")
 else:raise AssertionError("accepted duplicate layer")
 assert len(passed)==22,len(passed)
 save("gds-controls.json",dict(count=45,inherited_count=23,added_count=22,passed=passed,original=prior,**FLAGS))
def download(asset,target,repo=REPO):
 target.parent.mkdir(parents=True,exist_ok=True)
 with target.open("xb")as f:
  subprocess.run(["gh","api",repo+"releases/assets/"+str(asset["id"]),"-H","Accept: application/octet-stream"],stdout=f,check=True,timeout=900)
 return fp(target)
def acquire_snapshot():
 cfg=json.loads((ROOT/"scripts/mainchip-connectivity-diagnosis-inputs.json").read_bytes())
 r=api("releases/430583367");run=api("actions/runs/41308526628")
 assert run["status"]=="completed"and run["conclusion"]=="failure"and run["head_sha"]==base.SOURCE and run["run_attempt"]==1
 assert r["target_commitish"]==base.SOURCE and api("git/ref/tags/"+r["tag_name"])["object"]["sha"]==base.SOURCE
 assets={a["name"]:a for a in r["assets"]};assert set(assets)==set(cfg["assets"])
 for name,p in cfg["assets"].items():
  a=assets[name];assert a["id"]==p["id"]and a["size"]==p["bytes"]and a["digest"]=="sha256:"+p["sha256"]
  if name in ["candidate-outputs.json","candidate-native.tar.gz.part000"]:
   assert download(a,NATIVE/name)=={k:p[k]for k in ["bytes","sha256"]}
 idx=json.loads((NATIVE/"candidate-outputs.json").read_bytes())
 assert idx["source"]==base.SOURCE and int(idx["run"])==41308526628 and int(idx["attempt"])==1
 wanted="bulk-postdrt-antenna/restored-snapshot.json";seen={};names=set();target=NATIVE/"restored-snapshot.json"
 with tarfile.open(NATIVE/"candidate-native.tar.gz.part000","r|gz")as tf:
  for m in tf:
   path=PurePosixPath(m.name);assert not path.is_absolute()and ".."not in path.parts and m.name not in names
   names.add(m.name)
   if m.isdir():continue
   assert m.isfile()and m.name in idx["files"],m.name
   assert m.size==idx["files"][m.name]["bytes"]
   sink=target.open("xb")if m.name==wanted else None
   h=hashlib.sha256();size=0
   try:
    with tf.extractfile(m)as f:
     for b in iter(lambda:f.read(1048576),b""):
      size+=len(b);h.update(b)
      if sink:sink.write(b)
   finally:
    if sink:sink.close()
   pin=dict(bytes=size,sha256=h.hexdigest());assert pin==idx["files"][m.name],m.name;seen[m.name]=pin
 assert set(seen)==set(idx["files"])and fp(target)==dict(bytes=627640193,sha256="7d9512e51de23b4cc927752bf56d969e78b59f5e78f902c6544ece93b7e9a2a5")
 save("native-authentication.json",dict(run=run,release=r,all_members=seen,selected=wanted,native_payloads_cloud_only=True))
 return target
def acquire_pdk():
 s=(ROOT/"scripts/prepare_mainchip_postroute_pdk.py").read_text();tree=ast.parse(s);values={}
 for n in tree.body:
  if isinstance(n,ast.Assign)and len(n.targets)==1 and isinstance(n.targets[0],ast.Name)and n.targets[0].id in ["REV","ARCHIVES"]:values[n.targets[0].id]=ast.literal_eval(n.value)
 assert values["REV"]=="c4b8b4e5e7a05f375cca3815d51b3a37721fbf5c"and len(values["ARCHIVES"])==5
 repo="repos/fossi-foundation/ciel-releases/";tag="ihp-sg13g2-"+values["REV"];r=api("releases/tags/"+tag,repo)
 assets={a["name"]:a for a in r["assets"]};records={};selected={}
 for name,(size,h)in values["ARCHIVES"].items():
  a=assets[name];assert a["size"]==size
  path=NATIVE/name;assert download(a,path,repo)==dict(bytes=size,sha256=h)
  members={};names=set()
  with zstandard.open(path,"rb")as stream,tarfile.open(fileobj=stream,mode="r|")as tf:
   for m in tf:
    rel=PurePosixPath(m.name);assert not rel.is_absolute()and ".."not in rel.parts and m.name not in names
    names.add(m.name)
    if m.isdir():continue
    assert m.isfile()and rel.parts[0]=="ihp-sg13g2",(name,m.name)
    take=m.name.endswith((".gds",".lef"))or m.name.endswith("/klayout/tech/sg13g2.map")
    dst=NATIVE/"pdk"/rel if take else None
    if dst:dst.parent.mkdir(parents=True,exist_ok=True);assert not dst.exists()
    sink=dst.open("xb")if dst else None;dig=hashlib.sha256();n=0
    try:
     with tf.extractfile(m)as f:
      for b in iter(lambda:f.read(1048576),b""):
       dig.update(b);n+=len(b)
       if sink:sink.write(b)
    finally:
     if sink:sink.close()
    members[m.name]=dict(bytes=n,sha256=dig.hexdigest())
    if take:selected[m.name]=dict(archive=name,**members[m.name])
  records[name]=dict(asset=a,archive=dict(bytes=size,sha256=h),members=members)
  path.unlink()
 save("pdk-authentication.json",dict(revision=values["REV"],release=r,archives=records,selected=selected))
 return selected
def analyze():
 NATIVE.mkdir(exist_ok=False)
 snapshot_path=acquire_snapshot();pdk=acquire_pdk()
 for key in ["GH_TOKEN","GITHUB_TOKEN"]:os.environ.pop(key,None)
 rows=json.loads((ROOT/(PROOF+"pin-metal-observation.json")).read_bytes())
 producer=json.loads((ROOT/(PROOF+"result.json")).read_bytes())
 assert len(rows)==producer["failed_nets"]==142 and producer["all_failed_original_graphs_replayed"]
 assert all(r["modes"]["positive_area"]["appended_pin_rectangles"]==r["modes"]["closed_boundary"]["appended_pin_rectangles"]for r in rows)
 with snapshot_path.open()as f:snapshot=json.load(f)
 assert len(snapshot["instances"])==154480 and len(snapshot["masters"])==58 and len(snapshot["protected"])==1691
 dbu=snapshot["block"]["dbu"];assert type(dbu)is int and dbu==snapshot["block"]["tech_dbu"]
 wanted={g["pin"][1]for r in rows for g in r["modes"]["positive_area"]["appended_pin_rectangles"]}
 instances={n:snapshot["instances"][n]for n in sorted(wanted)};masters=snapshot["masters"];block=snapshot["block"]
 del snapshot;gc.collect()
 save("actual-snapshot-projection.json",dict(source=fp(snapshot_path),instances=instances,masters=masters,block=block))
 needed={i["master"][1]for i in instances.values()}
 maps=[n for n in pdk if n.endswith("/klayout/tech/sg13g2.map")];assert len(maps)==1,maps
 mapping=layer_map((NATIVE/"pdk"/maps[0]).read_text())
 save("actual-layer-map.json",dict(path=maps[0],pin=pdk[maps[0]],metals=mapping))
 lefs=defaultdict(list);gds=defaultdict(list)
 for name in sorted(pdk):
  path=NATIVE/"pdk"/name
  if name.endswith(".lef"):
   for cell,data in parse_lef(path.read_text(),dbu,needed).items():lefs[cell].append((name,data))
  elif name.endswith(".gds"):
   layout=k.Layout();layout.read(str(path));scale=exact_int(Fraction(str(layout.dbu))*dbu)
   assert scale>0,"no geometry rounding"
   for cellname in needed:
    cell=layout.cell(cellname)
    if cell is not None:gds[cellname].append((name,layout,cell,scale))
 cache={};observed=[];missing=[]
 for row in rows:
  groups=defaultdict(list)
  for g in row["modes"]["positive_area"]["appended_pin_rectangles"]:groups[tuple(g["pin"])].append(g)
  for identity,geoms in sorted(groups.items()):
   _,iname,pname=identity;inst=instances[iname];lib,cellname=inst["master"];master=masters[lib+"/"+cellname]
   assert pname in master["pins"]and inst["pins"][pname]["net"]==row["net"]
   key=(lib,cellname,pname)
   if key not in cache:
    expected=defaultdict(list)
    for group in master["pins"][pname]["boxes"]:
     for name,x0,y0,x1,y1 in group:expected[name].append([x0,y0,x1,y1])
    native={n:region_rects(v)for n,v in expected.items()};checks=[]
    for filename,lef in lefs[cellname]:
     p=lef["pins"].get(pname)
     same=p is not None and lef["size"]==[master["width"],master["height"]]and set(p["regions"])==set(native)and all(equal(p["regions"][n],v)for n,v in native.items())
     checks.append(dict(kind="LEF",file=filename,passed=same))
    for filename,layout,cell,scale in gds[cellname]:
     for name,v in native.items():
      region=k.Region(cell.begin_shapes_rec(layout.layer(*mapping[name]))).transformed(k.ICplxTrans(scale,0,False,0,0)).merged()
      uncovered=v-region
      checks.append(dict(kind="GDS",file=filename,layer=name,passed=uncovered.is_empty(),uncovered_area_dbu2=uncovered.area(),uncovered_polygons=[str(p)for p in uncovered.each()]))
    cache[key]=dict(master=[lib,cellname],pin=pname,native_boxes=dict(expected),checks=checks,
      lef_candidates=len(lefs[cellname]),gds_candidates=len(gds[cellname]),
      passed=bool(lefs[cellname])and bool(gds[cellname])and all(x["passed"]for x in checks))
   rec=cache[key];t=transform(inst["orientation"],inst["origin"])
   actual=defaultdict(list)
   for g in geoms:actual[g["layer"]].append(g["box"])
   transformed={n:region_rects(v).transformed(t)for n,v in rec["native_boxes"].items()}
   same=set(actual)==set(transformed)and all(equal(region_rects(actual[n]),v)for n,v in transformed.items())
   good=rec["passed"]and same
   proof=dict(net=row["net"],pin=list(identity),master=[lib,cellname],orientation=inst["orientation"],origin=inst["origin"],
    exact_master_to_observed_pin_transform=same,master_pin_gds_lef_passed=rec["passed"],passed=good,observed_rectangles=geoms)
   observed.append(proof)
   if not good:missing.append(proof)
 save("master-pin-correspondence.json",list(cache.values()));save("placed-pin-correspondence.json",observed)
 save("unresolved.json",missing)
 result=dict(status="PASS_OBSERVED_PIN_METAL_GDS_LEF_TRANSFORMS_NOT_CHIP_ACCEPTANCE"if not missing else"UNRESOLVED_PIN_METAL_GDS_LEF_CORRESPONDENCE",
  context=dict(source=os.environ["GITHUB_SHA"],run=int(os.environ["GITHUB_RUN_ID"])),original_failed_nets=142,observed_pin_count=len(observed),
  unique_master_pins=len(cache),missing_or_mismatched_pins=len(missing),all_observed_pin_rectangles_verified=not missing,
  odb_dbu_per_micron=dbu,original_wire_only_gate_remains_failed=True,full_lvs_executed=False,full_drc_executed=False,
  full_chip_gds_emitted=False,peak_rss_kib=resource.getrusage(resource.RUSAGE_SELF).ru_maxrss,**FLAGS)
 save("result.json",result)
 assert not missing,"Actual observed pin geometry requires further qualification; inspect complete unresolved report"
def main():
 before=source_gate();OUT.mkdir(exist_ok=False)
 assert sys.argv[1:]in [["controls"],["analyze"]]
 controls()if sys.argv[1]=="controls"else analyze()
 assert source_gate()==before
if __name__=="__main__":
 try:main()
 except BaseException:
  OUT.mkdir(exist_ok=True);save("failure.json",dict(traceback=traceback.format_exc(),**FLAGS));raise
