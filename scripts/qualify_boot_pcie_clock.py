"""Run the exact runtime clock guard under both native simulators."""
import json,os,pathlib,subprocess,hashlib
from boot_pcie_clock_budget import CLOCK_GUARD
assert os.environ.get("GITHUB_ACTIONS")=="true"
ROOT=pathlib.Path.cwd();OUT=ROOT/"out/pcie-boot-clock-qualification";OUT.mkdir(parents=True)
r=dict(source_head=os.environ["GITHUB_SHA"],passed=False,scope="Clock-generation and observation gate only, not chip or timing acceptance",cases=[])
try:
 for engine in ("iverilog","cvc"):
  for half in (2,4):
   p=OUT/(engine+"-"+str(half));p.mkdir()
   source=chr(96)+"timescale 1ns/1ps\nmodule clock_probe;\nreg pcie_clk=0;\ninitial begin #1.3; forever #"+str(half)+" pcie_clk=~pcie_clk; end\n"+CLOCK_GUARD+'\ninitial begin #25; $display("CLOCK_PROBE_FINISHED"); $finish; end\nendmodule\n'
   tb=p/"tb.v";tb.write_text(source);exe=p/"sim"
   cmd=["iverilog","-g2012","-s","clock_probe","-o",str(exe),str(tb)] if engine=="iverilog" else [str(ROOT/"cvc-source/build64/cvc64"),"-sv","-o",str(exe),str(tb)]
   cp=subprocess.run(cmd,cwd=p,stdout=subprocess.PIPE,stderr=subprocess.STDOUT,timeout=120);(p/"compile.log").write_bytes(cp.stdout);assert cp.returncode==0
   cmd=["vvp",str(exe)]if engine=="iverilog"else[str(exe)]
   rp=subprocess.run(cmd,cwd=p,stdout=subprocess.PIPE,stderr=subprocess.STDOUT,timeout=30);(p/"run.log").write_bytes(rp.stdout);s=rp.stdout.decode()
   admitted=rp.returncode==0 and "NSSOC_BOOT_PCIE_CLOCK_PASS period_ns=4.000" in s and "CLOCK_PROBE_FINISHED" in s and "NSSOC_BOOT_PCIE_CLOCK_FAIL" not in s
   assert admitted==(half==2),(engine,half,s)
   if half==4:assert "NSSOC_BOOT_PCIE_CLOCK_FAIL period_ns=8.000"in s
   r["cases"].append(dict(engine=engine,half_period_ns=half,admitted=admitted,returncode=rp.returncode,run_sha256=hashlib.sha256(rp.stdout).hexdigest()))
 r["passed"]=True
finally:
 r["outputs"]={str(p.relative_to(OUT)):hashlib.sha256(p.read_bytes()).hexdigest()for p in OUT.rglob("*")if p.is_file()and p.name!="result.json"}
 (OUT/"result.json").write_text(json.dumps(r,indent=2))
