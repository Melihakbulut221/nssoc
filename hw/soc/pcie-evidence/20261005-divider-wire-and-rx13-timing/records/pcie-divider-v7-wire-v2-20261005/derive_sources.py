# SPDX-FileCopyrightText: 2026 Hasan Melih Akbulut
# SPDX-License-Identifier: Apache-2.0
"""Preserve first failure; distinguish actual via leaves from electrical devices."""
from pathlib import Path
import difflib
import hashlib
import json

B=Path(__file__).resolve().parent
OLD=B.parent/'pcie-divider-v7-wire-v1-20261005'


def pin(path):
    with Path(path).open('rb') as f:
        return dict(bytes=Path(path).stat().st_size,sha256=hashlib.file_digest(f,'sha256').hexdigest())


original=json.loads((OLD/'geometry-source-freeze.json').read_text())
assert original['inputs']=={p:pin(p) for p in original['inputs']}
assert json.loads((OLD/'geometry-execution.json').read_text())['status']=='FAIL_GEOMETRY_RETAINED'
diagnostic=json.loads((OLD/'native-pcell-inventory-diagnostic.json').read_text())
from collections import Counter
assert Counter(x['cell'].split('$')[0] for x in diagnostic)==dict(npn13G2=34,rppd=33,cmim=6,ptap1=18,via_stack=587)
bridges=[]
for path in original['producer_sources']:
    source=Path(path);target=B/source.name
    before=source.read_text()
    after=before.replace('/dev/shm/nssoc-div4-v7-wire-geometry-01','/dev/shm/nssoc-div4-v7-wire-geometry-02')
    if source.name=='probe_native_cells.py':
        after=after.replace('assert len(rows)==91','assert len(rows)==678')
        after=after.replace('dict(npn13G2=34,rppd=33,cmim=6,ptap1=18)','dict(npn13G2=34,rppd=33,cmim=6,ptap1=18,via_stack=587)')
    if source.name=='probe_device_locations.py':
        after=after.replace('assert len(leaves)==len(source)==91','assert len(leaves)==91 and len(source)==678\nassert Counter(r[\'cell\'].split(\'$\')[0] for r in source)==dict(npn13G2=34,rppd=33,cmim=6,ptap1=18,via_stack=587)')
    assert not target.exists();target.write_text(after)
    a,z=before.splitlines(True),after.splitlines(True)
    ops=[dict(tag=t,before=''.join(a[i:j]),after=''.join(z[k:l])) for t,i,j,k,l in difflib.SequenceMatcher(None,a,z,autojunk=False).get_opcodes()]
    assert ''.join(x['before'] for x in ops)==before and ''.join(x['after'] for x in ops)==after
    bridges.append(dict(before=dict(path=str(source),**pin(source)),after=dict(path=str(target),**pin(target)),opcodes=ops))
bp=B/'geometry-source-bridge.json';bp.write_text(json.dumps(bridges,indent=2)+'\n')
inputs={p:h for p,h in original['inputs'].items() if not Path(p).is_relative_to(OLD)}
inputs.update({str(p):pin(p) for p in [*(B/Path(p).name for p in original['producer_sources']),Path(__file__),bp,OLD/'geometry-source-freeze.json',OLD/'geometry-execution.json',OLD/'geometry-source-only-peer.json',OLD/'diagnostic01-source.json',OLD/'diagnostic01-execution.json',OLD/'native-pcell-inventory-diagnostic.json']})
r=dict(status='FROZEN_SOURCE_ONLY_DIVIDER_V7_WIRE_GEOMETRY_V2_NO_NATIVE_EXECUTION',inputs=inputs,producer_sources={str(B/Path(p).name):pin(B/Path(p).name) for p in original['producer_sources']},source_expected_census=original['source_expected_census'],actual_prior_hierarchy_census=dict(total_leaf_instances=678,electrical_instances=91,via_stack_instances=587),unmeasured_predicted_empty_layers=[134,133],scope='Exact first hierarchy diagnostic retained. Only total leaf census/electrical filtering fixed, with explicit587via leaves accounted; all actual recursive metal/via union geometry and91electrical devices unchanged. All37conductors/38nets and complete91device quantities/location/terminal bijection remain native requirements, not source-predicted acceptance. No RC extraction or qualification.')
out=B/'geometry-source-freeze.json';out.write_text(json.dumps(r,indent=2)+'\n');print(json.dumps(dict(path=str(out),**pin(out),sources=len(r['producer_sources']),inputs=len(inputs))))
