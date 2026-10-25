# SPDX-FileCopyrightText: 2026 Hasan Melih Akbulut
# SPDX-License-Identifier: Apache-2.0
"""Restore exact published570 failed capture; never overwrite an existing file."""
from pathlib import Path
import json,hashlib,urllib.request,time,os,sys
B=Path(__file__).resolve().parent

def verify(data,expected):
 assert len(data)==expected['bytes']and hashlib.sha256(data).hexdigest()==expected['sha256'],'Published range bytes or digest differ'

def main():
 r=json.loads((B/'pcie-native-wave-archive-20261011.json').read_text());dst=Path(sys.argv[1]) if len(sys.argv)==2 else Path(r['local_wave']);assert not dst.exists()and not dst.is_symlink();tmp=dst.with_name(dst.name+'.restore-partial');done=0;whole=hashlib.sha256()
 # Retained incomplete restoration can resume only at an independently verified part boundary.
 if tmp.exists():
  with tmp.open('rb')as f:
   for part in r['parts']:
    data=f.read(part['bytes'])
    if not data:break
    if len(data)<part['bytes']:
     with tmp.open('r+b')as out:out.truncate(done)
     break
    verify(data,part);whole.update(data);done+=len(data)
 with tmp.open('ab')as f:
  for part in r['parts']:
   if part['offset']<done:continue
   assert part['offset']==done
   ph=hashlib.sha256();received=0
   with urllib.request.urlopen(part['url']+'?restore='+str(time.time_ns()),timeout=60)as response:
    assert response.status==200
    while blob:=response.read(1024**2):
     assert received+len(blob)<=part['bytes'];f.write(blob);ph.update(blob);whole.update(blob);received+=len(blob)
   assert received==part['bytes']and ph.hexdigest()==part['sha256'];f.flush();os.fsync(f.fileno());done+=received;print('RESTORED_VERIFIED_PART',part['name'],done,flush=True)
 assert done==r['bytes']and whole.hexdigest()==r['sha256'];assert not dst.exists();os.link(tmp,dst);tmp.unlink();print('PASS_COMPLETE_EXACT_WAVE_RESTORATION')
if __name__=='__main__':main()
