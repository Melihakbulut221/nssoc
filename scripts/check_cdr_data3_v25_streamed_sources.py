#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0
"""Require exact original full loaded gates on the actual v25 parent."""
import ast,hashlib,json,re,runpy
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
def check():
    from check_cdr_selector_small_v24_streamed_sources import check as original
    from check_cdr_data3_v25_mim_sources import check as physical
    original();physical()
    for d in json.loads((ROOT/'scripts/cdr-data3-v25-streamed-source-delta.json').read_text())['files']:
        raw=(ROOT/d['baseline_path']).read_bytes()
        assert hashlib.sha256(raw).hexdigest()==d['baseline_sha256']
        text=raw.decode()
        for e in d['edits']:
            assert text.count(e['before'])==e['count']
            text=text.replace(e['before'],e['after'])
        actual=(ROOT/d['candidate_path']).read_bytes()
        assert actual==text.encode() and hashlib.sha256(actual).hexdigest()==d['candidate_sha256']
        assert re.findall(r'[0-9a-f]{64}',raw.decode())==re.findall(r'[0-9a-f]{64}',actual.decode())
    spec=json.loads((ROOT/'docs/evidence/cdr-data3-v25-fullwave-input-20261021.json').read_text())
    assert spec=={'run': 39513890526, 'source_head': '31e3f5df3532f5b9a92c6e730b743835cc737887', 'workflow_path': '.github/workflows/cdr-data3-v25-mim-validation-cloud.yml', 'capture_summary_sha256': '43fe7f46d64ec948d3e77f0b1c38241f310244da33dae710dadd17809898646c'}
    planes=json.loads((ROOT/'docs/evidence/cdr-data3-v25-planes-pass-20261021.json').read_text())
    assert planes['run']==39510628948 and planes['summary_sha256']=='6c95f4da6ac54520c4e7c2ac6b1d1d2fb27fcb6fc026e26bd679b865567280e8'
    assert planes['report']['physical_source']['summary_sha256']=='fc6fa3cfd6545db344a8f2dcd8f03fe49177a24403ff33ff86533f63187309b4'
    assert len(planes['report']['native_planes']['anchors'])==160
    producer=runpy.run_path(str(ROOT/'scripts/cloud_cdr_data3_v25_fullwave_stage.py'),run_name='fullwave_handoff_preflight')
    path=producer['receipt_path']('mim-composition')
    literals={n.value for n in ast.walk(ast.parse((ROOT/'scripts/cloud_cdr_data3_v25_mim_streamed.py').read_text())) if isinstance(n,ast.Constant) and isinstance(n.value,str)}
    assert str(path.relative_to(ROOT)) in literals
    print('PASS_DATA3_V25_FULL_ORIGINAL_LOADED_GATES_AND_EXACT_RECEIPT_HANDOFF')
if __name__=='__main__':check()
