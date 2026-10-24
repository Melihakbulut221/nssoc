#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0
"""Verify exact v25 source adaptation and real producer/consumer handoff paths."""
import ast,hashlib,json,runpy
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
def check():
    from check_cdr_selector_small_v24_mim_sources import check as prior
    from check_cdr_data3_v25_mim_capture_sources import check as capture
    prior();capture()
    for d in json.loads((ROOT/'scripts/cdr-data3-v25-mim-source-delta.json').read_text())['files']:
        raw=(ROOT/d['baseline_path']).read_bytes()
        assert hashlib.sha256(raw).hexdigest()==d['baseline_sha256']
        text=raw.decode()
        for e in d['edits']:
            assert text.count(e['before'])==e['count']
            text=text.replace(e['before'],e['after'])
        actual=(ROOT/d['candidate_path']).read_bytes()
        assert actual==text.encode() and hashlib.sha256(actual).hexdigest()==d['candidate_sha256']
    pin=json.loads((ROOT/'docs/evidence/cdr-data3-v25-mim-parent-capture-pass-20261021.json').read_text())
    assert pin['run']==39510847222 and pin['source_head']=='328927ad1ae5aef7fb2816dce02bfc83dfce6333'
    assert pin['summary_sha256']=='43fe7f46d64ec948d3e77f0b1c38241f310244da33dae710dadd17809898646c'
    assert pin['parts_sha256']=='09f0967cd76416f8dc6cd97301fa9949855dffa80e72213ae72ba18a3dac7d22'
    r=pin['report'];got=r['intrinsic_capture_binding']
    assert got['R']==17654 and got['C']==12682 and len(got['native_mim_devices'])==7
    for stage,p in r['extraction_prerequisites'].items():
        b=json.loads((ROOT/('docs/evidence/cdr-data3-v25-'+stage+'-pass-20261021.json')).read_text())
        assert b['run']==39510628948 and b['source_head']=='2e29b7ba7d776b8a5d2f77708b2ddc7faed86ef5'
        assert all(b[k]==p[k] for k in ('summary_sha256','parts_sha256','summary_asset','parts_asset','status'))
        assert b['report']['sources_unchanged']
    binding=json.loads((ROOT/'docs/evidence/cdr-data3-v25-binding-pass-20261021.json').read_text())
    assert binding['summary_sha256']==r['model_binding_source']['summary_sha256']
    producer=runpy.run_path(str(ROOT/'scripts/cloud_cdr_data3_v25_mim_stage.py'),run_name='handoff_preflight')
    generated=producer['receipt_path']('mim-parent-audit')
    consumer=ROOT/'scripts/cloud_cdr_data3_v25_mim_composition.py'
    literals={n.value for n in ast.walk(ast.parse(consumer.read_text())) if isinstance(n,ast.Constant) and isinstance(n.value,str)}
    assert str(generated.relative_to(ROOT)) in literals
    assert generated==ROOT/'docs/evidence/cdr-data3-v25-mim-parent-audit-pass-20261021.json'
    print('PASS_V25_EXACT_FRESH17654R12682C_SEVEN_MIM_AND_PRODUCER_CONSUMER_HANDOFF')
if __name__=='__main__':check()
