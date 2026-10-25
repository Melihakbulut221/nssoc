# SPDX-FileCopyrightText: 2026 Hasan Melih Akbulut
# SPDX-License-Identifier: Apache-2.0
from pathlib import Path
import hashlib,json,xml.etree.ElementTree as ET
R=Path.cwd();B=Path(__file__).resolve().parent
def pin(p):
 p=Path(p)
 with p.open('rb')as f:return dict(bytes=p.stat().st_size,sha256=hashlib.file_digest(f,'sha256').hexdigest())
p=B/'policy.json';assert pin(p)==dict(bytes=5719,sha256='1d6ca519ff6b785ec5968555f7232bc710a630f8ffcbe74e935112f1765a1b7b');j=json.loads(p.read_text());assert j['pins']=={p:pin(p)for p in j['pins']}
a=(B.parents[1]/'launch02/detach_launch.py').read_text();z=(B/'detach_launch.py').read_text()
for old,new in [('source-peer-vco.json','source-peer-rx01.json'),('PASS_SOURCE_ONLY_DETACHED_PLL_RESTART','PASS_SOURCE_ONLY_DETACHED_PLL_MAXSTEP125'),('nssoc-pll-acquisition-v3-step25-detached-02','nssoc-pll-acquisition-v4-max125-01'),('launch_acquisition25.py','launch_acquisition125.py')]:assert old in a;a=a.replace(old,new)
assert a==z
q=json.loads((B/'offline-prerequisites.json').read_text());assert q['status']=='PASS_OFFLINE_MAXSTEP125_PREREQUISITES'and len(q['inputs'])==3557 and q['devices']==539;assert q['inputs']=={p:pin(p)for p in q['inputs']}
assert q['prerequisites']==pin(B/'prerequisites.json')and q['declaration']==pin(B/'declaration.json')
d=json.loads((B/'declaration.json').read_text());assert d['TSTEP_s']==2.5e-12 and d['first_TMAX_s']==2.5e-12 and d['second_TMAX_s']==1.25e-12 and d['stop_s']==1e-6 and not d['phase_alignment_or_offset_removal']and d['matched_phase_limit_s']==50e-12
x=ET.parse(B.parent/'method-controls03.xml');assert len(x.findall('.//testcase'))==43 and not x.findall('.//failure')and not x.findall('.//error')and not x.findall('.//skipped')
assert not Path('/dev/shm/nssoc-pll-acquisition-v4-max125-01').exists()
r=dict(status='PASS_SOURCE_ONLY_DETACHED_PLL_MAXSTEP125',policy=pin(p),findings=[],method=pin(__file__),exact_detacher_four_substitution_inverse=True,policy_pin_count=len(j['pins']),independently_rehashed_completed_prerequisite_files=len(q['inputs']),saved_controls_recounted=43,scope='Full detacher/preflight bodies read; only source/hash/closed-byte checks executed. No launcher, producer, GH/API, SPICE, signal, or native replay executed. Same PID exec into reviewed V4, sanitized lexical runtime, boot/CPU12/fresh root/method peer/declaration/wholedeck/duplicate producer/headroom gates retained. 400 slots are a launch-time headroom check, not an atomic release reservation. Actual native birth/progress must be verified after dispatch; no convergence/physical pass claim.')
(B/'source-peer-rx01.json').write_text(json.dumps(r,indent=2)+'\n');print(json.dumps(r,indent=2))
