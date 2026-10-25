#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0
import ast,hashlib,json,re,runpy
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
def check():
    from check_cdr_selector_small_v24_streamed_sources import check as original
    from check_cdr_input_impedance_v30_mim_sources import check as physical
    original();physical()
    for d in json.loads((ROOT/'scripts/cdr-input-impedance-v30-streamed-source-delta.json').read_text())['files']:
        raw=(ROOT/d['baseline_path']).read_bytes()
        assert hashlib.sha256(raw).hexdigest()==d['baseline_sha256']
        text=raw.decode()
        for e in d['edits']:
            assert text.count(e['before'])==e['count']
            text=text.replace(e['before'],e['after'])
        actual=(ROOT/d['candidate_path']).read_bytes()
        assert actual==text.encode() and hashlib.sha256(actual).hexdigest()==d['candidate_sha256']
        assert re.findall(r'[0-9a-f]{64}',raw.decode())==re.findall(r'[0-9a-f]{64}',actual.decode())
    spec=json.loads((ROOT/'docs/evidence/cdr-input-impedance-v30-fullwave-input-20261022.json').read_text())
    assert spec=={'run': 39708600220, 'source_head': 'e20a8aa2da383cfeffaf8662c173923e87d12366', 'workflow_path': '.github/workflows/cdr-input-impedance-v30-mim-validation-cloud.yml', 'capture_summary_sha256': '260420a91547b8b245e6f7bca362e52991a11669f45f42d48801b1a2f8ea6a51'}
    planes=json.loads((ROOT/'docs/evidence/cdr-input-impedance-v30-planes-pass-20261022.json').read_text())
    assert planes['run']==39707446970 and planes['summary_sha256']=='5af71c91e0fd1942d65fec65d728c89eec72531e2decce087dc1a208d082d799'
    assert planes['report']['physical_source']['summary_sha256']=='c73830e98e87cbee1d1287c658dd29504e6a04275067b90bea7bd6dfbb4e9ae6'
    assert len(planes['report']['native_planes']['anchors'])==160
    producer=runpy.run_path(str(ROOT/'scripts/cloud_cdr_input_impedance_v30_fullwave_stage.py'),run_name='fullwave_handoff_preflight')
    path=producer['receipt_path']('mim-composition')
    literals={n.value for n in ast.walk(ast.parse((ROOT/'scripts/cloud_cdr_input_impedance_v30_mim_streamed.py').read_text()))if isinstance(n,ast.Constant)and isinstance(n.value,str)}
    assert str(path.relative_to(ROOT))in literals
    print('PASS_INPUT_IMPEDANCE_V30_FULL_ORIGINAL_LOADED_GATES_AND_EXACT_RECEIPT_HANDOFF')
if __name__=='__main__':check()
