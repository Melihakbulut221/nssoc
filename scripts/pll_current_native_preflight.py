import os,json,re,subprocess,hashlib,traceback
from pathlib import Path
import numpy as np
import cloud_pll_rhi120_c8_initial as original
ROOT=Path(__file__).resolve().parents[1];OUT=ROOT/"pll-current-native-preflight";OUT.mkdir()
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
 assert os.environ["GITHUB_REF"]=="refs/heads/codex/pll-current-native-preflight"
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
 # Separate zero-source OP observer; original circuit and full1us analysis
 # declaration remain byte unchanged. No run/tran command is executed.
 lines=["NSSOC exact PLL zero OP accessor preflight",'.include "circuit.cir"',".control","save "+" ".join(queries),"op"]
 for leaf in targets.values():lines+=["echo NSSOC_QUERY_DEVICE "+leaf,"show "+leaf+" : all"]
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
 assert all(original.sha(Path(p))==v for p,v in preparation["protected"].items())
 r.update(status="NATIVE_ZERO_OP_ACCESSORS_EXIST_REQUIRES_UNIT_SCALING_AND_DYNAMIC_SEMANTIC_QUALIFICATION",values=parsed,
          native_off_flags_verified=102,original_sources_unchanged=True,raw_sha256=original.sha(raw),
          native_query_existence_verified=True,current_scaling_qualified=False,transient_charge_semantics_qualified=False)
except BaseException as e:r.update(status="FAIL_OR_ERROR",error=repr(e),traceback=traceback.format_exc());raise
finally:
 subprocess.run(["docker","rm","-f",container],stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL)
 save()
