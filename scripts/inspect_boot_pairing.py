import os,json,subprocess,hashlib,io,zipfile,re
from pathlib import Path
assert os.environ.get("GITHUB_ACTIONS")=="true"
OUT=Path("boot-pairing-audit");OUT.mkdir()
def sha(b):return hashlib.sha256(b).hexdigest()
repo="repos/Melihakbulut221/nssoc/"
def api(p):return json.loads(subprocess.check_output(["gh","api",repo+p]))
run=api("actions/runs/43784139463")
assert run["head_sha"]=="dca03755037478493e530bbccc41a380dbd45a63" and run["conclusion"]=="failure" and run["run_attempt"]==1
meta=api("actions/artifacts/14194180460")
digest="28ae5246854343fe147d2d3b5b3e5590959504e8221ddc3855e5d82eaf36e0e9"
assert meta["workflow_run"]["id"]==run["id"] and meta["workflow_run"]["head_sha"]==run["head_sha"] and not meta["expired"] and meta["digest"]=="sha256:"+digest
data=subprocess.check_output(["gh","api",repo+"actions/artifacts/14194180460/zip"])
assert sha(data)==digest
z=zipfile.ZipFile(io.BytesIO(data))
result=json.loads(z.read("out/cvc-chip-boot/result.json"))
raw=z.read("out/cvc-chip-boot/run.log")
assert sha(raw)==result["logs"]["run.log"]["sha256"] and result["sources_unchanged"] and result["observer_unchanged"] and not result["passed"]
traces=[]
for line in raw.decode().splitlines():
 if line.startswith("NSSOC_BOOT_TRACE "):
  row=dict(re.findall(r"(\w+)=([^ ]+)",line))
  if 2180890<=int(row["cycle"])<=2181100 or 2370900<=int(row["cycle"])<=2370925:traces.append(row)
assert traces
firmware=Path("hw/soc/out/corrpre-pcie-mbist-native-boot/rtl")
elfs=sorted(firmware.rglob("*.elf"));assert elfs
files={}
for elf in elfs:
 out=subprocess.check_output(["riscv64-linux-gnu-objdump","-d","--start-address=0","--stop-address=128",str(elf)],text=True)
 name=elf.name+".first128.dis"
 assert not (OUT/name).exists()
 (OUT/name).write_text(out)
 files[str(elf)]=dict(sha256=sha(elf.read_bytes()),disassembly_sha256=sha(out.encode()),output=name)
(OUT/"focused-trace.json").write_text(json.dumps(traces,indent=2))
(OUT/"result.json").write_text(json.dumps(dict(source_head=os.environ["GITHUB_SHA"],source_run=run["id"],source_artifact=meta["id"],artifact_sha256=digest,run_log_sha256=sha(raw),firmware=files,trace_rows=len(traces),chip_accepted=False,root_cause_proven=False,scope="Exact mapped-source ELF disassembly and authenticated dense instruction operands. ID/EX observations are not retirement proof. Diagnostic only; no firmware, watchdog, gate model or acceptance changes."),indent=2))
print("BOOT_PAIRING_AUDIT_COMPLETE",len(traces),len(elfs))

# Compare the exact flash bytes, not only the ELF disassembly.
app=firmware/"app.elf";flash=firmware/"flash0.hex"
assert app.is_file() and flash.is_file()
flat=OUT/"app-flat.bin"
subprocess.run(["riscv64-linux-gnu-objcopy","-O","binary",str(app),str(flat)],check=True)
payload=flat.read_bytes();assert len(payload)>=128
text=flash.read_text()
text=re.sub(r"/\*.*?\*/","",text,flags=re.S)
text=re.sub(r"//[^\n]*","",text)
memory={};address=0
for token in text.split():
 if token.startswith("@"):
  address=int(token[1:],16)
 else:
  assert re.fullmatch(r"[0-9a-fA-F]{1,2}",token),repr(token)
  assert 0<=address<16*1024*1024 and address not in memory
  memory[address]=int(token,16);address+=1
assert memory
image=bytearray([255])*(max(memory)+1)
for address,value in memory.items():image[address]=value
def offsets(pattern):
 values=[];start=0
 while True:
  pos=image.find(pattern,start)
  if pos<0:break
  values.append(pos);assert len(values)<100
  start=pos+1
 return values
comparison=dict(flash_sha256=sha(flash.read_bytes()),elf_sha256=sha(app.read_bytes()),
 flat_binary_sha256=sha(payload),flat_binary_bytes=len(payload),
 flash_specified_bytes=len(memory),flash_address_extent=len(image),
 first128_offsets=offsets(payload[:128]),full_binary_offsets=offsets(payload),
 expected_first32_hex=payload[:32].hex(),flash_contains_exact_flat_elf=bool(offsets(payload)))
result_path=OUT/"result.json"
summary=json.loads(result_path.read_text())
summary["flash_comparison"]=comparison
summary["scope"]+=" Flash HEX is parsed bytewise with explicit address validation and compared to objcopy of the authenticated ELF. This is image consistency only, not RAM copy or execution acceptance."
result_path.write_text(json.dumps(summary,indent=2))
print("FLASH_IMAGE_COMPARISON",json.dumps(comparison))
