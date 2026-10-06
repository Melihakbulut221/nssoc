"""Seal finite methods, controls and launch proof, excluding the running capture."""
from pathlib import Path
import hashlib,io,json,tarfile,xml.etree.ElementTree as ET
R=Path.cwd();B=Path(__file__).resolve().parent

def pin(p):
 with p.open('rb')as f:return dict(bytes=p.stat().st_size,sha256=hashlib.file_digest(f,'sha256').hexdigest())
f=json.loads((B/'source-freeze01.json').read_text())
for p,v in(f['sources']|f['parent_methods']).items():assert pin(R/p)==v
cs=ET.parse(B/'method-controls03.xml').findall('.//testcase');assert len(cs)==43 and all(not any(c.find(k)is not None for k in['failure','error','skipped'])for c in cs)
for p,status in[(B/'source-only-peer-rx01.json','PASS_SOURCE_ONLY_PLL_RETAINED_TSTEP_MAXSTEP125'),(B/'launch01/source-peer-rx01.json','PASS_SOURCE_ONLY_DETACHED_PLL_MAXSTEP125')]:
 q=json.loads(p.read_text());assert q['status']==status and not q['findings']
proof=json.loads((B/'launch01/post-tool-progress01.json').read_text());assert proof['simulation_seconds_after']>proof['simulation_seconds_before']and proof['native_AS_bytes']==1073741824
paths={Path(p).resolve()for p in f['sources']}
for p in B.rglob('*'):
 if not p.is_file()or p.is_symlink()or '__pycache__'in p.parts:continue
 if p.name in ['active-checkpoint.json','launch.log','supervisor.log','seal-initial01.log']or p.suffix in['.xz','.gz']:continue
 paths.add(p.resolve())
manifest={str(p):pin(p)for p in sorted(paths)}
out=B/'pcie-pll-maxstep125-methods-launch-20261006.tar.xz';assert not out.exists()
with tarfile.open(out,'w:xz',preset=3)as tar:
 for p in manifest:tar.add(p,arcname=p.lstrip('/'),recursive=False)
 data=(json.dumps(manifest,indent=2)+'\n').encode();info=tarfile.TarInfo('members.json');info.size=len(data);tar.addfile(info,io.BytesIO(data))
seen=set()
with tarfile.open(out,'r:xz')as tar:
 for member in tar:
  assert member.isfile()and member.name not in seen;seen.add(member.name);data=tar.extractfile(member).read()
  if member.name=='members.json':assert json.loads(data)==manifest
  else:assert dict(bytes=len(data),sha256=hashlib.sha256(data).hexdigest())==manifest['/'+member.name]
assert len(seen)==len(manifest)+1
for p,v in manifest.items():assert pin(Path(p))==v
receipt=dict(status='PASS_FINITE_MAXSTEP125_METHODS_AND_ACTUAL_LAUNCH_PRESERVED_NATIVE_RUNNING',archive=dict(path=str(out),**pin(out)),members=len(seen),full_member_readback=True,all_originals_unchanged=True,files=manifest,source_allowlist=[dict(repository_path=p,**v)for p,v in f['sources'].items()],method_controls=43,previous_phase_pair_status='FAIL_FINITE_NOMINAL_TIMESTEP_SCREEN',native_running_at_finite_cut=proof['controller'],actual_native=proof['native'],simulation_progress_s=[proof['simulation_seconds_before'],proof['simulation_seconds_after']],source_peer=pin(B/'source-only-peer-rx01.json'),launch_peer=pin(B/'launch01/source-peer-rx01.json'),scope='Only finite methods/control/sourcepeer/declaration and actual detached launch proof. Running capture bytes/status/logs excluded; no1uscompletion/replay/convergence/physicalacceptanceclaim.')
(B/'pcie-pll-maxstep125-methods-launch-validation-20261006.json').write_text(json.dumps(receipt,indent=2)+'\n');print(receipt['status'],pin(out),len(seen))
