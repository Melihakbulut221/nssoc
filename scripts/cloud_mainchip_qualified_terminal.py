"""Authenticate the completed native capsule and expose physical gates on GitHub.
No CAD, geometry edits, new timing, or acceptance is performed by this reader.
"""
import hashlib,json,os,subprocess,tarfile,traceback
from pathlib import Path,PurePosixPath
ROOT=Path(__file__).resolve().parents[1]
OUT=ROOT/"qualified-native-terminal"
RUN=41317927121;SOURCE="340fb4f217e920c1bc4d5fa552e4b11eb81d0a4b";RELEASE=430648315
REPO="repos/Melihakbulut221/nssoc/"
FLAGS=dict(physical_acceptance=False,timing_accepted=False,full_phy_accepted=False)
def api(path):return json.loads(subprocess.check_output(["gh","api",REPO+path],timeout=120))
def fp(p):
 with p.open("rb")as f:return dict(bytes=p.stat().st_size,sha256=hashlib.file_digest(f,"sha256").hexdigest())
def save(name,v):
 p=OUT/name;p.parent.mkdir(parents=True,exist_ok=True)
 p.write_text(json.dumps(v,sort_keys=True,indent=2,allow_nan=False)+"\n")
def selected(n):
 fixed={"bulk-postdrt-scoped-inner-result.json","bulk-postdrt-antenna/result.json",
  "bulk-postdrt-antenna/connectivity-summary.json","bulk-postdrt-antenna/qualified-pin-conductor-binding.json",
  "bulk-postdrt-antenna/scoped-candidate-pg-audit.json","bulk-postdrt-antenna/original-clock-gate/result.json",
  "bulk-postdrt-antenna/route-delta.json","bulk-postdrt-antenna/new-diode-direct-pg-contacts.json",
  "work/bulk-postdrt-antenna/final-counts.json","work/bulk-postdrt-antenna/final-drc.rpt",
  "work/bulk-postdrt-antenna/final-drc-reread.rpt"}
 fixed.update("bulk-postdrt-antenna/"+name for name in ("final-antenna-summary.json","final-antenna-violations.json","final-audit-terminal.json","final-drc-markers.json","final-drc.json"))
 return n in fixed
def outline(value,depth=0):
 if isinstance(value,dict):return {k:outline(v,depth+1)for k,v in value.items()}
 if isinstance(value,list):return dict(type="list",count=len(value),examples=[outline(x,depth+1)for x in value[:3]]if depth<3 else [])
 return value
