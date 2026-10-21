#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0
import ast,hashlib,json,runpy
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
def check():
    from check_cdr_selector_small_v24_mim_sources import check as prior
    from check_cdr_input_loading_v28_mim_capture_sources import check as capture
    prior();capture()
    for d in json.loads((ROOT/'scripts/cdr-input-loading-v28-mim-source-delta.json').read_text())['files']:
        raw=(ROOT/d['baseline_path']).read_bytes()
        assert hashlib.sha256(raw).hexdigest()==d['baseline_sha256']
        text=raw.decode()
        for e in d['edits']:
            assert text.count(e['before'])==e['count']
            text=text.replace(e['before'],e['after'])
        actual=(ROOT/d['candidate_path']).read_bytes()
        assert actual==text.encode() and hashlib.sha256(actual).hexdigest()==d['candidate_sha256']
    pin=json.loads((ROOT/'docs/evidence/cdr-input-loading-v28-mim-parent-capture-pass-20261021.json').read_text())
    assert pin['run']==39561460306 and pin['source_head']=='84cce05f98a13e7fa96ddfc86dcb54eef0819724'
    assert pin['summary_sha256']=='d830a3e6ba3e0959a2e9382717afd3dd960eb0c43118284b0af183135a1186f2'
    assert pin['parts_sha256']=='7577df6bcf126a0f9c705f4e69853670aa5f84cd2872eb721e6ba0923e876618'
    r=pin['report'];got=r['intrinsic_capture_binding']
    assert got['R']==17674 and got['C']==12694 and len(got['native_mim_devices'])==7
    for stage,p in r['extraction_prerequisites'].items():
        b=json.loads((ROOT/('docs/evidence/cdr-input-loading-v28-'+stage+'-pass-20261021.json')).read_text())
        assert b['run']==39559188023 and b['source_head']=='f79741aa2d89467db07e00171355b8347d60dd36'
        assert all(b[k]==p[k] for k in ('summary_sha256','parts_sha256','summary_asset','parts_asset','status'))
        assert b['report']['sources_unchanged']
    binding=json.loads((ROOT/'docs/evidence/cdr-input-loading-v28-binding-pass-20261021.json').read_text())
    assert binding['summary_sha256']==r['model_binding_source']['summary_sha256']
    producer=runpy.run_path(str(ROOT/'scripts/cloud_cdr_input_loading_v28_mim_stage.py'),run_name='handoff_preflight')
    generated=producer['receipt_path']('mim-parent-audit')
    consumer=ROOT/'scripts/cloud_cdr_input_loading_v28_mim_composition.py'
    literals={n.value for n in ast.walk(ast.parse(consumer.read_text()))if isinstance(n,ast.Constant)and isinstance(n.value,str)}
    assert str(generated.relative_to(ROOT))in literals
    assert generated==ROOT/'docs/evidence/cdr-input-loading-v28-mim-parent-audit-pass-20261021.json'
    print('PASS_V28_EXACT_FRESH17674R12694C_SEVEN_MIM_AND_PRODUCER_CONSUMER_HANDOFF')
if __name__=='__main__':check()
