#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0
import ast,hashlib,json,runpy
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
def check():
    from check_cdr_selector_small_v24_mim_sources import check as prior
    from check_cdr_input_impedance_v30_mim_capture_sources import check as capture
    prior();capture()
    for path,digest in json.loads((ROOT/'scripts/cdr-input-impedance-v30-mim-input-pins.json').read_text()).items():
        assert hashlib.sha256((ROOT/path).read_bytes()).hexdigest()==digest,path
    for d in json.loads((ROOT/'scripts/cdr-input-impedance-v30-mim-source-delta.json').read_text())['files']:
        raw=(ROOT/d['baseline_path']).read_bytes()
        assert hashlib.sha256(raw).hexdigest()==d['baseline_sha256']
        text=raw.decode()
        for e in d['edits']:
            assert text.count(e['before'])==e['count']
            text=text.replace(e['before'],e['after'])
        actual=(ROOT/d['candidate_path']).read_bytes()
        assert actual==text.encode() and hashlib.sha256(actual).hexdigest()==d['candidate_sha256']
    pin=json.loads((ROOT/'docs/evidence/cdr-input-impedance-v30-mim-parent-capture-pass-20261022.json').read_text())
    assert pin['run']==39708084548 and pin['source_head']=='ea39f289a589d3a1bf2973a6c46b7e8d3406efc8'
    assert pin['summary_sha256']=='260420a91547b8b245e6f7bca362e52991a11669f45f42d48801b1a2f8ea6a51'
    assert pin['parts_sha256']=='e1215d30bf8db5e6d4a70ac496782c08f28b2a4782ecca36ee3ae2edd4689dcb'
    r=pin['report'];got=r['intrinsic_capture_binding']
    assert r['status']=='PASS_PD476_MIM_AWARE_NATIVE_CAPTURE_AND_INTRINSIC_BINDING_REQUIRES_RAW_RC_AUDIT' and r['sources_unchanged']
    assert set(r['extraction_prerequisites'])=={'planes','wire-inputs','binding','rc'}
    assert got['R']==17918 and got['C']==12850 and len(got['native_mim_devices'])==7
    for stage,p in r['extraction_prerequisites'].items():
        b=json.loads((ROOT/('docs/evidence/cdr-input-impedance-v30-'+stage+'-pass-20261022.json')).read_text())
        assert b['run']==39707446970 and b['source_head']=='97c114638871b59de1cb6f0192391436ce9f5b01'
        assert all(b[k]==p[k] for k in ('summary_sha256','parts_sha256','summary_asset','parts_asset','status'))
        assert b['report']['sources_unchanged']
    binding=json.loads((ROOT/'docs/evidence/cdr-input-impedance-v30-binding-pass-20261022.json').read_text())
    assert binding['summary_sha256']==r['model_binding_source']['summary_sha256']
    producer=runpy.run_path(str(ROOT/'scripts/cloud_cdr_input_impedance_v30_mim_stage.py'),run_name='handoff_preflight')
    generated=producer['receipt_path']('mim-parent-audit')
    consumer=ROOT/'scripts/cloud_cdr_input_impedance_v30_mim_composition.py'
    literals={n.value for n in ast.walk(ast.parse(consumer.read_text()))if isinstance(n,ast.Constant)and isinstance(n.value,str)}
    assert str(generated.relative_to(ROOT))in literals
    assert generated==ROOT/'docs/evidence/cdr-input-impedance-v30-mim-parent-audit-pass-20261022.json'
    print('PASS_V30_EXACT_FRESH17918R12850C_SEVEN_MIM_AND_PRODUCER_CONSUMER_HANDOFF')
if __name__=='__main__':check()
