#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0
import ast,hashlib,json,re,runpy
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
def check():
    from check_cdr_selector_small_v24_streamed_sources import check as original
    from check_cdr_gain_headroom_v29_mim_sources import check as physical
    original();physical()
    for d in json.loads((ROOT/'scripts/cdr-gain-headroom-v29-streamed-source-delta.json').read_text())['files']:
        raw=(ROOT/d['baseline_path']).read_bytes()
        assert hashlib.sha256(raw).hexdigest()==d['baseline_sha256']
        text=raw.decode()
        for e in d['edits']:
            assert text.count(e['before'])==e['count']
            text=text.replace(e['before'],e['after'])
        actual=(ROOT/d['candidate_path']).read_bytes()
        assert actual==text.encode() and hashlib.sha256(actual).hexdigest()==d['candidate_sha256']
        assert re.findall(r'[0-9a-f]{64}',raw.decode())==re.findall(r'[0-9a-f]{64}',actual.decode())
    spec=json.loads((ROOT/'docs/evidence/cdr-gain-headroom-v29-fullwave-input-20261022.json').read_text())
    assert spec=={'run': 39694882029, 'source_head': '2e789a549370f07ee5a7df5fde34460f990c095a', 'workflow_path': '.github/workflows/cdr-gain-headroom-v29-mim-validation-cloud.yml', 'capture_summary_sha256': 'ccfe6913daa977fe9de26cb413c993e408ba38ab53430cd6a24e74b3065da1a8'}
    planes=json.loads((ROOT/'docs/evidence/cdr-gain-headroom-v29-planes-pass-20261022.json').read_text())
    assert planes['run']==39693048851 and planes['summary_sha256']=='3b9a84eac7a0b117c895a624baad137958617e0a14e74031865abf08c1336259'
    assert planes['report']['physical_source']['summary_sha256']=='5e7ab07191831d3f378a7719d355cacc591f76553d5302ce10b53cad21788b6f'
    assert len(planes['report']['native_planes']['anchors'])==160
    producer=runpy.run_path(str(ROOT/'scripts/cloud_cdr_gain_headroom_v29_fullwave_stage.py'),run_name='fullwave_handoff_preflight')
    path=producer['receipt_path']('mim-composition')
    literals={n.value for n in ast.walk(ast.parse((ROOT/'scripts/cloud_cdr_gain_headroom_v29_mim_streamed.py').read_text()))if isinstance(n,ast.Constant)and isinstance(n.value,str)}
    assert str(path.relative_to(ROOT))in literals
    print('PASS_GAIN_HEADROOM_V29_FULL_ORIGINAL_LOADED_GATES_AND_EXACT_RECEIPT_HANDOFF')
if __name__=='__main__':check()
