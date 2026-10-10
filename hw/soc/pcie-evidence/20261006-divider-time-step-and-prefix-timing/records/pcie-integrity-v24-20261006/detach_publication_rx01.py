# SPDX-FileCopyrightText: 2026 Hasan Melih Akbulut
# SPDX-License-Identifier: Apache-2.0
import os,json,subprocess,hashlib
from pathlib import Path
R=Path('/home/hasanmelih/Documents/ChatGPT/nnsoc');B=Path(__file__).resolve().parent
names=['pcie-integrity-v24-component-controls-20261006.tar.xz','pcie-integrity-v24-composite-controls-20261006.tar.xz','pcie-integrity-v24-native-preplacement-20261006.tar.xz','pcie-integrity-v24-finite-peer-supplement-20261006.tar.xz','pcie-integrity-v24-finite-package-20261006.json']
def pin(p):
 with p.open('rb')as f:return dict(bytes=p.stat().st_size,sha256=hashlib.file_digest(f,'sha256').hexdigest())
assert not (B/'publication-release01.json').exists()
with (B/'publication-once01.json').open('x')as f:json.dump(dict(files={n:pin(B/n)for n in names},publisher=pin(R/'scripts/publish_pcie_native_capture_v4.py')),f,indent=2)
env=os.environ.copy()
for n in('PYTHONPATH','PYTHONHOME','PYTHONEXECUTABLE'):env.pop(n,None)
cmd=['/usr/bin/python3',str(R/'scripts/publish_pcie_native_capture_v4.py'),'--tag','evidence-20261006-pcie-closure','--out',str(B/'publication-release01.json'),*[str(B/n)for n in names]]
with (B/'publication01.log').open('xb')as log:
 p=subprocess.Popen(cmd,cwd=R,stdin=subprocess.DEVNULL,stdout=log,stderr=subprocess.STDOUT,env=env,start_new_session=True)
 stat=Path(f'/proc/{p.pid}/stat').read_text().rsplit(')',1)[1].split()
 record=dict(pid=p.pid,start_ticks=int(stat[19]),ppid=int(stat[1]),pgid=int(stat[2]),session=int(stat[3]),boot=Path('/proc/sys/kernel/random/boot_id').read_text().strip(),cmd=cmd)
 with (B/'publication-detached01.json').open('x')as f:json.dump(record,f,indent=2)
 print(json.dumps(record))
