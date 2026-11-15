import os,json,subprocess,hashlib,zipfile,tarfile
from pathlib import Path,PurePosixPath
ROOT=Path(__file__).resolve().parents[1];OUT=ROOT/"out";OUT.mkdir(exist_ok=True)
REPO="repos/Melihakbulut221/nssoc/"
def api(s):return json.loads(subprocess.check_output(["gh","api",REPO+s]))
def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
run=api("actions/runs/43696515079")
assert run["head_sha"]=="56f97b8744d2dcd92821a79a7dd63168aacefa9c" and run["conclusion"]=="failure" and run["run_attempt"]==1
def archive(i,digest,name):
 meta=api("actions/artifacts/"+str(i));assert meta["workflow_run"]["id"]==run["id"]and meta["digest"]=="sha256:"+digest and not meta["expired"]
 p=OUT/name
 with p.open("xb")as f:subprocess.run(["gh","api",REPO+"actions/artifacts/"+str(i)+"/zip"],stdout=f,check=True)
 assert sha(p)==digest
 return zipfile.ZipFile(p)
z=archive(14155771240,"579b44b07e51c09207bc7c6d3f1e5182502737d91d8eabc0f06307a6d586aa4b","original-native.zip")
assert z.namelist()==["build.tgz"]
p=OUT/"original-build.tgz";p.write_bytes(z.read("build.tgz"))
root="hw/soc/out/corrpre-pcie-mbist-native-boot"
original={}
with tarfile.open(p,"r:gz")as tar:
 for m in tar:
  path=PurePosixPath(m.name);assert not path.is_absolute() and ".."not in path.parts
  assert m.name==root or m.name.startswith(root+"/")
  assert m.isfile()or m.isdir()
  if m.isfile():
   target=ROOT/m.name;assert not target.exists();target.parent.mkdir(parents=True,exist_ok=True)
   target.write_bytes(tar.extractfile(m).read());original[m.name]=sha(target)
z=archive(14155776313,"0d949776b606699a6c01caac8d588a33bdff8ced1c513271b54dbbf29d31247e","original-gates.zip")
assert set(z.namelist())=={"rx-qualification-gate.json","ack-prefix-qualification-gate.json"}
for n in z.namelist():(OUT/n).write_bytes(z.read(n))
subprocess.run(["python3","scripts/check_predecode_mainchip_mapping.py",root],check=True)
assert all(sha(ROOT/n)==v for n,v in original.items()),"Original synthesis/boot artifacts changed"
result=json.loads((OUT/"mapping.json").read_text())
result["synthesis_producer"]={"run":43696515079,"source":run["head_sha"],"native_artifact":14155771240,"native_sha256":"579b44b07e51c09207bc7c6d3f1e5182502737d91d8eabc0f06307a6d586aa4b","original_conclusion":"failure","reason":"old-source assertion in post-synthesis checker","new_synthesis_performed":False}
result["original_native_outputs"]=original
(OUT/"mapping.json").write_text(json.dumps(result,indent=2)+"\n")
print(json.dumps({k:result[k]for k in ["status","cells","macros","accepted","synthesis_producer"]},indent=2))
