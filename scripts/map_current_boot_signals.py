# SPDX-License-Identifier: Apache-2.0
"""Map measured critical endpoints into exact source-bound synthesized signals."""
import os,subprocess,json,hashlib,zipfile,tarfile
from pathlib import Path
assert os.environ.get("GITHUB_ACTIONS")=="true"
P="repos/Melihakbulut221/nssoc/"
def api(s):return json.loads(subprocess.check_output(["gh","api",P+s]))
def sha(p):
 with Path(p).open("rb") as f:return hashlib.file_digest(f,"sha256").hexdigest()
run=api("actions/runs/43680923081")
assert run["status"]=="completed" and run["conclusion"]=="success" and run["head_sha"]=="b2e5e00493c2770f69f2ef37ac07d7010c9a8a74"
meta=api("actions/artifacts/14149016224")
expected="c1ea5a1f15feed9ca77c2b7073c3f63e901eb7844369902e1c5cbfdc89ce02fc"
assert meta["digest"]=="sha256:"+expected and meta["workflow_run"]["id"]==run["id"] and not meta["expired"]
with open("native.zip","xb") as f:subprocess.run(["gh","api",P+"actions/artifacts/14149016224/zip"],stdout=f,check=True)
assert sha("native.zip")==expected
z=zipfile.ZipFile("native.zip");assert z.namelist()==["build.tgz"]
with z.open("build.tgz")as f,tarfile.open(fileobj=f,mode="r|gz")as tar:
 found=[]
 for member in tar:
  if member.isfile() and member.name.endswith(".json"):
   raw=tar.extractfile(member).read()
   if hashlib.sha256(raw).hexdigest()=="6cbaa20bd3b0e911dcf66c4160a2130f18c1e0293ec57864d65341e052ca8eda":
    found.append((member.name,json.loads(raw)))
assert len(found)==1
name,model=found[0];assert "soc_top" in model["modules"]
mod=model["modules"]["soc_top"]
ids=[343483,343481,343480,160216,341914,180414,160343,365785,160518,164050,365787,310784,310786,160646,164200,164590]
cells={}
for i in ids:
 n="$auto$ff.cc:337:slice$"+str(i);assert n in mod["cells"]
 c=mod["cells"][n];bits={b for bs in c["connections"].values()for b in bs if isinstance(b,int)}
 signals={}
 for nn,v in mod["netnames"].items():
  hits=[dict(index=j,bit=b)for j,b in enumerate(v["bits"])if b in bits]
  if hits:signals[nn]=dict(bits=hits,attributes=v.get("attributes",{}))
 cells[n]=dict(cell=c,signals=signals)
out=Path("boot-signal-map");out.mkdir()
r=dict(source_run=run["id"],source_head=run["head_sha"],diagnostic_head=os.environ["GITHUB_SHA"],native_artifact=14149016224,native_sha256=expected,mapped_member=name,mapped_sha256="6cbaa20bd3b0e911dcf66c4160a2130f18c1e0293ec57864d65341e052ca8eda",targets=cells,accepted=False,scope="Source mapping only; postCTS timing counts from exact separate report remain authoritative, not new timing or equivalence acceptance.")
import re
patterns=re.compile(r"(?:pc(?:_q|_d|_id|_if|_set|_mux|$)|instr_(?:req|gnt|rvalid|rdata|err|addr)|data_(?:req|gnt|rvalid|rdata|err|addr)|fetch_enable|exc_cause|mcause|mepc|mtvec)")
core={n:v for n,v in mod["netnames"].items() if "pcie" not in n.lower() and patterns.search(n)}
assert core
r["core_signals"]=core
r["top_ports"]=mod["ports"]
(out/"result.json").write_text(json.dumps(r,indent=2)+"\n")
