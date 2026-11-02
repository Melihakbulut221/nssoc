"""Exact cloud capsule authentication; no extractall and no local native acquisition."""
import hashlib,json,shutil,subprocess,tarfile
from pathlib import Path,PurePosixPath
REPO="repos/Melihakbulut221/nssoc/"
def need(ok,message):
 if not ok:raise ValueError(message)
def fp(path):
 h=hashlib.sha256();size=0
 with path.open("rb")as f:
  for b in iter(lambda:f.read(4*1024**2),b""):h.update(b);size+=len(b)
 return dict(bytes=size,sha256=h.hexdigest())
def api(path):return json.loads(subprocess.check_output(["gh","api",REPO+path],text=True))
def canonical(name):
 p=PurePosixPath(name)
 need(bool(name)and not p.is_absolute()and p.as_posix()==name and all(x not in ("",".","..")for x in p.parts),"canonical archive path")
 return p
def restore(archive,expected,selected,destination,allow_directories):
 need(set(selected)<=set(expected),"selected subset")
 dirs={p.as_posix()for n in expected for p in canonical(n).parents if p.as_posix()!="."}
 observed={};seen=set();directory_seen=set()
 with tarfile.open(archive,"r|gz")as tar:
  for m in tar:
   name=m.name;path=canonical(name)
   need(name not in seen,"duplicate archive member");seen.add(name)
   if m.isdir():
    need(allow_directories and name in dirs and m.size==0,"unexpected directory");directory_seen.add(name);continue
   need(m.isfile()and not m.issym()and not m.islnk()and name in expected,"unexpected/nonregular archive member")
   need(m.size==expected[name]["bytes"],"archive declared size")
   src=tar.extractfile(m);h=hashlib.sha256();size=0;dest=None
   if name in selected:
    target=destination/path;target.parent.mkdir(parents=True,exist_ok=True)
    need(not target.exists()and not target.is_symlink(),"selected destination collision")
    dest=target.open("xb")
   try:
    for data in iter(lambda:src.read(4*1024**2),b""):
     size+=len(data);h.update(data)
     if dest is not None:dest.write(data)
   finally:
    if dest is not None:dest.close()
   observed[name]=dict(bytes=size,sha256=h.hexdigest());need(observed[name]==expected[name],"archive member bytes")
 need(observed==expected,"complete archive census")
 if allow_directories:need(directory_seen==dirs,"complete directory census")
 for name in selected:need(fp(destination/name)==expected[name],"selected bytes")
 return observed
def acquire(config,index_name,parts_name,selected,work,out,label,engine=False):
 producer=config["producer"]
 run=api("actions/runs/"+str(producer["run"]));rel=api("releases/"+str(producer["release"]))
 need(run["status"]=="completed"and run["conclusion"]=="success"and run["head_sha"]==producer["source"]and run["run_attempt"]==1,"successful exact producer")
 need(rel["target_commitish"]==producer["source"]and rel["tag_name"]==producer["tag"],"producer release")
 tag=api("git/ref/tags/"+producer["tag"])
 need(tag["object"]["type"]=="commit"and tag["object"]["sha"]==producer["source"],"producer tag")
 actual={a["name"]:a for a in rel["assets"]}
 need(len(actual)==len(rel["assets"])and set(actual)==set(config["assets"]),"exact asset census")
 transport=work/(label+"-transport");transport.mkdir()
 for name,pin in config["assets"].items():
  canonical(name);need("/"not in name,"asset basename")
  a=actual[name]
  need(a["id"]==pin["id"]and a["size"]==pin["bytes"]and a.get("digest")=="sha256:"+pin["sha256"],"asset identity")
  target=transport/name
  with target.open("xb")as f:subprocess.run(["gh","api",REPO+"releases/assets/"+str(a["id"]),"-H","Accept: application/octet-stream"],stdout=f,check=True,timeout=900)
  need(fp(target)=={k:pin[k]for k in("bytes","sha256")},"download bytes")
 index=json.loads((transport/index_name).read_bytes());parts=json.loads((transport/parts_name).read_bytes())
 need(index==config["output_index"if engine else"index"]and parts==config["parts"],"exact index and parts")
 need(index["source"]==producer["source"],"index source")
 if not engine:need(index["run"]==producer["run"]and index["attempt"]==1,"index run")
 archive=transport/"authenticated.tar.gz"
 with archive.open("xb")as dest:
  for part in parts["parts"]:
   name=part["name"];need(name in config["assets"],"declared part asset")
   need(fp(transport/name)=={k:part[k]for k in("bytes","sha256")},"part identity")
   with(transport/name).open("rb")as src:shutil.copyfileobj(src,dest,4*1024**2)
 need(fp(archive)==parts["archive"],"complete archive")
 expected=dict(index["files"])
 if engine:
  need(index_name not in expected,"index not self-referential")
  expected[index_name]={k:config["assets"][index_name][k]for k in("bytes","sha256")}
 destination=work/label;destination.mkdir()
 observed=restore(archive,expected,selected,destination,engine)
 pins={n:observed[n]for n in selected}
 (work/(label+"-pins.json")).write_text(json.dumps(pins,sort_keys=True,indent=2)+"\n")
 (out/("bulk-postdrt-"+label+"-acquisition.json")).write_text(json.dumps(dict(
  producer=producer,assets=config["assets"],all_members=observed,selected=pins,
  complete_archive_authenticated=True,native_bytes_remain_in_cloud=True,
  physical_acceptance=False,timing_accepted=False,full_phy_accepted=False),sort_keys=True,indent=2)+"\n")
 shutil.rmtree(transport)
 return pins
