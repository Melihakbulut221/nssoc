import os,json,re,subprocess,traceback
from pathlib import Path
import numpy as np
import cloud_pll_rhi120_c8_initial as original
ROOT=Path(__file__).resolve().parents[1];OUT=ROOT/"pll-passive-dynamic-fixture";OUT.mkdir()
r=dict(source=os.environ["GITHUB_SHA"],status="RUNNING",full_phy_accepted=False,pll_acquisition_accepted=False,dut_transient_run=False)
def save():(OUT/"result.json").write_text(json.dumps(r,indent=2)+"\n")
def command(label,args,timeout=600):
 p=subprocess.run(args,stdout=subprocess.PIPE,stderr=subprocess.STDOUT,timeout=timeout)
 (OUT/(label+".log")).write_bytes(p.stdout)
 assert p.returncode==0,(label,p.stdout[-3000:])
 return p.stdout.decode(errors="replace")
container="nssoc-passive-fixture"
try:
 assert os.environ["GITHUB_ACTIONS"]=="true" and os.environ["GITHUB_RUN_ATTEMPT"]=="1"
 assert os.environ["GITHUB_REF"]=="refs/heads/codex/pll-passive-dynamic-fixture"
 preparation=original.prepare();r["preparation"]=preparation;save()
 engine=original.OUT/"runtime/patched-ngspice"
 assert original.sha(engine)=="103134f6e3bf71771a7f9c94cc43fd5ea2f9d51490116718814aa344e9c51509"
 # Separate analytical fixture. Never alter or simulate the PLL DUT here.
 deck="""NSSOC existing passive current orientation transient fixture
Vdrive p 0 PWL(0 0 1n 1 2n 1)
Rpos p 0 100
Rneg 0 p 100
Cpos p 0 5p
Cneg 0 p 5p
.options reltol=1e-6 abstol=1e-12 vntol=1e-9
.control
set filetype=binary
save all @rpos[i] @rneg[i] @cpos[i] @cneg[i]
tran 1p 2n 0 1p
write passive-fixture.raw all
quit
.endc
.end
"""
 wrapper=original.CASE/"passive-fixture.cir";wrapper.write_text(deck)
 r["wrapper_sha256"]=original.sha(wrapper)
 assert original.sha(original.OUT/"native-image.tar")==preparation["native_image_sha256"]
 command("load-image",["docker","load","-i",str(original.OUT/"native-image.tar")])
 image=json.loads(command("inspect-image",["docker","image","inspect",preparation["image_id"]]))[0]
 assert image["Id"]==preparation["image_id"]
 command("create",["docker","create","--name",container,"--network","none","--cpuset-cpus",str(min(os.sched_getaffinity(0))),"--mount","type=bind,src="+str(ROOT)+",dst="+str(ROOT)+",readonly","--mount","type=bind,src="+str(original.CASE)+",dst="+str(original.CASE),"-w",str(original.CASE),"-e","SPICE_SCRIPTS="+str(original.CASE),"-e","OMP_NUM_THREADS=1","-e","RAYON_NUM_THREADS=1","-e","GLIBC_TUNABLES="+original.portable.TUNABLES,"--entrypoint",str(engine),preparation["image_id"],"-n","-b",wrapper.name])
 text=command("transient",["docker","start","-a",container],180)
 state=json.loads(command("inspect-completed",["docker","inspect",container]))[0]["State"]
 assert state["ExitCode"]==0 and not state["Running"]
 assert not re.search(r"(?im)^\s*(error|warning|fatal)\b|no such (device|vector|parameter)",text)
 raw=(original.CASE/"passive-fixture.raw").read_bytes();header,payload=raw.split(b"Binary:\n",1);header=header.decode()
 (OUT/"passive-fixture.raw").write_bytes(raw);(OUT/"header.txt").write_text(header)
 assert "Transient Analysis"in header and "Flags: real"in header
 nv=int(re.search(r"No. Variables:\s*(\d+)",header)[1]);nr=int(re.search(r"No. Points:\s*(\d+)",header)[1])
 assert len(payload)==nv*nr*8 and nr>1000
 names=[line.split()[1].lower()for line in header.split("Variables:\n",1)[1].splitlines()if len(line.split())==3]
 assert len(names)==nv and len(set(names))==nv
 data=np.frombuffer(payload,dtype="<f8").reshape(nr,nv);assert np.isfinite(data).all()
 vectors={name:data[:,i]for i,name in enumerate(names)}
 t=vectors["time"];v=vectors["v(p)"];rp=vectors["i(@rpos[i])"];rn=vectors["i(@rneg[i])"];cp=vectors["i(@cpos[i])"];cn=vectors["i(@cneg[i])"];vs=vectors["i(vdrive)"]
 ramp=(t>0.2e-9)&(t<0.8e-9);hold=(t>1.2e-9)&(t<1.8e-9);assert min(ramp.sum(),hold.sum())>100
 metrics={"resistor_positive_error_a":float(np.max(abs(rp-v/100))),"resistor_negative_error_a":float(np.max(abs(rn+v/100))),"capacitor_positive_ramp_error_a":float(np.max(abs(cp[ramp]-.005))),"capacitor_negative_ramp_error_a":float(np.max(abs(cn[ramp]+.005))),"capacitor_hold_error_a":float(max(np.max(abs(cp[hold])),np.max(abs(cn[hold])))),"kcl_error_a":float(np.max(abs((rp-rn+cp-cn+vs)[ramp|hold])))}
 def gate(m):
  assert all(np.isfinite(x)and x<1e-7 for x in m.values()),m
 gate(metrics)
 rejected=[]
 for fault,kcl in [("reversed_resistor_sign",rp+rn+cp-cn+vs),("omitted_capacitor",rp-rn+cp+vs)]:
  changed=dict(metrics,kcl_error_a=float(np.max(abs(kcl[ramp]))))
  try:gate(changed)
  except AssertionError:rejected.append(fault)
  else:raise AssertionError("Fault accepted: "+fault)
 assert len(rejected)==2
 assert all(original.sha(Path(p))==h for p,h in preparation["protected"].items())
 r.update(status="PASS_PASSIVE_FIXTURE_ORIENTATION_AND_KCL_ONLY",metrics=metrics,fault_controls=rejected,points=nr,variables=nv,raw_sha256=original.sha(original.CASE/"passive-fixture.raw"),original_sources_unchanged=True,scope="Separate linear RC fixture on exact frozen engine; not PLL trajectory equivalence or nonlinear terminal-current qualification.")
except BaseException as e:r.update(status="FAIL_OR_ERROR",error=repr(e),traceback=traceback.format_exc());raise
finally:
 subprocess.run(["docker","rm","-f",container],stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL);save()
