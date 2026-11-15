import os,json,re,subprocess,hashlib,traceback
from pathlib import Path
import numpy as np
import cloud_pll_rhi120_c8_initial as original
ROOT=Path(__file__).resolve().parents[1];OUT=ROOT/"pll-current-prefix4ns";OUT.mkdir()
r=dict(source=os.environ["GITHUB_SHA"],status="RUNNING",transient_run=False,acquisition_accepted=False,full_phy_accepted=False,complete_terminal_currents_qualified=False)
def save():(OUT/"result.json").write_text(json.dumps(r,indent=2)+"\n")
def run(label,args,seconds=600):
 p=subprocess.run(args,stdout=subprocess.PIPE,stderr=subprocess.STDOUT,timeout=seconds)
 (OUT/(label+".log")).write_bytes(p.stdout)
 r.setdefault("commands",[]).append(dict(label=label,returncode=p.returncode));save()
 assert p.returncode==0,(label,p.stdout[-3000:])
 return p.stdout.decode(errors="replace")
save()
container="nssoc-pll-current-op"
try:
 assert os.environ["GITHUB_ACTIONS"]=="true" and os.environ["GITHUB_RUN_ATTEMPT"]=="1"
 assert os.environ["GITHUB_REF"]=="refs/heads/codex/pll-current-prefix4ns"
 preparation=original.prepare()
 r["preparation"]=preparation;save()
 engine=original.OUT/"runtime/patched-ngspice"
 assert original.sha(engine)=="103134f6e3bf71771a7f9c94cc43fd5ea2f9d51490116718814aa344e9c51509"
 model=original.LIB/"models/models/sg13g2_hbt_mod.lib"
 assert original.sha(model)=="ae9288f885dd30fab24b07ed1e7e02e69eac9154022a0a6da576985183b0bd79"
 coverage=original.verify_new_physical(original.CASE)
 targets={}
 for i in [391,392,393,394,395,396,400]:
  found=[s.split()[1].split("[off]")[0][1:] for s in coverage["native_hbt_off_targets"]if ".xd"+str(i).zfill(4)+"."in s]
  assert len(found)==1
  targets[i]=found[0]
 queries=["@"+leaf+"["+field+"]"for leaf in targets.values()for field in ["ic","ib","ie","is","qbe","qbc"]]
 assert len(set(queries))==42
 import io,zipfile
 audit_run=json.loads(subprocess.check_output(["gh","api","repos/Melihakbulut221/nssoc/actions/runs/43700489696"]))
 assert audit_run["head_sha"]=="ec300f1e8cfa04b84ce0e12d819f56551757590c" and audit_run["conclusion"]=="success"
 meta=json.loads(subprocess.check_output(["gh","api","repos/Melihakbulut221/nssoc/actions/artifacts/14156446419"]))
 assert meta["workflow_run"]["id"]==43700489696 and meta["digest"]=="sha256:90ae28c3fc79198c1594944707f6e3f47936ff64086328732e139111cd3bf54c"
 packed=subprocess.check_output(["gh","api","repos/Melihakbulut221/nssoc/actions/artifacts/14156446419/zip"])
 assert hashlib.sha256(packed).hexdigest()=="90ae28c3fc79198c1594944707f6e3f47936ff64086328732e139111cd3bf54c"
 incidence=json.loads(zipfile.ZipFile(io.BytesIO(packed)).read("readback.json"))
 assert incidence["unique_boundaries"]==21 and len(incidence["terminal_incidence"])==21
 assert original.sha(original.CASE/"parent865.spice")==incidence["metal_model_sha256"]=="02210e5fe8dce4c0fbda06de98d5651b5a894e6ad2d9b2f3e7bb83acf671b258"
 boundary=[]
 for row in incidence["terminal_incidence"]:
  assert row["unique_device_with_explicit_passive_boundary"] and not row["other_device_cards"]
  for branch in row["passive_branches"]:
   query="@"+branch["kind"]+".xloop."+branch["instance"].lower()+"[i]"
   boundary.append(dict(device=row["device"],terminal=row["terminal"],query=query,device_current_sign=-branch["outward_sign"]))
 assert len(boundary)==54
 substrate=[]
 for i in targets:
  for kind,name in [("r","rsub"),("c","csub")]:substrate.append(dict(device=i,query="@"+kind+".xloop.xd"+str(i).zfill(4)+"."+name+"[i]",device_current_sign=-1))
 queries=list(dict.fromkeys(queries+[p["query"]for p in boundary+substrate]))
 assert len(queries)>42
 r.update(passive_boundary=boundary,substrate_boundary=substrate,incidence_source_run=43700489696)

 # Authenticate original full selected cache before a new diagnostic starts.
 import tarfile,shutil
 cache_dir=OUT/"reference";cache_dir.mkdir()
 def asset(aid,digest,path):
  meta=json.loads(subprocess.check_output(["gh","api","repos/Melihakbulut221/nssoc/releases/assets/"+str(aid)]))
  assert meta["digest"]=="sha256:"+digest
  with path.open("xb")as dest:subprocess.run(["gh","api","--allow-escape-sequences","repos/Melihakbulut221/nssoc/releases/assets/"+str(aid),"-H","Accept: application/octet-stream"],stdout=dest,check=True,timeout=900)
  assert original.sha(path)==digest
  return path
 summary=json.loads(asset(672440354,"6d2b595d734cfa1ee4f4f6a53b8baa124faef1a4f87cff664cb285b60b845969",cache_dir/"summary.json").read_text())
 assert summary["original_reproduction"]["original_cache_bits_identical"] and summary["full5106_column_capture_verified"] and not summary["acquisition_accepted"]
 c=summary["selected_cache"];assert c["rows"]==3201410 and len(c["columns"])==len(set(c["columns"]))==131 and c["columns"][0]=="time"
 assert c["sha256"]=="aad3cab8f3035a7c89eca665016bc15558152877bc058972f8a03dfa4172bf97" and c["bytes"]==3355077680
 archive=cache_dir/"source.tar.gz"
 parts=[(672440590,1073741824,"fcf03cf9a4b7956104e7f41763cba0b94258e922b85b7525b5fecd283b9167dc"),(672442100,1073741824,"222c22dab5ec349dbe4f4f64beab4514f16db6ad064b8cf0d277a005a7c0564e"),(672443604,820833375,"c6f743f96f760dc68056ac31f67117d8e497a4ee3512248b5b41197c368d577e")]
 with archive.open("xb")as out:
  for i,(aid,size,digest)in enumerate(parts):
   p=asset(aid,digest,cache_dir/("part"+str(i)));assert p.stat().st_size==size
   with p.open("rb")as inp:shutil.copyfileobj(inp,out,1048576)
   p.unlink()
 assert original.sha(archive)=="066f788046541e10f48e1d8122a442933c56d590d2206ca3883d7b931287b12c"
 found=False
 with tarfile.open(archive,"r|gz")as tar:
  for member in tar:
   if member.name=="cloud-pll-first-latch-sinks/selected-native.bin":
    assert not found and member.isfile()and member.size==c["bytes"];found=True
    with tar.extractfile(member)as inp,(cache_dir/"selected.bin").open("xb")as out:shutil.copyfileobj(inp,out,1048576)
 assert found and original.sha(cache_dir/"selected.bin")==c["sha256"]
 archive.unlink()
 ref=np.memmap(cache_dir/"selected.bin",dtype="<f8",mode="r",shape=(c["rows"],131))
 end=int(np.searchsorted(ref[:,0],4e-9,side="left"));assert end>12000
 expected=np.array(ref[:end,:],copy=True);del ref
 assert np.isfinite(expected).all()and expected[0,0]==0 and np.all(np.diff(expected[:,0])>0)
 (cache_dir/"selected.bin").unlink()
 r["reference"]={"cache_sha256":c["sha256"],"columns":c["columns"],"strictly_before_4ns_rows":end,"prefix_sha256":hashlib.sha256(expected.tobytes()).hexdigest(),"original_acquisition_accepted":False}
 body=(original.CASE/"circuit.cir").read_text();assert original.sha(original.CASE/"circuit.cir")=="690d1e9cf8ab1c7fcf1e0d6a5450df1c04dbb0eeef1f6b38018845cffd7671c6"
 declaration=".tran 3.125e-13 1e-06 0 3.125e-13";assert body.count(declaration)==1
 diagnostic=body.replace(declaration,".tran 3.125e-13 4e-09 0 3.125e-13")
 assert diagnostic.replace(".tran 3.125e-13 4e-09 0 3.125e-13",declaration)==body
 (original.CASE/"diagnostic-circuit.cir").write_text(diagnostic)
 lines=["NSSOC actual PLL4ns current observation diagnostic",'.include "diagnostic-circuit.cir"',".control","save all "+" ".join(queries),"op","write diagnostic-op.raw all","run current4ns.raw","quit",".endc",".end"]
 wrapper=original.CASE/"current4ns.cir";wrapper.write_text("\n".join(lines)+"\n")
 r.update(queries=queries,targets=targets,wrapper_sha256=original.sha(wrapper),diagnostic_deck_sha256=original.sha(original.CASE/"diagnostic-circuit.cir"),transient_run=True);save()
 assert original.sha(original.OUT/"native-image.tar")==preparation["native_image_sha256"]
 run("load-image",["docker","load","-i",str(original.OUT/"native-image.tar")])
 image=json.loads(run("inspect-image",["docker","image","inspect",preparation["image_id"]]))[0]
 assert image["Id"]==preparation["image_id"]
 cpu=str(min(os.sched_getaffinity(0)))
 args=["docker","create","--name",container,"--network","none","--cpuset-cpus",cpu,
       "--mount","type=bind,src="+str(ROOT)+",dst="+str(ROOT)+",readonly",
       "--mount","type=bind,src="+str(original.CASE)+",dst="+str(original.CASE),"-w",str(original.CASE),
       "-e","SPICE_SCRIPTS="+str(original.CASE),"-e","OMP_NUM_THREADS=1","-e","RAYON_NUM_THREADS=1",
       "-e","GLIBC_TUNABLES="+original.portable.TUNABLES,"--entrypoint",str(engine),preparation["image_id"],"-n","-b",wrapper.name]
 run("create",args)
 text=run("transient",["docker","start","-a",container],10800)
 state=json.loads(run("inspect-completed",["docker","inspect",container]))[0]["State"]
 assert state["ExitCode"]==0 and not state["Running"]
 original.verify_native_flags(text)
 assert not re.search(r"(?im)^\s*(error|warning|fatal)\b|no such (device|vector|parameter)",text)
 raw=original.CASE/"current4ns.raw"
 with raw.open("rb")as f:header=f.read(1024*1024)
 assert b"Binary:\n"in header
 offset=header.index(b"Binary:\n")+len(b"Binary:\n");header=header[:offset].decode()
 (OUT/"header.txt").write_text(header)
 nv=int(re.search(r"No. Variables:\s*(\d+)",header)[1]);nr=int(re.search(r"No. Points:\s*(\d+)",header)[1])
 names=[line.split()[1].lower()for line in header.split("Variables:\n",1)[1].split("Binary:",1)[0].splitlines()if len(line.split())==3]
 assert len(names)==len(set(names))==nv and nv==5216 and raw.stat().st_size-offset==nr*nv*8
 values=np.memmap(raw,dtype="<f8",offset=offset,mode="r",shape=(nr,nv));assert names[0]=="time"
 assert values[0,0]==0 and values[-1,0]==4e-9
 measured_end=int(np.searchsorted(values[:,0],4e-9,side="left"));assert measured_end==end
 indices=[names.index(n.lower())for n in c["columns"]]
 observed=np.array(values[:end,indices],copy=True)
 def prefix_gate(a,b):
  assert a.shape==b.shape and np.array_equal(a.view("<u8"),b.view("<u8")),"Original native trajectory diverged"
 prefix_gate(observed,expected)
 mutant=observed.copy();mutant.view("<u8")[1,1]^=np.uint64(1)
 try:prefix_gate(mutant,expected)
 except AssertionError:r["prefix_bit_mutant_rejected"]=True
 else:raise AssertionError("Bit mutation accepted")
 for lo in range(0,nr,512):assert np.isfinite(values[lo:lo+512,:]).all()
 typed={line.split()[1].lower():line.split()[2]for line in header.split("Variables:\n",1)[1].split("Binary:",1)[0].splitlines()if len(line.split())==3}
 for vector in coverage["vectors"]:assert typed[vector.lower()]=="voltage"
 for query in queries:assert typed[query.lower()if query.endswith(("[qbe]","[qbc]"))else"i("+query.lower()+")"]==("charge"if query.endswith(("[qbe]","[qbc]"))else"current")
 assert all(original.sha(Path(p))==h for p,h in preparation["protected"].items())
 r.update(status="PASS4NS_ORIGINAL131_BIT_PREFIX_WITH110_CURRENT_CHARGE_QUERIES",raw_sha256=original.sha(raw),rows=nr,variables=nv,original_sources_unchanged=True,shared_prefix_bits_identical=True,scope="First4ns diagnostic only, original131 samples exact; not full5106 equivalence, full terminal-current semantics, acquisition, safety, or fullPHY acceptance.")
except BaseException as e:r.update(status="FAIL_OR_ERROR",error=repr(e),traceback=traceback.format_exc());raise
finally:
 subprocess.run(["docker","rm","-f",container],stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL);save()
