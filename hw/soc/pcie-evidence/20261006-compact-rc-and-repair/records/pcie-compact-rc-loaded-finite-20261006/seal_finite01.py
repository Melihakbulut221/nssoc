from pathlib import Path
import json,hashlib,shutil,tarfile
R=Path.cwd();B=Path(__file__).resolve().parent;O=R/'hw/soc/out'
def pin(p):
 p=Path(p)
 with p.open('rb')as f:return dict(bytes=p.stat().st_size,sha256=hashlib.file_digest(f,'sha256').hexdigest())
W=O/'pcie-divider-v7-compact-v2-wire-v1-20261006';C=O/'pcie-divider-v7-compact-v2-wire-rc-v1-20261006';L=O/'pcie-vco-v6-divider-compact-v2-wire-v1-20261006';V=O/'pcie-compact-wave-root-20261006';N=Path('/dev/shm/nssoc-vco-v6-divider-compact-v2-wire-06-01')
sources={}
for name,want in json.loads((L/'source-freeze01.json').read_text())['new_sources'].items():
 p=R/name;assert pin(p)==want;sources[str(p)]=want
assert len(sources)==20
assert json.loads((N/'result.json').read_text())['status']=='FAIL_NATIVE_LOADED_FEEDBACK_SCREEN'
assert json.loads((L/'release-06-01.json').read_text())['status']=='PASS_IMMUTABLE_RELEASE_ROUNDTRIPS'
assert json.loads((C/'release-native01.json').read_text())['status']=='PASS_IMMUTABLE_RELEASE_ROUNDTRIPS'
files={}
for component,root in {'compact-wire-geometry':W,'compact-wire-rc':C,'compact-loaded455':L,'root-wave-peer':V}.items():
 for p in root.rglob('*'):
  if not p.is_file() or p.is_symlink() or '__pycache__'in p.parts or any(x.endswith('.transport')for x in p.parts):continue
  if p.suffix not in ['.json','.py','.log','.txt','.spice','.cir','.lvs','.xml','.png']:continue
  rel=Path(component)/p.relative_to(root);dest=B/'compact-evidence'/rel;assert not dest.exists();dest.parent.mkdir(parents=True,exist_ok=True);shutil.copyfile(p,dest);assert pin(p)==pin(dest);files[str(rel)]=dict(source=str(p),snapshot=str(dest),**pin(dest))
for name in ['result.json','execution.json']:
 p=N/name
 if p.exists():
  rel=Path('compact-loaded455-native')/name;dest=B/'compact-evidence'/rel;dest.parent.mkdir(parents=True,exist_ok=True);shutil.copyfile(p,dest);files[str(rel)]=dict(source=str(p),snapshot=str(dest),**pin(dest));assert pin(p)==pin(dest)
archives=[]
for manifest,archive,public in [(C/'closed-native-backup01.json',C/'pcie-divider-v7-compact-v2-wire-native01.tar.xz',C/'release-native01.json'),(L/'members-06-01.json',L/'pcie-vco-v6-divider-compact-v2-wire-06-01.tar.xz',L/'release-06-01.json')]:
 d=json.loads(manifest.read_text());members=d.get('members',d);seen={}
 with tarfile.open(archive,'r|xz')as tf:
  for item in tf:
   assert item.isfile()and item.name not in seen;h=dict(bytes=item.size,sha256=hashlib.file_digest(tf.extractfile(item),'sha256').hexdigest());want=members[item.name];assert h=={k:want[k]for k in ['bytes','sha256']};seen[item.name]=h
 assert set(seen)==set(members)
 receipt=json.loads(public.read_text());asset=next(v for v in receipt['assets']if v['name']==archive.name);assert pin(archive)=={k:asset[k]for k in ['bytes','sha256']}and asset['authenticated_roundtrip']and asset['anonymous_roundtrip']
 archives.append(dict(path=str(archive),**pin(archive),member_manifest=str(manifest),member_manifest_pin=pin(manifest),member_count=len(seen),public_receipt=dict(path=str(public),**pin(public)),asset=asset))
a=B/'pcie-compact-wire-loaded-additive01.tar.xz';assert not a.exists()
with tarfile.open(a,'x:xz',preset=3)as tf:
 for rel,row in files.items():tf.add(row['snapshot'],arcname=rel,recursive=False)
seen=set()
with tarfile.open(a,'r|xz')as tf:
 for item in tf:
  assert item.isfile()and item.name not in seen;seen.add(item.name);row=files[item.name];assert item.size==row['bytes']and hashlib.file_digest(tf.extractfile(item),'sha256').hexdigest()==row['sha256']
assert seen==set(files)
record=dict(status='FINITE_COMPACT_RC_LOADED_FAILURE_AND_INDEPENDENT_WAVE_PEERS_AWAITING_ADDITIVE_PUBLICATION',sources=sources,compact_evidence=files,archives=archives,additive_archive=dict(path=str(a),**pin(a),member_count=len(files)),source_files=len(sources),compact_files=len(files),native_results={'geometry':'91devices283terminals72clusters37conductors205anchors;7geometry+5copied-input binding controls; independent savedpeer PASS','wireRC':'382R649C,300couplingedges1444matrixentries,85bodyterminals retained unmodeled;13actual corruption controls and independent stdlib savedpeer PASS','loaded455':'6817rows957columns; all455electricalscreenPASS,minHBT_VCE0.4856206924610069V; VCO8.102486506GHz but secondstage divisionFAIL/no80feedback. Authoritative FAIL_NATIVE_LOADED_FEEDBACK_SCREEN retained','root_raw_peer':'Both PowerV2 andCompact13,048,695finitevalues; all64HBTbounds rederived each, real latch terminal mapping and failed secondstageclockfrequency; saved plot and initialmissingmatplotlibattempt retained'},explicit_limits=['No qualified RF/substrate RC or foundry PEX','No functionaldiv4/div80 closure despite all455electrical screens','No fullPHY/chip integration/manufacturing acceptance','Cap24 active physical experiment excluded entirely'],all_three_archives_fullmember_readback=True,root_owns_git_delivery=True)
p=B/'finite-snapshot01.json';p.write_text(json.dumps(record,indent=2)+'\n');print(len(sources),len(files),record['additive_archive'])
