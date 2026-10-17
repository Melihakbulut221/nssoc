# SPDX-FileCopyrightText: 2026 Hasan Melih Akbulut
# SPDX-License-Identifier: Apache-2.0
from pathlib import Path
import json,hashlib
R=Path.cwd();B=Path(__file__).resolve().parent;D=R/'docs/146-pcie-local-pll-capture.md';P=R/'hw/soc/out/pcie-pll-local-spool-v1-20261006/finite01/saved-finite-peer-vco01.json'
def pin(p):
 with p.open('rb')as f:return dict(bytes=p.stat().st_size,sha256=hashlib.file_digest(f,'sha256').hexdigest())
r=json.loads(P.read_text());s=D.read_text();assert r['findings']==[]and r['current_predicates']==69 and r['total_executions']==303 and r['total_historical_failures']==2 and r['readback_members']==3967
assert all('Explicit owned process kind'in f['message']for f in r['historical_failures'])
for text in ['rather than claiming one clean 69-test run','303 executions include 301 passes and','two retained host failures','not empirical\npower-loss tests','Uncommitted bytes still in RAM can be lost','partial waveform data is never a solver checkpoint','not a current or terminal\nstatus claim','no completed\n1 µs acquisition result','The reserve is not a filesystem quota','limits rather than promising unlimited offline operation']:
 assert text in s,text
out=dict(status='PASS_DOC146_SAVED_CONTROL_AND_DURABILITY_SCOPE',findings=[],document=pin(D),independent_saved_peer=pin(P),method=pin(Path(__file__)),verified=['69 composite current predicates distinguished from303 executions and2 retained historical host failures','Invalid owned-process-kind diagnostic accurately retained','Commit durability bounded by local storage and explicit failure handling; uncommitted RAM loss and no empirical power-loss qualification explicit','Immutable launch snapshot not treated as terminal status; ongoing PLL native/publication excluded','No completed1us acquisition, convergence or physical acceptance claimed'],scope='Narrative-scope read against already independently recounted closed archive. RX owns full source/publication/doc factual binding. No archive repeat, native or network read, test rerun or document edit.')
(B/'doc146-scope-peer-vco01.json').write_text(json.dumps(out,indent=2)+'\n');print(pin(B/'doc146-scope-peer-vco01.json'))
