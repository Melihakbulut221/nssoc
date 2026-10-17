# SPDX-FileCopyrightText: 2026 Hasan Melih Akbulut
# SPDX-License-Identifier: Apache-2.0
from pathlib import Path
import ast,hashlib,json
B=Path(__file__).resolve().parent
cache={}
def pin(p):
 p=Path(p);s=p.stat();k=(str(p),s.st_size,s.st_mtime_ns)
 if k not in cache:
  with p.open('rb') as f:cache[k]=dict(bytes=s.st_size,sha256=hashlib.file_digest(f,'sha256').hexdigest())
 return cache[k]
fpath=B/'source-freeze.json';assert pin(fpath)==dict(bytes=228971,sha256='a87ac3c4f8778d67f86a7d556f4afd7e61d70d12447882ff4c83fd5396b9985c');f=json.loads(fpath.read_text());assert len(f['inputs'])==995 and f['inputs']=={p:pin(p) for p in f['inputs']}
br=json.loads((B/'source-bridge.json').read_text());a=Path(br['parent']);z=Path(br['new']);assert pin(a)==br['parent_pin'] and pin(z)==br['new_pin']
assert z.read_text().replace('nssoc-div4-v7-compact-v2-layout-01','nssoc-div4-v7-power-v2-layout-01').replace('nssoc-div4-v7-compact-v2-binding-controls-01','nssoc-div4-v7-power-v2-binding-controls-01')==a.read_text();ast.parse(z.read_text())
g=json.loads((B.parent/'geometry-execution.json').read_text());assert g['status']=='PASS_DIVIDER_V7_SAVED_NATIVE_GEOMETRY_AND_SOURCE_BIJECTION_ONLY';assert g['outputs']=={p:pin(p) for p in g['outputs']}
assert [r['name'] for r in g['steps']]==['native_unsimplified_extraction','probe_native_cells','probe_device_locations','probe_wire_components','probe_terminal_anchors','prepare_anchors','bind_source_ids'] and all(r['execution']['returncode']==0 for r in g['steps'])
assert not Path('/dev/shm/nssoc-div4-v7-compact-v2-binding-controls-01').exists()
r=dict(status='PASS_SOURCE_ONLY_DIVIDER_V7_BINDING_CONTROLS',freeze=pin(fpath),findings=[],method=pin(__file__),source=pin(z),parent=pin(a),all_input_pins_rehashed=len(f['inputs']),exact_inverse='Only compact G and fresh fixture T roots, including the exact copied-production-source G replacement literal.',positive_geometry=pin(B.parent/'geometry-execution.json'),checks=['One positive and four precisely counted one-edit copied-input negatives remain identical.','Production binder source is byte-inverse exact except per-case fixtureGroot; actual source/layout/native files stay immutable.','Positive entire graph equality except provenance; negatives require correct specific assertion and no output, not any generic failure.','Original CPU10/2GiB/scratch80MiB/reserve24MiB/entry1GiB/floor512MiB/owned native groups and nohealthytimeout unchanged.'],scope='Source-only and completed geometry input/output rehash. No binder/control/native execution; five actual runs remain pending.')
p=B/'source-only-peer-rx.json';assert not p.exists();p.write_text(json.dumps(r,indent=2)+'\n');print(json.dumps(dict(path=str(p),**pin(p))))
