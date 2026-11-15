import os,json,re,subprocess,hashlib,traceback
from pathlib import Path
import numpy as np
import cloud_pll_rhi120_c8_initial as original
ROOT=Path(__file__).resolve().parents[1];OUT=ROOT/"pll-passive-current-preflight";OUT.mkdir()
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
 assert os.environ["GITHUB_REF"]=="refs/heads/codex/pll-passive-current-preflight"
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

 # Separate zero-source OP observer; original circuit and full1us analysis
 # declaration remain byte unchanged. No run/tran command is executed.
 lines=["NSSOC exact PLL zero OP accessor preflight",'.include "circuit.cir"',".control","save all "+" ".join(queries),"op"]
 for leaf in targets.values():lines+=["echo NSSOC_QUERY_DEVICE "+leaf,"show "+leaf+" : area m off"]
 lines+=["echo NSSOC_QUERY_VALUES_BEGIN","print "+" ".join(queries),"echo NSSOC_QUERY_VALUES_END","display","write current-op.raw all","quit",".endc",".end"]
 wrapper=original.CASE/"current-op.cir";wrapper.write_text("\n".join(lines)+"\n")
 r.update(queries=queries,targets=targets,wrapper_sha256=original.sha(wrapper));save()
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
 text=run("query",["docker","start","-a",container],180)
 info=json.loads(run("inspect-completed",["docker","inspect",container]))[0]
 assert info["State"]["ExitCode"]==0 and not info["State"]["Running"]
 assert not re.search(r"(?im)^\s*(error|warning|fatal)\b|no such (device|vector|parameter)",text)
 original.verify_native_flags(text)
 assert text.count("NSSOC_QUERY_VALUES_BEGIN")==text.count("NSSOC_QUERY_VALUES_END")==1
 values=text.split("NSSOC_QUERY_VALUES_BEGIN",1)[1].split("NSSOC_QUERY_VALUES_END",1)[0]
 parsed={}
 for query in queries:
  hits=re.findall(re.escape(query)+r"\s*=\s*([-+0-9.eE]+)",values,re.I)
  assert len(hits)==1,(query,hits)
  number=float(hits[0]);assert np.isfinite(number);parsed[query]=number
 raw=original.CASE/"current-op.raw"
 with raw.open("rb")as f:
  b=f.read(1024*1024)
 assert b"Binary:\n"in b
 header=b.split(b"Binary:\n",1)[0].decode()
 assert "Operating Point"in header
 (OUT/"current-op.raw").write_bytes(raw.read_bytes())
 (OUT/"current-op-header.txt").write_text(header)
 table=header.split("Variables:\n",1)[1].splitlines()
 typed={cols[1].lower():cols[2]for line in table if len(cols:=line.split())==3}
 def capture_gate(entries):
  for query in queries:
   name=query.lower() if query.endswith(("[qbe]","[qbc]")) else "i("+query.lower()+")"
   assert entries.get(name)==("charge"if query.endswith(("[qbe]","[qbc]"))else"current"),(name,entries.get(name))
  for vector in coverage["vectors"]:assert entries.get(vector.lower())=="voltage",vector
 capture_gate(typed)
 rejected=[]
 for fault,key,value in [("missing_passive","i("+boundary[0]["query"]+")",None),("wrong_current_type","i("+boundary[0]["query"]+")","voltage"),("missing_original_voltage",coverage["vectors"][0],None)]:
  changed=dict(typed)
  if value is None:del changed[key.lower()]
  else:changed[key.lower()]=value
  try:capture_gate(changed)
  except AssertionError:rejected.append(fault)
  else:raise AssertionError("Bad native observation coverage accepted")
 assert len(rejected)==3
 r.update(original_voltage_vectors_retained=len(coverage["vectors"]),native_variable_count=len(typed),coverage_fault_controls=rejected)

 assert all(original.sha(Path(p))==v for p,v in preparation["protected"].items())
 r.update(status="NATIVE_PASSIVE_CURRENT_AND_ORIGINAL_VOLTAGE_COVERAGE_REQUIRES_DYNAMIC_KCL_QUALIFICATION",values=parsed,
          native_off_flags_verified=102,original_sources_unchanged=True,raw_sha256=original.sha(raw),
          native_query_existence_verified=True,current_scaling_qualified=False,transient_charge_semantics_qualified=False)
except BaseException as e:r.update(status="FAIL_OR_ERROR",error=repr(e),traceback=traceback.format_exc());raise
finally:
 subprocess.run(["docker","rm","-f",container],stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL)
 save()
