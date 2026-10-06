# SPDX-FileCopyrightText: 2026 Hasan Melih Akbulut
# SPDX-License-Identifier: Apache-2.0
"""Finish a detached launch command; never attach a long job to tool lifetime."""
from pathlib import Path
import hashlib,json,subprocess,os,sys,time
S=Path(__file__).resolve().parent;B=S.parent;R=B.parents[3]
pin=lambda p:dict(bytes=Path(p).stat().st_size,sha256=hashlib.sha256(Path(p).read_bytes()).hexdigest())
version=sys.argv[1];assert version in ['14a','14b']
f=json.loads((S/'targeted-source-freeze.json').read_text());peer=json.loads((S/'targeted-source-only-peer-pll.json').read_text());assert peer['status']=='PASS_SOURCE_ONLY_RX14_TARGETED_GRT_REPORTS' and not peer['findings'];assert peer['freeze']==pin(S/'targeted-source-freeze.json')
row=f['variants'][version];p=Path(row['after']['path']);assert pin(p)=={k:row['after'][k] for k in ['bytes','sha256']};assert not Path(row['new_output']).exists()
if version=='14b':
 prior=S/'active14a-targeted.json';r=json.loads(prior.read_text());q=Path('/proc')/str(r['controller']['pid'])/'stat'
 if q.exists():a=q.read_text().rsplit(') ',1)[1].split();assert a[19]!=r['controller']['start_ticks'] or a[0]=='Z'
 O=Path(r['output']);actual=json.loads((O/'result.json').read_text());assert actual['status']=='COMPLETE_CANDIDATE_REQUIRES_EQUIVALENCE_ROUTE_RC' and actual['returncode']==0
 assert actual['inputs']=={q:pin(q) for q in actual['inputs']};assert actual['outputs']=={n:pin(O/n) for n in actual['outputs']}
command=['taskset','-c','8',str(R/'hw/soc/tools/cocotb-venv/bin/python'),'-u',str(p)]
with (S/('native'+version+'-targeted-launch.log')).open('x') as log:proc=subprocess.Popen(command,cwd=R,stdin=subprocess.DEVNULL,stdout=log,stderr=subprocess.STDOUT,start_new_session=True,env={**os.environ,'PYTHONDONTWRITEBYTECODE':'1'})
time.sleep(.3);assert proc.poll() is None
fields=(Path('/proc')/str(proc.pid)/'stat').read_text().rsplit(') ',1)[1].split()
receipt=dict(status='DETACHED_TARGETED_GRT_RUNNING',controller=dict(pid=proc.pid,start_ticks=fields[19],process_group=int(fields[2])),boot_id=Path('/proc/sys/kernel/random/boot_id').read_text().strip(),command=command,method=pin(__file__),source=pin(p),freeze=pin(S/'targeted-source-freeze.json'),peer=pin(S/'targeted-source-only-peer-pll.json'),output=row['new_output'],no_healthy_elapsed_watchdog=True,CPU=8,child_AS=2684354560)
(S/('active'+version+'-targeted.json')).write_text(json.dumps(receipt,indent=2)+'\n');print(json.dumps(receipt))
