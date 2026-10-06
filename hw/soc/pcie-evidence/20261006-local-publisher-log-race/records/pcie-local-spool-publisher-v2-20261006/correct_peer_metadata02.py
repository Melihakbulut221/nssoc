# SPDX-FileCopyrightText: 2026 Hasan Melih Akbulut
# SPDX-License-Identifier: Apache-2.0
"""Additive reviewer-metadata correction; no worker, tests or graph execution."""
from pathlib import Path
import ast,hashlib,json
B=Path(__file__).resolve().parent;R=Path.cwd()
def pin(p):
 p=Path(p)
 with p.open('rb')as f:return dict(bytes=p.stat().st_size,sha256=hashlib.file_digest(f,'sha256').hexdigest())
p=B/'source-saved-peer-vco01.json';assert pin(p)==dict(bytes=13775,sha256='43658da84d4c1269c0035d24fb755f30a55853a9bd0f2ccff07efcb0e3709e96');r=json.loads(p.read_text());assert r['unchanged_worker_functions']==['asset','receipt','receipt_pin','row']
old=R/'scripts/publish_pcie_local_spool_v1.py';new=R/'scripts/publish_pcie_local_spool_v2.py';a={x.name:x for x in ast.parse(old.read_text()).body if isinstance(x,ast.FunctionDef)};b={x.name:x for x in ast.parse(new.read_text()).body if isinstance(x,ast.FunctionDef)}
names=sorted(set(a)-{'guard'});assert all(ast.dump(a[name])==ast.dump(b[name])for name in names)
r['unchanged_worker_functions']=names;r['reviewer_metadata_correction']=dict(original_peer=pin(p),original_method=pin(B/'review_source_saved_vco01.py'),correction_method=pin(__file__),reason='Reader variable a initially held original-function dictionary, then was reused for saved asset rows after the whole-byte/AST checks. Only the reported function-name list was wrong; exact byte bridge, actual checks, pins, control recount and gate verdict remain unchanged.',original_peer_and_method_preserved=True,launcher_gate_unchanged=True)
q=B/'source-saved-peer-vco02.json';assert not q.exists();q.write_text(json.dumps(r,indent=2)+'\n');print(json.dumps(dict(receipt=pin(q),unchanged_functions=names)))
