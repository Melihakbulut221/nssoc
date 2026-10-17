# SPDX-FileCopyrightText: 2026 Hasan Melih Akbulut
# SPDX-License-Identifier: Apache-2.0
"""Curate an explicit finite evidence cut; no native runs, network, staging or deletion."""
from pathlib import Path,PurePosixPath
import argparse,datetime,gzip,hashlib,json,tarfile
R=Path(__file__).resolve().parents[4]
DEST=R/'hw/soc/pcie-evidence/20261005-feedback-margin-and-durable-capture'
def pin(p):
 p=Path(p)
 with p.open('rb') as f:return dict(bytes=p.stat().st_size,sha256=hashlib.file_digest(f,'sha256').hexdigest())
def hp(h):return {k:h[k] for k in ['bytes','sha256']}
def require(q,msg):
 if not q:raise ValueError(msg)
def copy_exact(source,target,want):
 source,target=Path(source),Path(target);require(source.is_file() and not source.is_symlink(),'regular source')
 require(pin(source)==hp(want),'source drift '+str(source));target.parent.mkdir(parents=True,exist_ok=True)
 if target.exists():require(pin(target)==hp(want),'existing destination differs '+str(target))
 else:
  with target.open('xb') as out:out.write(source.read_bytes())
 require(pin(source)==pin(target)==hp(want),'copy drift '+str(target))
 return dict(source_path=str(source),repository_path=str(target.relative_to(R)),**pin(target))
def main():
 p=argparse.ArgumentParser();p.add_argument('--config',required=True);p.add_argument('--output',required=True);args=p.parse_args()
 cfgpath=Path(args.config).resolve();out=Path(args.output).resolve();require(not out.exists(),'fresh output only')
 cfg=json.loads(cfgpath.read_text());components=[];sources={};copies={};public={};capsules=[]
 for c in cfg['components']:
  ready=Path(c['ready']['path']);require(pin(ready)==hp(c['ready']),'ready pin')
  copied=[]
  for row in c['sources']:
   path=R/row['repository_path'];require(pin(path)==hp(row),'allowlist drift');require(row['repository_path'] not in sources or sources[row['repository_path']]==hp(row),'source collision');sources[row['repository_path']]=hp(row)
  for row in c['evidence']:
   rel=PurePosixPath(row['relative_path']);require(not rel.is_absolute() and '..' not in rel.parts,'safe relative evidence path')
   q=copy_exact(row['path'],DEST/c['name']/str(rel),row);require(q['repository_path'] not in copies,'duplicate evidence target');copies[q['repository_path']]=q;copied.append(q['repository_path'])
   if row['path'].endswith('.gz'):
    with gzip.open(row['path'],'rb') as f:
     while f.read(1024**2):pass
  for a in c['public_assets']:
   require(a['authenticated_roundtrip'] and a['anonymous_roundtrip'],'dual public verification')
   name=a['name'];require(name not in public or public[name]==a,'asset identity collision');public[name]=a
  checks=[]
  for cap in c['capsules']:
   archive=Path(cap['path']);require(pin(archive)==hp(cap),'capsule bytes')
   manifest=Path(cap['manifest']['path']);require(pin(manifest)==hp(cap['manifest']),'capsule manifest pin');members=json.loads(manifest.read_text())
   if cap.get('members_key'):members=members[cap['members_key']]
   members=dict(members)
   if cap.get('manifest_self_name'):
    require(cap['manifest_self_name'] not in members,'no self-member collision');members[cap['manifest_self_name']]=pin(manifest)
   require(archive.name in public and hp(public[archive.name])==pin(archive),'public capsule identity')
   actual={};total=0
   with tarfile.open(archive,'r|xz') as tar:
    for member in tar:
     rel=PurePosixPath(member.name);require(member.isfile() and not rel.is_absolute() and '..' not in rel.parts and member.name not in actual,'regular unique safe member')
     require(member.name in members,'undeclared member')
     h=dict(bytes=member.size,sha256=hashlib.file_digest(tar.extractfile(member),'sha256').hexdigest());require(h==hp(members[member.name]),'member hash '+member.name);actual[member.name]=h;total+=member.size
   require(set(actual)==set(members),'full member set');require(pin(archive)==hp(cap),'capsule unchanged after readback')
   checked=dict(archive=dict(path=str(archive),**pin(archive)),member_count=len(actual),expanded_bytes=total,manifest=cap['manifest'],full_member_readback=True,public_asset=public[archive.name]);checks.append(checked);capsules.append(checked)
  require(pin(ready)==hp(c['ready']),'ready stable after copy')
  components.append(dict(name=c['name'],scope=c['scope'],ready=c['ready'],evidence_files=copied,capsules=checks,physical_acceptance=False))
 require(len(sources)==cfg['expected_source_count'],'exact source allowlist count')
 require(sum(v['bytes'] for v in copies.values())<8*1024**2,'compact cut under8MiB')
 # Public small assets are bound to exact copied local bytes as well as receipts.
 for name,a in public.items():
  matching=[v for v in copies.values() if Path(v['source_path']).name==name]
  if not name.endswith(('.tar.xz','.bin.xz')):require(any(hp(x)==hp(a) for x in matching),'public compact asset lacks matching copy '+name)
 for path,h in sources.items():require(pin(R/path)==h,'final source rehash')
 for path,row in copies.items():require(pin(R/path)==hp(row),'final compact rehash')
 record=dict(status=cfg['status'],utc=datetime.datetime.now(datetime.timezone.utc).isoformat(),method=dict(path=str(Path(__file__).resolve()),**pin(__file__)),configuration=dict(path=str(cfgpath),**pin(cfgpath)),source_allowlist=sources,source_count=len(sources),components=components,evidence=copies,evidence_file_count=len(copies),evidence_bytes=sum(v['bytes'] for v in copies.values()),public_assets=list(public.values()),full_capsule_readback_count=len(capsules),native_runs_executed=False,controls_rerun=False,public_roundtrips_repeated=False,physical_acceptance=False,limitations=cfg['limitations'])
 out.write_text(json.dumps(record,indent=2)+'\n');print(json.dumps(dict(output=str(out),**pin(out),sources=len(sources),copies=len(copies),evidence_bytes=record['evidence_bytes'],capsules=len(capsules))))
if __name__=='__main__':main()
