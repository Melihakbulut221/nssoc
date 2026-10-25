#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0
import ast,hashlib,json,re,runpy
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
def check():
    from check_cdr_selector_small_v24_streamed_sources import check as original
    from check_cdr_bias_access_v27_mim_sources import check as physical
    original();physical()
    for d in json.loads((ROOT/'scripts/cdr-bias-access-v27-streamed-source-delta.json').read_text())['files']:
        raw=(ROOT/d['baseline_path']).read_bytes()
        assert hashlib.sha256(raw).hexdigest()==d['baseline_sha256']
        text=raw.decode()
        for e in d['edits']:
            assert text.count(e['before'])==e['count']
            text=text.replace(e['before'],e['after'])
        actual=(ROOT/d['candidate_path']).read_bytes()
        assert actual==text.encode() and hashlib.sha256(actual).hexdigest()==d['candidate_sha256']
        assert re.findall(r'[0-9a-f]{64}',raw.decode())==re.findall(r'[0-9a-f]{64}',actual.decode())
    spec=json.loads((ROOT/'docs/evidence/cdr-bias-access-v27-fullwave-input-20261021.json').read_text())
    assert spec=={'run': 39548204907, 'source_head': 'b2a19223457398361ad61c51bd2c72fb44327f67', 'workflow_path': '.github/workflows/cdr-bias-access-v27-mim-validation-cloud.yml', 'capture_summary_sha256': 'af4e99efb0dfe42510302a84951a97bccfd88ddf6afc8f67883614038693de0f'}
    planes=json.loads((ROOT/'docs/evidence/cdr-bias-access-v27-planes-pass-20261021.json').read_text())
    assert planes['run']==39547338459 and planes['summary_sha256']=='8de1922742ab3a2d81aaed1bb034fc575268e269452979f1d7630169d9698f82'
    assert planes['report']['physical_source']['summary_sha256']=='bb26caca65c86d6f14c4e62a7a226eaa5e32e68e43c48aeeafa87e854a433ac8'
    assert len(planes['report']['native_planes']['anchors'])==160
    producer=runpy.run_path(str(ROOT/'scripts/cloud_cdr_bias_access_v27_fullwave_stage.py'),run_name='fullwave_handoff_preflight')
    path=producer['receipt_path']('mim-composition')
    literals={n.value for n in ast.walk(ast.parse((ROOT/'scripts/cloud_cdr_bias_access_v27_mim_streamed.py').read_text()))if isinstance(n,ast.Constant)and isinstance(n.value,str)}
    assert str(path.relative_to(ROOT))in literals
    print('PASS_BIAS_ACCESS_V27_FULL_ORIGINAL_LOADED_GATES_AND_EXACT_RECEIPT_HANDOFF')
if __name__=='__main__':check()
