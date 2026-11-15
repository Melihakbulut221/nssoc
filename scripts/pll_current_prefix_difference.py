import os,json,re,subprocess,hashlib,traceback,zipfile,io
from pathlib import Path
import numpy as np
import cloud_pll_rhi120_c8_initial as original
ROOT=Path(__file__).resolve().parents[1];OUT=ROOT/"pll-current-prefix-difference";OUT.mkdir()
r=dict(source=os.environ["GITHUB_SHA"],status="RUNNING",native_simulation_started=False,acquisition_accepted=False,full_phy_accepted=False,original_prefix_gate_passed=False)
def save():(OUT/"result.json").write_text(json.dumps(r,indent=2)+"\n")
try:
 assert os.environ["GITHUB_ACTIONS"]=="true" and os.environ["GITHUB_REF"]=="refs/heads/codex/pll-current-prefix-difference"
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
 source_run=json.loads(subprocess.check_output(["gh","api","repos/Melihakbulut221/nssoc/actions/runs/43702129953"]))
 assert source_run["head_sha"]=="b6e44d8a8bb58ab639dcef52d1d4de3cfe7347ba" and source_run["conclusion"]=="failure"
 aid=14156199159;digest="8cdd9bf7d0e92a3c59d0b141f5ab288326cb30a6cfea55a6e54cbadb2f6d83b8"
 meta=json.loads(subprocess.check_output(["gh","api","repos/Melihakbulut221/nssoc/actions/artifacts/"+str(aid)]));assert meta["workflow_run"]["id"]==43702129953 and meta["digest"]=="sha256:"+digest
 packed=OUT/"native.zip"
 with packed.open("xb")as dest:subprocess.run(["gh","api","repos/Melihakbulut221/nssoc/actions/artifacts/"+str(aid)+"/zip"],stdout=dest,check=True,timeout=900)
 assert original.sha(packed)==digest
 raw=OUT/"current4ns.raw"
 with zipfile.ZipFile(packed)as z:
  assert len(z.namelist())==len(set(z.namelist()))
  names=[n for n in z.namelist()if n=="current4ns.raw"];assert len(names)==1
  with z.open(names[0])as inp,raw.open("xb")as dest:shutil.copyfileobj(inp,dest,1048576)
 packed.unlink()
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
 diff=observed.view("<u8")!=expected.view("<u8");indices=np.argwhere(diff)
 assert len(indices)>0,"Failed producer unexpectedly matches reference"
 first=[]
 for row,col in indices[:30]:
  first.append(dict(row=int(row),column=c["columns"][int(col)],reference_time_s=float(expected[row,0]),observed_time_s=float(observed[row,0]),reference=float(expected[row,col]),observed=float(observed[row,col]),absolute_difference=float(abs(observed[row,col]-expected[row,col]))))
 bycolumn=[]
 for i,n in enumerate(c["columns"]):
  hits=np.flatnonzero(diff[:,i])
  if len(hits):bycolumn.append(dict(column=n,differing_rows=len(hits),first_row=int(hits[0]),first_time_s=float(expected[hits[0],0]),max_absolute_difference=float(np.max(abs(observed[:,i]-expected[:,i])))))
 r.update(status="READBACK_COMPLETE_ORIGINAL_PREFIX_STILL_REJECTED",source_run=43702129953,native_artifact_id=aid,native_artifact_sha256=digest,raw_sha256=original.sha(raw),rows=end,differing_values=len(indices),differing_columns=len(bycolumn),time_bits_equal=bool(np.array_equal(observed[:,0].view("<u8"),expected[:,0].view("<u8"))),first_differences=first,by_column=bycolumn,scope="Read-only exact failed pilot comparison; does not relax equality or establish cause.")
 # Do not republish the native waveform; original failed producer retains it.
 del values;raw.unlink()
except BaseException as e:r.update(status="FAIL_OR_ERROR",error=repr(e),traceback=traceback.format_exc());raise
finally:save()
