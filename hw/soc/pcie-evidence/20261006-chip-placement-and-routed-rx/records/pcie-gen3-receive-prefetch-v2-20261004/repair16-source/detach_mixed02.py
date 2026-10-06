# SPDX-FileCopyrightText: 2026 Hasan Melih Akbulut
# SPDX-License-Identifier: Apache-2.0
from pathlib import Path
import json,hashlib,subprocess,time,shutil
R=Path.cwd();B=Path(__file__).resolve().parent
def pin(p):
 p=Path(p);return dict(bytes=p.stat().st_size,sha256=hashlib.sha256(p.read_bytes()).hexdigest())
p=B/'source-only-peer02-vco.json'
assert pin(p)==dict(bytes=2833,sha256='752ce3d6b3134666cf40a28646cd89bfcb1df82518c95bbcd7bccabdf4f6963a')
j=json.loads(p.read_text());assert j['status']=='PASS_SOURCE_ONLY_RX16_MIXED_RC_CANDIDATE' and j['findings']==[]
fpath=B/'source-freeze02.json';assert pin(fpath)==j['freeze']
f=json.loads(fpath.read_text())
for k in ('sources',):
 assert f[k]=={p:pin(p) for p in f[k]}
candidate=Path(f['candidate']);assert pin(candidate)==j['source_pins'][str(candidate)]
assert not Path('/dev/shm/nssoc-rx-prefetch-v2-postroute-repair-16-mixed-02').exists()
assert shutil.disk_usage('/dev/shm').free>=1024**3
cmd=['taskset','-c','8',str(R/'hw/soc/tools/cocotb-venv/bin/python'),'-u',str(candidate)]
with (B/'mixed02-detached-launch.log').open('x') as log:
 p=subprocess.Popen(cmd,cwd=R,stdin=subprocess.DEVNULL,stdout=log,stderr=subprocess.STDOUT,start_new_session=True)
s=Path(f'/proc/{p.pid}/stat').read_text().rsplit(')',1)[1].split()
r=dict(status='DETACHED_RX16_MIXED_RC_CANDIDATE_STARTED',pid=p.pid,start_ticks=s[19],process_group=int(s[2]),command=cmd,peer=pin(B/'source-only-peer02-vco.json'),freeze=pin(fpath),launcher=pin(__file__),boot_id=Path('/proc/sys/kernel/random/boot_id').read_text().strip(),utc=time.strftime('%Y-%m-%dT%H:%M:%SZ',time.gmtime()))
with (B/'mixed02-detached-launch.json').open('x') as f: f.write(json.dumps(r,indent=2)+'\n')
print(json.dumps(r))
