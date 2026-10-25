# SPDX-FileCopyrightText: 2026 Hasan Melih Akbulut
# SPDX-License-Identifier: Apache-2.0
from pathlib import Path
import ast,difflib,hashlib,json
S=Path(__file__).resolve().parent;B=S.parent;Q=B/'repair16one-peer';C=B/'repair16one-continuation01';Q.mkdir(exist_ok=False);C.mkdir(exist_ok=False)
def pin(p):return {'bytes':p.stat().st_size,'sha256':hashlib.sha256(p.read_bytes()).hexdigest()}
bridges=[]
for old,new in [(B/'repair14a-peer/review.py',Q/'review.py'),(B/'repair14a-peer/seal.py',Q/'seal.py'),(B/'repair14a-continuation01/run.py',C/'run.py')]:
 a=old.read_text();z=a.replace('repair14a','repair16one').replace('RX14A','RX16ONE').replace('rx14a','rx16one').replace('nssoc-rx-prefetch-v2-postroute-repair-14a','nssoc-rx-prefetch-v2-postroute-repair-16-one-repair-04').replace('postroute_repair16one.py','postroute_repair16_one04.py').replace('repair14-source','repair16-source').replace('20261005.tar.xz','20261006.tar.xz').replace('repair16one-finite-physical-validation-20261005','repair16one-finite-physical-validation-20261006').replace('repair16one-continuation-binding-20261005','repair16one-continuation-binding-20261006')
 if new.name=='review.py':
  z=z.replace('import resource\n','import resource\nimport sys\n').replace('O = Path(__file__).resolve().parent','sys.path.insert(0, str(B))\nO = Path(__file__).resolve().parent')
  z=z.replace("old = B / 'repair13-peer/review.json'","old = B / 'repair14a-peer/review.json'").replace('SS_setup_improvement_vs13_ns','SS_setup_improvement_vs14a_ns')
 elif new.name=='seal.py':
  z=z.replace('SS_setup_improvement_vs_published13_ns','SS_setup_improvement_vs_published14a_ns').replace('SS_setup_improvement_vs13_ns','SS_setup_improvement_vs14a_ns')
  z=z.replace("'detailed_rc_repair16one.py', 'newtool", "'detailed_rc_repair16one.py', 'owned_lifecycle16.py', 'newtool")
  z=z.replace("pcie-rx-repair13-finite-physical-validation-20261005.json","pcie-rx-repair14a-finite-physical-validation-20261005.json").replace("prior-published/repair13/","prior-published/repair14a/").replace("B / 'repair13-peer'","B / 'repair14a-peer'").replace('Earlier routed13 inputs','Earlier routed14a inputs')
  # Only finite selected proof/route methods: avoid capturing live route/RC logs/status.
  astart=z.index("for p in sorted((B / 'repair16-source').glob('*')):");aend=z.index("# Controller's live status",astart)
  z=z[:astart]+"for name in ['source-freeze04.json','source-only-peer04-vco.json','one04-rejection-review.json','route-trial-selection16one.json','proof-source-freeze16one.json','proof-source-bridge16one.json','proof-source-only-peer-root16one.json','launcher-source-only-peer-root16one.json','run_proof_ports16one.py','proof16one-lifecycle-control.json','route-rc-source-freeze16one.json','route-rc-source-bridge16one.json','pre-drt-proof-port-review16one.json']:\n    files['preservation/repair16-source/' + name] = B / 'repair16-source' / name\n"+z[aend:]
 else:
  z=z.replace("PEER / 'review.log')", "PEER / 'review.log')")
  z=z.replace("process = owner.launch(kind, command, cwd=ROOT,","process = owner.launch(kind, command, cwd=ROOT,\n                                           env={k:v for k,v in os.environ.items() if k not in ('PYTHONPATH','PYTHONHOME','PYTHONEXECUTABLE')},")
 ast.parse(z);new.write_text(z)
 al=a.splitlines(True);zl=z.splitlines(True);ops=[dict(tag=t,before=''.join(al[i:j]),after=''.join(zl[k:l]))for t,i,j,k,l in difflib.SequenceMatcher(None,al,zl,autojunk=False).get_opcodes()]
 assert ''.join(x['before']for x in ops)==a and ''.join(x['after']for x in ops)==z
 bridges.append(dict(before={'path':str(old),**pin(old)},after={'path':str(new),**pin(new)},opcodes=ops))
(Q/'source-bridge.json').write_text(json.dumps(bridges[:2],indent=2)+'\n');(C/'source-bridge.json').write_text(json.dumps(bridges,indent=2)+'\n')
f=dict(status='FROZEN_RX16ONE_SAVED_OUTPUT_REVIEW_AND_SEAL_BEFORE_DRT',sources={str(p):pin(p)for p in [Q/'review.py',Q/'seal.py',C/'run.py']},bridge=pin(C/'source-bridge.json'),scope='Exact priorreview/seal/controller with fresh16one paths and published14a comparator. Canonical78CTS dummy loads unchanged; sourcehelper import path added, finite selected source list excludes live current route/RC logs. Controller child environment sanitized. Actual route identity/manifest to be bound after independent DRT launch.')
(Q/'source-freeze.json').write_text(json.dumps(f,indent=2)+'\n');print(json.dumps(f,indent=2))
