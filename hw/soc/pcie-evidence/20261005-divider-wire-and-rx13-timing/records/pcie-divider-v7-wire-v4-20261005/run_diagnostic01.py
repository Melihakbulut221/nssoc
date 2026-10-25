# SPDX-FileCopyrightText: 2026 Hasan Melih Akbulut
# SPDX-License-Identifier: Apache-2.0
"""Owned saved-GDS diagnostic; original assertion failure is not bypassed."""
import ast,hashlib,json,os,resource,shutil,signal,subprocess,threading,time
from pathlib import Path
B=Path(__file__).resolve().parent;R=B.parents[3]
def pin(p):
 with Path(p).open('rb') as f:return dict(bytes=Path(p).stat().st_size,sha256=hashlib.file_digest(f,'sha256').hexdigest())
checker=R/'hw/soc/flow/check_pcie_clock_div4_v7_v2.py'
assert pin(checker)['sha256']=='24c89628c6d61226344214e077b5fa535c5570e4a7853fbd109e8cb1b1fcd163'
freeze=json.loads((B/'geometry-source-freeze.json').read_text());assert freeze['inputs']=={p:pin(p) for p in freeze['inputs']}
source=json.loads((B/'diagnostic01-source.json').read_text());assert source['diagnostic']==pin(B/'diagnose_wire_census.py')
names={'require','atomic','lifecycle','limits','scratch_bytes','guard_resources','execute'}
selected=[n for n in ast.parse(checker.read_text()).body if isinstance(n,ast.FunctionDef) and n.name in names];assert len(selected)==7
ns=dict(__file__=str(checker),os=os,Path=Path,resource=resource,shutil=shutil,signal=signal,subprocess=subprocess,threading=threading,time=time,ast=ast,json=json,digest=lambda p:pin(p)['sha256'],LIFECYCLE_SOURCE='scripts/characterize_pcie_clock_trim_stream_v2.py',LIFECYCLE_SHA='39312e364fa2a788784d88f3a63845f64db25bb420e2ee5d58c07a8c805bc886',SCRATCH_LIMIT=80*1024**2,SHARED_FLOOR=512*1024**2,ENTRY_FREE=1024**3,LAUNCH_RESERVATION=24*1024**2,SCRATCH_ROOTS=(B,Path('/dev/shm/nssoc-div4-v7-wire-geometry-diagnostic01')),CPU=10)
exec(compile(ast.Module(selected,[]),str(checker),'exec'),ns)
r=ns['execute']([R/'hw/soc/tools/physical/librelane-3.0.5-x86_64.AppImage','python',B/'diagnose_wire_census.py'],B,'diagnostic01')
out=B/'diagnostic01-execution.json';assert not out.exists();ns['atomic'](out,dict(status='OBSERVED_DIAGNOSTIC_ONLY_NO_GEOMETRY_ACCEPTANCE',execution=r,source=source,method=pin(__file__),original_inputs_unchanged=freeze['inputs']=={p:pin(p) for p in freeze['inputs']}));print(json.dumps(r))
