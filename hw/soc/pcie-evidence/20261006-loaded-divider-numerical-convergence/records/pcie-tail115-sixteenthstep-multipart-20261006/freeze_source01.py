# SPDX-FileCopyrightText: 2026 Hasan Melih Akbulut
# SPDX-License-Identifier: Apache-2.0
from pathlib import Path
import ast,hashlib,json,shutil
R=Path.cwd();B=Path(__file__).resolve().parent;N=R/'hw/soc/out/pcie-vco-v6-divider-tail115-v1-sixteenthstep-20261006'
def pin(p):
 with p.open('rb')as f:return dict(bytes=p.stat().st_size,sha256=hashlib.file_digest(f,'sha256').hexdigest())
files={p for p in B.rglob('*')if p.is_file()and'__pycache__'not in p.parts};pending=[R/'scripts/publish_pcie_native_capture_v4.py'];closure=set()
while pending:
 p=pending.pop()
 if p in closure:continue
 closure.add(p)
 for node in ast.walk(ast.parse(p.read_text())):
  names=([x.name for x in node.names]if isinstance(node,ast.Import)else[node.module]if isinstance(node,ast.ImportFrom)and node.module else[])
  for name in names:
   q=R/'scripts'/(name.split('.')[0]+'.py')
   if q.exists():pending.append(q)
files|=closure
files|={R/'hw/soc/tools/cocotb-venv/bin/python',R/'hw/soc/tools/cocotb-venv/pyvenv.cfg',Path(shutil.which('gh')),N/'pcie-vco-v6-divider-tail115-v1-sixteenthstep-06-01.tar.xz',N/'validation-06-01.json',N/'members-06-01.json',N/'release-06-01.json'}
parent=json.loads((N/'source-freeze01.json').read_text())
files|={Path(p)for p in parent['pins']if'/numpy/'in p or'/numpy.libs/'in p}
assert all(p.exists()for p in files)
archive=N/'pcie-vco-v6-divider-tail115-v1-sixteenthstep-06-01.tar.xz'
record=dict(status='FROZEN_IMMUTABLE32MIB_MULTIPART_PUBLICATION_SOURCE_NO_TRANSPORT_STARTED',inputs={str(p):pin(p)for p in sorted(files)},publisher_transitive_project_sources=[str(p)for p in sorted(closure)],original_failed_transport=pin(N/'release-06-01.json'),original_archive=pin(archive),controls=pin(B/'controls01.json'),reconstruction=pin(B/'local-reconstruction01.json'),part_count=24,publisher='Exact V4 byte-bound; unchanged120s per-attempt and ownership. All24 parts plus1 manifest independently authenticated and anonymous byte-roundtrip. No monolithic retry or source mutation.')
(B/'source-freeze01.json').write_text(json.dumps(record,indent=2)+'\n');print(json.dumps(dict(freeze=pin(B/'source-freeze01.json'),inputs=len(files),publisher_sources=len(closure))))
