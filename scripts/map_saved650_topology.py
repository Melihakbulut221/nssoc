# SPDX-License-Identifier: Apache-2.0
"""Diagnose saved full-load wave, never rerun or relax its acceptance gates."""
import os,json,subprocess,hashlib,zipfile,stat
from pathlib import Path
import numpy as np
from cdr_mos650_full650_loaded import read_streamed_wave,START,UI,STOP,STEP
assert os.environ.get("GITHUB_ACTIONS")=="true"
OUT=Path("saved650-diagnosis");OUT.mkdir()
def api(path):
 return json.loads(subprocess.check_output(["gh","api","repos/Melihakbulut221/nssoc/"+path]))
def sha(p):
 with Path(p).open("rb") as f:return hashlib.file_digest(f,"sha256").hexdigest()
run=api("actions/runs/43682293907")
assert run["status"]=="completed" and run["conclusion"]=="failure" and run["head_sha"]=="cf0a6547b53e7dd3b5961bd92bfcd74347cde78f" and run["run_attempt"]==1
def fetch(i,h,name):
 meta=api("actions/artifacts/"+str(i))
 assert meta["workflow_run"]["id"]==run["id"] and meta["digest"]=="sha256:"+h and not meta["expired"]
 p=Path(name)
 with p.open("xb") as f:subprocess.run(["gh","api","repos/Melihakbulut221/nssoc/actions/artifacts/"+str(i)+"/zip"],stdout=f,check=True)
 assert sha(p)==h
 z=zipfile.ZipFile(p);assert len(z.namelist())==len(set(z.namelist()))
 for info in z.infolist():
  n=Path(info.filename);assert not n.is_absolute() and ".." not in n.parts and not stat.S_ISLNK(info.external_attr>>16)
 return z
safe=fetch(14151372439,"e4f73f8e9cfa6544455ddb87c479e91300962c6785ec34515efc615e2cfeddab","safe.zip")
m=json.loads(safe.read("loaded-n1-nominal_late.json"))
assert m["source_head"]==run["head_sha"] and m["sources_unchanged"] and m["returncode"]==0 and not m["accepted"]
native=fetch(14151930537,"1df16dedf119d2511bb1bbddf0881cc258db82bb9251f6015b61ec08c43b1423","native.zip")

meta=json.loads(safe.read("composition-n1.json"))["contract"]
matches=[i for i in native.infolist() if i.file_size==meta["bytes"] and not i.is_dir()]
contracts=[]
for i in matches:
 raw=native.read(i)
 if hashlib.sha256(raw).hexdigest()==meta["sha256"]:contracts.append((i.filename,json.loads(raw)))
assert len(contracts)==1
name,c=contracts[0]
devices=c["devices"];assert len(devices)==650
byid={d["native_id"]:d for d in devices};assert len(byid)==650
bad=[211,212]
nets={v for i in bad for v in byid[i]["logical_terminals"].values()}
neighbors=[d for d in devices if set(d["logical_terminals"].values()) & (nets-{"avss","avdd","sub"})]
out=dict(source_run=run["id"],source_head=run["head_sha"],diagnostic_head=os.environ["GITHUB_SHA"],contract_member=name,contract_sha256=meta["sha256"],unsafe_device_source_mapping=[byid[i] for i in bad],unsafe_neighbors=neighbors,devices=devices,accepted=False,full_phy_accepted=False,scope="Authenticated source-to-physical parameter and topology map for electrical redesign. No circuit changes or acceptance.")
(OUT/"result.json").write_text(json.dumps(out,indent=2)+"\n")
print(json.dumps(dict(unsafe_source_names=[d["original_source"] for d in out["unsafe_device_source_mapping"]])))
