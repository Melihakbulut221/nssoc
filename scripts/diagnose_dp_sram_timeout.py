# SPDX-License-Identifier: Apache-2.0
import hashlib,json,zipfile,tarfile,io,pathlib
p=pathlib.Path
blob=p('native.zip').read_bytes()
assert hashlib.sha256(blob).hexdigest()=='d0109ba41e2d146d25a90f7dcaeba2602b87168cbe9b0d01a175b57b1734658e'
z=zipfile.ZipFile(io.BytesIO(blob));assert z.namelist()==['native-dp.tgz']
t=tarfile.open(fileobj=io.BytesIO(z.read('native-dp.tgz')),mode='r:gz')
expected={'native/run.log':'31feeff6656aa18d5af26b5c4be66d18add3c4e2ce6fa1ed75d50efb86085526','native/deck.log':'dc745231f6eb5a706c39c8bf42d9f845d73739c52e235e0a31ecb3bcc197a39e'}
logs={}
for name,digest in expected.items():
 matches=[m for m in t.getmembers() if m.name==name];assert len(matches)==1 and matches[0].isfile()
 raw=t.extractfile(matches[0]).read();assert hashlib.sha256(raw).hexdigest()==digest
 lines=raw.decode().splitlines();logs[name]={'sha256':digest,'lines':len(lines),'tail':lines[-120:]}
r={'source_run':43562021054,'native_artifact_id':14110867794,'native_artifact_sha256':hashlib.sha256(blob).hexdigest(),'full_comparison_completed':False,'scope':'Cloud-only archive inspection after confirmed 18000-second native timeout. No new LVS or change in acceptance.','top_result_files_present':[m.name for m in t.getmembers() if m.isfile() and m.name in ['native/lvs.lvsdb','native/extracted.cir']],'logs':logs}
p('out').mkdir();p('out/timeout-diagnosis.json').write_text(json.dumps(r,indent=2))
