# SPDX-FileCopyrightText: 2026 Hasan Melih Akbulut
# SPDX-License-Identifier: Apache-2.0
from pathlib import Path
import json,hashlib,subprocess,time,shutil
R=Path.cwd();B=Path(__file__).resolve().parent
def pin(p):
 p=Path(p);return dict(bytes=p.stat().st_size,sha256=hashlib.sha256(p.read_bytes()).hexdigest())
fpath=B/'source-freeze03-debug.json';f=json.loads(fpath.read_text())
assert f['status']=='FROZEN_RX16_NATIVE_SIZEUP_DIAGNOSTIC_SOURCE'
assert f['sources']=={p:pin(p) for p in f['sources']}
parent=B/'source-only-peer-vco.json';j=json.loads(parent.read_text())
assert j['status']=='PASS_SOURCE_ONLY_RX16_MIXED_RC_CANDIDATE' and not j['findings']
candidate=Path(f['candidate'])
bridge=json.loads((B/'source-bridge03-debug.json').read_text())
assert ''.join(x['after'] for x in bridge['opcodes'])==candidate.read_text()
assert ''.join(x['before'] for x in bridge['opcodes'])==Path(bridge['before']['path']).read_text()
# Root explicitly authorized exact failed native diagnostic replay; peer pins
# identify the already reviewed parent. This is not a fabricated new peer.
assert not Path('/dev/shm/nssoc-rx-prefetch-v2-postroute-repair-16-debug-03').exists()
assert shutil.disk_usage('/dev/shm').free>=1024**3
cmd=['taskset','-c','8',str(R/'hw/soc/tools/cocotb-venv/bin/python'),'-u',str(candidate)]
with (B/'debug03-detached-launch.log').open('x') as log:
 p=subprocess.Popen(cmd,cwd=R,stdin=subprocess.DEVNULL,stdout=log,stderr=subprocess.STDOUT,start_new_session=True)
s=Path(f'/proc/{p.pid}/stat').read_text().rsplit(')',1)[1].split()
r=dict(status='DETACHED_ROOT_AUTHORIZED_RX16_DEBUG_REPLAY_STARTED',pid=p.pid,start_ticks=s[19],process_group=int(s[2]),command=cmd,peer=pin(B/'source-only-peer-vco.json'),freeze=pin(fpath),launcher=pin(__file__),boot_id=Path('/proc/sys/kernel/random/boot_id').read_text().strip(),utc=time.strftime('%Y-%m-%dT%H:%M:%SZ',time.gmtime()))
with (B/'debug03-detached-launch.json').open('x') as f: f.write(json.dumps(r,indent=2)+'\n')
print(json.dumps(r))
