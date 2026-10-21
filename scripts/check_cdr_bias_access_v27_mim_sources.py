#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0
import ast,hashlib,json,runpy
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
def check():
    from check_cdr_selector_small_v24_mim_sources import check as prior
    from check_cdr_bias_access_v27_mim_capture_sources import check as capture
    prior();capture()
    for d in json.loads((ROOT/'scripts/cdr-bias-access-v27-mim-source-delta.json').read_text())['files']:
        raw=(ROOT/d['baseline_path']).read_bytes()
        assert hashlib.sha256(raw).hexdigest()==d['baseline_sha256']
        text=raw.decode()
        for e in d['edits']:
            assert text.count(e['before'])==e['count']
            text=text.replace(e['before'],e['after'])
        actual=(ROOT/d['candidate_path']).read_bytes()
        assert actual==text.encode() and hashlib.sha256(actual).hexdigest()==d['candidate_sha256']
    pin=json.loads((ROOT/'docs/evidence/cdr-bias-access-v27-mim-parent-capture-pass-20261021.json').read_text())
    assert pin['run']==39547470228 and pin['source_head']=='40389f8567f6f8e771b17b767cdcb5deb62103c9'
    assert pin['summary_sha256']=='af4e99efb0dfe42510302a84951a97bccfd88ddf6afc8f67883614038693de0f'
    assert pin['parts_sha256']=='b26c57763f75ae01b415c4f01c9f7313f150620a60854382f8f04c2d19d6f133'
    r=pin['report'];got=r['intrinsic_capture_binding']
    assert got['R']==17694 and got['C']==12714 and len(got['native_mim_devices'])==7
    for stage,p in r['extraction_prerequisites'].items():
        b=json.loads((ROOT/('docs/evidence/cdr-bias-access-v27-'+stage+'-pass-20261021.json')).read_text())
        assert b['run']==39547338459 and b['source_head']=='991d8d3b8feb82d018fe937a16fc8f0261201e9b'
        assert all(b[k]==p[k] for k in ('summary_sha256','parts_sha256','summary_asset','parts_asset','status'))
        assert b['report']['sources_unchanged']
    binding=json.loads((ROOT/'docs/evidence/cdr-bias-access-v27-binding-pass-20261021.json').read_text())
    assert binding['summary_sha256']==r['model_binding_source']['summary_sha256']
    producer=runpy.run_path(str(ROOT/'scripts/cloud_cdr_bias_access_v27_mim_stage.py'),run_name='handoff_preflight')
    generated=producer['receipt_path']('mim-parent-audit')
    consumer=ROOT/'scripts/cloud_cdr_bias_access_v27_mim_composition.py'
    literals={n.value for n in ast.walk(ast.parse(consumer.read_text()))if isinstance(n,ast.Constant)and isinstance(n.value,str)}
    assert str(generated.relative_to(ROOT))in literals
    assert generated==ROOT/'docs/evidence/cdr-bias-access-v27-mim-parent-audit-pass-20261021.json'
    print('PASS_V27_EXACT_FRESH17694R12714C_SEVEN_MIM_AND_PRODUCER_CONSUMER_HANDOFF')
if __name__=='__main__':check()