def main():
 assert os.environ.get("GITHUB_ACTIONS")=="true"and os.environ["GITHUB_RUN_ATTEMPT"]=="1"
 assert os.environ["GITHUB_REPOSITORY"]=="Melihakbulut221/nssoc"and os.environ["GITHUB_EVENT_NAME"]=="workflow_dispatch"
 assert os.environ["GITHUB_REF"]=="refs/heads/codex/mainchip-qualified-terminal"
 assert subprocess.check_output(["git","rev-parse","HEAD"],text=True).strip()==os.environ["GITHUB_SHA"]
 pins=json.loads((ROOT/"scripts/mainchip-qualified-terminal-pins.json").read_bytes())
 for name,pin in pins.items():assert fp(ROOT/name)==pin,("source",name)
 assert selected("bulk-postdrt-antenna/final-antenna-violations.json")
 assert selected("bulk-postdrt-antenna/final-drc-markers.json")
 assert not selected("bulk-postdrt-antenna/final-antenna-nets.json")
 assert not selected("bulk-postdrt-antenna/final-unexpected.json")
 OUT.mkdir(exist_ok=False)
 inputs=json.loads((ROOT/"scripts/mainchip-qualified-terminal-inputs.json").read_bytes())
 run=api("actions/runs/"+str(RUN));assert run["head_sha"]==SOURCE and run["status"]=="completed"and run["conclusion"]=="failure"and run["run_attempt"]==1
 release=api("releases/"+str(RELEASE));assert release["target_commitish"]==SOURCE
 tag=api("git/ref/tags/"+release["tag_name"]);assert tag["object"]["type"]=="commit"and tag["object"]["sha"]==SOURCE
 assets={a["name"]:a for a in release["assets"]};assert set(assets)==set(inputs["assets"])
 work=Path(os.environ["RUNNER_TEMP"])/("qualified-terminal-"+os.environ["GITHUB_RUN_ID"]);work.mkdir(exist_ok=False)
 for name,pin in inputs["assets"].items():
  a=assets[name];assert a["id"]==pin["id"]and a["size"]==pin["bytes"]and a["digest"]=="sha256:"+pin["sha256"]
  with(work/name).open("xb")as f:subprocess.run(["gh","api",REPO+"releases/assets/"+str(a["id"]),"-H","Accept: application/octet-stream"],stdout=f,check=True,timeout=900)
  assert fp(work/name)=={k:pin[k]for k in ("bytes","sha256")}
 parts=json.loads((work/"candidate-parts.json").read_bytes());index=json.loads((work/"candidate-outputs.json").read_bytes())
 assert index["source"]==SOURCE and int(index["run"])==RUN and int(index["attempt"])==1
 archive=work/"assembled.tar.gz"
 with archive.open("xb")as sink:
  for part in parts["parts"]:
   assert fp(work/part["name"])=={k:part[k]for k in ("bytes","sha256")}
   with(work/part["name"]).open("rb")as f:
    for b in iter(lambda:f.read(1048576),b""):sink.write(b)
 assert fp(archive)==parts["archive"]
 seen={};names=set();kept={}
 with tarfile.open(archive,mode="r|gz")as tar:
  for member in tar:
   n=member.name;p=PurePosixPath(n)
   assert str(p)==n and not p.is_absolute()and ".."not in p.parts and n not in names
   names.add(n)
   if member.isdir():continue
   assert member.isfile()and n in index["files"]
   keep=selected(n);h=hashlib.sha256();size=0
   dest=OUT/"native"/n
   if keep:assert member.size<16000000;dest.parent.mkdir(parents=True,exist_ok=True)
   sink=dest.open("xb")if keep else None
   try:
    with tar.extractfile(member)as f:
     for b in iter(lambda:f.read(1048576),b""):
      h.update(b);size+=len(b)
      if sink:sink.write(b)
   finally:
    if sink:sink.close()
   pin=dict(bytes=size,sha256=h.hexdigest());assert pin==index["files"][n]
   seen[n]=pin
   if keep:kept[n]=pin
 assert set(seen)==set(index["files"])
 def read(n):return json.loads((OUT/"native"/n).read_bytes())
 inner=read("bulk-postdrt-scoped-inner-result.json");physical=read("bulk-postdrt-antenna/result.json")
 binding=read("bulk-postdrt-antenna/qualified-pin-conductor-binding.json");pg=read("bulk-postdrt-antenna/scoped-candidate-pg-audit.json")
 clock=read("bulk-postdrt-antenna/original-clock-gate/result.json")
 assert inner["status"]=="COMPLETE_SCOPED_CLASS_RESTORATION_AND_QUALIFIED_PHYSICAL_AUDITS"
 assert inner["restoration_and_qualified_physical_audits_completed"]is True and inner["terminal_errors"]==[]
 assert len(inner["phases"])==6 and all(r["status"]=="complete"for r in inner["phases"])
 assert all(inner[k]==0 for k in ("current_route_calls","current_repair_calls","current_reconstruction_calls"))
 assert inner["qualified_physical_result"]==physical
 assert binding["status"]=="COMPLETE"and binding["native_adapter_executed"]is True
 assert binding["connectivity"]["changed_nets"]==828 and binding["connectivity"]["both_modes_complete"]is True
 assert pg["complete"]is True and pg["contacts"]==2702
 assert clock["all_source_clock_and_fixed_records_preserved"]is True and clock["clock_or_fixed_nets"]==1691
 assert all(physical[k]is False for k in FLAGS)
 save("physical-result-outline.json",outline(physical))
 save("native-inner-outline.json",{k:v for k,v in inner.items()if k in ("status","error","terminal_errors","bounded_cycle_qualified","candidate","elapsed_seconds","original_wire_only_acceptance","restoration_and_qualified_physical_audits_completed","phases")})
 save("authentication.json",dict(run=run,release=release,tag=tag,archive=parts["archive"],all_native_members_authenticated=seen,selected=kept,native_payloads_cloud_only=True))
 save("result.json",dict(status="PASS_AUTHENTICATED_COMPLETED_NATIVE_AUDITS_NOT_PHYSICAL_ACCEPTANCE",producer_run=RUN,producer_source=SOURCE,producer_release=RELEASE,
  source=os.environ["GITHUB_SHA"],run=int(os.environ["GITHUB_RUN_ID"]),members=len(seen),selected=len(kept),
  connectivity=binding["connectivity"],power_contacts=pg["contacts"],protected_nets=clock["clock_or_fixed_nets"],
  bounded_cycle_qualified=physical["bounded_cycle_qualified"],native_simulation=False,**FLAGS))
 for name,pin in pins.items():assert fp(ROOT/name)==pin
if __name__=="__main__":
 try:main()
 except BaseException:
  OUT.mkdir(exist_ok=True);save("failure.json",dict(traceback=traceback.format_exc(),**FLAGS));raise
