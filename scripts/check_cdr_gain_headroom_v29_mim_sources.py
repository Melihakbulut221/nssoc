#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0
import ast,hashlib,json,runpy
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
def check():
    from check_cdr_selector_small_v24_mim_sources import check as prior
    from check_cdr_gain_headroom_v29_mim_capture_sources import check as capture
    prior();capture()
    for path,digest in json.loads((ROOT/'scripts/cdr-gain-headroom-v29-mim-input-pins.json').read_text()).items():
        assert hashlib.sha256((ROOT/path).read_bytes()).hexdigest()==digest,path
    for d in json.loads((ROOT/'scripts/cdr-gain-headroom-v29-mim-source-delta.json').read_text())['files']:
        raw=(ROOT/d['baseline_path']).read_bytes()
        assert hashlib.sha256(raw).hexdigest()==d['baseline_sha256']
        text=raw.decode()
        for e in d['edits']:
            assert text.count(e['before'])==e['count']
            text=text.replace(e['before'],e['after'])
        actual=(ROOT/d['candidate_path']).read_bytes()
        assert actual==text.encode() and hashlib.sha256(actual).hexdigest()==d['candidate_sha256']
    pin=json.loads((ROOT/'docs/evidence/cdr-gain-headroom-v29-mim-parent-capture-pass-20261022.json').read_text())
    assert pin['run']==39694160820 and pin['source_head']=='d4b48ffbf77a10a048166681a5054d9e1fbb4c12'
    assert pin['summary_sha256']=='ccfe6913daa977fe9de26cb413c993e408ba38ab53430cd6a24e74b3065da1a8'
    assert pin['parts_sha256']=='a7ae9795c127ebcfd94ab737f7a7592a7377d630f5d447be4f2e0b6bbe20c78a'
    r=pin['report'];got=r['intrinsic_capture_binding']
    assert r['status']=='PASS_PD476_MIM_AWARE_NATIVE_CAPTURE_AND_INTRINSIC_BINDING_REQUIRES_RAW_RC_AUDIT' and r['sources_unchanged']
    assert set(r['extraction_prerequisites'])=={'planes','wire-inputs','binding','rc'}
    assert got['R']==17906 and got['C']==12834 and len(got['native_mim_devices'])==7
    for stage,p in r['extraction_prerequisites'].items():
        b=json.loads((ROOT/('docs/evidence/cdr-gain-headroom-v29-'+stage+'-pass-20261022.json')).read_text())
        assert b['run']==39693048851 and b['source_head']=='db62ee1056042d7531d068c09a62359afe8cdcde'
        assert all(b[k]==p[k] for k in ('summary_sha256','parts_sha256','summary_asset','parts_asset','status'))
        assert b['report']['sources_unchanged']
    binding=json.loads((ROOT/'docs/evidence/cdr-gain-headroom-v29-binding-pass-20261022.json').read_text())
    assert binding['summary_sha256']==r['model_binding_source']['summary_sha256']
    producer=runpy.run_path(str(ROOT/'scripts/cloud_cdr_gain_headroom_v29_mim_stage.py'),run_name='handoff_preflight')
    generated=producer['receipt_path']('mim-parent-audit')
    consumer=ROOT/'scripts/cloud_cdr_gain_headroom_v29_mim_composition.py'
    literals={n.value for n in ast.walk(ast.parse(consumer.read_text()))if isinstance(n,ast.Constant)and isinstance(n.value,str)}
    assert str(generated.relative_to(ROOT))in literals
    assert generated==ROOT/'docs/evidence/cdr-gain-headroom-v29-mim-parent-audit-pass-20261022.json'
    print('PASS_V29_EXACT_FRESH17906R12834C_SEVEN_MIM_AND_PRODUCER_CONSUMER_HANDOFF')
if __name__=='__main__':check()
