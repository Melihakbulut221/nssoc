# SPDX-FileCopyrightText: 2026 Hasan Melih Akbulut
# SPDX-License-Identifier: Apache-2.0
"""Preserve narrow two-parent derivation for actual-SPEF-first RX repair."""
from pathlib import Path
import ast,difflib,hashlib,json
R=Path.cwd();B=R/'hw/soc/out/pcie-gen3-receive-prefetch-v2-20261004';S=B/'repair16-source';T=R/'hw/soc/out/pcie-gen3-transmit-v4-repair-20261005'
def pin(p):
 p=Path(p)
 with p.open('rb') as f:return dict(bytes=p.stat().st_size,sha256=hashlib.file_digest(f,'sha256').hexdigest())
a=(B/'postroute_repair15_v3.py').read_text();tx=(T/'postroute_repair05.py').read_text()
z=a.replace('postroute-repair-15-v3','postroute-repair-16-mixed-01').replace('RX15V3','RX16MIXED').replace('-setup_margin 0.60','-setup_margin 0.25')
start=tx.index('# Keep the initialized global-route topology');end=tx.index('# Optimization margins',start)
block=tx[start:end].replace('TX05','RX16MIXED').replace('-0.601762','-0.402478')
z=z.replace('# Optimization margins',block+'# Optimization margins',1)
z=z.replace("    final_log = log.split", "    assert 'EXACT_ACTUAL_BASELINE_RC_RESTORED_BEFORE_REPAIR' in log\n    final_log = log.split",1)
z=z.replace('Fresh broad RX16MIXED setup/hold candidate from exact closed RX14A; GRT estimates only.','Actual-SPEF-first RX16 mixed-RC experiment from exact closed RX14A.')
z=z.replace('fresh global route estimates then setup sequence clone,sizeup,buffer,split allTNS/0.60ns margin with final fresh full GRT and guarded hold0.05ns','fresh GRT topology then reload exact baseline SPEF/assert actual WNS before setup sequence clone,sizeup,buffer,split allTNS/0.25ns and guarded hold0.05ns; modified nets may use estimates; final fresh fullGRT')
z=z.replace('GRT estimates only; new graph proof','Mixed-RC optimization and final GRT estimates only; new graph proof')
files=[T/'postroute_repair05.py',T/'repair05-source/source-only-peer-rx.json',Path('/dev/shm/nssoc-tx-path-v4-postroute-repair-05/result.json'),B/'repair15-source/explicit-rejection-review.json',B/'repair15-source/broad-v3-rejection-review.json']
basis={str(p):pin(p) for p in files}
z=z.replace('inputs.update(MARGIN_BASIS)','inputs.update(MARGIN_BASIS)\nMIXED_RC_BASIS = '+repr(basis)+'\nassert MIXED_RC_BASIS == {p: pin(p) for p in MIXED_RC_BASIS}\ninputs.update(MIXED_RC_BASIS)')
for n in ('pin','interrupted','limits','identity','report','save'):
 def function(s):return ast.dump(next(x for x in ast.parse(s).body if isinstance(x,ast.FunctionDef) and x.name==n),include_attributes=False)
 assert function(a)==function(z),n
out=B/'postroute_repair16_mixed.py';assert not out.exists();ast.parse(z);out.write_text(z)
bridge=S/'source-bridge.json';bridge.write_text(json.dumps(dict(before=dict(path=str(B/'postroute_repair15_v3.py'),**pin(B/'postroute_repair15_v3.py')),after=dict(path=str(out),**pin(out)),opcodes=[dict(tag=t,before=a[i:j],after=z[k:l]) for t,i,j,k,l in difflib.SequenceMatcher(None,a,z,autojunk=False).get_opcodes()],actual_SPEF_block=dict(parent=dict(path=str(T/'postroute_repair05.py'),**pin(T/'postroute_repair05.py')),before=tx[start:end],after=block,inverse='RX16MIXED→TX05 and -0.402478→-0.601762 only')),indent=2)+'\n')
paths=[out,bridge,Path(__file__),B/'postroute_repair15_v3.py',B/'repair15-source/broad-candidate-v3-source-only-peer-vco.json',*files]
f=dict(status='FROZEN_RX16_MIXED_RC_CANDIDATE_BEFORE_NATIVE',candidate=str(out),sources={str(p):pin(p) for p in paths},scope='Original RX14A exact actual SPEF reloaded after initializing GRT. Before repair must reproduce SS WNS -0.402478. Same original4ns/IO/hold0.05, setup optimization margin0.25. All6 inherited functions/cleanup unchanged. Modified nets may use estimates; final fresh fullGRT/no missing routes/exact netlist. New proof+10faults+6ports+actualDRT/RC still mandatory.')
(S/'source-freeze.json').write_text(json.dumps(f,indent=2)+'\n');print(json.dumps(f,indent=2))
