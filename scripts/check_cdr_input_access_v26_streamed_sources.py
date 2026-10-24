#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0
import ast,hashlib,json,re,runpy
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
def check():
    from check_cdr_selector_small_v24_streamed_sources import check as original
    from check_cdr_input_access_v26_mim_sources import check as physical
    original();physical()
    for d in json.loads((ROOT/'scripts/cdr-input-access-v26-streamed-source-delta.json').read_text())['files']:
        raw=(ROOT/d['baseline_path']).read_bytes()
        assert hashlib.sha256(raw).hexdigest()==d['baseline_sha256']
        text=raw.decode()
        for e in d['edits']:
            assert text.count(e['before'])==e['count']
            text=text.replace(e['before'],e['after'])
        actual=(ROOT/d['candidate_path']).read_bytes()
        assert actual==text.encode() and hashlib.sha256(actual).hexdigest()==d['candidate_sha256']
        assert re.findall(r'[0-9a-f]{64}',raw.decode())==re.findall(r'[0-9a-f]{64}',actual.decode())
    spec=json.loads((ROOT/'docs/evidence/cdr-input-access-v26-fullwave-input-20261021.json').read_text())
    assert spec=={'run': 39533943848, 'source_head': 'ac80df8ba248afe9223a458552a467cb2081c2b9', 'workflow_path': '.github/workflows/cdr-input-access-v26-mim-validation-cloud.yml', 'capture_summary_sha256': 'dc8d837daa706d973287704cea244e09eea21fbf71a4a54a3625964951f66149'}
    planes=json.loads((ROOT/'docs/evidence/cdr-input-access-v26-planes-pass-20261021.json').read_text())
    assert planes['run']==39532277767 and planes['summary_sha256']=='0a368140e54a1a9483f3142e8d20271a9505673351b106503aa505dca8aee397'
    assert planes['report']['physical_source']['summary_sha256']=='9182d81d1edd700aa7a5884b2f29f4611e254c298ad278fa8fc6898ee77c6856'
    assert len(planes['report']['native_planes']['anchors'])==160
    producer=runpy.run_path(str(ROOT/'scripts/cloud_cdr_input_access_v26_fullwave_stage.py'),run_name='fullwave_handoff_preflight')
    path=producer['receipt_path']('mim-composition')
    literals={n.value for n in ast.walk(ast.parse((ROOT/'scripts/cloud_cdr_input_access_v26_mim_streamed.py').read_text()))if isinstance(n,ast.Constant)and isinstance(n.value,str)}
    assert str(path.relative_to(ROOT))in literals
    print('PASS_INPUT_ACCESS_V26_FULL_ORIGINAL_LOADED_GATES_AND_EXACT_RECEIPT_HANDOFF')
if __name__=='__main__':check()
