# SPDX-FileCopyrightText: 2026 Hasan Melih Akbulut
# SPDX-License-Identifier: Apache-2.0
"""Exact prior TX03 saved-output chain adapted to measured TX05, no native run."""
from pathlib import Path
import ast,difflib,hashlib,json
R=Path('/home/hasanmelih/Documents/ChatGPT/nnsoc');B=R/'hw/soc/out/pcie-gen3-transmit-v4-repair-20261005';S=B/'repair05-source';Q=B/'repair05-peer';C=B/'repair05-continuation01'
Q.mkdir();C.mkdir()
def pin(p):
 with p.open('rb') as f:return dict(bytes=p.stat().st_size,sha256=hashlib.file_digest(f,'sha256').hexdigest())
def exact(s,a,b):
 assert s.count(a)==1,(a,s.count(a));return s.replace(a,b)
rows=[]
for parent,new in [(B/'repair03-peer/review.py',Q/'review.py'),(B/'repair03-peer/seal.py',Q/'seal.py'),(B/'repair03-continuation02/run.py',C/'run.py')]:
 before=parent.read_text();s=before.replace('TX03','TX05').replace('tx03','tx05').replace('repair03','repair05').replace('repair-03','repair-05').replace('proof03','proof05')
 s=s.replace('repair05-physical-replay-01','repair05-physical-replay-02')
 if new.name=='review.py':
  s=exact(s,'import resource\n','import resource\nimport sys\n')
  s=exact(s,'O = Path(__file__).resolve().parent\n','O = Path(__file__).resolve().parent\nsys.path.insert(0, str(B))  # Exact proof gate imports reviewed owned_lifecycle05.\n')
  s=exact(s,"nssoc-tx-path-v4-repair02-detailed-rc-02/result.json","nssoc-tx-path-v4-repair03-detailed-rc-01/result.json")
 if new.name=='seal.py':
  s=s.replace('repair05-route-nominal-rc-and-peer-20261005','repair05-route-nominal-rc-and-peer-20261006').replace('repair05-finite-physical-validation-20261005','repair05-finite-physical-validation-20261006')
  s=exact(s,"'replay_repair05.py', 'drt_repair05.py'","'replay_repair05_resume02.py', 'owned_lifecycle05.py', 'drt_repair05.py'")
  s=exact(s,"nssoc-tx-path-v4-repair02-detailed-rc-02'","nssoc-tx-path-v4-repair03-detailed-rc-01'")
  first=s.index("for directory in ['repair05-source', 'repair02-peer']:")
  last=s.index("for name in ['review.py'",first)
  names=['source-freeze.json','source-bridge.json','source-only-peer-rx.json','proof-source-freeze02.json','proof-source-bridge.json','proof-source-only-peer-rx02.json','ports02-source-freeze.json','ports02-source-only-peer-rx.json','route-rc-source-freeze.json','route-rc-source-bridge.json','route-rc-source-only-peer-rx.json','pre-drt-proof-port-review.json','owned_lifecycle05-before02.py','proof-source-review-rx01-findings.json','test_owned_lifecycle05.py','lifecycle-controls02.log','binding-controls02.log','ports-launch01.json','ports-launch01.log','ports-launch02.json','ports-launch02.log']
  replacement='for name in '+repr(names)+":\n    files['preservation/repair05-source/' + name] = B / 'repair05-source' / name\n"
  replacement+="for name in ['review.json','package.json','release.json','pcie-tx-repair03-finite-physical-validation-20261005.json']:\n    files['prior-published/repair03/' + name] = B / 'repair03-peer' / name\n"
  replacement+="for name in ['package.json','validation.json','publication.json']:\n    files['prior-preroute-publication/' + name] = B / 'repair05-preroute-preservation' / name\n"
  s=s[:first]+replacement+s[last:]
  s=exact(s,"['run.py', 'manifest.json', 'source-only-peer-vco.json', 'launch-preflight.json', 'active-controller.json']","['run.py', 'manifest.json', 'source-only-peer-vco.json', 'launch.py', 'launch.json', 'detached-confirmed.json']")
  s=s.replace("Completed TX05 candidate/proof/ports/DRT01/RC01 preserved;","Completed TX05 actual-SPEF-first candidate/proof/ports02/DRT01/RC01 preserved; original ports01 interpreter failure retained;")
 if new.name=='run.py':
  s=s.replace('repair05-continuation-binding-20261005','repair05-continuation-binding-20261006').replace('repair05-finite-physical-validation-20261005','repair05-finite-physical-validation-20261006')
  s=exact(s,'process = owner.launch(kind, command, cwd=ROOT,\n','process = owner.launch(kind, command, cwd=ROOT,\n                                           env={k:v for k,v in os.environ.items() if k not in (\'PYTHONPATH\',\'PYTHONHOME\',\'PYTHONEXECUTABLE\')},\n')
  s=s.replace('own 5s group cleanup.','own 2s group cleanup.')
 ast.parse(s);new.write_text(s)
 oldlines=before.splitlines(True);newlines=s.splitlines(True)
 rows.append(dict(before=dict(path=str(parent),**pin(parent)),after=dict(path=str(new),**pin(new)),opcodes=[dict(tag=t,before=''.join(oldlines[i:j]),after=''.join(newlines[k:l]))for t,i,j,k,l in difflib.SequenceMatcher(None,oldlines,newlines,autojunk=False).get_opcodes()]))
for p,data in [(Q/'source-derivation.json',rows[:2]),(C/'source-bridge.json',rows)]:p.write_text(json.dumps(data,indent=2)+'\n')
freeze=dict(status='FROZEN_TX05_DEPENDENT_BODIES_BEFORE_EXECUTION',sources={str(p):pin(p) for p in [Q/'review.py',Q/'seal.py',C/'run.py']},bridge=pin(C/'source-bridge.json'),scope='Exact prior TX03 reviewer/sealer/continuation; fresh05 paths, ports02 and actual03 prior timing comparator, four timing classes/150 input-only CTS loads unchanged. Import path for reviewed helper, sanitized subprocess env and explicit finite preservation list added. Existing route only observed; native DRT/RC and acceptance gates unchanged.')
(Q/'source-freeze.json').write_text(json.dumps(freeze,indent=2)+'\n')
print(json.dumps(freeze,indent=2))
