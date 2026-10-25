# SPDX-FileCopyrightText: 2026 Hasan Melih Akbulut
# SPDX-License-Identifier: Apache-2.0
"""One exact detached DRT launch; no duplicate native routing."""
import datetime, hashlib, json, os, shutil, subprocess
from pathlib import Path
ROOT=Path('/home/hasanmelih/Documents/ChatGPT/nnsoc')
B=ROOT/'hw/soc/out/pcie-gen3-receive-prefetch-v2-20261004'
S=B/'repair16-source'
D=Path('/dev/shm/nssoc-rx-prefetch-v2-repair16one-drt-01')
def pin(p):
 p=Path(p)
 with p.open('rb') as f:return dict(bytes=p.stat().st_size,sha256=hashlib.file_digest(f,'sha256').hexdigest())
f=S/'route-rc-source-freeze16one.json'; peer=S/'route-rc-source-only-peer-root16one.json'
j=json.loads(f.read_text()); q=json.loads(peer.read_text())
assert q['status']=='PASS_SOURCE_ONLY_RX16ONE_ROUTE_RC_AND_SAVED_NATIVE_PROOF_PORTS' and q['findings']==[] and q['freeze']==pin(f)
for collection in ('files','inputs'):
 assert j[collection]=={p:pin(p) for p in j[collection]}
assert not D.exists() and not (S/'active-drt16one-launch.json').exists()
assert shutil.disk_usage('/dev/shm').free>=1024**3 and 8 in os.sched_getaffinity(0)
python=ROOT/'hw/soc/tools/cocotb-venv/bin/python3'
assert pin(python)==dict(bytes=8025024,sha256='a92f0f95e883390c7256b2e441484aac06b1002dbe1d924141a77c8d82f96223')
boot=Path('/proc/sys/kernel/random/boot_id').read_text().strip()
assert boot=='e1b7ced9-2243-4340-a046-92e8b30a45bc'
env={k:v for k,v in os.environ.items() if k not in ('PYTHONPATH','PYTHONHOME','PYTHONEXECUTABLE')}
command=[str(python),str(B/'drt_repair16one.py')]
with (S/'active-drt16one-launch.json').open('x') as out:
 out.write(json.dumps(dict(status='PREFLIGHT_PASSED_BEFORE_POPEN',boot_id=boot,source=pin(B/'drt_repair16one.py'),freeze=pin(f),peer=pin(peer)))+'\n');out.flush();os.fsync(out.fileno())
with (S/'drt16one.log').open('x') as log:
 p=subprocess.Popen(command,cwd=ROOT,env=env,stdin=subprocess.DEVNULL,stdout=log,stderr=subprocess.STDOUT,start_new_session=True,preexec_fn=lambda:os.sched_setaffinity(0,{8}))
 s=Path(f'/proc/{p.pid}/stat').read_text().rsplit(')',1)[1].split()
 record=dict(status='DETACHED_EXACT_RX16ONE_DRT_LAUNCHED',utc=datetime.datetime.now(datetime.timezone.utc).isoformat(),boot_id=boot,owner=dict(pid=p.pid,start_ticks=int(s[19]),process_group=int(s[2])),command=command,method=pin(Path(__file__)),freeze=pin(f),peer=pin(peer),source=pin(B/'drt_repair16one.py'),python=pin(python),cpu=8,AS_bytes=int(2.5*1024**3),healthy_elapsed_watchdog=None)
 (S/'active-drt16one-launch.json').write_text(json.dumps(record,indent=2)+'\n')
 print(json.dumps(record,indent=2))
