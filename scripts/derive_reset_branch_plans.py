# SPDX-License-Identifier: Apache-2.0
import os,subprocess,json,hashlib,zipfile,re,collections
from pathlib import Path
assert os.environ.get("GITHUB_ACTIONS")=="true"
P="repos/Melihakbulut221/nssoc/"
def api(s):return json.loads(subprocess.check_output(["gh","api",P+s]))
run=api("actions/runs/43688957642")
assert run["status"]=="completed" and run["conclusion"]=="success" and run["head_sha"]=="14db852f55f5a10b6a1de9c46267a9c3d6a07ce0"
h="b7eb5e15f8c7a68f70628197517297a92e0c2f241cd9bf896c56a98d5be1cc1b"
meta=api("actions/artifacts/14151584150");assert meta["digest"]=="sha256:"+h and meta["workflow_run"]["id"]==run["id"] and not meta["expired"]
with open("reports.zip","xb")as f:subprocess.run(["gh","api",P+"actions/artifacts/14151584150/zip"],stdout=f,check=True)
with open("reports.zip","rb")as f:assert hashlib.file_digest(f,"sha256").hexdigest()==h
z=zipfile.ZipFile("reports.zip");r=json.loads(z.read("result.json"));assert r["sources_unchanged"] and r["returncode"]==0
n="run/5-nssoc-corrpreonebranchafterslow/max.rpt";raw=z.read(n);assert hashlib.sha256(raw).hexdigest()==r["outputs"][n]
rows={};groups=collections.Counter();starts=collections.Counter()
for part in raw.decode().split("Startpoint: ")[1:]:
 m=re.search(r"([-+]?\d+\.\d+)\s+slack \(",part)
 if not m or float(m[1])>=0:continue
 start=part.splitlines()[0];groups[re.search(r"Path Group: (.+)",part)[1]]+=1;starts[start]+=1
 if start not in ["$auto$ff.cc:337:slice$343483","$auto$ff.cc:337:slice$343481"]:continue
 lines=part.split("data arrival time")[0].splitlines();idx=next(i for i,s in enumerate(lines)if start+"/Q "in s)
 pins=re.findall(r"[\^v]\s+(\S+) \((sg13g2_\S+)\)","\n".join(lines[idx:]));chain=[]
 for pin,cell in pins[1:]:
  if re.fullmatch("sg13g2_buf_(1|2|4|8|16)",cell):
   if pin.endswith("/A"):chain.append(pin.rsplit("/",1)[0])
   continue
  key=(pins[0][0],pins[0][1],pin,cell,tuple(chain));rows[key]=rows.get(key,0)+1;break
plans=[dict(source=k[0],source_master=k[1],sink=k[2],sink_master=k[3],chain=k[4],reported_path_count=v)for k,v in rows.items()]
assert sum(p["reported_path_count"]for p in plans)==755
out=Path("reset-branch-plans");out.mkdir()
d=dict(source_run=run["id"],source_head=run["head_sha"],diagnostic_head=os.environ["GITHUB_SHA"],source_odb_sha256=r["candidate_odb_sha256"],artifact=14151584150,artifact_sha256=h,report_member=n,report_sha256=r["outputs"][n],plans=plans,reported_groups=dict(groups),reported_starts=dict(starts),accepted=False,scope="Report-derived identity-only branch candidates. Must revalidate actual DB topology before modification; report count capped1000/group, not total STA endpoints.")
(out/"result.json").write_text(json.dumps(d,indent=2)+"\n")
