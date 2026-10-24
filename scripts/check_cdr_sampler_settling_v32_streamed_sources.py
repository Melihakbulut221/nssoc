#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0
import ast,hashlib,json,re,runpy
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
def check():
    from check_cdr_follower_v31_streamed_sources import check as original
    from check_cdr_sampler_settling_v32_mim_sources import check as physical
    original();physical()
    for d in json.loads((ROOT/'scripts/cdr-sampler-settling-v32-streamed-source-delta.json').read_text())['files']:
        raw=(ROOT/d['baseline_path']).read_bytes()
        assert hashlib.sha256(raw).hexdigest()==d['baseline_sha256']
        text=raw.decode()
        for e in d['edits']:
            assert text.count(e['before'])==e['count']
            text=text.replace(e['before'],e['after'])
        actual=(ROOT/d['candidate_path']).read_bytes()
        assert actual==text.encode() and hashlib.sha256(actual).hexdigest()==d['candidate_sha256']
        assert re.findall(r'[0-9a-f]{64}',raw.decode())==re.findall(r'[0-9a-f]{64}',actual.decode())
    spec=json.loads((ROOT/'docs/evidence/cdr-sampler-settling-v32-fullwave-input-20261022.json').read_text())
    assert spec=={'run': 39742448854, 'source_head': '0a0d9d20af589206b24b281faf28fa5c329d64fc', 'workflow_path': '.github/workflows/cdr-sampler-settling-v32-mim-validation-cloud.yml', 'capture_summary_sha256': 'e12cfa1fe10452af4ce3de39516ac19d52aa05d7b2b37284d025050fbc3bac98'}
    planes=json.loads((ROOT/'docs/evidence/cdr-sampler-settling-v32-planes-pass-20261022.json').read_text())
    assert planes['run']==39740697762 and planes['summary_sha256']=='e4a4ba4533c6e8603dc7765250b840d6cc4a574623150ad047325f58cd4780da'
    assert planes['report']['physical_source']['summary_sha256']=='946587a69d7843b31025493531a10f1bfad2454029fe91df703cb0967ea71ae1'
    assert len(planes['report']['native_planes']['anchors'])==160
    producer=runpy.run_path(str(ROOT/'scripts/cloud_cdr_sampler_settling_v32_fullwave_stage.py'),run_name='fullwave_handoff_preflight')
    path=producer['receipt_path']('mim-composition')
    literals={n.value for n in ast.walk(ast.parse((ROOT/'scripts/cloud_cdr_sampler_settling_v32_mim_streamed.py').read_text()))if isinstance(n,ast.Constant)and isinstance(n.value,str)}
    assert str(path.relative_to(ROOT))in literals
    print('PASS_SAMPLER_SETTLING_V32_FULL_ORIGINAL_LOADED_GATES_AND_EXACT_RECEIPT_HANDOFF')
if __name__=='__main__':check()
