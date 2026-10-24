# SPDX-FileCopyrightText: 2026 Hasan Melih Akbulut
# SPDX-License-Identifier: Apache-2.0
"""Additive source-only save batching; never rerun completed controls or native."""
from pathlib import Path
import ast,difflib,hashlib,json
B=Path(__file__).resolve().parent;C=B.parent/'pcie-tail115-connected570-save-batches-20261006'
def pin(p):
 with p.open('rb')as f:return dict(bytes=p.stat().st_size,sha256=hashlib.file_digest(f,'sha256').hexdigest())
def replace(s,a,b):
 assert s.count(a)==1,(a,s.count(a))
 return s.replace(a,b)
changes=[]
def save(name,parent,text):
 path=B/name;assert not path.exists();before=(B/parent).read_text();ast.parse(text);path.write_text(text)
 changes.append(dict(parent=parent,path=name,parent_pin=pin(B/parent),pin=pin(path),before=before,after=text,full_diff=''.join(difflib.unified_diff(before.splitlines(True),text.splitlines(True)))))
old=(B/'driver_custom02.py').read_text();new=replace(old,"NATIVE_ROOT=B/'native02'","NATIVE_ROOT=B/'native03'")
new=replace(new,"POINTS=(0.5,0.6,0.7)","POINTS=(0.5,0.6,0.7)\nSAVE_SOURCE=B.parent/'pcie-tail115-connected570-save-batches-20261006'\nsys.path.insert(0,str(SAVE_SOURCE))\nimport save_batches03 as batch")
save('driver_custom03.py','driver_custom02.py',new)
save('capture_custom03.py','capture_custom02.py',(B/'capture_custom02.py').read_text())
old=(B/'prepare_driver02.py').read_text();new=old
for a,b in [('driver_custom02.py','driver_custom03.py'),('capture_custom02.py','capture_custom03.py'),('characterize_clamped570_02.py','characterize_clamped570_03.py'),('driver-source-bridge02.json','driver-source-bridge03.json')]:new=new.replace(a,b)
needle=" if name=='run':"
insert=" if name=='deck':\n  old_save='        \\\"save \\\" + \\\" \\\".join(n.vectors(rows, c[\\\"extra_vectors\\\"])),'.replace('\\\\\\\"','\\\"')\n  assert after.count(old_save)==1\n  after=after.replace(old_save,'        *batch.commands(n.vectors(rows, c[\\\"extra_vectors\\\"])),')\n"
# Literal generator statement, not a regex or broad source rewrite.
insert=''' if name=='deck':
  old_save='        "save " + " ".join(n.vectors(rows, c["extra_vectors"])), '
  old_save=old_save.rstrip()
  assert after.count(old_save)==1
  after=after.replace(old_save,'        *batch.commands(n.vectors(rows, c["extra_vectors"])),')
'''
new=replace(new,needle,insert+needle)
save('prepare_driver03.py','prepare_driver02.py',new)
old=(B/'launch_three02.py').read_text();new=old
for a,b in [('characterize_clamped570_02','characterize_clamped570_03'),('source-freeze02.json','source-freeze03.json'),('source-only-peer-root02.json','source-only-peer-root03.json'),('campaign02.json','campaign03.json'),('launch-once02.json','launch-once03.json'),('controller02.log','controller03.log'),('detached-launch02.json','detached-launch03.json')]:new=new.replace(a,b)
save('launch_three03.py','launch_three02.py',new)
(B/'retry-source-bridge03.json').write_text(json.dumps(dict(status='DRAFT_SOURCE_ONLY_BATCHED_SAVE_RETRY_NOT_DISPATCHED',changes=changes,batch_helper=pin(C/'save_batches03.py'),scope='Only fresh03 namespace, helper import and exact1133-vector save batching. Full34ns/.3125ps/4–34ns window and every570 safety/13+4 criterion unchanged. Native control and final source gate remain prerequisites.'),indent=2)+'\n')
print(json.dumps(dict(files=[r['path']for r in changes])))
