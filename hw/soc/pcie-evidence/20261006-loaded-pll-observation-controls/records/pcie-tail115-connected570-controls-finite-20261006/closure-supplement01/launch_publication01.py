# SPDX-FileCopyrightText: 2026 Hasan Melih Akbulut
# SPDX-License-Identifier: Apache-2.0
"""Dispatch frozenV4 for one closed immutable source/control archive."""
from pathlib import Path
import hashlib,json,os,resource,shutil,subprocess
F=Path(__file__).resolve().parent;R=Path.cwd()
def pin(p):
 p=Path(p)
 with p.open('rb')as f:return dict(bytes=p.stat().st_size,sha256=hashlib.file_digest(f,'sha256').hexdigest())
s=json.loads((F/'finite-snapshot01.json').read_text());a=s['archives'][0];archive=Path(a['path']);assert pin(archive)=={k:a[k]for k in ['bytes','sha256']}
source=R/'scripts/publish_pcie_native_capture_v4.py';selection=json.loads((F/'snapshot-inputs01.json').read_text());assert pin(source)==selection['files'][str(source)]
closed=json.loads((F/'seal-execution01.json').read_text());assert closed['status']=='PASS_CLOSED_FINITE_RESOURCE_WRAPPER'
assert not(F/'publication-launch01.json').exists()and not(F/'release01.json').exists();assert shutil.disk_usage('/dev/shm').free>=1024**3 and shutil.disk_usage(F).free>=1024**3
cmd=[str(R/'hw/soc/tools/cocotb-venv/bin/python'),str(source),'--tag','evidence-20261006-pcie-closure','--out',str(F/'release01.json'),str(archive)]
env={k:v for k,v in os.environ.items()if k not in ('PYTHONPATH','PYTHONHOME','PYTHONEXECUTABLE','PYTHONOPTIMIZE','LD_PRELOAD','GH_TOKEN','GITHUB_TOKEN')};env.update(PYTHONDONTWRITEBYTECODE='1',OPENBLAS_NUM_THREADS='1',OMP_NUM_THREADS='1')
def limit():
 resource.setrlimit(resource.RLIMIT_AS,(2*1024**3,)*2);resource.setrlimit(resource.RLIMIT_CORE,(0,0));os.sched_setaffinity(0,{10})
with(F.parent/'pcie-570-finite-publication01.log').open('x')as log:p=subprocess.Popen(cmd,cwd=R,stdin=subprocess.DEVNULL,stdout=log,stderr=subprocess.STDOUT,env=env,start_new_session=True,close_fds=True,preexec_fn=limit)
fields=Path('/proc',str(p.pid),'stat').read_text().rsplit(') ',1)[1].split();assert int(fields[2])==p.pid
row=dict(pid=p.pid,start_ticks=fields[19],process_group=fields[2],boot_id=Path('/proc/sys/kernel/random/boot_id').read_text().strip(),command=cmd,archive=pin(archive),source=pin(source),snapshot=pin(F/'finite-snapshot01.json'),CPU=10,AS=2*1024**3)
(F/'publication-launch01.json').write_text(json.dumps(row,indent=2)+'\n');print(json.dumps(row))
