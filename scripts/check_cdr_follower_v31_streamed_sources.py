#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0
import ast,hashlib,json,re,runpy
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
def check():
    from check_cdr_input_impedance_v30_streamed_sources import check as original
    from check_cdr_follower_v31_mim_sources import check as physical
    original();physical()
    for d in json.loads((ROOT/'scripts/cdr-follower-v31-streamed-source-delta.json').read_text())['files']:
        raw=(ROOT/d['baseline_path']).read_bytes()
        assert hashlib.sha256(raw).hexdigest()==d['baseline_sha256']
        text=raw.decode()
        for e in d['edits']:
            assert text.count(e['before'])==e['count']
            text=text.replace(e['before'],e['after'])
        actual=(ROOT/d['candidate_path']).read_bytes()
        assert actual==text.encode() and hashlib.sha256(actual).hexdigest()==d['candidate_sha256']
        assert re.findall(r'[0-9a-f]{64}',raw.decode())==re.findall(r'[0-9a-f]{64}',actual.decode())
    spec=json.loads((ROOT/'docs/evidence/cdr-follower-v31-fullwave-input-20261022.json').read_text())
    assert spec=={'run': 39721805172, 'source_head': 'd63e597c03d297a6f566907ecc6514c1103c0903', 'workflow_path': '.github/workflows/cdr-follower-v31-mim-validation-cloud.yml', 'capture_summary_sha256': '30f3aeea746835dd56dea6edb6c826c16dfcb99cf0bba71855f02c7e2c490851'}
    planes=json.loads((ROOT/'docs/evidence/cdr-follower-v31-planes-pass-20261022.json').read_text())
    assert planes['run']==39720055542 and planes['summary_sha256']=='f253446a15d10b075cbbe8add43e7e4e4a3a1eb8d68638e2a37b3009a501062a'
    assert planes['report']['physical_source']['summary_sha256']=='e197afa755eda54ab91f8153ab786eb0b2e5f559f73a7871c7ee7f099aa2545f'
    assert len(planes['report']['native_planes']['anchors'])==160
    producer=runpy.run_path(str(ROOT/'scripts/cloud_cdr_follower_v31_fullwave_stage.py'),run_name='fullwave_handoff_preflight')
    path=producer['receipt_path']('mim-composition')
    literals={n.value for n in ast.walk(ast.parse((ROOT/'scripts/cloud_cdr_follower_v31_mim_streamed.py').read_text()))if isinstance(n,ast.Constant)and isinstance(n.value,str)}
    assert str(path.relative_to(ROOT))in literals
    print('PASS_FOLLOWER_V31_FULL_ORIGINAL_LOADED_GATES_AND_EXACT_RECEIPT_HANDOFF')
if __name__=='__main__':check()
