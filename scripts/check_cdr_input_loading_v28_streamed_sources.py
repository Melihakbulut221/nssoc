#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0
import ast,hashlib,json,re,runpy
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
def check():
    from check_cdr_selector_small_v24_streamed_sources import check as original
    from check_cdr_input_loading_v28_mim_sources import check as physical
    original();physical()
    for d in json.loads((ROOT/'scripts/cdr-input-loading-v28-streamed-source-delta.json').read_text())['files']:
        raw=(ROOT/d['baseline_path']).read_bytes()
        assert hashlib.sha256(raw).hexdigest()==d['baseline_sha256']
        text=raw.decode()
        for e in d['edits']:
            assert text.count(e['before'])==e['count']
            text=text.replace(e['before'],e['after'])
        actual=(ROOT/d['candidate_path']).read_bytes()
        assert actual==text.encode() and hashlib.sha256(actual).hexdigest()==d['candidate_sha256']
        assert re.findall(r'[0-9a-f]{64}',raw.decode())==re.findall(r'[0-9a-f]{64}',actual.decode())
    spec=json.loads((ROOT/'docs/evidence/cdr-input-loading-v28-fullwave-input-20261021.json').read_text())
    assert spec=={'run': 39562157915, 'source_head': '0f39a9fdcc2a848fb00048a5d5d14231e7fab99a', 'workflow_path': '.github/workflows/cdr-input-loading-v28-mim-validation-cloud.yml', 'capture_summary_sha256': 'd830a3e6ba3e0959a2e9382717afd3dd960eb0c43118284b0af183135a1186f2'}
    planes=json.loads((ROOT/'docs/evidence/cdr-input-loading-v28-planes-pass-20261021.json').read_text())
    assert planes['run']==39559188023 and planes['summary_sha256']=='6c9b1811733caaa9d19f11723fa7c194d28fed4150ad483729a6af99485e2adc'
    assert planes['report']['physical_source']['summary_sha256']=='5407a43497d9a65716c57a19db43e7130d94827034ea58ecf44de1d98e04cdb6'
    assert len(planes['report']['native_planes']['anchors'])==160
    producer=runpy.run_path(str(ROOT/'scripts/cloud_cdr_input_loading_v28_fullwave_stage.py'),run_name='fullwave_handoff_preflight')
    path=producer['receipt_path']('mim-composition')
    literals={n.value for n in ast.walk(ast.parse((ROOT/'scripts/cloud_cdr_input_loading_v28_mim_streamed.py').read_text()))if isinstance(n,ast.Constant)and isinstance(n.value,str)}
    assert str(path.relative_to(ROOT))in literals
    print('PASS_INPUT_LOADING_V28_FULL_ORIGINAL_LOADED_GATES_AND_EXACT_RECEIPT_HANDOFF')
if __name__=='__main__':check()
