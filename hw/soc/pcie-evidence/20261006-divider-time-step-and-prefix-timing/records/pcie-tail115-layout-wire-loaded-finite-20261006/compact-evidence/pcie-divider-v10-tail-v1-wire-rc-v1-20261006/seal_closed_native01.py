from pathlib import Path
import json,hashlib,tarfile,io
B=Path(__file__).resolve().parent;G=B.parent/'pcie-divider-v10-tail-v1-wire-v1-20261006'
def pin(p):
 p=Path(p)
 with p.open('rb') as f:return dict(bytes=p.stat().st_size,sha256=hashlib.file_digest(f,'sha256').hexdigest())
r=json.loads((B/'native-execution.json').read_text());assert r['status']=='PASS_NATIVE_WIRE_RC_GRAPH_AND13_RAW_CONTROLS_ONLY';assert r['outputs']=={p:pin(p)for p in r['outputs']}
geo=json.loads((G/'geometry-execution.json').read_text());assert geo['status']=='PASS_DIVIDER_V10_TAIL115_SAVED_NATIVE_GEOMETRY_AND_SOURCE_BIJECTION_ONLY';assert geo['outputs']=={p:pin(p)for p in geo['outputs']}
controls=json.loads((G/'binding-controls01/result.json').read_text());assert controls['status']=='PASS_BASELINE_AND_FOUR_ACTUAL_COPIED_INPUT_BINDING_CONTROLS'
roots=[Path('/dev/shm')/n for n in ['nssoc-div4-v10-tail-v1-wire-native-01','nssoc-div4-v10-tail-v1-wire-geometry-01','nssoc-div4-v10-tail-v1-wire-rc-01','nssoc-div4-v10-tail-v1-binding-controls-01']]
files={str(Path('ram')/d.name/p.relative_to(d)):p for d in roots for p in d.rglob('*')if p.is_file()}
for d in [G,B]:
 for p in d.glob('*'):
  if p.is_file() and p.suffix in ['.json','.py','.log','.lvs'] and not p.name.startswith(('saved-rc','source-review','review_','seal_closed','closed-native')):files[str(Path('evidence')/d.name/p.name)]=p
manifest={n:dict(path=str(p),**pin(p)) for n,p in files.items()};out=B/'closed-native-backup01.tar.xz';assert not out.exists()
with tarfile.open(out,'w:xz')as t:
 for n,p in files.items():
  data=p.read_bytes();info=tarfile.TarInfo(n);info.size=len(data);info.mtime=0;info.mode=0o644;t.addfile(info,io.BytesIO(data))
with tarfile.open(out)as t:
 assert set(t.getnames())==set(manifest)
 for m in t:
  data=t.extractfile(m).read();assert dict(bytes=len(data),sha256=hashlib.sha256(data).hexdigest())=={k:manifest[m.name][k]for k in ['bytes','sha256']}
f=dict(status='CLOSED_NATIVE_ALL_MEMBER_READBACK_VERIFIED',archive=dict(path=str(out),**pin(out)),members=manifest,member_count=len(manifest),actual_R=382,actual_C=649,raw_controls=13,body_resistance_modeled=False)
(B/'closed-native-backup01.json').write_text(json.dumps(f,indent=2)+'\n');print(len(manifest),pin(out))
