# SPDX-FileCopyrightText: 2026 Hasan Melih Akbulut
# SPDX-License-Identifier: Apache-2.0
"""Seal an explicit closed byte list; no directory traversal of live evidence."""
from pathlib import Path
import hashlib,json,os,resource,shutil,tarfile
F=Path(__file__).resolve().parent;R=Path.cwd();OUT=F.parent
T=OUT/'pcie-tail115-connected570-tuning-20261006';C=OUT/'pcie-tail115-connected570-save-batches-20261006'
def pin(p):
 p=Path(p)
 with p.open('rb')as src:return dict(bytes=p.stat().st_size,sha256=hashlib.file_digest(src,'sha256').hexdigest())
def guard():
 assert os.sched_getaffinity(0)=={10}and resource.getrlimit(resource.RLIMIT_AS)[0]<=2*1024**3
 assert shutil.disk_usage('/dev/shm').free>=512*1024**2 and shutil.disk_usage(F).free>=1024**3
 assert sum(p.stat().st_size for p in F.rglob('*')if p.is_file())<=256*1024**2
snapshot=F/'snapshot-inputs01.json';selection=json.loads(snapshot.read_text());assert not(F/'finite-snapshot01.json').exists()
assert selection['status']=='CLOSED_SOURCE_AND_CONTROLS_SNAPSHOT_EXCLUDING_ACTIVE570_NATIVE'
for p,v in selection['files'].items():assert pin(p)==v,p
for folder,count in [('finite-controls05',11),('storage-controls04',23),('lifecycle-controls04',7)]:
 d=json.loads((T/folder/'result.json').read_text());assert d['cases']==count and d['status'].startswith('PASS_')and all(x['passed']for x in d['outcomes'])
a=json.loads((C/'native-control01/result.json').read_text());assert a['status']=='PASS_BOUNDED_NATIVE570_SAVE_BATCH_COMMAND_AND_OBSERVATION_CONTROLS'and a['cases']==8 and all(x['passed']for x in a['outcomes'])
assert a['full34ns_tuning_executed']is False and a['physics_acceptance']is False
originals=dict(selection['files']);originals[str(snapshot)]=pin(snapshot);members={};compact={};methods={}
for name,value in originals.items():
 p=Path(name);assert p.is_relative_to(R)
 rel=p.relative_to(R);dest=F/'compact-evidence'/rel;dest.parent.mkdir(parents=True,exist_ok=True);assert not dest.exists();shutil.copyfile(p,dest);assert pin(dest)==value
 compact[str(dest)]=value;members['compact-evidence/'+str(rel)]=value
 if p.suffix=='.py'and p.is_relative_to(OUT)and'upstream-source01'not in p.parts:methods[str(p)]=value
 guard()
archive=F/'pcie-tail115-connected570-source-controls-20261006.tar.xz';assert not archive.exists()
with tarfile.open(archive,'w:xz',preset=1)as tar:
 for name,value in members.items():
  p=F/name;info=tarfile.TarInfo(name);info.size=value['bytes'];info.mode=0o644;info.mtime=0
  with p.open('rb')as src:tar.addfile(info,src)
  guard()
seen={}
with tarfile.open(archive,'r|xz')as tar:
 for member in tar:
  assert member.isfile()and member.name not in seen
  seen[member.name]=dict(bytes=member.size,sha256=hashlib.file_digest(tar.extractfile(member),'sha256').hexdigest());guard()
assert seen==members
for p,v in originals.items():assert pin(p)==v,p
manifest=F/'members01.json';manifest.write_text(json.dumps(members,indent=2)+'\n')
record=dict(status='SEALED_CLOSED570_SOURCE_CONTROLS_PENDING_PUBLICATION',sources={},method_allowlist=methods,compact_evidence=compact,original_evidence=originals,method_files=len(methods),compact_files=len(compact),source_files=0,archives=[dict(path=str(archive),**pin(archive),members=len(members),manifest=str(manifest),manifest_pin=pin(manifest))],assets=[],public_receipts={},current_control_cases=dict(inherited_finite=11,inherited_storage=23,inherited_lifecycle=7,new_actual_command_and_observation=8,total=49),historical_failures_retained=True,source_contract_controls_separate=12,active_native_excluded=True,physics_acceptance=False,polarity_selected=False,scope=selection['scope'],root_owns_git_delivery=True)
(F/'finite-snapshot01.json').write_text(json.dumps(record,indent=2)+'\n');guard();print(json.dumps(dict(archive=pin(archive),members=len(members),methods=len(methods),snapshot=pin(F/'finite-snapshot01.json'))))
